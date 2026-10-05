# Data sources

**Last updated:** 2026-10-05

Every dataset the forward model and its evaluation use. A file only counts as
"in use" once it has a line in `Apps/moana/inputs.tsv` (sha256, path, source,
version, script). See [REPRODUCIBILITY.md](../../REPRODUCIBILITY.md).

## Configuration and benchmark

| Dataset | Provider | Variables | Resolution | Period | DataMesh ID / access | Used for | Licence |
|---|---|---|---|---|---|---|---|
| Published Moana configuration v1.0 | Souza (2022), Zenodo [10.5281/zenodo.6484908](https://doi.org/10.5281/zenodo.6484908) | Grid, `roms.in`, `roms3d.h`, `roms_config.sh` | 5 km | — | `scripts/fetch_published_config.sh` | Grid (in `inputs.tsv`), reference config | None stated in the archive, so the files are fetched rather than committed |
| Published Moana hindcast v2 output | Zenodo [10.5281/zenodo.5895265](https://doi.org/10.5281/zenodo.5895265) / THREDDS | ❓ UNKNOWN | 5 km, 50 levels | 1993–2020 | ❓ UNKNOWN | Statistics benchmark (P1-M9); possibly initial conditions (yet to decide) ([ADR-0006](../decisions/0006-published-hindcast-as-benchmark.md)) | ❓ UNKNOWN |

## Model inputs

| Dataset | Provider | Variables | Resolution | Period | DataMesh ID / access | Used for | Licence |
|---|---|---|---|---|---|---|---|
| GLORYS12v1 reanalysis | Mercator / CMEMS, via Oceanum DataMesh | T, S, u, v, ζ | 1/12°, daily | 1993– | ❓ UNKNOWN: datasource ID (P1-M3-T01) | Initial, boundary, climatology, nudging | ❓ UNKNOWN |
| Mercator operational analysis / nowcast | Mercator / CMEMS, via Oceanum DataMesh | T, S, u, v, ζ | ❓ | Continues GLORYS | ❓ UNKNOWN: datasource ID | Boundary after GLORYS ends | ❓ UNKNOWN |
| TPXO 7.8.1 (or newer) | OSU | Tidal elevation and currents, 11 constituents | ❓ | — | Licence request | Tide file (P1-M4-T01) | Licence needed |
| CFSR (1979–2010) and CFSv2 (2011–) | NCEP, via NCAR RDA | 10 m wind, 2 m air T, humidity, rain, SW down, LW down, MSLP | ❓ | Run period (yet to decide) | NCAR RDA account | Surface forcing (P1-M5) | ❓ UNKNOWN |

The paper only says "CFSR", so how the authors joined CFSR and CFSv2 is
unknown ([risk R6](../risks.md)). Each DataMesh query must be recorded
(datasource ID, variables, geofilter, timefilter, `oceanum` version, fetch
date), because a DataMesh datasource can change in place
([ADR-0001](../decisions/0001-datamesh-for-forcing-and-boundaries.md)). The
token goes in the `DATAMESH_TOKEN` environment variable, never in git.

## Rivers

The paper's 42 rivers are "climatological values obtained from the
data.govt.nz portal" (§2.1). It names no dataset or river list. The published
`roms.in` reads `nz5km_N50_rivers.nc`, which is not in the archive
([risk R2](../risks.md)).

| Dataset | Provider | Variables | Resolution | Period | Access | Used for | Licence |
|---|---|---|---|---|---|---|---|
| [Natural river flow statistics, all river reaches](https://data.mfe.govt.nz/table/52536-natural-river-flow-statistics-predicted-for-all-river-reaches/) | Ministry for the Environment (on [data.govt.nz](https://catalogue.data.govt.nz/dataset/natural-river-flow-statistics-predicted-for-all-river-reaches)) | Mean flow statistics per reach | Reach | Climatology | Manual browser download; record the date | Rebuild the 42 rivers (fallback) | ❓ UNKNOWN |
| [River flows](https://data.mfe.govt.nz/layer/53309-river-flows/) | MfE | Flows | ❓ | ❓ | Manual download | Cross-check ranking | ❓ UNKNOWN |
| [NZ River Maps](https://shiny.niwa.co.nz/nzrivermaps/) | NIWA | Flows | Reach | ❓ | Web app | Cross-check ranking | ❓ UNKNOWN |
| [CAMELS-NZ](https://doi.org/10.26021/canterburynz.28827644) ([ESSD 17, 5745, 2025](https://essd.copernicus.org/articles/17/5745/2025/)) | University of Canterbury | Hourly streamflow, 369 catchments | Gauge | 1972–2024 | Download | Time-varying flows (P1-M6-T02) | CC-BY 4.0 (14 stations need permission) |
| [NIWA hydrometric data](https://data.niwa.co.nz/products/hydro-data) | NIWA | Daily observed flow | Gauge | ❓ | DataHub login + API key | Time-varying flows | ❓ UNKNOWN |
| NIWA TopNet / NZ Water Model | NIWA | Modelled hourly flow | Every reach | 1972– | On request only | Time-varying flows | ❓ UNKNOWN |

## Observations

Needed for 4D-Var (P2-M1-T01). Using them to check the Phase 1 forward model
as well is (yet to decide) ([ADR-0006](../decisions/0006-published-hindcast-as-benchmark.md)).

| Dataset | Provider | Variables | Resolution | Period | Access | Used for | Licence |
|---|---|---|---|---|---|---|---|
| CMEMS MSS and SLA (L4) | Copernicus Marine | Sea surface height | ❓ | ❓ | Copernicus Marine account | P2-M1-T01 | ❓ |
| NOAA OISST v2.1 | NOAA NCEI | SST | Daily | ❓ | [NCEI](https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/v2.1/) | P2-M1-T01 | ❓ |
| CORA5.2 | Copernicus Marine | T/S profiles | Profiles | ❓ | Copernicus Marine account | P2-M1-T01 | ❓ |
| LINZ tide gauges (15, paper Table 2) | LINZ | Sea level | Hourly | 2015–2017 used | ❓ | (yet to decide) | ❓ |
| Coastal temperature stations (10, paper Table 3) | Zenodo [10.5281/zenodo.6399921](https://doi.org/10.5281/zenodo.6399921) | Temperature | ❓ | ❓ | Download | (yet to decide) | ❓ |

## Not used

| Dataset | Why not |
|---|---|
| GEBCO, LINZ charts, NIWA bathymetry | Bathymetry comes with the published grid ([ADR-0002](../decisions/0002-start-from-published-moana-config.md)) |
