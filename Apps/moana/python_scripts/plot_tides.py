#!/usr/bin/env python
"""Figure of the TPXO9-atlas v5 tides for the Moana domain.

Usage (moana_python environment, see env/moana_python.yml):

    python Apps/moana/python_scripts/plot_tides.py [--out DIR]

Reads oceanum_input/tide_forcing/tpxo9_atlas_v5_moana.nc (scripts/fetch_tpxo.py) and writes
moana_tides.{pdf,png} to --out (default Apps/moana/Figures).

Panels a-e: elevation amplitude (shading) and Greenwich phase lag (cotidal
lines every 30 deg) of M2, S2, N2, K1 and O1. Panel f: semi-major axis of
the M2 tidal-current ellipse. Cotidal lines are drawn from the complex
amplitude smoothed over ~10 km (Gaussian, 3 cells), for display only: where
phase changes slowly, small steps in TPXO9-atlas otherwise turn the lines
into staircases. Shading is unsmoothed. Panels g, h: amplitude and phase at the 15
LINZ tide gauges of the hindcast paper (Table 2), in the paper's station
order (anticlockwise round New Zealand), to set beside its Fig. 11.

Phase is G = atan2(-Im, Re) (OSU convention). Checked 2026-10-08: with
it, M2 phase rises from station 1 to 15 as the paper's Fig. 11 shows; with
the opposite sign it falls. Values at a gauge are from the nearest wet
TPXO cell. These are TPXO fields, not yet the model's tidal forcing.
"""

import argparse
from pathlib import Path

import cmocean
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import LogNorm, Normalize
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, NullLocator
from scipy.ndimage import gaussian_filter

from plot_glorys_ic_bc import colorbar, map_axes, save, tidy
from plot_grid import APP, HALO, INK, MM, axes_mm, load_grid, merc, panel_label

TPXO = Path("/projects/f_omg_1/moa/moana/oceanum_input/tide_forcing/tpxo9_atlas_v5_moana.nc")
MAPS = ("M2", "S2", "N2", "K1", "O1")
GAUGE_CONS = ("M2", "S2", "N2", "K1")
# dataviz categorical slots 1-4 (validated adjacent, light mode)
SLOTS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
# Hindcast paper Table 2: LINZ gauges, anticlockwise from Port Chalmers.
GAUGES = [
    ("Port Chalmers", -45.82, 170.65), ("Chatham Islands", -44.03, 183.63),
    ("Sumner", -43.57, 172.57), ("Kaikōura", -42.42, 173.70),
    ("Wellington", -41.28, 174.78), ("Castlepoint", -40.92, 176.22),
    ("Napier", -39.48, 176.92), ("Gisborne", -38.67, 178.03),
    ("Lottin Point", -37.55, 178.17), ("Auckland", -36.83, 174.78),
    ("Great Barrier Island", -36.18, 175.48), ("North Cape", -34.42, 173.05),
    ("Manukau", -37.05, 174.52), ("Charleston", -41.90, 171.43),
    ("Puysegur", -46.08, 166.58),
]


def load():
    ds = xr.open_dataset(TPXO)
    cx = lambda v: ds[v + "Re"] + 1j * ds[v + "Im"]
    h, u, v = cx("h"), cx("u"), cx("v")
    wet = (ds.dep > 0) & (np.abs(h.sel(con="M2")) > 0)
    return ds, h.where(wet), u.where(wet), v.where(wet), wet


def amp_phase(z):
    return np.abs(z), np.degrees(np.arctan2(-z.imag, z.real)) % 360


def smooth(z, sigma=3):
    """Gaussian smoothing of a complex field with NaN (land) left out."""
    wet = np.isfinite(z)
    z0 = np.where(wet, z, 0)
    norm = gaussian_filter(wet.astype(float), sigma)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (gaussian_filter(z0.real, sigma) + 1j * gaussian_filter(z0.imag, sigma)) / norm
    return np.where(wet, out, np.nan)


def semi_major(u, v):
    """Semi-major axis of the current ellipse from complex amplitudes."""
    return (np.abs(u + 1j * v) + np.abs(np.conj(u) + 1j * np.conj(v))) / 2


def cotidal(ax, lon, y, G, A, step=30, floor=0.05):
    """Phase contours without the 360 -> 0 seam: 90..270 from G with values
    near 0/360 masked, -60..60 from G - 360 (G > 180) with values near
    +-180 masked. Phase is left out where the amplitude is below `floor`
    of its 99th percentile (near amphidromes it is noise)."""
    kw = dict(colors=INK, linewidths=0.35, linestyles="solid", zorder=3)
    G = np.where(A >= floor * np.nanpercentile(A, 99), G, np.nan)
    G1 = np.where((G > 45) & (G < 315), G, np.nan)
    Gs = np.where(G > 180, G - 360, G)
    G2 = np.where(np.abs(Gs) < 135, Gs, np.nan)
    cs1 = ax.contour(lon, y, G1, levels=np.arange(90, 271, step), **kw)
    cs2 = ax.contour(lon, y, G2, levels=np.arange(-60, 61, step), **kw)
    for cs, lv in ((cs1, [90, 180, 270]), (cs2, [0])):
        ax.clabel(cs, levels=lv, fontsize=4.5, inline_spacing=1,
                  fmt=lambda x: f"{x % 360:.0f}°")


def at_gauges(ds, wet, z):
    """Nearest wet TPXO cell to each gauge: (amplitude, phase) arrays."""
    lat2, lon2 = np.meshgrid(ds.lat.values, ds.lon.values, indexing="ij")
    out = []
    for _, la, lo in GAUGES:
        d = np.where(wet, (lat2 - la) ** 2
                     + ((lon2 - lo) * np.cos(np.radians(la))) ** 2, np.inf)
        j, i = np.unravel_index(d.argmin(), d.shape)
        out.append(complex(z.values[j, i]))
    return amp_phase(np.array(out))


def fig_tides(g, out):
    ds, h, u, v, wet = load()
    lon, y = ds.lon.values, merc(ds.lat.values)
    H = 232
    fig = plt.figure(figsize=(180 * MM, H * MM))
    w, gap, left = 50, 8, 12
    hmap = w * (g["y_vert"].max() - g["y_vert"].min()) / (
        g["lon_vert"].max() - g["lon_vert"].min())
    pos = [(left + c * (w + gap), b) for b in (162, 76) for c in range(3)]

    axs = []
    for k, ((x0, y0), con) in enumerate(zip(pos, MAPS + ("M2 current",))):
        ax = axes_mm(fig, x0, y0, w, hmap)
        map_axes(ax, g, lat_labels=(k % 3 == 0))
        if k < len(MAPS):
            z = h.sel(con=con).values
            A, _ = amp_phase(z)
            As, G = amp_phase(smooth(z))
            hi = np.ceil(np.nanpercentile(A, 99) * 20) / 20
            pm = ax.pcolormesh(lon, y, A, shading="nearest", cmap=cmocean.cm.amp,
                               norm=Normalize(0, hi), rasterized=True, zorder=1)
            cotidal(ax, lon, y, G, As)
            colorbar(fig, pm, (x0, y0 - 13, w, 1.8), f"{con} amplitude (m)")
            title = f"{con} elevation"
        else:
            S = semi_major(u.sel(con="M2").values, v.sel(con="M2").values)
            pm = ax.pcolormesh(lon, y, S, shading="nearest", cmap=cmocean.cm.speed,
                               norm=LogNorm(0.01, 2), rasterized=True, zorder=1)
            cb = colorbar(fig, pm, (x0, y0 - 13, w, 1.8),
                          "M2 current, semi-major axis (m s$^{-1}$)",
                          ticks=[0.01, 0.03, 0.1, 0.3, 1])
            cb.ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))
            cb.ax.xaxis.set_minor_locator(NullLocator())
            title = "M2 tidal current"
        axs.append(ax)
        panel_label(ax, "abcdef"[k], x=-0.06, y=1.02)
        ax.text(0.0, 1.02, title, transform=ax.transAxes, fontsize=6.5,
                ha="left", va="bottom")
    axs[0].text(0.02, 0.02, "lines: phase, 30°", transform=axs[0].transAxes,
                fontsize=5.5, color=INK, path_effects=HALO, zorder=5)
    for n, (_, la, lo) in enumerate(GAUGES, 1):
        axs[0].plot(lo, merc(la), "o", ms=3, mfc="white", mec=INK, mew=0.6,
                    zorder=6)
        dx = -0.45 if n == 13 else 0.45  # Manukau sits beside Auckland (10)
        axs[0].text(lo + dx, merc(la), str(n), fontsize=4.5, va="center",
                    ha="right" if dx < 0 else "left", color=INK,
                    path_effects=HALO, zorder=6)

    # g, h: the gauges.
    st = np.arange(1, len(GAUGES) + 1)
    ax_a = axes_mm(fig, left + 4, 12, 70, 30)
    ax_p = axes_mm(fig, left + 98, 12, 70, 30)
    for con, color in zip(GAUGE_CONS, SLOTS):
        A, G = at_gauges(ds, wet, h.sel(con=con))
        G = np.unwrap(G, period=360)
        for ax, val in ((ax_a, A), (ax_p, G)):
            ax.plot(st, val, color=color, lw=0.8, marker="o", ms=3, mfc=color,
                    mec="white", mew=0.6, zorder=3)
    for ax, ylab in ((ax_a, "Amplitude (m)"), (ax_p, "Phase (°, unwrapped)")):
        ax.set_xticks(st)
        ax.set_xlim(0.5, 15.5)
        ax.set_xlabel("Station number (paper Table 2)")
        ax.set_ylabel(ylab)
        ax.grid(axis="y", color="#e1e0d9", lw=0.4)
        ax.set_axisbelow(True)
        tidy(ax)
    ax_a.set_ylim(0, None)
    ax_p.set_yticks(np.arange(0, 451, 90))
    for ax, letter, title in ((ax_a, "g", "Amplitude at the LINZ tide gauges"),
                              (ax_p, "h", "Phase at the LINZ tide gauges")):
        panel_label(ax, letter, x=-0.12, y=1.04)
        ax.text(0.0, 1.04, title, transform=ax.transAxes, fontsize=6.5,
                ha="left", va="bottom")
    fig.legend(handles=[Line2D([], [], color=c, lw=0.8, marker="o", ms=3,
                               mec="white", mew=0.6, label=con)
                        for con, c in zip(GAUGE_CONS, SLOTS)],
               loc="lower left", bbox_to_anchor=(left / 180, 49 / H), ncol=4,
               frameon=False, fontsize=6, handlelength=1.8, borderaxespad=0)
    fig.text(left / 180, 0.985, "TPXO9-atlas v5 (1/30°) tides, before "
             "interpolation to the model grid; compare g, h with the "
             "hindcast paper's Fig. 11", fontsize=7, va="top")
    save(fig, out / "moana_tides")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", type=Path, default=APP / "Figures")
    args = p.parse_args()
    g = load_grid(APP / "Input" / "moana_grid.nc")
    fig_tides(g, args.out)


if __name__ == "__main__":
    main()
