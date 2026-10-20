# CLAUDE.md

Project docs start at [docs/README.md](docs/README.md). How runs are made
reproducible is in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## Docs maintenance
At the end of any session that changes code, configs, or plans:
- Add a dated entry to `docs/devlog.md`. Keep it very short: the problem and how we handle it.
- Do not change `docs/roadmap.md` or `docs/README.md`. The user updates them.
- If a model run was made, add a row to `docs/runs.md`.
- If a significant choice was made, add an entry to `docs/decisions.md` with status `Proposed`.
- If DataMesh access changes, run `scripts/check_datamesh.py` and update `docs/data.md`.
- Never invent facts; use `❓ UNKNOWN` and ask. In `docs/roadmap.md`, write `(yet to decide)` for anything not decided or not clear yet.
- Keep the docs simple. Write them in ASD-STE100 Simplified Technical English (rules in `docs/decisions.md`, D3).
- Do not change `docs/hindcast_paper/`.
