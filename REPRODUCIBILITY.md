# Reproducibility guide

This page explains, in plain terms, how this repository makes sure a model
run can be repeated later (by you, a colleague, or a reviewer) and get the
same result.

## The idea

A ROMS run depends on four things. If any one of them changes, the results
can change:

| # | Ingredient | Example |
|---|---|---|
| 1 | The **ROMS source code** | the Fortran model itself |
| 2 | **Our configuration** | CPP options (`.h`), input files (`.in`), build and job scripts |
| 3 | The **software environment** | compiler, MPI, NetCDF versions on the cluster |
| 4 | The **input data** | grid, initial, boundary, forcing and observation files |

This repository records each of these so it can be recreated exactly.

## How each ingredient is recorded

**1. ROMS source code: a "bookmark", not a copy**

The `roms/` folder is a *git submodule*. Instead of storing thousands of ROMS
files, this repository stores a bookmark to one exact version (commit) of the
official ROMS repository, [myroms/roms](https://github.com/myroms/roms).
Anyone who clones this repository gets that same version of ROMS.

- ROMS is only upgraded when someone deliberately moves the bookmark and
  commits that change, so the history shows exactly when it happened.
- Don't edit files inside `roms/`. Those edits are *not* saved in this
  repository. If ROMS itself needs changes, ask how to set up a fork first.

**2. Our configuration: saved in git**

Everything we write lives in `Apps/<application>/` (for example
`Apps/moana/`) and in `scripts/`, and is tracked by git like normal code.

Every application folder has the same files, named after the application:

| File | What it is |
|---|---|
| `<app>.h` | CPP options: which physics and features ROMS compiles in |
| `roms_<app>.in` | run parameters: grid size, time step, tiling, file names |
| `run_<app>.slurm` | the job: build, run, check |
| `inputs.tsv` | the input data manifest (see 4 below); not needed if there are no input files |

`tests/upwelling/` is a complete, working example of this layout.
(`Apps/moana/` has only `inputs.tsv` so far; its `.h`, `.in` and job
files are still to be written.) To set up a new application (another
region, or a Moana variant), copy it and change those files. The folder name
is the application name: `scripts/build_roms.sh Apps/moana` builds
`ROMS_APPLICATION=MOANA` from `Apps/moana/moana.h`.

There is one build script for every application, `scripts/build_roms.sh`,
so the compiler settings cannot drift apart between applications. It always
builds the pinned `roms/` (the upstream `-b <branch>` option was removed
because it could build some other ROMS version). It puts the build
(`Build_romsM/`) and executable (`romsM`) in the directory it is run from,
normally a run directory, so application folders only hold configuration.

**3. Software environment: one file lists the modules**

`env/amarel.sh` lists the cluster modules we use, with exact version numbers
(for example `nco/5.3.9`, not just `nco`). Loading this file before working
means everyone uses the same compiler and libraries.

On Amarel the toolchain is Intel oneAPI 2025.3 (`ifx` compiler) with Intel
MPI 2021.17 and NetCDF-C 4.10.0 / NetCDF-Fortran 4.6.3. These are the only
NetCDF modules on Amarel, and they only load together with that compiler and
MPI. `scripts/build_roms.sh` is set to match (`FORT=ifx`,
`which_MPI=oneapi`); if you change one, change the other.

Python tools (pre/post-processing and plots) use the `moana_python` conda
environment. `env/moana_python.yml` lists the packages we ask for (xroms,
xarray, matplotlib, cmocean, ...), and `env/moana_python.lock.txt` records
the exact versions that were installed, so the same environment can be
rebuilt on any Linux x86-64 machine:

```bash
conda create -n moana_python --file env/moana_python.lock.txt   # exact
conda env create -f env/moana_python.yml                        # or latest
```

The receipt (below) records a checksum of the active conda environment. It
equals `grep -v '^#' env/moana_python.lock.txt | sha256sum` when the
environment matches the lock file exactly.

**4. Input data: a manifest with checksums**

NetCDF (`*.nc`) files are too large for git, so they are ignored. Instead,
each application lists its input files in `<app>/inputs.tsv`, one line
per file:

| Column | Example |
|---|---|
| `sha256` | output of `sha256sum <file>`: a fingerprint of the file contents |
| `path` | absolute, or relative to `$MOANA_DATA` |
| `source` | where it came from (URL, product name) |
| `version_or_date` | product version or download date |
| `made_by` | the script in this repository that made or fetched it |

`scripts/check_inputs.sh Apps/moana/inputs.tsv` checks every file and
reports `OK`, `MISSING` or `CHANGED`. Submitting a run does this
automatically and refuses to submit if anything is missing or changed, so
a run can't silently use a different grid or forcing file. When you add or
regenerate an input file, update its line and commit.

**The receipt: `scripts/record_env.sh`**

This script prints a short "receipt" of the exact state used: the commit of
this repository, the ROMS version, any unsaved changes, the CPU, the loaded
modules, the active conda environment, and the compiler/MPI/NetCDF
versions. It's the note that lets you rebuild that run later.

You don't normally run it by hand: `scripts/submit_run.sh` (next section)
writes one into every run directory, and adds the checksums of the
configuration files and input data. The job adds a second one from the
compute node (`receipt_node.txt`) with the compiler flags and MPI tiling.

**Submitting a run: `scripts/submit_run.sh <app_dir>`**

This is how every job is submitted, on a login node. It:

1. **refuses to run from uncommitted or untracked changes**, so every run
   traces back to a commit (`--allow-dirty` overrides this for a throwaway
   test, and the receipt says so);
2. makes `<app_dir>/run_<date>_<time>/` and **copies the exact code**
   (this repository and ROMS) into its `src/` folder. The job builds and
   runs from that copy, so editing files, switching branches or updating
   `roms/` while a job waits in the queue can't change what it runs;
3. writes the receipt, checks the input data, and submits
   `<app_dir>/run_<app>.slurm`.

## What's where

```
Moana-2.0/
├── roms/                  ROMS source (submodule: a bookmark to one version)
├── Apps/moana/            our model configuration and input data manifest
├── env/amarel.sh          the list of cluster modules to load
├── env/moana_python.*     the Python environment (package list + exact lock)
├── scripts/build_roms.sh  builds ROMS for any application folder
├── scripts/submit_run.sh  checks, copies the code, writes the receipt, submits
├── scripts/record_env.sh  writes the "receipt" for a build or run
├── scripts/check_inputs.sh  checks input files against inputs.tsv
├── scripts/compare_energy.sh  regression check: energy vs. reference, within tolerance
├── scripts/plot_upwelling.py  figures from an UPWELLING test run
├── tests/upwelling/       toolchain and regression test (step-by-step guide in its README), template for a new application
├── .gitignore             keeps big/generated files (builds, *.nc) out of git
└── .gitmodules            where the ROMS bookmark points
```

## How to reproduce

### First time: get the code

```bash
git clone --recurse-submodules git@github.com:Ocean-Atmosphere-modeling/Moana-2.0.git
cd Moana-2.0
```

If you already cloned without `--recurse-submodules` and `roms/` is empty:

```bash
git submodule update --init
```

### Every time: load the environment

```bash
source env/amarel.sh                 # load the exact modules
```

Commit your changes, then submit with `scripts/submit_run.sh <app_dir>`
(it refuses if anything is uncommitted and writes the receipt for you).

### Check the toolchain works (UPWELLING test)

Before building Moana, or after changing modules or the ROMS version, run
the stock ROMS UPWELLING case. It needs no input data, so it only tests that
the compiler, MPI and NetCDF work together with our ROMS version, and that
they still give the same answer:

```bash
tests/upwelling/submit.sh
```

Run it on a login node: Amarel compute nodes have no git, so the receipt
(code versions and modules) is written there before submitting. The job
builds ROMS, runs it on 4 MPI ranks, and ends with `PASS` or `FAIL` in its
`slurm-<jobid>.out`. Everything for that test (receipt, code copy, build
log, ROMS log, the `.in` file used, NetCDF output) is in
`tests/upwelling/run_<date>_<time>/`, which git ignores.

`PASS` means more than "it ran": the energy diagnostics ROMS prints every
time step must match `tests/upwelling/reference_energy.txt` within a small
tolerance (the `# rtol:` line in that file), checked by
`scripts/compare_energy.sh`. Time steps and dates must match exactly.

Why a tolerance and not exact digits? Different CPU types (Amarel has
several, and AWS has others) take slightly different paths through the
math library, so the last digits can differ even with the same code and
modules. (In practice, the four Amarel CPU types we tried gave identical
digits.) The tolerance, about the 7 digits ROMS prints, leaves room for
other machines while still catching real changes: raising the viscosity
by 1% fails the test. Each run records how close it came in
`receipt_node.txt`; the reference file explains how the tolerance was set.

If you change the ROMS version, modules or build options and the numbers
move beyond the tolerance, the test fails and shows the difference. If the change is expected,
check the new run and update the reference as explained at the top of that
file, with a commit message saying why the results changed.

To check the output looks physically right, make the figures (domain,
forcing and boundary conditions, surface currents, SST/SSS, sections and
profiles) into `tests/upwelling/results/`:

```bash
conda activate moana_python
python scripts/plot_upwelling.py tests/upwelling/run_<date>_<time>
```

[tests/upwelling/README.md](tests/upwelling/README.md) walks through the
test step by step and shows what each figure should look like.

### Repeating an old run

The quickest way is to rebuild from the run's own code copy, `src/`,
which is exactly what that job ran. To go back through git instead, open
that run's `receipt.txt` and find the `moana-2.0:` commit line under
"Code copy used by the job". Then:

```bash
git checkout <commit-from-receipt>
git submodule update                 # moves roms/ to the version used then
source env/amarel.sh                 # loads the modules used then
```

Compare the modules and versions in a fresh receipt with the old one, and
check the input data with `scripts/check_inputs.sh`. If they match, you're
running the same model setup.

## Simple rules

1. **Commit before you run.** `scripts/submit_run.sh` enforces this.
2. **Submit every run with `scripts/submit_run.sh`**, which keeps a receipt
   and a copy of the code with it.
3. **Don't edit inside `roms/`.** Change our files in `Apps/` instead.
4. **Change modules only in `env/amarel.sh`**, with exact versions, and
   commit that change. Then run the UPWELLING test.
5. **List every input file in `inputs.tsv`**, with its checksum and where
   it came from.
