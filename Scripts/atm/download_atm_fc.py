#!/usr/bin/env python3
"""
Forecast part of the atmospheric forcing, joined after the past days from download_atm.py.

download_atm.py keeps +3h to +12h of each cycle up to CYCLE, so its file ends at CYCLE+12h.
This script takes CYCLE again from +15h to +135h (the forecast days), then joins the two into
OUTPUT_DIR/<name>_<VAR_NAME>_raw_<DATE>_fc.nc for make_atm_forcing.py.
Settings (datasource, variables, grid, output folder, DATE, PERIOD) come from download_atm.yaml.
"""
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
import xarray as xr
from oceanum.datamesh import Connector

CYCLE = pd.Timestamp("2026-11-09 12:00")                    # newest cycle, the last one download_atm.py uses
LEAD0, LEAD1 = pd.Timedelta("15h"), pd.Timedelta("135h")    # 10 Nov 03:00 -> 15 Nov 03:00
path = '/home/nn411/Projects/OceanAtm/Moana-2.0/yaml/download_atm.yaml'


def bbox_from_grid(path, pad=0.5):                          # same as in download_atm.py
    g = xr.open_dataset(path)
    lon, lat = g["lon_rho"], g["lat_rho"]
    lon = lon.where(lon >= 0, lon + 360)
    return [float(lon.min()) - pad, float(lat.min()) - pad, float(lon.max()) + pad, float(lat.max()) + pad]


def main():
    cfg = yaml.safe_load(open(path))
    outdir = Path(cfg['OUTPUT_DIR'])
    fc_file = outdir / "cycles" / f"ifs_{CYCLE:%Y%m%d%H}_fc015-135.nc"

    # 1. download the forecast part (skipped if already there)
    if not fc_file.exists():
        dm = Connector()
        ds = dm.query(
            datasource=cfg['DATASOURCE'],
            variables=cfg['VARIABLES'],
            parameters={"cycle": f"{CYCLE:%Y%m%d%H}"},
            geofilter={"type": "bbox", "geom": bbox_from_grid(cfg['GRID'])},
            timefilter={"type": "range", "times": [CYCLE + LEAD0, CYCLE + LEAD1]},
        )
        if ds is None:
            raise SystemExit(f"{CYCLE:%Y%m%d%H} NO DATA for +15h to +135h")
        ds.to_netcdf(fc_file)
        print(f"saved {fc_file}")

    # 2. join with the past days
    hind_file = outdir / f"{cfg['name']}_{cfg['VAR_NAME']}_raw_{cfg['DATE']}_{cfg['PERIOD']}.nc"
    if not hind_file.exists():
        raise SystemExit(f"{hind_file} not there yet: run download_atm.py first, then this again")
    h = xr.open_dataset(hind_file)
    f = xr.open_dataset(fc_file)
    ds = xr.concat([h, f], dim="time", coords="minimal", compat="override").sortby("time")

    # 3. checks
    t = pd.to_datetime(ds["time"].values)
    steps = np.unique(np.diff(t) / pd.Timedelta("1h"))
    print(f"past days: {pd.Timestamp(h.time.values[0])} -> {pd.Timestamp(h.time.values[-1])}, {h.sizes['time']} records")
    print(f"forecast:  {pd.Timestamp(f.time.values[0])} -> {pd.Timestamp(f.time.values[-1])}, {f.sizes['time']} records")
    print(f"joined:    {t[0]} -> {t[-1]}, {len(t)} records, steps (h): {steps}, duplicates: {t.duplicated().sum()}")
    for v in ds.data_vars:
        if "time" in ds[v].dims:
            a = ds[v]
            allnan = int(a.isnull().all(dim=[d for d in a.dims if d != "time"]).sum())
            print(f"  {v:5s} [{a.attrs.get('units', '?')}]  min {float(a.min()):.4g}  max {float(a.max()):.4g}  NaN-only records {allnan}")
    night = ds["ssr"].sel(time=ds.time.dt.hour == 15).max(dim=[d for d in ds["ssr"].dims if d != "time"])
    print("ssr domain max at 15:00 UTC (night everywhere), should be ~0 in BOTH parts:")
    for tt, v in zip(pd.to_datetime(night.time.values), night.values):
        part = "forecast" if tt > pd.Timestamp(h.time.values[-1]) else "past    "
        print(f"  {tt}  {part}  {v:.4g}")

    # 4. write the joined raw file
    out = outdir / f"{cfg['name']}_{cfg['VAR_NAME']}_raw_{cfg['DATE']}_fc.nc"
    ds.attrs["forecast_reference_time"] = (f"+3h to +12h of each 00Z/12Z cycle up to {CYCLE:%Y-%m-%d %HZ}, "
                                           f"then {CYCLE:%Y-%m-%d %HZ} from +15h to +135h")
    ds.to_netcdf(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()