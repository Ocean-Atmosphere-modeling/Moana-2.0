# run with 'moana_pyroms' conda environment


import xarray as xr
# import xroms
import numpy as np 
import pandas as pd 
import matplotlib.pyplot as plt 
from pyroms.vgrid import s_coordinate_5


SRC = "/projects/f_omg_1/moa/moana/grd_moana5km.nc"          # existing grid file; not modified
DST = "/projects/f_omg_1/moa/moana/moana_grid_N50.nc"      # new grid file name
FORMAT = "NETCDF3_64BIT"    # same format as the original Moana grid file

# upload the old grid with N=40
g = xr.open_dataset(SRC)
print('opening the old grid files')


# Setting up the updated grid parameters
VTRANSFORM = 2
VSTRETCHING = 5
THETA_S = 6.0
THETA_B = 2.0
TCLINE = 250.0
N = 50

VERT = ("s_rho", "s_w", "Cs_r", "Cs_w", "theta_s", "theta_b", "Tcline", "hc")

# computing the vertical dimension and s_rho on 50 levels using pyroms
vgrd = s_coordinate_5(g["h"].values, THETA_B, THETA_S, TCLINE, N)

# preparing new grid
attrs = {v: g[v].attrs for v in VERT if v in g.variables}
g = g.drop_vars([v for v in VERT if v in g.variables])
 
g["s_rho"] = ("s_rho", vgrd.s_rho, attrs.get("s_rho", {}))
g["s_w"] = ("s_w", vgrd.s_w, attrs.get("s_w", {}))
g["Cs_r"] = ("s_rho", vgrd.Cs_r, attrs.get("Cs_r", {}))
g["Cs_w"] = ("s_w", vgrd.Cs_w, attrs.get("Cs_w", {}))
for name in ("theta_s", "theta_b", "Tcline", "hc"):     # hc = Tcline for Vtransform = 2
    g[name] = ((), getattr(vgrd, name), attrs.get(name, {}))

print('start saving the new grid')

# don't let xarray add _FillValue attributes that weren't in the original
g.to_netcdf(DST, format=FORMAT, encoding={v: {"_FillValue": None} for v in g.variables})
print(f"Wrote {DST}: N={N}, Vtransform={VTRANSFORM}, Vstretching={VSTRETCHING}, "
      f"theta_s={THETA_S}, theta_b={THETA_B}, Tcline=hc={TCLINE}")