"""Figure: what the TPXO input looks like before make_tides.py touches it.

Usage (moana_python environment):  python webpage_folder/fig_tpxo_input.py
Writes webpage_folder/figures/tpxo_input.png. Two panels on the TPXO grid:
  left   M2 sea-level amplitude |hRe + i hIm|
  right  TPXO water depth (dep)
The magenta line is the edge of the ROMS grid.
"""
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from common import GRID, MARK, TPXO, map_axes, save

tpxo = xr.open_dataset(TPXO)
grid = xr.open_dataset(GRID)
land = np.isnan(tpxo.hRe.sel(con="M2"))
m2_amp = np.abs(tpxo.hRe.sel(con="M2") + 1j * tpxo.hIm.sel(con="M2"))
depth = tpxo.dep.where(~land)

# ROMS grid edge: walk round the outer rho points
lon, lat = grid.lon_rho.values, grid.lat_rho.values
edge_lon = np.concatenate([lon[0, :], lon[:, -1], lon[-1, ::-1], lon[::-1, 0]])
edge_lat = np.concatenate([lat[0, :], lat[:, -1], lat[-1, ::-1], lat[::-1, 0]])

fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), constrained_layout=True)
pc = axes[0].pcolormesh(tpxo.lon, tpxo.lat, m2_amp, cmap="viridis")
fig.colorbar(pc, ax=axes[0], label="m", shrink=0.8)
axes[0].set_title("TPXO M2 sea-level amplitude")

pc = axes[1].pcolormesh(tpxo.lon, tpxo.lat, depth, cmap="Blues", vmax=6000)
fig.colorbar(pc, ax=axes[1], label="m", shrink=0.8, extend="max")
axes[1].set_title("TPXO water depth")

for ax in axes:
    map_axes(ax)
    ax.plot(edge_lon, edge_lat, color=MARK, lw=1.5)
axes[1].text(edge_lon.min() + 0.4, edge_lat.max() - 0.8, "ROMS grid edge", color=MARK, fontsize=9)

save(fig, "tpxo_input.png")
