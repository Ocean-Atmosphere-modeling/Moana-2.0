"""
Build a ROMS boundary file from CMEMS (DataMesh) strips, one strip per open boundary.

Input:  RAW/<side>/*.nc for each side in SIDES: CMEMS fields on a bbox strip around that ROMS boundary line
Output: one boundary file with temp/salt/u/v/ubar/vbar/zeta _<side>, on a shared bry_time
        bry_zlevels_<CHECK_TIME>.nc next to it: the 3-D fields at one record after step c only
        (still on the CMEMS levels), for scripts/plot_bry_vertical_check.py

Same method as interp_u_ic.py, applied to a 1-D line of points per side and looped over time:
  1. ROMS grid -> boundary lines and their depths                  (xroms)
  2. For each side, for each block of time steps:
     a. load the strip, keep only +-PAD deg around the boundary line
     b. fill NaNs (same-depth neighbours, then downward, then the rest)
     c. horizontal interpolation to the boundary line            (xarray)
     d. vertical interpolation to the s-levels                    (xarray + np.interp)
     e. mask land, depth-average u/v to ubar/vbar
  3. Write

Assumptions (checked where possible)
- Grid is rectangular in lon/lat: CMEMS uo/vo are ROMS u/v with no rotation.
- CMEMS depth axis is elevation: negative-up, ordered deep -> surface (DataMesh convention).
- Depths and layer thicknesses use zeta = 0.
- Raw files for one side can be opened together with open_mfdataset (same coords, split by time or variable).
"""
import glob
import time
import numpy as np
import xarray as xr
import xroms
from scipy.ndimage import convolve

# %% 0. Settings
GRID = "/projects/f_omg_1/moa/moana/moana_grid_N50.nc"
RAW = "/projects/f_omg_1/moa/moana/oceanum_input/boundary_cond/raw"
OUT = "/projects/f_omg_1/moa/moana/oceanum_input/boundary_cond/roms-ready/nz5km_N50_bry.nc"
SIDES = ["south", "north"]                         # drop any closed boundary; west/east not downloaded yet
VTRANSFORM = 2
REF_TIME = "2026-01-01"                            # TIME_REF in ocean.in
START = "2026-01-01"                               # first day of the run
CHECK_TIME = None                                  # record written to bry_zlevels_*.nc; None: first record at or after START
LON, LAT, DEPTH, TIME = "longitude", "latitude", "elevation", "time"
VARS = {                                           # CMEMS name: (ROMS name, point type)
    "thetao": ("temp", "rho"),
    "so": ("salt", "rho"),
    "uo": ("u", "u"),
    "vo": ("v", "v"),
    "zos": ("zeta", "rho"),
}
PAD = 1.0                                          # deg of strip kept either side of the boundary line
N_LATERAL = 10                                     # same-depth fill reach, in CMEMS cells
TBLOCK = 30                                        # time steps processed at once
TIMES = slice(None)                                # all times; e.g. slice("2026-01-01", "2026-01-03T00") for a 2-day test

# %% 1. ROMS grid: boundary lines and their depths (xroms)
grid = xr.open_dataset(GRID)
grid["zeta"] = xr.zeros_like(grid.h)
grid, xgrid = xroms.roms_dataset(grid, Vtransform=VTRANSFORM)
assert float(abs(grid.angle).max()) < 1e-3, "grid is rotated: u/v need rotating with the angle"

# xroms renames eta_u -> eta_rho and xi_v -> xi_rho; map back for the file
ROMS_DIMS = {"rho": {}, "u": {"eta_rho": "eta_u"}, "v": {"xi_rho": "xi_v"}}


def roms_dims(da, pt):
    return da.rename({k: v for k, v in ROMS_DIMS[pt].items() if k in da.dims})
POINTS = {                                         # h = -(bottom w-level), as in the s-levels
    "rho": dict(z=grid.z_rho, lon=grid.lon_rho, lat=grid.lat_rho, mask=grid.mask_rho, dz=grid.dz,
                h=-grid.z_w.isel(s_w=0)),
    "u": dict(z=grid.z_rho_u, lon=grid.lon_u, lat=grid.lat_u, mask=grid.mask_u, dz=grid.dz_u,
              h=-grid.z_w_u.isel(s_w=0)),
    "v": dict(z=grid.z_rho_v, lon=grid.lon_v, lat=grid.lat_v, mask=grid.mask_v, dz=grid.dz_v,
              h=-grid.z_w_v.isel(s_w=0)),
}


def edge(da, side):
    """The boundary line of a 2-D/3-D grid field: first or last row/column."""
    axis = "eta_" if side in ("south", "north") else "xi_"
    dim = next(d for d in da.dims if d.startswith(axis))
    return da.isel({dim: 0 if side in ("south", "west") else -1}).reset_coords(drop=True)


def lines(side, pt):
    """Boundary-line versions of the POINTS entries, with longitude on 0-360."""
    out = {k: edge(v, side) for k, v in POINTS[pt].items()}
    out["lon"] = out["lon"] % 360
    return out


# %% 2. Fill and interpolate
def flood_fill(da, max_passes=None):
    """Fill NaNs with the mean of valid 3x3 neighbours at the same depth, one ring of cells per pass.

    Same result as da.fillna(da.rolling({LON: 3, LAT: 3}, center=True, min_periods=1).mean())
    repeated, but ~7x faster via scipy (exact sums; uniform_filter's running sums are not exact).
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
    assert bool(cm.notnull().any()), "field is all NaN"
    cm = flood_fill(cm, max_passes=N_LATERAL)          # a. same-depth neighbours (coasts, slopes)
    if DEPTH in cm.dims:
        cm = cm.bfill(DEPTH)                           # b. deepest valid value copied downward
    return flood_fill(cm)                              # c. whatever is left (land interiors)


def horizontal(cm, ln):
    """CMEMS strip (time, [depth], lat, lon) -> boundary line (time, [depth], line), per depth level."""
    return cm.interp({LON: ln["lon"], LAT: ln["lat"]})


def vertical(cm_h, ln):
    """Boundary line on the CMEMS levels (time, depth, line) -> on the s-levels (time, s_rho, line), per column."""
    return xr.apply_ufunc(
        np.interp, ln["z"], cm_h[DEPTH], cm_h,
        input_core_dims=[["s_rho"], [DEPTH], [DEPTH]],
        output_core_dims=[["s_rho"]],
        vectorize=True,
    )


def to_line(cm, ln):
    """CMEMS strip (time, [depth], lat, lon) -> boundary line (time, [s_rho], line), land set to 0."""
    cm_h = horizontal(cm, ln)
    if DEPTH not in cm.dims:
        return cm_h.where(ln["mask"] == 1, 0.0)
    return vertical(cm_h, ln).where(ln["mask"] == 1, 0.0)


def open_side(side):
    files = sorted(glob.glob(f"{RAW}/{side}/*.nc"))
    assert files, f"no files in {RAW}/{side}"
    ds = xr.open_mfdataset(files, combine="by_coords")
    ds = ds.assign_coords({LON: ds[LON] % 360}).sortby(LON).sortby(TIME)
    ds = ds.drop_duplicates(TIME)                                        # overlapping downloads
    ds = ds.sel({TIME: TIMES})
    assert ds[DEPTH].attrs.get("positive") == "up" and bool((ds[DEPTH].diff(DEPTH) > 0).all()), \
        "expected elevation: negative-up, ordered deep -> surface"
    return ds


bry = {}
check = {}                                                              # step c only, at one record: bry_zlevels_*.nc
t_checks = set()
for side in SIDES:
    ds = open_side(side)
    t_check = ds[TIME].sel({TIME: np.datetime64(CHECK_TIME or START)}, method="bfill").values
    t_checks.add(t_check)
    ln = {pt: lines(side, pt) for pt in POINTS}
    lon0, lon1 = min(l["lon"].min() for l in ln.values()), max(l["lon"].max() for l in ln.values())
    lat0, lat1 = min(l["lat"].min() for l in ln.values()), max(l["lat"].max() for l in ln.values())
    ds = ds.sel({LON: slice(lon0 - PAD, lon1 + PAD), LAT: slice(lat0 - PAD, lat1 + PAD)})
    print(f"{side}: {ds.sizes[TIME]} times, strip {dict(ds.sizes)}")

    here = {cv: VARS[cv] for cv in VARS if cv in ds}                  # skip variables not downloaded yet
    print(f"  missing in {RAW}/{side}: {sorted(set(VARS) - set(here))}")
    blocks = {v: [] for v in here}
    t_read = t_interp = 0.0                                             # seconds: read from disk, fill + interpolate
    for t0 in range(0, ds.sizes[TIME], TBLOCK):
        tic = time.perf_counter()
        blk = ds.isel({TIME: slice(t0, t0 + TBLOCK)}).load()
        t_read += time.perf_counter() - tic
        tic = time.perf_counter()
        for cv, (rv, pt) in here.items():
            filled = fill(blk[cv])
            blocks[cv].append(to_line(filled, ln[pt]))
            if DEPTH in filled.dims and t_check in blk[TIME].values:
                cm_h = horizontal(filled.sel({TIME: t_check}), ln[pt]).reset_coords(drop=True)
                check[f"{rv}_{side}"] = roms_dims(cm_h, pt)
        t_interp += time.perf_counter() - tic
        print(f"  {side}: {min(t0 + TBLOCK, ds.sizes[TIME])}/{ds.sizes[TIME]}")
    print(f"  {side} timing: read {t_read:.1f} s, fill + interpolation {t_interp:.1f} s")
    for pt in {pt for cv, (rv, pt) in here.items() if DEPTH in ds[cv].dims}:   # the lines of bry_zlevels_*.nc
        for k in ("lon", "lat", "h", "mask"):
            check[f"{k}_{pt}_{side}"] = roms_dims(ln[pt][k], pt)

    for cv, (rv, pt) in here.items():
        da = xr.concat(blocks[cv], dim=TIME).reset_coords(drop=True)     # keep only the time coordinate
        order = [TIME] + (["s_rho"] if "s_rho" in da.dims else [])      # ROMS order: time, s_rho, line
        bry[f"{rv}_{side}"] = roms_dims(da, pt).transpose(*order, ...)
    for rv, pt in (("u", "u"), ("v", "v")):                             # thickness-weighted depth mean
        if f"{rv}_{side}" not in bry:
            continue
        dz, mask = roms_dims(ln[pt]["dz"], pt), roms_dims(ln[pt]["mask"], pt)
        bar = (bry[f"{rv}_{side}"] * dz).sum("s_rho") / dz.sum("s_rho")
        bry[f"{rv}bar_{side}"] = bar.where(mask == 1, 0.0).reset_coords(drop=True)

# %% 3. Write
out = xr.Dataset(bry).rename({TIME: "bry_time"})
out = out.drop_vars([c for c in out.coords if c != "bry_time"])          # no index coords on xi/eta/s_rho
for v in out.data_vars:
    assert not out[v].isnull().any(), f"NaNs in {v}"
    out[v].attrs = {"long_name": f"{v.split('_')[0]} {v.split('_')[1]}ern boundary condition", "time": "bry_time"}
out["bry_time"].encoding = {"units": f"days since {REF_TIME}", "calendar": "proleptic_gregorian", "dtype": "float64"}
out.attrs = {"title": "ROMS boundary conditions from CMEMS via DataMesh", "grid": GRID,
             "Vtransform": VTRANSFORM, "N": grid.sizes["s_rho"]}
out.to_netcdf(OUT)
print(f"Wrote {OUT}: {dict(out.sizes)}")
# %% 4. Write the check file: 3-D fields after the horizontal step only, at one record
assert len(t_checks) == 1, f"CHECK_TIME record differs between sides: {t_checks}"
stamp = np.datetime_as_string(t_checks.pop(), unit="h")
zl = xr.Dataset(check)
zl.attrs = {"title": "Boundary lines after the horizontal interpolation only, on the CMEMS levels",
            "time": stamp, "bry_file": OUT,
            "note": "elevation is negative-up; h = depth of the line at that point type; mask 1 = ocean"}
zl_out = OUT.rsplit("/", 1)[0] + f"/bry_zlevels_{stamp}.nc"
zl.to_netcdf(zl_out)
print(f"Wrote {zl_out}: {dict(zl.sizes)}")
