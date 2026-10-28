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
- LON_CONVENTION in the yaml is the DATASOURCE's longitude convention ("0_360" or "-180_180").
  DataMesh silently truncates a box that crosses that convention's seam, so such a box is
  requested as two pieces and joined. The output longitudes are contiguous across the seam
  (e.g. 160.5 to 185.5 for NZ from a -180_180 source).
"""
import sys
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
import xarray as xr
from oceanum.datamesh import Connector

# ----------------------------------------------------------------- settings
NZ_BBOX = [160.0, -52.0, 185.0, -30.0]     # x_min, y_min, x_max, y_max (used only if GRID is None)
# ------------------------------------------------------------------------


def wrap_lon(x, convention):
    """Express longitude(s) x in the given convention, "0_360" or "-180_180"."""
    if convention == "0_360":
        return x % 360
    if convention == "-180_180":
        return (x + 180) % 360 - 180
    raise ValueError(f"Unknown LON_CONVENTION: {convention!r}")


def bbox_from_grid(path, pad=0.5, convention="0_360"):
    with xr.open_dataset(path) as g:
        lon = g["lon_rho"].values
        lat = g["lat_rho"].values
    # compute the box in whichever convention keeps the grid contiguous (narrower span)
    lon360, lon180 = wrap_lon(lon, "0_360"), wrap_lon(lon, "-180_180")
    lon = lon360 if np.ptp(lon360) <= np.ptp(lon180) else lon180
    xmin = wrap_lon(lon.min() - pad, convention)
    xmax = wrap_lon(lon.max() + pad, convention)
    return [float(xmin), float(lat.min()) - pad, float(xmax), float(lat.max()) + pad]


def split_at_seam(bbox, convention):
    """Return [bbox], or two bboxes if it crosses the convention's seam (written with xmin > xmax)."""
    xmin, ymin, xmax, ymax = bbox
    if xmin <= xmax:
        return [bbox]
    lo, hi = (0.0, 360.0) if convention == "0_360" else (-180.0, 180.0)
    return [[xmin, ymin, hi, ymax], [lo, ymin, xmax, ymax]]


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

    conv = cfg['LON_CONVENTION']
    if cfg.get('GRID'):
        bbox = bbox_from_grid(cfg['GRID'], convention=conv)
    else:
        bbox = [float(wrap_lon(NZ_BBOX[0], conv)), NZ_BBOX[1], float(wrap_lon(NZ_BBOX[2], conv)), NZ_BBOX[3]]
    t0 = pd.Timestamp(cfg['DATE'])
    print(f"datasource={cfg['DATASOURCE']}, bbox={bbox}, time=[{t0}, +1 day)")

    pieces = []
    for box in split_at_seam(bbox, conv):
        pieces.append(dm.query(
            datasource=cfg['DATASOURCE'],
            variables=cfg['VARIABLES'],
            geofilter={"type": "bbox", "geom": box},
            timefilter={"type": "range", "times": [t0, t0 + pd.Timedelta(cfg['PERIOD'])]},
        ))
    if len(pieces) == 2:
        # shift the piece east of the seam by +360 so longitude is contiguous, then join
        lon = "longitude" if "longitude" in pieces[1].coords else "lon"
        pieces[1] = pieces[1].assign_coords({lon: pieces[1][lon] + 360})
        ds = xr.concat(pieces, dim=lon).drop_duplicates(lon)
    else:
        ds = pieces[0]
    # ds = ds.isel(time=0)  # first field at or after DATE
    print(ds)

    
    out = Path(cfg['OUTPUT_DIR']) / f"{cfg['name']}_{cfg['VAR_NAME']}_raw_{cfg['DATE']}.nc"
    ds.to_netcdf(out)
    print(f"Yayyyy wrote {out}")


if __name__ == "__main__":
    main()