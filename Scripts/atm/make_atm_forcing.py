#!/usr/bin/env python3
"""
Convert an ECMWF file (IFS or ERA5 short names) into a ROMS atmospheric forcing file.

    python Scripts/atm/make_atm_forcing.py yaml/make_atm_forcing.yaml

ROMS interpolates forcing onto its own grid, so the ECMWF lon/lat grid is kept.
Names, units and time variables are the ROMS defaults (ROMS/External/varinfo.yaml).
Qair is in percent: varinfo.yaml scales it by 0.01, and bulk_flux.F expects a fraction after that.
"""
import sys
import numpy as np
import pandas as pd
import xarray as xr
import yaml

cfg = yaml.safe_load(open(sys.argv[1]))
ds = xr.open_dataset(cfg["INPUT"])


def relative_humidity(t, td):
    """Relative humidity (%) from air temperature and dew point in Celsius (Magnus formula)."""
    e = lambda x: np.exp(17.67 * x / (x + 243.5))
    return 100 * (e(td) / e(t)).clip(0, 1)


# ECMWF -> ROMS: (converted data, ROMS units, ROMS time variable)
roms = {
    "Uwind":      (ds.u10,                                      "meter second-1",            "wind_time"),
    "Vwind":      (ds.v10,                                      "meter second-1",            "wind_time"),
    "Tair":       (ds.t2m - 273.15,                             "Celsius",                   "tair_time"),
    "Pair":       (ds.msl / 100,                                "millibar",                  "pair_time"),
    "Qair":       (relative_humidity(ds.t2m - 273.15, ds.d2m - 273.15), "percentage",        "qair_time"),
    "rain":       (ds.tp * 1000,                                "kilogram meter-2 second-1", "rain_time"),
    "swrad":      (ds.ssr,                                      "watt meter-2",              "srf_time"),
    "lwrad_down": (ds.strd,                                     "watt meter-2",              "lrf_time"),
}

days = (ds.time.values - np.datetime64(cfg["REF_TIME"])) / np.timedelta64(1, "D")
out = xr.Dataset(coords={"lon": ds.longitude.values, "lat": ds.latitude.values})

for name, (da, units, tname) in roms.items():
    out[tname] = ("time", days, {"units": f"days since {cfg['REF_TIME']}"})
    out[name] = (("time", "lat", "lon"), da.transpose("time", "latitude", "longitude").values.astype("f4"),
                 {"units": units, "time": tname, "coordinates": "lon lat"})
    print(f"{name:11s} {float(out[name].min()):10.4g} to {float(out[name].max()):10.4g}  {units}")

out.to_netcdf(cfg["OUTPUT"])
print(f"Wrote {cfg['OUTPUT']}")
