"""Figure: sea-level amplitude of all 15 constituents in the ROMS tide file.

Usage (moana_python environment):  python webpage_folder/fig_all_amplitudes.py
Writes webpage_folder/figures/all_amplitudes.png. One small map per constituent, each with
its own colour scale (the largest value is in the title), grouped by type.
"""
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from common import LAND, TIDES, save

ORDER = ["M2", "S2", "N2", "K2", "2N2",       # twice a day
         "K1", "O1", "P1", "Q1", "S1",        # once a day
         "M4", "MS4", "MN4", "MF", "MM"]      # shallow water and long period

f = xr.open_dataset(TIDES)
names = [str(c) for c in f.tidal_constituents.values]
water = f.mask_rho == 1

fig, axes = plt.subplots(3, 5, figsize=(14, 9.6), constrained_layout=True)
for ax, name in zip(axes.flat, ORDER):
    k = names.index(name)
    amp = f.tide_Eamp[k].where(water) * 100          # cm
    pc = ax.pcolormesh(f.lon_rho, f.lat_rho, amp, cmap="viridis", vmin=0)
    fig.colorbar(pc, ax=ax, shrink=0.8, pad=0.02)
    ax.set_title(f"{name}  ({f.tide_period[k].item():.2f} h, max {float(amp.max()):.1f} cm)", fontsize=9.5)
    ax.set_facecolor(LAND)
    ax.set_aspect(1 / np.cos(np.radians(41)))
    ax.set_xticks([])
    ax.set_yticks([])

for row, label in enumerate(["Twice a day", "Once a day", "Shallow water and long period"]):
    axes[row, 0].set_ylabel(label, fontsize=10.5, fontweight="bold")

fig.suptitle("Sea-level amplitude of each constituent (cm)", fontweight="bold")
save(fig, "all_amplitudes.png")
