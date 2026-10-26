#!/usr/bin/env python
"""Figures of the ROMS-ready boundary file (from scripts/make_bry.py).

Usage (in the moana_python environment):

    python misc_scripts/plot_bry.py

Writes concept_figures/bry_<side>.png for each side in the boundary file.

Each figure has two rows (u, v) and two panels per row:
  left   a section along the boundary at the first record, depth from the s-levels at rest
         (Vtransform 2, zeta = 0, as in make_bry.py)
  right  ubar or vbar along the boundary for every record (time on the y axis)

The boundary file has no coordinates, so lon, lat, h and mask come from the grid file.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

REPO = Path(__file__).resolve().parents[1]
GRID = Path("/projects/f_omg_1/moa/moana/moana_grid_N50.nc")
BRY = Path("/projects/f_omg_1/moa/moana/oceanum_input/boundary_cond/roms-ready/nz5km_N50_bry.nc")

INK = "#0b0b0b"
INK2 = "#52514e"
LAND = "#bdb8ad"
EDGE = {"south": np.s_[0, :], "north": np.s_[-1, :], "west": np.s_[:, 0], "east": np.s_[:, -1]}


def at_point(f, pt):
    """A rho-point field (e.g. h) moved to u- or v-points by averaging neighbours."""
    if pt == "u":
        return 0.5 * (f[:, :-1] + f[:, 1:])
    if pt == "v":
        return 0.5 * (f[:-1] + f[1:])
    return f


def z_levels(g, h):
    """Depth (m, negative) of the s-levels at rest, Vtransform 2: (s_rho, points)."""
    s = g.s_rho.values[:, None]
    C = g.Cs_r.values[:, None]
    hc = float(g.hc)
    return h * (hc * s + h * C) / (hc + h)


def plot_side(side, g, bry):
    times = pd.DatetimeIndex(bry.bry_time.values)
    along = "longitude (°E)" if side in ("south", "north") else "latitude (°)"
    fig, axes = plt.subplots(2, 2, figsize=(15, 8), layout="constrained",
                             gridspec_kw={"width_ratios": [1.3, 1]})

    for row, var in enumerate(("u", "v")):
        x = (g[f"lon_{var}"].values % 360 if side in ("south", "north") else g[f"lat_{var}"].values)[EDGE[side]]
        ocean = g[f"mask_{var}"].values[EDGE[side]] == 1
        h = at_point(g.h.values, var)[EDGE[side]]
        sec = np.where(ocean, bry[f"{var}_{side}"].isel(bry_time=0).values, np.nan)   # (s_rho, points)
        bar = np.where(ocean, bry[f"{var}bar_{side}"].values, np.nan)                   # (time, points)

        # colour limits from the ocean values, centred on 0
        hi = np.nanpercentile(abs(bry[f"{var}_{side}"].values[..., ocean]), 99)

        ax = axes[row, 0]
        ax.set_facecolor(LAND)
        z = z_levels(g, h)
        mesh = ax.pcolormesh(np.broadcast_to(x, z.shape), z, sec, cmap="RdBu_r",
                             vmin=-hi, vmax=hi, shading="gouraud")
        ax.set_title(f"{var}_{side}, {times[0]:%Y-%m-%d %H:%M}", loc="left", color=INK)
        ax.set_xlabel(along)
        ax.set_ylabel("depth (m)")
        fig.colorbar(mesh, ax=ax, label=f"{var} (m/s)")

        ax = axes[row, 1]
        ax.set_facecolor(LAND)
        hb = np.nanpercentile(abs(bar), 99)
        mesh = ax.pcolormesh(x, times, bar, cmap="RdBu_r", vmin=-hb, vmax=hb, shading="nearest")
        ax.set_title(f"{var}bar_{side}, all {len(times)} records", loc="left", color=INK)
        ax.set_xlabel(along)
        ax.yaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%m-%d %H:%M"))
        fig.colorbar(mesh, ax=ax, label=f"{var}bar (m/s)")

    n_nan = sum(int(bry[v].isnull().sum()) for v in bry.data_vars if v.endswith(side))
    fig.text(0.01, -0.02,
             f"file: {BRY.name}   {times[0]} to {times[-1]}   NaN in {side} variables: {n_nan}   "
             f"colour range: 99th percentile of |value| at ocean points   grey: land",
             fontsize=8, color=INK2)

    out = REPO / "concept_figures" / f"bry_{side}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    g = xr.open_dataset(GRID)
    bry = xr.open_dataset(BRY)
    for side in EDGE:
        if f"u_{side}" in bry:
            plot_side(side, g, bry)


if __name__ == "__main__":
    main()
