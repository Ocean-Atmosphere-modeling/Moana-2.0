#!/usr/bin/env python
"""Figure that compares two sets of Moana vertical levels.

Usage (moana_python environment, see env/moana_python.yml):

    python Apps/moana/python_scripts/plot_slevels.py [--out DIR]

Reads Apps/moana/Input/moana_grid.nc and writes moana_slevels.{pdf,png} to
--out (default Apps/moana/Figures).

Both panels are the zonal section of panel d of moana_grid (plot_grid.py)
along SECTION_LAT, with the same depth axis:
  a  previous levels: grid-file N, theta_s, theta_b, hc with Vstretching =
     plot_grid.VSTRETCHING (as in moana_grid panel d)
  b  trial levels: TRIAL below, with the grid-file N
Both use Vtransform = 2, so hc = Tcline. Neither set is chosen for the model
yet (docs/roadmap.md, M2-T2).
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_glorys_ic_bc import save
from plot_grid import (APP, MM, SECTION_LAT, axes_mm, grid_levels, load_grid,
                       panel_label, panel_section, s_coord, z_w)

TRIAL = {"Vstretching": 4, "theta_s": 7.0, "theta_b": 2.0, "hc": 250.0}
REF_DEPTHS = (100.0, 1000.0, 4000.0)  # m; layer thicknesses printed here


def layers(v, h):
    """Top and bottom layer thickness (m) for depth h."""
    s_w, Cs_w = s_coord(v["N"], v["theta_s"], v["theta_b"], v["Vstretching"])
    dz = np.diff(z_w(np.array([h]), v["hc"], s_w, Cs_w)[:, 0])
    return dz[-1], dz[0]


def fig_slevels(g, out):
    j = int(np.argmin(np.abs(g["lat_rho"][:, 0] - SECTION_LAT)))
    prev = grid_levels(g)
    trial = {"N": g["N"], **TRIAL}

    fig = plt.figure(figsize=(180 * MM, 104 * MM))
    ax_a = axes_mm(fig, 12, 59, 166, 41)
    ax_b = axes_mm(fig, 12, 9, 166, 41, sharex=ax_a, sharey=ax_a)
    panel_section(ax_a, g, j, prev, note="previous")
    panel_section(ax_b, g, j, trial, note="trial values")
    ax_a.tick_params(labelbottom=False)
    for ax, letter in ((ax_a, "a"), (ax_b, "b")):
        panel_label(ax, letter, x=-0.04)

    out.mkdir(parents=True, exist_ok=True)
    save(fig, out / "moana_slevels")

    for name, v in (("previous", prev), ("trial", trial)):
        print(f"{name:8s} " + ", ".join(
            f"h {h:g} m: top {t:.2f} m, bottom {b:.1f} m"
            for h, (t, b) in ((h, layers(v, h)) for h in REF_DEPTHS)))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", type=Path, default=APP / "Figures")
    args = p.parse_args()
    g = load_grid(APP / "Input" / "moana_grid.nc")
    fig_slevels(g, args.out)


if __name__ == "__main__":
    main()
