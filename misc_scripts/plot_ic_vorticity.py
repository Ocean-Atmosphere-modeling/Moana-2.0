#!/usr/bin/env python
"""Figure of the relative vorticity of the ROMS-ready initial condition, computed with xroms.

Usage (in the moana_python environment):

    python misc_scripts/plot_ic_vorticity.py

Writes concept_figures/ic_vorticity_<DATE>.png.

xroms.relative_vorticity() gives zeta = dv/dx - du/dy on psi-points and on the w-levels (s_w).
The figure shows zeta / f (no unit). f < 0 in the southern hemisphere, so zeta / f > 0 is cyclonic.

The top and bottom w-levels are 0 everywhere (xroms has no derivative there), so the maps
use the first w-level below the surface and the first w-level above the bottom.

Panels:
  left    first w-level below the surface
  middle  first w-level above the bottom
  right   a west-east section along the middle psi row, depth from the w-levels at rest
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import xroms

REPO = Path(__file__).resolve().parents[1]
GRID = Path("/projects/f_omg_1/moa/moana/moana_grid_N50.nc")
IC_DIR = Path("/projects/f_omg_1/moa/moana/oceanum_input/initial_cond/roms_ready")
DATE = "2026-01-01"

INK = "#0b0b0b"
INK2 = "#52514e"
LAND = "#bdb8ad"


def to_psi(f):
    """A rho-point field (f, h) moved to psi-points: mean of the four neighbours."""
    return 0.25 * (f[:-1, :-1] + f[1:, :-1] + f[:-1, 1:] + f[1:, 1:])


def relative_vorticity(g):
    """zeta (1/s) from the IC u and v, with xroms: (s_w, eta_psi, xi_psi)."""
    u = xr.open_dataset(IC_DIR / f"ic_u_{DATE}.nc").u.isel(ocean_time=0)
    v = xr.open_dataset(IC_DIR / f"ic_v_{DATE}.nc").v.isel(ocean_time=0)
    ds = g.assign(u=u, v=v, zeta=xr.zeros_like(g.h))     # sea surface at rest, as in make_ic.py
    ds, xgrid = xroms.roms_dataset(ds, Vtransform=2)
    zeta = xroms.relative_vorticity(ds.u, ds.v, xgrid)
    return zeta.transpose("s_w", "eta_v", "xi_u").values  # xroms names the psi dims eta_v, xi_u


def main():
    g = xr.open_dataset(GRID)
    lon = g.lon_psi.values % 360
    lat = g.lat_psi.values
    ocean = g.mask_psi.values == 1
    ro = relative_vorticity(g) / to_psi(g.f.values)      # zeta / f
    ro = np.where(ocean, ro, np.nan)

    hi = np.nanpercentile(abs(ro[1:-1]), 99)             # colour range from the inner levels

    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5), layout="constrained",
                             gridspec_kw={"width_ratios": [1, 1, 1.3]})
    for ax, k, name in ((axes[0], -2, "first w-level below the surface"),
                        (axes[1], 1, "first w-level above the bottom")):
        ax.set_facecolor(LAND)
        mesh = ax.pcolormesh(lon, lat, ro[k], cmap="RdBu_r", vmin=-hi, vmax=hi, shading="nearest")
        ax.set_aspect(1 / np.cos(np.deg2rad(41)))
        ax.set_title(f"ζ / f, {name}", loc="left", color=INK)
        ax.set_xlabel("longitude (°E)")
    axes[0].set_ylabel("latitude (°)")

    # section along the middle psi row, on the w-levels at rest (Vtransform 2)
    j = lat.shape[0] // 2
    axes[0].axhline(lat[j].mean(), color=INK, linewidth=0.8, linestyle="--")
    h = to_psi(g.h.values)[j]
    s, C, hc = g.s_w.values[:, None], g.Cs_w.values[:, None], float(g.hc)
    z = h * (hc * s + h * C) / (hc + h)
    x = np.broadcast_to(lon[j], z.shape)
    ax = axes[2]
    ax.set_facecolor(LAND)
    ax.pcolormesh(x[1:-1], z[1:-1], ro[1:-1, j], cmap="RdBu_r", vmin=-hi, vmax=hi, shading="gouraud")
    ax.set_title(f"ζ / f, section at {lat[j].mean():.1f}° (dashed line, left)", loc="left", color=INK)
    ax.set_xlabel("longitude (°E)")
    ax.set_ylabel("depth (m)")

    fig.colorbar(mesh, ax=axes, shrink=0.8, label="ζ / f   (> 0 cyclonic in the southern hemisphere)")
    inner = ro[1:-1][:, ocean]
    fig.text(0.01, 0.0,
             f"u, v from ic_u/ic_v_{DATE}.nc   ζ = dv/dx − du/dy from xroms {xroms.__version__}   "
             f"ζ/f min {np.nanmin(inner):.2f}  max {np.nanmax(inner):.2f}   colour range: 99th percentile of |ζ/f|",
             fontsize=8, color=INK2)

    out = REPO / "concept_figures" / f"ic_vorticity_{DATE}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}   zeta/f min {np.nanmin(inner):.2f}  max {np.nanmax(inner):.2f}")


if __name__ == "__main__":
    main()
