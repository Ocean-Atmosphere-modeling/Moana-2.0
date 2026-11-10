#!/usr/bin/env python
"""Four Moana-2.0 model inputs as one 2 x 2 poster figure, sized to the poster region.

    python plot_poster_inputs.py                      # 13 x 17 in, writes to ../Figures
    python plot_poster_inputs.py --width 12 --height 16 --out ~/poster

Panels (same map extent, land mask and fonts):
    Tides             TPXO9-atlas v5, M2 amplitude
    Atmosphere        ECMWF IFS forcing file, mean 10 m wind over the run
    Boundaries        CMEMS boundary file, surface temperature on the open edges at t0,
                      plus the 200 km nudging zone
    Initial conditions  CMEMS initial file, surface temperature at t0

Run on Amarel in the moana_python environment. Paths match Apps/moana/Runs/moana.in.
Writes poster_inputs.png (300 dpi, transparent background) and poster_inputs.pdf.
"""
import argparse
from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

try:
    import cmocean
    CM_SST, CM_TIDE = cmocean.cm.thermal, cmocean.cm.amp
except ImportError:
    CM_SST, CM_TIDE = plt.get_cmap("inferno"), plt.get_cmap("Reds")
CM_WIND = plt.get_cmap("viridis")

# ---------------------------------------------------------------- inputs (moana.in)
ROOT = Path("/projects/f_omg_1/moa/moana")
GRID = ROOT / "grid/moana_grid_N50.nc"
TPXO = ROOT / "oceanum_input/tide_forcing/tpxo9_atlas_v5_moana.nc"
FRC = ROOT / "oceanum_input/atm_forcing/moana_frc_ifs_2025-12-31_91D.nc"
BRY = ROOT / "oceanum_input/boundary_cond/roms-ready_jan26/bry_temp.nc"
INI = ROOT / "oceanum_input/initial_cond/roms_ready/ic_2026-01-01.nc"

# ---------------------------------------------------------------- style
SST_LIMS = (9.5, 23.5)          # same as the ROMS SST figures, so before/after match
TIDE_LIMS = (0.0, 1.0)          # m
WIND_LIMS = (0.0, 8.0)          # m s-1
NUDGE_KM = 200                  # nudging file: nz5km_nudgcoef_200km_1day.nc
LAND, COAST, INK = "#d9d4c7", "#5f5a50", "#0B2545"
OCEAN_BG = "#EEF3F6"
FONT = "DejaVu Sans"
PT_TITLE, PT_SUB, PT_TICK, PT_LABEL = 30, 22, 18, 19


def lon360(x):
    return np.mod(x, 360.0)


def load_grid():
    g = xr.open_dataset(GRID)
    lon, lat = lon360(g.lon_rho.values), g.lat_rho.values
    return lon, lat, g.mask_rho.values


def regular(ds, lonname, latname):
    """Put a lon/lat dataset on 0-360 longitudes, sorted, so pcolormesh works across 180."""
    ds = ds.assign_coords({lonname: lon360(ds[lonname])})
    return ds.sortby(lonname).sortby(latname)


# ---------------------------------------------------------------- panels
def panel_tides(ax):
    ds = regular(xr.open_dataset(TPXO), "lon", "lat")
    h = ds.hRe.sel(con="M2") + 1j * ds.hIm.sel(con="M2")
    amp = np.abs(h).where(ds.dep > 0)
    return ax.pcolormesh(ds.lon, ds.lat, amp, cmap=CM_TIDE, vmin=TIDE_LIMS[0],
                         vmax=TIDE_LIMS[1], shading="auto", rasterized=True)


def panel_wind(ax, extent):
    ds = xr.open_dataset(FRC)
    ds = regular(ds, "lon", "lat")
    u, v = ds.Uwind.mean("time"), ds.Vwind.mean("time")
    spd = np.hypot(u, v)
    pc = ax.pcolormesh(ds.lon, ds.lat, spd, cmap=CM_WIND, vmin=WIND_LIMS[0],
                       vmax=WIND_LIMS[1], shading="auto", rasterized=True)
    sl = ds.sel(lon=slice(extent[0], extent[1]), lat=slice(extent[2], extent[3]))
    step = max(1, int(round(1.5 / float(abs(ds.lon.diff("lon")).median()))))   # an arrow every ~1.5 deg
    us = u.sel(lon=sl.lon, lat=sl.lat)[::step, ::step]
    vs = v.sel(lon=sl.lon, lat=sl.lat)[::step, ::step]
    ax.quiver(us.lon, us.lat, us, vs, color="white", scale=120, width=0.0035,
              headwidth=4, zorder=4)
    return pc


def panel_boundaries(ax, glon, glat, extent):
    ax.add_patch(plt.Rectangle((extent[0], extent[2]), extent[1] - extent[0],
                               extent[3] - extent[2], fc=OCEAN_BG, ec="none", zorder=0))
    ds = xr.open_dataset(BRY)
    edges = {"west": (glon[:, 0], glat[:, 0]), "east": (glon[:, -1], glat[:, -1]),
             "south": (glon[0, :], glat[0, :]), "north": (glon[-1, :], glat[-1, :])}
    lc = None
    for side, (x, y) in edges.items():
        name = f"temp_{side}"
        if name not in ds:
            continue
        da = ds[name].isel({ds[name].dims[0]: 0})          # first record
        if "s_rho" in da.dims:
            da = da.isel(s_rho=-1)                         # surface
        val = da.values
        pts = np.column_stack([x, y])
        segs = np.stack([pts[:-1], pts[1:]], axis=1)
        mid = 0.5 * (val[:-1] + val[1:])
        ok = np.isfinite(mid)
        lc = LineCollection(segs[ok], cmap=CM_SST, linewidths=12, capstyle="butt", zorder=9, clip_on=False)
        lc.set_array(mid[ok])
        lc.set_clim(*SST_LIMS)
        ax.add_collection(lc)
    # nudging zone: ~NUDGE_KM inside the open edges
    lat0 = 0.5 * (extent[2] + extent[3])
    dlat = NUDGE_KM / 111.0
    dlon = dlat / np.cos(np.radians(lat0))
    ax.add_patch(plt.Rectangle((extent[0] + dlon, extent[2] + dlat),
                               extent[1] - extent[0] - 2 * dlon, extent[3] - extent[2] - 2 * dlat,
                               fill=False, ec=INK, lw=1.6, ls=(0, (6, 4)), zorder=4))
    ax.text(extent[0] + dlon + 0.4, extent[2] + dlat + 0.4, f"nudging zone ({NUDGE_KM} km)",
            fontsize=PT_TICK - 2, color=INK, fontfamily=FONT, zorder=6)
    return lc


def panel_initial(ax, glon, glat):
    ds = xr.open_dataset(INI)
    t = ds.temp.isel({ds.temp.dims[0]: 0}).isel(s_rho=-1)
    return ax.pcolormesh(glon, glat, t.values, cmap=CM_SST, vmin=SST_LIMS[0],
                         vmax=SST_LIMS[1], shading="auto", rasterized=True)


# ---------------------------------------------------------------- layout
def header(fig, x, top, H, title, sub):
    """Bold title with a lighter source line under it, left-aligned; top in inches."""
    fig.text(x, (top - 0.42) / H, title, fontsize=PT_TITLE, fontweight="bold", color=INK,
             fontfamily=FONT, va="baseline")
    fig.text(x, (top - 0.80) / H, sub, fontsize=PT_SUB, color="#3E5566",
             fontfamily=FONT, va="baseline")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=float, default=13.0, help="region width (in)")
    ap.add_argument("--height", type=float, default=17.0, help="region height (in)")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "Figures")
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()

    glon, glat, mask = load_grid()
    extent = (float(glon.min()), float(glon.max()), float(glat.min()), float(glat.max()))
    lat0 = 0.5 * (extent[2] + extent[3])
    aspect = (extent[1] - extent[0]) * np.cos(np.radians(lat0)) / (extent[3] - extent[2])

    W, H = a.width, a.height
    gap, head_h, cbar_h, cbar_lab = 0.4, 1.0, 0.22, 0.85       # inches
    map_w = (W - gap) / 2
    map_h = map_w / aspect
    row_h = head_h + map_h + cbar_h + cbar_lab
    if 2 * row_h + gap > H:                                     # too tall: shrink maps to fit
        map_h = (H - gap) / 2 - head_h - cbar_h - cbar_lab
        map_w = map_h * aspect
        row_h = head_h + map_h + cbar_h + cbar_lab
    x0 = (W - (2 * map_w + gap)) / 2
    y_top = (H - (2 * row_h + gap)) / 2

    plt.rcParams.update({"font.family": FONT, "xtick.labelsize": PT_TICK,
                         "axes.labelsize": PT_LABEL, "text.color": INK,
                         "axes.labelcolor": INK, "xtick.color": INK})
    fig = plt.figure(figsize=(W, H))

    panels = [("Tides", "TPXO9 M2 amplitude", "M2 amplitude (m)"),
              ("Atmosphere", "ECMWF IFS mean 10 m wind", "Wind speed (m s⁻¹)"),
              ("Boundaries", "CMEMS, 1 Jan 2026", "Surface temperature (°C)"),
              ("Initial conditions", "CMEMS SST, 1 Jan 2026", "Sea surface temperature (°C)")]

    for k, (title, sub, cblabel) in enumerate(panels):
        col, row = k % 2, k // 2
        left = x0 + col * (map_w + gap)
        top = H - (y_top + row * (row_h + gap))                  # inches from bottom
        header(fig, left / W, top, H, title, sub)
        mb = top - head_h - map_h
        ax = fig.add_axes([left / W, mb / H, map_w / W, map_h / H])
        cax = fig.add_axes([left / W, (mb - 0.12 - cbar_h) / H, map_w / W, cbar_h / H])

        if k == 0:
            m = panel_tides(ax)
        elif k == 1:
            m = panel_wind(ax, extent)
        elif k == 2:
            m = panel_boundaries(ax, glon, glat, extent)
        else:
            m = panel_initial(ax, glon, glat)

        land = np.ma.masked_where(mask > 0.5, np.ones_like(mask))
        ax.pcolormesh(glon, glat, land, cmap=matplotlib.colors.ListedColormap([LAND]),
                      shading="auto", zorder=7, rasterized=True)
        ax.contour(glon, glat, mask, levels=[0.5], colors=COAST, linewidths=0.8, zorder=8)

        ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
        ax.set_aspect(1 / np.cos(np.radians(lat0)))
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor(INK); s.set_linewidth(1.0)

        cb = fig.colorbar(m, cax=cax, orientation="horizontal")
        cb.outline.set_linewidth(0.6)
        cb.set_label(cblabel, fontsize=PT_LABEL, labelpad=4)
        cb.ax.tick_params(labelsize=PT_TICK, length=4)

    a.out.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out / "poster_inputs.png", dpi=a.dpi, transparent=True)
    fig.savefig(a.out / "poster_inputs.pdf", transparent=True)
    print("wrote", a.out / "poster_inputs.png", "and .pdf")


if __name__ == "__main__":
    main()
