#!/usr/bin/env python
"""Figures of the ROMS-ready initial condition (from scripts/make_ic.py).

Usage (in the moana_python environment):

    python misc_scripts/plot_ic.py

Writes concept_figures/ic_<var>_<DATE>.png for temp, salt, u and v.

Each figure has three panels:
  left    the top s-level
  middle  the bottom s-level
  right   a west-east section along the middle row of the grid, depth from the s-levels at rest
          (Vtransform 2, zeta = 0, as in make_ic.py)

The IC files have no coordinates, so lon, lat, h and mask come from the grid file.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

REPO = Path(__file__).resolve().parents[1]
GRID = Path("/projects/f_omg_1/moa/moana/moana_grid_N50.nc")
IC_DIR = Path("/projects/f_omg_1/moa/moana/oceanum_input/initial_cond/roms_ready")
DATE = "2026-01-01"

INK = "#0b0b0b"
INK2 = "#52514e"
LAND = "#bdb8ad"
# ROMS variable: (point type, colormap, units)
VARS = {
    "temp": ("rho", "OrRd", "°C"),
    "salt": ("rho", "Blues", "PSU"),
    "u": ("u", "RdBu_r", "m/s"),
    "v": ("v", "RdBu_r", "m/s"),
}


def at_point(f, pt):
    """A rho-point field (e.g. h) moved to u- or v-points by averaging neighbours."""
    if pt == "u":
        return 0.5 * (f[:, :-1] + f[:, 1:])
    if pt == "v":
        return 0.5 * (f[:-1] + f[1:])
    return f


def z_levels(g, h):
    """Depth (m, negative) of the s-levels at rest, Vtransform 2: (s_rho, eta, xi)."""
    s = g.s_rho.values[:, None, None]
    C = g.Cs_r.values[:, None, None]
    hc = float(g.hc)
    return h * (hc * s + h * C) / (hc + h)


def plot_var(var, g):
    pt, cmap, units = VARS[var]
    data = xr.open_dataset(IC_DIR / f"ic_{var}_{DATE}.nc")[var].isel(ocean_time=0).values   # (s_rho, eta, xi)
    lon = g[f"lon_{pt}"].values % 360
    lat = g[f"lat_{pt}"].values
    ocean = g[f"mask_{pt}"].values == 1
    h = at_point(g.h.values, pt)
    data = np.where(ocean, data, np.nan)                 # land is not used by ROMS

    # colour limits from the ocean values; u and v are centred on 0
    lo, hi = np.nanpercentile(data, [1, 99])
    if cmap == "RdBu_r":
        hi = max(abs(lo), abs(hi))
        lo = -hi

    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5), layout="constrained",
                             gridspec_kw={"width_ratios": [1, 1, 1.3]})
    for ax, k, name in ((axes[0], -1, "top s-level"), (axes[1], 0, "bottom s-level")):
        ax.set_facecolor(LAND)
        mesh = ax.pcolormesh(lon, lat, data[k], cmap=cmap, vmin=lo, vmax=hi, shading="nearest")
        ax.set_aspect(1 / np.cos(np.deg2rad(41)))
        ax.set_title(f"{var}, {name}", loc="left", color=INK)
        ax.set_xlabel("longitude (°E)")

    axes[0].set_ylabel("latitude (°)")

    # section along the middle row
    j = lat.shape[0] // 2
    axes[0].axhline(lat[j].mean(), color=INK, linewidth=0.8, linestyle="--")
    z = z_levels(g, h)[:, j, :]
    x = np.broadcast_to(lon[j], z.shape)
    ax = axes[2]
    ax.set_facecolor(LAND)
    ax.pcolormesh(x, z, data[:, j, :], cmap=cmap, vmin=lo, vmax=hi, shading="gouraud")
    ax.set_title(f"{var}, section at {lat[j].mean():.1f}° (dashed line, left)", loc="left", color=INK)
    ax.set_xlabel("longitude (°E)")
    ax.set_ylabel("depth (m)")

    fig.colorbar(mesh, ax=axes, shrink=0.8, label=f"{var} ({units})")
    wet = data[:, ocean]
    fig.text(0.01, 0.0,
             f"file: ic_{var}_{DATE}.nc   ocean min {np.nanmin(wet):.3f}  max {np.nanmax(wet):.3f}   "
             f"NaN at ocean points: {np.isnan(wet).sum()}   colour range: 1st to 99th percentile",
             fontsize=8, color=INK2)

    out = REPO / "concept_figures" / f"ic_{var}_{DATE}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}   min {np.nanmin(wet):.3f}  max {np.nanmax(wet):.3f}  NaN at ocean points {np.isnan(wet).sum()}")


def main():
    g = xr.open_dataset(GRID)
    for var in VARS:
        plot_var(var, g)


if __name__ == "__main__":
    main()
