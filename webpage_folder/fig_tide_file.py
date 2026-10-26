"""Figure: overview of the ROMS tide file (same as misc_scripts/plot_tide_file.py).

Usage (moana_python environment):  python webpage_folder/fig_tide_file.py
Writes webpage_folder/figures/tide_file.png. Three panels:
  left    M2 elevation amplitude, phase every 30° (white lines)
  middle  K1 elevation amplitude, phase every 30° (white lines)
  right   M2 current, ellipse semi-major axis (tide_Cmax)
Phases are relative to zero_phase_date (2026-01-01), not Greenwich phases.
"""
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from common import TIDES, map_axes, save

f = xr.open_dataset(TIDES)
names = [str(c) for c in f.tidal_constituents.values]
water = f.mask_rho == 1
lon, lat = f.lon_rho, f.lat_rho

fig, axes = plt.subplots(1, 3, figsize=(15, 5.6), constrained_layout=True)
for ax, con in zip(axes[:2], ["M2", "K1"]):
    k = names.index(con)
    pc = ax.pcolormesh(lon, lat, f.tide_Eamp[k].where(water), cmap="viridis")
    ax.contour(lon, lat, f.tide_Ephase[k].where(water), levels=np.arange(30, 360, 30), colors="w", linewidths=0.6)
    fig.colorbar(pc, ax=ax, label="m", shrink=0.8)
    ax.set_title(f"{con} elevation amplitude and phase")

pc = axes[2].pcolormesh(lon, lat, f.tide_Cmax[0].where(water), cmap="magma", vmax=1.0)
fig.colorbar(pc, ax=axes[2], label="m/s", shrink=0.8, extend="max")
axes[2].set_title("M2 current, semi-major axis")

for ax in axes:
    map_axes(ax)

save(fig, "tide_file.png")
