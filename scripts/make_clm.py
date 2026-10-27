"""
This script is to interpolate the raw cmems climatology files (from download_clm.py) on roms grid.
Same method as make_ic.py, for every record in the raw files.
With one condition that the roms grid should not be rotated with respect to the lon/lat lines.

    python scripts/make_clm.py temp        # one of u, v, temp, salt (default salt)

Output: one file per variable, OUT_DIR/clm_<var>_<first day>_<last day>.nc, so ROMS reads four
climatology files (NCLMFILES = 4). The time variable has the ROMS default name for that field
(varinfo.yaml): v3d_time for u and v, temp_time, salt_time.
Records are written one at a time, so only one record is in memory.
"""

import sys
import glob
import time
import numpy as np
import pandas as pd
import xarray as xr
import xroms
import netCDF4
from scipy.ndimage import convolve

var = sys.argv[1] if len(sys.argv) > 1 else 'salt'   # ROMS variable to make: 'u', 'v', 'temp', 'salt'
# ROMS variable: (CMEMS name, raw file name, ROMS point type, ROMS time name, long_name, units)
VARS = {
    "u": ("uo", "uo_vo", "u", "v3d_time", "u-momentum component climatology", "meter second-1"),
    "v": ("vo", "uo_vo", "v", "v3d_time", "v-momentum component climatology", "meter second-1"),
    "temp": ("thetao", "thetao", "rho", "temp_time", "potential temperature climatology", "Celsius"),
    "salt": ("so", "so", "rho", "salt_time", "salinity climatology", "PSU"),
}
VAR, SRC, pt, TNAME, long_name, units = VARS[var]
REF_TIME = "2026-01-01"                                      # TIME_REF in ocean.in
grid_path = '/projects/f_omg_1/moa/moana/grid/moana_grid_N50.nc'
source_files = f'/projects/f_omg_1/moa/moana/oceanum_input/climatology/raw/{SRC}_raw_*.nc'
OUT_DIR = '/projects/f_omg_1/moa/moana/oceanum_input/climatology/roms_ready'
TIMES = slice(None)                     # all records; e.g. slice("2026-01-01", "2026-01-02") for a test
N_LATERAL = 10                          # same-depth fill reach, in CMEMS cells (~0.8 deg at 1/12 deg)
LON, LAT, DEPTH, TIME = "longitude", "latitude", "elevation", "time"

g = xr.open_dataset(grid_path)
g['zeta'] = xr.zeros_like(g.h)
grid, xgrid = xroms.roms_dataset(g, Vtransform=2)
assert float(abs(grid.angle).max()) < 1e-3, "grid is rotated: u must be rotated using vo as well"

# target depths, coordinates and mask at ROMS 'rho', 'u' or 'v' points
sfx = "" if pt == "rho" else f"_{pt}"
z = grid[f"z_rho{sfx}"].reset_coords(drop=True)
lon = (grid[f"lon_{pt}"] % 360).reset_coords(drop=True)
lat = grid[f"lat_{pt}"].reset_coords(drop=True)
ocean = grid[f"mask_{pt}"].reset_coords(drop=True) == 1
DIMS = {"rho": ("s_rho", "eta_rho", "xi_rho"), "u": ("s_rho", "eta_u", "xi_u"), "v": ("s_rho", "eta_v", "xi_v")}[pt]

# loading cmems input files: one per time chunk, two chunks share one record
files = sorted(glob.glob(source_files))
assert files, f"no files match {source_files}"
ds = xr.open_mfdataset(files, combine="nested", concat_dim=TIME)
ds = ds.assign_coords({LON: ds[LON] % 360}).sortby(LON).drop_duplicates(TIME).sel({TIME: TIMES})
times = pd.DatetimeIndex(ds[TIME].values)
print(f"{len(files)} files, {len(times)} records: {times[0]} to {times[-1]}")


def flood_fill(da, max_passes=None):
    """Fill NaNs with the mean of valid 3x3 neighbours at the same depth, one ring of cells per pass.

    Same result as make_ic.py's xarray rolling mean, but faster (copied from make_bry.py).
    """
    a = da.transpose(..., LAT, LON).values.astype("float64")
    kernel = np.ones((1,) * (a.ndim - 2) + (3, 3))
    n = 0
    while np.isnan(a).any() and (max_passes is None or n < max_passes):
        valid = ~np.isnan(a)
        total = convolve(np.where(valid, a, 0.0), kernel, mode="constant")
        count = convolve(valid.astype("float64"), kernel, mode="constant")
        with np.errstate(invalid="ignore", divide="ignore"):
            a = np.where(valid, a, total / count)          # count == 0 -> NaN, stays unfilled this pass
        n += 1
    return da.copy(data=a).transpose(*da.dims)


def fill(cm):
    cm = flood_fill(cm, max_passes=N_LATERAL)     # same-depth neighbours first (slopes and coasts)
    cm = cm.bfill(DEPTH)                          # below the CMEMS seafloor: deepest valid value downward
    return flood_fill(cm)                         # whatever is left (land interiors)


def horizontal(cm, lon, lat):
    """CMEMS -> ROMS points (bilinear), on every CMEMS depth level."""
    return cm.interp({LON: lon, LAT: lat})


def vertical(cm_h, z):
    """CMEMS depth levels -> ROMS s-levels, column by column (end values held beyond the data)."""
    return xr.apply_ufunc(
        np.interp, z, cm_h[DEPTH], cm_h,
        input_core_dims=[["s_rho"], [DEPTH], [DEPTH]],
        output_core_dims=[["s_rho"]],
        vectorize=True,
    )


# empty ROMS file: var(TNAME, s_rho, eta, xi), with an unlimited time dimension
target_file = f"{OUT_DIR}/clm_{var}_{times[0]:%Y-%m-%d}_{times[-1]:%Y-%m-%d}.nc"
nc = netCDF4.Dataset(target_file, "w")
nc.createDimension(TNAME, None)
for d in DIMS:
    nc.createDimension(d, g.sizes[d])
t_nc = nc.createVariable(TNAME, "f8", (TNAME,))
t_nc.units = f"days since {REF_TIME}"
t_nc.calendar = "proleptic_gregorian"
v_nc = nc.createVariable(var, "f4", (TNAME,) + DIMS)
v_nc.long_name, v_nc.units, v_nc.time = long_name, units, TNAME
nc.title = f"ROMS climatology ({var}) from CMEMS via DataMesh"
nc.grid, nc.source = grid_path, source_files

for n, t in enumerate(times):
    tic = time.perf_counter()
    cm = ds[VAR].sel({TIME: t}).load()
    assert bool(cm.notnull().any()), f"CMEMS field is all NaN at {t}"

    da = vertical(horizontal(fill(cm), lon, lat), z).transpose("s_rho", ...)
    da = da.where(ocean, 0)
    assert not da.isnull().any(), f"NaNs left in data at {t}"
    # interpolation and neighbour-averaging can't create values outside the CMEMS range
    assert float(da.where(ocean).min()) >= float(cm.min()) and float(da.where(ocean).max()) <= float(cm.max())

    v_nc[n] = da.values
    t_nc[n] = (t - pd.Timestamp(REF_TIME)) / pd.Timedelta("1D")
    print(f"{n + 1}/{len(times)} {t}: {float(da.where(ocean).min()):.3f} to "
          f"{float(da.where(ocean).max()):.3f} {units}, {time.perf_counter() - tic:.1f} s")

nc.close()
print(f"wrote {target_file}")
