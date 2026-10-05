# Reproducibility scorecard

How this repository scores on the ten criteria used to compare ocean-model
repositories in [useful_repos.md](useful_repos.md) (section 2). Each
criterion scores 0, 1 or 2, and a point only counts if a file in the
repository backs it: anything not visible scores 0.

The best repositories in that survey scored 18 out of 20 (C-Star,
access-om3-configs, CEFI-regional-MOM6). The best Rutgers-ROMS repository
scored 13.

| # | Criterion | Score | Evidence |
|---|---|---|---|
| 1 | Model source pinned to an exact version | 2 | `.gitmodules` and the `roms` submodule commit; repeated in each `blueprint.yaml` and checked by `scripts/check_blueprint.sh` |
| 2 | CPP header and `.in` files in git | 2 | `tests/upwelling/upwelling.h`, `roms_upwelling.in`. The Moana header and `.in` are not written yet (`Apps/moana/blueprint.yaml` is `state: draft`) |
| 3 | Scripts that generate the input files | 1 | `scripts/fetch_published_config.sh` fetches and verifies the published grid. Nothing yet builds initial, boundary, tidal, atmospheric or river files |
| 4 | Input provenance | 2 | `Apps/moana/inputs.tsv` (sha256, source, version, script) checked by `scripts/check_inputs.sh` on every submit |
| 5 | Software environment | 2 | `env/amarel.sh` (exact modules), `env/moana_python.lock.txt`, `env/ci_gfortran.lock.txt` |
| 6 | Run scripts and restart chaining | 2 | `scripts/submit_run.sh --segments N`; chaining, executable and restart checks in `tests/upwelling/run_upwelling.slurm` |
| 7 | Tests or CI that check answers | 2 | `.github/workflows/upwelling.yml` runs `scripts/ci_upwelling.sh`: regression test and restart test against `tests/upwelling/reference_energy_gfortran.txt`; the same tests on Amarel with `tests/upwelling/submit.sh` |
| 8 | Per-run record of code and settings | 2 | `receipt.txt`, `receipt_node.txt`, `blueprint.lock.yaml`, `executable.sha256`, `seg_NN/restart.sha256` in every run directory; `scripts/verify_run.sh` checks them |
| 9 | Documentation an outsider can follow | 2 | `REPRODUCIBILITY.md`, `tests/upwelling/README.md`, `docs/README.md` and the docs it links |
| 10 | Licence and citable release | 1 | `LICENSE`, `CITATION.cff`. No tagged release or DOI yet |
| | **Total** | **18** | |

## What the remaining two points need

- **Criterion 10 (one point):** tag a release and archive it on Zenodo. The
  steps are under "Releases and citing" in
  [REPRODUCIBILITY.md](../REPRODUCIBILITY.md). This needs a push and a
  GitHub-side setting, so it is done by a person, not a script.
- **Criterion 3 (one point):** scripts that build the grid, the initial and
  boundary files and the forcing files (milestones P1-M1 and P1-M3 to
  P1-M6 of the [roadmap](01-roadmap.md)). This is the project's own work; the score
  moves when those scripts are committed and listed in the `made_by` column
  of `inputs.tsv`.

Two caveats on the 18:

- Criterion 2 is scored on the test application. The Moana header and `.in`
  file do not exist yet.
- Criterion 3 gets its point from a script that fetches a published file,
  not one that generates an input. A strict reading would score it 0.

## Where each practice came from

| Practice | Borrowed from | Here |
|---|---|---|
| One file that says what the application is, checked against the real files | C-Star blueprints | `blueprint.yaml`, `scripts/check_blueprint.sh`, `blueprint.lock.yaml` |
| Hash the executable and the restart files; refuse to run on a mismatch | ACCESS-NRI access-om3-configs (payu manifests) | `executable.sha256`, `seg_NN/restart.sha256`, checked by every segment |
| Restart chaining by editing a copy of the `.in` file per segment | LiveOcean `dot_in`, ACCESS roms-configs `set_ininame.sh` | `in_set` in `scripts/run_lib.sh`, used by the job script |
| Restart-reproducibility test: chained segments must equal one run | ACCESS-NRI model-config-tests | `tests/upwelling/submit.sh --segments 2`, and in CI |
| CI with one reference answer per compiler, in a locked environment | ucla-roms, CEFI-regional-MOM6 | `.github/workflows/upwelling.yml`, `reference_energy_gfortran.txt`, `env/ci_gfortran.lock.txt` |
| Citable metadata | access-om3-configs | `CITATION.cff` |

Re-score this page whenever one of the files in the Evidence column is
added, removed or renamed.
