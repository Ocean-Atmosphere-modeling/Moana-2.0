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

**3. Software environment: one file lists the modules**

`env/amarel.sh` lists the cluster modules we use, with exact version numbers
(for example `nco/5.3.9`, not just `nco`). Loading this file before working
means everyone uses the same compiler and libraries.

On Amarel the toolchain is Intel oneAPI 2025.3 (`ifx` compiler) with Intel
MPI 2021.17 and NetCDF-C 4.10.0 / NetCDF-Fortran 4.6.3. These are the only
NetCDF modules on Amarel, and they only load together with that compiler and
MPI. `Apps/moana/build_roms.sh` is set to match (`FORT=ifx`,
`which_MPI=oneapi`); if you change one, change the other.

**4. Input data: not in git (yet)**

NetCDF (`*.nc`) files are too large for git, so they are ignored. Record where
each input file came from (source, version, download date, and the script
that made it) so it can be fetched or regenerated.

**The receipt: `scripts/record_env.sh`**

This script prints a short "receipt" of the exact state used: the commit of
this repository, the ROMS version, any unsaved changes, the loaded modules,
and the compiler/MPI/NetCDF versions. Save one next to every build or run.
It's the note that lets you rebuild that run later.

## What's where

```
Moana-2.0/
├── roms/                  ROMS source (submodule: a bookmark to one version)
├── Apps/moana/            our model configuration and build script
├── env/amarel.sh          the list of cluster modules to load
├── scripts/record_env.sh  writes the "receipt" for a build or run
├── tests/upwelling/       toolchain check: builds and runs a stock ROMS case
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

### Every time: load the environment, then save a receipt

```bash
source env/amarel.sh                 # load the exact modules
scripts/record_env.sh my_receipt.txt # write down what was used
```

Check the receipt. If it says `WARNING: uncommitted changes present`,
commit your changes first so the run can be traced back to saved code.

### Check the toolchain works (UPWELLING test)

Before building Moana, or after changing modules or the ROMS version, run
the stock ROMS UPWELLING case. It needs no input data, so it only tests that
the compiler, MPI and NetCDF work together with our ROMS version:

```bash
sbatch tests/upwelling/run_upwelling.slurm
```

The job builds ROMS, runs it on 4 MPI ranks, and ends with `PASS` or `FAIL`
in its `slurm-<jobid>.out`. Everything it made (build log, ROMS log,
receipt, NetCDF output) is in `tests/upwelling/run_<jobid>/`, which git
ignores.

### Repeating an old run

Open that run's receipt and find the `moana-2.0:` commit line. Then:

```bash
git checkout <commit-from-receipt>
git submodule update                 # moves roms/ to the version used then
source env/amarel.sh                 # loads the modules used then
```

Compare the modules and versions in a fresh receipt with the old one. If
they match, and you use the same input data, you're running the same model
setup.

## Simple rules

1. **Commit before you run.** A run from uncommitted code can't be traced.
2. **Keep a receipt with every run** (`scripts/record_env.sh`).
3. **Don't edit inside `roms/`.** Change our files in `Apps/` instead.
4. **Change modules only in `env/amarel.sh`**, with exact versions, and
   commit that change.
5. **Write down where input data came from.**
