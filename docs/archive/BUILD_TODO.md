# Building the Moana model: step-by-step to-do list

This is the work plan for rebuilding the **Moana Ocean Hindcast** configuration
(Souza et al., 2023; [markdown copy](hindcast_paper/MoanaHindcast.md)) in this
repository. Each numbered task below is written to become **one GitHub
issue**: it says what the component does in the model, what to do, what it
produces and how we know it is done.

The tasks are ordered the way a regional ocean model is actually put
together, so reading the list top to bottom also explains how the model works.

---

## 1. How a regional ROMS model works (the big picture)

ROMS solves the ocean equations on a grid. It knows nothing about New Zealand
until we give it files that describe **where** (grid), **what it starts
from** (initial conditions), **what drives it** (atmosphere, tides, rivers,
open-ocean boundaries) and **how to compute** (compile options and run
parameters). Everything else is checking that the solution to the governing equation is physical.

```
                 ┌──────────────── HOW TO COMPUTE ─────────────────┐
                 │  moana.h  (CPP options: physics, numerics)      │
                 │  roms_moana.in  (dt, tiling, files, output)     │
                 └───────────────────────┬─────────────────────────┘
                                         │ build (scripts/build_roms.sh)
                                         ▼
 WHERE                                ┌──────┐                      OUTPUT
 grid.nc  (lon/lat, bathymetry h,  ──▶│      │──▶ his.nc  hourly instantaneous
          land mask, s-levels)        │      │──▶ avg.nc  daily means
                                      │ ROMS │──▶ rst.nc  restart (to continue)
 START FROM                           │      │
 ini.nc   (T, S, u, v, ζ on 1 Jan) ──▶│      │           │
                                      │      │           ▼
 WHAT DRIVES IT                       │      │      EVALUATION
 bry.nc   GLORYS T,S,u,v,ζ at edges ─▶│      │      vs satellites (SSH, SST),
 nudging coefficients (sponge)     ──▶│      │      profiles (CORA), tide gauges,
 tide.nc  TPXO 11 constituents     ──▶│      │      coastal thermometers,
 frc.nc   CFSR wind, air T, RH,    ──▶│      │      literature transports
          rain, SW, LW, pressure      │      │
 river.nc 42 NZ rivers (climatology)─▶│      │
                                      └──────┘
```

### Component checklist (what the model needs)

| # | Component | File(s) | Source data | Paper § |
|---|---|---|---|---|
| A | Horizontal grid | `moana_grd.nc` | — (designed) | 2.1 |
| B | Bathymetry + land mask | in `moana_grd.nc` | GEBCO + NZ charts/surveys | 2.1 |
| C | Vertical grid | parameters in `.in` | — (designed) | 2.1 |
| D | Physics / numerics options | `moana.h`, `roms_moana.in` | — | 2.1 |
| E | Initial conditions | `moana_ini.nc` | GLORYS12v1, fetched through Oceanum Datamesh | 2.1–2.2 |
| F | Open boundary conditions | `moana_bry.nc` (+ nudging file) | GLORYS12v1 / Mercator nowcast, fetched through Oceanum Datamesh | 2.1–2.2 |
| G | Tides | `moana_tide.nc` | TPXO 7.8.1 (11 constituents) | 2.3 |
| H | Atmospheric forcing | `moana_frc_*.nc` | CFSR (NCAR) | 2.1, 2.3 |
| I | Rivers | `moana_rivers.nc` | data.govt.nz / MfE reach flow statistics (42 rivers, climatology; see 6.1) | 2.1 |
| J | Runs (spin-up + production) | job scripts, restarts | — | 2.1 |
| K | Evaluation | analysis scripts, figures | CMEMS, OISST, CORA5.2, LINZ, NIWA | 2.4, 3 |

### Target configuration (from the paper)

| Setting | Value |
|---|---|
| Domain | ≈ 161–185° E, ≈ 52–31° S (NZ EEZ incl. Auckland and Chatham Islands) |
| Grid | ≈ 5 km, 467 × 397 cells, 50 s-levels |
| Vertical stretching | Souza et al. (2015), θs = 6, θb = 2 |
| Tracer advection | Horizontal: split 3rd-order upstream; vertical: 4th-order centred |
| Vertical mixing | GLS k-kl (≈ Mellor–Yamada 2.5) |
| Horizontal mixing | Tracers along isopycnals, momentum along s-levels |
| Boundaries | T/S: radiation + nudging (1 d⁻¹ → 0 over ≈ 200 km); 3D u,v: clamped; ζ: Chapman (implicit); ubar/vbar: Flather |
| Period | 1993-01-01 → 2020-12-31, 1993 = spin-up |
| Output | Hourly instantaneous + daily mean |

---

## 2. Suggested GitHub labels and milestones

- **Milestones** = the phases below (`P0 Foundations` … `P9 Towards DA`).
- **Labels:** `grid`, `forcing`, `boundary`, `tides`, `rivers`, `config`,
  `run`, `evaluation`, `data`, `infra`, `docs`, plus `blocked` and
  `good first issue`.
- Each issue should end with **"Done when"** so it can be closed objectively,
  and new input files must be added to `Apps/moana/inputs.tsv` (sha256,
  source, version, script that made it; see [REPRODUCIBILITY.md](../REPRODUCIBILITY.md)).

Tasks marked ✅ are already done in this repository.

---

## Phase 0: Foundations

### 0.1 ✅ Reproducible toolchain and run system
Pinned ROMS submodule, `env/amarel.sh`, `scripts/build_roms.sh`,
`scripts/submit_run.sh` (code snapshot + receipt), `inputs.tsv` checks.

### 0.2 ✅ UPWELLING toolchain/regression test
`tests/upwelling/` builds and runs stock ROMS, PASS/FAIL against reference
energy.

### 0.3 Get the published Moana configuration as a reference `docs` `config`
**Why:** the authors published their exact ROMS source and configuration
files (Zenodo [10.5281/zenodo.6484908](https://doi.org/10.5281/zenodo.6484908)).
Starting from them avoids guessing dozens of settings.
- [x] Download the Zenodo archive, store it outside git and record its checksum: `scripts/fetch_published_config.sh` (the grid is listed in `Apps/moana/inputs.tsv`). The archive holds only the grid, `roms.in`, `roms3d.h` and `roms_config.sh`; its `roms_src/` folder is empty and the nudging file is missing, so those must be requested from the authors.
- [ ] List every CPP option in their `.h` and every non-default parameter in their `.in` in a table (`docs/reference_config.md`).
- [ ] Note which input files they used and how they were made (scripts included?).

**Done when:** a table of the reference CPP options and `.in` parameters is committed.

### 0.4 Decide ROMS version: 3.9 (paper) vs pinned 4.x `config`
**Why:** the paper used ROMS 3.9; `roms/` is pinned to `roms-4.2-39`.
Several CPP options and `.in` keywords were renamed or moved between these
versions (e.g. lateral boundary settings, tidal and bulk-flux options), so the
reference config cannot be copied blindly.
- [ ] Map every option from 0.3 to its ROMS 4.x equivalent (or mark as removed).
- [ ] Decide: stay on 4.x (recommended; newer DA code) or pin 3.9 for a first like-for-like reproduction.

**Done when:** the decision and the option mapping are written down. *Depends on 0.3.*

### 0.5 Data storage plan `data` `infra`
**Why:** 28 years of 5 km forcing, boundaries and hourly output is several TB.
- [ ] Choose `$MOANA_DATA` location(s) on Amarel (scratch vs project space), quotas, backup.
- [ ] Estimate sizes: GLORYS subset, CFSR subset, outputs (hourly + daily, 28 years).
- [ ] Set up accounts: Oceanum Datamesh token (GLORYS for initial and boundary conditions, see 3.1), Copernicus Marine (SSH, CORA for evaluation), NCAR RDA (CFSR), TPXO licence.

**Done when:** storage paths are in `env/amarel.sh` / README and accounts exist.

### 0.6 Download the published Moana hindcast (v2) as a benchmark `data` `evaluation`
**Why:** the published output (THREDDS, [10.5281/zenodo.5895265](https://doi.org/10.5281/zenodo.5895265))
lets us check our grid, and later our results, against theirs field by field.
- [ ] Download the grid and a sample period (e.g. 1 month of daily means, 1 week of hourly).
- [ ] Document the variables and file layout.

**Done when:** sample files are listed in a manifest and readable in Python.

---

## Phase 1: Where: grid, bathymetry, vertical levels

### 1.1 Horizontal grid `grid`
**Why:** defines the model cells: position, size (≈ 5 km), orientation,
Coriolis parameter `f`, metric terms `pm`, `pn`.
- [ ] Create a 467 × 397 grid over ≈ 161–185° E, 31–52° S (or reuse the published grid from 0.6; compare either way).
- [ ] Check the Tasman Front (north) and Subtropical Front (south) enter through the western boundary, and boundaries are far from the islands.
- [ ] Plot grid spacing and domain map.

**Output:** `moana_grd.nc` (without final bathymetry). **Done when:** grid matches the published one (size, corners, spacing).

### 1.2 Bathymetry compilation `grid` `data`
**Why:** depth `h` controls the flow: boundary currents, shelf upwelling,
canyons (Kaikōura, Pegasus), tides.
- [ ] Download GEBCO (2021 or newer) for the domain.
- [ ] Gather local sources (LINZ navigation charts, NIWA bathymetry, echo-sounder surveys) and merge.
- [ ] Interpolate to the grid; set minimum depth.

**Output:** raw `h` in `moana_grd.nc`. *Depends on 1.1.*

### 1.3 Land/sea mask and hand editing `grid`
**Why:** the mask decides which cells are ocean. Narrow passages matter
(Cook Strait is only ≈ 3 cells wide at 5 km, and the paper blames its
narrowness for low transport).
- [ ] Build `mask_rho/u/v/psi` from a coastline (e.g. GSHHG or LINZ coastline).
- [ ] Remove isolated wet cells and 1-cell channels; check Cook Strait, Foveaux Strait, harbour mouths, Chatham and Auckland Islands.

**Done when:** mask plot reviewed; no isolated wet points. *Depends on 1.2.*

### 1.4 Vertical coordinate `grid` `config`
**Why:** ROMS layers follow the seafloor (s-coordinates). A thin, stable top
layer matters for SST and for assimilating SST later.
- [ ] Set `N = 50`, `Vtransform = 2`, `Vstretching = 5` (Souza et al., 2015), `THETA_S = 6`, `THETA_B = 2`, `TCLINE` (take from reference config, 0.3).
- [ ] Plot layer depths along a section across the shelf and in deep water.

**Done when:** surface layer thickness range is documented.

### 1.5 Bathymetry smoothing with pressure-gradient-error test `grid` `run`
**Why:** steep slopes in s-coordinates create fake currents (pressure
gradient error, PGE). The paper smooths **only** where the PGE bottom velocity
exceeds 1 cm s⁻¹, keeping the total volume.
- [ ] Set up an "ocean at rest" test: horizontally uniform T/S stratification, no forcing, closed boundaries, run ~30 days.
- [ ] Find points with spurious bottom speed > 1 cm s⁻¹; smooth locally; repeat until none remain.
- [ ] Check basin volume is preserved; record `rx0`/`rx1` before and after.

**Output:** final `moana_grd.nc`, added to `inputs.tsv`. *Depends on 1.3, 1.4, 2.1, 2.2.*

---

## Phase 2: How to compute: model configuration

### 2.1 CPP options file `Apps/moana/moana.h` `config`
**Why:** decides what physics and numerics are compiled into ROMS.
- [ ] Start from the reference `.h` (0.3) translated to ROMS 4.x (0.4).
- [ ] Include (names to be checked against 0.4): `UV_ADV`, `UV_COR`, `UV_VIS2` + `MIX_S_UV`, `TS_DIF2` + `MIX_ISO_TS`, `GLS_MIXING` (k-kl), `BULK_FLUXES`, `LONGWAVE_OUT`, `ATM_PRESS` (inverse barometer), `SSH_TIDES`, `UV_TIDES`, `RAMP_TIDES`, `SOLAR_SOURCE`, `MASKING`, `SPHERICAL`, `CURVGRID`, `AVERAGES`, `NONLIN_EOS`, `SALINITY`.
- [ ] Tracer advection is **not** a CPP option in ROMS ≥ 3.8: set `Hadvection == SU3` (split third-order upstream) and `Vadvection == C4` in `roms_moana.in` (2.2). Rivers are switched on in the `.in` file too (`LuvSrc`, `LtracerSrc`).
- [ ] Comment every option with the paper section it comes from.

**Done when:** `scripts/build_roms.sh Apps/moana` compiles. *Depends on 0.4.*

### 2.2 Run parameters `Apps/moana/roms_moana.in` `config`
**Why:** grid size, time steps, tiling, boundary types, input/output file
names and output frequencies.
- [ ] `Lm = 465`, `Mm = 395` (interior points for 467 × 397, verify), `N = 50`.
- [ ] Baroclinic `DT` and `NDTFAST` from CFL (start ≈ 300 s / 30; tune in 7.1).
- [ ] Lateral boundary types per paper (see table in §1) for all 4 edges.
- [ ] Nudging timescales, `NHIS`/`NAVG`/`NRST` (hourly his, daily avg, monthly rst), tiling `NtileI × NtileJ`.
- [ ] `run_moana.slurm` following `tests/upwelling/`.

**Done when:** a 1-day run with dummy/analytic inputs starts without errors. *Depends on 2.1.*

---

## Phase 3: Start from / edges: initial and boundary conditions (GLORYS via Datamesh)

### 3.1 Fetch GLORYS12v1 and Mercator nowcasts through Datamesh `data` `boundary`
**Why:** the open ocean outside the domain drives the large currents (EAUC,
Tasman Front, ACC branch). GLORYS was the best of four global reanalyses for NZ
(Souza et al., 2020). We fetch it through
[Oceanum Datamesh](https://docs.oceanum.io/docs/category/datamesh/index.html)
(Python package `oceanum`) instead of downloading from Copernicus Marine
directly: one query returns the domain subset as an xarray dataset.
- [ ] Get a Datamesh token and keep it in the `DATAMESH_TOKEN` environment variable (never in git, job scripts or receipts).
- [ ] Add `oceanum` to `env/moana_python.yml` and regenerate the lock file.
- [ ] Find the Datamesh datasource IDs for the GLORYS12v1 reanalysis and for the operational analysis/nowcast that continues it; check each against the CMEMS product it mirrors (product ID, version, time coverage, variables).
- [ ] Query daily T, S, u, v, ζ for the domain + margin, 1993–2020 (geofilter = bounding box, timefilter in chunks, e.g. one month per query) and write the subsets to `$MOANA_DATA`.
- [ ] Fetch script in `scripts/`; for every file record in `inputs.tsv` the datasource ID, the query (variables, geofilter, timefilter), the `oceanum` version and the fetch date, because a Datamesh datasource can be updated in place.

**Done when:** the full 1993–2020 subset is on disk, listed in `inputs.tsv`, and a spot check of one day matches the same field from Copernicus Marine. *Depends on 0.5.*

### 3.2 Initial conditions `boundary`
- [ ] Interpolate GLORYS 1993-01-01 to the grid (horizontal, then vertical onto s-levels); adjust for mask; compute ubar/vbar consistently.
- [ ] Plot SST, SSS and a section vs GLORYS.

**Output:** `moana_ini.nc`. *Depends on 1.5, 3.1.*

### 3.3 Boundary condition files `boundary`
- [ ] Extract daily boundary slices (N, S, E, W) for 1993–2020; yearly files.
- [ ] Check continuity across the GLORYS → nowcast switch.

**Output:** `moana_bry_YYYY.nc`. *Depends on 1.5, 3.1.*

### 3.4 Nudging (sponge) zone `boundary` `config`
**Why:** T/S near the edges are relaxed to GLORYS (1 d⁻¹ at the boundary → 0
at ≈ 200 km) so the interior and exterior do not drift apart; needs the
climatology/nudging fields.
- [ ] Build nudging coefficient file (`M3NUDG`/`TNUDG`-style or `NUDGING_COEF` file in 4.x).
- [ ] Decide whether full 3D climatology fields are needed for nudging or boundary values suffice (ROMS 4.x specifics).

**Done when:** a 1-month run shows no boundary noise or drift at the edges. *Depends on 3.3.*

---

## Phase 4: Tides

### 4.1 Tidal forcing file from TPXO `tides` `forcing`
**Why:** tides explain > 98 % of sea level variance at NZ tide gauges and
drive mixing on the shelf; global reanalyses leave them out.
- [ ] Get TPXO 7.8.1 (as in paper) or newer (TPXO9/10, document the change).
- [ ] Extract 11 constituents (M2, S2, N2, K2, K1, O1, P1, Q1, + 3 more, check reference config), including nodal corrections for the start date.
- [ ] Write the ROMS tide file (elevation and current ellipse parameters).

**Output:** `moana_tide.nc`. *Depends on 1.5.*

### 4.2 Tides-only test run `tides` `run`
**Why:** check tides on their own before mixing with everything else.
- [ ] Run 2–3 months barotropic or with constant stratification, tides only, Chapman/Flather boundaries.
- [ ] Harmonic analysis (e.g. `utide` in Python) at the 15 LINZ gauges; compare with Table 6 of the paper (M2 amplitude RMSE ≈ 4 cm).

**Done when:** M2/S2/N2/K1 amplitude and phase maps look like Fig. 11. *Depends on 4.1, 2.2, 9.5 (data).*

---

## Phase 5: Atmospheric forcing

### 5.1 Download CFSR / CFSv2 `data` `forcing`
**Why:** wind, heat and freshwater fluxes at the surface. Note: CFSR covers
1979–2010 and **CFSv2** continues from 2011; the paper just says "CFSR", so
check the reference config for how they joined them.
- [ ] 10 m u/v wind, 2 m air temperature, relative (or specific) humidity, precipitation rate, downward shortwave, downward longwave, mean sea level pressure; 1993–2020, domain + margin.
- [ ] Download script and manifest entries.

### 5.2 Forcing files for bulk fluxes `forcing`
- [ ] Convert to ROMS forcing format (units, names: `Uwind`, `Vwind`, `Tair`, `Qair`, `rain`, `swrad`, `lwrad_down`, `Pair`), time coordinate, yearly files.
- [ ] Decide whether to interpolate to the model grid or let ROMS interpolate on the fly.
- [ ] Check the 6-hourly vs hourly frequency and daily cycle of shortwave.

**Output:** `moana_frc_*_YYYY.nc`. *Depends on 5.1.*

### 5.3 Inverse barometer check `forcing` `run`
- [ ] Confirm `ATM_PRESS` (or equivalent) is on and `Pair` is read; in a short run, check ζ responds ≈ −1 cm per hPa.

---

## Phase 6: Rivers

### 6.1 River discharge climatology `rivers` `data`
**Why:** freshwater changes coastal density (e.g. Waihou and Piako rivers in
the Firth of Thames / Hauraki Gulf).

**What is known.** The paper only says the 42 rivers are "climatological
values obtained from the data.govt.nz portal" (§2.1); it names no dataset and
no river list. The reference config (0.3) reads them from
`nz5km_N50_rivers.nc` with `LuvSrc == T` and `LtracerSrc == T T`, but that
file is not in the Zenodo archive or the GitHub repository. So which rivers,
where their mouths sit on the grid, and whether "climatological" means annual
mean or monthly are all unknown.

- [ ] Ask the corresponding author (J. M. A. C. Souza) for `nz5km_N50_rivers.nc`; it is the only thing that settles the three unknowns above. Also look for a forcing folder on the Moana THREDDS server.
- [ ] If the file is not available, rebuild from the Ministry for the Environment table [Natural river flow statistics, predicted for all river reaches](https://data.mfe.govt.nz/table/52536-natural-river-flow-statistics-predicted-for-all-river-reaches/) (listed on [data.govt.nz](https://catalogue.data.govt.nz/dataset/natural-river-flow-statistics-predicted-for-all-river-reaches), so the closest match to the paper's wording): keep the reaches that end at the coast, rank by mean flow, take the 42 largest. Hadfield and Stevens (2021) did the same for Cook Strait (17 largest rivers, annual means).
- [ ] Cross-check the ranking against the MfE [River flows](https://data.mfe.govt.nz/layer/53309-river-flows/) layer and NIWA [NZ River Maps](https://shiny.niwa.co.nz/nzrivermaps/).
- [ ] Decide annual mean or monthly climatology. The reach statistics may only give an annual mean; a seasonal cycle would then have to come from gauge records (see 6.2).
- [ ] Assign each river mouth to a grid cell edge and direction; set river T and S (S = 0, T from climatology or air temperature) and the vertical distribution of the flow.
- [ ] Record the dataset, its version and the river list in `inputs.tsv` and in a short table (`docs/rivers.md`).

These portals block scripted access, so download by hand in a browser and
record the date.

**Output:** `moana_rivers.nc`. **Done when:** the 42 rivers are mapped on the grid and their total mean discharge is documented. *Depends on 1.3.*

### 6.2 (Later, improvement) Time-varying river flows `rivers`
The paper's conclusions name this as an improvement: inter-annual flow changes
can matter more than the seasonal cycle. Candidate sources:
- [CAMELS-NZ](https://doi.org/10.26021/canterburynz.28827644) (Canterbury; described in [ESSD 17, 5745, 2025](https://essd.copernicus.org/articles/17/5745/2025/)): hourly streamflow at 369 gauged catchments, 1972–2024, CC-BY 4.0 (14 stations need the provider's permission). Gauges are upstream of the mouths, so flows need scaling to the coast with the reach mean flows from 6.1.
- [NIWA hydrometric station data](https://data.niwa.co.nz/products/hydro-data): daily observed flows; needs a DataHub login and API key.
- NIWA TopNet / NZ Water Model: modelled hourly flow for every reach back to 1972; no public download, request from NIWA.

---

## Phase 7: First runs and tuning

### 7.1 One-month test run `run`
- [ ] Run January 1993 with everything on; tune `DT`/`NDTFAST` for stability.
- [ ] Watch for blow-ups, boundary noise, unrealistic SSH/SST.
- [ ] Check energy diagnostics and output file sizes.

### 7.2 Performance and cost `run` `infra`
- [ ] Try several tilings; measure simulated days per wall-clock hour.
- [ ] Estimate total core-hours and wall time for 28 years; fit within allocation and queue limits.

### 7.3 One-year run and sanity checks `run` `evaluation`
- [ ] Run 1993 (the spin-up year).
- [ ] Domain-mean KE, T, S, SSH time series: should settle, not drift.
- [ ] Quick comparison with OISST and the published hindcast for 1993.

**Done when:** no drift and no boundary artefacts. *Depends on 3, 4, 5, 6, 7.1.*

---

## Phase 8: Production hindcast

### 8.1 Restart chaining for 1993–2020 `run` `infra`
- [ ] Job chain: each job runs N months, writes a restart, next job continues (SLURM dependencies); inputs switch year by year.
- [ ] Each segment goes through `scripts/submit_run.sh` (receipts per segment).
- [ ] Automatic check after each segment (NaNs, blow-up, file completeness).

### 8.2 Run the hindcast `run`
- [ ] 1993 spin-up, 1994–2020 production. Monitor.

### 8.3 Output management `data`
- [ ] Hourly instantaneous + daily mean files, naming convention, CF metadata.
- [ ] Compression, archiving, and access for the team (e.g. THREDDS or shared directory).

---

## Phase 9: Evaluation (reproduce the paper's figures and tables)

Each item compares the model with observations **and** with GLORYS and the
published hindcast. Put reusable code in a Python package/folder
(e.g. `analysis/`), one script or notebook per figure.

### 9.1 Download observations `data` `evaluation`
CMEMS MSS and SLA (L4), NOAA OISST v2.1, CORA5.2 profiles, LINZ tide gauges
(15 stations, Table 2), coastal temperature stations (10, Table 3; Zenodo
[10.5281/zenodo.6399921](https://doi.org/10.5281/zenodo.6399921)).

### 9.2 Surface SSH: mean, variance, EOFs (Figs. 2–4, Table 4) `evaluation`
Daily means; 40-day low-pass before EOF; RMSE, MAE, MaxAE.

### 9.3 SST: domain mean, RMSE and bias maps (Figs. 5–6, Table 4) `evaluation`
Target: RMSE ≈ 0.23 °C.

### 9.4 Water column vs CORA5.2 and mixed layer depth (Figs. 7–9) `evaluation`
Co-locate in time, interpolate in space; RMSE profiles; layer-mean bias maps;
MLD with 0.2 °C threshold (de Boyer Montégut) / Holte & Talley; seasonal maps
and zonal percentiles.

### 9.5 Tides at LINZ gauges (Fig. 11, Table 6) `evaluation` `tides`
Hourly ζ at nearest wet point, 2015–2017, harmonic analysis of 8 constituents.

### 9.6 Sub-tidal sea level (Fig. 12) `evaluation`
Detide, 40 h low-pass, Willmott skill; target WS > 0.9 at most gauges.

### 9.7 Coastal temperature stations (Figs. 13–14, Table 7) `evaluation`
Mean, seasonal amplitude, anomaly std, correlation, Willmott skill.

### 9.8 Boundary current transports (Fig. 10, Table 5) `evaluation`
Define the 12 sections; daily transport (Eq. 3); compare with Table 5
(EAUC ≈ 10 Sv, SC ≈ 9 Sv, Cook Strait ≈ 0.2 Sv).

### 9.9 Evaluation report `docs`
Collect all metrics in one table next to the paper's values; decide whether
the rebuild reproduces the published hindcast.

---

## Phase 10: Towards data assimilation (project goal)

The paper frames the free run as the necessary base for a data-assimilating
reanalysis (strong-constraint 4D-Var assumes a good background model). Open
these as a separate epic once Phase 9 passes:

- 10.1 Observation files for ROMS DA (SST, SSH, Argo/CORA profiles) with errors.
- 10.2 Background error covariance: standard deviations and decorrelation scales from the free run.
- 10.3 Tangent linear / adjoint build of the Moana config (check which CPP options are supported in TL/AD).
- 10.4 Short 4D-Var test cycles (e.g. 3–7-day windows), then a cycling reanalysis.

---

## 3. Dependency overview

```
P0 foundations ─┬─▶ 1.1 grid ─▶ 1.2 bathy ─▶ 1.3 mask ─┐
                │                                       ├─▶ 1.5 smoothing (PGE) ─┐
                ├─▶ 2.1 moana.h ─▶ 2.2 roms_moana.in ──┘   + 1.4 vertical       │
                │                                                                ▼
                ├─▶ 3.1 GLORYS (Datamesh) ───────────────▶ 3.2 ini, 3.3 bry, 3.4 nudging
                ├─▶ 4.1 TPXO ─────────────────────────────▶ 4.2 tides-only test
                ├─▶ 5.1 CFSR ─────────────────────────────▶ 5.2 forcing, 5.3 IB check
                └─▶ 6.1 rivers
                                   all of the above ─▶ 7 test runs ─▶ 8 production ─▶ 9 evaluation ─▶ 10 DA
```

Phases 3, 4, 5, 6 and 9.1 (data downloads) can run **in parallel** once the
grid (Phase 1) exists, so they are good to assign to different people.
