#!/usr/bin/env python
"""Check a ROMS tide file against pyTMD's prediction from TPXO.

Usage (moana_python environment):

    python scripts/check_tide_file.py FILE [--tpxo FILE] [--grid FILE]

At the 15 LINZ gauges of the hindcast paper (nearest wet model cell) and
every 25th wet open-boundary cell, rebuilds hourly zeta, u, v over the
file's run period from FILE with the formulas of ROMS/Nonlinear/set_tides.F,
and compares them with pyTMD.predict.time_series run on the TPXO complex
amplitudes at the same cells (same interpolation as make_tide_file.py,
so only the conversion is tested). pyTMD updates f and u every hour; the
file holds them fixed at mid-period. So:

  - within 3 days of mid-period the two must agree to within the drift
    of f and u in 3 days (limit 1 mm, 1 mm/s); a wrong sign, phase origin
    or ellipse convention gives errors as large as the tide itself (checked
    2026-10-08 by flipping tide_Ephase and tide_Cmin: 2.8 m and 0.6 m/s);
  - over the whole period the difference is the cost of fixed f and u,
    which ROMS cannot avoid; it is reported, not tested.

Currents are compared in the geographic frame; ROMS rotates by angler,
which is below 0.03 deg on this grid. Exits 1 if a limit is exceeded.
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pyTMD.predict
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_tide_file import GRID, TPXO, mjd, MJD_TIDE, on_grid  # noqa: E402

GAUGES = [  # hindcast paper Table 2, as Apps/moana/python_scripts/plot_tides.py
    ("Port Chalmers", -45.82, 170.65), ("Chatham Islands", -44.03, 183.63),
    ("Sumner", -43.57, 172.57), ("Kaikoura", -42.42, 173.70),
    ("Wellington", -41.28, 174.78), ("Castlepoint", -40.92, 176.22),
    ("Napier", -39.48, 176.92), ("Gisborne", -38.67, 178.03),
    ("Lottin Point", -37.55, 178.17), ("Auckland", -36.83, 174.78),
    ("Great Barrier Island", -36.18, 175.48), ("North Cape", -34.42, 173.05),
    ("Manukau", -37.05, 174.52), ("Charleston", -41.90, 171.43),
    ("Puysegur", -46.08, 166.58),
]
LIMIT = {"zeta": 1e-3, "u": 1e-3, "v": 1e-3}
NEAR_DAYS = 3


def cells(grd):
    """(j, i) of the nearest wet cell to each gauge, then boundary cells."""
    lat, lon, ocean = grd.lat_rho.values, grd.lon_rho.values, grd.mask_rho.values > 0.5
    out, names = [], []
    for name, la, lo in GAUGES:
        d = np.where(ocean, (lat - la) ** 2 + ((lon - lo) * np.cos(np.radians(la))) ** 2,
                     np.inf)
        out.append(np.unravel_index(d.argmin(), d.shape))
        names.append(name)
    edge = np.zeros_like(ocean)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    for j, i in list(zip(*np.nonzero(edge & ocean)))[::25]:
        out.append((j, i))
        names.append(f"boundary j={j} i={i}")
    return np.array(out), names


def roms(tide, jj, ii, hours):
    """zeta, u, v (time, point) as set_tides.F builds them (angler = 0)."""
    sel = lambda k: tide[k].values[:, jj, ii]  # (con, point)
    w = 2 * np.pi / tide.tide_period.values  # rad per hour
    arg = w[None, :, None] * hours[:, None, None]  # (time, con, point)
    rad = np.radians
    zeta = (sel("tide_Eamp") * np.cos(arg - rad(sel("tide_Ephase")))).sum(1)
    psi = arg - rad(sel("tide_Cphase"))
    ca, sa = np.cos(rad(sel("tide_Cangle"))), np.sin(rad(sel("tide_Cangle")))
    M, m = sel("tide_Cmax"), sel("tide_Cmin")
    u = (M * ca * np.cos(psi) - m * sa * np.sin(psi)).sum(1)
    v = (M * sa * np.cos(psi) + m * ca * np.sin(psi)).sum(1)
    return {"zeta": zeta, "u": u, "v": v}


def pytmd(z, cons, t):
    """pyTMD prediction (time, point) from complex amplitudes (con, point)."""
    ds = xr.Dataset({c.lower(): ("point", z[k]) for k, c in enumerate(cons)})
    r = pyTMD.predict.time_series(t, ds, corrections="OTIS")
    return np.asarray(r.transpose("time", "point"))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("file", type=Path)
    p.add_argument("--tpxo", type=Path, default=TPXO)
    p.add_argument("--grid", type=Path, default=GRID)
    a = p.parse_args()
    tide = xr.open_dataset(a.file)
    grd = xr.open_dataset(a.grid)
    cons = [bytes(n).decode().strip("\x00 ") if not isinstance(n, str) else n
            for n in tide.tide_name.values]
    start = dt.datetime.fromisoformat(tide.attrs["run_start"])
    end = dt.datetime.fromisoformat(tide.attrs["run_end"])
    nodal = start + (end - start) / 2
    zpd = float(tide.zero_phase_date)
    assert zpd == float(f"{start:%Y%m%d}"), (zpd, start)

    ji, names = cells(grd)
    jj, ii = ji[:, 0], ji[:, 1]
    h, u, v, _, _ = on_grid(a.tpxo, cons, grd.lat_rho.values[jj, ii],
                            grd.lon_rho.values[jj, ii], grd.h.values[jj, ii])
    hours = np.arange(0, (end - start).total_seconds() / 3600 + 1, 1.0)
    t = mjd(start) - MJD_TIDE + hours / 24  # days since 1992-01-01
    near = np.abs(hours - (nodal - start).total_seconds() / 3600) <= NEAR_DAYS * 24
    got = roms(tide, jj, ii, hours)
    ref = {"zeta": pytmd(h, cons, t), "u": pytmd(u, cons, t), "v": pytmd(v, cons, t)}

    print(f"{a.file.name}: {len(cons)} constituents, {len(names)} cells, "
          f"{start:%Y-%m-%d} to {end:%Y-%m-%d}, f and u at {nodal:%Y-%m-%d %H:%M}")
    print(f"{'':5s} {'rms':>8s} {'max|diff| +-3 d':>18s} {'max|diff| period':>17s}  where")
    ok = True
    for k in ("zeta", "u", "v"):
        d = np.abs(got[k] - ref[k])
        dn, dall = d[near].max(), d.max()
        worst = names[int(np.unravel_index(d.argmax(), d.shape)[1])]
        unit = "m" if k == "zeta" else "m/s"
        flag = "ok" if dn <= LIMIT[k] else "FAIL"
        ok &= flag == "ok"
        print(f"{k:5s} {np.sqrt((ref[k] ** 2).mean()):8.4f} {dn:14.5f} {unit:3s}"
              f" {dall:13.4f} {unit:3s}  {worst}  {flag}")
    # Wellington, first 12 h, for the eye.
    w = names.index("Wellington")
    print("Wellington zeta, first 12 h (file / pyTMD):",
          " ".join(f"{x:+.3f}/{y:+.3f}" for x, y in zip(got["zeta"][:12, w],
                                                       ref["zeta"][:12, w])))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
