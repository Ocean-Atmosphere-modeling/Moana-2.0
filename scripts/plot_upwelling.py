#!/usr/bin/env python
"""Publication figures for the ROMS UPWELLING test case.

Usage (in the moana_python environment, see env/moana_python.yml):

    conda activate moana_python
    python scripts/plot_upwelling.py tests/upwelling/run_<date>_<time>
    python scripts/plot_upwelling.py RUN_DIR --out some/other/folder

RUN_DIR is a run directory written by tests/upwelling/submit.sh. It must hold
roms_his.nc (snapshots), roms_avg.nc (averages), roms_dia.nc (diagnostics)
and roms_upwelling.in (run parameters). PNGs go to --out, default
tests/upwelling/results.

UPWELLING is a channel that is periodic east-west and closed by walls to the
north and south, with a shelf along each wall. It is forced only by an
along-channel (westward) wind stress, so the flow is nearly uniform along
the channel: sections and profiles are averaged along x.
"""

import argparse
import re
from pathlib import Path

import cmocean
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import xroms
from matplotlib.ticker import MaxNLocator

REPO = Path(__file__).resolve().parents[1]

# Text ink and station colors (validated categorical slots 1-3; every
# station line also has its own line style and a direct label).
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#d9d8d4"
LAND = "#bdb8ad"
STATIONS = [  # name, target y (km), color, line style
    ("South shelf", 12.0, "#2a78d6", "-"),
    ("Mid-channel", 40.0, "#eb6834", "--"),
    ("North shelf", 68.0, "#1baf7a", "-."),
]

# ROMS lateral boundary condition keywords (roms_*.in, LBC lines).
LBC_NAMES = {
    "Per": "Periodic", "Clo": "Closed (wall)", "Gra": "Gradient",
    "Rad": "Radiation", "Mix": "Mixed", "Nes": "Nested", "Cha": "Chapman",
    "Fla": "Flather", "Shc": "Shchepetkin", "Red": "Reduced",
    "Cla": "Clamped",
}
LBC_VARS = {
    "isFsur": "Free surface", "isUbar": "2D u", "isVbar": "2D v",
    "isUvel": "3D u", "isVvel": "3D v", "isTvar": "Tracers (T, S)",
}

MM = 1 / 25.4
FULL_WIDTH = 180 * MM  # double-column figure width

mpl.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.titlelocation": "left", "axes.titleweight": "bold",
    "figure.facecolor": "white", "axes.facecolor": "white",
})


# ---------------------------------------------------------------- data ---

def open_output(path, t0=None):
    """Open a ROMS output file; return (dataset, xgcm grid) from xroms.

    xroms adds depths (z_rho, z_w, and z_rho0/z_w0 at rest) and the grid
    used to move fields between u, v, w and rho points. A "days" coordinate
    counts from t0 (the run start), or from the file's first record.
    """
    # ROMS times are "seconds since 0001-01-01", which needs cftime.
    ds = xr.open_dataset(
        path, decode_times=xr.coders.CFDatetimeCoder(use_cftime=True))
    ds, grid = xroms.roms_dataset(ds, include_Z0=True)
    t0 = ds.ocean_time[0] if t0 is None else t0
    elapsed = (ds.ocean_time - t0).dt.total_seconds()
    return ds.assign_coords(days=elapsed / 86400), grid


def at_rho(da, grid):
    """Interpolate a u/v-point field to rho points (xroms)."""
    return xroms.to_rho(da, grid)


def xmean(da):
    """Along-channel (x) mean, whatever grid point the field lives on."""
    return da.mean([d for d in da.dims if d.startswith("xi_")])


def is_uniform(da):
    return float(da.max() - da.min()) < 1e-6


def mean_period(ds):
    """Label for a time mean of averaged records (stamped mid-window)."""
    d = ds.days.values
    half = (d[1] - d[0]) / 2 if d.size > 1 else 0
    return f"mean over days {d[0] - half:.3g}-{d[-1] + half:.3g}"


def parse_lbc(in_file):
    """Return {variable: [W, S, E, N]} from the LBC lines of a ROMS .in."""
    lbc = {}
    for line in Path(in_file).read_text().splitlines():
        m = re.match(r"\s*LBC\((is\w+)\)\s*==\s*(\w+)\s+(\w+)\s+(\w+)\s+(\w+)",
                     line)
        if m and m.group(1) in LBC_VARS:
            lbc[m.group(1)] = list(m.groups()[1:])
    return lbc


def wind_stress(dia, grid, rho0):
    """Domain-mean surface stress (N/m2) recovered from the diagnostics.

    ubar_sstr is the surface-stress term of the depth-averaged momentum
    equation, tau / (rho0 * D), so tau = rho0 * D * ubar_sstr.
    """
    D = dia.h + dia.zeta
    taux = rho0 * at_rho(dia.ubar_sstr, grid) * D
    tauy = rho0 * at_rho(dia.vbar_sstr, grid) * D
    return (taux.mean(["eta_rho", "xi_rho"]),
            tauy.mean(["eta_rho", "xi_rho"]))


# ------------------------------------------------------------- helpers ---

def style_axes(ax, grid=False):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if grid:
        ax.grid(True, color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)


def colorbar(fig, mappable, ax, label):
    cb = fig.colorbar(mappable, ax=ax, shrink=0.9, pad=0.02, aspect=30)
    cb.set_label(label)
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(width=0.5)
    levels = getattr(mappable, "levels", None)
    if levels is None:
        cb.locator = MaxNLocator(6)
        cb.update_ticks()
    else:  # contour fills: round ticks within the plotted levels only
        ticks = MaxNLocator(6).tick_values(levels[0], levels[-1])
        eps = 1e-9 * (levels[-1] - levels[0])
        cb.set_ticks(ticks[(ticks >= levels[0] - eps)
                           & (ticks <= levels[-1] + eps)])
    return cb


def nice_levels(lo, hi, n=24):
    """Round contour levels spanning [lo, hi]."""
    return MaxNLocator(n).tick_values(float(lo), float(hi))


def symmetric_levels(da, pct=99.0, n=20):
    """Round levels symmetric about zero, clipped at a high percentile so a
    few extreme cells do not wash out the rest (the colorbar extends)."""
    vmax = float(np.nanpercentile(np.abs(np.asarray(da)), pct)) or 1.0
    lev = MaxNLocator(n, symmetric=True).tick_values(-vmax, vmax)
    return lev


def plan_view(ax, ds):
    ax.set_aspect("equal")
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_xlim(float(ds.x_rho.min()) / 1e3, float(ds.x_rho.max()) / 1e3)
    ax.set_ylim(float(ds.y_rho.min()) / 1e3, float(ds.y_rho.max()) / 1e3)


def uniform_note(ax, da, name, units):
    """Say a field is uniform instead of drawing a flat colour field."""
    ax.text(0.5, 0.5, f"{name} is uniform: {float(da.mean()):.2f} {units}"
            "\n(no forcing in this case)", ha="center", va="center",
            transform=ax.transAxes, color=INK2, fontsize=8)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(GRID)


def save(fig, out, name):
    path = out / name
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path}")


# ------------------------------------------------------------- figures ---

def fig_domain(his, lbc, out):
    """Bathymetry, boundaries and forcing direction; vertical grid."""
    g = his.isel(ocean_time=0)
    fig, (a, b) = plt.subplots(
        1, 2, figsize=(FULL_WIDTH, 95 * MM),
        gridspec_kw={"width_ratios": [1, 1.5]}, layout="constrained")

    x, y = g.x_rho / 1e3, g.y_rho / 1e3
    pc = a.pcolormesh(x, y, g.h, cmap=cmocean.cm.deep, shading="nearest")
    cs = a.contour(x, y, g.h, levels=[50, 100, 140], colors="white",
                   linewidths=0.5)
    a.clabel(cs, fmt="%d m", fontsize=6)
    plan_view(a, g)
    colorbar(fig, pc, a, "Depth h (m)")

    # Boundaries: closed walls thick and solid, periodic edges dashed, each
    # labelled just inside the domain.
    x0, x1 = float(x.min()), float(x.max())
    y0, y1 = float(y.min()), float(y.max())
    wsen = lbc.get("isFsur", ["?"] * 4)
    edges = [((x0, x0), (y0, y1)), ((x0, x1), (y0, y0)),
             ((x1, x1), (y0, y1)), ((x0, x1), (y1, y1))]
    for (xs, ys), code in zip(edges, wsen):
        a.plot(xs, ys, color=INK, lw=2.5 if code == "Clo" else 1.2,
               ls="-" if code == "Clo" else (0, (3, 2)), clip_on=False)
    name = [LBC_NAMES.get(c, c) for c in wsen]
    box = dict(facecolor="white", edgecolor="none", pad=1, alpha=0.85)
    a.text(0.5, 0.985, f"North: {name[3]}", transform=a.transAxes,
           ha="center", va="top", fontsize=6.5, bbox=box)
    a.text(0.5, 0.015, f"South: {name[1]}", transform=a.transAxes,
           ha="center", va="bottom", fontsize=6.5, bbox=box)
    a.text(0.03, 0.4, f"West: {name[0]}", transform=a.transAxes,
           rotation=90, ha="left", va="center", fontsize=6.5, bbox=box)
    a.text(0.97, 0.4, f"East: {name[2]}", transform=a.transAxes,
           rotation=90, ha="right", va="center", fontsize=6.5, bbox=box)
    a.annotate("", xy=(0.25, 0.55), xytext=(0.75, 0.55),
               xycoords="axes fraction",
               arrowprops=dict(arrowstyle="-|>", color="white", lw=1.5))
    a.text(0.5, 0.58, "wind stress", transform=a.transAxes, color="white",
           ha="center", va="bottom", fontsize=7)
    a.set_title("(a) Domain and bathymetry")

    # Cross-channel depth with every s-level (x-mean, at rest).
    yk = xmean(g.y_rho) / 1e3
    z_w = xmean(g.z_w0)
    for k in range(z_w.sizes["s_w"]):
        b.plot(yk, z_w.isel(s_w=k), color=INK2, lw=0.4)
    bottom = -1.05 * float(g.h.max())
    b.fill_between(yk, -xmean(g.h), bottom, color=LAND, lw=0)
    b.plot(yk, -xmean(g.h), color=INK, lw=1.2)
    b.set_xlim(float(yk.min()), float(yk.max()))
    b.set_ylim(bottom, 2)
    b.set_xlabel("y (km)")
    b.set_ylabel("z (m)")
    b.set_title(f"(b) Cross-channel depth and the {z_w.sizes['s_w'] - 1} "
                "terrain-following levels")
    style_axes(b)
    save(fig, out, "fig01_domain.png")


def fig_forcing(dia, grid, lbc, rho0, out):
    """Surface wind stress through the run; boundary condition table."""
    taux, tauy = wind_stress(dia, grid, rho0)
    fig, (a, b) = plt.subplots(
        1, 2, figsize=(FULL_WIDTH, 70 * MM),
        gridspec_kw={"width_ratios": [1.1, 1]}, layout="constrained")

    a.axhline(0, color=INK2, lw=0.6)
    a.plot(dia.days, taux, color=STATIONS[0][2], lw=2, marker="o", ms=3)
    a.set_xlabel("Time (days)")
    a.set_ylabel(r"$\tau_x$ (N m$^{-2}$)")
    a.set_xlim(0, np.ceil(float(dia.days.max())))
    note = ("domain mean of 6-h averages\n"
            r"cross-channel $\tau_y$ = 0 throughout"
            if float(np.abs(tauy).max()) < 1e-8 else
            "domain mean of 6-h averages")
    a.text(0.97, 0.95, note, transform=a.transAxes, ha="right", va="top",
           color=INK2, fontsize=7)
    a.set_title("(a) Along-channel wind stress")
    style_axes(a, grid=True)

    b.axis("off")
    rows = [[LBC_VARS[k]] + [LBC_NAMES.get(c, c) for c in v]
            for k, v in lbc.items()]
    t = b.table(cellText=rows,
                colLabels=["", "West", "South", "East", "North"],
                loc="center", cellLoc="center", edges="horizontal")
    t.auto_set_font_size(False)
    t.set_fontsize(7)
    t.scale(1, 1.5)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(GRID)
        if r == 0 or c == 0:
            cell.set_text_props(weight="bold")
    b.set_title("(b) Lateral boundary conditions")
    save(fig, out, "fig02_forcing_boundaries.png")


def fig_surface_currents(avg, grid, out):
    """Time-mean surface currents and sea surface height."""
    s = avg.isel(s_rho=-1)
    u = at_rho(s.u, grid).mean("ocean_time")
    v = at_rho(s.v, grid).mean("ocean_time")
    speed = np.hypot(u, v)
    zeta = avg.zeta.mean("ocean_time") * 100  # cm
    x, y = avg.x_rho / 1e3, avg.y_rho / 1e3
    period = mean_period(avg)

    fig, (a, b) = plt.subplots(1, 2, figsize=(FULL_WIDTH, 100 * MM),
                               layout="constrained")
    pc = a.pcolormesh(x, y, speed, cmap=cmocean.cm.speed, shading="nearest")
    colorbar(fig, pc, a, r"Surface speed (m s$^{-1}$)")
    q = (slice(3, None, 6), slice(2, None, 5))
    ref = float(MaxNLocator(2).tick_values(0, float(speed.max()))[1])
    qv = a.quiver(x[q], y[q], u[q], v[q], color=INK, width=0.006,
                  scale=ref * 12, scale_units="width", pivot="middle")
    a.quiverkey(qv, 0.8, -0.085, ref, rf"{ref:g} m s$^{{-1}}$",
                labelpos="E", coordinates="axes",
                fontproperties={"size": 6.5})
    plan_view(a, avg)
    a.set_title("(a) Surface currents")

    cf = b.contourf(x, y, zeta, levels=symmetric_levels(zeta, pct=100),
                    cmap=cmocean.cm.balance)
    colorbar(fig, cf, b, "Sea surface height (cm)")
    plan_view(b, avg)
    b.set_title("(b) Sea surface height")
    fig.suptitle(period.capitalize(), x=0.01, ha="left", fontsize=8,
                 color=INK2)
    save(fig, out, "fig03_surface_currents.png")


def fig_surface_tracers(avg, out):
    """Time-mean sea surface temperature and salinity."""
    s = avg.isel(s_rho=-1).mean("ocean_time")
    x, y = avg.x_rho / 1e3, avg.y_rho / 1e3
    fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 100 * MM),
                             layout="constrained")
    for ax, name, cmap, units, tag in [
            (axes[0], "temp", cmocean.cm.thermal, "°C", "(a) SST"),
            (axes[1], "salt", cmocean.cm.haline, "", "(b) SSS")]:
        da = s[name]
        label = "Temperature" if name == "temp" else "Salinity"
        ax.set_title(tag)
        if is_uniform(avg[name]):
            uniform_note(ax, da, label, units)
            continue
        cf = ax.contourf(x, y, da, levels=nice_levels(da.min(), da.max()),
                         cmap=cmap)
        ax.contour(x, y, da, levels=cf.levels[::4], colors="white",
                   linewidths=0.4)
        colorbar(fig, cf, ax, f"{label} ({units})" if units else label)
        plan_view(ax, avg)
    fig.suptitle(mean_period(avg).capitalize(), x=0.01, ha="left",
                 fontsize=8, color=INK2)
    save(fig, out, "fig04_surface_tracers.png")


def section(ax, fig, da, z, y, cmap, levels, label, contour_every=None):
    cf = ax.contourf(y, z, da, levels=levels, cmap=cmap, extend="both")
    if contour_every:
        cs = ax.contour(y, z, da, levels=levels[::contour_every],
                        colors=INK, linewidths=0.4)
        ax.clabel(cs, fmt="%g", fontsize=6)
    ax.fill_between(y[0], z[0], z[0].min() - 5, color=LAND, lw=0)
    ax.set_ylim(float(z.min()) - 2, 1)
    ax.set_xlim(float(y.min()), float(y.max()))
    colorbar(fig, cf, ax, label)


def fig_sections(his, grid, out):
    """Along-channel mean cross-sections at start and end of the run."""
    first, last = his.isel(ocean_time=0), his.isel(ocean_time=-1)
    z = xmean(last.z_rho).transpose("s_rho", "eta_rho").values
    y = np.broadcast_to(xmean(last.y_rho).values / 1e3, z.shape)
    t0, t1 = xmean(first.temp), xmean(last.temp)
    u = xmean(at_rho(last.u, grid))
    w = xmean(xroms.to_s_rho(last.w, grid)) * 86400  # m/day
    day = float(last.days)

    fig, axes = plt.subplots(2, 2, figsize=(FULL_WIDTH, 120 * MM),
                             sharex=True, sharey=True, layout="constrained")
    tlev = np.arange(np.floor(float(min(t0.min(), t1.min()))),
                     np.ceil(float(max(t0.max(), t1.max()))) + 0.01, 0.25)
    for ax, t, when in [(axes[0, 0], t0, "day 0"),
                        (axes[0, 1], t1, f"day {day:g}")]:
        section(ax, fig, t.values, z, y, cmocean.cm.thermal, tlev,
                "T (°C)", contour_every=4)
        ax.set_title(f"({'ab'[ax is axes[0, 1]]}) Temperature, {when}")
    section(axes[1, 0], fig, u.values, z, y, cmocean.cm.balance,
            symmetric_levels(u, pct=100), r"u (m s$^{-1}$)")
    axes[1, 0].set_title(f"(c) Along-channel velocity u, day {day:g}")
    section(axes[1, 1], fig, w.values, z, y, cmocean.cm.balance,
            symmetric_levels(w, pct=98), r"w (m day$^{-1}$)")
    axes[1, 1].set_title(f"(d) Vertical velocity w, day {day:g}")
    for ax in axes[1]:
        ax.set_xlabel("y (km)")
    for ax in axes[:, 0]:
        ax.set_ylabel("z (m)")
    fig.suptitle("Cross-channel sections, along-channel mean", x=0.01,
                 ha="left", fontsize=8, color=INK2)
    save(fig, out, "fig05_sections.png")


def fig_profiles(his, grid, out):
    """Vertical profiles of T, S, u, v at three cross-channel stations."""
    first, last = his.isel(ocean_time=0), his.isel(ocean_time=-1)
    yk = xmean(last.y_rho).values / 1e3
    fields = [
        ("temp", "Temperature (°C)", lambda d: d.temp),
        ("salt", "Salinity", lambda d: d.salt),
        ("u", r"u, along-channel (m s$^{-1}$)", lambda d: at_rho(d.u, grid)),
        ("v", r"v, cross-channel (m s$^{-1}$)", lambda d: at_rho(d.v, grid)),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(FULL_WIDTH, 85 * MM),
                             sharey=True, layout="constrained")
    for i, (ax, (name, label, get)) in enumerate(zip(axes, fields)):
        ax.set_xlabel(label)
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.set_title(f"({'abcd'[i]})")
        style_axes(ax, grid=True)
        if name == "salt" and is_uniform(his.salt):
            ax.text(0.5, 0.5, f"uniform\n{float(his.salt.mean()):.2f}"
                    "\n(no forcing)", ha="center", va="center",
                    transform=ax.transAxes, color=INK2, fontsize=7)
            ax.set_xticks([])
            continue
        for sname, ytarget, color, ls in STATIONS:
            j = int(np.argmin(np.abs(yk - ytarget)))
            z = xmean(last.z_rho).isel(eta_rho=j)
            prof = xmean(get(last)).isel(eta_rho=j)
            ax.plot(prof, z, color=color, ls=ls, lw=2, label=sname)
            if name == "temp":
                ax.plot(xmean(get(first)).isel(eta_rho=j), z, color=color,
                        ls=":", lw=1)
                # Direct label at the deepest point, where profiles part.
                ax.text(float(prof[0]) + 0.15, float(z[0]), sname,
                        color=INK, fontsize=6, ha="left", va="center")
        if name in ("u", "v"):
            ax.axvline(0, color=INK2, lw=0.6)
    axes[0].set_ylabel("z (m)")
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(mpl.lines.Line2D([], [], color=INK2, ls=":", lw=1))
    labels.append("Day 0 temperature")
    fig.legend(handles, labels, loc="outside lower center", ncol=4,
               frameon=False)
    fig.suptitle(f"Vertical profiles at day {float(last.days):g}, "
                 f"along-channel mean at y = "
                 + ", ".join(f"{s[1]:g}" for s in STATIONS) + " km",
                 x=0.01, ha="left", fontsize=8, color=INK2)
    save(fig, out, "fig06_profiles.png")


def fig_sst_evolution(his, out):
    """Hovmoller of along-channel mean SST across the channel."""
    sst = xmean(his.temp.isel(s_rho=-1))
    yk = xmean(his.y_rho).values / 1e3
    fig, ax = plt.subplots(figsize=(FULL_WIDTH * 0.6, 75 * MM),
                           layout="constrained")
    cf = ax.contourf(his.days, yk, sst.T,
                     levels=nice_levels(sst.min(), sst.max()),
                     cmap=cmocean.cm.thermal)
    cs = ax.contour(his.days, yk, sst.T, levels=cf.levels[::4],
                    colors="white", linewidths=0.4)
    ax.clabel(cs, fmt="%g", fontsize=6)
    colorbar(fig, cf, ax, "SST (°C)")
    ax.axvline(2, color="white", lw=0.8, ls="--")
    ax.text(1.95, yk.max() * 0.5, "wind reaches full strength",
            color="white", fontsize=6, rotation=90, ha="right", va="center")
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("y (km)")
    ax.set_title("Along-channel mean SST through the run")
    save(fig, out, "fig07_sst_evolution.png")


# ---------------------------------------------------------------- main ---

def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("run_dir", type=Path)
    p.add_argument("--out", type=Path,
                   default=REPO / "tests" / "upwelling" / "results")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    his, his_grid = open_output(args.run_dir / "roms_his.nc")
    t0 = his.ocean_time[0]  # run start: times in all files count from it
    avg, avg_grid = open_output(args.run_dir / "roms_avg.nc", t0)
    dia, dia_grid = open_output(args.run_dir / "roms_dia.nc", t0)
    rho0 = float(his.rho0)
    lbc = parse_lbc(args.run_dir / "roms_upwelling.in")

    fig_domain(his, lbc, args.out)
    fig_forcing(dia, dia_grid, lbc, rho0, args.out)
    fig_surface_currents(avg, avg_grid, args.out)
    fig_surface_tracers(avg, args.out)
    fig_sections(his, his_grid, args.out)
    fig_profiles(his, his_grid, args.out)
    fig_sst_evolution(his, args.out)


if __name__ == "__main__":
    main()
