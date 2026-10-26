"""Figure: the 18.6-year nodal factors f and u, and the date make_tides.py takes them at.

Usage (moana_python environment):  python webpage_folder/fig_nodal.py
Writes webpage_folder/figures/nodal.png. Two panels, 2010 to 2035:
  top     amplitude factor f for M2, K1, O1, K2
  bottom  phase shift u (degrees) for the same constituents
The grey band is the model run (2026-01-01 to 2026-04-01). The dashed line is NODAL_DATE.
S2 is not drawn: it is a solar tide, so f = 1 and u = 0 at all times.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyTMD

from common import MUTED, SERIES, save

NAMES = ["M2", "K1", "O1", "K2"]
NODAL_DATE = pd.Timestamp("2026-02-15")
RUN = (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-04-01"))

dates = pd.date_range("2010-01-01", "2035-01-01", freq="10D")
mjd = (dates - pd.Timestamp("1858-11-17")).days.values.astype(float)
u, f, _ = pyTMD.constituents.arguments(mjd, [n.lower() for n in NAMES])

fig, axes = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True, constrained_layout=True)
for k, name in enumerate(NAMES):
    axes[0].plot(dates, f[:, k], color=SERIES[k], lw=2)
    axes[1].plot(dates, np.degrees(u[:, k]), color=SERIES[k], lw=2)
    axes[0].text(dates[-1], f[-1, k], f"  {name}", va="center", fontsize=9.5)
    axes[1].text(dates[-1], np.degrees(u[-1, k]), f"  {name}", va="center", fontsize=9.5)

for ax in axes:
    ax.axvspan(*RUN, color=MUTED, alpha=0.18, lw=0)
    ax.axvline(NODAL_DATE, color=MUTED, ls="--", lw=1)
    ax.grid(axis="y", color=MUTED, alpha=0.2)
axes[0].axhline(1, color=MUTED, lw=0.8)
axes[0].set_ylabel("amplitude factor f")
axes[1].set_ylabel("phase shift u (degrees)")
axes[0].set_title("Nodal factors over one 18.6-year cycle")
axes[0].text(NODAL_DATE, axes[0].get_ylim()[1], " NODAL_DATE 2026-02-15", va="top", fontsize=9, color=MUTED)

save(fig, "nodal.png")
