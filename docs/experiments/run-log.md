# Run log

One row per model run, newest first. The run directory's `receipt.txt` is the
full record; this table is the index. Git commit is the repository HEAD at
submit time, then (in brackets) the code-copy snapshot the job actually ran;
all runs below were submitted with uncommitted changes present.

No Moana runs yet. UPWELLING runs: config `tests/upwelling/roms_upwelling.in`
(`NTIMES = 1440`, `DT = 300 s`, so 5 days), 4 MPI ranks, Amarel.

| Run ID | Date | Git commit | Config file | Period simulated | Purpose | Result / skill | Output path | Notes |
|---|---|---|---|---|---|---|---|---|
| upwelling_20261001_203127 | 2026-10-01 | 0f4677a (402e8f7) | `roms_upwelling.in` | 5 days, 2 segments | Restart test, exact | PASS (tolerance 0) | `tests/upwelling/run_20261001_203127/` | `PERFECT_RESTART` chain |
| upwelling_20261001_201504 | 2026-10-01 | 0f4677a (348ec84) | `roms_upwelling.in` | 5 days, 2 segments | Restart test | PASS within tolerance | `tests/upwelling/run_20261001_201504/` | |
| upwelling_20261001_201453 | 2026-10-01 | 0f4677a (af75057) | `roms_upwelling.in` | 5 days | Regression test | PASS within tolerance | `tests/upwelling/run_20261001_201453/` | |
| upwelling_20260924_164034 | 2026-09-24 | ed9c32b (fd0d0c9) | `roms_upwelling.in` | 5 days | Tolerance sensitivity check | FAIL: 1016 values outside tolerance (expected) | `tests/upwelling/run_20260924_164034/` | Job 61833233, viscosity +1 % (see `reference_energy.txt`) |
| upwelling_20260924_164012 | 2026-09-24 | ed9c32b (11c7d01) | `roms_upwelling.in` | 5 days | Regression test | PASS within tolerance | `tests/upwelling/run_20260924_164012/` | |
| upwelling_20260924_163128 | 2026-09-24 | ed9c32b | `roms_upwelling.in` | 5 days | Regression test | PASS | `tests/upwelling/run_20260924_163128/` | ❓ UNKNOWN: why three runs at 16:31 (CPU types?) |
| upwelling_20260924_163122 | 2026-09-24 | ed9c32b | `roms_upwelling.in` | 5 days | Regression test | PASS | `tests/upwelling/run_20260924_163122/` | |
| upwelling_20260924_163102 | 2026-09-24 | ed9c32b | `roms_upwelling.in` | 5 days | Regression test | PASS | `tests/upwelling/run_20260924_163102/` | |
| upwelling_20260924_151928 | 2026-09-24 | 8c99887 | `roms_upwelling.in` | 5 days | Regression test | PASS | `tests/upwelling/run_20260924_151928/` | |
| upwelling_20260923_211406 | 2026-09-23 | 4dbe8d5 | `roms_upwelling.in` | 5 days | First toolchain test | PASS (built and ran) | `tests/upwelling/run_20260923_211406/` | No reference comparison yet |
