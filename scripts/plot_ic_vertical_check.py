#!/usr/bin/env python
"""Check the vertical interpolation in the ROMS initial condition (scripts/make_ic.py).

Question: do features in the IC sections that follow the bathymetry come from CMEMS,
from the vertical interpolation (CMEMS levels -> s-levels), or from the plotting?

Usage (in the moana_python environment):

    python scripts/plot_ic_vertical_check.py

Inputs, for each of temp, salt, u, v
  IC_DIR/ic_<var>_<DATE>.nc            the IC, on the s-levels
  IC_DIR/ic_zlevels_<var>_<DATE>.nc    the same field after the horizontal interpolation only, still on
                                       the CMEMS levels (elevation, negative-up), with lon, lat, h, mask
  GRID                                 z_rho (xroms, Vtransform 2, zeta = 0, as in make_ic.py)

Two sections: west-east along the middle row of the grid (the section in plot_ic.py) and
south-north along the middle column.

Writes concept_figures/ic_vertical_check/
  section_<line>_<var>_<DATE>.png    columns: CMEMS levels | s-levels; rows: full depth | top 500 m
  profiles_<line>_<DATE>.png         4 points per variable on that line: CMEMS dots, s-levels line + dots
and prints, per variable over the whole grid, the NaN count at ocean points and the max |ROMS - CMEMS|
at s-levels that lie within 1 m of a CMEMS level.

Shading: the s-level panels use shading="gouraud". With "nearest" (matplotlib's default when
X, Y and C have the same shape) each s-level cell is flat-coloured and follows the s-surfaces,
which follow the bathymetry, so the figure draws bands with the shape of the bathymetry.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import xroms

REPO = Path(__file__).resolve().parents[1]
GRID = "/projects/f_omg_1/moa/moana/moana_grid_N50.nc"
IC_DIR = Path("/projects/f_omg_1/moa/moana/oceanum_input/initial_cond/roms_ready")
DATE = "2026-01-01"
OUT = REPO / "concept_figures" / "ic_vertical_check"
VTRANSFORM = 2
TOP = 500.0                     # m, depth of the zoom row
NEAR = 1.0                      # m, an s-level this close to a CMEMS level is compared with it

POINT = {"temp": "rho", "salt": "rho", "u": "u", "v": "v"}
UNITS = {"temp": "°C", "salt": "psu", "u": "m/s", "v": "m/s"}
CMAP = {"temp": "RdYlBu_r", "salt": "viridis", "u": "RdBu_r", "v": "RdBu_r"}
LINES = ["we", "sn"]            # west-east along the middle row, south-north along the middle column

INK = "#0b0b0b"
INK2 = "#52514e"
LAND = "#bdb8ad"
CMEMS_C = "#eb6834"
ROMS_C = "#2a78d6"


# %% 1. Inputs
def z_rho():
    """z_rho (s_rho, eta, xi) at each point type, from xroms (zeta = 0)."""
    g = xr.open_dataset(GRID)
    g["zeta"] = xr.zeros_like(g.h)
    g, _ = xroms.roms_dataset(g, Vtransform=VTRANSFORM)
    z = {"rho": g.z_rho, "u": g.z_rho_u, "v": g.z_rho_v}
    return {pt: da.transpose("s_rho", ...).values for pt, da in z.items()}


def load(var, z):
    """The whole 3-D field of one variable, as numpy arrays."""
    zl = xr.open_dataset(IC_DIR / f"ic_zlevels_{var}_{DATE}.nc")
    ic = xr.open_dataset(IC_DIR / f"ic_{var}_{DATE}.nc")[var].isel(ocean_time=0)
    d = {k: zl[k].values for k in ("lon", "lat", "h", "mask")}
    d["ocean"] = d["mask"] == 1
    d["elev"] = zl.elevation.values
    d["cm"] = zl[var].transpose("elevation", ...).values                  # (elevation, eta, xi)
    d["z"] = z[POINT[var]]                                                 # (s_rho, eta, xi)
    d["roms"] = np.where(d["ocean"], ic.transpose("s_rho", ...).values, np.nan)
    assert d["z"].shape == d["roms"].shape, f"{var}: grid and IC file differ"
    return d


def line(d, name):
    """One section through the 3-D field: the middle row (we) or the middle column (sn)."""
    ny, nx = d["h"].shape
    cut = np.s_[ny // 2, :] if name == "we" else np.s_[:, nx // 2]
    s = {k: d[k][cut] for k in ("lon", "lat", "h", "ocean")}
    s.update({k: d[k][(slice(None),) + cut] for k in ("cm", "z", "roms")})
    s["x"] = s["lon"] if name == "we" else s["lat"]
    s["elev"] = d["elev"]
    s["where"] = (f"west-east at {s['lat'].mean():.2f}°N" if name == "we"
                  else f"south-north at {s['lon'].mean():.2f}°E")
    return s


# %% 2. Figures
def limits(var, roms):
    """1st-99th percentile of the ROMS ocean values; centred on 0 for velocities."""
    lo, hi = np.nanpercentile(roms, [1, 99])
    if var in ("u", "v"):
        hi = max(abs(lo), abs(hi))
        lo = -hi
    return lo, hi


def seafloor_and_land(ax, s, bottom):
    """Grey from -h downward, and grey land columns."""
    ax.fill_between(s["x"], -s["h"], bottom, color=LAND, linewidth=0, zorder=3)
    dx = np.median(np.diff(s["x"]))
    land = ~s["ocean"]
    ax.bar(s["x"][land], bottom, width=dx, color=LAND, linewidth=0, zorder=3)


def section(name, var, s):
    cm = np.where(s["ocean"] & (s["elev"][:, None] >= -s["h"]), s["cm"], np.nan)
    vmin, vmax = limits(var, s["roms"])
    bottom = -1.02 * s["h"][s["ocean"]].max()

    fig, axes = plt.subplots(2, 2, figsize=(15, 8), sharex=True, layout="constrained")
    for row, ylim in enumerate(((bottom, 0), (-TOP, 0))):
        ax = axes[row, 0]
        mesh = ax.pcolormesh(s["x"], s["elev"], cm, cmap=CMAP[var], vmin=vmin, vmax=vmax, shading="nearest")
        ax = axes[row, 1]
        ax.pcolormesh(np.broadcast_to(s["x"], s["z"].shape), s["z"], s["roms"], cmap=CMAP[var],
                      vmin=vmin, vmax=vmax, shading="gouraud")
        for ax in axes[row]:
            seafloor_and_land(ax, s, bottom)
            ax.set_ylim(ylim)
            ax.set_ylabel("depth (m)")

    axes[0, 0].set_title(f"CMEMS on its {len(s['elev'])} levels (after the horizontal step)", loc="left", color=INK)
    axes[0, 1].set_title(f"ROMS on {s['z'].shape[0]} s-levels (IC file), gouraud", loc="left", color=INK)
    axes[1, 0].set_title(f"top {TOP:.0f} m", loc="left", color=INK2)
    axes[1, 1].set_title(f"top {TOP:.0f} m", loc="left", color=INK2)
    along = "longitude (°E)" if name == "we" else "latitude (°N)"
    for ax in axes[1]:
        ax.set_xlabel(along)
    fig.colorbar(mesh, ax=axes, label=f"{var} ({UNITS[var]})", shrink=0.8)
    fig.suptitle(f"IC {var}, {DATE}, section {s['where']}", x=0.01, ha="left", color=INK)
    fig.text(0.01, -0.02, f"colour range: 1st-99th percentile of the ROMS ocean values on this section   "
             f"grey: below -h, and land   CMEMS values below -h not drawn", fontsize=8, color=INK2)

    out = OUT / f"section_{name}_{var}_{DATE}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def pick_points(h, ocean):
    """Deepest, shallowest ocean point, and the deeper end of the two steepest steps in h."""
    idx = np.flatnonzero(ocean)
    picks = [("deepest", idx[np.argmax(h[idx])]), ("shallowest", idx[np.argmin(h[idx])])]
    dh = np.abs(np.diff(h))
    dh[~(ocean[:-1] & ocean[1:])] = -1                     # only steps between two ocean points
    for k in np.argsort(dh)[::-1]:
        i = k if h[k] > h[k + 1] else k + 1
        if i not in [p for _, p in picks]:
            picks.append((f"steep |dh| = {dh[k]:.0f} m", i))
        if len(picks) == 4:
            return picks


def profiles(name, sections):
    fig, axes = plt.subplots(len(sections), 4, figsize=(15, 5 * len(sections)), layout="constrained",
                             squeeze=False)
    for row, (var, s) in enumerate(sections.items()):
        for col, (label, i) in enumerate(pick_points(s["h"], s["ocean"])):
            ax = axes[row, col]
            wet = s["elev"] >= -s["h"][i]
            ax.plot(s["cm"][wet, i], s["elev"][wet], "o", color=CMEMS_C, ms=5, label="CMEMS levels")
            ax.plot(s["roms"][:, i], s["z"][:, i], "-", color=ROMS_C, lw=1, label="ROMS s-levels")
            ax.plot(s["roms"][:, i], s["z"][:, i], ".", color=ROMS_C, ms=4)
            ax.axhline(-s["h"][i], color=LAND, lw=3)
            ax.set_ylim(-s["h"][i] * 1.02, 0)
            ax.set_title(f"{var}: {label}\n{s['lon'][i]:.2f}°E {s['lat'][i]:.2f}°N, h = {s['h'][i]:.0f} m",
                         loc="left", fontsize=9, color=INK)
            ax.set_xlabel(f"{var} ({UNITS[var]})")
            if col == 0:
                ax.set_ylabel("depth (m)")
    axes[0, 0].legend(fontsize=8, loc="lower left")
    where = next(iter(sections.values()))["where"]
    fig.suptitle(f"IC profiles, {DATE}, section {where}   (grey line: -h)", x=0.01, ha="left", color=INK)

    out = OUT / f"profiles_{name}_{DATE}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


# %% 3. Numbers, over the whole grid
def compare(d):
    """NaN at ocean points, and max |ROMS - CMEMS| over s-levels within NEAR m of a CMEMS level."""
    wet = d["elev"][:, None, None] >= -d["h"]                              # CMEMS levels above the seafloor
    nan_roms = int(np.isnan(d["roms"][:, d["ocean"]]).sum())
    nan_cm = int(np.isnan(np.where(wet, d["cm"], 0.0)[:, d["ocean"]]).sum())
    n, worst = 0, 0.0
    for k in range(d["z"].shape[0]):
        dist = np.where(wet, np.abs(d["elev"][:, None, None] - d["z"][k]), np.inf)
        j = dist.argmin(axis=0)[None]
        near = (np.take_along_axis(dist, j, 0)[0] <= NEAR) & d["ocean"]
        diff = np.abs(d["roms"][k] - np.take_along_axis(d["cm"], j, 0)[0])[near]
        n += diff.size
        worst = max(worst, diff.max(initial=0.0))
    return nan_roms, nan_cm, n, worst


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    z = z_rho()
    sections = {name: {} for name in LINES}
    rows = []
    for var in POINT:
        d = load(var, z)
        rows.append((var,) + compare(d))
        for name in LINES:
            sections[name][var] = line(d, name)
            section(name, var, sections[name][var])
    for name in LINES:
        profiles(name, sections[name])

    print(f"\n{'var':5s} {'NaN ROMS':>9s} {'NaN CMEMS':>10s} {'pairs <1 m':>11s} {'max |ROMS-CMEMS|':>17s}")
    for var, nr, nc, n, dmax in rows:
        print(f"{var:5s} {nr:9d} {nc:10d} {n:11d} {dmax:17.3g}")


if __name__ == "__main__":
    main()
