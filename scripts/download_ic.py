#!/usr/bin/env python3
"""
Author: Suman Shekhar

Download the ocean state for one date from Oceanum DataMesh, for a ROMS initial condition.

  export DATAMESH_TOKEN=...
  python get_datamesh_ic.py --list     # search the catalog for the datasource id, then set DATASOURCE below
  python get_datamesh_ic.py            # download

Output: OUTPUT_DIR/ic_raw_<DATE>.nc, with the source's native variable names and grid, over the
bounding box. Interpolation to the ROMS grid is a separate step.

Assumptions
- DATASOURCE is a gridded 3D ocean product (GLORYS/Copernicus mirror or Oceanum's own hindcast)
  with lon/lat/depth coordinates.
- DATE means the first available time at or after DATE 00:00. For daily-mean products (GLORYS)
  that is the DATE field, stamped 12:00.
- Bounding box is read from GRID's lon_rho/lat_rho, padded by 0.5 deg so the later interpolation
  has data past the edges. If GRID is None, NZ_BBOX is used.
"""
import sys
from pathlib import Path
import yaml
import pandas as pd
import xarray as xr
from oceanum.datamesh import Connector

# ----------------------------------------------------------------- settings
DATASOURCE = "cmems_mod_glo_phy-cur_anfc_0-083deg_pt6h-i"                     # find it with --list
DATE = "2025-01-01"                                                           # model start date
OUTPUT_DIR = Path("/projects/f_omg_1/moa/moana/oceanum_input/initial_cond")   # where the file goes
GRID = "/projects/f_omg_1/moa/moana/grd_moana5km.nc"  # ROMS grid, or None to use NZ_BBOX
NZ_BBOX = [160.0, -52.0, 185.0, -30.0]     # x_min, y_min, x_max, y_max (used only if GRID is None)
DAY = 1                                                              # number of "days" you want data to download
# Variables to download, in the datasource's own names.
# GLORYS / Copernicus:  zos = sea level, thetao = temperature, so = salinity, uo / vo = 3D velocity
# If the datasource uses ROMS names, change to ["zeta", "temp", "salt", "u", "v"].
#VARIABLES = ["zos", "thetao", "so", "uo", "vo"]   # for IC and BC we need all ["zeta", "temp", "salt", "u", "v"]
VARIABLES = ["uo", "vo"]
# ------------------------------------------------------------------------


def bbox_from_grid(path, pad=0.5):
    g = xr.open_dataset(path)
    lon, lat = g["lon_rho"], g["lat_rho"]
    lon = lon.where(lon >= 0, lon + 360)  # keep the box contiguous across 180E
    return [float(lon.min()) - pad, float(lat.min()) - pad, float(lon.max()) + pad, float(lat.max()) + pad]


def main():
    
    dm = Connector()  # token from DATAMESH_TOKEN
    print("Connected to Oceanum Datamesh successfully :)")

    if "--list" in sys.argv:
        for term in ("glorys", "mercator", "moana", "ocean hindcast"):
            for ds in dm.get_catalog(search=term, timefilter=[DATE, DATE]):
                print(f"{ds.id:50s} {ds.name}")
        return

    bbox = bbox_from_grid(GRID) if GRID else NZ_BBOX
    t0 = pd.Timestamp(DATE)
    print(f"datasource={DATASOURCE}, bbox={bbox}, time=[{t0}, +1 day)")

    ds = dm.query(
        datasource=DATASOURCE,
        variables=VARIABLES,
        geofilter={"type": "bbox", "geom": bbox},
        timefilter={"type": "range", "times": [t0, t0 + pd.Timedelta(days=DAY)]},
    )
    # ds = ds.isel(time=0)  # first field at or after DATE
    print(ds)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"ic_raw_{DATE}.nc"
    ds.to_netcdf(out)
    print(f"Yayyyy wrote {out}")


if __name__ == "__main__":
    main()