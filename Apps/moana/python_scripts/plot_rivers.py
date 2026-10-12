#!/usr/bin/env python
"""Figure of CAMELS-NZ river flows, a first look for the Moana river forcing.

Usage (moana_python environment, see env/moana_python.yml):

    python Apps/moana/python_scripts/plot_rivers.py [--out DIR]

Reads the CAMELS-NZ daily streamflow and catchment information
(scripts/fetch_camels_nz.sh, Input/rivers/camels_nz/) and writes
moana_rivers.{pdf,png} to --out (default Apps/moana/Figures).

  a  gauges coloured by mean flow over the run period
  b  the largest rivers: mean flow at the most downstream gauge of each
     river system
  c  daily flow through the run period for the six largest, with each
     gauge's day-of-year mean over all its years

"Run period" is 2017-10-01 to 2019-12-31; a gauge counts if it has flow on
at least 90 % of those days. A counted gauge is "most downstream" if it lies
in no other counted gauge's catchment (All_Nested_Catchments.shp, tested in
the shapefiles' own NZ Map Grid coordinates), so tributary and upstream
gauges drop out. DIST_SEA is in metres ("Waiau at Mouth" is 1.6 km).

Data notes (CAMELS-NZ version 5, checked 2026-10-08): 14 of 369 stations
have no flow in the public files (the Readme lists them as needing the
owner's permission); station 57521 writes dates as d/m/Y. The Clutha,
Waikato, Waitaki and Waimakariri have no gauge in CAMELS-NZ, so these
flows are not the river forcing; they show what an open, gauged source
covers.
"""

import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyogrio
import shapely
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D

from plot_glorys_ic_bc import colorbar, save, tidy
from plot_grid import (APP, HALO, INK, INK2, LAND, MM, SLOT1, axes_mm,
                       load_grid, merc, panel_label, set_lat_ticks,
                       set_lon_ticks)

CAMELS = Path("/projects/f_omg_1/moa/moana/Input/rivers/camels_nz")
RUN = ("2017-10-01", "2019-12-31")
NDAYS = 822
MIN_COVER = 0.9
N_BARS, N_SERIES = 15, 6
# dataviz sequential blue, steps 250-700 (lightest still clears 2:1)
BLUES = LinearSegmentedColormap.from_list(
    "blues", ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
              "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"])
MUTED = "#898781"
GRID = "#e1e0d9"


def read_flow(path):
    """Daily flow (m3 s-1) or None for the stations without public data."""
    try:
        q = pd.read_csv(path, na_values="NA")
    except pd.errors.EmptyDataError:
        return None
    if "time" not in q or q["flow"].notna().sum() == 0:
        return None
    fmt = "%d/%m/%Y" if "/" in str(q["time"].iloc[0]) else "%Y-%m-%d"
    s = pd.Series(q["flow"].astype(float).values,
                  index=pd.to_datetime(q["time"], format=fmt)).sort_index()
    assert not s.index.duplicated().any(), path
    return s


def load():
    info = pd.read_csv(CAMELS / "CAMELS_NZ_Catchment_Atrributes"
                       / "1.CAMELS_NZ_Catchment_information.csv",
                       encoding="utf-8-sig")
    info = info.rename(columns={"Latitude (WGS 84)": "lat",
                                "Longitude(WGS 84)": "lon",
                                "Station Name": "name"}).set_index("Station_ID")
    flows = {}
    for f in (CAMELS / "CAMELS_NZ_daily_Streamflow").glob("daily_flow_station_id_*.csv"):
        q = read_flow(f)
        if q is not None:
            flows[int(f.stem.split("_")[-1])] = q
    run = {k: q[RUN[0]:RUN[1]] for k, q in flows.items()}
    info["cover"] = pd.Series({k: r.notna().sum() / NDAYS for k, r in run.items()})
    info["mean_run"] = pd.Series({k: r.mean() for k, r in run.items()})
    info["river"] = info["name"].str.split(" at ").str[0]
    return info, flows


def largest(info):
    """Counted gauges inside no other counted gauge's catchment, by mean flow."""
    ok = info[info.cover >= MIN_COVER]
    shp = CAMELS / "CAMELS_NZ_Shapefiles"
    cat = pyogrio.read_dataframe(shp / "All_Nested_Catchments.shp")
    pts = pyogrio.read_dataframe(shp / "camel_stationsNZ.shp")
    cat = cat[cat.stationnum.isin(ok.index)].reset_index(drop=True)
    pts = pts[pts.Station_ID.isin(ok.index)].reset_index(drop=True)
    ip, ic = shapely.STRtree(cat.geometry.values).query(
        pts.geometry.values, predicate="within")
    inner = pts.Station_ID.values[ip] != cat.stationnum.values[ic]
    upstream = set(pts.Station_ID.values[ip[inner]])
    return ok.drop(index=list(upstream)).sort_values("mean_run", ascending=False)


def doy_mean(q):
    """Day-of-year mean over all years, smoothed with a 31-day circular window."""
    c = q.groupby(q.index.dayofyear).mean().reindex(range(1, 367))
    c = pd.concat([c.iloc[-15:], c, c.iloc[:15]]).rolling(31, center=True,
                                                          min_periods=20).mean()
    return c.iloc[15:-15]


def fig_rivers(g, out):
    info, flows = load()
    top = largest(info)
    H = 192
    fig = plt.figure(figsize=(180 * MM, H * MM))

    # a: map of the gauges.
    lon0, lon1, lat0, lat1 = 166.0, 179.0, -47.6, -34.0
    wmap, ybot = 56, 104
    hmap = wmap * (merc(lat1) - merc(lat0)) / (lon1 - lon0)
    ax = axes_mm(fig, 12, ybot, wmap, hmap)
    land = np.ma.masked_where(g["ocean"], np.ones_like(g["h"]))
    ax.pcolormesh(g["lon_vert"], g["y_vert"], land, rasterized=True,
                  cmap=LinearSegmentedColormap.from_list("land", [LAND, LAND]))
    ax.set_xlim(lon0, lon1)
    ax.set_ylim(merc(lat0), merc(lat1))
    ax.set_aspect("equal")
    set_lon_ticks(ax, [168, 172, 176])
    set_lat_ticks(ax, [-46, -42, -38, -34])
    off = info[~(info.cover >= MIN_COVER)]
    ax.scatter(off.lon, merc(off.lat.values), s=5, facecolor="none",
               edgecolor=MUTED, linewidth=0.4, zorder=3)
    on = info[info.cover >= MIN_COVER].sort_values("mean_run")
    sc = ax.scatter(on.lon, merc(on.lat.values), c=on.mean_run, s=9,
                    cmap=BLUES, norm=LogNorm(0.1, 500), edgecolor="white",
                    linewidth=0.4, zorder=4)
    for n, (sid, r) in enumerate(top.head(N_BARS).iterrows(), 1):
        ax.text(r.lon + 0.18, merc(r.lat), str(n), fontsize=5, va="center",
                color=INK, path_effects=HALO, zorder=5)
    cb = colorbar(fig, sc, (12, ybot - 12, wmap, 1.8),
                  "Mean flow, run period (m$^3$ s$^{-1}$)",
                  ticks=[0.1, 1, 10, 100])
    cb.ax.set_xticklabels(["0.1", "1", "10", "100"])
    cb.ax.minorticks_off()
    ax.legend(handles=[Line2D([], [], ls="none", marker="o", ms=3, mfc="none",
                              mec=MUTED, mew=0.4,
                              label=f"< {MIN_COVER:.0%} of days, or no public data")],
              loc="lower right", frameon=False, fontsize=5.5, handletextpad=0.3,
              borderaxespad=0.3)
    panel_label(ax, "a", x=-0.08, y=1.01)
    ax.text(0.0, 1.01, f"CAMELS-NZ gauges ({len(on)} of {len(info)} with "
            "run-period data)", transform=ax.transAxes, fontsize=6.5,
            ha="left", va="bottom")

    # b: the largest rivers.
    b = top.head(N_BARS)
    ax = axes_mm(fig, 124, ybot, 50, hmap)
    yy = np.arange(len(b))[::-1]
    ax.barh(yy, b.mean_run, height=0.62, color=SLOT1, zorder=2)
    for y, (sid, r) in zip(yy, b.iterrows()):
        ax.text(r.mean_run + 6, y, f"{r.mean_run:.0f}", fontsize=5.5,
                va="center", color=INK)
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{n}  {r['name']} ({r.DIST_SEA / 1000:.0f} km)"
                        for n, (_, r) in enumerate(b.iterrows(), 1)],
                       fontsize=5.5)
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-0.6, len(b) - 0.4)
    ax.set_xlim(0, b.mean_run.max() * 1.18)
    ax.set_xlabel("Mean flow, run period (m$^3$ s$^{-1}$)")
    ax.grid(axis="x", color=GRID, lw=0.4)
    ax.set_axisbelow(True)
    tidy(ax)
    ax.spines["left"].set_visible(False)
    panel_label(ax, "b", x=-0.96, y=1.01)
    ax.text(-0.92, 1.01, "Largest rivers: most downstream gauge of each "
            "(distance from the sea)", transform=ax.transAxes,
            fontsize=6.5, ha="left", va="bottom")

    # c: daily flow, six largest.
    w, h, gx, gy = 46, 24, 12, 12
    x0, y_top = 16, 72
    t0, t1 = pd.Timestamp(RUN[0]), pd.Timestamp(RUN[1])
    axs = []
    for k, (sid, r) in enumerate(top.head(N_SERIES).iterrows()):
        cx, cy = x0 + (k % 3) * (w + gx), y_top - h - (k // 3) * (h + gy)
        ax = axes_mm(fig, cx, cy, w, h)
        q = flows[sid]
        run = q[t0:t1]
        clim = doy_mean(q)
        ax.plot(run.index, run.values, color=SLOT1, lw=0.5, zorder=2)
        ax.plot(run.index, clim.reindex(run.index.dayofyear).values,
                color=INK, lw=0.8, zorder=3)
        ax.set_xlim(t0, t1)
        ax.set_ylim(0, None)
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.tick_params(labelsize=5.5)
        if k % 3 == 0:
            ax.set_ylabel("m$^3$ s$^{-1}$", fontsize=6)
        if k < 3:
            ax.tick_params(labelbottom=False)
        tidy(ax)
        ax.text(0.0, 1.03, f"{k + 1}  {r['name']}", transform=ax.transAxes,
                fontsize=6, ha="left", va="bottom")
        axs.append(ax)
    fig.text(12 / 180, 80 / H, "c", fontsize=8, fontweight="bold",
             ha="right", va="bottom")
    fig.text(14 / 180, 80 / H, "Daily flow through the run period, six "
             "largest", fontsize=6.5, va="bottom")
    fig.legend(handles=[Line2D([], [], color=SLOT1, lw=0.8, label="daily flow"),
                        Line2D([], [], color=INK, lw=0.8,
                               label="day-of-year mean, all years (31-day smoothed)")],
               loc="lower right", bbox_to_anchor=(1 - 4 / 180, 80 / H),
               ncol=2, frameon=False, fontsize=5.5, handlelength=1.8,
               borderaxespad=0)
    fig.text(12 / 180, 2 / H, "The Clutha, Waikato, Waitaki and Waimakariri "
             "have no gauge in CAMELS-NZ; the Dart and Waipa gauges lie far up "
             "the Clutha and Waikato systems.\nThese flows are not yet the "
             "model's river inflows.", fontsize=6, color=INK2)
    fig.text(12 / 180, 0.99, "CAMELS-NZ daily streamflow (v5), run period "
             f"{RUN[0]} to {RUN[1]}", fontsize=7, va="top")
    save(fig, out / "moana_rivers")
    return top


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", type=Path, default=APP / "Figures")
    args = p.parse_args()
    g = load_grid(APP / "Input" / "moana_grid.nc")
    top = fig_rivers(g, args.out)
    print(top.head(N_BARS)[["name", "DIST_SEA", "mean_run", "cover"]].round(2))


if __name__ == "__main__":
    main()
