"""
This script is to interpolate raw cmems initial condition file on roms grid
With one condition that the roms grid should not be rotated with respect to the lon/lat lines.
"""

import xarray as xr
import xroms
import numpy as np 
import matplotlib.pyplot as plt 

var = 'salt'                                          # ROMS variable to make: 'u', 'v', 'temp', 'salt'
# ROMS variable: (CMEMS name, ROMS point type, long_name, units)
VARS = {
    "u": ("uo", "u", "u-momentum component", "meter second-1"),
    "v": ("vo", "v", "v-momentum component", "meter second-1"),
    "temp": ("thetao", "rho", "potential temperature", "Celsius"),
    "salt": ("so", "rho", "salinity", "PSU"),
}
VAR, pt, long_name, units = VARS[var]
REF_TIME = "2026-01-01"                                      # TIME_REF in yaml suman: fix this later for yaml version
grid_path = '/projects/f_omg_1/moa/moana/moana_grid_N50.nc'
source_file = '/projects/f_omg_1/moa/moana/oceanum_input/initial_cond/ic_so_raw_2026-01-01.nc'
target_file = f'/projects/f_omg_1/moa/moana/oceanum_input/initial_cond/roms_ready/ic_{var}_2026-01-01.nc'

g = xr.open_dataset(grid_path)
g['zeta'] = xr.zeros_like(g.h)
grid, xgrid = xroms.roms_dataset(g, Vtransform=2)




def grid_points(grid, pt):
    """Target depths, coordinates and mask at ROMS 'rho', 'u' or 'v' points."""
    sfx = "" if pt == "rho" else f"_{pt}"
    return dict(
        z=grid[f"z_rho{sfx}"].reset_coords(drop=True),
        lon=(grid[f"lon_{pt}"] % 360).reset_coords(drop=True),
        lat=grid[f"lat_{pt}"].reset_coords(drop=True),
        mask=grid[f"mask_{pt}"].reset_coords(drop=True),
        dz=grid[f"dz{sfx}"].reset_coords(drop=True),
    )

p = grid_points(grid, pt)
z, lon, lat, mask, dz = p["z"], p["lon"], p["lat"], p["mask"], p["dz"]


# loading cmems input file
ds1 = xr.open_dataset(source_file)
LON, LAT, DEPTH, TIME = "longitude", "latitude", "elevation", "time"



assert float(abs(grid.angle).max()) < 1e-3, "grid is rotated: u must be rotated using vo as well"
# put a note on the top that this code should be updated in teh case where the grid is rotated

cm = ds1[VAR].isel({TIME: 0}).load()
cm = cm.assign_coords({LON: cm[LON] % 360}).sortby(LON)
t0 = cm[TIME].values
print(dict(cm.sizes), "| NaN fraction:", round(float(cm.isnull().mean()), 3))

assert bool(cm.notnull().any()), "CMEMS field is all NaN"

def flood_fill(da, max_passes=None):
    """Fill NaNs with the mean of valid neighbours at the same depth, one ring of cells per pass."""
    n = 0
    while bool(da.isnull().any()) and (max_passes is None or n < max_passes):
        da = da.fillna(da.rolling({LON: 3, LAT: 3}, center=True, min_periods=1).mean())
        n += 1
    return da

# 3a. Same-depth neighbours first (right for slopes and coasts), within N_LATERAL cells
N_LATERAL = 10                                     # ~0.8 deg at 1/12 deg
cm_f = flood_fill(cm, max_passes=N_LATERAL)
 
# 3b. Anything still missing below the CMEMS seafloor: copy each column's deepest valid value downward
cm_f = cm_f.bfill(DEPTH)          # axis is deep -> surface, so "backward" = toward the seafloor
cm_f = flood_fill(cm_f)


# 4. Horizontal: CMEMS -> ROMS u-points (bilinear), on every CMEMS depth level
cm_h = cm_f.interp({LON: lon, LAT: lat})       # (depth, eta_rho, xi_u)

# 5. Vertical: CMEMS depth levels -> ROMS s-levels, column by column
# np.interp holds the end values beyond the data: above CMEMS's top level and below its bottom level
da = xr.apply_ufunc(
    np.interp, z, cm_h[DEPTH], cm_h,
    input_core_dims=[["s_rho"], [DEPTH], [DEPTH]],
    output_core_dims=[["s_rho"]],
    vectorize=True,
).transpose("s_rho", ...)
da.attrs = {"long_name": long_name, "units": units}   # not z's attributes

da = da.where(mask ==1, 0)
ocean = mask == 1
assert not da.isnull().any(), "NaNs left in data"
print(f'Interpolation of {var} is done')

# interpolation and neighbour-averaging can't create values outside the CMEMS range
assert float(da.where(ocean).min()) >= float(cm.min()) and float(da.where(ocean).max()) <= float(cm.max())
print(f"CMEMS {VAR}: {float(cm.min()):.3f} to {float(cm.max()):.3f} {units}")
print(f"ROMS {var}:   {float(da.where(ocean).min()):.3f} to {float(da.where(ocean).max()):.3f} {units}")
 

# 7. Visual check: one ocean column, CMEMS vs ROMS
# import matplotlib.pyplot as plt

# j, i = 200, 50                                     # any ocean u-point
# ZOOM = None                                        # elevation (m) to zoom to; None for full column
# assert bool(ocean[j, i]), "pick an ocean point"
# pt_lon, pt_lat = float(lon[j, i]), float(lat[j, i])

# fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
# cm.sel({LON: pt_lon, LAT: pt_lat}, method="nearest").plot(y=DEPTH, ax=ax1, marker=".", label="CMEMS (nearest)")
# ax1.plot(da[:, j, i], z[:, j, i], "r.-", label="ROMS")
# if ZOOM is not None:
#     ax1.set_ylim(ZOOM, 0)
# ax1.set_xlabel("u (m/s)"); ax1.set_ylabel("z (m)"); ax1.legend()
# ax1.set_title(f"{pt_lon:.2f}E, {pt_lat:.2f}N  (h = {float(grid.h[j, i]):.0f} m)")
# da.isel(s_rho=-1).where(ocean).plot(ax=ax2)
# ax2.plot(i, j, "kx")
# ax2.set_title("ROMS surface u")
# plt.show()
## comment for Nikki: Hi @Nikki can you please add one piece of code here which can plot any data this script is making roms format?

print(f'Now trying to save the file {target_file}')
# save in ROMS layout: var(ocean_time, s_rho, eta, xi), with ROMS dimension names
ROMS_DIMS = {"rho": {}, "u": {"eta_rho": "eta_u"}, "v": {"xi_rho": "xi_v"}}   # xroms renamed these
out = (da.rename({k: v for k, v in ROMS_DIMS[pt].items() if k in da.dims})
         .reset_coords(drop=True)                  # drop leftover lon/lat/time coordinates
         .drop_vars(["eta_rho", "xi_rho", "eta_u", "xi_u", "eta_v", "xi_v"], errors="ignore")
         .expand_dims(ocean_time=[t0])
         .to_dataset(name=var))                    # name it, or it keeps the name of z
out["ocean_time"].encoding = {"units": f"seconds since {REF_TIME}", "calendar": "proleptic_gregorian"}
out.to_netcdf(target_file)

print('done with creating roms format data')