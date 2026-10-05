# ADR-0003: Use 40 vertical levels instead of 50

**Status:** Accepted · **Date:** 2026-10-05 · **Deciders:** Suman

## Context
The paper and the published `roms.in` use `N = 50`. The published grid file
stores 40 s-levels. The forward model will be the background for 4D-Var,
where every tangent-linear and adjoint run costs several forward runs.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| 40 levels | Matches the grid file; about 20 % fewer 3D points, so cheaper forward, TL and AD runs | Differs from the paper; the published `_N50` files cannot be reused as they are |
| 50 levels (paper) | Like-for-like with the paper | More expensive, especially for 4D-Var |

## Decision
Use `N = 40` with `Vtransform = 2` and `Vstretching = 5`. The stretching
parameters are set in P1-M1-T03.

Which of the pros above drove the choice is not recorded: ❓ UNKNOWN.

## Consequences
- Initial, boundary, climatology, nudging and river files are built for 40 levels.
- Vertical comparisons with the paper (profiles, mixed-layer depth) are not like-for-like ([risk R5](../risks.md)).
- `THETA_S`, `THETA_B` and `TCLINE` must still be chosen: the `.in` (6, 2, 250 m) and the grid file (6.5, 2, 100 m) disagree.
