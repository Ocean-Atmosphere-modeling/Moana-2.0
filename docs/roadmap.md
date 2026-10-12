# Roadmap

**Last updated:** 2026-10-09

This roadmap is for the forward model only ([decision D2](decisions.md#d2-forward-model-only)).
All input data comes from Oceanum DataMesh ([decision D1](decisions.md#d1-use-datamesh-data-only)).

Rules:

- Task IDs are `M<milestone>-T<task>`.
- Status: 🔲 not started · 🔄 in progress · ⛔ blocked · ✅ done · 🗑️ dropped.
- "(yet to decide)" shows a choice that nobody has made.
- Each input file gets one line in `Apps/moana/inputs.tsv` (sha256, source, version, script).

## M1 Data access

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M1-T1 | Find the DataMesh data that the token can read. | Suman | ✅ 2026-10-09 | The tables in [data.md](data.md) are written. `scripts/check_datamesh.py` makes them again. |
| M1-T2 | Send the [request list](data.md#requests-to-oceanum) to Oceanum. | (yet to decide) | 🔲 | Oceanum has the list. |
| M1-T3 | Get a reply for each request. Write the reply in the Status column. | (yet to decide) | 🔲 | No request has the status "Not sent" or "Sent". |
| M1-T4 | Run `scripts/check_datamesh.py` after each reply. Update [data.md](data.md). | (yet to decide) | 🔲 | The tables agree with the script output. |

## M2 Grid

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M2-T1 | Select the grid: `Apps/moana/Input/moana_grid.nc` (397 × 467 points, 40 levels), or a new grid from `gebco_2026` on DataMesh: (yet to decide). | (yet to decide) | 🔲 | The grid file is in `inputs.tsv`. |
| M2-T2 | Set the vertical levels (number of levels, `THETA_S`, `THETA_B`, `TCLINE`): (yet to decide). | (yet to decide) | 🔲 | The values are in the `.in` file and the grid file. |

## M3 Model setup

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M3-T1 | Examine `Apps/moana/Include/moana.h` for DataMesh inputs. Change it if necessary. | (yet to decide) | 🔲 | `scripts/build_roms.sh Apps/moana` builds ROMS. |
| M3-T2 | Examine `Apps/moana/Runs/moana.in`. Set the file names, time step and run period. | (yet to decide) | 🔲 | ROMS reads the file with no error. |
| M3-T3 | Write the job script and complete `Apps/moana/blueprint.yaml`. | (yet to decide) | 🔲 | `scripts/check_blueprint.sh` passes. |

## M4 Ocean initial and boundary files

Source: CMEMS GLOBAL_ANALYSISFORECAST_PHY_001_024 on DataMesh ([data.md](data.md#ocean)).

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M4-T1 | Write a script that gets T, S, u, v and ζ for the domain and run period. Record the datasource ID, query, `oceanum` version and cache hash. | (yet to decide) | 🔲 | The files are in `inputs.tsv`. |
| M4-T2 | Make the initial file. | (yet to decide) | 🔲 | The file is in `inputs.tsv`. A plot shows the fields. |
| M4-T3 | Make the boundary files. | (yet to decide) | 🔲 | The files are in `inputs.tsv`. A plot shows the four edges. |
| M4-T4 | Make the climatology and nudging files. Use nudging or not: (yet to decide). | (yet to decide) | 🔲 | The files are in `inputs.tsv`, or the task is dropped. |

## M5 Tides

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M5-T1 | Make the tide file from TPXO9 on DataMesh. Which TPXO9 set and which constituents: (yet to decide). `scripts/fetch_tpxo.py` and `scripts/make_tide_file.py` exist. Examine them first. | (yet to decide) | 🔲 | The file is in `inputs.tsv`. |

## M6 Atmosphere

Source: ERA5 on DataMesh ([data.md](data.md#atmosphere)).

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M6-T1 | Get the missing ERA5 fields from Oceanum (requests 1–4). | (yet to decide) | ⛔ | DataMesh has all eight ROMS fields for the run period. |
| M6-T2 | Write a script that gets the ERA5 fields for the domain and run period. | (yet to decide) | 🔲 | The files are in `inputs.tsv`. |
| M6-T3 | Make the ROMS forcing file: `Uwind`, `Vwind`, `Tair`, `Qair`, `Pair`, `rain`, `swrad`, `lwrad_down`. | (yet to decide) | 🔲 | The file is in `inputs.tsv`. A plot shows each field. |

## M7 Rivers

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M7-T1 | DataMesh has no river data. Select an option: no rivers, river data from Oceanum (request 9), or an exception to decision D1: (yet to decide). | (yet to decide) | 🔲 | The option is in [decisions.md](decisions.md). |

## M8 Test runs

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M8-T1 | Run for 1 day. Find a stable time step. | (yet to decide) | 🔲 | The run is in [runs.md](runs.md). |
| M8-T2 | Run for 1 month. Examine the boundaries for noise and drift. | (yet to decide) | 🔲 | The run is in [runs.md](runs.md). |

## M9 Forward run

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M9-T1 | Select the run period. It must start on or after 2022-06-01 (start of the ocean data). It must stop before the forecast part of the ocean data. Which period: (yet to decide). | (yet to decide) | 🔲 | The period is in [decisions.md](decisions.md). |
| M9-T2 | Do the forward run. | (yet to decide) | 🔲 | The run is in [runs.md](runs.md). |

## M10 Check the results

| ID | Task | Owner | Status | Done when |
|---|---|---|---|---|
| M10-T1 | Select the observations and statistics for the check (for example OSTIA SST, Argo profiles). Which ones, and which differences are acceptable: (yet to decide). | (yet to decide) | 🔲 | The list is in [decisions.md](decisions.md). |
| M10-T2 | Compare the run with the observations. Write the result. | (yet to decide) | 🔲 | The result is in this folder. |

## Open questions

| Question | Where |
|---|---|
| Does the hourly ζ in the ocean data include tides? We add TPXO tides at the boundary. | [Request 6](data.md#requests-to-oceanum) |
| Do past values in the ocean data change? Which model versions does it contain? | [Request 7](data.md#requests-to-oceanum) |
| Which licence terms apply to the input files that we make? | [Request 8](data.md#requests-to-oceanum) |
| Which river option do we use? | M7-T1 |
| Which grid do we use? | M2-T1 |
| Which run period do we use? | M9-T1 |
| How do we check the results? | M10-T1 |
