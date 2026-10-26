"""Figure: M2 tidal current ellipses from the ROMS tide file.

Usage (moana_python environment):  python webpage_folder/fig_ellipses.py
Writes webpage_folder/figures/ellipses.png.
  left   whole domain, one ellipse every 14 points, on top of M2 Cmax
  right  zoom on Cook Strait, one ellipse every 3 points
Blue ellipses turn anticlockwise (Cmin > 0), orange ones clockwise (Cmin < 0).
"""
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.lines import Line2D

from common import SERIES, TIDES, map_axes, save

f = xr.open_dataset(TIDES)
water = f.mask_rho.values == 1
lon, lat = f.lon_rho.values, f.lat_rho.values
cmax, cmin, cangle = (f[v][0].values for v in ["tide_Cmax", "tide_Cmin", "tide_Cangle"])   # M2 is first


def draw_ellipses(ax, step, scale):
    """scale: degrees of latitude per 1 m/s."""
    theta = np.linspace(0, 2 * np.pi, 40)
    for j in range(0, lon.shape[0], step):
        for i in range(0, lon.shape[1], step):
            if not water[j, i]:
                continue
            a, b, angle = cmax[j, i], cmin[j, i], np.radians(cangle[j, i])
            east = a * np.cos(theta) * np.cos(angle) - b * np.sin(theta) * np.sin(angle)
            north = a * np.cos(theta) * np.sin(angle) + b * np.sin(theta) * np.cos(angle)
            colour = SERIES[0] if b > 0 else SERIES[1]
            ax.plot(lon[j, i] + scale * east / np.cos(np.radians(lat[j, i])), lat[j, i] + scale * north,
                    color=colour, lw=0.8)


fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
for ax in axes:
    pc = ax.pcolormesh(lon, lat, np.where(water, cmax, np.nan), cmap="Greys", vmin=0, vmax=1.5, alpha=0.6)
    map_axes(ax)
fig.colorbar(pc, ax=axes, shrink=0.7, extend="max", label="M2 Cmax (m/s)")

draw_ellipses(axes[0], step=14, scale=1.2)
axes[0].set_title("M2 current ellipses")
draw_ellipses(axes[1], step=3, scale=0.12)
axes[1].set_xlim(173.6, 175.6)
axes[1].set_ylim(-42.0, -40.4)
axes[1].set_title("Cook Strait")

legend = [Line2D([], [], color=SERIES[0], label="turns anticlockwise"),
          Line2D([], [], color=SERIES[1], label="turns clockwise")]
axes[0].legend(handles=legend, loc="lower right", fontsize=9, framealpha=0.95)
save(fig, "ellipses.png")
