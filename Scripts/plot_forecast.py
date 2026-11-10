#!/usr/bin/env python3
"""
Plots and animations for a Moana ROMS forecast run (no data assimilation).

  python Scripts/plot_forecast.py <run_dir> <part> [<out_dir>]

part:
  maps    daily maps of surface temp, salt and speed (moana_avg.nc), and the forecast change
  anim    hourly animation of surface temp, salt and speed (moana_his.nc), mp4 or gif
  cmems   model minus CMEMS (the climatology files the run is nudged toward): bias/RMS and maps
  points  hourly sea level at tide gauges, SST at coastal stations, domain-mean SST and SSS
  log     kinetic energy, volume change and max speed from roms.log
  all     everything above, one after the other
Output: <out_dir> (default <run_dir>/plots). Times from FC_START on are labelled "forecast".
"""
import sys
import re
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")                                   # no screen on a compute node
import matplotlib.pyplot as plt
from matplotlib import animation

GRID = "/projects/f_omg_1/moa/moana/grid/moana_grid_N50.nc"
CLM = {"temp": "/projects/f_omg_1/moa/moana/oceanum_input/climatology/roms_ready_nov26/clm_temp_2026-10-31_2026-11-16.nc",
       "salt": "/projects/f_omg_1/moa/moana/oceanum_input/climatology/roms_ready_nov26/clm_salt_2026-10-31_2026-11-16.nc"}
REF = pd.Timestamp("2026-01-01")                        # TIME_REF
FC_START = pd.Timestamp("2026-11-10 00:00")             # first forecast day
# coastal locations from Souza et al. (2023), Tables 2 and 3: name -> (lon, lat)
GAUGES = {"North Cape": (173.05, -34.42), "Auckland": (174.78, -36.83),
          "Wellington": (174.78, -41.28), "Port Chalmers": (170.65, -45.82)}
SST_STATIONS = {"Leigh": (174.80, -36.27), "Moturiki": (176.18, -37.63),
                "Evans Bay": (174.80, -41.30), "Portobello": (170.65, -45.83)}

run = Path(sys.argv[1])
part = sys.argv[2]
out = Path(sys.argv[3]) if len(sys.argv) > 3 else run / "plots"
out.mkdir(parents=True, exist_ok=True)

g = xr.open_dataset(GRID)
lon = g.lon_rho.values % 360                            # domain crosses 180E, so plot in 0-360
lat = g.lat_rho.values
water = g.mask_rho.values == 1
water_da = xr.DataArray(water, dims=("eta_rho", "xi_rho"))
ASPECT = 1 / np.cos(np.deg2rad(-41))                    # roughly equal distances in x and y
PANELS = [("surface temperature (°C)", "RdYlBu_r"), ("surface salinity (PSU)", "viridis"),
          ("surface current speed (m/s)", "magma")]


def label(t):
    t = pd.Timestamp(t)
    return f"{t:%Y-%m-%d %H:%M} UTC ({'forecast' if t >= FC_START else 'spin-up'})"


def mark_forecast(ax):
    ax.axvline(FC_START, color="r", ls="--", lw=1, label="forecast start (10 Nov)")


def nearest_water(lo, la):
    d = np.where(water, (lon - lo % 360) ** 2 + (lat - la) ** 2, np.inf)
    return np.unravel_index(np.argmin(d), d.shape)


def surface(ds, n):
    """Surface temp, salt and current speed of record n; land set to NaN."""
    r = ds.isel(ocean_time=n, s_rho=-1)
    sst = np.where(water, r.temp.values, np.nan)
    sss = np.where(water, r.salt.values, np.nan)
    if "u_eastward" in r:                               # history file: east/north currents on rho points
        spd = np.hypot(r.u_eastward.values, r.v_northward.values).astype(float)
    else:                                               # averages file: u, v on the staggered grid
        u, v = r.u.values, r.v.values
        spd = np.full(sst.shape, np.nan)
        spd[1:-1, 1:-1] = np.hypot(0.5 * (u[1:-1, :-1] + u[1:-1, 1:]), 0.5 * (v[:-1, 1:-1] + v[1:, 1:-1]))
    spd[~water] = np.nan
    return sst, sss, spd


def limits(fields):
    sst, sss, spd = fields
    return [np.nanpercentile(sst, [1, 99]), np.nanpercentile(sss, [1, 99]), (0, np.nanpercentile(spd, 99))]


def three_panels(fields, lims):
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.5), constrained_layout=True)
    pcs = []
    for axi, f, (title, cmap), (lo, hi) in zip(ax, fields, PANELS, lims):
        pc = axi.pcolormesh(lon, lat, f, shading="auto", cmap=cmap, vmin=lo, vmax=hi)
        fig.colorbar(pc, ax=axi, shrink=0.9)
        axi.set_title(title)
        axi.set_aspect(ASPECT)
        pcs.append(pc)
    return fig, pcs


def save(fig, name):
    fig.savefig(out / name, dpi=100)
    plt.close(fig)
    print("saved", out / name)


# ------------------------------------------------------------------ parts
def maps():
    avg = xr.open_dataset(run / "moana_avg.nc")
    times = avg.ocean_time.values
    print(f"moana_avg.nc: {len(times)} records")
    lims = limits(surface(avg, 0))
    for n, t in enumerate(times):
        fig, _ = three_panels(surface(avg, n), lims)
        fig.suptitle("Moana ROMS forecast run, daily mean " + label(t))
        save(fig, f"daily_{pd.Timestamp(t):%Y-%m-%d}.png")
    fc = [n for n, t in enumerate(times) if pd.Timestamp(t) >= FC_START]
    a, b = surface(avg, fc[0]), surface(avg, fc[-1])
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)
    for axi, d, title, lim in zip(ax, (b[0] - a[0], b[1] - a[1]), ("temperature change (°C)", "salinity change (PSU)"), (2, 0.3)):
        pc = axi.pcolormesh(lon, lat, d, shading="auto", cmap="RdBu_r", vmin=-lim, vmax=lim)
        fig.colorbar(pc, ax=axi, shrink=0.9)
        axi.set_title("surface " + title)
        axi.set_aspect(ASPECT)
    fig.suptitle(f"Forecast change: daily mean {pd.Timestamp(times[fc[-1]]):%d %b} minus {pd.Timestamp(times[fc[0]]):%d %b}")
    save(fig, "forecast_change.png")


def anim():
    his = xr.open_dataset(run / "moana_his.nc")
    times = his.ocean_time.values
    print(f"moana_his.nc: {len(times)} records, {pd.Timestamp(times[0])} -> {pd.Timestamp(times[-1])}")
    first = surface(his, 0)
    fig, pcs = three_panels(first, limits(first))
    title = fig.suptitle("Moana ROMS forecast run, hourly " + label(times[0]))

    def update(n):
        for pc, f in zip(pcs, surface(his, n)):
            pc.set_array(f.ravel())
        title.set_text("Moana ROMS forecast run, hourly " + label(times[n]))
        if n % 24 == 0:
            print("frame", n, "of", len(times), flush=True)
        return pcs + [title]

    a = animation.FuncAnimation(fig, update, frames=len(times), blit=False)
    if animation.writers.is_available("ffmpeg"):
        name = out / "surface_hourly.mp4"
        a.save(name, writer=animation.FFMpegWriter(fps=12, bitrate=4000), dpi=90)
    else:
        name = out / "surface_hourly.gif"
        a.save(name, writer=animation.PillowWriter(fps=12), dpi=60)
    plt.close(fig)
    print("saved", name)


def cmems():
    his = xr.open_dataset(run / "moana_his.nc")
    th = pd.to_datetime(his.ocean_time.values)
    fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True, constrained_layout=True)
    diffs = {}
    for axi, var, unit in zip(ax, ("temp", "salt"), ("°C", "PSU")):
        clm = xr.open_dataset(CLM[var], decode_times=False)
        tc = REF + pd.to_timedelta(clm[f"{var}_time"].values, unit="D")
        keep = [k for k, t in enumerate(tc) if th[0] <= t <= th[-1]]
        tt, bias, rms = [], [], []
        for k in keep:
            n = int(np.argmin(np.abs(th - tc[k])))
            d = (his[var].isel(ocean_time=n, s_rho=-1).values - clm[var].isel({f"{var}_time": k, "s_rho": -1}).values)[water]
            tt.append(tc[k]); bias.append(np.nanmean(d)); rms.append(np.sqrt(np.nanmean(d ** 2)))
            if tc[k] in (FC_START, th[-1]):
                full = np.full(water.shape, np.nan); full[water] = d
                diffs[(var, tc[k])] = full
        axi.plot(tt, rms, label="RMS difference")
        axi.plot(tt, bias, label="mean difference (bias)")
        axi.axhline(0, color="k", lw=0.5)
        mark_forecast(axi)
        axi.set_ylabel(f"surface {var} ({unit})")
        axi.grid(alpha=0.3)
        axi.legend()
    fig.suptitle("Moana ROMS minus CMEMS (analysis, then forecast) at the surface, every 6 h\n"
                 "CMEMS = the climatology the run is nudged toward, not observations")
    save(fig, "model_minus_cmems_timeseries.png")

    fig, ax = plt.subplots(2, 2, figsize=(13, 10), constrained_layout=True)
    for row, var, lim in ((0, "temp", 2), (1, "salt", 0.3)):
        for col, t in enumerate((FC_START, th[-1])):
            d = diffs.get((var, t))
            if d is None:
                continue
            pc = ax[row, col].pcolormesh(lon, lat, d, shading="auto", cmap="RdBu_r", vmin=-lim, vmax=lim)
            fig.colorbar(pc, ax=ax[row, col], shrink=0.9)
            ax[row, col].set_title(f"surface {var}, ROMS minus CMEMS, {label(t)}")
            ax[row, col].set_aspect(ASPECT)
    save(fig, "model_minus_cmems_maps.png")


def points():
    his = xr.open_dataset(run / "moana_his.nc")
    th = pd.to_datetime(his.ocean_time.values)
    fig, ax = plt.subplots(4, 1, figsize=(13, 13), sharex=True, constrained_layout=True)
    for name, (lo, la) in GAUGES.items():
        j, i = nearest_water(lo, la)
        ax[0].plot(th, his.zeta.isel(eta_rho=j, xi_rho=i).values, lw=0.8, label=name)
    ax[0].set_ylabel("sea level (m)")
    ax[0].set_title("Sea level at the grid point nearest each LINZ tide gauge (tides + weather)")
    for name, (lo, la) in SST_STATIONS.items():
        j, i = nearest_water(lo, la)
        ax[1].plot(th, his.temp.isel(s_rho=-1, eta_rho=j, xi_rho=i).values, label=name)
    ax[1].set_ylabel("SST (°C)")
    ax[1].set_title("Surface temperature at the grid point nearest each coastal station")
    surf = his.isel(s_rho=-1)
    ax[2].plot(th, surf.temp.where(water_da).mean(dim=["eta_rho", "xi_rho"]).values)
    ax[2].set_ylabel("domain-mean SST (°C)")
    ax[3].plot(th, surf.salt.where(water_da).mean(dim=["eta_rho", "xi_rho"]).values)
    ax[3].set_ylabel("domain-mean SSS (PSU)")
    for axi in ax:
        mark_forecast(axi)
        axi.grid(alpha=0.3)
    ax[0].legend(ncol=5, fontsize=8)
    ax[1].legend(ncol=5, fontsize=8)
    fig.suptitle(f"Moana ROMS forecast run, hourly, {th[0]:%d %b} to {th[-1]:%d %b %Y}")
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
    print(f"roms.log: {len(df)} steps, {df.time.iloc[0]} -> {df.time.iloc[-1]}")
    fig, ax = plt.subplots(4, 1, figsize=(12, 11), sharex=True, constrained_layout=True)
    ax[0].plot(df.time, df.KE); ax[0].set_ylabel("kinetic energy")
    ax[1].plot(df.time, (df.volume / df.volume.iloc[0] - 1) * 1e6); ax[1].set_ylabel("volume change (ppm)")
    ax[2].plot(df.time, df.max_speed); ax[2].set_ylabel("max speed (m/s)")
    ax[3].plot(df.time, df.Cw); ax[3].set_ylabel("max vertical Courant")
    for axi in ax:
        mark_forecast(axi)
        axi.grid(alpha=0.3)
    fig.suptitle("Moana ROMS forecast run: model health from roms.log (every time step)")
    save(fig, "run_health_from_roms_log.png")

def anim_single(var):
    """Full-size hourly animation of one surface field: var = 'temp' or 'salt'."""
    his = xr.open_dataset(run / "moana_his.nc")
    times = his.ocean_time.values
    name_units, cmap = {"temp": ("surface temperature (°C)", "RdYlBu_r"),
                        "salt": ("surface salinity (PSU)", "viridis")}[var]
    get = lambda n: np.where(water, his[var].isel(ocean_time=n, s_rho=-1).values, np.nan)
    f0 = get(0)
    lo, hi = np.nanpercentile(f0, [1, 99])
    fig, ax = plt.subplots(figsize=(9, 8), constrained_layout=True)
    pc = ax.pcolormesh(lon, lat, f0, shading="auto", cmap=cmap, vmin=lo, vmax=hi)
    fig.colorbar(pc, ax=ax, shrink=0.85, label=name_units)
    ax.set_aspect(ASPECT)
    ax.set_xlabel("longitude (°E)")
    ax.set_ylabel("latitude (°N)")
    title = ax.set_title(f"Moana ROMS, {name_units}\n" + label(times[0]))

    def update(n):
        pc.set_array(get(n).ravel())
        title.set_text(f"Moana ROMS, {name_units}\n" + label(times[n]))
        if n % 24 == 0:
            print("frame", n, "of", len(times), flush=True)
        return [pc, title]

    a = animation.FuncAnimation(fig, update, frames=len(times), blit=False)
    if animation.writers.is_available("ffmpeg"):
        name = out / f"surface_{var}_hourly.mp4"
        a.save(name, writer=animation.FFMpegWriter(fps=12, bitrate=4000), dpi=100)
    else:
        name = out / f"surface_{var}_hourly.gif"
        a.save(name, writer=animation.PillowWriter(fps=12), dpi=70)
    plt.close(fig)
    print("saved", name)


PARTS = {"maps": maps, "anim": anim, "cmems": cmems, "points": points, "log": log}
for name in (PARTS if part == "all" else [part]):
    try:
        PARTS[name]()
    except Exception as e:                              # one failed part should not stop the others
        print(f"PART {name} FAILED: {e!r}")
        if part != "all":
            raise
