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
NZ_BBOX = [160.0, -52.0, 185.0, -30.0]     # x_min, y_min, x_max, y_max (used only if GRID is None)
# ------------------------------------------------------------------------


def bbox_from_grid(path, pad=0.5):
    g = xr.open_dataset(path)
    lon, lat = g["lon_rho"], g["lat_rho"]
    lon = lon.where(lon >= 0, lon + 360)  # keep the box contiguous across 180E
    return [float(lon.min()) - pad, float(lat.min()) - pad, float(lon.max()) + pad, float(lat.max()) + pad]


def main():
    
    
    dm = Connector()  # token from DATAMESH_TOKEN
    print("Connected to Oceanum Datamesh successfully :)")

    cfg = yaml.safe_load(open('/scratch/ss4338/Project/Moana-2.0/download_input.yaml'))
    print('Reading configuration yaml file')

    if "--list" in sys.argv:
        for term in ("glorys", "mercator", "moana", "ocean hindcast"):
            for ds in dm.get_catalog(search=term, timefilter=[cfg['DATE'], cfg['DATE']]):
                print(f"{ds.id:50s} {ds.name}")
        return

    bbox = bbox_from_grid(cfg['GRID']) if cfg.get('GRID') else NZ_BBOX
    t0 = pd.Timestamp(cfg['DATE'])
    print(f"datasource={cfg['DATASOURCE']}, bbox={bbox}, time=[{t0}, +1 day)")

    ds = dm.query(
        datasource=cfg['DATASOURCE'],
        variables=cfg['VARIABLES'],
        geofilter={"type": "bbox", "geom": bbox},
        timefilter={"type": "range", "times": [t0, t0 + pd.Timedelta(cfg['PERIOD'])]},
    )
    # ds = ds.isel(time=0)  # first field at or after DATE
    print(ds)

    
    out = Path(cfg['OUTPUT_DIR']) / f"{cfg['name']}_{cfg['VAR_NAME']}_raw_{cfg['DATE']}.nc"
    ds.to_netcdf(out)
    print(f"Yayyyy wrote {out}")


if __name__ == "__main__":
    main()