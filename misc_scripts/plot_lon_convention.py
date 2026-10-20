#!/usr/bin/env python
"""Concept figure: why the CMEMS download stops at 180 deg.

Usage (in the moana_python environment, see env/moana_python.yml):

    conda activate moana_python
    python misc_scripts/plot_lon_convention.py
    python misc_scripts/plot_lon_convention.py --grid GRID.nc --raw RAW.nc --out some/folder

lon_convention.png goes to --out, default concept_figures/.

The problem in one line: scripts/download_input.py asks DataMesh for the box
lon 160.5 .. 185.5 (0..360 convention, so the box does not split at 180).
CMEMS stores longitude as -180 .. 180, so the values 180 .. 185.5 do not
exist on its axis. They are stored as -180 .. -174.5, at the other end of
the array. The query keeps only 160.5 .. 180, and the east part of the
Moana grid has no data.

Panels:
  a  the world with CMEMS labels (-180 .. 180); the seam is at 180 (date line)
  b  the same world with 0 .. 360 labels; the seam is at 0 (Greenwich)
  c  the longitude axis as a number line: what we asked for, what we got
  d  the Moana region: surface temperature from the downloaded file, the
     Moana grid, the requested box, and the strip with no data

Every number on the figure is read from the grid file and the raw file.
"""

import argparse
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib import patheffects
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[1]
GRID = Path("/projects/f_omg_1/moa/moana/grd_moana5km.nc")
RAW = Path("/projects/f_omg_1/moa/moana/oceanum_input/initial_cond/ic_thetao_raw_2025-01-01.nc")

INK = "#0b0b0b"
INK2 = "#52514e"
LAND = "#bdb8ad"
GOT = "#2a78d6"     # dataviz slot 1: data we have
MISS = "#eb6834"    # dataviz slot 2: data we asked for but did not get
GRIDC = "#1baf7a"   # dataviz slot 3: Moana grid outline
HALO = [patheffects.withStroke(linewidth=2.5, foreground="white")]
PAD = 0.5           # same pad as bbox_from_grid() in scripts/download_input.py
PC = ccrs.PlateCarree()


def lon_cmems(x):
    """Any longitude -> CMEMS convention (-180 .. 180)."""
    return (x + 180) % 360 - 180


def lon_360(x):
    """Any longitude -> 0 .. 360 convention."""
    return x % 360


def deg(x):
    return f"{x:g}".replace("-", "−")


def world(ax, central, ticks, labeller, title):
    ax.set_global()
    ax.add_feature(cfeature.LAND, facecolor=LAND, edgecolor="none")
    ax.coastlines(linewidth=0.4, color=INK2)
    ax.set_xticks(ticks, crs=PC)
    ax.set_xticklabels([labeller(t) for t in ticks], fontsize=8, color=INK2)
    ax.set_yticks([-60, -30, 0, 30, 60], crs=PC)
    ax.set_yticklabels(["60S", "30S", "EQ", "30N", "60N"], fontsize=8, color=INK2)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    for x, name in ((0, " 0° Greenwich (London) "), (180, " 180° date line ")):
        # A line on the map edge gets its label on the inner side.
        on_right_edge = lon_cmems(x - central) == -180 and x != 0
        ax.plot([x, x], [-90, 90], transform=PC, color=INK, lw=1, ls=(0, (4, 2)))
        ax.text(x - 0.01 if on_right_edge else x, 80, name, transform=PC, fontsize=8,
                color=INK, ha="right" if on_right_edge else "left", va="top",
                path_effects=HALO)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--grid", type=Path, default=GRID)
    ap.add_argument("--raw", type=Path, default=RAW)
    ap.add_argument("--out", type=Path, default=REPO / "concept_figures")
    a = ap.parse_args()

    g = xr.open_dataset(a.grid)
    glon = g["lon_rho"].values
    glon = np.where(glon >= 0, glon, glon + 360)
    glat = g["lat_rho"].values
    ocean = g["mask_rho"].values == 1

    # The box that scripts/download_input.py sends to DataMesh.
    bx0, by0 = glon.min() - PAD, glat.min() - PAD
    bx1, by1 = glon.max() + PAD, glat.max() + PAD

    raw = xr.open_dataset(a.raw)
    rlon = raw["longitude"].values
    rlat = raw["latitude"].values
    sst = raw["thetao"].isel(time=0).sel(elevation=raw["elevation"].max())
    got0, got1 = float(rlon.min()), float(rlon.max())

    no_data = glon > got1
    frac_ocean = (no_data & ocean).sum() / ocean.sum()

    fig = plt.figure(figsize=(13, 13), facecolor="white")
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 0.55, 1.5], hspace=0.2, wspace=0.08)

    # ---- a, b: the two conventions on the world map
    ta = [-180, -120, -60, 0, 60, 120, 180]
    axa = fig.add_subplot(gs[0, 0], projection=ccrs.PlateCarree(central_longitude=0))
    world(axa, 0, ta, deg, "a  CMEMS convention: −180 → 180.  Map edge = 180 (date line)")
    tb = [0, 60, 120, 180, 240, 300, 359.99]
    axb = fig.add_subplot(gs[0, 1], projection=ccrs.PlateCarree(central_longitude=180))
    world(axb, 180, tb, lambda t: deg(round(t)) if t < 359 else "360",
          "b  0 → 360 convention.  Map edge = 0 (Greenwich)")
    for ax in (axa, axb):
        ax.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, transform=PC,
                               facecolor="none", edgecolor=MISS, lw=1.8))
    axa.text(bx0 - 3, by0, "Moana box is cut\nin two by the edge", transform=PC,
             fontsize=8, color=INK, ha="right", va="bottom", path_effects=HALO)
    axa.text(lon_cmems(bx1) + 3, by0, "← its east part", transform=PC,
             fontsize=8, color=INK, ha="left", va="bottom", path_effects=HALO)
    axb.text(bx1 + 3, by0, "Moana box is\nin one piece", transform=PC, fontsize=8,
             color=INK, ha="left", va="bottom", path_effects=HALO)

    # ---- c: number line
    axc = fig.add_subplot(gs[1, :])
    axc.set_xlim(-200, 200)
    axc.set_ylim(-1.4, 2.4)
    axc.axis("off")
    axc.set_title("c  The CMEMS longitude axis is a line from −180 to 180. "
                  "Our request runs off the right end.",
                  fontsize=10, color=INK, loc="left")
    axc.plot([-180, 180], [0, 0], color=INK, lw=1.2)
    for t in range(-180, 181, 30):
        axc.plot([t, t], [-0.15, 0.15], color=INK, lw=1)
        axc.text(t, -0.35, deg(t), ha="center", va="top", fontsize=8, color=INK2)
    axc.text(-180, -1.0, "first value in the file", ha="center", va="top", fontsize=8, color=INK2)
    axc.text(180, -1.0, "last value in the file", ha="center", va="top", fontsize=8, color=INK2)

    y, h = 0.6, 0.45
    axc.add_patch(Rectangle((got0, y), got1 - got0, h, facecolor=GOT, edgecolor="none"))
    axc.add_patch(Rectangle((180, y), bx1 - 180, h, facecolor="none", edgecolor=MISS,
                            hatch="////", lw=1.2))
    axc.text(got0 - 2, y + h / 2,
             f"asked for {bx0:.1f} → {bx1:.1f}\ngot {got0:.2f} → {got1:.2f}",
             ha="right", va="center", fontsize=8, color=INK)
    axc.text(bx1 + 2, y + h / 2, f"180 → {bx1:.1f}:\nnot on this axis",
             ha="left", va="center", fontsize=8, color=INK)

    # Where those longitudes really are: the far left end.
    w0, w1 = -180.0, lon_cmems(bx1)
    axc.add_patch(Rectangle((w0, y), w1 - w0, h, facecolor="none", edgecolor=MISS,
                            hatch="////", lw=1.2))
    axc.text(w1 + 2, y + h / 2,
             f"the same water is stored here, as {deg(w0)} → {deg(round(w1, 1))}",
             ha="left", va="center", fontsize=8, color=INK)
    xa, xb, ytop = (180 + bx1) / 2, (w0 + w1) / 2, y + h + 0.6
    axc.plot([xa, xa, xb], [y + h, ytop, ytop], color=MISS, lw=1.2)
    axc.annotate("", xy=(xb, y + h), xytext=(xb, ytop),
                 arrowprops=dict(arrowstyle="->", color=MISS, lw=1.2, shrinkA=0, shrinkB=0))
    axc.text(0, ytop + 0.08, "same longitudes, other end of the axis (take away 360)",
             ha="center", va="bottom", fontsize=8, color=INK, path_effects=HALO)

    # ---- d: zoom on the Moana region
    axd = fig.add_subplot(gs[2, :], projection=ccrs.PlateCarree(central_longitude=180))
    axd.set_extent([155, 195, -56, -27], crs=PC)
    pm = axd.pcolormesh(rlon, rlat, sst, transform=PC, cmap="Blues_r", shading="nearest",
                        rasterized=True)
    axd.add_feature(cfeature.LAND, facecolor=LAND, edgecolor="none", zorder=2)
    axd.coastlines(linewidth=0.5, color=INK2, zorder=3)

    axd.add_patch(Rectangle((180, by0), bx1 - 180, by1 - by0, transform=PC,
                            facecolor="none", edgecolor=MISS, hatch="////", lw=0, zorder=4))
    axd.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, transform=PC,
                            facecolor="none", edgecolor=INK, lw=1.2, ls=(0, (4, 2)), zorder=5))
    axd.add_patch(Rectangle((got0, float(rlat.min())), got1 - got0,
                            float(rlat.max() - rlat.min()), transform=PC,
                            facecolor="none", edgecolor=GOT, lw=2, zorder=5))
    edge = lambda v: np.concatenate([v[0], v[:, -1], v[-1, ::-1], v[::-1, 0]])
    axd.plot(edge(glon), edge(glat), transform=PC, color=GRIDC, lw=2, zorder=6)
    axd.plot([180, 180], [-56, -27], transform=PC, color=INK, lw=1, zorder=6)
    axd.text(180.3, -27.6, "180° date line", transform=PC, fontsize=8, color=INK,
             va="top", path_effects=HALO, zorder=7)

    ticks = [160, 170, 180, 190]
    axd.set_xticks(ticks, crs=PC)
    axd.set_xticklabels([f"0–360:  {deg(lon_360(t))}\nCMEMS:  {deg(lon_cmems(t))}"
                         if t != 180 else "0–360:  180\nCMEMS:  180 = −180"
                         for t in ticks], fontsize=8, color=INK2)
    axd.set_yticks([-55, -50, -45, -40, -35, -30], crs=PC)
    axd.set_yticklabels([f"{-v}S" for v in (-55, -50, -45, -40, -35, -30)],
                        fontsize=8, color=INK2)
    axd.set_title(f"d  Surface temperature in the downloaded file ({a.raw.name}).\n"
                  f"    {100 * frac_ocean:.0f}% of Moana ocean points are east of the data.",
                  fontsize=10, color=INK, loc="left")

    handles = [
        plt.Line2D([], [], color=GRIDC, lw=2, label="Moana grid (grd_moana5km.nc)"),
        plt.Line2D([], [], color=INK, lw=1.2, ls=(0, (4, 2)),
                   label=f"box asked for: {bx0:.1f} → {bx1:.1f}"),
        plt.Line2D([], [], color=GOT, lw=2,
                   label=f"data we got: {got0:.2f} → {got1:.2f}"),
        Rectangle((0, 0), 1, 1, facecolor="none", edgecolor=MISS, hatch="////", lw=0,
                  label=f"no data: 180 → {bx1:.1f}\n(the whole east boundary is in it)"),
    ]
    cb = fig.colorbar(pm, ax=axd, shrink=0.75, pad=0.015)
    cb.set_label("surface temperature (°C)", fontsize=8, color=INK2)
    cb.ax.tick_params(labelsize=8, colors=INK2)
    cb.outline.set_visible(False)
    axd.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.16, 1.0), fontsize=8,
               frameon=False)

    a.out.mkdir(parents=True, exist_ok=True)
    out = a.out / "lon_convention.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"wrote {out}")
    print(f"box asked for: {bx0:.3f} .. {bx1:.3f}; data got: {got0:.3f} .. {got1:.3f}")
    print(f"Moana ocean points with no data: {(no_data & ocean).sum()} of {ocean.sum()} "
          f"({100 * frac_ocean:.1f}%)")


if __name__ == "__main__":
    main()
