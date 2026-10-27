#!/usr/bin/env python3
"""
Author: Suman Shekhar

Download the ocean state over the ROMS grid for the full run from Oceanum DataMesh, for a ROMS
climatology file. The same request as download_input.py (the initial condition), but for many days.

  export DATAMESH_TOKEN=...
  python scripts/download_clm.py                # uses download_clm.yaml at the repo root
  python scripts/download_clm.py other.yaml

Output: OUTPUT_DIR/<name>_raw_<from>_<to>.nc, one file per dataset and time chunk, with the source's
native variable names and grid. Interpolation to the ROMS grid is a separate step (make_clm.py).

Assumptions
- The bbox and the seam handling are the same as in download_input.py: GRID's lon_rho/lat_rho padded
  by 0.5 deg, and a box that crosses the source's seam is requested as two pieces and joined.
- The download covers START - 1 day to END + 2 days, the same margin as download_bry.py.
- One query per CHUNK: one query for the full run over the full grid is ~4 to 9 GB.
  A chunk starts where the last one ends, so two chunks share one record; make_clm.py drops it.
- A file that exists already is not downloaded again, so a failed run can be started again.
"""
import sys
from pathlib import Path
import yaml
import pandas as pd
from oceanum.datamesh import Connector
from download_input import bbox_from_grid
from download_bry import query_bbox, check_coverage

REPO = Path(__file__).resolve().parents[1]


def main():
    config = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "download_clm.yaml"
    with open(config) as f:
        cfg = yaml.safe_load(f)
    print(f"Read configuration {config}")

    dm = Connector()  # token from DATAMESH_TOKEN
    print("Connected to Oceanum Datamesh successfully :)")

    bbox = bbox_from_grid(cfg['GRID'], convention=cfg['LON_CONVENTION'])
    t0 = pd.Timestamp(cfg['START']) - pd.Timedelta("1D")
    t1 = pd.Timestamp(cfg['END']) + pd.Timedelta("2D")      # the run ends at midnight after END
    edges = list(pd.date_range(t0, t1, freq=cfg['CHUNK']))
    if edges[-1] < t1:
        edges.append(t1)
    out_dir = Path(cfg['OUTPUT_DIR'])
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, src in cfg['DATASETS'].items():
        src = {**src, 'LON_CONVENTION': cfg['LON_CONVENTION']}   # the keys query_bbox reads
        for a, b in zip(edges[:-1], edges[1:]):
            out = out_dir / f"{name}_raw_{a:%Y-%m-%d}_{b:%Y-%m-%d}.nc"
            if out.exists():
                print(f"{out} exists, skipped")
                continue
            print(f"{name}: datasource={src['DATASOURCE']}, bbox={bbox}, time=[{a}, {b}]")
            ds = query_bbox(dm, src, bbox, a, b)
            check_coverage(ds, bbox, a, b)
            part = out.with_suffix(".nc.part")              # renamed only when complete
            ds.to_netcdf(part)
            part.rename(out)
            print(f"Yayyyy wrote {out}")


if __name__ == "__main__":
    main()
