"""Figure: the M2 phases in the tide file: sea level (Ephase), current (Cphase), and the difference.

Usage (moana_python environment):  python webpage_folder/fig_cphase.py
Writes webpage_folder/figures/cphase.png. Three maps of M2:
  left    Ephase: time of high water, as an angle from 0 to 360 (cyclic colour map), lines every 30 degrees
  middle  Cphase: time of the fastest current, same colour map. Short black lines show Cangle,
          the direction of Cmax (every 14th point). Points with Cmax below 2 cm/s are grey.
  right   the angle between Cphase and Ephase, folded to 0 to 90 (Cangle is only known to 180 degrees,
          so 180 means the same as 0). Near 0: fastest current at high or low water (progressive wave).
          Near 90: fastest current at mid tide, slack water at high and low tide (standing wave).
"""
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from common import MUTED, TIDES, map_axes, save

f = xr.open_dataset(TIDES)
water = f.mask_rho.values == 1
lon, lat = f.lon_rho.values, f.lat_rho.values
eph, cph, cmax, cang = (np.where(water, f[v][0].values, np.nan)
                        for v in ["tide_Ephase", "tide_Cphase", "tide_Cmax", "tide_Cangle"])   # M2 is first
weak = cmax < 0.02
diff = (cph - eph) % 180
diff = np.where(diff > 90, 180 - diff, diff)          # 0 = progressive wave, 90 = standing wave

fig, axes = plt.subplots(1, 3, figsize=(19, 6.2), constrained_layout=True)

ax = axes[0]
pc = ax.pcolormesh(lon, lat, eph, cmap="twilight", vmin=0, vmax=360)
ax.contour(lon, lat, eph, levels=np.arange(30, 360, 30), colors="w", linewidths=0.5)
fig.colorbar(pc, ax=ax, shrink=0.8, ticks=[0, 90, 180, 270, 360], label="degrees")
ax.set_title("M2 Ephase: when high water comes")

ax = axes[1]
pc = ax.pcolormesh(lon, lat, np.where(weak, np.nan, cph), cmap="twilight", vmin=0, vmax=360)
ax.pcolormesh(lon, lat, np.where(weak, 1.5, np.nan), cmap="Greys", vmin=0, vmax=3)
fig.colorbar(pc, ax=ax, shrink=0.8, ticks=[0, 90, 180, 270, 360], label="degrees")
step = 14
for j in range(0, lon.shape[0], step):
    for i in range(0, lon.shape[1], step):
        if not water[j, i] or weak[j, i]:
            continue
        a = np.radians(cang[j, i])
        dx, dy = 0.22 * np.cos(a) / np.cos(np.radians(lat[j, i])), 0.22 * np.sin(a)
        ax.plot([lon[j, i] - dx, lon[j, i] + dx], [lat[j, i] - dy, lat[j, i] + dy], color="k", lw=0.7)
ax.set_title("M2 Cphase: when the fastest current comes  (lines: Cangle)")

ax = axes[2]
pc = ax.pcolormesh(lon, lat, np.where(weak, np.nan, diff), cmap="Blues", vmin=0, vmax=90)
ax.pcolormesh(lon, lat, np.where(weak, 1.5, np.nan), cmap="Greys", vmin=0, vmax=3)
fig.colorbar(pc, ax=ax, shrink=0.8, ticks=[0, 30, 60, 90], label="degrees")
ax.set_title("angle between Cphase and Ephase: 0 progressive, 90 standing")

for ax in axes:
    map_axes(ax)
    ax.set_xlim(lon.min(), lon.max())
    ax.set_ylim(lat.min(), lat.max())
for ax in axes[1:]:
    ax.set_ylabel("")
    ax.text(0.02, 0.02, "grey: Cmax < 2 cm/s", transform=ax.transAxes, fontsize=8.5, color=MUTED)
save(fig, "cphase.png")
