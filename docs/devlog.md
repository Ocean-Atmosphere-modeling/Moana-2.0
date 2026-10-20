# Development log

Newest entry first.

## 2026-10-20

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
