"""Figure: sea level that ROMS will build from the tide file, at three places.

Usage (moana_python environment):  python webpage_folder/fig_tide_series.py
Writes webpage_folder/figures/tide_series.png. One row per place in PLACES:
  left   zeta(t) = sum of Eamp * cos(omega * t - Ephase) over the 15 constituents, hourly,
         for the model run (2026-01-01 to 2026-04-01). t is counted from zero_phase_date.
  right  the 6 largest constituent amplitudes at that place
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from common import INK, PLACES, SERIES, TIDES, nearest_water, save

f = xr.open_dataset(TIDES)
names = [str(c) for c in f.tidal_constituents.values]
omega = 2 * np.pi / f.tide_period.values                      # radians per hour
zero = pd.to_datetime(str(int(f.zero_phase_date.item())), format="%Y%m%d")
times = pd.date_range("2026-01-01", "2026-04-01", freq="1h")
hours = (times - zero) / pd.Timedelta("1h")

fig, axes = plt.subplots(3, 2, figsize=(13, 8), width_ratios=[4, 1], constrained_layout=True)
for row, (place, (lon, lat)) in enumerate(PLACES.items()):
    j, i = nearest_water(f, lon, lat)
    amp = f.tide_Eamp[:, j, i].values
    phase = np.radians(f.tide_Ephase[:, j, i].values)
    zeta = (amp[:, None] * np.cos(omega[:, None] * hours.values[None, :] - phase[:, None])).sum(axis=0)

    ax = axes[row, 0]
    ax.plot(times, zeta, color=SERIES[0], lw=0.6)
    ax.set_ylabel("sea level (m)")
    ax.set_title(f"{place}  ({f.lon_rho[j, i].item():.2f}°E, {f.lat_rho[j, i].item():.2f}°N)", loc="left")
    ax.grid(axis="y", alpha=0.2)

    top = np.argsort(amp)[::-1][:6]
    ax = axes[row, 1]
    ax.barh([names[k] for k in top][::-1], amp[top][::-1] * 100, color=SERIES[0], height=0.6)
    for y, k in enumerate(top[::-1]):
        ax.text(amp[k] * 100, y, f" {amp[k] * 100:.0f}", va="center", fontsize=8.5, color=INK)
    ax.set_xlabel("amplitude (cm)")
    ax.set_xlim(0, amp.max() * 130)

save(fig, "tide_series.png")
