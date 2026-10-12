# Data

**Last updated:** 2026-10-09

All model input data comes from Oceanum DataMesh ([decision D1](decisions.md#d1-use-datamesh-data-only)).
This page shows the data that we can read now, the data that we need, and our requests to Oceanum.

## How we checked

- Date: 2026-10-09. Tool: `oceanum` 1.2.1. Token: `$DATAMESH_TOKEN` (never put it in git).
- Script: `scripts/check_datamesh.py`. Run it again when the access changes.
- The token lists 41 datasources.
- "OK" means that a read of a 1° × 1° box west of New Zealand (2024-01-15) gave real values.
- "403" means that the datasource exists, but the token cannot read it. "404" means that no datasource has this ID.

## What the model needs

`Apps/moana/Include/moana.h` sets `BULK_FLUXES`, `LONGWAVE_OUT`, `SOLAR_SOURCE`, `EMINUSP`, `ATM_PRESS`, `SSH_TIDES` and `UV_TIDES`.
Thus the model needs these inputs:

| Input | Fields |
|---|---|
| Ocean (initial and boundary) | Temperature, salinity, u, v, sea level (ζ) |
| Atmosphere | `Uwind`, `Vwind`, `Tair`, `Qair`, `Pair`, `rain`, `swrad`, `lwrad_down` |
| Tides | Elevation and current constituents |

The model grid (`Apps/moana/Input/moana_grid.nc`) is 397 × 467 points, 161.03–184.97° E, 51.98–31.03° S.

## Ocean

CMEMS GLOBAL_ANALYSISFORECAST_PHY_001_024 (Mercator GLO12). Grid: 1/12°. Levels: 50, from 0.494 m to 5728 m.

| Fields | DataMesh ID | Time (real) | Step | Status |
|---|---|---|---|---|
| Temperature, 3D | `cmems_mod_glo_phy-thetao_anfc_0-083deg_pt6h-i` | 2022-06-01 → 2026-10-19 | 6 h, instantaneous | OK |
| Salinity, 3D | `cmems_mod_glo_phy-so_anfc_0-083deg_pt6h-i` | 2022-06-01 → 2026-10-19 | 6 h, instantaneous | OK |
| u, v, 3D | `cmems_mod_glo_phy-cur_anfc_0-083deg_pt6h-i` | 2022-06-01 → 2026-10-19 | 6 h, instantaneous | OK |
| ζ, and surface T, S, u, v | `cmems_mod_glo_phy_anfc_0-083deg_pt1h-m` | 2022-06-01 → 2026-10-18 | 1 h, mean | OK |
| Daily means (`..._anfc_..._p1d-m`, 4 IDs) | — | — | — | 403 |
| `-timeseries` copies of the 6 h sets | — | — | — | 403 |
| GLORYS12v1 reanalysis (`cmems_mod_glo_phy_my_0-083deg_p1d-m`, `_p1m-m`) | — | — | — | 403 |
| GLORYS12v1 interim (`..._myint_...`) | — | — | — | 404 |

Notes:

- The time series have no gaps.
- The time axis goes to about 10 days after the check date. Values after the check date are forecast.
- Past values can change (request 7).
- Longitudes are −180 to 179.92. The model domain crosses 180°. Use two boxes for each query.
- The 3D sets are too large to open with `load_datasource`. Use `query` with a box and a time range.

## Atmosphere

ERA5. Grid: 0.25°. Step: 1 h. Longitudes are 0 to 359.75, so one box covers the domain.

| ROMS field | DataMesh ID | ERA5 variable | Time (real) | Status |
|---|---|---|---|---|
| `Uwind`, `Vwind` | `era5_wind10m` | `u10`, `v10` | 1940-01-01 → 2026-08-01 | OK |
| `Pair` | `era5_mslp` | `msl` | 1979-01-01 → 2026-08-01 | OK |
| `Tair` | `era5_temp2m` | `t2m` | 1979-01-01 → **2025-05-01** | OK. The catalogue says 2026-08-01. |
| `rain` | `era5_precip_rate` | `mtpr` | 1979-01-01 → **2025-05-01** | OK. The catalogue says 2026-08-01. |
| `swrad` | `era5_mean_surface_downward_short_wave_radiation_flux` | `msdwswrf` | **2010-01-01 → 2020-01-01** | No data after 2020. |
| `Qair` | — | `d2m` or `q` | — | **Missing.** 404 for all IDs that we tried. |
| `lwrad_down` | — | `msdwlwrf` | — | **Missing.** 404 for all IDs that we tried. |

Notes:

- Now, no period has all eight fields.
- `ecmwf_ifs_0p25_oper_sfc` has all the fields. But it keeps only the latest forecast (6 days). We cannot use it for a past period.

## Tides

| DataMesh ID | Grid | Constituents | Covers the model boundaries? |
|---|---|---|---|
| `tpxo9_atlas_v5_cons` | 1/30° | 15 | Yes (longitudes 0–360) |
| `tpxo9_v5a_cons` | 1/6° | 22 | Yes (longitudes 0–360) |
| `oceanum_tide_cons_nz_2km` | 0.02° | 14 | No (165–180° E, 49.2–32.7° S). Use it only to check results. |

## Grid and bathymetry

| DataMesh ID | Content |
|---|---|
| `gebco_2026` | GEBCO 2026 bathymetry, 15″ |

## Rivers

DataMesh has no river data (roadmap M7-T1).

## Observations

These can help to check the results (roadmap M10). "Real" times come from the data. "Catalogue" times come from the catalogue only.

| DataMesh ID | Content | Time |
|---|---|---|
| `metoffice-glo-sst-l4-nrt-obs-sst-v2` | OSTIA L4 SST, 0.05°, daily | 2007-01-01 → 2026-10-08 (real) |
| `esacci-glo-sst-l4-rep-obs-sst` | ESA CCI L4 SST v3.0, daily | 1980-01-01 → 2021-12-31 (real) |
| `noaa-acspo-l3s-leo-*` (8 IDs) | NOAA ACSPO L3S SST, 0.02° | 2002 or 2006 → no end date; NRT sets from 2025-10-06 (catalogue) |
| `argo_floats` | Argo profiles | 1997-07-28 → no end date (catalogue) |
| `fvon_profile_fv_nrt` | Fishing vessel profiles | 2021-07-01 → no end date (catalogue) |
| `moana-project-sensors` | Mangopare sensors, New Zealand | 2023-10-11 → no end date (catalogue) |

DataMesh has no altimetry and no tide gauge data.

## Requests to Oceanum

Status: Not sent · Sent · Granted · Refused · Answered.

| No. | Request | Why | Status |
|---|---|---|---|
| 1 | ERA5 2 m dewpoint (`d2m`) or 2 m specific humidity. Hourly, 2022-06-01 → now. | `Qair` | Not sent |
| 2 | ERA5 mean surface downward long-wave flux. Hourly, 2022-06-01 → now. | `lwrad_down` | Not sent |
| 3 | ERA5 short-wave flux after 2020-01-01 (downward or net). Hourly. | `swrad` | Not sent |
| 4 | ERA5 2 m temperature and precipitation rate after 2025-05-01. Or correct the catalogue end date. | `Tair`, `rain` | Not sent |
| 5 | Keep our access to the four ocean sets above. | The `-timeseries` copies give 403 now. The access must not change during the project. | Not sent |
| 6 | Question: does the hourly `zos` include tides? | We add TPXO tides at the boundary. Tides must not be added two times. | Not sent |
| 7 | Question: which Mercator system versions cover 2022-06 → now? Do past values change? | A model run must be reproducible. | Not sent |
| 8 | Question: which licence terms apply to model input files that we make from these data? | We must know if we can share these files. | Not sent |
| 9 | Optional: river flow data for New Zealand. | Rivers (M7-T1) | Not sent |
| 10 | Optional: GLORYS12v1 daily (now 403). | Only if we need a period before 2022-06-01. | Not sent |
