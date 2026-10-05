# ADR-0002: Start from the published Moana grid and configuration

**Status:** Accepted · **Date:** 2026-10-05 · **Deciders:** Suman

## Context
The Moana hindcast authors published their grid, `roms.in`, `roms3d.h` and
build settings (Zenodo 10.5281/zenodo.6484908). The old plan rebuilt the grid
from GEBCO and local surveys (old tasks 1.1–1.2). The published grid is now in
`Apps/moana/nz5km_grd.nc` and its sha256 matches `inputs.tsv`.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| Reuse the published grid and settings | Same bathymetry and mask as the paper; comparison with the published hindcast is like-for-like horizontally; weeks of grid work saved | Inherits their choices, including undocumented ones; the archive has no licence |
| Rebuild grid and bathymetry | Full control; newer GEBCO | Large effort; results no longer comparable cell by cell |

## Decision
Use the published grid and start `moana.h` and `roms_moana.in` from the
published files, translated to ROMS 4.x.

## Consequences
- Bathymetry compilation (old 1.2) is dropped. The mask review and PGE test stay (P1-M1-T02, T04).
- Where the published files disagree with the paper, the files are recorded as what actually ran ([model-config](../reference/model-config.md)).
- The published files have no licence, so they stay fetched, not committed ([risk R12](../risks.md)).
