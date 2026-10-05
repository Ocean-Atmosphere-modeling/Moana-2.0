# Devlog

Dated session notes, newest first. Dates before 2026-10-05 are reconstructed
from git history.

### 2026-10-05
- **Did:** Moved the published configuration (`roms.in`, `roms3d.h`, `roms_config.sh`, `nz5km_grd.nc`) into `Apps/moana/`; started `Moana_grid.ipynb` (replaces `Moana.ipynb`). Replaced the todo list with this docs set; old list archived. Git-ignored the published reference copies in `Apps/moana/`; added `CLAUDE.md` with the docs-maintenance rules.
- **Decided:** The published hindcast is a statistical benchmark and maybe an initial-condition source, not a target to reproduce; run period yet to decide (→ [ADR-0006](decisions/0006-published-hindcast-as-benchmark.md)). ROMS 4.x over 3.9 (→ [ADR-0005](decisions/0005-roms-version.md)). Reuse the published grid (→ [ADR-0002](decisions/0002-start-from-published-moana-config.md)); 40 vertical levels (→ [ADR-0003](decisions/0003-use-40-vertical-levels.md)); forward model first, then ROMS 4D-Var, no JEDI (→ [ADR-0004](decisions/0004-forward-model-first-then-4dvar.md)).
- **Blocked:** —
- **Next:** P1-M0-T06 (ask authors for missing files), P1-M0-T08 (`$MOANA_DATA`), P1-M1-T02/T03 (mask review, stretching parameters).

### 2026-10-01
- **Did:** Blueprints and `check_blueprint.sh`; segment chains with executable and restart checksums; `verify_run.sh`; GitHub Actions CI with a gfortran reference; `CITATION.cff`; `fetch_published_config.sh`; reproducibility scorecard (18/20). UPWELLING regression and restart tests PASS.

### 2026-09-29
- **Did:** Added the hindcast paper (markdown + figures) and the build todo list.

### 2026-09-24
- **Did:** Frozen code copies per run, input manifest, tolerance-based regression check, UPWELLING guide with reference figures.

### 2026-09-23
- **Did:** Pinned ROMS as a submodule; module environment; oneAPI/ifx toolchain on Amarel; first UPWELLING test; reproducibility guide.

### 2026-09-17
- **Did:** Repository created.
