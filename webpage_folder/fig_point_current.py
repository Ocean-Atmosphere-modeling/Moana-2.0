"""Figure: the M2 current at two points, built from the ellipse the way ROMS builds it.

Usage (moana_python environment):  python webpage_folder/fig_point_current.py
Writes webpage_folder/figures/point_current.png. One row per place (Taranaki Bight, Cook Strait):
  left    hodograph: the tip of the current vector over one M2 period (12.42 h), with a dot every hour.
          The magenta arrow is the current at t = 0 (2026-01-01 00:00). The blue arrow is the current at
          t = Cphase / omega, when it lies along Cmax.
  middle  east (u) and north (v) current and speed over 25 hours (two M2 periods)
  right   direction of the current (degrees from east) over the same 25 hours
u and v come from the ROMS formula in set_tides.F:
  u = Cmax cos(Cangle) cos(phi) - Cmin sin(Cangle) sin(phi),  v = Cmax sin(Cangle) cos(phi) + Cmin cos(Cangle) sin(phi),
  phi = omega t - Cphase.  (The Moana grid angle is below 0.03 degrees, so it is left out here.)
"""
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from common import INK, MARK, MUTED, PLACES, SERIES, TIDES, nearest_water, save

f = xr.open_dataset(TIDES)
names = [str(c) for c in f.tidal_constituents.values]
k = names.index("M2")
period = float(f.tide_period[k])                 # hours
omega = 2 * np.pi / period                       # radians per hour
t = np.linspace(0, 25, 1001)                     # hours from 2026-01-01 00:00


def roms_uv(cmax, cmin, cangle, cphase, t):
    th, phi = np.radians(cangle), omega * t - np.radians(cphase)
    u = cmax * np.cos(th) * np.cos(phi) - cmin * np.sin(th) * np.sin(phi)
    v = cmax * np.sin(th) * np.cos(phi) + cmin * np.cos(th) * np.sin(phi)
    return u, v


fig, axes = plt.subplots(2, 3, figsize=(16, 9.5), width_ratios=[1, 1.5, 1.1], constrained_layout=True)
for row, place in enumerate(["Taranaki Bight", "Cook Strait"]):
    j, i = nearest_water(f, *PLACES[place])
    cmax, cmin, cangle, cphase = (float(f[v][k, j, i]) for v in ["tide_Cmax", "tide_Cmin", "tide_Cangle", "tide_Cphase"])
    u, v = roms_uv(cmax, cmin, cangle, cphase, t)
    t_max = np.radians(cphase) / omega                                        # hours: when the current is Cmax
    uh, vh = roms_uv(cmax, cmin, cangle, cphase, np.arange(0, period, 1.0))
    u0, v0 = roms_uv(cmax, cmin, cangle, cphase, np.array([0.0, t_max]))

    ax = axes[row, 0]
    lim = cmax * 1.25
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.axvline(0, color=MUTED, lw=0.6)
    one = t < period
    ax.plot(u[one], v[one], color=INK, lw=1.2)
    ax.scatter(uh, vh, s=14, color=INK, zorder=3)
    for n, (x, y) in enumerate(zip(uh, vh)):
        ax.annotate(f"{n}", (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7.5, color=MUTED)
    ax.annotate("", (u0[0], v0[0]), (0, 0), arrowprops=dict(arrowstyle="->", color=MARK, lw=2))
    ax.annotate("", (u0[1], v0[1]), (0, 0), arrowprops=dict(arrowstyle="->", color=SERIES[0], lw=2))
    a = np.radians(cangle)
    ax.plot([-cmax * np.cos(a), cmax * np.cos(a)], [-cmax * np.sin(a), cmax * np.sin(a)], color=SERIES[0], lw=0.8, ls="--")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xlabel("east current u (m/s)")
    ax.set_ylabel("north current v (m/s)")
    turn = "anticlockwise" if cmin > 0 else "clockwise"
    ax.set_title(f"{place}: M2 ellipse, numbers are hours", loc="left")
    ax.text(0.02, 0.02, f"Cmax {cmax:.2f}  Cmin {cmin:+.3f} ({turn})\nCangle {cangle:.0f}°  Cphase {cphase:.0f}°",
            transform=ax.transAxes, fontsize=8.5, va="bottom", color=INK)

    ax = axes[row, 1]
    ax.plot(t, u, color=SERIES[0], lw=1.6, label="u (east)")
    ax.plot(t, v, color=SERIES[1], lw=1.6, label="v (north)")
    ax.plot(t, np.hypot(u, v), color=INK, lw=1.2, ls="--", label="speed")
    ax.axhline(0, color=MUTED, lw=0.6)
    for tm in [t_max, t_max + period]:
        ax.axvline(tm, color=SERIES[0], lw=0.9, ls=":")
    ax.axvline(0, color=MARK, lw=1.2)
    ax.text(t_max, cmax * 1.08, f" Cphase/ω = {t_max:.1f} h", color=SERIES[0], fontsize=8.5)
    ax.text(0, -cmax * 1.2, " t = 0", color=MARK, fontsize=8.5)
    ax.set_ylim(-cmax * 1.25, cmax * 1.35)
    ax.set_ylabel("current (m/s)")
    ax.legend(loc="lower right", fontsize=8.5, ncol=3, framealpha=0.95)
    ax.set_title("the same current as ROMS builds it, 2026-01-01 00:00 onwards", loc="left")

    ax.set_xlabel("hours since 2026-01-01 00:00")
    ax.set_xlim(0, 25)

    ax = axes[row, 2]
    ax.plot(t, np.degrees(np.arctan2(v, u)) % 360, color=INK, lw=1.4)
    ax.axhline(cangle, color=SERIES[0], lw=0.9, ls="--")
    ax.axhline((cangle + 180) % 360, color=SERIES[0], lw=0.9, ls="--")
    ax.text(25, cangle, f"Cangle {cangle:.0f}° ", ha="right", va="bottom", color=SERIES[0], fontsize=8.5)
    ax.text(25, (cangle + 180) % 360, f"Cangle + 180° ", ha="right", va="bottom", color=SERIES[0], fontsize=8.5)
    for tm in [t_max, t_max + period]:
        ax.axvline(tm, color=SERIES[0], lw=0.9, ls=":")
    ax.axvline(0, color=MARK, lw=1.2)
    ax.set_ylim(0, 360)
    ax.set_yticks([0, 90, 180, 270, 360])
    ax.set_ylabel("direction, degrees from east")
    ax.set_xlabel("hours since 2026-01-01 00:00")
    ax.set_xlim(0, 25)
    ax.set_title("direction of the current", loc="left")

save(fig, "point_current.png")
