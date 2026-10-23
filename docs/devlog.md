# Development log

Newest entry first.

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
