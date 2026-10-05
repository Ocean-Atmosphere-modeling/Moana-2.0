# Risks and open questions

**Last updated:** 2026-10-05

| ID | Risk or open question | Likelihood (L/M/H) | Impact (L/M/H) | Owner | Next step | Status |
|---|---|---|---|---|---|---|
| R1 | The nudging coefficient file (`nz5km_nudg_N50.nc`) is not in the published archive, so the published nudging cannot be reproduced exactly | H | M | ❓ | Ask the authors (P1-M0-T06); otherwise build one to the paper's description (1 d⁻¹ → 0 over ≈ 200 km) | Open |
| R2 | The rivers file (`nz5km_N50_rivers.nc`) is not published; which 42 rivers, mouth locations, and annual vs monthly climatology are unknown | H | M | ❓ | Ask the authors; fallback is the MfE reach statistics (P1-M6-T01) | Open |
| R3 | The archive's `roms_src/` is empty and the scripts that made the inputs are not included | H | M | ❓ | Ask the authors (P1-M0-T06) | Open |
| R4 | The published files disagree with the paper: `MY25_MIXING` vs GLS k-kl; `RadNud` vs clamped 3D momentum boundaries | — | M | ❓ | Decide which to follow when writing `moana.h` / `roms_moana.in` (P1-M2-T01, T02) | Open |
| R5 | 40 levels instead of 50 ([ADR-0003](decisions/0003-use-40-vertical-levels.md)) makes vertical statistics not like-for-like with the 50-level published hindcast, and initial conditions from it need 50 → 40 interpolation; stretching parameters in `.in` and grid file disagree | H | L | ❓ | Choose `THETA_S`, `THETA_B`, `TCLINE` (P1-M1-T03); compare on depth levels (P1-M9-T04) | Open |
| R6 | How the authors joined CFSR (to 2010) and CFSv2 (from 2011) is unknown | M | M | ❓ | Ask the authors or check the published `meteo` file attributes if obtained | Open |
| R7 | 28 years of 5 km input and hourly output is several TB; storage location and quota not chosen | M | H | ❓ | Choose `$MOANA_DATA` and estimate sizes (P1-M0-T08) | Open |
| R8 | Core-hours for the forward run (period yet to decide) and later 4D-Var may exceed the Amarel allocation | ❓ | H | ❓ | Time tilings and estimate cost (P1-M7-T02) | Open |
| R9 | A DataMesh datasource can change in place, and it is not confirmed that it exposes the upstream GLORYS version | M | M | ❓ | Record every query and fetch date; spot-check against Copernicus Marine (P1-M3-T01) | Open |
| R10 | Some forward-model options may not be supported in ROMS tangent-linear/adjoint (to be checked: `MY25_MIXING`, `BULK_FLUXES` and others) | ❓ | H | ❓ | Check every option (P1-M2-T04) before the production run | Open |
| R11 | The grid sits in `Apps/moana/` but `inputs.tsv` expects it under `$MOANA_DATA/published/moana_hindcast_v1.0/`, and `MOANA_DATA` is unset, so `scripts/check_inputs.sh` reports it missing. `Moana_grid.ipynb` reads a second copy outside the manifest, in conda env `chapter1` | H | L | ❓ | Move the grid to `$MOANA_DATA` (P1-M0-T08); point the notebook at the manifest copy and `moana_python` | Open |
| R12 | The published archive has no licence, so its files must not be committed. The copies of `roms.in`, `roms3d.h`, `roms_config.sh` and the grid in `Apps/moana/` are git-ignored (2026-10-05), so they can't be committed by accident or block `scripts/submit_run.sh` | L | M | ❓ | Ask the authors for a licence if the files need to be shared | Mitigated |
| R13 | A free-running forecast, extending the hindcast to the present, and what the Royal New Zealand Navy needs are not on the roadmap | ❓ | ❓ | ❓ | Confirm with Oceanum and the advisor whether they belong to this project | Open |
