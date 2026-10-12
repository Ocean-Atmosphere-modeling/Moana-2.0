#!/usr/bin/env python
"""Check which DataMesh datasources the Moana model can use.

Usage (moana_python environment, DATAMESH_TOKEN set):

    python scripts/check_datamesh.py [--date 2024-01-15] | tee datamesh_check.log

Prints four parts (the tables in docs/data.md come from this output):
  1. every datasource the token lists, with the catalogue start and end;
  2. the real time axis of each source the model needs (first, last, step,
     gaps) and its longitude range; the 3D ocean sets are too big to open
     lazily, so their time axis comes from a query of one small box
     (about 4 minutes each);
  3. 403 (exists, no access) or 404 (no such ID) for IDs the token does not list;
  4. one read of a small NZ box at --date for each needed variable.
"""

import argparse
import datetime as dt
import os

import numpy as np
import oceanum
import pandas as pd
from oceanum.datamesh import Connector

# Sources the model needs: (datasource ID, variables, open lazily?).
NEEDED = [
    ("cmems_mod_glo_phy-thetao_anfc_0-083deg_pt6h-i", ["thetao"], False),
    ("cmems_mod_glo_phy-so_anfc_0-083deg_pt6h-i", ["so"], False),
    ("cmems_mod_glo_phy-cur_anfc_0-083deg_pt6h-i", ["uo", "vo"], False),
    ("cmems_mod_glo_phy_anfc_0-083deg_pt1h-m", ["zos"], True),
    ("era5_wind10m", ["u10", "v10"], True),
    ("era5_mslp", ["msl"], True),
    ("era5_temp2m", ["t2m"], True),
    ("era5_precip_rate", ["mtpr"], True),
    ("era5_mean_surface_downward_short_wave_radiation_flux", ["msdwswrf"], True),
    ("tpxo9_atlas_v5_cons", ["h"], True),
    ("tpxo9_v5a_cons", ["h"], True),
    ("oceanum_tide_cons_nz_2km", ["h"], True),
    ("metoffice-glo-sst-l4-nrt-obs-sst-v2", ["analysed_sst"], True),
]
# IDs that the token does not list (requested, or tried as names for missing fields).
UNLISTED = [
    "cmems_mod_glo_phy_my_0-083deg_p1d-m", "cmems_mod_glo_phy_my_0-083deg_p1m-m",
    "cmems_mod_glo_phy_myint_0-083deg_p1d-m",
    "cmems_mod_glo_phy-thetao_anfc_0-083deg_p1d-m", "cmems_mod_glo_phy-so_anfc_0-083deg_p1d-m",
    "cmems_mod_glo_phy-cur_anfc_0-083deg_p1d-m", "cmems_mod_glo_phy_anfc_0-083deg_p1d-m",
    "cmems_mod_glo_phy-thetao_anfc_0-083deg_pt6h-i-timeseries",
    "cmems_mod_glo_phy-cur_anfc_0-083deg_pt6h-i-timeseries",
    "era5_mean_surface_downward_long_wave_radiation_flux",
    "era5_mean_surface_net_short_wave_radiation_flux",
    "era5_dewpoint2m", "era5_dewpoint_temp2m", "era5_2m_dewpoint_temperature", "era5_d2m",
    "era5_specific_humidity", "era5_relative_humidity",
]
POINT = [174.0, -40.0, 174.1, -39.9]  # W, S, E, N: small box west of NZ, for 3D time axes
BOX = [173.5, -41.0, 174.5, -40.0]    # W, S, E, N: test read box (sea, 1 x 1 deg)


def time_axis(t):
    t = pd.to_datetime(t)
    if len(t) < 2:
        return f"{t[0]} (1 time)" if len(t) else "no time axis"
    d = pd.Series(np.diff(t)).value_counts()
    step = d.index[0]
    gaps = np.where(np.diff(t) > step)[0]
    s = f"{t[0]} -> {t[-1]}  n={len(t)}  step={step}  gaps={len(gaps)}"
    return s + "".join(f"\n      gap {t[g]} -> {t[g + 1]}" for g in gaps[:10])


def lon_range(ds):
    for c in ("longitude", "lon"):
        if c in ds.coords:
            v = ds[c].values
            return f"{c} {v.min():.3f} .. {v.max():.3f}"
    return ""


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--date", default="2024-01-15", help="time of the test read (part 4)")
    a = p.parse_args()
    dm = Connector(token=os.environ["DATAMESH_TOKEN"])
    print(f"DataMesh check {dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ}, "
          f"oceanum {oceanum.__version__}")

    print("\n## 1. Datasources the token lists (catalogue start and end)")
    cat = list(dm.get_catalog())
    print(f"{len(cat)} datasources")
    for ds in sorted(cat, key=lambda d: d.id):
        print(f"  {ds.id} | {ds.name} | {ds.tstart} -> {ds.tend}")

    print("\n## 2. Real time axis and longitude range of the sources the model needs")
    for i, var, lazy in NEEDED:
        try:
            if lazy:
                ds = dm.load_datasource(i)
            else:
                ds = dm.query(dict(datasource=i, variables=var[:1],
                                   geofilter={"type": "bbox", "geom": POINT},
                                   timefilter={"type": "range",
                                               "times": ["1970-01-01", "2100-01-01"]}))
            tname = next((c for c in ds.coords if c.startswith("time")), None)
            levels = next((ds[c].values for c in ("elevation", "depth") if c in ds.coords), None)
            print(f"  {i}: {list(ds.data_vars)}")
            print(f"    time: {time_axis(ds[tname].values) if tname else 'none (static)'}")
            if lazy:
                print(f"    {lon_range(ds)}")
            if levels is not None:
                print(f"    levels: {len(levels)}, {np.abs(levels).min():.3f} .. {np.abs(levels).max():.1f} m")
            if "source" in ds.attrs or "title" in ds.attrs:
                print(f"    source: {ds.attrs.get('source', '')} | {ds.attrs.get('title', '')}")
        except Exception as e:
            print(f"  {i}: ERROR {e!r}"[:300])

    print("\n## 3. IDs the token does not list: 403 = exists, no access; 404 = no such ID")
    for i in UNLISTED:
        try:
            dm.get_datasource(i)
            print(f"  OK   {i}")
        except Exception as e:
            s = str(e)
            code = "403" if "permission" in s else "404" if "not found" in s else "ERR"
            print(f"  {code}  {i}")

    print(f"\n## 4. Test read of box {BOX} (W, S, E, N) at {a.date}")
    for i, var, _ in NEEDED:
        if i.startswith(("tpxo", "oceanum_tide", "metoffice")):
            continue
        try:
            ds = dm.query(dict(datasource=i, variables=var,
                               geofilter={"type": "bbox", "geom": BOX},
                               timefilter={"type": "range", "times": [a.date, a.date]}))
            if ds is None:
                print(f"  NONE {i}: no data at {a.date}")
                continue
            for v in var:
                x = ds[v].values
                print(f"  OK   {i} {v}: {np.isfinite(x).sum()}/{x.size} finite, "
                      f"{np.nanmin(x):.4g} .. {np.nanmax(x):.4g}")
        except Exception as e:
            print(f"  FAIL {i}: {e!r}"[:300])


if __name__ == "__main__":
    main()
