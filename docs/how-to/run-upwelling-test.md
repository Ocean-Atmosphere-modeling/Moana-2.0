# How to run the UPWELLING toolchain test

**Goal:** a `PASS` showing the compiler, MPI, NetCDF and pinned ROMS still give the reference answer.
**Time:** ❓ UNKNOWN (one short SLURM job)

Run it before building Moana, and after any change to modules, ROMS version or build options.
The full walk-through with expected figures is [tests/upwelling/README.md](../../tests/upwelling/README.md).
Why it uses a tolerance: [REPRODUCIBILITY.md](../../REPRODUCIBILITY.md).

## Prerequisites
- Amarel login node (compute nodes have no git)
- Repository cloned with `--recurse-submodules`

## Steps
1. Load the environment.
   ```bash
   source env/amarel.sh
   ```
2. Submit the regression test.
   ```bash
   tests/upwelling/submit.sh
   ```
3. To also test restarts, submit the two-segment version.
   ```bash
   tests/upwelling/submit.sh --segments 2
   ```

## Check it worked
The last lines of `tests/upwelling/run_<date>_<time>/slurm-<jobid>.out` (for
`--segments 2`, the second segment's output) say `PASS`. Add a row to the
[run log](../experiments/run-log.md).

## If it goes wrong
| Symptom | Likely cause | Fix |
|---|---|---|
| `FAIL: N value(s) outside the tolerance` | Modules, ROMS version or build options changed the answer | If expected, update the reference as explained at the top of `tests/upwelling/reference_energy.txt` and say why in the commit |
| Submit refuses: uncommitted changes | Working tree not committed | Commit first |
| Blueprint check fails | `blueprint.yaml` disagrees with files or `roms/` | Fix the blueprint |
