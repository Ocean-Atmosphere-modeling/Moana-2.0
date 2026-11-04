#!/usr/bin/env python
"""Figure: what is known, assumed and risky about the Moana nudging map.

Usage (in the moana_python environment, see env/moana_python.yml):

    conda activate moana_python
    python Apps/moana/python_scripts/plot_nudging.py
    python Apps/moana/python_scripts/plot_nudging.py GRID.nc --out some/folder

The published run (hindcast v2.2) relaxes the interior toward GLORYS with a
nudging-coefficient file, nz5km_nudg_N50.nc, that is not in the published
archive. Its output records only the file name and the maximum rates.
moana_nudging.pdf and moana_nudging.png go to --out (default
Apps/moana/Figures).

Panels:
  a  published run: interior shape unknown; relaxation at the open edges
  b  paper's description (1/day at the boundary to 0 at ~200 km), drawn
     with a linear taper; the shape is an assumption
  c  ROMS analytic default (ana_nudgcoef.h): uniform 1/day everywhere
  d  the grid file's viscosity sponge, switched off in v2.2
  e  nudging rate against distance from the western edge along 40 S
  f  sponge factors along the same line
"""

import argparse
from pathlib import Path

import cmocean
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize

from plot_grid import (APP, INK, INK2, LAND, MM, axes_mm, lat_label,
                       load_grid, merc, panel_label, set_lat_ticks,
                       set_lon_ticks)

# Settings of the published run, read from the global attributes and scalar
# variables of hindcast v2.2 output (THREDDS moana/NZB/moana_backbone_v2.2/
# avg/nz5km_avg_201801.nc; same in nz5km_avg_201906.nc):
#   NLM_LBC: u, v, temp, salt RadNud on WEST SOUTH EAST NORTH
#   Tnudg = M3nudg = 1/day; LnudgeM3CLM = LnudgeTCLM = T
#   M3obc_in = Tobc_in = 10/day, M3obc_out = Tobc_out = 1/day (OBCFAC = 10)
#   LuvSponge = 0, LtracerSponge = 0 0
#   nud_file: nz5km_nudg_N50.nc (not in Zenodo 10.5281/zenodo.6484908)
NUDG_MAX = 1.0       # 1/day
OBC_IN, OBC_OUT = 10.0, 1.0   # 1/day, open-boundary relaxation
TAPER_KM = 200.0     # paper section 2.1: "decreasing ... to 0 at ~200 km"
PROFILE_LAT = -40.0
PROFILE_KM = 420.0

FIG_W, FIG_H = 180, 128  # mm

# Categorical slots 1-3 of the dataviz reference palette, in fixed order
# (validated all-pairs, light mode). Slot 3 is below 3:1 contrast on white,
# so every use carries a visible label.
SLOT1, SLOT2, SLOT3 = "#2a78d6", "#eb6834", "#1baf7a"
EDGE = SLOT3  # the open-edge relaxation, same colour in panels a and e


def edge_distance(g):
    """Distance (km) from each rho-point to the nearest open edge, summed
    along grid lines (the grid is orthogonal, angle ~ 0)."""
    dx, dy = 1e-3 / g["pm"], 1e-3 / g["pn"]
    west = np.cumsum(dx, axis=1) - dx[:, :1]
    east = np.cumsum(dx[:, ::-1], axis=1)[:, ::-1] - dx[:, -1:]
    south = np.cumsum(dy, axis=0) - dy[:1, :]
    north = np.cumsum(dy[::-1, :], axis=0)[::-1, :] - dy[-1:, :]
    return np.minimum.reduce([west, east, south, north]), west


def base_map(ax, g, lat_labels):
    """Land, model coastline, ticks; returns the plotting coordinates."""
    xv, yv = g["lon_vert"], g["y_vert"]
    land = np.ma.masked_where(g["ocean"], np.ones_like(g["h"]))
    ax.pcolormesh(xv, yv, land, cmap=mpl.colors.ListedColormap([LAND]),
                  rasterized=True, zorder=2)
    ax.contour(g["lon_rho"], g["y_rho"], g["mask_rho"], levels=[0.5],
               colors=INK, linewidths=0.3, zorder=3)
    ax.set_xlim(xv.min(), xv.max())
    ax.set_ylim(yv.min(), yv.max())
    ax.set_aspect("equal")
    set_lon_ticks(ax, [165, 175])
    set_lat_ticks(ax, [-50, -40], labels=lat_labels)
    return xv, yv


def title(ax, text):
    ax.text(0.0, 1.02, text, transform=ax.transAxes, fontsize=6.5,
            ha="left", va="bottom")


def note(ax, x, y, text, **kw):
    kw = {"fontsize": 5.5, "ha": "center", "va": "center", "color": INK,
          "linespacing": 1.1, "zorder": 6,
          "bbox": dict(boxstyle="round,pad=0.25", fc="white", ec="none",
                       alpha=0.85), **kw}
    ax.text(x, y, text, transform=ax.transAxes, **kw)


def edge_ring(ax, g, **kw):
    xv, yv = g["lon_vert"], g["y_vert"]
    ring_x = np.r_[xv[0, :], xv[:, -1], xv[-1, ::-1], xv[::-1, 0]]
    ring_y = np.r_[yv[0, :], yv[:, -1], yv[-1, ::-1], yv[::-1, 0]]
    ax.plot(ring_x, ring_y, clip_on=False, zorder=5, **kw)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("grid", nargs="?", type=Path,
                   default=APP / "Input" / "moana_grid.nc",
                   help="ROMS grid file (default: %(default)s)")
    p.add_argument("--out", type=Path, default=APP / "Figures",
                   help="output folder (default: %(default)s)")
    args = p.parse_args()

    g = load_grid(args.grid)
    dist, west = edge_distance(g)
    ocean = g["ocean"]
    taper = np.clip(1.0 - dist / TAPER_KM, 0.0, None) * NUDG_MAX
    uniform = np.full_like(dist, NUDG_MAX)
    rate_cmap, rate_norm = cmocean.cm.amp, Normalize(0, NUDG_MAX)
    sponge_cmap, sponge_norm = cmocean.cm.tempo, Normalize(1, 10)

    fig = plt.figure(figsize=(FIG_W * MM, FIG_H * MM))
    w, gap, bottom, left = 37, 5, 74, 11
    h = w * (g["y_vert"].max() - g["y_vert"].min()) / (
        g["lon_vert"].max() - g["lon_vert"].min())
    axs = [axes_mm(fig, left + k * (w + gap), bottom, w, h) for k in range(4)]
    ax_a, ax_b, ax_c, ax_d = axs

    # a: published run.
    base_map(ax_a, g, lat_labels=True)
    mpl.rcParams["hatch.color"] = INK2
    mpl.rcParams["hatch.linewidth"] = 0.3
    ax_a.contourf(g["lon_rho"], g["y_rho"], ocean.astype(float),
                  levels=[0.5, 1.5], colors=["#efeeea"], hatches=["////"],
                  zorder=1)
    edge_ring(ax_a, g, color=EDGE, lw=1.8)
    note(ax_a, 0.5, 0.8, "Interior nudging map\n(nz5km_nudg_N50.nc)\n"
         "missing: shape unknown\nmax rate 1 d$^{-1}$")
    note(ax_a, 0.5, 0.1, f"edge: inflow {OBC_IN:g} d$^{{-1}}$ (≈2.4 h)\n"
         f"outflow {OBC_OUT:g} d$^{{-1}}$", color=INK)
    title(ax_a, "Published run (v2.2)")

    # b: paper's description, linear taper assumed.
    xv, yv = base_map(ax_b, g, lat_labels=False)
    pm_rate = ax_b.pcolormesh(xv, yv, np.ma.masked_where(~ocean, taper),
                              cmap=rate_cmap, norm=rate_norm,
                              rasterized=True, zorder=1)
    ax_b.contour(g["lon_rho"], g["y_rho"], dist, levels=[TAPER_KM],
                 colors=INK, linewidths=0.6, linestyles=[(0, (3, 1.5))],
                 zorder=4)
    note(ax_b, 0.5, 0.5, f"{TAPER_KM:g} km\n(linear taper\nassumed)")
    title(ax_b, "Paper: 1 → 0 d$^{-1}$ over ≈200 km")

    # c: ROMS analytic default.
    base_map(ax_c, g, lat_labels=False)
    ax_c.pcolormesh(xv, yv, np.ma.masked_where(~ocean, uniform),
                    cmap=rate_cmap, norm=rate_norm, rasterized=True, zorder=1)
    ax_c.contour(g["lon_rho"], g["y_rho"], dist, levels=[TAPER_KM],
                 colors="white", linewidths=0.6,
                 linestyles=[(0, (3, 1.5))], zorder=4)
    note(ax_c, 0.5, 0.5, "Whole domain relaxed\nto GLORYS every day\n"
         "(ana_nudgcoef.h default)")
    title(ax_c, "Trap: ROMS analytic default")

    # d: grid-file sponge, not used by v2.2.
    base_map(ax_d, g, lat_labels=False)
    pm_sp = ax_d.pcolormesh(xv, yv,
                            np.ma.masked_where(~ocean, g["visc_factor"]),
                            cmap=sponge_cmap, norm=sponge_norm,
                            rasterized=True, zorder=1)
    n_sp = int((g["visc_factor"][g["visc_factor"].shape[0] // 2] > 1)
               .argmin())
    note(ax_d, 0.5, 0.5, f"{n_sp}-cell sponge in grid file\n"
         "LuvSponge = 0: not used\nby the published run")
    title(ax_d, "Grid-file viscosity sponge")

    # Colour bars under b-c (shared) and d.
    cb_y = bottom - 9.5
    cax = axes_mm(fig, left + (w + gap), cb_y, 2 * w + gap, 1.8)
    cb = fig.colorbar(pm_rate, cax=cax, orientation="horizontal",
                      ticks=[0, 0.25, 0.5, 0.75, 1])
    cb.set_label("Nudging rate toward GLORYS (d$^{-1}$)", fontsize=6)
    cax = axes_mm(fig, left + 3 * (w + gap), cb_y, w, 1.8)
    cb2 = fig.colorbar(pm_sp, cax=cax, orientation="horizontal",
                       ticks=[1, 4, 7, 10])
    cb2.set_label("Viscosity factor (×)", fontsize=6)
    for c in (cb, cb2):
        c.ax.tick_params(labelsize=5.5, length=2, width=0.4)
        c.outline.set_linewidth(0.4)

    # Profile line on the maps.
    j = int(np.argmin(np.abs(g["lat_rho"][:, 0] - PROFILE_LAT)))
    i_end = int(np.searchsorted(west[j], PROFILE_KM))
    for ax in axs:
        ax.plot(g["lon_rho"][j, :i_end], g["y_rho"][j, :i_end], color=INK,
                lw=1.0, zorder=5)
    ax_a.text(g["lon_rho"][j, i_end // 2], g["y_rho"][j, i_end] - 0.5, "e, f",
              fontsize=6, fontweight="bold", ha="center", va="top", zorder=6)

    # e: nudging rate along the profile.
    km = west[j, :i_end]
    sea = ocean[j, :i_end]
    ax_e = axes_mm(fig, left + 8, 12, 2 * w + gap - 8, 34)
    ax_e.plot(km, np.where(sea, taper[j, :i_end], np.nan), color=SLOT1,
              lw=1.4, label="paper, linear taper (assumed shape)")
    ax_e.plot(km, np.where(sea, uniform[j, :i_end], np.nan), color=SLOT2,
              lw=1.4, ls=(0, (3, 1.5)), label="ROMS analytic default")
    ax_e.text(330, 0.95, "ROMS analytic default", fontsize=6, color=INK2,
              ha="center", va="top")
    ax_e.text(120, 0.55, "paper, linear taper\n(assumed shape)", fontsize=6,
              color=INK, ha="left", va="center")
    ax_e.plot([0], [OBC_OUT], "o", ms=4, color=EDGE, mec="white", mew=0.8,
              clip_on=False, zorder=5, label="edge cell only")
    ax_e.annotate("", xy=(0, 1.25), xytext=(0, 1.06),
                  arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=1.0),
                  annotation_clip=False)
    ax_e.text(10, 1.155, f"edge cell only: inflow {OBC_IN:g} d$^{{-1}}$ "
              f"(↑ off scale), outflow {OBC_OUT:g} d$^{{-1}}$ (●)",
              fontsize=5.5, color=INK2, ha="left", va="center")
    ax_e.legend(loc="center right", bbox_to_anchor=(1.0, 0.6), frameon=False,
                fontsize=5.5, handlelength=2.5)
    ax_e.set_xlim(0, PROFILE_KM)
    ax_e.set_ylim(0, 1.25)
    ax_e.set_xlabel(f"Distance from western edge along "
                    f"{lat_label(PROFILE_LAT)} (km)")
    ax_e.set_ylabel("Nudging rate (d$^{-1}$)")
    title(ax_e, "Rate along the profile")

    # f: sponge factors along the profile.
    ax_f = axes_mm(fig, left + 2 * (w + gap) + 8, 12, 2 * w + gap - 8, 34)
    ax_f.plot(km, g["visc_factor"][j, :i_end], color=SLOT1, lw=1.4,
              label="viscosity")
    ax_f.plot(km, g["diff_factor"][j, :i_end], color=SLOT2, lw=1.4,
              ls=(0, (3, 1.5)), label="diffusivity")
    for fac, va in ((g["visc_factor"], "top"), (g["diff_factor"], "bottom")):
        ax_f.text(6, fac[j, 0] + (-0.4 if va == "top" else 0.3),
                  f"×{fac[j, 0]:.0f}", fontsize=6, color=INK, ha="left", va=va)
    ax_f.legend(loc="center", bbox_to_anchor=(0.5, 0.62), frameon=False,
                fontsize=6, handlelength=2.5)
    ax_f.axvline(km[n_sp], color=INK2, lw=0.4)
    ax_f.text(km[n_sp] + 6, 6.5, f"{n_sp} cells ≈ {km[n_sp]:.0f} km",
              fontsize=6, ha="left", va="center")
    ax_f.text(0.98, 0.9, "not applied in v2.2\n(LuvSponge = LtracerSponge = 0)",
              transform=ax_f.transAxes, fontsize=5.5, ha="right", va="top",
              color=INK2)
    ax_f.set_xlim(0, PROFILE_KM)
    ax_f.set_ylim(0, 16)
    ax_f.set_xlabel(f"Distance from western edge along "
                    f"{lat_label(PROFILE_LAT)} (km)")
    ax_f.set_ylabel("Sponge factor (×)")
    title(ax_f, "Grid-file sponge along the profile")

    for ax in (ax_e, ax_f):
        ax.grid(color="#d9d8d4", lw=0.4)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    for ax, letter in zip(axs + [ax_e, ax_f], "abcdef"):
        panel_label(ax, letter, x=-0.05 if ax in axs else -0.12, y=1.02)

    args.out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = args.out / f"moana_nudging.{ext}"
        fig.savefig(out, metadata={"Title": "Moana nudging map"})
        print(f"wrote   {out}")
    print(f"taper reaches 0 at {TAPER_KM:g} km = "
          f"{int(np.searchsorted(west[j], TAPER_KM))} cells along "
          f"{lat_label(PROFILE_LAT)}; sponge {n_sp} cells = {km[n_sp]:.0f} km")


if __name__ == "__main__":
    main()
