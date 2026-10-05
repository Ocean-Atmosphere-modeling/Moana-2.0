# ADR-0005: Use the pinned ROMS 4.x instead of ROMS 3.9

**Status:** Accepted · **Date:** 2026-10-05 · **Deciders:** Suman

## Context
The paper used ROMS 3.9. `roms/` is pinned to a 4.x commit (`roms-4.2-39`).
Several CPP options and `.in` keywords were renamed or moved between these
versions (for example tracer advection moved from CPP to the `.in` file). The
published `roms_src/` folder is empty, so the authors' exact 3.9 source is not
available.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| Stay on 4.x | Newer 4D-Var code; already pinned, built and tested (UPWELLING, CI) | Published options must be translated; not like-for-like with the paper |
| Pin 3.9 | Like-for-like first reproduction | Exact authors' source missing anyway; older DA code; tests and CI must be redone |

## Decision
Stay on the pinned 4.x. Map every published option to its 4.x equivalent
(P1-M0-T07).

## Consequences
- Differences from the paper may come from the version change as well as from 40 levels; the evaluation report (P1-M9-T09) must say so.
