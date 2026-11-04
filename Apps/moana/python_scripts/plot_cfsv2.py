#!/usr/bin/env python
"""Figures of the CFSv2 atmospheric forcing over the Moana domain.

Usage (moana_python environment, see env/moana_python.yml):

    python Apps/moana/python_scripts/plot_cfsv2.py [--out DIR]

Reads the CFSv2 files cut to the Moana box by scripts/subset_cfsv2.py
(Input/atmosphere/cfsv2_nz/<var>.cdas1.<YYYYMM>.nz.nc) and writes to --out
(default Apps/moana/Figures):

  moana_cfsv2_mean.{pdf,png}    2018 mean of the bulk-forcing fields
  moana_cfsv2_series.{pdf,png}  daily ocean-mean series for the run period,
                                and one week of hourly values at point P

These are the CFSv2 fields as stored, before conversion to ROMS bulk
forcing and before interpolation to the model grid; only units change
(K to °C, kg kg-1 to g kg-1, Pa to hPa, kg m-2 s-1 to mm). Averaged fluxes
(precipitation, shortwave, longwave) are stored as means over the first n
forecast hours (n = 1-6). The hourly values in the right-hand panels are
recovered with F_n = n A_n - (n - 1) A_(n-1), the step the bulk-forcing
conversion needs. "Ocean mean" is the cos(latitude)-weighted mean over
CFSv2 points whose nearest model cell is ocean.
"""

import argparse
from pathlib import Path

import cmocean
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

from plot_glorys_ic_bc import colorbar, map_axes, robust, save, tidy
from plot_grid import (APP, HALO, INK, INK2, MM, SLOT1, axes_mm, lat_label,
                       load_grid, lon_label, merc, panel_label)

NZ = Path("/projects/f_omg_1/moa/moana/Input/atmosphere/cfsv2_nz")
RUN = (np.datetime64("2017-10-01"), np.datetime64("2020-01-01"))  # end exclusive
SPINUP_END = np.datetime64("2018-01-01")
YEAR = "2018"                  # mean maps: first full year after spin-up
POINT = (172.0, -40.0)         # P: Tasman Sea, north-west of Farewell Spit
WEEK = (np.datetime64("2018-01-10"), np.datetime64("2018-01-17"))
SLOT2 = "#eb6834"              # dataviz categorical slot 2
WASH = "#f0efec"               # dataviz neutral gray, spin-up band
HOUR = np.timedelta64(1, "h")


# ------------------------------------------------------------- reading ---

def open_var(prefix, var):
    files = sorted(NZ.glob(f"{prefix}.cdas1.*.nz.nc"))
    if not files:
        raise SystemExit(f"no {prefix} files in {NZ}; run scripts/subset_cfsv2.py")
    ds = xr.open_mfdataset(files, combine="nested", concat_dim="time",
                           data_vars="minimal", coords="minimal",
                           compat="override", chunks={"time": 124})
    return ds[var]


def deaverage(da):
    """Hourly means from means over the first n forecast hours.

    The result at step n is the mean over [valid_time - 1 h, valid_time].
    """
    n = (da.step / HOUR).astype(int)
    total = da * n
    return total - total.shift(step=1, fill_value=0)


# Each field: how to read it, unit conversion, kind ("instant" or "avg").
def wind_speed():
    u, v = open_var("wnd10m", "u10"), open_var("wnd10m", "v10")
    return np.hypot(u, v)


FIELDS = {
    "wind": dict(read=wind_speed, kind="instant", scale=1, offset=0,
                 label="10 m wind speed", units="m s$^{-1}$"),
    "slp": dict(read=lambda: open_var("prmsl", "prmsl"), kind="instant",
                scale=0.01, offset=0, label="Sea-level pressure", units="hPa"),
    "t2m": dict(read=lambda: open_var("tmp2m", "t2m"), kind="instant",
                scale=1, offset=-273.15, label="2 m air temperature", units="°C"),
    "q2m": dict(read=lambda: open_var("q2m", "sh2"), kind="instant",
                scale=1000, offset=0, label="2 m specific humidity",
                units="g kg$^{-1}$"),
    "swnet": dict(read=lambda: open_var("dswsfc", "sdswrf") - open_var("uswsfc", "suswrf"),
                  kind="avg", scale=1, offset=0,
                  label="Net shortwave (down − up)", units="W m$^{-2}$"),
    "lwdown": dict(read=lambda: open_var("dlwsfc", "sdlwrf"), kind="avg",
                   scale=1, offset=0, label="Downward longwave",
                   units="W m$^{-2}$"),
    "rain": dict(read=lambda: open_var("prate", "prate"), kind="avg",
                 scale=86400, offset=0, label="Precipitation",
                 units="mm d$^{-1}$"),
}


def convert(da, f):
    return da * f["scale"] + f["offset"]


def ocean_weights(da, g):
    """cos(lat) on CFSv2 points whose nearest model cell is ocean."""
    lat, lon = da.latitude.values, da.longitude.values
    glon, glat = g["lon_rho"][0, :], g["lat_rho"][:, 0]
    i = np.abs(glon[None, :] - lon[:, None]).argmin(1)
    j = np.abs(glat[None, :] - lat[:, None]).argmin(1)
    inside = (((lat >= glat[0]) & (lat <= glat[-1]))[:, None]
              & ((lon >= glon[0]) & (lon <= glon[-1]))[None, :])
    w = np.cos(np.radians(lat))[:, None] * (g["ocean"][np.ix_(j, i)] & inside)
    return xr.DataArray(w, dims=("latitude", "longitude"),
                        coords={"latitude": lat, "longitude": lon})


def as_series(da):
    """A small (time, step) array as a pandas Series on valid_time."""
    da = da.compute()
    s = pd.Series(da.values.ravel(),
                  index=pd.DatetimeIndex(da.valid_time.values.ravel()))
    return s.sort_index()


def annual_mean(da, kind):
    """Mean over YEAR: hourly records valid in YEAR, or 0-6 h means of the
    cycles in YEAR (four of them tile each day exactly)."""
    if kind == "avg":
        da = da.sel(step=6 * HOUR, time=YEAR)
        return da.mean("time")
    da = da.sel(time=slice(f"{int(YEAR) - 1}-12-31T18", f"{YEAR}-12-31T18"))
    inyear = da.valid_time.dt.year == int(YEAR)
    return da.where(inyear).mean(("time", "step"))


def daily_ocean_mean(da, kind, w):
    m = (da * w).sum(("latitude", "longitude")) / w.sum()
    if kind == "avg":
        s = m.sel(step=6 * HOUR).compute()
        s = pd.Series(s.values, index=pd.DatetimeIndex(s.time.values))
    else:
        s = as_series(m)
    s = s.resample("1D").mean()
    return s[(s.index >= RUN[0]) & (s.index < RUN[1])]


def point_week(da, kind):
    p = da.sel(longitude=POINT[0], latitude=POINT[1], method="nearest")
    p = p.sel(time=slice(WEEK[0] - np.timedelta64(6, "h"), WEEK[1]))
    hourly = as_series(deaverage(p) if kind == "avg" else p)
    stored = as_series(p) if kind == "avg" else None
    keep = lambda s: s[(s.index > WEEK[0]) & (s.index <= WEEK[1])]
    return keep(hourly), None if stored is None else keep(stored)


# ------------------------------------------------------------- figures ---

def fig_mean(g, out):
    fig = plt.figure(figsize=(180 * MM, 180 * MM))
    w, gap, left = 50, 8, 12
    h = w * (g["y_vert"].max() - g["y_vert"].min()) / (
        g["lon_vert"].max() - g["lon_vert"].min())
    pos = [(left + c * (w + gap), b) for b in (108, 22) for c in range(3)]

    u = annual_mean(open_var("wnd10m", "u10"), "instant").compute()
    v = annual_mean(open_var("wnd10m", "v10"), "instant").compute()
    slp = convert(annual_mean(FIELDS["slp"]["read"](), "instant"), FIELDS["slp"]).compute()
    panels = [
        ("wind", cmocean.cm.speed, 1, "Wind and sea-level pressure"),
        ("t2m", cmocean.cm.thermal, 1, "Air temperature"),
        ("q2m", cmocean.cm.tempo, 0.5, "Specific humidity"),
        ("swnet", cmocean.cm.solar, 10, "Net shortwave radiation"),
        ("lwdown", cmocean.cm.matter, 10, "Downward longwave radiation"),
        ("rain", cmocean.cm.rain, 1, "Precipitation"),
    ]
    axs = []
    for k, ((x0, y0), (key, cmap, step, title)) in enumerate(zip(pos, panels)):
        f = FIELDS[key]
        field = convert(annual_mean(f["read"](), f["kind"]), f).compute()
        ax = axes_mm(fig, x0, y0, w, h)
        map_axes(ax, g, lat_labels=(k % 3 == 0))
        lo, hi = robust(field.values, step=step)
        if key == "rain":
            lo = 0
        pm = ax.pcolormesh(field.longitude, merc(field.latitude.values), field.values,
                           shading="nearest", cmap=cmap, norm=Normalize(lo, hi),
                           rasterized=True, zorder=1)
        colorbar(fig, pm, (x0, y0 - 13, w, 1.8), f"{f['label']} ({f['units']})")
        axs.append(ax)
        panel_label(ax, "abcdef"[k], x=-0.06, y=1.02)
        ax.text(0.0, 1.02, title, transform=ax.transAxes, fontsize=6.5,
                ha="left", va="bottom")

    ax = axs[0]
    cs = ax.contour(slp.longitude, merc(slp.latitude.values), slp.values,
                    levels=np.arange(980, 1040, 2), colors=INK, linewidths=0.35,
                    zorder=3)
    ax.clabel(cs, fontsize=4.5, fmt="%d")
    sk = 6  # every 6th CFSv2 point, about 1.2 deg
    q = ax.quiver(u.longitude[::sk], merc(u.latitude.values[::sk]),
                  u.values[::sk, ::sk], v.values[::sk, ::sk], color=INK,
                  scale=120, width=0.004, headwidth=3.5, zorder=4)
    ax.quiverkey(q, 0.06, 0.845, 5, "5 m s$^{-1}$", labelpos="E",
                 fontproperties={"size": 5.5}, color=INK)
    ax.text(0.02, 0.97, "arrows: mean wind\ncontours: pressure, 2 hPa",
            transform=ax.transAxes, fontsize=5.5, va="top", color=INK,
            path_effects=HALO, zorder=5)
    for ax in axs:
        ax.plot(POINT[0], merc(POINT[1]), "o", ms=3.5, mfc="white", mec=INK,
                mew=0.8, zorder=6)
    axs[0].text(POINT[0] + 0.5, merc(POINT[1]), "P", fontsize=6, va="center",
                color=INK, path_effects=HALO, zorder=6)
    fig.text(left / 180, 0.985, f"CFSv2 mean over {YEAR} (first year after "
             "spin-up), before conversion to ROMS forcing and interpolation "
             "to the model grid", fontsize=7, va="top")
    save(fig, out / "moana_cfsv2_mean")


def fig_series(g, out):
    keys = list(FIELDS)
    H = 222
    fig = plt.figure(figsize=(180 * MM, H * MM))
    xl, wl, xr_, wr = 20, 108, 140, 36
    hrow, pitch, top = 20, 27.5, H - 30
    w_cache = {}
    axes_l, axes_r = [], []
    for r, key in enumerate(keys):
        f = FIELDS[key]
        da = f["read"]()
        wkey = da.sizes["latitude"]
        if wkey not in w_cache:
            w_cache[wkey] = ocean_weights(da, g)
        daily = convert(daily_ocean_mean(da, f["kind"], w_cache[wkey]), f)
        hourly, stored = point_week(da, f["kind"])
        hourly, stored = convert(hourly, f), None if stored is None else convert(stored, f)
        y0 = top - hrow - r * pitch

        ax = axes_mm(fig, xl, y0, wl, hrow)
        ax.axvspan(RUN[0], SPINUP_END, color=WASH, lw=0, zorder=0)
        ax.plot(daily.index, daily.values, color=SLOT1, lw=0.5, zorder=2)
        roll = daily.rolling(30, center=True, min_periods=20).mean()
        ax.plot(roll.index, roll.values, color=INK, lw=0.9, zorder=3)
        ax.set_xlim(RUN[0], RUN[1])
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.set_ylabel(f["units"], fontsize=6)
        tidy(ax)
        if r < len(keys) - 1:
            ax.tick_params(labelbottom=False)
        panel_label(ax, "abcdefg"[r], x=-0.1, y=1.04)
        ax.text(0.0, 1.04, f["label"], transform=ax.transAxes, fontsize=6.5,
                ha="left", va="bottom")
        axes_l.append(ax)

        ax = axes_mm(fig, xr_, y0, wr, hrow)
        if stored is not None:
            ax.plot(stored.index, stored.values, color=SLOT2, lw=0.6,
                    drawstyle="steps-pre", zorder=2)
        ax.plot(hourly.index, hourly.values, color=SLOT1, lw=0.8,
                drawstyle="steps-pre" if f["kind"] == "avg" else "default",
                zorder=3)
        ax.set_xlim(WEEK[0], WEEK[1])
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%-d %b"))
        ax.set_ylabel(f["units"] if key != "rain" else "mm d$^{-1}$", fontsize=6)
        tidy(ax)
        if r < len(keys) - 1:
            ax.tick_params(labelbottom=False)
        axes_r.append(ax)

    axes_l[0].text(np.datetime64("2017-11-15"), 1.0, "spin-up",
                   transform=axes_l[0].get_xaxis_transform(), ha="center",
                   va="top", fontsize=5.5, color=INK2)
    head = top + 15
    fig.text(xl / 180, head / H, "Ocean mean, daily, 2017-10-01 to 2019-12-31",
             fontsize=7, va="bottom")
    fig.text(xr_ / 180, head / H,
             f"Point P ({lon_label(POINT[0])}, {lat_label(POINT[1])}), hourly,\n"
             f"{pd.Timestamp(WEEK[0]):%-d}–{pd.Timestamp(WEEK[1]):%-d %b %Y}",
             fontsize=7, va="bottom", linespacing=1.2)
    fig.legend(handles=[Line2D([], [], color=SLOT1, lw=0.8, label="daily mean"),
                        Line2D([], [], color=INK, lw=0.9, label="30-day running mean")],
               loc="lower left", bbox_to_anchor=(xl / 180, (head - 8) / H),
               ncol=2, frameon=False, fontsize=6, handlelength=1.8,
               borderaxespad=0, borderpad=0)
    fig.legend(handles=[Line2D([], [], color=SLOT1, lw=0.8, label="hourly"),
                        Line2D([], [], color=SLOT2, lw=0.6,
                               label="as stored: mean over first n h")],
               loc="lower left", bbox_to_anchor=(xr_ / 180, (head - 9) / H),
               ncol=1, frameon=False, fontsize=5.5, handlelength=1.8,
               borderaxespad=0, borderpad=0, labelspacing=0.2)
    save(fig, out / "moana_cfsv2_series")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", type=Path, default=APP / "Figures")
    args = p.parse_args()
    g = load_grid(APP / "Input" / "moana_grid.nc")
    j = np.abs(g["lat_rho"][:, 0] - POINT[1]).argmin()
    i = np.abs(g["lon_rho"][0, :] - POINT[0]).argmin()
    assert g["ocean"][j, i], "point P is on land in the model mask"
    fig_mean(g, args.out)
    fig_series(g, args.out)


if __name__ == "__main__":
    main()
