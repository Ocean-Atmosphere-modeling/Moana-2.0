#!/usr/bin/env python
"""Publication figure of the Moana model grid.

Usage (in the moana_python environment, see env/moana_python.yml):

    conda activate moana_python
    python Apps/moana/python_scripts/plot_grid.py
    python Apps/moana/python_scripts/plot_grid.py GRID.nc --out some/folder

GRID.nc defaults to Apps/moana/Input/moana_grid.nc (the published 5 km grid,
listed in Apps/moana/inputs.tsv). moana_grid.pdf and moana_grid.png go to
--out, default Apps/moana/Figures.

Panels:
  a  bathymetry h and land mask, every 20th grid line, sponge inner edge,
     200 m and 2000 m isobaths
  b  horizontal grid spacing against latitude (the grid is Mercator, so the
     spacing depends on latitude only)
  c  Cook Strait at native resolution (one quadrilateral per rho-cell)
  d  zonal section of the 40 terrain-following levels (Vtransform = 2) along
     SECTION_LAT. The s-levels use Cs_w and hc stored in the grid file;
     THETA_S, THETA_B and TCLINE for the model are not chosen yet
     (docs/roadmap.md, M2-T2).

Every number on the figure is read from the grid file, except Vtransform = 2
(the file has no Vtransform; the value is not chosen yet, docs/roadmap.md,
M2-T2). Coastline and land are the model's own mask, not an external
coastline.
"""

import argparse
import hashlib
from pathlib import Path

import cmocean
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib import patheffects
from matplotlib.colors import PowerNorm
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[3]
APP = REPO / "Apps" / "moana"

# Text ink and fills, as in scripts/plot_upwelling.py.
INK = "#0b0b0b"
INK2 = "#52514e"
LAND = "#bdb8ad"
ACCENT = "#eb6834"  # transect and zoom box (marks only; their labels stay ink)
SLOT1 = "#2a78d6"   # dataviz categorical slot 1, for a single data series
HALO = [patheffects.withStroke(linewidth=1.6, foreground="white")]

MESH_EVERY = 20          # draw every 20th grid line in panel a
SECTION_LAT = -40.0      # latitude of the panel d section
ZOOM_LON = (173.6, 175.6)  # Cook Strait (panel c); north edge fits the axes
ZOOM_LAT0 = -42.4
ISOBATHS = (200, 2000)   # m, as in the hindcast paper's Fig. 1
DEPTH_TICKS = (0, 200, 1000, 2000, 4000, 6000)
DEEP = 1500              # m; names over deeper water are set in white

MM = 1 / 25.4
FIG_W, FIG_H = 180, 172  # mm, Nature double-column width

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7,
    "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 6,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.5,
    "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "xtick.direction": "out", "ytick.direction": "out",
    "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.dpi": 300, "pdf.fonttype": 42, "ps.fonttype": 42,
})


# ------------------------------------------------------------ helpers ---

def merc(lat):
    """Mercator y (in degrees) of a latitude, so grid cells plot square."""
    return np.degrees(np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)))


def inv_merc(y):
    return np.degrees(2 * np.arctan(np.exp(np.radians(y))) - np.pi / 2)


def lon_label(lon):
    lon = (lon + 180) % 360 - 180
    if np.isclose(lon, 180) or np.isclose(lon, -180):
        return "180°"
    return f"{abs(lon):g}°{'E' if lon > 0 else 'W'}" if lon else "0°"


def lat_label(lat):
    return f"{abs(lat):g}°{'S' if lat < 0 else 'N'}" if lat else "0°"


def set_lon_ticks(ax, lons):
    ax.set_xticks(lons)
    ax.set_xticklabels([lon_label(x) for x in lons])


def set_lat_ticks(ax, lats, labels=True):
    ax.set_yticks(merc(np.asarray(lats, float)))
    ax.set_yticklabels([lat_label(y) for y in lats] if labels else [])


def axes_mm(fig, left, bottom, width, height, **kw):
    """Axes placed in millimetres from the figure's lower-left corner."""
    w, h = fig.get_size_inches() / MM
    return fig.add_axes([left / w, bottom / h, width / w, height / h], **kw)


def panel_label(ax, letter, x=-0.02, y=1.0):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=8,
            fontweight="bold", ha="right", va="bottom")


def place_name(ax, g, name, lon, lat, **kw):
    """Italic name at (lon, lat): white over deep water, ink elsewhere."""
    j = int(np.argmin(np.abs(g["lat_rho"][:, 0] - lat)))
    i = int(np.argmin(np.abs(g["lon_rho"][0, :] - lon)))
    deep = g["ocean"][j, i] and g["h"][j, i] > DEEP
    kw = {"fontsize": 6, "style": "italic", "ha": "center", "va": "center",
          "linespacing": 1.0, **kw}
    ax.text(lon, merc(lat), name, color="white" if deep else INK, **kw)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def in_manifest(digest):
    manifest = APP / "inputs.tsv"
    if not manifest.exists():
        return False
    return any(line.split("\t")[0] == digest
               for line in manifest.read_text().splitlines()
               if line and not line.startswith("#"))


# --------------------------------------------------------------- data ---

def load_grid(path):
    ds = xr.open_dataset(path)
    g = {k: ds[k].values for k in (
        "h", "mask_rho", "pm", "pn", "lon_rho", "lat_rho",
        "lon_vert", "lat_vert", "visc_factor", "diff_factor", "s_w", "Cs_w")}
    g["hc"] = float(ds.hc)
    g["theta_s"], g["theta_b"] = float(ds.theta_s), float(ds.theta_b)
    g["Tcline"] = float(ds.Tcline)
    g["hraw_max"] = float(ds.hraw.max())
    ds.close()
    g["ocean"] = g["mask_rho"] > 0.5
    g["y_vert"] = merc(g["lat_vert"])
    g["y_rho"] = merc(g["lat_rho"])
    return g


def z_w(h, hc, s_w, Cs_w):
    """Depths of the w-levels at rest (zeta = 0) for Vtransform = 2."""
    h = h[None, :]
    s, C = s_w[:, None], Cs_w[:, None]
    return h * (hc * s + h * C) / (hc + h)


# ------------------------------------------------------------- panels ---

def draw_bathymetry(ax, g, norm, cmap, sl=np.s_[:, :]):
    """Ocean depth and land cells on the cell corners (lon_vert, lat_vert)."""
    jr, ir = sl
    jv = slice(jr.start, None if jr.stop is None else jr.stop + 1)
    iv = slice(ir.start, None if ir.stop is None else ir.stop + 1)
    x, y = g["lon_vert"][jv, iv], g["y_vert"][jv, iv]
    ocean = g["ocean"][sl]
    depth = np.ma.masked_where(~ocean, g["h"][sl])
    land = np.ma.masked_where(ocean, np.ones_like(g["h"][sl]))
    pm = ax.pcolormesh(x, y, depth, cmap=cmap, norm=norm, rasterized=True)
    ax.pcolormesh(x, y, land, cmap=mpl.colors.ListedColormap([LAND]),
                  rasterized=True)
    return pm


def panel_domain(ax, g, norm, cmap, j_sec, zoom):
    pm = draw_bathymetry(ax, g, norm, cmap)
    lon, y = g["lon_rho"], g["y_rho"]
    ax.contour(lon, y, np.where(g["ocean"], g["h"], np.nan), levels=ISOBATHS,
               colors=INK2, linewidths=0.35)
    ax.contour(lon, y, g["mask_rho"], levels=[0.5], colors=INK,
               linewidths=0.4)

    # Mesh: every MESH_EVERY-th grid line, including the outer boundary.
    xv, yv = g["lon_vert"], g["y_vert"]
    nj, ni = xv.shape
    for i in sorted(set(range(0, ni, MESH_EVERY)) | {ni - 1}):
        ax.plot(xv[:, i], yv[:, i], color="white", lw=0.3, alpha=0.55)
    for j in sorted(set(range(0, nj, MESH_EVERY)) | {nj - 1}):
        ax.plot(xv[j, :], yv[j, :], color="white", lw=0.3, alpha=0.55)

    # Inner edge of the viscosity/diffusivity sponge.
    ax.contour(lon, y, g["visc_factor"], levels=[1.0 + 1e-6], colors=INK,
               linewidths=0.6, linestyles=[(0, (3, 1.5))])
    n_sponge = int((g["visc_factor"][g["visc_factor"].shape[0] // 2] > 1)
                   .argmin())
    ax.text(lon[0, n_sponge] - 0.2, merc(-33.2), "Sponge", rotation=90,
            fontsize=6, color="white", ha="right", va="center")

    # Section line (panel d) and zoom box (panel c).
    ax.plot(lon[j_sec, :], y[j_sec, :], color=ACCENT, lw=0.9)
    ax.text(lon[j_sec, 6], y[j_sec, 6] + 0.25, "d", color=INK, path_effects=HALO,
            fontsize=7, fontweight="bold", ha="left", va="bottom")
    x0, x1, la0, la1 = zoom
    ax.add_patch(Rectangle((x0, merc(la0)), x1 - x0, merc(la1) - merc(la0),
                           fill=False, ec=ACCENT, lw=0.9))
    ax.text(x1 + 0.2, merc(la1), "c", color=INK, path_effects=HALO, fontsize=7,
            fontweight="bold", ha="left", va="top")

    # Regional names, set in italic as on a chart.
    for name, lo, la in (("Tasman\nSea", 164.5, -37.0),
                         ("South Pacific\nOcean", 181.5, -35.0),
                         ("Challenger\nPlateau", 167.8, -39.3),
                         ("Chatham Rise", 179.5, -43.75),
                         ("Campbell\nPlateau", 171.5, -49.4)):
        place_name(ax, g, name, lo, la)

    ax.set_xlim(xv.min(), xv.max())
    ax.set_ylim(yv.min(), yv.max())
    ax.set_aspect("equal")
    set_lon_ticks(ax, [165, 170, 175, 180])
    set_lat_ticks(ax, [-50, -45, -40, -35])
    return pm


def panel_spacing(ax, g):
    """Grid spacing against latitude. On this Mercator grid dx and dy
    differ by well under 1%, so one line stands for both."""
    lat = g["lat_rho"][:, 0]
    dx = (1e-3 / g["pm"]).mean(axis=1)
    dy = (1e-3 / g["pn"]).mean(axis=1)
    ax.plot(dx, merc(lat), color=SLOT1, lw=1.2)
    gap = np.max(np.abs(1 / g["pm"] - 1 / g["pn"]) * g["pm"])
    j = int(np.argmin(np.abs(lat + 44)))
    ax.text(dx[j] + 0.1, merc(lat[j]),
            f"Δx ≈ Δy\n(within\n{np.ceil(gap * 1000) / 10:g}%)",
            ha="left", va="center", fontsize=6, color=INK, linespacing=1.1)
    ax.set_xlim(4.0, 6.0)
    ax.set_xticks([4, 5, 6])
    ax.set_xlabel("Grid\nspacing (km)")
    ax.grid(color="#d9d8d4", lw=0.4)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def panel_zoom(ax, g, norm, cmap, zoom):
    x0, x1, la0, la1 = zoom
    lon, lat = g["lon_rho"][0, :], g["lat_rho"][:, 0]
    ir = np.flatnonzero((lon >= x0) & (lon <= x1))
    jr = np.flatnonzero((lat >= la0) & (lat <= la1))
    ir = np.r_[ir[0] - 1, ir, ir[-1] + 1]  # one extra cell so edges are full
    jr = np.r_[jr[0] - 1, jr, jr[-1] + 1]
    sl = np.s_[jr[0]:jr[-1] + 1, ir[0]:ir[-1] + 1]
    draw_bathymetry(ax, g, norm, cmap, sl)
    # Cell edges, drawn once over ocean and land.
    jv = slice(jr[0], jr[-1] + 2)
    iv = slice(ir[0], ir[-1] + 2)
    ax.pcolormesh(g["lon_vert"][jv, iv], g["y_vert"][jv, iv],
                  np.zeros((len(jr), len(ir))), facecolor="none",
                  edgecolor="white", lw=0.15, alpha=0.6, rasterized=True)
    ax.contour(g["lon_rho"][sl], g["y_rho"][sl],
               np.where(g["ocean"][sl], g["h"][sl], np.nan),
               levels=ISOBATHS, colors=INK2, linewidths=0.35)
    ax.set_xlim(x0, x1)
    ax.set_ylim(merc(la0), merc(la1))
    ax.set_aspect("equal")
    set_lon_ticks(ax, [174, 175])
    set_lat_ticks(ax, [-42, -41, -40])
    for name, lo, la in (("North\nIsland", 175.35, -40.1),
                         ("South\nIsland", 173.8, -41.75)):
        ax.text(lo, merc(la), name, fontsize=6, color=INK, ha="center",
                va="center", linespacing=1.0)
    place_name(ax, g, "Cook\nStrait", 174.55, -41.6)
    # Scale bar: 5 cells at the zoom's mean latitude.
    j = jr[len(jr) // 2]
    dx_km = 1e-3 / g["pm"][j, ir].mean()
    dlon = g["lon_rho"][j, ir[1]] - g["lon_rho"][j, ir[0]]
    xs, ys = x0 + 0.1, merc(la1) - 0.25
    ax.plot([xs, xs + 5 * dlon], [ys, ys], color=INK, lw=1.2,
            solid_capstyle="butt")
    ax.text(xs, ys + 0.05, f"5 cells ≈ {5 * dx_km:.0f} km",
            fontsize=6, ha="left", va="bottom")


def panel_section(ax, g, j):
    lon = g["lon_rho"][j, :]
    h = g["h"][j, :]
    ocean = g["ocean"][j, :]
    z = z_w(h, g["hc"], g["s_w"], g["Cs_w"])
    z[:, ~ocean] = np.nan
    floor = 6200
    # Depth on a square-root axis so the near-surface levels are visible.
    ax.set_yscale("function",
                  functions=(lambda d: np.sqrt(np.clip(d, 0, None)), np.square))
    for k in range(z.shape[0]):
        ax.plot(lon, -z[k], color="#8a8984", lw=0.2)
    # Seabed and land in one fill: land columns (mask = 0) span all depths.
    ax.fill_between(lon, np.where(ocean, h, 0), floor, step="mid",
                    color=LAND, lw=0)
    ax.plot(lon, np.where(ocean, h, np.nan), color=INK, lw=0.5)
    edges = g["lon_vert"][j, :]
    ax.set_xlim(edges[0], edges[-1])
    ax.set_ylim(floor, 0)
    ax.set_yticks([0, 50, 200, 500, 1000, 2000, 4000, 6000])
    ax.set_ylabel("Depth (m)")
    set_lon_ticks(ax, [165, 170, 175, 180])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.text(0.995, 0.05,
            f"{lat_label(round(float(g['lat_rho'][j, 0]), 1))};  "
            f"N = {z.shape[0] - 1}, Vtransform = 2, hc = {g['hc']:g} m, "
            f"θs = {g['theta_s']:g}, θb = {g['theta_b']:g} "
            "(grid-file values, not yet final)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6,
            color=INK)


# --------------------------------------------------------------- main ---

def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("grid", nargs="?", type=Path,
                   default=APP / "Input" / "moana_grid.nc",
                   help="ROMS grid file (default: %(default)s)")
    p.add_argument("--out", type=Path, default=APP / "Figures",
                   help="output folder (default: %(default)s)")
    args = p.parse_args()

    digest = sha256(args.grid)
    listed = in_manifest(digest)
    print(f"grid    {args.grid}\nsha256  {digest} "
          f"({'listed' if listed else 'NOT listed'} in inputs.tsv)")

    g = load_grid(args.grid)
    j_sec = int(np.argmin(np.abs(g["lat_rho"][:, 0] - SECTION_LAT)))
    cmap = cmocean.cm.deep
    norm = PowerNorm(gamma=0.5, vmin=0, vmax=6000)

    # Layout in mm. Panel c is 44 mm wide; its north edge is set so the
    # zoom fills an 84 mm tall axes at true (Mercator) aspect.
    c_w, c_h = 44, 84
    x0, x1 = ZOOM_LON
    zoom = (x0, x1, ZOOM_LAT0,
            float(inv_merc(merc(ZOOM_LAT0) + (x1 - x0) * c_h / c_w)))

    fig = plt.figure(figsize=(FIG_W * MM, FIG_H * MM))
    ax_a = axes_mm(fig, 12, 58, 92, 110)
    ax_b = axes_mm(fig, 107, 58, 15, 110, sharey=ax_a)
    ax_c = axes_mm(fig, 133, 168 - c_h, c_w, c_h)
    ax_cb = axes_mm(fig, 133, 66, c_w, 2.2)
    ax_d = axes_mm(fig, 12, 9, 166, 34)

    pm = panel_domain(ax_a, g, norm, cmap, j_sec, zoom)
    panel_spacing(ax_b, g)
    ax_b.tick_params(labelleft=False)
    panel_zoom(ax_c, g, norm, cmap, zoom)
    panel_section(ax_d, g, j_sec)

    cb = fig.colorbar(pm, cax=ax_cb, orientation="horizontal",
                      ticks=DEPTH_TICKS)
    cb.ax.tick_params(labelsize=6, length=2, width=0.5)
    cb.outline.set_linewidth(0.5)
    cb.set_label("Depth h (m)")

    for ax, letter, x in ((ax_a, "a", -0.07), (ax_b, "b", -0.1),
                          (ax_c, "c", -0.2), (ax_d, "d", -0.04)):
        panel_label(ax, letter, x=x)

    args.out.mkdir(parents=True, exist_ok=True)
    meta_src = (f"{Path(__file__).relative_to(REPO)}; grid "
                f"{args.grid.name} sha256 {digest}")
    for ext, meta in (("pdf", {"Title": "Moana grid", "Subject": meta_src}),
                      ("png", {"Title": "Moana grid", "Description": meta_src})):
        out = args.out / f"moana_grid.{ext}"
        fig.savefig(out, metadata=meta)
        print(f"wrote   {out}")

    ny, nx = g["h"].shape
    dx = 1e-3 / g["pm"]
    print(f"rho-points {nx} x {ny}, ocean {g['ocean'].mean():.1%}, "
          f"spacing {dx.min():.2f}-{dx.max():.2f} km, "
          f"h {g['h'][g['ocean']].min():g}-{g['h'][g['ocean']].max():g} m "
          f"(hraw max {g['hraw_max']:.0f} m), section at row {j_sec}")


if __name__ == "__main__":
    main()
