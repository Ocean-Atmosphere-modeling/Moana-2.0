"""Figure: Cmax and Cmin of the six largest constituents, from the ROMS tide file.

Usage (moana_python environment):  python webpage_folder/fig_cmax_cmin.py
Writes webpage_folder/figures/cmax_cmin.png.
  top row     Cmax (semi-major axis, m/s), own colour scale per constituent, 99.5th percentile at the top
  bottom row  Cmin (semi-minor axis, m/s). Blue = positive = turns anticlockwise, orange = negative = clockwise.
              Same colours as the ellipse figure. Symmetric scale about zero.
"""
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import LinearSegmentedColormap

from common import SERIES, TIDES, map_axes, save

NAMES = ["M2", "S2", "N2", "K2", "K1", "O1"]
cmin_cmap = LinearSegmentedColormap.from_list("rot", [SERIES[1], "white", SERIES[0]])

f = xr.open_dataset(TIDES)
water = f.mask_rho.values == 1
names = [str(c) for c in f.tidal_constituents.values]
lon, lat = f.lon_rho.values, f.lat_rho.values

# 4 rows x 3 columns: Cmax row then Cmin row for M2 S2 N2, then the same for K2 K1 O1
fig, axes = plt.subplots(4, 3, figsize=(14, 17), constrained_layout=True)
for n, name in enumerate(NAMES):
    k = names.index(name)
    cmax = np.where(water, f.tide_Cmax[k].values, np.nan)
    cmin = np.where(water, f.tide_Cmin[k].values, np.nan)
    col, top_row = n % 3, 2 * (n // 3)

    ax = axes[top_row, col]
    top = np.nanpercentile(cmax, 99.5)
    pc = ax.pcolormesh(lon, lat, cmax, cmap="magma", vmin=0, vmax=top)
    fig.colorbar(pc, ax=ax, shrink=0.9, extend="max", label="m/s")
    ax.set_title(f"{name} Cmax  (max {np.nanmax(cmax):.2f} m/s)")

    ax = axes[top_row + 1, col]
    lim = np.nanpercentile(np.abs(cmin), 99.5)
    pc = ax.pcolormesh(lon, lat, cmin, cmap=cmin_cmap, vmin=-lim, vmax=lim)
    fig.colorbar(pc, ax=ax, shrink=0.9, extend="both", label="m/s")
    share = 100 * np.nanmean(cmin[water] > 0)
    ax.set_title(f"{name} Cmin  ({share:.0f}% of points anticlockwise)")

for ax in axes.flat:
    map_axes(ax)
    ax.tick_params(labelsize=8)
for ax in axes[:, 1:].flat:
    ax.set_ylabel("")
for ax in axes[:3].flat:
    ax.set_xlabel("")
save(fig, "cmax_cmin.png")
