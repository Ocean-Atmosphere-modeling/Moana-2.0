#!/usr/bin/env python
"""Concept figures: what scripts/download_bry.py downloads for each ROMS boundary.

Usage (in the moana_python environment):

    python misc_scripts/plot_bry_strips.py                # uses download_bry.yaml at the repo root
    python misc_scripts/plot_bry_strips.py other.yaml

Writes concept_figures/bry_strip_<side>.png for each side in SIDES.

Each figure has two panels:
  left   the whole Moana grid, the box download_bry.py asks DataMesh for, and the surface
         current speed in the downloaded file (first record)
  right  a zoom on the middle of the edge: the source grid cells and the ROMS rho-, u- and
         v-points that the boundary file needs

The boxes come from boundary_bboxes() and split_at_seam() in scripts/download_bry.py, so the
figure shows exactly what the script asks for. All longitudes are drawn in 0..360.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import yaml
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from download_bry import boundary_bboxes, split_at_seam  # noqa: E402

INK = "#0b0b0b"
INK2 = "#52514e"
LAND = "#bdb8ad"
BOX = "#eb6834"     # the requested box
GRIDC = "#1baf7a"   # Moana grid outline
POINTS = {"rho": ("o", "#0b0b0b"), "u": (">", "#2a78d6"), "v": ("^", "#9b3fd1")}
EDGE = {"south": (0, slice(None)), "north": (-1, slice(None)),
        "west": (slice(None), 0), "east": (slice(None), -1)}


def surface_speed(path):
    """Surface current speed at the first record, with longitude in 0..360."""
    ds = xr.open_dataset(path).isel(time=0)
    ds = ds.sel(elevation=ds.elevation.max())          # the top level
    ds = ds.assign_coords(longitude=ds.longitude % 360).sortby("longitude")
    return np.hypot(ds.uo, ds.vo)


def draw_requests(ax, side, cfg, boxes):
    """The requested box; a box that crosses the source's seam is drawn as its two pieces."""
    pieces = split_at_seam(boxes[side], cfg["LON_CONVENTION"])
    for n, (xmin, ymin, xmax, ymax) in enumerate(pieces):
        xmin, xmax = xmin % 360, xmax % 360
        if xmax <= xmin:                                # piece ends at 180 = -180
            xmax += 360
        label = "requested box (edge points + PAD)" if n == 0 else None
        ax.add_patch(Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, fill=False,
                               edgecolor=BOX, linewidth=1.5, label=label))
    if len(pieces) == 2:
        ax.axvline(180, color=BOX, linestyle="--", linewidth=1,
                   label="seam of the source: asked as two pieces")


def plot_side(side, cfg, boxes, grid):
    raw = Path(cfg["OUTPUT_DIR"]) / side / f"{cfg['name']}_{side}_raw_{cfg['START']}_{cfg['END']}.nc"
    speed = surface_speed(raw)
    lon_rho, lat_rho = grid["lon_rho"], grid["lat_rho"]
    outline_lon = np.concatenate([lon_rho[0], lon_rho[:, -1], lon_rho[-1, ::-1], lon_rho[::-1, 0]])
    outline_lat = np.concatenate([lat_rho[0], lat_rho[:, -1], lat_rho[-1, ::-1], lat_rho[::-1, 0]])

    land = speed.isnull().where(speed.isnull())        # 1 on land (NaN in the file), NaN elsewhere

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [1.2, 1]})
    for ax in (ax1, ax2):
        cell_edges = "white" if ax is ax2 else "none"   # show the source cells only in the zoom
        mesh = ax.pcolormesh(speed.longitude, speed.latitude, speed, cmap="Blues", vmin=0, vmax=0.6,
                             shading="nearest", edgecolor=cell_edges, linewidth=0.2)
        ax.pcolormesh(land.longitude, land.latitude, land, cmap=ListedColormap([LAND]), shading="nearest")
        ax.set_xlabel("longitude (°E, 0..360)")
        ax.set_ylabel("latitude (°)")

    # left: whole grid, outside the strip is white (not downloaded)
    ax1.plot(outline_lon % 360, outline_lat, color=GRIDC, linewidth=1.5, label="Moana ROMS grid")
    draw_requests(ax1, side, cfg, boxes)
    ax1.add_patch(Rectangle((0, 0), 0, 0, color=LAND, label="land (NaN in the file)"))
    ax1.set_xlim(158, 188)
    ax1.set_ylim(-55, -28)
    ax1.set_aspect(1 / np.cos(np.deg2rad(41)))
    ax1.set_title(f"{side} boundary: the strip download_bry.py fetches", loc="left", color=INK)
    ax1.legend(loc="center", fontsize=8, framealpha=0.9)

    # right: zoom on the middle of the edge, with the source cells and the ROMS points
    mid_lon = np.median(lon_rho[EDGE[side]]) % 360
    mid_lat = np.median(lat_rho[EDGE[side]])
    ax2.set_xlim(mid_lon - 0.5, mid_lon + 0.5)
    ax2.set_ylim(mid_lat - 0.4, mid_lat + 0.4)
    ax1.add_patch(Rectangle((mid_lon - 0.5, mid_lat - 0.4), 1.0, 0.8, fill=False, edgecolor=INK,
                            linewidth=1, label="zoom (right panel)"))
    ax2.set_aspect(1 / np.cos(np.deg2rad(mid_lat)))
    for pt, (marker, color) in POINTS.items():
        lon = grid[f"lon_{pt}"][EDGE[side]] % 360
        lat = grid[f"lat_{pt}"][EDGE[side]]
        ax2.plot(lon, lat, marker, color=color, markersize=6, linestyle="none", label=f"{pt}-points on the edge")
    ax2.set_title("zoom: source cells (1/12°) and ROMS edge points", loc="left", color=INK)
    ax2.legend(loc="best", fontsize=8, framealpha=0.9)

    fig.colorbar(mesh, ax=[ax1, ax2], shrink=0.7, label="surface current speed (m/s)")
    lon, lat = speed.longitude.values, speed.latitude.values
    fig.text(0.01, 0.01,
             f"file: {raw.name}   lon {lon.min():.2f} .. {lon.max():.2f}   lat {lat.min():.2f} .. {lat.max():.2f}   "
             f"first record {str(speed.time.values)[:16]}   PAD {cfg['PAD']}°   source {cfg['DATASOURCE']}",
             fontsize=8, color=INK2)

    out = REPO / "concept_figures" / f"bry_strip_{side}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    config = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "download_bry.yaml"
    with open(config) as f:
        cfg = yaml.safe_load(f)
    boxes = boundary_bboxes(cfg["GRID"], pad=cfg["PAD"], convention=cfg["LON_CONVENTION"])
    with xr.open_dataset(cfg["GRID"]) as g:
        grid = {f"{c}_{pt}": g[f"{c}_{pt}"].values for c in ("lon", "lat") for pt in ("rho", "u", "v")}
    for side in cfg["SIDES"]:
        plot_side(side, cfg, boxes, grid)


if __name__ == "__main__":
    main()
