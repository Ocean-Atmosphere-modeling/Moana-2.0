#!/usr/bin/env python
"""Cut the global CFSv2 hourly GRIB2 files to the Moana box, as netCDF.

Usage (moana_python environment; ~0.3 s per GRIB record, 15 CPU-hours for
2017-09..2019-12, so run it as a batch job):

    sbatch -p p_omg_1,main,cmain -c 32 --mem 64G -t 3:00:00 \\
        -o /projects/f_omg_1/moa/moana/Input/atmosphere/subset_cfsv2.log \\
        --export=ALL,MOANA_GIT=$(git describe --always --dirty) \\
        --wrap "$HOME/miniconda3/envs/moana_python/bin/python \\
                scripts/subset_cfsv2.py --jobs 32"
    python scripts/subset_cfsv2.py --jobs 1 dswsfc.cdas1.201709.grb2

Reads <var>.cdas1.<YYYYMM>.grb2 from --src (made by scripts/fetch_cfsv2.sh)
and writes <var>.cdas1.<YYYYMM>.nz.nc to --out: every GRIB record, values
as decoded, cut to BOX. No interpolation and no unit conversion; those are
the bulk-forcing step.

Each output has dimensions (time, step, latitude, longitude). time is the
analysis cycle (00, 06, 12, 18 UTC), step the forecast hour, and
valid_time = time + step. Steps are 1-6 for every variable except prmsl,
which has 0-5 (analysis plus 1-5 h). For averaged fields (GRIB stepType
"avg": prate, dswsfc, uswsfc, dlwsfc) the value at step n is the mean over
[time, time + n h], not over the last hour. Latitude runs north to south as
in the source. Grids: Gaussian, N = 440 (0.2045 deg in longitude), except
prmsl on a regular 0.5 deg grid.

A file is kept only if it passes two checks:
  - every GRIB record fills exactly one (time, step) slot, the slots cover
    the whole month 6-hourly, and the record count equals the source's;
  - the first, middle and last records, read again with cfgrib (which
    indexes the file and builds the coordinates itself), match exactly.
A failed file is not written and the script exits non-zero. Existing
outputs are skipped (they are only created after passing). At the end
SHA256SUMS in --out lists every output.
"""

import argparse
import datetime as dt
import hashlib
import os
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import eccodes as ec
import numpy as np
import xarray as xr

ROOT = Path("/projects/f_omg_1/moa/moana/Input/atmosphere")
SRC = ROOT / "cfsv2_global"
OUT = ROOT / "cfsv2_nz"
URL = "https://osdf-director.osg-htc.org/ncar/gdex/d094001"
# W, E, S, N in degrees (GRIB longitudes are 0-360, so the box is one piece).
# Model rho-points span 161.03-184.97 E, 51.98-31.03 S; this keeps about
# 4 CFSv2 cells beyond every edge for interpolation.
BOX = (160.0, 186.0, -53.0, -30.0)
REPO = Path(__file__).resolve().parents[1]


def box_index(h):
    """Row and column indices of BOX on the message's grid."""
    assert ec.codes_get(h, "gridType") in ("regular_gg", "regular_ll")
    assert ec.codes_get(h, "jScansPositively") == 0
    assert ec.codes_get(h, "iScansNegatively") == 0
    lat = ec.codes_get_array(h, "distinctLatitudes")
    lon = ec.codes_get_array(h, "distinctLongitudes")
    w, e, s, n = BOX
    j = np.flatnonzero((lat >= s) & (lat <= n))
    i = np.flatnonzero((lon >= w) & (lon <= e))
    return j, i, lat[j], lon[i]


def read_records(src):
    """All records of one GRIB file, cut to BOX: {(var, time, step): array}."""
    recs, meta, grid = {}, {}, None
    with open(src, "rb") as fh:
        while (h := ec.codes_grib_new_from_file(fh)) is not None:
            try:
                key = (ec.codes_get(h, "Ni"), ec.codes_get(h, "Nj"),
                       ec.codes_get(h, "latitudeOfFirstGridPoint"),
                       ec.codes_get(h, "longitudeOfLastGridPoint"))
                if grid is None:
                    grid, (j, i, lat, lon) = key, box_index(h)
                assert key == grid, f"grid changes inside {src.name}"
                var = ec.codes_get(h, "cfVarName")
                kind = ec.codes_get(h, "stepType")
                t0, t1 = ec.codes_get(h, "startStep"), ec.codes_get(h, "endStep")
                assert (kind == "avg" and t0 == 0) or (kind == "instant" and t0 == t1), \
                    f"{src.name}: {var} {kind} steps {t0}-{t1}"
                time = dt.datetime.strptime(
                    f"{ec.codes_get(h, 'dataDate')}{ec.codes_get(h, 'dataTime'):04d}",
                    "%Y%m%d%H%M")
                k = (var, time, t1)
                assert k not in recs, f"{src.name}: duplicate record {k}"
                nj, ni = key[1], key[0]
                v = ec.codes_get_values(h).reshape(nj, ni)
                recs[k] = v[np.ix_(j, i)].astype(np.float32)
                if var not in meta:
                    meta[var] = {
                        "units": ec.codes_get(h, "units"),
                        "long_name": ec.codes_get(h, "name"),
                        "GRIB_shortName": ec.codes_get(h, "shortName"),
                        "GRIB_paramId": ec.codes_get(h, "paramId"),
                        "GRIB_stepType": kind,
                        "GRIB_typeOfLevel": ec.codes_get(h, "typeOfLevel"),
                        "GRIB_level": ec.codes_get(h, "level"),
                    }
            finally:
                ec.codes_release(h)
    return recs, meta, lat, lon


def month_cycles(src):
    """The 6-hourly analysis cycles of the file's month."""
    ym = src.name.split(".")[2]
    first = dt.datetime(int(ym[:4]), int(ym[4:]), 1)
    nxt = dt.datetime(first.year + first.month // 12, first.month % 12 + 1, 1)
    n = int((nxt - first) / dt.timedelta(hours=6))
    return [first + k * dt.timedelta(hours=6) for k in range(n)]


def to_dataset(src, recs, meta, lat, lon):
    times = month_cycles(src)
    steps = sorted({k[2] for k in recs})
    assert steps in ([0, 1, 2, 3, 4, 5], [1, 2, 3, 4, 5, 6]), \
        f"{src.name}: steps {steps}"
    got = sorted({k[1] for k in recs})
    assert got == times, f"{src.name}: cycles {got[0]}..{got[-1]}, {len(got)} of {len(times)}"
    n = len(meta) * len(times) * len(steps)
    assert len(recs) == n, f"{src.name}: {len(recs)} records for {n} slots"
    assert ec.codes_count_in_file(open(src, "rb")) == n, f"{src.name}: record count"

    t = np.array(times, dtype="datetime64[ns]")
    s = np.array(steps, dtype="timedelta64[h]").astype("timedelta64[ns]")
    ds = xr.Dataset(coords={
        "time": ("time", t, {"long_name": "analysis cycle (forecast reference time)"}),
        "step": ("step", s, {"long_name": "forecast hour"}),
        "latitude": ("latitude", lat, {"units": "degrees_north"}),
        "longitude": ("longitude", lon, {"units": "degrees_east"}),
    })
    ds = ds.assign_coords(valid_time=ds.time + ds.step)
    for var, attrs in meta.items():
        a = np.stack([np.stack([recs[(var, tt, st)] for st in steps]) for tt in times])
        if attrs["GRIB_stepType"] == "avg":
            attrs = {**attrs, "comment": "mean over [time, valid_time], i.e. "
                     "over the first `step` hours of the forecast"}
        ds[var] = (("time", "step", "latitude", "longitude"), a, attrs)
    return ds


def check_cfgrib(src, ds):
    """First, middle and last records again through cfgrib."""
    ref = xr.open_dataset(src, engine="cfgrib", backend_kwargs={"indexpath": ""})
    w, e, s, n = BOX
    ref = ref.sel(latitude=slice(n, s), longitude=slice(w, e))
    np.testing.assert_array_equal(ref.latitude.values, ds.latitude.values)
    np.testing.assert_array_equal(ref.longitude.values, ds.longitude.values)
    np.testing.assert_array_equal(ref.time.values, ds.time.values)
    np.testing.assert_array_equal(ref.step.values, ds.step.values)
    nt, ns = ds.sizes["time"], ds.sizes["step"]
    for var in ds.data_vars:
        for ti, si in ((0, 0), (nt // 2, ns // 2), (nt - 1, ns - 1)):
            a = ref[var].isel(time=ti, step=si).values
            b = ds[var].isel(time=ti, step=si).values
            assert np.array_equal(a, b), f"{src.name}: {var} differs at ({ti}, {si})"
    ref.close()


def source_sha256(src):
    sums = src.parent / "SHA256SUMS"
    for line in sums.read_text().splitlines():
        h, name = line.split()
        if name == src.name:
            return h
    return "❓ not in SHA256SUMS"


def git_version():
    """MOANA_GIT if set (compute nodes have no git), else git describe."""
    if os.environ.get("MOANA_GIT"):
        return os.environ["MOANA_GIT"]
    try:
        r = subprocess.run(["git", "-C", str(REPO), "describe", "--always", "--dirty"],
                           capture_output=True, text=True)
        return r.stdout.strip() or "unknown"
    except FileNotFoundError:
        return "unknown (no git)"


def subset(args):
    src, out, stamp = args
    dst = out / src.name.replace(".grb2", ".nz.nc")
    if dst.exists():
        return f"skip {dst.name}"
    recs, meta, lat, lon = read_records(src)
    ds = to_dataset(src, recs, meta, lat, lon)
    check_cfgrib(src, ds)
    ds.attrs = {
        "title": f"CFSv2 hourly {src.name.split('.')[0]}, cut to the Moana box",
        "source": "NCEP Climate Forecast System Version 2 (CFSv2) 6-hourly "
                  "products, NCAR GDEX d094001, doi:10.5065/D6N877VB",
        "license": "CC BY 4.0",
        "source_file": src.name,
        "source_url": f"{URL}/{src.name.split('.')[2][:4]}/{src.name}",
        "source_sha256": source_sha256(src),
        "box_W_E_S_N": list(BOX),
        "history": f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ} "
                   f"{stamp}; values as decoded by eccodes, checked against cfgrib",
        "Conventions": "CF-1.8",
    }
    enc = {v: {"zlib": True, "complevel": 4, "shuffle": True} for v in ds.data_vars}
    tmp = dst.with_name(dst.name + ".part")
    ds.to_netcdf(tmp, encoding=enc)
    os.replace(tmp, dst)
    return f"ok   {dst.name} ({len(recs)} records)"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("files", nargs="*", help="file names in --src (default: all)")
    p.add_argument("--src", type=Path, default=SRC)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--jobs", type=int, default=1)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    files = [a.src / f for f in a.files] or sorted(a.src.glob("*.grb2"))
    stamp = (f"scripts/subset_cfsv2.py (sha256 {sha256(__file__)[:16]}, "
             f"Moana-2.0 git {git_version()})")
    print(stamp, flush=True)
    failed = 0
    with Pool(a.jobs) as pool:
        for f, r in zip(files, pool.imap(_safe, [(f, a.out, stamp) for f in files])):
            print(r, flush=True)
            failed += r.startswith("FAIL")
    outs = sorted(a.out.glob("*.nz.nc"))
    (a.out / "SHA256SUMS").write_text(
        "".join(f"{sha256(f)}  {f.name}\n" for f in outs))
    print(f"done: {len(outs)} files in {a.out}, {failed} failed", flush=True)
    sys.exit(1 if failed else 0)


def _safe(args):
    try:
        return subset(args)
    except Exception as e:  # report and carry on with the other files
        return f"FAIL {args[0].name}: {type(e).__name__}: {e}"


if __name__ == "__main__":
    main()
