# Moana 2.0

**Last updated:** 2026-10-09

## What this project does

We run the ROMS ocean model for New Zealand waters on a 5 km grid.
We start from the Moana model configuration ([paper](hindcast_paper/MoanaHindcast.md)).
We use input data from Oceanum DataMesh only ([decision D1](decisions.md#d1-use-datamesh-data-only)).
The goal is one forward model run. A forward model run has no data assimilation.
Oceanum is the commercial partner.

## Status

| Milestone | Status |
|---|---|
| M1 Data access | 🔄 |
| M2 Grid | 🔲 |
| M3 Model setup | 🔲 |
| M4 Ocean initial and boundary files | 🔲 |
| M5 Tides | 🔲 |
| M6 Atmosphere | ⛔ |
| M7 Rivers | 🔲 |
| M8 Test runs | 🔲 |
| M9 Forward run | 🔲 |
| M10 Check the results | 🔲 |

🔲 not started · 🔄 in progress · ⛔ blocked · ✅ done. The tasks are in the [roadmap](roadmap.md).

## Next actions

| Task | Action | Owner |
|---|---|---|
| M1-T2 | Send the [request list](data.md#requests-to-oceanum) to Oceanum. | (yet to decide) |
| M2-T1 | Select the grid. | (yet to decide) |
| M9-T1 | Select the run period. It must start on or after 2022-06-01. | (yet to decide) |

## Pages

| Page | Content |
|---|---|
| [roadmap.md](roadmap.md) | Milestones, tasks and open questions |
| [data.md](data.md) | Data on DataMesh, data that we need, requests to Oceanum |
| [decisions.md](decisions.md) | Decisions and the reasons for them |
| [runs.md](runs.md) | Model runs |
| [devlog.md](devlog.md) | Work log, by date |
| [hindcast_paper/MoanaHindcast.md](hindcast_paper/MoanaHindcast.md) | The Moana hindcast paper (Souza et al., 2023) |
| [../REPRODUCIBILITY.md](../REPRODUCIBILITY.md) | How we make runs that other people can do again |
