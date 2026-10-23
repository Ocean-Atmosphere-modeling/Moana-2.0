#!/usr/bin/env python3
"""
Author: Suman Shekhar

Download the ocean state along each ROMS open boundary from Oceanum DataMesh, for a ROMS boundary file.

  export DATAMESH_TOKEN=...
  python download_bry.py --list     # search the catalog for the datasource id, then set DATASOURCE in the yaml
  python download_bry.py            # download

Output: OUTPUT_DIR/<side>/<name>_<side>_raw_<START>_<END>.nc for each side in SIDES, with the source's
native variable names and grid, over a strip around that boundary. Interpolation to the ROMS grid is
a separate step (make_bry.py).

Assumptions
- DATASOURCE is a gridded 3D ocean product (GLORYS/Copernicus mirror or Oceanum's own hindcast)
  with lon/lat/depth coordinates.
- START and END are the first and last day of the run. The download covers START - 1 day to
  END + 2 days, so there is a record before the run starts and after it ends (daily means are
  stamped 12:00); this is checked after download.
- The strips are computed from GRID's rho-, u- and v-points on each edge, padded by PAD degrees so
  the later interpolation and fill have data past the edges.
- LON_CONVENTION in the yaml is the DATASOURCE's longitude convention ("0_360" or "-180_180").
  DataMesh silently truncates a box that crosses that convention's seam, so such a box is
  requested as two pieces and joined. The output longitudes are contiguous across the seam
  (e.g. 160 to 186 for NZ from a -180_180 source). Coverage is checked after download.
"""
import sys
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
import xarray as xr
from oceanum.datamesh import Connector

CONFIG = '/scratch/ss4338/Project/Moana-2.0/download_bry.yaml'


def wrap_lon(x, convention):
    """Express longitude(s) x in the given convention, "0_360" or "-180_180"."""
    if convention == "0_360":
        return x % 360
    if convention == "-180_180":
        return (x + 180) % 360 - 180
    raise ValueError(f"Unknown LON_CONVENTION: {convention!r}")


def boundary_bboxes(path, pad=1.0, convention="0_360"):
    """[xmin, ymin, xmax, ymax] around each ROMS boundary, padded by `pad` degrees.

    Covers the rho-, u- and v-points on each edge, since the boundary file uses all three.
    Longitudes are in `convention` (the data source's); xmin > xmax means the box crosses its seam.
    """
    edge = {"south": (0, slice(None)), "north": (-1, slice(None)),
            "west": (slice(None), 0), "east": (slice(None), -1)}
    with xr.open_dataset(path) as g:
        pts = {pt: (g[f"lon_{pt}"].values, g[f"lat_{pt}"].values) for pt in ("rho", "u", "v")}

    boxes = {}
    for side, idx in edge.items():
        lon = np.concatenate([lon[idx] for lon, _ in pts.values()])
        lat = np.concatenate([lat[idx] for _, lat in pts.values()])
        # compute in whichever convention keeps the edge contiguous (narrower span)
        lon360, lon180 = wrap_lon(lon, "0_360"), wrap_lon(lon, "-180_180")
        lon = lon360 if np.ptp(lon360) <= np.ptp(lon180) else lon180
        boxes[side] = [float(wrap_lon(lon.min() - pad, convention)), float(lat.min() - pad),
                       float(wrap_lon(lon.max() + pad, convention)), float(lat.max() + pad)]
    return boxes


def split_at_seam(bbox, convention):
    """Return [bbox], or two bboxes if it crosses the convention's seam (written with xmin > xmax)."""
    xmin, ymin, xmax, ymax = bbox
    if xmin <= xmax:
        return [bbox]
    lo, hi = (0.0, 360.0) if convention == "0_360" else (-180.0, 180.0)
    return [[xmin, ymin, hi, ymax], [lo, ymin, xmax, ymax]]


def query_bbox(dm, cfg, bbox, t0, t1):
    """One bbox -> one dataset; splits at the source's seam and joins the pieces."""
    pieces = []
    for box in split_at_seam(bbox, cfg['LON_CONVENTION']):
        pieces.append(dm.query(
            datasource=cfg['DATASOURCE'],
            variables=cfg['VARIABLES'],
            geofilter={"type": "bbox", "geom": box},
            timefilter={"type": "range", "times": [t0, t1]},
        ))
    if len(pieces) == 2:
        # shift the piece east of the seam by +360 so longitude is contiguous, then join
        lon = "longitude" if "longitude" in pieces[1].coords else "lon"
        pieces[1] = pieces[1].assign_coords({lon: pieces[1][lon] + 360})
        return xr.concat(pieces, dim=lon).drop_duplicates(lon)
    return pieces[0]


def check_coverage(ds, bbox, run_start, run_end):
    """Raise if the download doesn't cover the requested box and run period (DataMesh truncates silently)."""
    lon = ds["longitude"] if "longitude" in ds.coords else ds["lon"]
    lat = ds["latitude"] if "latitude" in ds.coords else ds["lat"]
    dlon, dlat = float(abs(lon.diff(lon.dims[0])).median()), float(abs(lat.diff(lat.dims[0])).median())
    want_lon = (bbox[2] - bbox[0]) % 360                  # span, also for a box crossing the seam
    got_lon = float(lon.max() - lon.min())
    got_lat = float(lat.max() - lat.min())
    assert got_lon >= want_lon - 2 * dlon, f"longitude span {got_lon:.2f} < requested {want_lon:.2f}"
    assert got_lat >= (bbox[3] - bbox[1]) - 2 * dlat, f"latitude span {got_lat:.2f} < requested {bbox[3] - bbox[1]:.2f}"
    assert ds.time.min() <= run_start, f"first record {ds.time.values.min()} is after the run start {run_start}"
    assert ds.time.max() >= run_end, f"last record {ds.time.values.max()} is before the run end {run_end}"


def main():

    dm = Connector()  # token from DATAMESH_TOKEN
    print("Connected to Oceanum Datamesh successfully :)")

    cfg = yaml.safe_load(open(CONFIG))
    print('Reading configuration yaml file')

    if "--list" in sys.argv:
        for term in ("glorys", "mercator", "moana", "ocean hindcast"):
            for ds in dm.get_catalog(search=term, timefilter=[cfg['START'], cfg['START']]):
                print(f"{ds.id:50s} {ds.name}")
        return

    run_start = pd.Timestamp(cfg['START'])
    run_end = pd.Timestamp(cfg['END']) + pd.Timedelta("1D")   # the run ends at midnight after END
    t0, t1 = run_start - pd.Timedelta("1D"), run_end + pd.Timedelta("1D")
    boxes = boundary_bboxes(cfg['GRID'], pad=cfg['PAD'], convention=cfg['LON_CONVENTION'])

    for side in cfg['SIDES']:
        print(f"{side}: datasource={cfg['DATASOURCE']}, bbox={boxes[side]}, time=[{t0}, {t1}]")
        ds = query_bbox(dm, cfg, boxes[side], t0, t1)
        check_coverage(ds, boxes[side], run_start, run_end)
        print(ds)

        out = Path(cfg['OUTPUT_DIR']) / side / f"{cfg['name']}_{side}_raw_{cfg['START']}_{cfg['END']}.nc"
        out.parent.mkdir(parents=True, exist_ok=True)
        ds.to_netcdf(out)
        print(f"Yayyyy wrote {out}")


if __name__ == "__main__":
    main()