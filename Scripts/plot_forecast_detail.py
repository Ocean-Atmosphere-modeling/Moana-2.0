#!/usr/bin/env python3
"""
Presentation plots and animations for the Moana ROMS November 2026 forecast run.

  python Scripts/plot_forecast_pretty.py <run_dir> <part> [<out_dir>]

part:
  overview   timeline of the run and of every input and its source (needs no model output)
  maps       one figure per day: daily-mean surface temperature, salinity and currents
  change     forecast change at the surface: last forecast day minus first forecast day
  anim       hourly animation: surface temperature, salinity and currents side by side
  anim_temp  hourly animation of surface temperature, full size
  anim_salt  hourly animation of surface salinity, full size
  cmems      ROMS minus CMEMS at the surface (bias and RMS over time, maps)
  points     sea level at tide gauges, SST at coastal stations, domain means
  log        run health from roms.log
  all        everything above
Every figure shows the valid time, spin-up or forecast (with lead time) and the data sources.
Output: <out_dir> (default <run_dir>/plots_pretty).
"""
import sys
import re
import textwrap
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")                                   # no screen on a compute node
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import animation
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

# ------------------------------------------------------------------ the run
GRID = "/projects/f_omg_1/moa/moana/grid/moana_grid_N50.nc"
CLM = {"temp": "/projects/f_omg_1/moa/moana/oceanum_input/climatology/roms_ready_nov26/clm_temp_2026-10-31_2026-11-16.nc",
       "salt": "/projects/f_omg_1/moa/moana/oceanum_input/climatology/roms_ready_nov26/clm_salt_2026-10-31_2026-11-16.nc"}
REF = pd.Timestamp("2026-01-01")                        # TIME_REF in moana.in
RUN_START = pd.Timestamp("2026-11-01 00:00")
FC_START = pd.Timestamp("2026-11-10 00:00")
RUN_END = pd.Timestamp("2026-11-15 00:00")
ATM_CYCLE = pd.Timestamp("2026-11-09 12:00")            # IFS forecast used for the forecast days
SOURCE = ("Model: Moana ROMS, New Zealand, 5 km, 50 levels, free run (no data assimilation). "
          "Start: CMEMS ocean state 1 Nov 2026 00 UTC (cold start). "
          "Atmosphere: ECMWF IFS 0.25° (first 12 h of each cycle up to 10 Nov, then the 9 Nov 12 UTC forecast). "
          "Ocean boundaries and T/S nudging: CMEMS global analysis/forecast via Oceanum DataMesh. Tides: TPXO9.")
SPIN, FC = "#2f6db5", "#c8323c"                         # colours for spin-up and forecast
# locations from Souza et al. (2023), Tables 2 and 3: name -> (lon, lat)
GAUGES = {"North Cape": (173.05, -34.42), "Auckland": (174.78, -36.83),
          "Wellington": (174.78, -41.28), "Port Chalmers": (170.65, -45.82)}
SST_STATIONS = {"Leigh": (174.80, -36.27), "Moturiki": (176.18, -37.63),
                "Evans Bay": (174.80, -41.30), "Portobello": (170.65, -45.83)}
CITIES = {"Auckland": (174.76, -36.85), "Wellington": (174.78, -41.29),
          "Christchurch": (172.64, -43.53), "Dunedin": (170.50, -45.87)}
FIELDS = {"temp": ("Sea surface temperature", "°C", "RdYlBu_r"),
          "salt": ("Sea surface salinity", "PSU", "viridis"),
          "speed": ("Surface current speed", "m/s", "magma")}
plt.rcParams.update({"font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
                     "figure.facecolor": "white", "savefig.facecolor": "white"})

run = Path(sys.argv[1])
part = sys.argv[2]
out = Path(sys.argv[3]) if len(sys.argv) > 3 else run / "plots_pretty"
out.mkdir(parents=True, exist_ok=True)

g = xr.open_dataset(GRID)
lon = g.lon_rho.values % 360                            # domain crosses 180E, so plot in 0-360
lat = g.lat_rho.values
water = g.mask_rho.values == 1
water_da = xr.DataArray(water, dims=("eta_rho", "xi_rho"))
angle = g["angle"].values if "angle" in g else np.zeros_like(lon)   # grid rotation: u, v -> east, north
ASPECT = 1 / np.cos(np.deg2rad(-41))                    # roughly equal distances in x and y
ARROWS = (slice(7, None, 14), slice(7, None, 14))      # every 14th point (~70 km) for current arrows
TL3 = [0.25, 0.075, 0.50, 0.03]                         # timeline bar, three-panel figures
TL1 = [0.14, 0.085, 0.74, 0.03]                         # timeline bar, single-panel figures


# ------------------------------------------------------------------ labels
def num(t):
    return mdates.date2num(pd.Timestamp(t).to_pydatetime())


def valid(t):
    return f"Valid {pd.Timestamp(t):%a %d %b %Y, %H:%M} UTC"


def phase(t):
    """Badge text, explanation and colour for time t."""
    t = pd.Timestamp(t)
    if t >= FC_START:
        h = (t - FC_START) / pd.Timedelta("1h")
        return f"FORECAST · day {min(int(h // 24) + 1, 5)} of 5", f"lead time +{h:.0f} h from 10 Nov 00 UTC", FC
    d = int((t - RUN_START) / pd.Timedelta("1D")) + 1
    return f"SPIN-UP · day {min(d, 9)} of 9", "past days: model adjusting from the 1 Nov cold start", SPIN


def header(fig, title, subtitle, t=None):
    """Title, subtitle and (if t is given) a coloured spin-up/forecast badge. Returns the texts animations update."""
    fig.text(0.012, 0.985, title, ha="left", va="top", fontsize=16, fontweight="bold")
    v = fig.text(0.012, 0.938, subtitle, ha="left", va="top", fontsize=12)
    if t is None:
        return v, None, None
    tag, sub, col = phase(t)
    b = fig.text(0.988, 0.985, tag, ha="right", va="top", fontsize=13, fontweight="bold", color="white",
                 bbox=dict(boxstyle="round,pad=0.45", fc=col, ec="none"))
    s = fig.text(0.988, 0.928, sub, ha="right", va="top", fontsize=10, color="0.35")
    return v, b, s


def set_header(texts, subtitle, t):
    v, b, s = texts
    tag, sub, col = phase(t)
    v.set_text(subtitle)
    b.set_text(tag)
    b.get_bbox_patch().set_facecolor(col)
    s.set_text(sub)


def footer(fig):
    fig.text(0.012, 0.008, textwrap.fill(SOURCE, int(fig.get_figwidth() * 15)),
             ha="left", va="bottom", fontsize=8, color="0.35")


def timeline(fig, rect):
    """Bar from 1 to 15 Nov, spin-up blue, forecast red. Returns the marker line to move."""
    ax = fig.add_axes(rect)
    ax.axvspan(num(RUN_START), num(FC_START), color=SPIN, alpha=0.25, lw=0)
    ax.axvspan(num(FC_START), num(RUN_END), color=FC, alpha=0.25, lw=0)
    ax.text(num(RUN_START + (FC_START - RUN_START) / 2), 0.5, "SPIN-UP  1–9 Nov", ha="center", va="center",
            fontsize=9, fontweight="bold", color=SPIN)
    ax.text(num(FC_START + (RUN_END - FC_START) / 2), 0.5, "FORECAST  10–14 Nov", ha="center", va="center",
            fontsize=9, fontweight="bold", color=FC)
    ax.text(-0.01, 0.5, "Nov 2026 (UTC)", transform=ax.transAxes, ha="right", va="center", fontsize=8)
    ax.set_xlim(num(RUN_START), num(RUN_END))
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d"))
    ax.tick_params(axis="x", labelsize=8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    return ax.axvline(num(RUN_START), color="black", lw=3)


PHASE_PATCHES = [Patch(facecolor=SPIN, alpha=0.25, label="spin-up (1–9 Nov)"),
                 Patch(facecolor=FC, alpha=0.3, label="forecast (10–14 Nov)")]


def shade(ax):
    """Shade spin-up and forecast periods on a time-series axis."""
    ax.axvspan(num(RUN_START), num(FC_START), color=SPIN, alpha=0.07, lw=0)
    ax.axvspan(num(FC_START), num(RUN_END), color=FC, alpha=0.09, lw=0)
    ax.axvline(num(FC_START), color=FC, lw=1.2, ls="--")
    ax.set_xlim(num(RUN_START), num(RUN_END))
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.grid(alpha=0.3)


def legend_with_phases(ax, **kw):
    h, l = ax.get_legend_handles_labels()
    ax.legend(h + PHASE_PATCHES, l + [p.get_label() for p in PHASE_PATCHES], **kw)


# ------------------------------------------------------------------ maps
def style_map(ax):
    ax.set_facecolor("#d4d4d4")                         # land shows through as grey
    ax.contour(lon, lat, water.astype(float), levels=[0.5], colors="0.25", linewidths=0.5)
    ax.set_xlim(lon.min(), lon.max())
    ax.set_ylim(lat.min(), lat.max())
    ax.set_aspect(ASPECT)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x % 360:.0f}°E" if x % 360 <= 180 else f"{360 - x % 360:.0f}°W"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{abs(y):.0f}°S" if y < 0 else f"{y:.0f}°N"))
    ax.tick_params(labelsize=9)
    for name, (lo, la) in CITIES.items():
        ax.plot(lo, la, "o", ms=3, color="black", zorder=5)
        ax.text(lo + 0.35, la, name, fontsize=8, va="center", zorder=5)


def surface(ds, n):
    """Surface temp, salt, east and north current of record n; land set to NaN."""
    r = ds.isel(ocean_time=n, s_rho=-1)
    sst = np.where(water, r.temp.values, np.nan)
    sss = np.where(water, r.salt.values, np.nan)
    if "u_eastward" in r:                               # history file: east/north currents on rho points
        ue = r.u_eastward.values.astype(float)
        vn = r.v_northward.values.astype(float)
    else:                                               # averages file: u, v on the staggered grid
        u, v = r.u.values, r.v.values
        ur, vr = np.full(sst.shape, np.nan), np.full(sst.shape, np.nan)
        ur[1:-1, 1:-1] = 0.5 * (u[1:-1, :-1] + u[1:-1, 1:])
        vr[1:-1, 1:-1] = 0.5 * (v[:-1, 1:-1] + v[1:, 1:-1])
        ue = ur * np.cos(angle) - vr * np.sin(angle)
        vn = ur * np.sin(angle) + vr * np.cos(angle)
    ue[~water] = np.nan
    vn[~water] = np.nan
    return sst, sss, ue, vn

def limits(s):
    sst, sss, ue, vn = s
    return {"temp": tuple(np.nanpercentile(sst, [1, 99])), "salt": tuple(np.nanpercentile(sss, [1, 99])),
            "speed": (0, np.nanpercentile(np.hypot(ue, vn), 99))}


def map_panel(fig, ax, cax, key, f, lim):
    name, unit, cmap = FIELDS[key]
    pc = ax.pcolormesh(lon, lat, f, shading="auto", cmap=cmap, vmin=lim[0], vmax=lim[1])
    style_map(ax)
    ax.set_title(name)
    cb = fig.colorbar(pc, cax=cax, orientation="horizontal")
    cb.set_label(f"{name} ({unit})", fontsize=10)
    return pc


def add_arrows(ax, ue, vn):
    q = ax.quiver(lon[ARROWS], lat[ARROWS], ue[ARROWS], vn[ARROWS], color="white", scale=15,
                  width=0.0022, headwidth=4, alpha=0.85, zorder=4)
    ax.quiverkey(q, 0.88, 0.05, 0.5, "0.5 m/s", labelpos="N", coordinates="axes", color="black",
                 fontproperties={"size": 8})
    return q


def three_panel_fig():
    fig = plt.figure(figsize=(19, 8.6))
    xs = (0.03, 0.355, 0.68)
    axes = [fig.add_axes([x, 0.20, 0.30, 0.62]) for x in xs]
    caxes = [fig.add_axes([x + 0.04, 0.155, 0.22, 0.02]) for x in xs]
    return fig, axes, caxes


def single_fig():
    fig = plt.figure(figsize=(10, 10.5))
    ax = fig.add_axes([0.08, 0.20, 0.86, 0.66])
    cax = fig.add_axes([0.20, 0.155, 0.60, 0.02])
    return fig, ax, cax


def save(fig, name):
    fig.savefig(out / name, dpi=150)
    plt.close(fig)
    print("saved", out / name, flush=True)


def write_animation(a, stem, dpi):
    if animation.writers.is_available("ffmpeg"):
        name = out / f"{stem}.mp4"
        a.save(name, writer=animation.FFMpegWriter(fps=12, bitrate=6000), dpi=dpi)
    else:
        name = out / f"{stem}.gif"
        a.save(name, writer=animation.PillowWriter(fps=12), dpi=int(dpi * 0.6))
    print("saved", name, flush=True)


def nearest_water(lo, la):
    d = np.where(water, (lon - lo % 360) ** 2 + (lat - la) ** 2, np.inf)
    return np.unravel_index(np.argmin(d), d.shape)


# ------------------------------------------------------------------ parts
def overview():
    fig, ax = plt.subplots(figsize=(15, 7.5))
    fig.subplots_adjust(left=0.17, right=0.97, top=0.80, bottom=0.16)
    t_bry0, t_bry1 = pd.Timestamp("2026-10-31"), pd.Timestamp("2026-11-16")
    rows = [
        ("ROMS model run", [(RUN_START, FC_START, SPIN, "white", "spin-up: 9 days"),
                            (FC_START, RUN_END, FC, "white", "forecast: 5 days")]),
        ("Initial condition", []),
        ("Atmosphere\nECMWF IFS", [(pd.Timestamp("2026-10-31 15:00"), FC_START, "#9dbbe3", "black",
                                    "first 12 h of each 00/12 UTC cycle (31 Oct 12Z – 9 Nov 12Z)"),
                                   (FC_START, pd.Timestamp("2026-11-15 03:00"), "#eba3a8", "black",
                                    "one forecast: 9 Nov 12 UTC, +15 to +135 h")]),
        ("Ocean boundaries\nCMEMS", [(t_bry0, t_bry1, "0.75", "black",
                                      "analysis for past days, then forecast · sea level hourly, u, v, T, S 6-hourly")]),
        ("T/S nudging\nCMEMS", [(t_bry0, t_bry1, "0.75", "black",
                                 "temperature and salinity, 6-hourly · analysis, then forecast")]),
        ("Tides\nTPXO9", [(RUN_START, RUN_END, "0.88", "black", "15 constituents, phases referenced to 1 Jan 2026")]),
    ]
    n = len(rows)
    for k, (name, bars) in enumerate(rows):
        y = n - 1 - k
        for t0, t1, col, tcol, text in bars:
            ax.barh(y, num(t1) - num(t0), left=num(t0), height=0.55, color=col, edgecolor="none")
            ax.text(num(t0 + (t1 - t0) / 2), y, text, ha="center", va="center", fontsize=9.5, color=tcol)
        if name == "Initial condition":
            ax.plot(num(RUN_START), y, marker="D", ms=10, color="black")
            ax.text(num(RUN_START) + 0.3, y, "CMEMS ocean state on 1 Nov 00 UTC (cold start)", va="center", fontsize=9.5)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=10.5)
    ax.axvline(num(FC_START), color=FC, lw=1.5, ls="--")
    ax.axvline(num(ATM_CYCLE), color="0.3", lw=1.2, ls=":")
    ax.text(num(FC_START) + 0.08, n - 0.45, "forecast starts\n10 Nov 00 UTC", color=FC, fontsize=9, va="bottom", ha="left")
    ax.text(num(ATM_CYCLE) - 0.08, n - 0.45, "newest ECMWF forecast\nused: 9 Nov 12 UTC", color="0.3", fontsize=9,
            va="bottom", ha="right")
    ax.set_ylim(-0.6, n - 0.45)
    ax.set_xlim(num(pd.Timestamp("2026-10-31")), num(pd.Timestamp("2026-11-16 06:00")))
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d\n%b"))
    ax.grid(axis="x", alpha=0.3)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    header(fig, "Moana ocean forecast run · November 2026",
           "What drives the model, and when (UTC). From 10 Nov on, every input is a forecast available on 9 Nov 2026.")
    footer(fig)
    save(fig, "00_overview_timeline.png")


def maps():
    avg = xr.open_dataset(run / "moana_avg.nc")
    times = avg.ocean_time.values
    print(f"moana_avg.nc: {len(times)} records", flush=True)
    L = limits(surface(avg, 0))
    for n, t in enumerate(times):
        t = pd.Timestamp(t)
        day = t.floor("D")
        sst, sss, ue, vn = surface(avg, n)
        fig, axes, caxes = three_panel_fig()
        map_panel(fig, axes[0], caxes[0], "temp", sst, L["temp"])
        map_panel(fig, axes[1], caxes[1], "salt", sss, L["salt"])
        map_panel(fig, axes[2], caxes[2], "speed", np.hypot(ue, vn), L["speed"])
        add_arrows(axes[2], ue, vn)
        H = header(fig, "Moana ocean forecast · sea surface, daily mean", f"Daily mean for {day:%a %d %b %Y} (00–24 UTC)", t)
        if day >= FC_START:
            k = (day - FC_START).days + 1
            H[2].set_text(f"forecast day {k}: lead time +{24 * (k - 1)} to +{24 * k} h from 10 Nov 00 UTC")
        else:
            H[2].set_text(f"spin-up day {(day - RUN_START).days + 1} of 9: model adjusting from the 1 Nov cold start")
        timeline(fig, TL3).set_xdata([num(t)] * 2)
        footer(fig)
        save(fig, f"daily_{day:%Y-%m-%d}.png")


def change():
    avg = xr.open_dataset(run / "moana_avg.nc")
    times = avg.ocean_time.values
    fc = [n for n, t in enumerate(times) if pd.Timestamp(t) >= FC_START]
    a, b = surface(avg, fc[0]), surface(avg, fc[-1])
    t0, t1 = pd.Timestamp(times[fc[0]]).floor("D"), pd.Timestamp(times[fc[-1]]).floor("D")
    fig = plt.figure(figsize=(14, 8.6))
    axes = [fig.add_axes([x, 0.20, 0.44, 0.62]) for x in (0.04, 0.53)]
    caxes = [fig.add_axes([x + 0.08, 0.155, 0.28, 0.02]) for x in (0.04, 0.53)]
    for ax, cax, d, key, lim, word in zip(axes, caxes, (b[0] - a[0], b[1] - a[1]), ("temp", "salt"), (1.5, 0.2),
                                          ("warmer", "saltier")):
        name, unit, _ = FIELDS[key]
        pc = ax.pcolormesh(lon, lat, d, shading="auto", cmap="RdBu_r", vmin=-lim, vmax=lim)
        style_map(ax)
        ax.set_title(f"Change in {name.lower()}")
        cb = fig.colorbar(pc, cax=cax, orientation="horizontal", extend="both")
        cb.set_label(f"{unit}  (red = {word} at the end of the forecast)", fontsize=10)
    H = header(fig, "Moana ocean forecast · predicted change over the 5 forecast days",
               f"Daily mean {t1:%a %d %b} minus daily mean {t0:%a %d %b %Y}", times[fc[-1]])
    H[2].set_text("forecast day 5 minus forecast day 1")
    timeline(fig, TL3)
    footer(fig)
    save(fig, "forecast_change.png")


def anim():
    his = xr.open_dataset(run / "moana_his.nc")
    times = his.ocean_time.values
    print(f"moana_his.nc: {len(times)} records, {pd.Timestamp(times[0])} -> {pd.Timestamp(times[-1])}", flush=True)
    s = surface(his, 0)
    L = limits(s)
    fig, axes, caxes = three_panel_fig()
    pcs = [map_panel(fig, axes[0], caxes[0], "temp", s[0], L["temp"]),
           map_panel(fig, axes[1], caxes[1], "salt", s[1], L["salt"]),
           map_panel(fig, axes[2], caxes[2], "speed", np.hypot(s[2], s[3]), L["speed"])]
    q = add_arrows(axes[2], s[2], s[3])
    H = header(fig, "Moana ocean forecast · sea surface, hourly", valid(times[0]), times[0])
    marker = timeline(fig, TL3)
    footer(fig)

    def update(n):
        sst, sss, ue, vn = surface(his, n)
        for pc, f in zip(pcs, (sst, sss, np.hypot(ue, vn))):
            pc.set_array(f.ravel())
        q.set_UVC(ue[ARROWS], vn[ARROWS])
        set_header(H, valid(times[n]), times[n])
        marker.set_xdata([num(times[n])] * 2)
        if n % 24 == 0:
            print("frame", n, "of", len(times), flush=True)

    write_animation(animation.FuncAnimation(fig, update, frames=len(times), blit=False), "surface_hourly", dpi=100)
    plt.close(fig)


def anim_single(var):
    his = xr.open_dataset(run / "moana_his.nc")
    times = his.ocean_time.values
    print(f"moana_his.nc: {len(times)} records", flush=True)
    get = lambda n: np.where(water, his[var].isel(ocean_time=n, s_rho=-1).values, np.nan)
    f0 = get(0)
    fig, ax, cax = single_fig()
    pc = map_panel(fig, ax, cax, var, f0, tuple(np.nanpercentile(f0, [1, 99])))
    ax.set_title("")
    H = header(fig, f"Moana ocean forecast · {FIELDS[var][0].lower()}", valid(times[0]), times[0])
    marker = timeline(fig, TL1)
    footer(fig)

    def update(n):
        pc.set_array(get(n).ravel())
        set_header(H, valid(times[n]), times[n])
        marker.set_xdata([num(times[n])] * 2)
        if n % 24 == 0:
            print("frame", n, "of", len(times), flush=True)

    write_animation(animation.FuncAnimation(fig, update, frames=len(times), blit=False), f"surface_{var}_hourly", dpi=110)
    plt.close(fig)


def cmems():
    his = xr.open_dataset(run / "moana_his.nc")
    th = pd.to_datetime(his.ocean_time.values)
    fig, ax = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.12, hspace=0.25)
    diffs = {}
    for axi, var in zip(ax, ("temp", "salt")):
        name, unit, _ = FIELDS[var]
        clm = xr.open_dataset(CLM[var], decode_times=False)
        tc = REF + pd.to_timedelta(clm[f"{var}_time"].values, unit="D")
        tt, bias, rms = [], [], []
        for k, t in enumerate(tc):
            if not th[0] <= t <= th[-1]:
                continue
            n = int(np.argmin(np.abs(th - t)))
            d = (his[var].isel(ocean_time=n, s_rho=-1).values - clm[var].isel({f"{var}_time": k, "s_rho": -1}).values)[water]
            tt.append(t); bias.append(np.nanmean(d)); rms.append(np.sqrt(np.nanmean(d ** 2)))
            if t in (FC_START, th[-1]):
                full = np.full(water.shape, np.nan); full[water] = d
                diffs[(var, t)] = full
        shade(axi)
        axi.plot(tt, rms, lw=2, color="black", label="RMS difference")
        axi.plot(tt, bias, lw=2, color="#e08a00", label="mean difference (bias)")
        axi.axhline(0, color="0.5", lw=0.8)
        axi.set_ylabel(unit)
        axi.set_title(f"{name}: ROMS minus CMEMS, whole domain")
    legend_with_phases(ax[0], ncol=4, fontsize=9, loc="upper left")
    header(fig, "Moana ROMS compared with CMEMS at the sea surface",
           "Every 6 h. CMEMS (analysis, then forecast) is the product the run is nudged toward: a consistency check, not observations.")
    footer(fig)
    save(fig, "model_minus_cmems_timeseries.png")

    fig = plt.figure(figsize=(14, 14))
    pos = {(0, 0): [0.05, 0.53, 0.42, 0.34], (0, 1): [0.53, 0.53, 0.42, 0.34],
           (1, 0): [0.05, 0.10, 0.42, 0.34], (1, 1): [0.53, 0.10, 0.42, 0.34]}
    for row, (var, lim) in enumerate((("temp", 2), ("salt", 0.3))):
        for col, (t, when) in enumerate(((FC_START, "forecast start"), (th[-1], "end of forecast, +120 h"))):
            d = diffs.get((var, t))
            if d is None:
                continue
            ax = fig.add_axes(pos[(row, col)])
            pc = ax.pcolormesh(lon, lat, d, shading="auto", cmap="RdBu_r", vmin=-lim, vmax=lim)
            style_map(ax)
            ax.set_title(f"{FIELDS[var][0]}\n{pd.Timestamp(t):%d %b %H:%M} UTC ({when})", fontsize=12)
            cb = fig.colorbar(pc, ax=ax, orientation="horizontal", fraction=0.04, pad=0.07, extend="both")
            cb.set_label(f"ROMS minus CMEMS ({FIELDS[var][1]})", fontsize=10)
    header(fig, "Where Moana ROMS and CMEMS differ at the sea surface",
           "At the start and at the end of the 5-day forecast. Red: ROMS warmer / saltier than CMEMS.")
    footer(fig)
    save(fig, "model_minus_cmems_maps.png")


def points():
    his = xr.open_dataset(run / "moana_his.nc")
    th = pd.to_datetime(his.ocean_time.values)
    fig, ax = plt.subplots(4, 1, figsize=(14, 15), sharex=True)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.08, hspace=0.3)
    for name, (lo, la) in GAUGES.items():
        j, i = nearest_water(lo, la)
        ax[0].plot(th, his.zeta.isel(eta_rho=j, xi_rho=i).values, lw=0.9, label=name)
    ax[0].set_ylabel("sea level (m)")
    ax[0].set_title("Sea level at LINZ tide gauges (tides + weather)")
    for name, (lo, la) in SST_STATIONS.items():
        j, i = nearest_water(lo, la)
        ax[1].plot(th, his.temp.isel(s_rho=-1, eta_rho=j, xi_rho=i).values, lw=1.5, label=name)
    ax[1].set_ylabel("°C")
    ax[1].set_title("Sea surface temperature at coastal stations")
    surf = his.isel(s_rho=-1)
    ax[2].plot(th, surf.temp.where(water_da).mean(dim=["eta_rho", "xi_rho"]).values, lw=2, color="#c0392b")
    ax[2].set_ylabel("°C")
    ax[2].set_title("Sea surface temperature, average over the whole domain")
    ax[3].plot(th, surf.salt.where(water_da).mean(dim=["eta_rho", "xi_rho"]).values, lw=2, color="#1f7a5a")
    ax[3].set_ylabel("PSU")
    ax[3].set_title("Sea surface salinity, average over the whole domain")
    for axi in ax:
        shade(axi)
    legend_with_phases(ax[0], ncol=6, fontsize=9, loc="upper left")
    legend_with_phases(ax[1], ncol=6, fontsize=9, loc="upper left")
    header(fig, "Moana ocean forecast · coastal and domain-wide time series",
           "Hourly, 1–15 Nov 2026 (UTC), model grid point nearest each site. Sites: LINZ gauges and coastal stations (Souza et al., 2023).")
    footer(fig)
    save(fig, "coastal_and_domain_timeseries.png")


def log():
    step = re.compile(r"^\s*(\d+)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$")
    cour = re.compile(r"^\s*\(\d+,\d+,\d+\)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$")
    rows, lines = [], open(run / "roms.log").read().splitlines()
    for a, b in zip(lines, lines[1:]):
        m, c = step.match(a), cour.match(b)
        if m and c:
            rows.append((pd.Timestamp(m.group(2)), float(m.group(3)), float(m.group(6)), float(c.group(3)), float(c.group(4))))
    df = pd.DataFrame(rows, columns=["time", "KE", "volume", "Cw", "max_speed"])
    print(f"roms.log: {len(df)} steps, {df.time.iloc[0]} -> {df.time.iloc[-1]}", flush=True)
    fig, ax = plt.subplots(4, 1, figsize=(14, 14), sharex=True)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.08, hspace=0.3)
    panels = [(df.KE, "kinetic energy", "Kinetic energy: grows after the cold start, should level off before the forecast"),
              ((df.volume / df.volume.iloc[0] - 1) * 1e6, "ppm", "Total water volume change: tides moving water through the open boundaries"),
              (df.max_speed, "m/s", "Fastest current anywhere in the domain (strong tidal flows)"),
              (df.Cw, "Courant number", "Largest vertical Courant number: high during the cold-start adjustment, then settles")]
    for axi, (y, unit, title) in zip(ax, panels):
        shade(axi)
        axi.plot(df.time, y, lw=1, color="black")
        axi.set_ylabel(unit)
        axi.set_title(title, fontsize=12)
    legend_with_phases(ax[0], fontsize=9, loc="lower right")
    header(fig, "Moana ROMS run health", f"Every model time step (100 s), {len(df)} steps, from roms.log")
    footer(fig)
    save(fig, "run_health_from_roms_log.png")


PARTS = {"overview": overview, "maps": maps, "change": change, "anim": anim,
         "anim_temp": lambda: anim_single("temp"), "anim_salt": lambda: anim_single("salt"),
         "cmems": cmems, "points": points, "log": log}
for name in (PARTS if part == "all" else [part]):
    try:
        PARTS[name]()
    except Exception as e:                              # one failed part should not stop the others
        print(f"PART {name} FAILED: {e!r}", flush=True)
        if part != "all":
            raise