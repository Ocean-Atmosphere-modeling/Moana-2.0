# Devlog

Add new entries at the top. Use the date of the work.

## 2026-10-09

- **Changed goal:** We do not copy the Moana paper and its data. We run the Moana model with Oceanum DataMesh data only ([D1](decisions.md#d1-use-datamesh-data-only)). The roadmap covers the forward model only ([D2](decisions.md#d2-forward-model-only)).
- **Did:**
  - Found the data that the DataMesh token can read. The results are in [data.md](data.md).
  - Wrote `scripts/check_datamesh.py`. It makes the data.md tables again.
  - Deleted all old docs, but not `docs/hindcast_paper/`. We did not commit the old docs first. Six uncommitted edits and two untracked decision records are lost.
  - Wrote new docs in ASD-STE100 ([D3](decisions.md#d3-simple-docs-in-asd-ste100)).
  - Changed the links to old docs pages in `CLAUDE.md`, `README.md`, `REPRODUCIBILITY.md`, `.gitignore`, `Apps/moana/blueprint.yaml` and `Apps/moana/python_scripts/plot_grid.py`.
- **Found:**
  - The ocean data (T, S, u, v every 6 hours, ζ every hour) is on DataMesh from 2022-06-01. The 3D currents are new since 2026-10-07.
  - ERA5 wind and pressure are on DataMesh. ERA5 air temperature and rain stop on 2025-05-01. The catalogue says 2026-08-01.
  - ERA5 short-wave stops on 2020-01-01. ERA5 humidity and long-wave are not on DataMesh.
  - DataMesh has no river data.
- **Blocked:** M6 Atmosphere. We need requests 1–4 in [data.md](data.md#requests-to-oceanum).
- **Next:** Send the request list to Oceanum (M1-T2).
- **Not changed:** The old download scripts (`scripts/fetch_glorys.py`, `fetch_cfsv2.sh`, `subset_cfsv2.py`, `fetch_camels_nz.sh`) and the data on disk. They are not part of the DataMesh-only plan.
