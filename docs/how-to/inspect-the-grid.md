# How to inspect the grid

**Goal:** the Moana grid loaded with xroms and its bathymetry plotted.
**Time:** minutes

## Prerequisites
- The grid file (see [fetch the published configuration](fetch-published-config.md))
- The `moana_python` conda environment ([environment](../reference/environment.md))

## Steps
1. Open `Moana_grid.ipynb` with a Python kernel that has the `moana_python`
   packages. `env/moana_python.yml` has no Jupyter or `ipykernel`, so a
   notebook front end must come from elsewhere: ❓ UNKNOWN which one the
   project uses.
2. Run the cells. The notebook reads the grid, sets `Vtransform = 2` and
   `Vstretching = 5`, builds the xroms grid and plots `h`.

## Check it worked
A map of `h` over 161–185° E, 31–52° S, depths 10–6000 m.

## If it goes wrong
| Symptom | Likely cause | Fix |
|---|---|---|
| File not found | The notebook reads `/projects/f_omg_1/moa/moana/grd_moana5km.nc` | Point `data_folder`/`file_name` at the grid listed in `inputs.tsv` ([risk R11](../risks.md)) |
| `ModuleNotFoundError: xroms` | Wrong conda environment (the notebook was run in `chapter1`) | Activate `moana_python` |
