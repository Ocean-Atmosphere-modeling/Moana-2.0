# ADR-0006: Use the published hindcast as a statistical benchmark, not a target to reproduce

**Status:** Accepted · **Date:** 2026-10-05 · **Deciders:** Suman

## Context
The old plan rebuilt the Moana hindcast for 1993–2020 and checked it against
the paper's observation-based tables. The goal of this project is a forward
model for 4D-Var ([ADR-0004](0004-forward-model-first-then-4dvar.md)), not a
second copy of the hindcast. The published hindcast output (Zenodo
10.5281/zenodo.5895265) covers 1993–2020 on the same grid with 50 levels.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| Reproduce the 1993–2020 hindcast and its paper tables | Like-for-like with a published paper | 28 years of compute; not needed for 4D-Var |
| Compare our forward model's statistics with the published hindcast | Same grid, so maps compare cell by cell; any period inside 1993–2020 works | Inherits the hindcast's own errors; 40 vs 50 levels |

## Decision
The published hindcast is used to check the statistics of our forward model
(means, variances, seasonal cycles, tides, transports). It may also be used
to make initial conditions: (yet to decide).

## Consequences
- The run period no longer has to be 1993–2020; it is (yet to decide).
- Observation-based checks (tide gauges, coastal stations, CORA) are no longer Phase 1 tasks; whether to keep any is (yet to decide). Observations are still needed for 4D-Var in Phase 2.
- Initial conditions from the hindcast would need vertical interpolation from 50 to 40 levels ([ADR-0003](0003-use-40-vertical-levels.md)).
- Downloading the needed hindcast output (P1-M0-T10) becomes a Phase 1 dependency.
