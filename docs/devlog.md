# Development log

Newest entry first.

## 2026-10-23

### Initial condition: vertical interpolation check

- Problem: the same question as for the boundary file. Do features with
  the shape of the bathymetry come from CMEMS, from the vertical
  interpolation, or from the plot?
- Handling: in `scripts/make_ic.py`, new functions `horizontal()` and
  `vertical()`. The variable is now the first argument (default salt). The
  raw file is chosen from the variable (u and v use `ic_uo_vo_raw`). The
  script also writes `ic_zlevels_<var>_2026-01-01.nc`: the field after the
  horizontal step only. Job 62929211 made temp, salt, u and v again. All 4
  files are identical to the old files (max |diff| = 0).
- New `scripts/plot_ic_vertical_check.py` makes sections (middle row and
  middle column) and profiles in `concept_figures/ic_vertical_check/`. In
  `misc_scripts/plot_ic.py` and `misc_scripts/plot_ic_vorticity.py`, the
  section panel uses gouraud shading now.
- Result: no NaN at ocean points. At s-levels within 1 m of a CMEMS level,
  max |ROMS − CMEMS| is 0.50 °C, 0.38 psu, 0.05 m/s (u) and 0.09 m/s (v),
  at coastal points with h = 11 to 16 m. This is the CMEMS gradient times
  the distance. The bands that follow the bathymetry come from "nearest"
  shading.
- In 10.5 % of the ocean columns, ROMS is deeper than the CMEMS seafloor
  (median 295 m deeper). The bottom s-levels there get values from the
  same-depth fill in `make_ic.py`, not from CMEMS data at that point.
  Example: 5.7 °C at 1000 m near 167.6°E 32.4°S, where CMEMS has water only
  to 40 m. These values are also in the CMEMS sections.

### Boundary sections: features with the shape of the bathymetry

- Problem: the boundary sections showed bands that follow the bathymetry.
  The source was not known: CMEMS, the vertical interpolation, or the plot.
- Handling: in `scripts/make_bry.py`, `to_line()` calls two new functions,
  `horizontal()` and `vertical()`. New settings START and CHECK_TIME. The
  script also writes `bry_zlevels_<CHECK_TIME>.nc`: the boundary lines after
  the horizontal step only, on the CMEMS levels. The interpolation did not
  change. Job 62928670 made a boundary file that is identical to the old
  file (max |diff| = 0 for all variables).
- New `scripts/plot_bry_vertical_check.py` makes sections (CMEMS levels
  and s-levels) and profiles at 4 points per side in
  `concept_figures/bry_vertical_check/`. The s-level panels use gouraud
  shading. In `misc_scripts/plot_bry.py`, the s-level panel uses gouraud
  shading now.
- Only uo and vo for south and north are on disk, so the check uses u and
  v. temp and salt are (yet to decide) (data not downloaded).
- Result (2026-01-01T00): no NaN at ocean points. At s-levels within 1 m
  of a CMEMS level, max |ROMS − CMEMS| is 0.010 to 0.040 m/s. This is the
  CMEMS gradient times the distance. The bands on the slopes come from
  "nearest" shading. With gouraud shading, they are not there. The flow
  along the slopes is also in the CMEMS sections.

### TIME_REF in moana.in

- Problem: `Apps/moana/Runs/moana.in` had TIME_REF = 20100101.
- Handling: TIME_REF is 20260101.0d0 now. DSTART (199302) is not changed.
  It is days since TIME_REF, so it must agree with the new TIME_REF.
  `make_tides.py` (REF_DATE) and `make_bry.yaml` (TIME_REF) still use
  2010-01-01. `make_ic.py` uses 2026-01-01.

### make_bry.py test (make_ic.py style)

- Problem: the new `scripts/make_bry.py` did not run. The grid file
  `nz_grid_N50.nc` does not exist. Only `uo` and `vo` for south and north
  are downloaded.
- Handling: GRID is `moana_grid_N50.nc`. SIDES is south and north. The
  script skips variables that are not in the raw files and prints them.
- Test: 369 times (6-hourly, 2025-12-31 to 2026-04-02). Run time is 5.5 min,
  memory is 5 GB. u agrees with a scipy interpolation to 1e-16 at wet
  points. ubar agrees with the Hz-weighted mean of u. No NaN.
- `make_bry.yaml` is for the old version of the script. The new script does
  not read it.
- 2-day test: new setting TIMES (2026-01-01 00:00 to 2026-01-03 00:00, 9
  records). Output is in `boundary_cond/roms-ready/` (new directory).
  `misc_scripts/plot_bry.py` makes `concept_figures/bry_<side>.png`: a u and
  v section at the first record, and ubar and vbar for all records.
- Full run: `scripts/make_bry.slurm` (job 62908208, halk0105, 1 CPU). TIMES
  is all 369 records. make_bry.py now prints the read time and the fill +
  interpolation time for each side. South: read 38.4 s, fill +
  interpolation 88.0 s. North: read 34.9 s, fill + interpolation 80.6 s.
  Total wall time 5 min 35 s, peak memory 2.6 GB. The 2-day file is
  replaced.

### make_tides.py (tide file in Python)

- Problem: the tide file code (Code-Commons `examples/tides`) is MATLAB. It
  needs the OTPS program `extract_HC`, t_tide and other MATLAB toolboxes.
- Handling: new `scripts/make_tides.py` (about 90 lines). It reads the
  DataMesh TPXO9-atlas-v5 cut `Input/tides/tpxo9_atlas_v5_moana.nc` with
  xarray. TPXO land cells get the nearest TPXO water cell, then bilinear
  interpolation to the rho points. pyTMD gives the nodal corrections and the
  current ellipses. Phase is zero at REF_DATE (V from REF_DATE, f and u from
  NODAL_DATE), as in `otps2frc_v7.m`. Output variables and units are the
  same as the MATLAB file.
- Differences from the MATLAB: all ROMS water points get a value (MATLAB
  fills only the edge rows and uses the mean of the phases, which is wrong
  near 0/360°). Currents are TPXO transport / ROMS h (MATLAB: TPXO
  velocity). All 15 TPXO constituents (MATLAB: 12).
- Test 1: a test grid in the Ross Sea with CATS2008 (pyTMD test data). The
  ROMS sum (set_tides.F) of the file agrees with a direct pyTMD sum to 1e-13
  for zeta, u and v when the nodal values are fixed. With nodal values that
  change in time, the difference after 30 days is 1 to 3 mm.
- Test 2: Moana grid `grd_moana5km.nc` (the same lon, lat, mask and h as
  `moana_grid_N50.nc`). The Oceanum Re/Im sign is the same as in the OSU
  TPXO files (M2 agrees to 1e-8 m). The file agrees with the raw TPXO at
  deep points to 5e-16 m.
- Problem: TPXO velocity is TPXO transport / TPXO depth. On the shelf south
  of Stewart Island the TPXO depth is 7 to 16 m, but ROMS h is 130 to
  160 m. There, the raw TPXO M2 speed is up to 12.5 m/s, and 50 ROMS cells
  had Cmax > 2 m/s.
- Handling: currents are TPXO transport / ROMS h. Then the tidal transport
  into ROMS is the same as in TPXO. Max Cmax is now 1.32 m/s (Cook Strait,
  h = 29 m). No cell has Cmax > 2 m/s. On the open edges, TPXO depth / ROMS
  h is 0.69 to 2.04, and Cmax is 0.26 m/s or less.
- Output: `Input/tides/moana_tides.nc`. 15 constituents, REF_DATE
  2010-01-01 (TIME_REF = 20100101 and TIDE_START = 0 in
  `Apps/moana/Runs/moana.in`), NODAL_DATE 2026-02-15 (middle of the
  boundary data on disk). Run time 15 s, memory 1 GB, no NaN. Eamp is up to
  1.24 m (M2, Taranaki Bight). A ROMS sum 16 years after REF_DATE agrees
  with a direct sum to 1e-10 m.
- `misc_scripts/plot_tide_file.py` makes `concept_figures/tide_file.png`:
  M2 and K1 amplitude and phase, and M2 Cmax.
- If TIME_REF or TIDE_START changes, set REF_DATE again. If the run period
  changes (M9-T1), set NODAL_DATE to its middle. In 2026, f is 1.18 for O1
  and 1.30 for K2.
- Choice "currents = TPXO transport / ROMS h" is Proposed. It is not in
  `docs/decisions.md`, because that file is deleted (commit 83d0b32).

### download_bry.py review

- Problem: the docstring of `scripts/download_bry.py` said "daily means",
  but the source is 6-hourly. It said that all output longitudes are 160 to
  186, but the east file has −176 to −174. The checks used `assert`, which
  `python -O` removes. The checks did not find missing records or a strip
  that has only NaN. The config path was a fixed path in `/scratch`.
- Handling: the docstring is correct now. `check_coverage` raises
  `ValueError`. It also checks that the time step is regular and that each
  variable has data. The config is the first argument, default
  `download_bry.yaml` at the repo root. The `--list` feature is removed.
- Test: the boxes did not change. The south and north files (2026-01-01 to
  2026-03-31) pass the new checks.
- New `misc_scripts/plot_bry_strips.py` makes
  `concept_figures/bry_strip_<side>.png`. Each figure shows the requested box,
  the split at 180°, the downloaded surface speed, and a zoom on the rho-, u-
  and v-points of the edge.
- One run gets one DATASOURCE. The boundary file also needs thetao, so and
  zos. Each needs its own run.
- New `scripts/download_bry.slurm` runs `download_bry.py` as a SLURM job
  (p_omg_1, 16 GB, 6 h). In `download_bry.yaml`, SIDES is now [west, east], because
  south and north are already on disk. Job 62908396 downloads west and east
  for 2026-01-01 to 2026-03-31.
- Job 62908396 failed on the west side after 2 h. DataMesh did not send a
  reply in 900 s, 8 times (`DatameshConnectError`, read timeout). No file
  was written. SLURM showed COMPLETED, because the last line of the job
  script was `echo`. The script now exits with the python exit status.
  Fix for the timeout is (yet to decide).

### Figures of the ROMS-ready initial condition

- Problem: there were no figures to check the ROMS-ready IC files
  (`initial_cond/roms_ready/ic_<var>_2026-01-01.nc`).
- Handling: new `misc_scripts/plot_ic.py` makes
  `concept_figures/ic_<var>_2026-01-01.png` for temp, salt, u and v. Each
  figure shows the top s-level, the bottom s-level and a west-east section
  at 42.4°S. The IC files have no coordinates, so lon, lat, h and mask come
  from `moana_grid_N50.nc`.
- Result: no NaN at ocean points. temp 0.52 to 24.24 °C, salt 32.55 to
  35.80 PSU, u −0.53 to 0.94 m/s, v −0.82 to 0.78 m/s.
- There is no zeta IC file in `roms_ready/`.
- New `misc_scripts/plot_ic_vorticity.py` makes
  `concept_figures/ic_vorticity_2026-01-01.png`: ζ/f from
  `xroms.relative_vorticity` (xroms 0.6.2) on psi-points and w-levels. The
  top and bottom w-levels are 0 (xroms has no derivative there), thus the
  maps use the first w-level inside the water. ζ/f is −1.92 to 1.17.

## 2026-10-21

### pyroms install

- Problem: `pip install -e pyroms/...` failed. The pyroms `setup.py` files
  use `numpy.distutils`. `moana_python` has Python 3.12 and numpy 2, which do
  not have `numpy.distutils`. `copernicusmarine` (>= 2.4) needs numpy >= 2.1,
  thus pyroms cannot go in `moana_python`.
- Handling: new conda env `moana_pyroms` (Python 3.11, numpy 1.26,
  setuptools < 60), in `env/moana_pyroms.yml` and `env/moana_pyroms.lock.txt`.
  New `scripts/install_pyroms.sh` clones ESMG/pyroms at commit 1370d22 (if
  `pyroms/` is not there) and installs pyroms, pyroms_toolbox,
  bathy_smoother and SCRIP. `pyroms/` is in `.gitignore`.
- SCRIP: f2py read `pyscrip.f90` as free-form, but it is fixed-form. The
  import then failed with "undefined symbol: unknown_subroutine_". The
  script builds SCRIP in a temporary copy with a `! -*- fix -*-` first line.
  The pyroms clone does not change.
- `env/moana_python.yml` does not list `oceanum`, `cfgrib`,
  `python-eccodes`, `pytmd` and `copernicusmarine`, but the env has them.
  Fix is (yet to decide).

## 2026-10-20

### ECMWF IFS forcing on DataMesh: which period is available

- Problem: the entry below says that DataMesh has no ECMWF archive for 2025.
  This is not correct. DataMesh shows "2024 to live" for
  `ecmwf_ifs_0p25_oper_sfc`, but the time dimension has only 85 steps.
- Cause: each query gets one forecast cycle. With no `cycle` parameter, you
  get the latest cycle. The "2024 to live" range is the range of cycles, not
  one time series. One 00 or 12 UTC cycle has 85 steps: 49 steps at 3 h
  (+0 to +144 h) and 36 steps at 6 h (+150 to +360 h).
- Handling: to get an earlier cycle, add
  `parameters={"cycle": "YYYYMMDDHH"}` to `dm.query`.
- Available cycles:

  | Datasource | Cycles | Model |
  |---|---|---|
  | `ecmwf_ifs_0p25_oper_sfc_2024` | 00 and 12 UTC, 2024-03-18 12 UTC to 2024-11-12 00 UTC | IFS 48r1, to +240 h |
  | `ecmwf_ifs_0p25_oper_sfc` | 2024-11-12 12 UTC to now. 06 and 18 UTC cycles (to +144 h) start 2026-05-12. | IFS 49r1 and later, to +360 h |
  | `ecmwf_wind10m_0p25_nowcast` | One continuous series, 3-hourly, 2025-10-21 12 UTC to now | u10 and v10 only |

  The single-field sets (`ecmwf_msl_0p25`, `ecmwf_t2m_0p25`, `ecmwf_tp_0p25`,
  `ecmwf_wind10m_0p25`, `ecmwf_tprate_0p25`) have only the latest forecast.
- Test: 7 cycles from 2024-03-18 to 2026-06-01, on one point near
  Wellington. Each cycle had all 8 ROMS forcing fields: u10, v10, msl, t2m,
  d2m, tp, ssrd, strd. The fluxes (tp, ssrd, strd) are NaN at step 0. A
  cycle before the first cycle of a datasource gives an error. The nowcast
  has no gap. The other cycles are not examined, so gaps are possible.
- Grid: 0.25°. Longitude is 0 to 360, thus there is no cut at 180E.
- Result for the run period (M9-T1): with ECMWF forcing, the run cannot
  start before 2024-03-18. A run across 2024-11-12 uses two IFS versions.
- Next steps: (yet to decide)
  - Make one time series: join the +0 to +12 h steps of each 00 and 12 UTC
    cycle. This is approximately 730 queries for each year (25 to 70 s for
    each query).
  - The datasource text says: for many cycles, ask the Oceanum data team
    for a bulk extraction.
  - Do a scan of all cycles for gaps.

- Problem: no script made the ROMS boundary file from the raw DataMesh files.
- Handling: new `scripts/make_bry.py` with config `make_bry.yaml`. It reads
  only a strip around each open edge, fills land cells with the nearest wet
  cell, and interpolates bilinearly in longitude and latitude and linearly
  in depth (zeta = 0). It rotates uo and vo to the grid. ubar and vbar are
  the depth means of u and v on the ROMS levels. Longitude is 0 to 360, so
  tiles on the two sides of 180E join. The script stops if the source does
  not cover an edge point.
- Test: 2025-01-01 data, the west files plus a new east tile (−180 to
  −174.5). The values agree with `xarray.interp` to 1e-6 °C. Cs_r agrees
  with the grid file. Run time is 19 s.
- DataMesh has no daily-mean CMEMS physics data. Thus T, S, u and v are
  6-hourly and zos is hourly; each field has its own time variable. The
  hourly zos has no tides (24 h range 1 to 2 cm), so it agrees with
  ADD_FSOBC.

- Problem: `scripts/download_input.py` asks for longitude 160.5 to 185.5.
  CMEMS longitude is −180 to 180, so the files stop at 179.92. 22.5 % of the
  Moana ocean points and the full east boundary have no data.
- Handling: `misc_scripts/plot_lon_convention.py` makes
  `concept_figures/lon_convention.png`, which shows the problem. The fix to the
  script is (yet to decide).
- `ecmwf_ifs_0p25_oper_sfc` uses longitude 0 to 360, so it has no cut at 180.
  But a month-by-month scan of the ECMWF sets on DataMesh found only one
  forecast in each set: the latest one (from 2026-10-20), or 2024-11-12 to
  2024-11-22 in `ecmwf_ifs_0p25_oper_sfc_2024`. There is no ECMWF archive for
  2025 or 2026-01-01. `era5_mslp` has data for 2026-01-01.
