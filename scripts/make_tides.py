"""
Build a ROMS tide forcing file (TIDENAME) from TPXO9-atlas-v5.

Python version of the MATLAB OTPS scripts in Code-Commons/examples/tides
(process_tides_GOG.m -> otps2frc_v7.m). pyTMD replaces t_tide; xarray replaces extract_HC (OTPS).

Input: the DataMesh TPXO cut (scripts/fetch_tpxo.py): hRe, hIm [m], uRe, uIm, vRe, vIm [m/s]
on a lon/lat grid, one layer per constituent. Complex harmonic = Re + i*Im = amp * exp(-i * phase).

  1. ROMS grid
  2. Harmonics on the ROMS grid: fill TPXO land with the nearest TPXO water, then bilinear.
     Currents are TPXO transport / ROMS h
  3. Nodal corrections: phase zero at REF_DATE, amplitude for NODAL_DATE
  4. u, v -> current ellipses
  5. Land = 0, write
"""
import numpy as np
import pandas as pd
import pyTMD
import xarray as xr
from scipy.ndimage import distance_transform_edt

# %% 0. Settings
GRID = "/projects/f_omg_1/moa/moana/grid/moana_grid_N50.nc"
TPXO = "/projects/f_omg_1/moa/moana/oceanum_input/tide_forcing/tpxo9_atlas_v5_moana.nc"
CONSTITUENTS = ["M2", "S2", "N2", "K2", "K1", "O1", "P1", "Q1", "MM", "MF", "M4", "MN4", "MS4", "2N2", "S1"]
REF_DATE = "2026-01-01"                  # phase zero time = TIME_REF + TIDE_START in moana.in
NODAL_DATE = "2026-02-15"                # date for nodal amplitude and phase: middle of the run
OUT = "/projects/f_omg_1/moa/moana/oceanum_input/tide_forcing/moana_tides.nc"

# %% 1. ROMS grid
grid = xr.open_dataset(GRID)
water = grid.mask_rho.values == 1
lon = xr.DataArray(grid.lon_rho.values % 360, dims=("eta_rho", "xi_rho"))
lat = xr.DataArray(grid.lat_rho.values, dims=("eta_rho", "xi_rho"))
h = xr.DataArray(grid.h.values, dims=("eta_rho", "xi_rho"))

# %% 2. Harmonics on the ROMS grid
tpxo = xr.open_dataset(TPXO).sel(con=CONSTITUENTS)


def harmonics(var, scale=1.0):
    """Complex harmonics (con, eta_rho, xi_rho) of var = h, u or v, times scale."""
    hc = (tpxo[var + "Re"] + 1j * tpxo[var + "Im"]) * scale
    i, j = distance_transform_edt(np.isnan(hc[0]), return_distances=False, return_indices=True)
    hc = hc.copy(data=hc.values[:, i, j])                 # each land cell takes its nearest water cell
    return hc.interp(lon=lon, lat=lat).drop_vars(["lon", "lat"])


# Currents: TPXO transport / ROMS depth. TPXO u = transport / TPXO depth, which is too large
# where the TPXO depth is too shallow (up to 12 m/s on the shelf south of Stewart Island).
z = harmonics("h")
u, v = harmonics("u", tpxo.dep) / h, harmonics("v", tpxo.dep) / h

# %% 3. Nodal corrections: amp * f, phase - (V + u)  (V at REF_DATE, f and u at NODAL_DATE)
def mjd(date):
    return np.array([(pd.Timestamp(date) - pd.Timestamp("1858-11-17")).days])


names = [c.lower() for c in CONSTITUENTS]
_, _, V = pyTMD.constituents.arguments(mjd(REF_DATE), names)
nodal_u, f, _ = pyTMD.constituents.arguments(mjd(NODAL_DATE), names)
correction = xr.DataArray(f[0] * np.exp(1j * (np.radians(V[0]) + nodal_u[0])), dims="con")
z, u, v = z * correction, u * correction, v * correction

# %% 4. Current ellipses
Cmax, Cmin, Cangle, Cphase = pyTMD.ellipse.ellipse(u.values, v.values)

# %% 5. Land = 0, write
dims = ("tide_period", "eta_rho", "xi_rho")
period_hours = 2 * np.pi / pyTMD.constituents.frequency(names) / 3600


def field(values, long_name, units):
    return xr.DataArray(np.where(water, values, 0.0), dims=dims, attrs={"long_name": long_name, "units": units})


out = xr.Dataset(
    {
        "zero_phase_date": ((), float(pd.Timestamp(REF_DATE).strftime("%Y%m%d")),
                            {"long_name": "tidal reference date for zero phase", "units": "days as %Y%m%d.%f"}),
        "tide_period": ("tide_period", period_hours, {"long_name": "tide angular period", "units": "hours"}),
        "tidal_constituents": ("tide_period", CONSTITUENTS, {"long_name": "Tidal Constituent Names"}),
        "tide_Eamp": field(np.abs(z.values), "tidal elevation amplitude", "meter"),
        "tide_Ephase": field(np.degrees(-np.angle(z.values)) % 360, "tidal elevation phase angle",
                             "degrees, time of maximum elevation with respect to chosen time origin"),
        "tide_Cmax": field(Cmax, "maximum tidal current, ellipse semi-major axis", "meter second-1"),
        "tide_Cmin": field(Cmin, "minimum tidal current, ellipse semi-minor axis", "meter second-1"),
        "tide_Cangle": field(Cangle, "tidal current inclination angle", "degrees between semi-major axis and East"),
        "tide_Cphase": field(Cphase, "tidal current phase angle",
                             "degrees, time of maximum velocity with respect chosen time origin"),
        "lon_rho": grid.lon_rho.reset_coords(drop=True),
        "lat_rho": grid.lat_rho.reset_coords(drop=True),
        "mask_rho": grid.mask_rho.reset_coords(drop=True),
    },
    attrs={"type": "ROMS Tidal Forcing File", "source": TPXO, "grid_file": GRID,
           "history": f"{pd.Timestamp.now():%Y-%m-%d %H:%M} scripts/make_tides.py"},
)
out.to_netcdf(OUT, encoding={"tidal_constituents": {"dtype": "S1"}})
print(f"wrote {OUT}")
