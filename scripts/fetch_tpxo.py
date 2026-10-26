#!/usr/bin/env python
"""Cut TPXO9-atlas v5 tidal constituents to the Moana box from DataMesh.

Usage (moana_python environment, DATAMESH_TOKEN set):

    python scripts/fetch_tpxo.py [--out FILE] [--source ID]

Writes all constituents of the DataMesh datasource (default
tpxo9_atlas_v5_cons: 1/30 deg, 15 constituents) inside BOX to --out
(default oceanum_input/tide_forcing/tpxo9_atlas_v5_moana.nc). DataMesh stores complex
amplitudes (h in m, u and v in m s-1); netCDF has no complex type, so each is
written as real and imaginary parts (hRe, hIm, ...), as in the OSU files.
Amplitude is |h|; the Greenwich phase lag convention is checked in
Apps/moana/python_scripts/plot_tides.py. Longitudes are 0-360, so the box
crossing 180 E is one piece.
"""

import argparse
import datetime as dt
import os
from pathlib import Path

import numpy as np
import oceanum
import xarray as xr
from oceanum.datamesh import Connector

SOURCE = "tpxo9_atlas_v5_cons"
OUT = Path("/projects/f_omg_1/moa/moana/oceanum_input/tide_forcing/tpxo9_atlas_v5_moana.nc")
BOX = (160.0, 186.0, -53.0, -30.0)  # W, E, S, N, as scripts/subset_cfsv2.py


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--source", default=SOURCE)
    a = p.parse_args()
    dm = Connector(token=os.environ["DATAMESH_TOKEN"])
    w, e, s, n = BOX
    ds = dm.load_datasource(a.source).sel(lon=slice(w, e), lat=slice(s, n)).load()
    out = xr.Dataset(coords={"con": ds.con.astype(str), "lat": ds.lat, "lon": ds.lon})
    for v in ("h", "u", "v"):
        for part, f in (("Re", np.real), ("Im", np.imag)):
            out[v + part] = (ds[v].dims, f(ds[v].values).astype(np.float32),
                             {**ds[v].attrs, "long_name": f"{ds[v].attrs['long_name']}, "
                              f"{'real' if part == 'Re' else 'imaginary'} part"})
    out["dep"] = ds.dep.astype(np.float32)
    out.attrs = {
        "title": f"{a.source} cut to the Moana box",
        "source": f"Oceanum DataMesh datasource {a.source} (TPXO9-atlas, "
                  "Egbert and Erofeeva 2002, OSU)",
        "datamesh_cache_hash": ds.attrs.get("_datamesh_cache_hash", "❓"),
        "box_W_E_S_N": list(BOX),
        "history": f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ} "
                   f"scripts/fetch_tpxo.py, oceanum {oceanum.__version__}",
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    enc = {v: {"zlib": True, "complevel": 4} for v in out.data_vars}
    out.to_netcdf(a.out, encoding=enc)
    print(out)
    print(f"wrote {a.out} ({a.out.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
