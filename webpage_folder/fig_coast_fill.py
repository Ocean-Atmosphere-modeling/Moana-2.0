"""Figure: why make_tides.py fills TPXO land before it interpolates.

Usage (moana_python environment):  python webpage_folder/fig_coast_fill.py
Writes webpage_folder/figures/coast_fill.png. A zoom on Cook Strait:
  left   TPXO cells (water / land) and the ROMS water points. Ringed points are ROMS water
         points where at least one of the 4 TPXO cells used by the bilinear step is TPXO land.
         Without the fill, these points would get NaN.
  right  M2 amplitude on the TPXO grid after the fill, with the TPXO coastline
Prints how many ROMS water points need the fill in the whole domain.
"""
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import ListedColormap

from common import GRID, INK, LAND, MARK, SEA, TPXO, fill_land, map_axes, save

BOX = (173.6, 175.6, -42.0, -40.4)   # west, east, south, north

tpxo = xr.open_dataset(TPXO)
grid = xr.open_dataset(GRID)
tlon, tlat = tpxo.lon.values, tpxo.lat.values
tpxo_land = np.isnan(tpxo.hRe.sel(con="M2").values)

# ROMS water points whose 4 surrounding TPXO cells include TPXO land
water = grid.mask_rho.values == 1
lon, lat = grid.lon_rho.values[water], grid.lat_rho.values[water]
i = np.searchsorted(tlon, lon) - 1
j = np.searchsorted(tlat, lat) - 1
touches_land = tpxo_land[j, i] | tpxo_land[j, i + 1] | tpxo_land[j + 1, i] | tpxo_land[j + 1, i + 1]
print(f"{touches_land.sum()} of {water.sum()} ROMS water points touch TPXO land")

# M2 amplitude after the fill
m2 = (tpxo.hRe + 1j * tpxo.hIm).sel(con=["M2"]).values
m2_filled = np.abs(fill_land(m2)[0])

fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), constrained_layout=True)

ax = axes[0]
ax.pcolormesh(tlon, tlat, tpxo_land, cmap=ListedColormap([SEA, LAND]), edgecolors="white", linewidth=0.3)
inside = (lon > BOX[0]) & (lon < BOX[1]) & (lat > BOX[2]) & (lat < BOX[3])
ax.plot(lon[inside & ~touches_land], lat[inside & ~touches_land], ".", color=INK, ms=3, label="ROMS water point")
ax.plot(lon[inside & touches_land], lat[inside & touches_land], "o", mfc="none", mec=MARK, mew=1.4, ms=6,
        label="ROMS water point next to TPXO land")
ax.legend(loc="lower right", fontsize=8.5, framealpha=0.95)
ax.set_title("TPXO cells and ROMS points")

ax = axes[1]
pc = ax.pcolormesh(tlon, tlat, m2_filled, cmap="viridis", vmin=0.2, vmax=1.2)
ax.contour(tlon, tlat, tpxo_land, levels=[0.5], colors="white", linewidths=1)
fig.colorbar(pc, ax=ax, label="m", shrink=0.8)
ax.set_title("M2 amplitude after the fill (white: TPXO coast)")

for ax in axes:
    map_axes(ax)
    ax.set_xlim(BOX[0], BOX[1])
    ax.set_ylim(BOX[2], BOX[3])

save(fig, "coast_fill.png")
