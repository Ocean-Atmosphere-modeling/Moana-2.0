#!/usr/bin/env python3
"""
Interpolate raw ocean fields (from download_input.py) to the open boundaries of a ROMS grid.

  python scripts/make_bry.py                 # uses make_bry.yaml at the repo root
  python scripts/make_bry.py other.yaml

Output: one ROMS boundary file (BRYNAME) with zeta, ubar, vbar, u, v, temp, salt for each edge in
EDGES, on the grid's rho/u/v points and on the s-levels in VERTICAL.

Method, per edge (only edge points are computed, never the full 3-D grid):
1. Source: each file in SOURCES is cut to a strip around the edge. Longitude is taken modulo 360,
   so tiles on both sides of 180E join into one array; tiles of different dates are joined in time
   and duplicate times dropped. Each variable keeps its own time axis (hourly zos with 6-hourly
   T/S/UV is fine).
2. Land fill: on each source level, a NaN cell takes the value of the nearest wet cell (distance
   transform). A level with no wet cell takes the level above.
3. Horizontal: bilinear from the regular lon/lat source to the edge points. Steps 2-3 are one
   precomputed gather index, so each variable costs one fancy-index over all times.
4. Vertical: linear in depth to the ROMS z of the s-levels at rest (zeta = 0); constant above the
   top and below the bottom source level.
5. Velocity: uo/vo (east/north) go to u- and v-points and are rotated by the grid angle.
   ubar/vbar are the Hz-weighted mean of u/v on the ROMS levels, so 2-D and 3-D fields agree.

The script stops if an edge point is outside the source or the source has a gap (e.g. the cut at
180E, docs/devlog.md 2026-10-20), and if any output value is not finite.
"""
import glob
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import yaml
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
EDGE = {"west": np.s_[:, 0], "east": np.s_[:, -1], "south": np.s_[0, :], "north": np.s_[-1, :]}
# ROMS field -> (point set, time variable, units, long name)
META = {
    "zeta": ("rho", "zeta_time", "meter", "free-surface"),
    "ubar": ("u", "v2d_time", "meter second-1", "vertically integrated u-momentum component"),
    "vbar": ("v", "v2d_time", "meter second-1", "vertically integrated v-momentum component"),
    "u": ("u", "v3d_time", "meter second-1", "u-momentum component"),
    "v": ("v", "v3d_time", "meter second-1", "v-momentum component"),
    "temp": ("rho", "temp_time", "Celsius", "potential temperature"),
    "salt": ("rho", "salt_time", "PSU", "salinity"),
}
SRC_TIME = {"zeta_time": "zeta", "v2d_time": "u", "v3d_time": "u", "temp_time": "temp", "salt_time": "salt"}


# ------------------------------------------------------------------ grid and s-levels
def grid_points(g):
    """lon (0-360), lat, h, angle on rho, u and v points, as full 2-D arrays."""
    h, a = g.h.values, g.angle.values
    au = lambda f: 0.5 * (f[:, :-1] + f[:, 1:])
    av = lambda f: 0.5 * (f[:-1] + f[1:])
    return {
        "rho": dict(lon=g.lon_rho.values % 360, lat=g.lat_rho.values, h=h, angle=a),
        "u": dict(lon=g.lon_u.values % 360, lat=g.lat_u.values, h=au(h), angle=au(a)),
        "v": dict(lon=g.lon_v.values % 360, lat=g.lat_v.values, h=av(h), angle=av(a)),
    }


def s_coord(N, Vstretching, theta_s, theta_b, w=False):
    """s and C(s) on rho (N) or w (N+1) levels, as ROMS/Utility/set_scoord.F."""
    k = np.arange(N + 1.0) if w else np.arange(1, N + 1) - 0.5
    if Vstretching == 4:
        s = (k - N) / N
    elif Vstretching == 5:
        s = -(k * k - 2 * k * N + k + N * N - N) / (N * N - N) - 0.01 * (k * k - k * N) / (1 - N)
    else:
        sys.exit(f"Vstretching {Vstretching} is not coded (4 or 5)")
    C = (1 - np.cosh(theta_s * s)) / (np.cosh(theta_s) - 1) if theta_s > 0 else -s**2
    if theta_b > 0:
        C = (np.exp(theta_b * C) - 1) / (1 - np.exp(-theta_b))
    return s, C


def z_levels(h, v, w=False):
    """z (m, negative) of the s-levels at rest, Vtransform 2 (hc = Tcline): (N or N+1, points)."""
    s, C = s_coord(v["N"], v["Vstretching"], v["theta_s"], v["theta_b"], w)
    hc = v["Tcline"]
    return h * (hc * s[:, None] + h * C[:, None]) / (hc + h)


# ------------------------------------------------------------------ source
def open_source(path):
    """Raw file with dims named lon, lat, depth (positive down, surface first), lon in 0-360."""
    ds = xr.open_dataset(path)
    ds = ds.rename({k: v for k, v in (("longitude", "lon"), ("latitude", "lat")) if k in ds.dims})
    if "elevation" in ds.dims:
        ds = ds.assign_coords(depth=-ds.elevation).swap_dims(elevation="depth").drop_vars("elevation")
    ds = ds.assign_coords(lon=ds.lon % 360)
    return ds.sortby([d for d in ("lon", "lat", "depth") if d in ds.dims])


def load(sources, name, lon, lat, pad, edge):
    """Variable `name` on a strip around the points, tiles joined: (time, depth, lat, lon)."""
    tiles = {}
    for ds in sources:
        if name not in ds:
            continue
        da = ds[name] if "depth" in ds[name].dims else ds[name].expand_dims(depth=[0.0])
        da = da.sel(lon=slice(lon.min() - pad, lon.max() + pad), lat=slice(lat.min() - pad, lat.max() + pad))
        if da.lon.size and da.lat.size:
            tiles.setdefault((round(float(da.lon[0]), 3), round(float(da.lat[0]), 3)), []).append(da)
    if not tiles:
        sys.exit(f"{edge} edge: no file in SOURCES has {name} near the edge")
    parts = [xr.concat(t, "time").sortby("time").drop_duplicates("time").to_dataset(name=name)
             for t in tiles.values()]
    da = xr.combine_by_coords(parts, join="inner")[name].transpose("time", "depth", "lat", "lon").load()
    for c, x in (("lon", lon), ("lat", lat)):
        s = da[c].values
        ds_ = np.diff(s)
        if x.min() < s[0] or x.max() > s[-1] or ds_.max() > 1.5 * np.median(ds_):
            sys.exit(f"{edge} edge, {name}: points need {c} {x.min():.2f} to {x.max():.2f}; "
                     f"source has {s[0]:.2f} to {s[-1]:.2f}, largest step {ds_.max():.3f}")
    return da


# ------------------------------------------------------------------ interpolation
def hinterp(da, lon, lat):
    """Land-filled bilinear interpolation of da (time, depth, lat, lon) to points: (time, depth, pt)."""
    x, y, f = da.lon.values, da.lat.values, da.values
    nt, nz, ny, nx = f.shape
    i = np.clip(np.searchsorted(x, lon) - 1, 0, nx - 2)
    j = np.clip(np.searchsorted(y, lat) - 1, 0, ny - 2)
    wx, wy = (lon - x[i]) / (x[i + 1] - x[i]), (lat - y[j]) / (y[j + 1] - y[j])
    jc, ic = np.stack([j, j, j + 1, j + 1]), np.stack([i, i + 1, i, i + 1])        # 4 corners
    w = np.stack([(1 - wx) * (1 - wy), wx * (1 - wy), (1 - wx) * wy, wx * wy])
    idx, kk = np.empty((nz,) + jc.shape, dtype=np.intp), np.arange(nz)
    for k in range(nz):                                    # surface first
        wet = np.isfinite(f[0, k])
        if not wet.any():
            if k == 0:
                sys.exit(f"{da.name}: no wet source cell at the top level")
            idx[k], kk[k] = idx[k - 1], kk[k - 1]
            continue
        _, (nj, ni) = ndimage.distance_transform_edt(~wet, return_indices=True)
        idx[k] = (nj * nx + ni)[jc, ic]
    return (f.reshape(nt, nz, ny * nx)[:, kk[:, None, None], idx] * w).sum(axis=2)


def vinterp(f, dep, z):
    """Linear in depth: f (time, depth, pt) on source depths dep -> (time, N, pt) at z (N, pt)."""
    d = np.clip(-z, dep[0], dep[-1])
    k = np.clip(np.searchsorted(dep, d) - 1, 0, len(dep) - 2)
    w = (d - dep[k]) / (dep[k + 1] - dep[k])
    p = np.arange(z.shape[1])
    return f[:, k, p] * (1 - w) + f[:, k + 1, p] * w


# ------------------------------------------------------------------ main
def main():
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "make_bry.yaml"
    cfg = yaml.safe_load(open(cfg_path))
    vert, vmap = cfg["VERTICAL"], cfg["VARMAP"]
    if vert["Vtransform"] != 2:
        sys.exit("only Vtransform 2 is coded")
    files = sorted(f for p in cfg["SOURCES"] for f in glob.glob(str(p)))
    if not files:
        sys.exit(f"no file matches SOURCES {cfg['SOURCES']}")
    print(f"config {cfg_path}\n{len(files)} source files")
    sources = [open_source(f) for f in files]
    pts = grid_points(xr.open_dataset(cfg["GRID"]))

    out, times = {}, {}
    for edge in cfg["EDGES"]:
        e = {p: {q: a[EDGE[edge]] for q, a in d.items()} for p, d in pts.items()}
        lon = np.concatenate([e[p]["lon"] for p in e])
        lat = np.concatenate([e[p]["lat"] for p in e])
        src = {r: load(sources, vmap[r], lon, lat, cfg["PAD_DEG"], edge) for r in ("zeta", "temp", "salt", "u", "v")}

        def on(r, p):
            f = hinterp(src[r], e[p]["lon"], e[p]["lat"])
            return f[:, 0] if r == "zeta" else vinterp(f, src[r].depth.values, z_levels(e[p]["h"], vert))

        f = {r: on(r, "rho") for r in ("zeta", "temp", "salt")}
        for p in ("u", "v"):
            ue, vn = on("u", p), on("v", p)
            ca, sa = np.cos(e[p]["angle"]), np.sin(e[p]["angle"])
            f[p] = ue * ca + vn * sa if p == "u" else vn * ca - ue * sa
            hz = np.diff(z_levels(e[p]["h"], vert, w=True), axis=0)
            f[p + "bar"] = (f[p] * hz).sum(axis=1) / hz.sum(axis=0)

        if not np.array_equal(src["u"].time, src["v"].time):
            sys.exit(f"{edge} edge: {vmap['u']} and {vmap['v']} have different times")
        for tname, r in SRC_TIME.items():
            t = src[r].time.values
            if tname in times and not np.array_equal(times[tname], t):
                sys.exit(f"{edge} edge: {tname} differs from the other edges")
            times[tname] = t
        for r, a in f.items():
            if not np.isfinite(a).all():
                sys.exit(f"{edge} edge: {r} has values that are not finite")
            out[r, edge] = a
            print(f"{r + '_' + edge:11s} {str(a.shape):16s} min {a.min():9.3f}  max {a.max():9.3f}")

    t_ref = pd.Timestamp(cfg["TIME_REF"])
    s_rho, Cs_r = s_coord(vert["N"], vert["Vstretching"], vert["theta_s"], vert["theta_b"])
    ds = xr.Dataset(coords={"s_rho": ("s_rho", s_rho, {"long_name": "S-coordinate at RHO-points"})})
    ds["Cs_r"] = ("s_rho", Cs_r, {"long_name": "S-coordinate stretching curves at RHO-points"})
    for tname, t in times.items():
        ds[tname] = (tname, (pd.DatetimeIndex(t) - t_ref) / pd.Timedelta("1D"),
                     {"long_name": f"{tname.replace('_', ' ')}", "units": f"days since {t_ref:%Y-%m-%d %H:%M:%S}"})
    for (r, edge), a in out.items():
        p, tname, units, long_name = META[r]
        along = f"{'eta' if edge in ('west', 'east') else 'xi'}_{p}"
        dims = (tname, "s_rho", along) if a.ndim == 3 else (tname, along)
        ds[f"{r}_{edge}"] = (dims, a.astype("f4"),
                             {"long_name": f"{long_name}, {edge} boundary", "units": units, "time": tname})

    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    ds.attrs = {"type": "ROMS boundary file", "grid": str(cfg["GRID"]), "sources": " ".join(files),
                **{k: str(v) for k, v in vert.items()},
                "history": f"scripts/make_bry.py {cfg_path} (git {commit or 'unknown'}), {pd.Timestamp.now():%Y-%m-%d %H:%M}"}
    out_path = Path(cfg["OUTPUT"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out_path, encoding={v: {"_FillValue": None} for v in ds.variables})
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
