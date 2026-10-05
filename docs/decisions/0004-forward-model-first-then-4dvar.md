# ADR-0004: Build the forward model first, then add ROMS 4D-Var

**Status:** Accepted · **Date:** 2026-10-05 · **Deciders:** Suman

## Context
The goal is a data-assimilating model of NZ waters. Strong-constraint 4D-Var
assumes a good background model (paper §4). Earlier notes also mentioned a
later move to ROMS-JEDI.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| Forward model first, then ROMS 4D-Var | The free run's statistics are checked against the published hindcast before DA hides its errors; 4D-Var ships with ROMS | Adjoint support limits physics options |
| Plan a later move to ROMS-JEDI | ❓ | Removed from scope on 2026-10-05 |

## Decision
Phase 1 builds and checks the forward model. Phase 2 adds ROMS 4D-Var on top.
ROMS-JEDI is out of scope.

## Consequences
- The forward model's CPP options are checked for TL/AD support during Phase 1 (P1-M2-T04), not after it.
- No JEDI tasks are on the roadmap.
- A free-running forecast and extending the hindcast to the present are not on the roadmap ([risk R13](../risks.md)).
