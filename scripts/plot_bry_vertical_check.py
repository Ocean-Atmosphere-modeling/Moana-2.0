#!/usr/bin/env python
"""Check the vertical interpolation in the ROMS boundary file (scripts/make_bry.py).

Question: do features in the boundary sections that follow the bathymetry come from CMEMS,
from the vertical interpolation (CMEMS levels -> s-levels), or from the plotting?

Usage (in the moana_python environment):

    python scripts/plot_bry_vertical_check.py                  # newest bry_zlevels_*.nc
    python scripts/plot_bry_vertical_check.py 2026-01-01T00    # bry_zlevels_2026-01-01T00.nc

Inputs
  BRY       the boundary file, on the s-levels
  ZLEVELS   bry_zlevels_<time>.nc from make_bry.py: the same boundary lines after the horizontal
            interpolation only, still on the CMEMS levels (elevation, negative-up), with lon, lat,
            h and mask of each line
  GRID      z_rho on the boundary lines (xroms, Vtransform 2, zeta = 0, as in make_bry.py)

Writes concept_figures/bry_vertical_check/
  section_<side>_<var>_<time>.png         columns: CMEMS levels | s-levels; rows: full depth | top 500 m
  profiles_<side>_<vars>_<time>.png       4 points per side: CMEMS dots, s-levels line + dots
and prints, per side and variable, the NaN count at ocean points and the max |ROMS - CMEMS| at
s-levels that lie within 1 m of a CMEMS level.

Shading: the s-level panels use shading="gouraud". With "nearest" (matplotlib's default when
X, Y and C have the same shape) each s-level cell is flat-coloured and follows the s-surfaces,
which follow the bathymetry, so the figure draws bands with the shape of the bathymetry.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import xroms

REPO = Path(__file__).resolve().parents[1]
GRID = "/projects/f_omg_1/moa/moana/moana_grid_N50.nc"
BRY = Path("/projects/f_omg_1/moa/moana/oceanum_input/boundary_cond/roms-ready/nz5km_N50_bry.nc")
OUT = REPO / "concept_figures" / "bry_vertical_check"
VTRANSFORM = 2
TOP = 500.0                     # m, depth of the zoom row
NEAR = 1.0                      # m, an s-level this close to a CMEMS level is compared with it

POINT = {"temp": "rho", "salt": "rho", "u": "u", "v": "v"}
UNITS = {"temp": "°C", "salt": "psu", "u": "m/s", "v": "m/s"}
CMAP = {"temp": "RdYlBu_r", "salt": "viridis", "u": "RdBu_r", "v": "RdBu_r"}
SIDES = ["south", "north", "west", "east"]

INK = "#0b0b0b"
INK2 = "#52514e"
LAND = "#bdb8ad"
CMEMS_C = "#eb6834"
ROMS_C = "#2a78d6"


# %% 1. Inputs
def z_lines():
    """z_rho (s_rho, line) on each boundary line and point type, from xroms (zeta = 0)."""
    g = xr.open_dataset(GRID)
    g["zeta"] = xr.zeros_like(g.h)
    g, _ = xroms.roms_dataset(g, Vtransform=VTRANSFORM)
    z = {"rho": g.z_rho, "u": g.z_rho_u, "v": g.z_rho_v}
    edge = {"south": np.s_[:, 0, :], "north": np.s_[:, -1, :], "west": np.s_[:, :, 0], "east": np.s_[:, :, -1]}
    return {(side, pt): z[pt].transpose("s_rho", ...).values[edge[side]] for side in SIDES for pt in z}


def line(zl, side, var):
    """Everything about one variable on one side, as numpy arrays."""
    pt = POINT[var]
    d = {k: zl[f"{k}_{pt}_{side}"].values for k in ("lon", "lat", "h", "mask")}
    d["x"] = d["lon"] if side in ("south", "north") else d["lat"]
    d["ocean"] = d["mask"] == 1
    d["elev"] = zl.elevation.values
    d["cm"] = zl[f"{var}_{side}"].transpose("elevation", ...).values          # (elevation, line)
    return d


# %% 2. Figures
def limits(var, roms):
    """1st-99th percentile of the ROMS ocean values; centred on 0 for velocities."""
    lo, hi = np.nanpercentile(roms, [1, 99])
    if var in ("u", "v"):
        hi = max(abs(lo), abs(hi))
        lo = -hi
    return lo, hi


def seafloor_and_land(ax, d, bottom):
    """Grey from -h downward, and grey land columns."""
    ax.fill_between(d["x"], -d["h"], bottom, color=LAND, linewidth=0, zorder=3)
    dx = np.median(np.diff(d["x"]))
    land = ~d["ocean"]
    ax.bar(d["x"][land], bottom, width=dx, color=LAND, linewidth=0, zorder=3)


def section(side, var, d, z, roms, stamp):
    cm = np.where(d["ocean"] & (d["elev"][:, None] >= -d["h"]), d["cm"], np.nan)
    vmin, vmax = limits(var, roms)
    bottom = -1.02 * d["h"][d["ocean"]].max()

    fig, axes = plt.subplots(2, 2, figsize=(15, 8), sharex=True, layout="constrained")
    for row, ylim in enumerate(((bottom, 0), (-TOP, 0))):
        ax = axes[row, 0]
        mesh = ax.pcolormesh(d["x"], d["elev"], cm, cmap=CMAP[var], vmin=vmin, vmax=vmax, shading="nearest")
        ax = axes[row, 1]
        ax.pcolormesh(np.broadcast_to(d["x"], z.shape), z, roms, cmap=CMAP[var], vmin=vmin, vmax=vmax,
                      shading="gouraud")
        for ax in axes[row]:
            seafloor_and_land(ax, d, bottom)
            ax.set_ylim(ylim)
            ax.set_ylabel("depth (m)")

    axes[0, 0].set_title(f"CMEMS on its {len(d['elev'])} levels (after the horizontal step)", loc="left", color=INK)
    axes[0, 1].set_title(f"ROMS on {z.shape[0]} s-levels (boundary file), gouraud", loc="left", color=INK)
    axes[1, 0].set_title(f"top {TOP:.0f} m", loc="left", color=INK2)
    axes[1, 1].set_title(f"top {TOP:.0f} m", loc="left", color=INK2)
    along = "longitude (°E)" if side in ("south", "north") else "latitude (°N)"
    for ax in axes[1]:
        ax.set_xlabel(along)
    fig.colorbar(mesh, ax=axes, label=f"{var} ({UNITS[var]})", shrink=0.8)
    fig.suptitle(f"{var}_{side}, {stamp}", x=0.01, ha="left", color=INK)
    fig.text(0.01, -0.02, f"colour range: 1st-99th percentile of the ROMS ocean values on this side   "
             f"grey: below -h, and land   CMEMS values below -h not drawn", fontsize=8, color=INK2)

    out = OUT / f"section_{side}_{var}_{stamp}.png"
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


def profiles(side, vars_, lines_, z, roms, stamp):
    fig, axes = plt.subplots(len(vars_), 4, figsize=(15, 5 * len(vars_)), layout="constrained", squeeze=False)
    for row, var in enumerate(vars_):
        d, zz = lines_[var], z[var]
        for col, (label, i) in enumerate(pick_points(d["h"], d["ocean"])):
            ax = axes[row, col]
            wet = d["elev"] >= -d["h"][i]
            ax.plot(d["cm"][wet, i], d["elev"][wet], "o", color=CMEMS_C, ms=5, label="CMEMS levels")
            ax.plot(roms[var][:, i], zz[:, i], "-", color=ROMS_C, lw=1, label="ROMS s-levels")
            ax.plot(roms[var][:, i], zz[:, i], ".", color=ROMS_C, ms=4)
            ax.axhline(-d["h"][i], color=LAND, lw=3)
            ax.set_ylim(-d["h"][i] * 1.02, 0)
            ax.set_title(f"{var}: {label}\n{d['lon'][i]:.2f}°E {d['lat'][i]:.2f}°N, h = {d['h'][i]:.0f} m",
                         loc="left", fontsize=9, color=INK)
            ax.set_xlabel(f"{var} ({UNITS[var]})")
            if col == 0:
                ax.set_ylabel("depth (m)")
    axes[0, 0].legend(fontsize=8, loc="lower left")
    fig.suptitle(f"profiles on the {side} boundary, {stamp}   (grey line: -h)", x=0.01, ha="left", color=INK)

    out = OUT / f"profiles_{side}_{'-'.join(vars_)}_{stamp}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


# %% 3. Numbers
def compare(d, z, roms):
    """NaN at ocean points, and max |ROMS - CMEMS| over s-levels within NEAR m of a CMEMS level."""
    nan_roms = int(np.isnan(roms[:, d["ocean"]]).sum())
    wet = d["elev"][:, None] >= -d["h"]
    nan_cm = int(np.isnan(np.where(wet, d["cm"], 0.0)[:, d["ocean"]]).sum())
    diffs = []
    for i in np.flatnonzero(d["ocean"]):
        elev = d["elev"][d["elev"] >= -d["h"][i]]
        cm = d["cm"][d["elev"] >= -d["h"][i], i]
        for k in range(z.shape[0]):
            j = np.argmin(abs(elev - z[k, i]))
            if abs(elev[j] - z[k, i]) <= NEAR:
                diffs.append(abs(roms[k, i] - cm[j]))
    return nan_roms, nan_cm, len(diffs), max(diffs) if diffs else np.nan


def main():
    files = sorted(BRY.parent.glob(f"bry_zlevels_{sys.argv[1] if len(sys.argv) > 1 else '*'}.nc"))
    assert files, f"no bry_zlevels file in {BRY.parent}"
    zl = xr.open_dataset(files[-1])
    stamp = zl.attrs["time"]
    bry = xr.open_dataset(BRY).sel(bry_time=np.datetime64(stamp))
    z_all = z_lines()
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{files[-1].name} and {BRY.name} at {stamp}")

    rows = []
    for side in SIDES:
        vars_ = [v for v in POINT if f"{v}_{side}" in zl]
        if not vars_:
            continue
        lines_, z, roms = {}, {}, {}
        for var in vars_:
            d = line(zl, side, var)
            z[var] = z_all[(side, POINT[var])]
            assert z[var].shape[1] == d["h"].size, f"{var}_{side}: grid and file lines differ"
            roms[var] = np.where(d["ocean"], bry[f"{var}_{side}"].transpose("s_rho", ...).values, np.nan)
            lines_[var] = d
            section(side, var, d, z[var], roms[var], stamp)
            rows.append((side, var) + compare(d, z[var], roms[var]))
        profiles(side, vars_, lines_, z, roms, stamp)

    print(f"\n{'side':6s} {'var':5s} {'NaN ROMS':>9s} {'NaN CMEMS':>10s} {'pairs <1 m':>11s} {'max |ROMS-CMEMS|':>17s}")
    for side, var, nr, nc, n, dmax in rows:
        print(f"{side:6s} {var:5s} {nr:9d} {nc:10d} {n:11d} {dmax:17.3g}")


if __name__ == "__main__":
    main()
