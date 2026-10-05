# Brief

**Last updated:** 2026-10-05

## Headline
A reproducible 5 km ROMS forward model of New Zealand waters, rebuilt from
the published Moana hindcast on the pinned ROMS 4.x ([ADR-0005](decisions/0005-roms-version.md)) and ready to be the background
model for 4D-Var data assimilation. Its statistics are checked against the
published hindcast ([ADR-0006](decisions/0006-published-hindcast-as-benchmark.md)).

## The problem
The Moana Ocean Hindcast (Souza et al., 2023,
[markdown copy](hindcast_paper/MoanaHindcast.md)) is a free-running 28-year
model of the NZ ocean estate. Free runs drift from the real ocean. Data
assimilation corrects that, and strong-constraint 4D-Var needs a good
background model first (paper §4). The published configuration is
incomplete for a rebuild: no ROMS source, no nudging or rivers file, no
scripts that made the inputs ([risks R1–R3](risks.md)). So the model has to
be rebuilt, in a form someone else can rerun. The goal is the forward model,
not a second copy of the hindcast: the published hindcast output is the
benchmark for its statistics, and possibly a source of initial conditions.

## Who it serves
| Stakeholder | What they need from Moana | How we'll know they got it |
|---|---|---|
| Oceanum (commercial partner, DataMesh) | ❓ UNKNOWN | ❓ UNKNOWN |
| Royal New Zealand Navy (has expressed interest) | ❓ UNKNOWN | ❓ UNKNOWN |
| This project's own 4D-Var work (Phase 2) | A forward model that runs, is checked against observations, and builds in tangent-linear/adjoint form | Phase 1 exit criteria in the [roadmap](01-roadmap.md) |
| Anyone reproducing a run | Code, inputs and environment recorded per run | `scripts/verify_run.sh` passes on an old run directory |

## What success looks like (measurable)
Our forward model's statistics are compared with the published hindcast's
over the same period. Our 40-level model on a newer ROMS is not
like-for-like ([risk R5](risks.md)), so how close is close enough is
(yet to decide).

| Metric | Compared with | How measured |
|---|---|---|
| SSH mean, variance, leading EOFs | Published hindcast | P1-M9-T02 |
| SST and SSS mean, variance, seasonal cycle | Published hindcast | P1-M9-T03 |
| T/S profiles and mixed-layer depth | Published hindcast | P1-M9-T04 |
| Tidal constants (M2, S2, N2, K1) | Published hindcast (paper: M2 amplitude RMSE ≈ 4 cm at gauges) | P1-M4-T02, P1-M9-T05 |
| Mean transports | Published hindcast (paper Table 5: EAUC ≈ 10 Sv, SC ≈ 9 Sv, Cook Strait ≈ 0.2 Sv) | P1-M9-T06 |
| Run period | (yet to decide), inside 1993–2020 | P1-M8-T02 |
| Reproducibility | Every run has a receipt; every input is in `inputs.tsv` | `scripts/verify_run.sh`, `scripts/check_inputs.sh` |

## Non-goals
- ROMS-JEDI ([ADR-0004](decisions/0004-forward-model-first-then-4dvar.md)).
- Rebuilding the bathymetry ([ADR-0002](decisions/0002-start-from-published-moana-config.md)).
- Reproducing the 1993–2020 hindcast or the paper's observation tables ([ADR-0006](decisions/0006-published-hindcast-as-benchmark.md)).
- In this phase: a free-running forecast and extending the hindcast past 2020 ([risk R13](risks.md)).

## External FAQ
**Q:** Is this the same model as the published Moana hindcast?
**A:** Same grid and starting configuration. It differs in ROMS version (4.x
vs 3.9) and vertical levels (40 vs 50); see [model-config](reference/model-config.md).

**Q:** Where does the boundary data come from?
**A:** GLORYS12v1 through Oceanum DataMesh ([ADR-0001](decisions/0001-datamesh-for-forcing-and-boundaries.md)).

**Q:** Can I rerun a result?
**A:** Yes: every run is submitted with `scripts/submit_run.sh`, which keeps a
code copy and a receipt. See [REPRODUCIBILITY.md](../REPRODUCIBILITY.md).

## Internal FAQ
**Q:** How much compute does the hindcast need, and is it within the allocation?
**A:** ❓ UNKNOWN until P1-M7-T02 ([risk R8](risks.md)).

**Q:** What if a key input is unavailable (nudging file, rivers file)?
**A:** Build it from the paper's description and public data (P1-M3-T04, P1-M6-T01); record the difference.

**Q:** Can the forward model's physics be used by 4D-Var?
**A:** To be checked option by option in P1-M2-T04 ([risk R10](risks.md)).

**Q:** What are the data-licensing terms through DataMesh?
**A:** ❓ UNKNOWN.

**Q:** Who maintains the model after Phase 1?
**A:** ❓ UNKNOWN.
