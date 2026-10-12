#!/usr/bin/env python
"""Make the ROMS tidal forcing file (TIDENAME) from the TPXO9-atlas cut.

Usage (moana_python environment, see env/moana_python.yml):

    python scripts/make_tide_file.py --start 2017-10-01 --end 2018-10-01 \\
        --cons M2,S2,N2,K2,K1,O1,P1,Q1,MF,MM,M4 [--out FILE]

Reads Input/tides/tpxo9_atlas_v5_moana.nc (scripts/fetch_tpxo.py) and the
model grid, and writes --out (default
Input/tides/moana_tide_<start>_<end>.nc) in the form the pinned ROMS reads
(ROMS/Nonlinear/get_idata.F, ROMS/Nonlinear/set_tides.F):

  tide_period(tide_period)                  hours
  tide_Eamp, tide_Ephase                    m, degrees
  tide_Cmax, tide_Cmin, tide_Cangle, tide_Cphase   m s-1, degrees
  zero_phase_date                           YYYYMMDD.dddd

Every field is (tide_period, eta_rho, xi_rho) on rho-points; ROMS takes the
number of constituents from the length of tide_period. set_tides.F makes

  zeta = sum Eamp cos(w (t - t0) - Ephase)
  (u, v) along/across the major axis = Cmax cos(psi), Cmin sin(psi),
      psi = w (t - t0) - Cphase, major axis Cangle - angler from east,

with t0 = zero_phase_date (when the file has it, ROMS ignores TIDE_START in
the .in file). ROMS applies no nodal correction, so the file carries it:
Eamp, Cmax, Cmin are f times the TPXO values and the phases are
G - (V0 + u), with V0 at --start and f, u at the middle of [--start, --end].
f and u drift (by up to ~4 % and ~2.5 deg a year for K1 and O1), so a file is
for one run period, and a long run needs one file per segment.

V0 + u and f are those of pyTMD's TPXO ("OTIS") predictor:
V0 = w (t0 - 1992-01-01) + phase0 from its OTIS constituent table, which for
M4 and MN4 differs from the Doodson argument by 5-10 deg. Constituents with
no OTIS frequency (S1) are refused. TPXO complex amplitudes use the OSU sign
(G = atan2(-Im, Re), as in Apps/moana/python_scripts/plot_tides.py).

Interpolation: TPXO land cells are first filled from the nearest wet cell
(so wet model cells beside a TPXO coast get the coastal value, not zero),
then the real and imaginary parts of h and of the transports U = u dep,
V = v dep (dep: TPXO depth) are interpolated bilinearly to the rho-points;
amplitude and phase are never interpolated. Model velocities are U / h and
V / h with the model depth h, which keeps TPXO's volume flux where the two
bathymetries differ; interpolating u, v instead carries currents of up to
12 m/s from TPXO's 1-5 m island cells (e.g. the Snares) into 140 m of model
water. Current ellipses are made from these u, v. Model land is 0. ROMS
only uses the values at the open boundaries (ADD_FSOBC, ADD_M2OBC in
moana.h), but the whole grid is written.

scripts/check_tide_file.py checks a file against pyTMD's own prediction.
"""

import argparse
import datetime as dt
import hashlib
import os
import subprocess
from pathlib import Path

import numpy as np
import pyTMD
import pyTMD.constituents as tc
import xarray as xr
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import distance_transform_edt

REPO = Path(__file__).resolve().parents[1]
TIDES = Path("/projects/f_omg_1/moa/moana/Input/tides")
TPXO = TIDES / "tpxo9_atlas_v5_moana.nc"
GRID = REPO / "Apps" / "moana" / "Input" / "moana_grid.nc"
MJD_EPOCH = dt.datetime(1858, 11, 17)
MJD_TIDE = 48622.0  # MJD of 1992-01-01, the epoch of pyTMD's OTIS phases


def mjd(t):
    return (t - MJD_EPOCH).total_seconds() / 86400.0


def git_version():
    """MOANA_GIT if set (compute nodes have no git), else git describe."""
    if os.environ.get("MOANA_GIT"):
        return os.environ["MOANA_GIT"]
    try:
        r = subprocess.run(["git", "-C", str(REPO), "describe", "--always", "--dirty"],
                           capture_output=True, text=True)
        return r.stdout.strip() or "unknown"
    except FileNotFoundError:
        return "unknown (no git)"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def astro(cons, start, nodal):
    """Period (h), f, and V0 + u (rad) at `start`, f and u at `nodal`."""
    names = [c.lower() for c in cons]
    _, phase0, omega, _, _ = tc._constituent_parameters(names)
    if np.any(omega <= 0):
        bad = [c for c, w in zip(cons, omega) if w <= 0]
        raise SystemExit(f"no OTIS frequency in pyTMD for {bad}")
    pu, pf, _ = tc.arguments(np.array([mjd(nodal)]), names, corrections="OTIS")
    v0u = omega * 86400.0 * (mjd(start) - MJD_TIDE) + phase0 + pu[0]
    return 2 * np.pi / omega / 3600.0, pf[0], v0u


def interpolator(tpxo, wet):
    """Function mapping a TPXO (con, lat, lon) complex field to (lat, lon)
    points, with TPXO land filled from the nearest wet cell first."""
    jj, ii = distance_transform_edt(~wet, return_distances=False, return_indices=True)
    lat, lon = tpxo.lat.values, tpxo.lon.values

    def to(z, plat, plon):
        z = z[:, jj, ii]
        vals = np.stack([z.real, z.imag], axis=-1).transpose(1, 2, 0, 3)
        f = RegularGridInterpolator((lat, lon), vals, bounds_error=True)
        out = f(np.column_stack([np.ravel(plat), np.ravel(plon)]))
        out = out[..., 0] + 1j * out[..., 1]  # (point, con)
        return out.T.reshape((z.shape[0],) + np.shape(plat))

    return to


def load_tpxo(path, cons):
    tpxo = xr.open_dataset(path)
    have = [str(c) for c in tpxo.con.values]
    missing = [c for c in cons if c not in have]
    if missing:
        raise SystemExit(f"{missing} not in {path} (has {have})")
    tpxo = tpxo.sel(con=list(cons))
    cx = {v: (tpxo[v + "Re"] + 1j * tpxo[v + "Im"]).values.astype(np.complex128)
          for v in ("h", "u", "v")}
    wet = (tpxo.dep.values > 0) & (np.abs(cx["h"][0]) > 0)
    return tpxo, cx, wet


def on_grid(path, cons, lat, lon, depth):
    """TPXO complex h (m), u, v (m/s) at points of model depth `depth`,
    each (con,) + lat.shape. Also returns the TPXO dataset and wet mask."""
    tpxo, cx, wet = load_tpxo(path, cons)
    to = interpolator(tpxo, wet)
    dep = np.where(wet, tpxo.dep.values, 0.0)
    h = to(cx["h"], lat, lon)
    u = to(cx["u"] * dep, lat, lon) / depth
    v = to(cx["v"] * dep, lat, lon) / depth
    return h, u, v, tpxo, wet


def ellipse(u, v):
    """Current ellipse from complex amplitudes (OSU sign, e^{i(wt + V)}).

    Returns semi-major, semi-minor (positive: anticlockwise), inclination
    (deg anticlockwise from east, in [0, 180)) and the phase G_c (deg) at
    which the current is largest along the inclination, so that along the
    major and minor axes the current is (major cos(V - G_c), minor sin(V - G_c)).
    """
    wp = (u + 1j * v) / 2          # anticlockwise part, ~ e^{+iV}
    wm = (np.conj(u) + 1j * np.conj(v)) / 2  # clockwise part, ~ e^{-iV}
    tp, tm = np.angle(wp), np.angle(wm)
    incl = (tp + tm) / 2
    gc = (tm - tp) / 2
    k = np.floor(incl / np.pi)     # turning the axis by pi moves the phase by pi
    incl, gc = incl - k * np.pi, gc + k * np.pi
    return (np.abs(wp) + np.abs(wm), np.abs(wp) - np.abs(wm),
            np.degrees(incl), np.degrees(gc))


def tide_fields(h, u, v, f, v0u):
    """ROMS tide variables from complex amplitudes on the model grid."""
    f = f[:, None, None]
    v0u = np.degrees(v0u)[:, None, None]
    major, minor, incl, gc = ellipse(u, v)
    G = np.degrees(np.arctan2(-h.imag, h.real))
    return {
        "tide_Eamp": f * np.abs(h),
        "tide_Ephase": np.mod(G - v0u, 360.0),
        "tide_Cmax": f * major,
        "tide_Cmin": f * minor,
        "tide_Cangle": incl,
        "tide_Cphase": np.mod(gc - v0u, 360.0),
    }


ATTRS = {  # as ROMS/External/varinfo.yaml
    "tide_period": ("tidal period", "hours"),
    "tide_Eamp": ("tidal elevation amplitude", "meter"),
    "tide_Ephase": ("tidal elevation phase angle", "degrees"),
    "tide_Cmax": ("maximum tidal current, ellipse major axis", "meter second-1"),
    "tide_Cmin": ("minimum tidal current, ellipse minor axis", "meter second-1"),
    "tide_Cangle": ("tidal current inclination angle", "degrees"),
    "tide_Cphase": ("tidal current phase angle", "degrees"),
}
NOTES = {
    "tide_Ephase": "phase lag behind zero_phase_date: Greenwich phase minus (V0 + u)",
    "tide_Cmin": "positive: anticlockwise rotation",
    "tide_Cangle": "anticlockwise from east (geographic); ROMS subtracts angler",
    "tide_Cphase": "phase lag of the major-axis current behind zero_phase_date",
}


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--start", required=True, type=dt.date.fromisoformat,
                   help="zero-phase date (00 UTC), normally the run start")
    p.add_argument("--end", required=True, type=dt.date.fromisoformat,
                   help="run end; f and u are taken at mid-period")
    p.add_argument("--cons", required=True,
                   help="comma-separated TPXO names, e.g. M2,S2,K1,O1")
    p.add_argument("--tpxo", type=Path, default=TPXO)
    p.add_argument("--grid", type=Path, default=GRID)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    cons = [c.strip().upper() for c in a.cons.split(",") if c.strip()]
    start = dt.datetime.combine(a.start, dt.time())
    end = dt.datetime.combine(a.end, dt.time())
    if end <= start:
        raise SystemExit("--end must be after --start")
    nodal = start + (end - start) / 2
    out = a.out or TIDES / f"moana_tide_{start:%Y%m%d}_{end:%Y%m%d}.nc"

    grd = xr.open_dataset(a.grid)
    lat_r, lon_r = grd.lat_rho.values, grd.lon_rho.values
    ocean = grd.mask_rho.values > 0.5
    h, u, v, tpxo, wet = on_grid(a.tpxo, cons, lat_r, lon_r, grd.h.values)
    period, f, v0u = astro(cons, start, nodal)
    fields = tide_fields(h, u, v, f, v0u)

    ds = xr.Dataset(coords={"tide_period": ("tide_period", period)})
    ds["tide_name"] = ("tide_period", np.array(cons, dtype="S4"),
                       {"long_name": "tidal constituent name"})
    for k, val in fields.items():
        ds[k] = (("tide_period", "eta_rho", "xi_rho"), np.where(ocean, val, 0.0))
    for k, (ln, units) in ATTRS.items():
        ds[k].attrs.update(long_name=ln, units=units)
        if k in NOTES:
            ds[k].attrs["comment"] = NOTES[k]
    ds["tide_period"].attrs["comment"] = "2 pi / omega, omega from pyTMD (OTIS)"
    ds["zero_phase_date"] = ((), float(f"{start:%Y%m%d}"), {
        "long_name": "tidal reference date for zero phase",
        "units": "days as %Y%m%d.%f", "C_format": "%13.4f",
        "FORTRAN_format": "(f13.4)"})
    for k in ("lon_rho", "lat_rho", "mask_rho"):
        ds[k] = (("eta_rho", "xi_rho"), grd[k].values, grd[k].attrs)
    ds["nodal_f"] = ("tide_period", f, {"long_name": "nodal amplitude factor f "
                                        "applied to Eamp, Cmax, Cmin"})
    ds["V0_plus_u"] = ("tide_period", np.mod(np.degrees(v0u), 360.0), {
        "long_name": "equilibrium argument V0 at zero_phase_date plus nodal angle u",
        "units": "degrees"})
    ds.attrs = {
        "type": "ROMS tidal forcing file",
        "title": "Moana tidal forcing from TPXO9-atlas v5",
        "constituents": " ".join(cons),
        "run_start": start.isoformat(),
        "run_end": end.isoformat(),
        "zero_phase_date": f"{start:%Y-%m-%d %H:%M} UTC",
        "nodal_correction_date": f"{nodal:%Y-%m-%d %H:%M} UTC (middle of "
                                 f"{start:%Y-%m-%d} to {end:%Y-%m-%d})",
        "nodal_corrections": f"pyTMD {pyTMD.__version__}, corrections='OTIS'",
        "tpxo_file": f"{a.tpxo} (sha256 {sha256(a.tpxo)})",
        "tpxo_datamesh_cache_hash": tpxo.attrs.get("datamesh_cache_hash", "❓"),
        "grid_file": f"{a.grid} (sha256 {sha256(a.grid)})",
        "interpolation": "TPXO land filled from nearest wet cell; bilinear in "
                         "lon/lat on real and imaginary parts of h and of the "
                         "transports u*dep, v*dep; velocities = transport / model h",
        "history": f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ} "
                   f"scripts/make_tide_file.py (moana {git_version()})",
    }
    enc = {k: {"_FillValue": None} for k in list(ds.data_vars) + ["tide_period"]}
    enc["tide_name"]["char_dim_name"] = "namelen"
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out, format="NETCDF3_64BIT", encoding=enc)

    # Diagnostics.
    print(f"zero phase {start:%Y-%m-%d}, nodal f, u at {nodal:%Y-%m-%d %H:%M}")
    print(" con   period_h      f  V0+u_deg  max_Eamp_m  max_Cmax_m/s")
    for k, c in enumerate(cons):
        print(f" {c:4s} {period[k]:10.5f} {f[k]:6.4f} {np.degrees(v0u[k]) % 360:9.3f}"
              f" {fields['tide_Eamp'][k][ocean].max():11.3f}"
              f" {fields['tide_Cmax'][k][ocean].max():13.3f}")
    pts = np.column_stack([lat_r.ravel(), lon_r.ravel()])
    axes = (tpxo.lat.values, tpxo.lon.values)
    wetness = RegularGridInterpolator(axes, wet.astype(float))(pts).reshape(lat_r.shape)
    coast = wetness < 1 - 1e-6  # a TPXO land cell among the four used
    print(f"wet model cells using filled TPXO land values: "
          f"{int((coast & ocean).sum())} of {int(ocean.sum())}")
    dep = RegularGridInterpolator(axes, np.where(wet, tpxo.dep.values, 0.0))(
        pts).reshape(lat_r.shape)
    edge = np.zeros_like(ocean)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    edge &= ocean & ~coast
    r = dep[edge] / grd.h.values[edge]
    print(f"open-boundary wet cells: {int(edge.sum())}; TPXO depth / model h "
          f"from {r.min():.2f} to {r.max():.2f} (median {np.median(r):.2f})")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
