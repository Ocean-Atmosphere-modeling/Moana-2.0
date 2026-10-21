#!/usr/bin/env python3
# ^ lets you run it as ./download_atm.py on Linux, using the active Python

"""
Download atmospheric forcing (ECMWF IFS) from Oceanum DataMesh for a ROMS run.

  export DATAMESH_TOKEN=...
  python download_atm.py

Output: OUTPUT_DIR/cycles/ifs_<CYCLE>.nc for each forecast cycle, and
OUTPUT_DIR/<name>_<VAR_NAME>_raw_<DATE>_<PERIOD>.nc combining them.
Native variable names and grid, over the bounding box. Conversion to ROMS forcing is a separate step.

Assumptions
- DATASOURCE is the IFS forecast (ecmwf_ifs_0p25_oper_sfc), stored as cycles. A query without
  a cycle returns only the latest forecast, so each cycle is requested with parameters={"cycle": ...}.
- From each 00Z and 12Z cycle we keep +3h to +12h, so every step comes from the freshest forecast
  and the series is continuous 3-hourly. Flux fields (tp, ssr, strd) are rates over the preceding
  3h and are NaN at +0h, which is why we start at +3h.
- The first cycle is DATE-12h, so DATE 00:00 is included. The series runs DATE 00:00 -> DATE+PERIOD.
- IFS longitudes are 0-360, so the bbox from GRID (converted to 0-360) works as is.
- Bounding box is read from GRID's lon_rho/lat_rho, padded by 0.5 deg. If GRID is None, NZ_BBOX is used.
"""

from pathlib import Path                 # handles file and folder paths
import yaml                              # reads the YAML config file
import pandas as pd                      # dates, times and time differences
import xarray as xr                      # opens, combines and saves NetCDF data
from oceanum.datamesh import Connector   # connects to Oceanum DataMesh

# ----------------------------------------------------------------- 
NZ_BBOX = [160.0, -52.0, 185.0, -30.0]                       # fallback box [lon_min, lat_min, lon_max, lat_max] if GRID is None
# -----------------------------------------------------------------

path = '/home/nn411/Projects/OceanAtm/Moana-2.0/yaml/download_atm.yaml'        # location of the YAML config file


def bbox_from_grid(path, pad=0.5):                # builds the download box from the ROMS grid
    g = xr.open_dataset(path)                           # open the ROMS grid file
    lon, lat = g["lon_rho"], g["lat_rho"]              # grid longitudes and latitudes
    lon = lon.where(lon >= 0, lon + 360)                  # convert any negative lons to 0-360, so the box doesn't break at 180
    return [float(lon.min()) - pad, float(lat.min()) - pad, float(lon.max()) + pad, float(lat.max()) + pad]  # [west, south, east, north], padded
                                                         


def main():

    dm = Connector()                                   # connect to DataMesh (token read from DATAMESH_TOKEN)
    print("Connected to Oceanum Datamesh successfully :)")

    cfg = yaml.safe_load(open(path))                   # read the YAML into a dictionary
    print('Reading configuration yaml file')

    bbox = bbox_from_grid(cfg['GRID']) if cfg.get('GRID') else NZ_BBOX   # box from grid, or the fallback
    t0 = pd.Timestamp(cfg['DATE'])                           # start date as a timestamp, e.g. 2026-01-01 00:00
    period = pd.Timedelta(cfg['PERIOD'])                         # length of the run, e.g. "90D" -> 90 days
 
    # list of cycle start times: every 12 h (00Z and 12Z), from DATE-12h so DATE 00:00 is covered
    cycles = pd.date_range(t0 - pd.Timedelta("12h"),                   # first cycle: day before at 12Z
                           t0 + period - pd.Timedelta("12h"),      # last cycle: its +12h lands on DATE+PERIOD
                           freq="12h")                                 # one cycle every 12 hours
    print(f"datasource={cfg['DATASOURCE']}, bbox={bbox}, "
          f"{len(cycles)} cycles: {cycles[0]} -> {cycles[-1]}")     # summary of what will be downloaded

    cycle_dir = Path(cfg['OUTPUT_DIR']) / "cycles"           # subfolder for the per-cycle files
    cycle_dir.mkdir(parents=True, exist_ok=True)           # create it (and parents) if it doesn't exist
    files = [cycle_dir / f"ifs_{c:%Y%m%d%H}.nc"               # one filename per cycle, e.g. ifs_2026010100.nc
             for c in cycles]

    # download +3h to +12h of each cycle, one file per cycle
    for cycle, out in zip(cycles, files):                   # go through each cycle with its filename
        if out.exists():                                          # if already downloaded earlier cycle, skip it
            continue                                   

        ds = dm.query(                                        # ask DataMesh for this cycle's data
            datasource=cfg['DATASOURCE'],                        # which dataset
            variables=cfg['VARIABLES'],                       # which variables
            parameters={"cycle": f"{cycle:%Y%m%d%H}"},            # which forecast run, e.g. "2026010100"
            geofilter={"type": "bbox", "geom": bbox},           # which region
            timefilter={"type": "range",                            # which times: +3h to +12h of this cycle
                        "times": [cycle + pd.Timedelta("3h"), cycle + pd.Timedelta("12h")]},
        )
        
        if ds is None:                                      # if nothing returned then report it
            print(f"{cycle:%Y%m%d%H} NO DATA")         
            continue                                     # move on instead of crashing

        ds.to_netcdf(out)                                       # save this cycle to its own file
        print(f"{cycle:%Y%m%d%H} saved")                        # progress message

    # combine all cycles into one file
    if not all(f.exists() for f in files):                     # are any cycle files missing?
        print("Some cycles are missing, not combining. Rerun to fill them.")
        return                                                   # stop here rather than write a file with gaps

    ds = xr.open_mfdataset(files).sortby("time")          # open all cycle files as one dataset, in time order
    print(ds)                                            # show the combined dataset

    out = Path(cfg['OUTPUT_DIR']) / f"{cfg['name']}_{cfg['VAR_NAME']}_raw_{cfg['DATE']}_{cfg['PERIOD']}.nc"
    # combined filename, e.g. atm_ifs_raw_2026-01-01_90D.nc
    ds.attrs["forecast_reference_time"] = "multiple cycles: +3h to +12h of each 00Z/12Z cycle" # combined file spans many cycles
    ds.to_netcdf(out)                                     # save the combined file
    print(f"Yayyyy wrote {out}")                             # done


if __name__ == "__main__":                             # only run main() when this file is run directly,
    main()                                              # not when it's imported from another script