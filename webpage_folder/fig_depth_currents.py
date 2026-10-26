"""Figure: why currents are TPXO transport / ROMS h, not the TPXO velocity.

Usage (moana_python environment):  python webpage_folder/fig_depth_currents.py
Writes webpage_folder/figures/depth_currents.png. Three panels on the ROMS grid:
  left    TPXO depth / ROMS h (both on the ROMS points)
  middle  M2 peak current (Cmax) from the TPXO velocity
  right   M2 peak current (Cmax) from TPXO transport / ROMS h   (what make_tides.py does)
No nodal correction in the middle and right panels, so they differ only by the depth.
Prints the largest Cmax and the number of points above 2 m/s for both.
"""
import matplotlib.pyplot as plt
import numpy as np
import pyTMD
import xarray as xr
from matplotlib.colors import LogNorm

from common import GRID, TPXO, fill_land, map_axes, save

tpxo = xr.open_dataset(TPXO).sel(con=["M2"])
grid = xr.open_dataset(GRID)
water = grid.mask_rho == 1
lon = xr.DataArray(grid.lon_rho.values, dims=("eta_rho", "xi_rho"))
lat = xr.DataArray(grid.lat_rho.values, dims=("eta_rho", "xi_rho"))
h = grid.h.values


def to_roms(values):
    """Fill TPXO land, then bilinear to the ROMS points. values: (con, lat, lon)."""
    filled = xr.DataArray(fill_land(values), dims=("con", "lat", "lon"),
                          coords={"lat": tpxo.lat, "lon": tpxo.lon})
    return filled.interp(lon=lon, lat=lat).values


u = (tpxo.uRe + 1j * tpxo.uIm).values
v = (tpxo.vRe + 1j * tpxo.vIm).values
dep = tpxo.dep.where(~np.isnan(tpxo.hRe[0])).values[None]

tpxo_depth = to_roms(dep)[0]
cmax_velocity = pyTMD.ellipse.ellipse(to_roms(u), to_roms(v))[0][0]
cmax_transport = pyTMD.ellipse.ellipse(to_roms(u * dep) / h, to_roms(v * dep) / h)[0][0]

for name, cmax in [("TPXO velocity", cmax_velocity), ("transport / ROMS h", cmax_transport)]:
    wet = cmax[water]
    print(f"{name}: max Cmax {wet.max():.2f} m/s, {(wet > 2).sum()} points above 2 m/s")

fig, axes = plt.subplots(1, 3, figsize=(15, 5.6), constrained_layout=True)
pc = axes[0].pcolormesh(lon, lat, np.where(water, tpxo_depth / h, np.nan), cmap="RdBu_r",
                        norm=LogNorm(0.1, 10))
bar = fig.colorbar(pc, ax=axes[0], shrink=0.8, extend="both", label="TPXO depth / ROMS h")
bar.set_ticks([0.1, 0.2, 0.5, 1, 2, 5, 10], labels=["0.1", "0.2", "0.5", "1", "2", "5", "10"])
axes[0].set_title("Depth ratio (blue: TPXO shallower)")

for ax, cmax, title in [(axes[1], cmax_velocity, "M2 Cmax from TPXO velocity"),
                        (axes[2], cmax_transport, "M2 Cmax from transport / ROMS h")]:
    pc = ax.pcolormesh(lon, lat, np.where(water, cmax, np.nan), cmap="magma", vmin=0, vmax=2)
    ax.set_title(title)
fig.colorbar(pc, ax=axes[1:], shrink=0.8, extend="max", label="m/s")

for ax in axes:
    map_axes(ax)
for ax in axes[1:]:
    ax.annotate("Stewart Island shelf", xy=(168.4, -47.6), xytext=(171.5, -50.5), fontsize=9,
                color="white", arrowprops={"arrowstyle": "-", "color": "white", "lw": 0.8})

save(fig, "depth_currents.png")
