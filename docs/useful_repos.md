# GitHub repositories useful for the Moana rebuild

Survey done on 2026-10-01 by five search agents, one per area, each returning
its top 15. Every repository listed was fetched from GitHub (page, API record
or shallow clone) at that date. **Nothing was installed or run**, so what a
tool can do is taken from its source tree and README.

Stars and dates are a snapshot. The date column is GitHub's last-push date in
sections 1, 3 and 5 and the last commit on the default branch in sections 2
and 4.

Contents:
1. [Building ROMS input files](#1-building-roms-input-files)
2. [ROMS repositories scored for reproducibility](#2-roms-repositories-scored-for-reproducibility)
3. [Fetching and tracking data](#3-fetching-and-tracking-data)
4. [Analysing output and evaluating against observations](#4-analysing-output-and-evaluating-against-observations)
5. [Workflow and reproducibility infrastructure](#5-workflow-and-reproducibility-infrastructure)
6. [Shortlist](#6-shortlist)

---

## 1. Building ROMS input files

| # | Repo | Stars | Last push | Licence | Helps with | Caveats |
|---|---|---|---|---|---|---|
| 1 | [joaometocean/moana_hindcast](https://github.com/joaometocean/moana_hindcast) | 1 | 2022-04 | none | The original Moana config: `nz5km_grd.nc` (grid, bathymetry, mask), `roms.in`, `roms3d.h`, `roms_config.sh` | ROMS 3.9, needs porting to 4.2. No preprocessing scripts. `roms_src` is empty and the nudging file the README lists is missing (same in the Zenodo archive) |
| 2 | [myroms/roms_matlab](https://github.com/myroms/roms_matlab) | 25 | 2026-09 | none at root (headers say MIT/X style) | Nudging coefficients (`initial/d_nudgcoef.m`), sponge, TPXO tides (`forcing/otps2roms.m`), mask editing, smoothing, IC/BC from Mercator | MATLAB. No CFSR script, no river-file writer |
| 3 | [ESMG/pyroms](https://github.com/ESMG/pyroms) | 159 | 2023-12 | BSD-style | Grid, LP bathymetry smoothing, GLORYS IC/BC examples, TPXO tides, rivers | No push since 2023; custom installer with compiled Fortran; examples to adapt, not a library API |
| 4 | [powellb/seapy](https://github.com/powellb/seapy) | 33 | 2026-09 | MIT | Rivers (`roms/psource.py`), tide-file writer, bulk forcing, boundary/clim/initial | Forcing maps ship for GFS and NCEP only; no GLORYS or TPXO reader |
| 5 | [trondkr/model2roms](https://github.com/trondkr/model2roms) | 67 | 2026-04 | MIT | Initial, boundary and climatology files from GLORYS12 | Configured by editing a Python file; Fortran modules to compile. No tides, rivers or grid |
| 6 | [ivicajan/roms-bathy-smooth](https://github.com/ivicajan/roms-bathy-smooth) | 9 | 2026-09 | GPL-3.0 | Bathymetry smoothing, rx0/rx1 reporting | Young, single author. Its rx0/rx1 are sea-only by default, unlike ROMS |
| 7 | [parkermac/LO](https://github.com/parkermac/LO) | 15 | 2026-09 | MIT | Grid/mask/smoothing (`pgrid`), GLORYS IC/BC, tides, rivers | Built around one group's layout; mine it for code rather than install it |
| 8 | [pyTMD/pyTMD](https://github.com/pyTMD/pyTMD) | 211 | 2026-09 | MIT | Extracting TPXO harmonic constants at grid points | Does not write a ROMS tide file; pair with seapy |
| 9 | [CWorthy-ocean/roms-tools](https://github.com/CWorthy-ocean/roms-tools) | 39 | 2026-09 | Apache-2.0 | Best-engineered Python preprocessor (grid, smoothing, IC/BC, tides, forcing, rivers, nudging) | Targets UCLA-ROMS; its files are not usable by ROMS 4.2. Reference only |
| 10 | [DOI-USGS/COAWST](https://github.com/DOI-USGS/COAWST) | 158 | 2026-09 | custom | `Tools/mfiles`: rivers, tides, IC/BC/clim, forcing | MATLAB; whole coupled model; no CFSR |
| 11 | [martalmeida/okean](https://github.com/martalmeida/okean) | 28 | 2026-08 | EUPL-1.2 | CFSR bulk forcing (`make_blk_cfsr`), rivers, IC/BC | Effectively undocumented; CFSR reader from 2013 |
| 12 | [pygridgen/pygridgen](https://github.com/pygridgen/pygridgen) | 17 | 2024-10 | none | Grid generation, if the grid is regenerated | Needs gridgen-c built first |
| 13 | [sakov/gridgen-c](https://github.com/sakov/gridgen-c) | 47 | 2026-07 | custom | Orthogonal grid generator behind pygridgen | C library; gives coordinates, not a ROMS grid file |
| 14 | [lhico/pyroms_tools](https://github.com/lhico/pyroms_tools) | 6 | 2024-11 | none | Config-driven grid, IC/BC, TPXO tides, nudging file | Depends on pyroms (ships Docker because it is hard to build) |
| 15 | [evanmason/pyroms2roms](https://github.com/evanmason/pyroms2roms) | 6 | 2018-01 | LGPL-3.0 | CFSR bulk forcing, Mercator boundaries | Python 2, unmaintained, UCLA file conventions. Reference only |

**Gap:** no maintained Python tool converts CFSR/CFSv2 to Rutgers-ROMS bulk
forcing; expect to write that step.

---

## 2. ROMS repositories scored for reproducibility

**Answer: no public Rutgers-ROMS configuration repository is well organised
for reproducibility.** The best in the ROMS family (C-Star) drives UCLA-ROMS
and cannot run ROMS 4.2. The best templates to copy from are not ROMS at all.
This repository already combines things none of the Rutgers-ROMS repos do
(pinned submodule, locked environment, sha256 manifest, run receipt,
tolerance test).

Each repo is scored 0–2 on ten criteria (total out of 20):
1 source pinned, 2 header and `.in` in git, 3 input-generation scripts,
4 input provenance, 5 environment, 6 run scripts and restart chaining,
7 tests/CI, 8 per-run provenance, 9 documentation, 10 licence and release.

| # | Repo | Model | Stars | Last commit | Scores 1–10 | /20 |
|---|---|---|---|---|---|---|
| 1 | [CWorthy-ocean/C-Star](https://github.com/CWorthy-ocean/C-Star) | UCLA-ROMS framework (not Rutgers) | 22 | 2026-09 | 2/2/2/2/2/2/1/1/2/2 | 18 |
| 2 | [ACCESS-NRI/access-om3-configs](https://github.com/ACCESS-NRI/access-om3-configs) | not ROMS (MOM6-CICE6, payu) | 10 | 2026-09 | 2/2/0/2/2/2/2/2/2/2 | 18 |
| 3 | [NOAA-GFDL/CEFI-regional-MOM6](https://github.com/NOAA-GFDL/CEFI-regional-MOM6) | not ROMS (regional MOM6) | 26 | 2026-09 | 2/2/2/1/2/2/2/1/2/2 | 18 |
| 4 | [CWorthy-ocean/ucla-roms](https://github.com/CWorthy-ocean/ucla-roms) | UCLA-ROMS source and tests | 3 | 2026-09 | 2/2/1/1/2/1/2/0/2/2 | 15 |
| 5 | [SAEON/somisana-croco](https://github.com/SAEON/somisana-croco) | CROCO | 6 | 2026-09 | 2/2/2/1/2/2/1/0/1/1 | 14 |
| 6 | [DOI-USGS/COAWST](https://github.com/DOI-USGS/COAWST) | COAWST (ROMS + WRF + SWAN) | 158 | 2026-09 | 2/2/2/1/1/1/0/0/2/2 | 13 |
| 7 | [parkermac/LO](https://github.com/parkermac/LO) + [LO_roms_user](https://github.com/parkermac/LO_roms_user) | ROMS (LiveOcean) | 15 | 2026-09 | 1/2/2/1/1/2/0/1/1/2 | 13 |
| 8 | [myroms/roms](https://github.com/myroms/roms) | ROMS source | 144 | 2026-09 | 2/2/0/0/1/1/0/1/2/2 | 11 |
| 9 | [ioos/Cloud-Sandbox](https://github.com/ioos/Cloud-Sandbox) | multi-model incl. ROMS | 16 | 2026-09 | 0/1/0/1/2/2/1/0/2/2 | 11 |
| 10 | [myroms/roms_eccofs](https://github.com/myroms/roms_eccofs) | ROMS 4D-Var application | 5 | 2026-06 | 0/2/0/1/0/2/0/1/2/1 | 9 |
| 11 | [beringnpz/roms-bering-sea](https://github.com/beringnpz/roms-bering-sea) | ROMS (Bering10K) | 9 | 2025-02 | 2/2/0/0/1/1/0/0/1/2 | 9 |
| 12 | [alaurent101/ROMS_OAE](https://github.com/alaurent101/ROMS_OAE) | ROMS 3.9 fork with config | 0 | 2026-10 | 2/2/0/2/0/0/0/0/1/2 | 9 |
| 13 | [kshedstrom/roms](https://github.com/kshedstrom/roms) | ROMS ice-branch source | 72 | 2021-09 | 2/2/0/0/1/1/0/0/1/2 | 9 |
| 14 | [ACCESS-Community-Hub/roms-configs](https://github.com/ACCESS-Community-Hub/roms-configs) | Rutgers ROMS run with payu | 1 | 2026-09 | 1/1/0/0/1/2/0/1/1/1 | 8 |
| 15 | [joaometocean/moana_hindcast](https://github.com/joaometocean/moana_hindcast) | ROMS 3.9, original Moana config | 1 | 2022-03 | 1/2/0/0/1/0/0/0/0/1 | 5 |

Row 15 is included because it is our predecessor, not on score; four others
scored 8 (myroms/roms_test, CWorthy-ocean/cstar_blueprint_roms_marbl_example,
devmetmar/inacawo-iht, metno/metroms). Source forks (rows 4, 6, 8, 11–13)
score 2 on criterion 1 simply because they are the source.

### Practices to copy (none of these is in this repo yet)

1. **Hash the executable and restarts, refuse to run on mismatch.**
   access-om3-configs, branch `release-MC_25km_jra_iaf`: `manifests/{exe,input,restart}.yaml`,
   `config.yaml` (`manifest: reproduce:`). A restart manifest lets each chained
   segment prove which restart it started from.
2. **Restart chaining with a templated `.in`.** LO:
   `dot_in/cas7_t1_x11b/{make_dot_in.py,BLANK.in,forcing_list.csv}`,
   `driver/driver_roms00.py`. Minimal version: roms-configs `set_ininame.sh`
   (branch `dev-eac4km_barra-ecmwf`).
3. **CI with per-compiler reference answers in a container.** ucla-roms:
   `tests/results/results_github_gnu.json`, `.github/workflows/containerized_ci.yml`.
   CEFI: `.github/workflows/ci-test-mom6-tide.yaml`. Our UPWELLING check could
   run this way on every push.
4. **Keep the input-generation code and its parameters in the repo.** CEFI:
   `tools/{grid,boundary,initial,rivers,sponge,atmos}`. Our manifest has a
   `made_by` column; these repos keep the making code itself.
5. **One declarative experiment file plus citable metadata.** C-Star:
   `cstar/tests/integration_tests/blueprints/blueprint_complete.yaml`.
   access-om3-configs: `metadata.yaml`, `CITATION.cff`, release tags. We have a
   LICENSE but no tags and no CITATION file.

The ROMS `makefile` already embeds the git revision in the executable, so the
ROMS log header reports the commit; the run receipt should keep that header.

---

## 3. Fetching and tracking data

| # | Repo | Stars | Last push | Licence | Covers | Caveats |
|---|---|---|---|---|---|---|
| 1 | [mercator-ocean/copernicus-marine-toolbox](https://github.com/mercator-ocean/copernicus-marine-toolbox) | 71 | 2026-09 | EUPL-1.2 | GLORYS12 (cross-check of Datamesh), CMEMS sea level, CORA | Account needed. Reports the dataset version it selected; pin it |
| 2 | [oceanum-io/oceanum-python](https://github.com/oceanum-io/oceanum-python) | 4 | 2026-10 | MIT | GLORYS12 through Datamesh (our route) | Needs `DATAMESH_TOKEN`. Not confirmed that Datamesh exposes the upstream GLORYS version; record query, date, checksum |
| 3 | [NCAR/gdex-api-client](https://github.com/NCAR/gdex-api-client) | 45 | 2025-10 | MIT | CFSR and CFSv2 from NCAR | Replaces `rda-apps-clients`. Account and token; requests queued, outputs purged after 7 days |
| 4 | [fatiando/pooch](https://github.com/fatiando/pooch) | 740 | 2026-09 | BSD-3-Clause | Anything with a stable URL: GEBCO, OISST, CAMELS-NZ, LINZ files | Registry of URL + SHA256. Not a subsetter |
| 5 | [datalad/datalad](https://github.com/datalad/datalad) | 664 | 2026-10 | MIT | Tracking layer for all sources | Strongest provenance; needs git-annex; learning curve |
| 6 | [pyTMD/pyTMD](https://github.com/pyTMD/pyTMD) | 211 | 2026-09 | MIT | TPXO harmonics, fetch scripts | TPXO needs registration with OSU first |
| 7 | [mullenkamp/hilltop-py](https://github.com/mullenkamp/hilltop-py) | 9 | 2026-07 | Apache-2.0 | Regional-council Hilltop servers (river flows) | Small project; each council has its own URL and naming |
| 8 | [euroargodev/argopy](https://github.com/euroargodev/argopy) | 230 | 2026-10 | EUPL-1.2 | Argo profiles | Argo only, not CORA 5.2. Live source; fix a snapshot |
| 9 | [ioos/erddapy](https://github.com/ioos/erddapy) | 93 | 2026-09 | BSD-3-Clause | OISST subsets from NOAA ERDDAP | Re-served data, not byte-identical to NCEI originals |
| 10 | [ecmwf/cdsapi](https://github.com/ecmwf/cdsapi) | 321 | 2026-03 | Apache-2.0 | ERA5 (alternative to CFSR) | Account, key, queued requests |
| 11 | [treeverse/dvc](https://github.com/treeverse/dvc) | 15898 | 2026-09 | Apache-2.0 | Tracking layer for all sources | Slow on very large NetCDF. Choose this or DataLad, not both |
| 12 | [intake/intake](https://github.com/intake/intake) | 1085 | 2026-09 | BSD-2-Clause | Catalogue of downloaded datasets | Does not fetch or checksum; v2 changed the API |
| 13 | [koordinates/python-client](https://github.com/koordinates/python-client) | 4 | 2024-08 | BSD-3-Clause | LINZ Data Service layers; possibly the MfE river layers | Not pushed since 2024; per-site API key |
| 14 | [hyex-research/AquaFetch](https://github.com/hyex-research/AquaFetch) | 17 | 2026-09 | AGPL-3.0 | CAMELS-NZ | Download not tested. pooch + the CAMELS-NZ DOI is simpler |
| 15 | [oceanmodeling/searvey](https://github.com/oceanmodeling/searvey) | 31 | 2026-09 | GPL-3.0 | NZ tide gauges via IOC | Real-time data without quality control; not the LINZ archive |

**No tool found:** GEBCO download (use pooch on the official URL), TPXO
download before registration, the LINZ quality-controlled tide-gauge archive,
NIWA hydrometric data, NZ coastal temperature stations.

---

## 4. Analysing output and evaluating against observations

| # | Repo | Stars | Last commit | Licence | Evaluation tasks served | Caveats |
|---|---|---|---|---|---|---|
| 1 | [xoceanmodel/xroms](https://github.com/xoceanmodel/xroms) | 73 | 2025-08 | MIT | Backbone: ROMS output as xarray/dask with grid and s-level depths; lat/lon co-location; density-threshold MLD | Slow release cadence; needs ESMF; no section transport |
| 2 | [xgcm/xgcm](https://github.com/xgcm/xgcm) | 255 | 2026-08 | MIT | Section transports, s-level to z-level transforms, area-weighted means | Not ROMS-aware alone; xroms builds the grid |
| 3 | [powellb/seapy](https://github.com/powellb/seapy) | 33 | 2026-09 | MIT | 4D-Var observation files, background-error std, tidal fit, filters | numpy/netCDF4, not dask; written around a Hawaii setup |
| 4 | [wesleybowman/UTide](https://github.com/wesleybowman/UTide) | 168 | 2026-09 | MIT | Harmonic analysis and detiding at the 15 gauges | 1-D series only |
| 5 | [xarray-contrib/xeofs](https://github.com/xarray-contrib/xeofs) | 136 | 2025-01 | MIT | SSH EOFs | No commits since 2025-01; pass ROMS cell areas as weights. Alternative: [ajdawson/eofs](https://github.com/ajdawson/eofs) |
| 6 | [euroargodev/argopy](https://github.com/euroargodev/argopy) | 230 | 2026-10 | EUPL-1.2 | Argo side of the T/S comparison | Does not read CORA5.2; no model co-location |
| 7 | [xarray-contrib/xskillscore](https://github.com/xarray-contrib/xskillscore) | 243 | 2026-09 | Apache-2.0 | RMSE, bias, correlation maps and profiles | No Willmott skill; supply area weights |
| 8 | [TEOS-10/GSW-Python](https://github.com/TEOS-10/GSW-Python) | 180 | 2026-09 | BSD-style | Density for MLD, pressure-to-depth | ROMS uses its own equation of state |
| 9 | [pangeo-data/xESMF](https://github.com/pangeo-data/xESMF) | 252 | 2026-09 | MIT | Model SST/SSH onto OISST and altimetry grids | Needs ESMF (conda) |
| 10 | [metno/pyromsobs](https://github.com/metno/pyromsobs) | 2 | 2026-05 | MIT | Building and editing 4D-Var observation files | Tiny user base; overlaps with seapy |
| 11 | [bjornaa/roppy](https://github.com/bjornaa/roppy) | 6 | 2023-09 | MIT | Flux-exact section transport (`fluxsec.FluxSection`) | numpy; no commits since 2023. Port the algorithm |
| 12 | [parkermac/LO](https://github.com/parkermac/LO) | 15 | 2026-09 | MIT | Section transport, mooring/cast extraction, low-pass filters | Workflow repo, not a package |
| 13 | [noaa-ocs-modeling/OCSTrack](https://github.com/noaa-ocs-modeling/OCSTrack) | 5 | 2026-08 | CC0-1.0 | Co-location of altimetry tracks and Argo with model output (has a ROMS class) | Expects its own run-directory layout; young |
| 14 | [garrettdreyfus/python-holteandtalley](https://github.com/garrettdreyfus/python-holteandtalley) | 26 | 2019-05 | MIT | Holte & Talley MLD | Unmaintained; one profile at a time |
| 15 | [myroms/roms_matlab](https://github.com/myroms/roms_matlab) | 25 | 2026-09 | MIT/X style | Reference 4D-Var scripts: observations, background-error std, balance operator | MATLAB |

**Write ourselves:** Willmott skill; co-location with CORA5.2; section
transport in xarray/dask; 40-day low-pass over the full SSH stack;
temperature-threshold MLD. For 4D-Var, the balance-operator scripts exist only
in MATLAB.

---

## 5. Workflow and reproducibility infrastructure

| # | Repo | Stars | Last push | Licence | What it would replace or add | Adoption cost |
|---|---|---|---|---|---|---|
| 1 | [snakemake/snakemake](https://github.com/snakemake/snakemake) | 2880 | 2026-09 | MIT | Input-file generation as a rerunnable DAG on SLURM | Medium |
| 2 | [pre-commit/pre-commit](https://github.com/pre-commit/pre-commit) | 15605 | 2026-09 | MIT | Runs the manifest check and linters on every commit; blocks NetCDF commits | Low |
| 3 | [myroms/roms_test](https://github.com/myroms/roms_test) | 11 | 2026-09 | MIT | More regression cases; WC13 4D-Var case as a rehearsal for DA | Low |
| 4 | [ACCESS-NRI/model-config-tests](https://github.com/ACCESS-NRI/model-config-tests) | 1 | 2026-09 | Apache-2.0 | Restart-reproducibility test design (two short runs equal one long run) | Medium: port the design, not the package |
| 5 | [cylc/cylc-flow](https://github.com/cylc/cylc-flow) | 383 | 2026-10 | GPL-3.0 | Cycling workflow for restart chains and DA | Medium-high; adopt when DA starts |
| 6 | [datalad/datalad](https://github.com/datalad/datalad) | 664 | 2026-10 | MIT | Would replace the TSV manifest, checker and part of the receipt | Medium-high |
| 7 | [fatiando/pooch](https://github.com/fatiando/pooch) | 740 | 2026-09 | BSD-3-Clause | Fetch-and-verify for URL-based inputs and test reference data | Low |
| 8 | [nco/nco](https://github.com/nco/nco) | 196 | 2026-10 | BSD-3-Clause | Field-by-field regression diffs; output compression | Low |
| 9 | [citation-file-format/citation-file-format](https://github.com/citation-file-format/citation-file-format) | 560 | 2026-09 | CC-BY-4.0 | `CITATION.cff` plus Zenodo DOI per release | Low |
| 10 | [payu-org/payu](https://github.com/payu-org/payu) | 24 | 2026-09 | Apache-2.0 | Closest existing tool to our submit script, receipt and manifest; has a ROMS driver | High: SLURM backend is a stub. Borrow the design |
| 11 | [ioos/compliance-checker](https://github.com/ioos/compliance-checker) | 133 | 2026-10 | Apache-2.0 | CF/ACDD checks before publishing output | Low |
| 12 | [spack/spack](https://github.com/spack/spack) | 5131 | 2026-10 | Apache-2.0 OR MIT | Lockfile for compiler, MPI, HDF5, NetCDF instead of module loads | High; only if cluster modules are unstable |
| 13 | [parkermac/LO](https://github.com/parkermac/LO) | 15 | 2026-09 | MIT | Template for forcing drivers and day-by-day run chaining | Low to borrow from |
| 14 | [zarr-developers/VirtualiZarr](https://github.com/zarr-developers/VirtualiZarr) | 304 | 2026-09 | Apache-2.0 | Opens 28 years of NetCDF output as one dataset without copying | Medium |
| 15 | [apptainer/apptainer](https://github.com/apptainer/apptainer) | 1977 | 2026-10 | BSD-3-Clause | Freezes the Python environment as one image | Low for Python; high for ROMS with Intel MPI |

**Ruled out:** C-Star (UCLA-ROMS only), ecFlow and Autosubmit (duplicate Cylc
with more overhead), ESMValTool, Nextflow, pixi and conda-lock (we already
have a locked environment).

---

## 6. Shortlist

| Need | Use | Why |
|---|---|---|
| Grid | `joaometocean/moana_hindcast` | The published grid file; no need to regenerate |
| Initial and boundary files | `trondkr/model2roms` | Maintained, reads GLORYS12 |
| Rivers, tide file | `powellb/seapy` with `pyTMD/pyTMD` | Rutgers-ROMS file writers; TPXO extraction |
| Nudging file | `myroms/roms_matlab` | Official reference to port |
| GLORYS cross-check | `mercator-ocean/copernicus-marine-toolbox` | Reports the dataset version |
| CFSR download | `NCAR/gdex-api-client` | Request is a file we can commit |
| Static downloads | `fatiando/pooch` | URL + hash registry |
| Analysis | `xoceanmodel/xroms`, `xgcm/xgcm`, `wesleybowman/UTide` | Handle the ROMS grid; tides at gauges |
| Repo hygiene | `pre-commit/pre-commit`, `CITATION.cff` | Low cost |
| Tests | `myroms/roms_test`, design from `ACCESS-NRI/model-config-tests` | More cases; restart reproducibility |
| Templates | `ACCESS-NRI/access-om3-configs`, `NOAA-GFDL/CEFI-regional-MOM6`, `parkermac/LO` | Manifests, CI, restart chaining |

**Open choices:** data versioning (keep `inputs.tsv`, or move to DataLad or
DVC; the two searches that looked at this disagreed on DVC); a workflow engine
for the restart chain (SLURM job dependencies are enough until DA cycling,
then Cylc).

**To write ourselves:** CFSR/CFSv2 to ROMS bulk forcing; CORA5.2 co-location;
section transports in xarray; Willmott skill.
