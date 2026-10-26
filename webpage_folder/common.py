"""Paths, colours and small helpers shared by the tide webpage figure scripts."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import distance_transform_edt

HERE = Path(__file__).resolve().parent
FIGURES = HERE / "figures"

GRID = "/projects/f_omg_1/moa/moana/moana_grid_N50.nc"
TPXO = "/projects/f_omg_1/moa/moana/oceanum_input/tide_forcing/tpxo9_atlas_v5_moana.nc"
TIDES = "/projects/f_omg_1/moa/moana/oceanum_input/tide_forcing/moana_tides.nc"

INK = "#13232d"
MUTED = "#546570"
LAND = "#c9c1b2"
SEA = "#dcecf1"
MARK = "#a3296c"                    # notes and highlights, same magenta as the webpage
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # categorical colours, fixed order

# Three places used in more than one figure: (lon, lat)
PLACES = {
    "Taranaki Bight": (173.4, -39.6),
    "Cook Strait": (174.6, -41.4),
    "Otago shelf": (171.0, -45.9),
}

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": MUTED, "axes.spines.top": False, "axes.spines.right": False,
})


def save(fig, name):
    FIGURES.mkdir(exist_ok=True)
    fig.savefig(FIGURES / name, dpi=130, facecolor="white")
    print(f"wrote {FIGURES / name}")


def fill_land(values):
    """Each NaN (land) cell takes the value of its nearest non-NaN cell. Same as make_tides.py."""
    i, j = distance_transform_edt(np.isnan(values[0]), return_distances=False, return_indices=True)
    return values[:, i, j]


def nearest_water(grid, lon, lat):
    """Index (eta, xi) of the ROMS water point nearest to lon, lat."""
    dist = (grid.lon_rho.values - lon) ** 2 + (grid.lat_rho.values - lat) ** 2
    dist[grid.mask_rho.values == 0] = np.inf
    return np.unravel_index(np.argmin(dist), dist.shape)


def map_axes(ax):
    """Land colour behind the data, equal distances, degree labels."""
    ax.set_facecolor(LAND)
    ax.set_aspect(1 / np.cos(np.radians(41)))
    ax.set_xlabel("longitude (°E)")
    ax.set_ylabel("latitude (°N)")
