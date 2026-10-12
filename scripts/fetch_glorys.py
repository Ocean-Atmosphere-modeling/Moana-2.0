#!/usr/bin/env python
"""Download GLORYS12v1 daily fields for the Moana domain from Copernicus Marine.

Usage (moana_python environment; run `copernicusmarine login` once first):

    python scripts/fetch_glorys.py 2017-10-01 2017-10-01 --out DIR
    python scripts/fetch_glorys.py 2017-10-01 2019-12-31 --out DIR --edges --surface

Without --edges: one file for the whole box (default 160.5-185.5 E,
52.5-30.5 S, all 50 levels, thetao so uo vo zos).
With --edges: four thin boxes along the model's open edges (W, E, S, N),
for boundary plots, written as glorys12_<edge>_<start>_<end>.nc.
--surface keeps only the top level (0.49 m).

Dataset: GLOBAL_MULTIYEAR_PHY_001_030, cmems_mod_glo_phy_my_0.083deg_P1D-m
(GLORYS12v1, doi:10.48670/moi-00021). The toolbox prints the dataset
version it selected; it is kept in the log next to the files.
"""

import argparse
from pathlib import Path

import copernicusmarine

DATASET = "cmems_mod_glo_phy_my_0.083deg_P1D-m"
VARS = ["thetao", "so", "uo", "vo", "zos"]
BOX = (160.5, 185.5, -52.5, -30.5)  # W, E, S, N (domain 161.03-184.97 E, 51.98-31.03 S)
# Thin boxes around the model's open edges (rho-points at 161.03 E,
# 184.97 E, 51.98 S, 31.03 S), two GLORYS cells wide.
EDGES = {
    "W": (160.95, 161.15, -52.1, -30.9),
    "E": (184.85, 185.05, -52.1, -30.9),
    "S": (160.95, 185.05, -52.1, -51.9),
    "N": (160.95, 185.05, -31.1, -30.9),
}


def fetch(box, start, end, out, name, surface):
    w, e, s, n = box
    copernicusmarine.subset(
        dataset_id=DATASET, variables=VARS,
        minimum_longitude=w, maximum_longitude=e,
        minimum_latitude=s, maximum_latitude=n,
        minimum_depth=0.0, maximum_depth=1.0 if surface else 6000.0,
        start_datetime=f"{start}T00:00:00", end_datetime=f"{end}T00:00:00",
        output_directory=str(out), output_filename=name,
        overwrite=True)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("start")
    p.add_argument("end")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--edges", action="store_true")
    p.add_argument("--surface", action="store_true")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    tag = f"{a.start.replace('-', '')}_{a.end.replace('-', '')}"
    lev = "_surf" if a.surface else ""
    if a.edges:
        for edge, box in EDGES.items():
            fetch(box, a.start, a.end, a.out, f"glorys12_{edge}{lev}_{tag}.nc",
                  a.surface)
    else:
        fetch(BOX, a.start, a.end, a.out, f"glorys12{lev}_{tag}.nc", a.surface)


if __name__ == "__main__":
    main()
