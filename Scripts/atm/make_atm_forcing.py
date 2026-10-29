#!/usr/bin/env python3
"""
Convert an ECMWF file (IFS or ERA5 short names) into a ROMS atmospheric forcing file.

    python Scripts/atm/make_atm_forcing.py yaml/make_atm_forcing.yaml

ROMS interpolates forcing onto its own grid, so the ECMWF lon/lat grid is kept.
Names and units are the ROMS defaults (ROMS/External/varinfo.yaml). All fields share one time
variable, "time" (unlimited dimension), named in each field's "time" attribute.
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


# ECMWF -> ROMS: (converted data, ROMS units)
roms = {
    "Uwind":      (ds.u10,                                      "meter second-1"),
    "Vwind":      (ds.v10,                                      "meter second-1"),
    "Tair":       (ds.t2m - 273.15,                             "Celsius"),
    "Pair":       (ds.msl / 100,                                "millibar"),
    "Qair":       (relative_humidity(ds.t2m - 273.15, ds.d2m - 273.15), "percentage"),
    "rain":       (ds.tp * 1000,                                "kilogram meter-2 second-1"),
    "swrad":      (ds.ssr,                                      "watt meter-2"),
    "lwrad_down": (ds.strd,                                     "watt meter-2"),
}

days = (ds.time.values - np.datetime64(cfg["REF_TIME"])) / np.timedelta64(1, "D")
#out = xr.Dataset(coords={"lon": ds.longitude.values, "lat": ds.latitude.values})
out = xr.Dataset(coords={"lon": ("lon", ds.longitude.values, {"units": "degree_east"}),
                         "lat": ("lat", ds.latitude.values, {"units": "degree_north"})})

out["time"] = ("time", days, {"units": f"days since {cfg['REF_TIME']}", "calendar": "proleptic_gregorian"})

for name, (da, units) in roms.items():
    out[name] = (("time", "lat", "lon"), da.transpose("time", "latitude", "longitude").values.astype("f4"),
                 {"units": units, "time": "time", "coordinates": "lon lat"})
    print(f"{name:11s} {float(out[name].min()):10.4g} to {float(out[name].max()):10.4g}  {units}")

out.to_netcdf(cfg["OUTPUT"], unlimited_dims=["time"],
              encoding={v: {"_FillValue": None} for v in ["time", "lon", "lat"]})
print(f"Wrote {cfg['OUTPUT']}")
