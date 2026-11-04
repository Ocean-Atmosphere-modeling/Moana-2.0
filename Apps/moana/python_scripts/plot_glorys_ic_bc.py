#!/usr/bin/env python
"""Figures of the GLORYS12v1 initial and boundary conditions for Moana.

Usage (moana_python environment, see env/moana_python.yml):

    python Apps/moana/python_scripts/plot_glorys_ic_bc.py [--out DIR]

Reads GLORYS files made by scripts/fetch_glorys.py:
  Input/initial/glorys12_20171001_20171001.nc        whole box, one day
  Input/boundary/glorys12_<W|E|S|N>_surf_20171001_20191231.nc  edge strips
and writes moana_glorys_ic.{pdf,png} and moana_glorys_bc.{pdf,png} to --out
(default Apps/moana/Figures).

These are the GLORYS fields themselves, not yet interpolated to the
model grid. Map frames are the model domain (its four open edges).

Initial condition (2017-10-01): sea surface temperature, salinity, surface
current speed with sea-level contours, and a temperature section along 40 S.
Boundary condition: the four open edges unwrapped clockwise from the
south-west corner (west edge northward, north edge eastward, east edge
southward, south edge westward); temperature and flow across the edge on
2017-10-01, and sea surface temperature along the edges for the whole run.
"""

import argparse
from pathlib import Path

import cmocean
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import Normalize, TwoSlopeNorm

from plot_grid import (APP, HALO, INK, INK2, LAND, MM, axes_mm, lat_label,
                       load_grid, merc, panel_label, set_lat_ticks,
                       set_lon_ticks)

INPUT = Path("/projects/f_omg_1/moa/moana/Input")
IC_FILE = INPUT / "initial" / "glorys12_20171001_20171001.nc"
EDGE_FILE = str(INPUT / "boundary" / "glorys12_{}_surf_20171001_20191231.nc")
SECTION_LAT = -40.0
R_EARTH = 6371.0  # km
EDGE_NAMES = ("West", "North", "East", "South")


def open_glorys(path):
    """GLORYS file with longitudes 0-360, so the box crossing 180 is one
    piece."""
    ds = xr.open_dataset(path)
    return ds.assign_coords(longitude=ds.longitude % 360).sortby("longitude")


def depth_axis(ax, dmax):
    """Square-root depth axis, as in the grid figure's section panel."""
    ax.set_yscale("function",
                  functions=(lambda d: np.sqrt(np.clip(d, 0, None)), np.square))
    ax.set_ylim(dmax, 0)
    ticks = [t for t in (0, 50, 200, 500, 1000, 2000, 4000) if t <= dmax]
    ax.set_yticks(ticks)
    ax.set_ylabel("Depth (m)")


def colorbar(fig, mappable, rect, label, ticks=None, orientation="horizontal"):
    cax = axes_mm(fig, *rect)
    cb = fig.colorbar(mappable, cax=cax, orientation=orientation, ticks=ticks)
    cb.set_label(label, fontsize=6)
    cb.ax.tick_params(labelsize=5.5, length=2, width=0.4)
    cb.outline.set_linewidth(0.4)
    return cb


def tidy(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ------------------------------------------------------------ boundary ---

def edges_of(g):
    """Model open-edge positions (rho-points) and edge lengths (km)."""
    lon0, lon1 = float(g["lon_rho"][0, 0]), float(g["lon_rho"][0, -1])
    lat0, lat1 = float(g["lat_rho"][0, 0]), float(g["lat_rho"][-1, 0])
    deg = np.pi / 180 * R_EARTH
    lengths = (deg * (lat1 - lat0), deg * np.cos(np.radians(lat1)) * (lon1 - lon0),
               deg * (lat1 - lat0), deg * np.cos(np.radians(lat0)) * (lon1 - lon0))
    return (lon0, lon1, lat0, lat1), np.cumsum((0,) + lengths)


def perimeter(sources, g):
    """GLORYS along the open edges, clockwise from the SW corner.

    sources: dict edge -> dataset (one dataset for all edges is fine).
    Returns a dataset along dimension "p" with variables as in the sources
    plus "inflow" (velocity across the edge, positive into the domain) and
    the coordinate "dist" (km along the perimeter).
    """
    (lon0, lon1, lat0, lat1), start = edges_of(g)
    deg = np.pi / 180 * R_EARTH
    parts = []
    for k, edge in enumerate("WNES"):
        ds = sources[edge]
        if edge in "WE":
            s = ds.sel(longitude=lon0 if edge == "W" else lon1, method="nearest")
            s = s.sel(latitude=slice(lat0, lat1))
            if edge == "E":
                s = s.isel(latitude=slice(None, None, -1))
            along = s.latitude.values
            d = deg * (along - lat0 if edge == "W" else lat1 - along)
            inflow = s.uo if edge == "W" else -s.uo
            s = s.assign(inflow=inflow).drop_vars("longitude")
            s = s.rename(latitude="p")
        else:
            s = ds.sel(latitude=lat1 if edge == "N" else lat0, method="nearest")
            s = s.sel(longitude=slice(lon0, lon1))
            if edge == "S":
                s = s.isel(longitude=slice(None, None, -1))
            along = s.longitude.values
            coslat = np.cos(np.radians(lat1 if edge == "N" else lat0))
            d = deg * coslat * (along - lon0 if edge == "N" else lon1 - along)
            inflow = -s.vo if edge == "N" else s.vo
            s = s.assign(inflow=inflow).drop_vars("latitude")
            s = s.rename(longitude="p")
        s = s.drop_vars("p").assign_coords(dist=("p", start[k] + d))
        parts.append(s)
    return xr.concat(parts, dim="p", coords="minimal", compat="override")


def mark_corners(ax, g, label_y=None, labels=True):
    _, start = edges_of(g)
    for x in start[1:-1]:
        ax.axvline(x, color=INK, lw=0.5, zorder=4)
    if labels:
        for k, name in enumerate(EDGE_NAMES):
            ax.text((start[k] + start[k + 1]) / 2, 1.02, name,
                    transform=ax.get_xaxis_transform(), ha="center",
                    va="bottom", fontsize=6.5)
    ax.set_xlim(0, start[-1])


# ----------------------------------------------------------------- maps ---

def map_axes(ax, g, lat_labels=True):
    xv, yv = g["lon_vert"], g["y_vert"]
    ax.set_facecolor(LAND)  # GLORYS land is NaN
    ax.contour(g["lon_rho"], g["y_rho"], g["mask_rho"], levels=[0.5],
               colors=INK, linewidths=0.3, zorder=3)
    ax.set_xlim(xv.min(), xv.max())
    ax.set_ylim(yv.min(), yv.max())
    ax.set_aspect("equal")
    set_lon_ticks(ax, [165, 170, 175, 180])
    set_lat_ticks(ax, [-50, -45, -40, -35], labels=lat_labels)


def mesh(ax, ds, field, **kw):
    lon, lat = ds.longitude.values, ds.latitude.values
    return ax.pcolormesh(lon, merc(lat), field, shading="nearest",
                         rasterized=True, **kw)


def robust(a, lo=2, hi=98, step=0.5):
    v0, v1 = np.nanpercentile(a, [lo, hi])
    return np.floor(v0 / step) * step, np.ceil(v1 / step) * step


def fig_ic(ds, g, out):
    sur = ds.isel(time=0, depth=0)
    fig = plt.figure(figsize=(180 * MM, 142 * MM))
    w, gap, left, bottom = 50, 8, 12, 72
    h = w * (g["y_vert"].max() - g["y_vert"].min()) / (
        g["lon_vert"].max() - g["lon_vert"].min())
    axs = [axes_mm(fig, left + k * (w + gap), bottom, w, h) for k in range(3)]

    t0, t1 = robust(sur.thetao.values, step=1)
    s0, s1 = robust(sur.so.values, step=0.1)
    speed = np.hypot(sur.uo, sur.vo)
    panels = (
        (sur.thetao, cmocean.cm.thermal, Normalize(t0, t1), "SST (°C)"),
        (sur.so, cmocean.cm.haline, Normalize(s0, s1), "SSS (g kg$^{-1}$)"),
        (speed, cmocean.cm.speed, Normalize(0, 0.6), "Surface current (m s$^{-1}$)"),
    )
    for k, (ax, (field, cmap, norm, label)) in enumerate(zip(axs, panels)):
        map_axes(ax, g, lat_labels=(k == 0))
        pm = mesh(ax, sur, field.values, cmap=cmap, norm=norm)
        colorbar(fig, pm, (left + k * (w + gap), bottom - 13, w, 1.8), label)
    cs = axs[2].contour(sur.longitude, merc(sur.latitude.values), sur.zos,
                        levels=np.arange(-1.6, 1.61, 0.2), colors=INK,
                        linewidths=0.35)
    axs[2].clabel(cs, fontsize=4.5, fmt=lambda v: f"{abs(v) if abs(v) < 1e-9 else v:.1f}")
    axs[2].text(0.02, 0.02, "contours: sea level, 0.2 m (dashed < 0)",
                transform=axs[2].transAxes, fontsize=5.5, color=INK,
                path_effects=HALO)
    axs[0].axhline(merc(SECTION_LAT), color=INK, lw=0.8, ls=(0, (3, 1.5)))
    axs[0].text(161.6, merc(SECTION_LAT) + 0.3, "d", fontsize=7,
                fontweight="bold", color=INK, path_effects=HALO)

    sec = ds.isel(time=0).thetao.sel(latitude=SECTION_LAT, method="nearest")
    sec = sec.sel(longitude=slice(g["lon_vert"].min(), g["lon_vert"].max()))
    ax = axes_mm(fig, left, 12, 150, 34)
    ax.set_facecolor(LAND)
    pm = ax.pcolormesh(sec.longitude, sec.depth, sec.values, shading="nearest",
                       cmap=cmocean.cm.thermal, norm=Normalize(0, t1),
                       rasterized=True)
    depth_axis(ax, float(ds.depth.max()))
    ax.set_xlim(g["lon_vert"].min(), g["lon_vert"].max())
    set_lon_ticks(ax, [165, 170, 175, 180])
    tidy(ax)
    colorbar(fig, pm, (left + 152, 12, 1.8, 34), "Temperature (°C)",
             orientation="vertical")
    axs.append(ax)

    titles = ("Sea surface temperature", "Sea surface salinity",
              "Surface current and sea level",
              f"Temperature along {lat_label(SECTION_LAT)}")
    for ax, letter, title in zip(axs, "abcd", titles):
        panel_label(ax, letter, x=-0.06 if ax is not axs[3] else -0.03, y=1.02)
        ax.text(0.0, 1.02, title, transform=ax.transAxes, fontsize=6.5,
                ha="left", va="bottom")
    fig.text(left / 180, 0.985, "GLORYS12v1 on 2017-10-01 (model start), "
             "before interpolation to the model grid", fontsize=7, va="top")
    save(fig, out / "moana_glorys_ic")


def fig_bc(ic, edges, g, out):
    p0 = perimeter({e: ic for e in "WNES"}, g).isel(time=0)
    pt = perimeter(edges, g).isel(depth=0)
    (lon0, lon1, lat0, lat1), start = edges_of(g)

    fig = plt.figure(figsize=(180 * MM, 178 * MM))
    # a: where the perimeter runs.
    ax_a = axes_mm(fig, 12, 116, 44, 44 * (g["y_vert"].max() - g["y_vert"].min())
                   / (g["lon_vert"].max() - g["lon_vert"].min()))
    land = np.ma.masked_where(g["ocean"], np.ones_like(g["h"]))
    ax_a.pcolormesh(g["lon_vert"], g["y_vert"], land, cmap=plt.matplotlib.colors
                    .ListedColormap([LAND]), rasterized=True)
    ax_a.set_xlim(g["lon_vert"].min() - 0.6, g["lon_vert"].max() + 0.6)
    ax_a.set_ylim(g["y_vert"].min() - 3.0, g["y_vert"].max() + 3.0)
    ax_a.set_aspect("equal")
    ax_a.axis("off")
    ring_lon = [lon0, lon0, lon1, lon1, lon0]
    ring_lat = [lat0, lat1, lat1, lat0, lat0]
    ax_a.plot(ring_lon, merc(np.array(ring_lat)), color=INK, lw=1.4)
    ax_a.annotate("", xy=(lon0, merc(lat0 + 6)), xytext=(lon0, merc(lat0 + 1)),
                  arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8))
    ax_a.text(lon0 - 0.3, merc(lat0), "0 km", ha="right", va="center",
              fontsize=5.5)
    for k, (name, x, y, ha, va) in enumerate((
            ("West", lon0 - 0.5, merc((lat0 + lat1) / 2), "right", "center"),
            ("North", (lon0 + lon1) / 2, merc(lat1) + 0.4, "center", "bottom"),
            ("East", lon1 + 0.5, merc((lat0 + lat1) / 2), "left", "center"),
            ("South", (lon0 + lon1) / 2, merc(lat0) - 0.4, "center", "top"))):
        ax_a.text(x, y, f"{name}\n{start[k]:.0f}–{start[k + 1]:.0f} km",
                  ha=ha, va=va, fontsize=5.5, linespacing=1.1,
                  rotation=90 if name in ("West", "East") else 0)

    # b, c: sections around the perimeter on 2017-10-01.
    x0, wsec = 72, 92
    dmax = float(ic.depth.max())
    ax_b = axes_mm(fig, x0, 136, wsec, 26)
    ax_b.set_facecolor(LAND)
    _, t1 = robust(p0.thetao.isel(depth=0).values, step=1)
    pm_t = ax_b.pcolormesh(p0.dist, p0.depth, p0.thetao.transpose("depth", "p").values,
                           shading="nearest", cmap=cmocean.cm.thermal,
                           norm=Normalize(0, t1), rasterized=True)
    depth_axis(ax_b, dmax)
    mark_corners(ax_b, g)
    ax_b.tick_params(labelbottom=False)
    colorbar(fig, pm_t, (x0 + wsec + 2, 136, 1.8, 26), "Temperature (°C)",
             orientation="vertical")

    ax_c = axes_mm(fig, x0, 104, wsec, 26)
    ax_c.set_facecolor(LAND)
    pm_v = ax_c.pcolormesh(p0.dist, p0.depth, p0.inflow.transpose("depth", "p").values,
                           shading="nearest", cmap=cmocean.cm.balance,
                           norm=TwoSlopeNorm(0, -0.3, 0.3), rasterized=True)
    depth_axis(ax_c, dmax)
    mark_corners(ax_c, g, labels=False)
    ax_c.set_xlabel("Distance along the open boundary, clockwise from the "
                    "south-west corner (km)")
    cb = colorbar(fig, pm_v, (x0 + wsec + 2, 104, 1.8, 26),
                  "Flow across edge (m s$^{-1}$)\n← out    in →",
                  orientation="vertical", ticks=[-0.3, 0, 0.3])
    for ax in (ax_b, ax_c):
        tidy(ax)

    # d: SST along the perimeter through the run.
    ax_d = axes_mm(fig, 22, 14, 142, 70)
    sst = pt.thetao.transpose("time", "p")
    s0, s1 = robust(sst.values, step=1)
    pm_s = ax_d.pcolormesh(pt.dist, pt.time, sst.values, shading="nearest",
                           cmap=cmocean.cm.thermal, norm=Normalize(s0, s1),
                           rasterized=True)
    mark_corners(ax_d, g)
    ax_d.yaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    ax_d.yaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax_d.set_ylim(pt.time.values[0], pt.time.values[-1])
    ax_d.set_xlabel("Distance along the open boundary, clockwise from the "
                    "south-west corner (km)")
    tidy(ax_d)
    colorbar(fig, pm_s, (22 + 144, 14, 1.8, 70), "Sea surface temperature (°C)",
             orientation="vertical")
    spin = (np.datetime64("2017-10-01"), np.datetime64("2018-01-01"))
    ax_d.axhspan(*spin, xmin=0, xmax=1, fc="none", ec=INK, lw=0.6, ls=(0, (3, 1.5)))
    ax_d.text(start[-1] * 0.995, spin[0] + np.timedelta64(45, "D"),
              "spin-up", ha="right", va="center", fontsize=6, color=INK,
              path_effects=HALO)

    for ax, letter, title, x in (
            (ax_a, "a", "Open boundary of the model", -0.02),
            (ax_b, "b", "Temperature on 2017-10-01", -0.1),
            (ax_c, "c", "Flow across the boundary on 2017-10-01", -0.1),
            (ax_d, "d", "Sea surface temperature at the boundary, "
             "2017-10-01 to 2019-12-31", -0.08)):
        y = 1.12 if ax is ax_b else 1.07 if ax is ax_d else 1.02
        panel_label(ax, letter, x=x, y=y)
        ax.text(0.0, y, title,
                transform=ax.transAxes, fontsize=6.5, ha="left", va="bottom")
    fig.text(12 / 180, 0.985, "GLORYS12v1 at the model's open edges "
             "(nearest GLORYS point; before interpolation to the model grid)",
             fontsize=7, va="top")
    save(fig, out / "moana_glorys_bc")


def save(fig, stem):
    for ext in ("pdf", "png"):
        fig.savefig(f"{stem}.{ext}", metadata={"Title": stem.name})
        print(f"wrote   {stem}.{ext}")
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", type=Path, default=APP / "Figures")
    args = p.parse_args()
    g = load_grid(APP / "Input" / "moana_grid.nc")
    ic = open_glorys(IC_FILE)
    fig_ic(ic, g, args.out)
    edges = {e: open_glorys(EDGE_FILE.format(e)) for e in "WNES"}
    fig_bc(ic, edges, g, args.out)


if __name__ == "__main__":
    main()
