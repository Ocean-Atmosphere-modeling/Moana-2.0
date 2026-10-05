# CLAUDE.md

Project docs start at [docs/README.md](docs/README.md). How runs are made
reproducible is in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## Docs maintenance
At the end of any session that changes code, configs, or plans:
- Add a dated entry to `docs/devlog.md`.
- Update task status in `docs/01-roadmap.md` and the "Status at a glance" table in `docs/README.md`.
- If a model run was made, add a row to `docs/experiments/run-log.md`.
- If a significant choice was made, draft an ADR in `docs/decisions/` with status `Proposed`.
- Never invent facts; use `❓ UNKNOWN` and ask. In `docs/01-roadmap.md`, write `(yet to decide)` for anything not decided or not clear yet.
