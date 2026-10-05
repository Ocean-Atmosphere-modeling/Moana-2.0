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
| `blueprint.yaml` | what defines the application, in one file (see below) |
| `<app>.h` | CPP options: which physics and features ROMS compiles in |
| `roms_<app>.in` | run parameters: grid size, time step, tiling, file names |
| `run_<app>.slurm` | the job: build, run, check |
| `inputs.tsv` | the input data manifest (see 4 below); not needed if there are no input files |

`tests/upwelling/` is a complete, working example of this layout.
(`Apps/moana/` has only `blueprint.yaml` and `inputs.tsv` in git so far; its
`.h`, `.in` and job files are still to be written. Unmodified copies of the
published `roms3d.h`, `roms.in` and `roms_config.sh` may sit beside them as
references; they are not committed, see
[docs/reference/model-config.md](docs/reference/model-config.md).) To set up a new application (another
region, or a Moana variant), copy it and change those files. The folder name
is the application name: `scripts/build_roms.sh Apps/moana` builds
`ROMS_APPLICATION=MOANA` from `Apps/moana/moana.h`.

There is one build script for every application, `scripts/build_roms.sh`,
so the compiler settings cannot drift apart between applications. It always
builds the pinned `roms/` (the upstream `-b <branch>` option was removed
because it could build some other ROMS version). It puts the build
(`Build_romsM/`) and executable (`romsM`) in the directory it is run from,
normally a run directory, so application folders only hold configuration.

**The blueprint: one file that says what the application is**

`<app>/blueprint.yaml` names everything that defines the application: the
ROMS commit, the CPP header, the `.in` file, the job script, the input data
manifest, how many segments a run has, and the test references. It is short
enough to read in a minute, and it is the first file to open in any
application folder. (The idea is borrowed from the C-Star blueprints.)

A description like this is only useful if it stays true, so
`scripts/check_blueprint.sh <app_dir>` compares it with the real files and
with the pinned `roms/` commit. Submitting a run does this automatically and
refuses to submit if they disagree; the automated test checks every
blueprint on every push. Moving the ROMS bookmark therefore takes two
deliberate edits: the submodule and the blueprint.

A blueprint with `state: draft` (like `Apps/moana/` today) may point to
files that are not written yet; they are listed as `TODO`. Change it to
`validated` once the application has been compared with something.

**3. Software environment: one file lists the modules**

`env/amarel.sh` lists the cluster modules we use, with exact version numbers
(for example `nco/5.3.9`, not just `nco`). Loading this file before working
means everyone uses the same compiler and libraries.

On Amarel the toolchain is Intel oneAPI 2025.3 (`ifx` compiler) with Intel
MPI 2021.17 and NetCDF-C 4.10.0 / NetCDF-Fortran 4.6.3. These are the only
NetCDF modules on Amarel, and they only load together with that compiler and
MPI. The same file sets `MOANA_FORT=ifx` and `MOANA_MPI=oneapi`, which tell
`scripts/build_roms.sh` which compiler to build with, so the modules and the
build cannot disagree.

GitHub's machines do not have the Intel toolchain, so the automated test
(below) uses a second environment: gfortran, MPICH and NetCDF-Fortran from
conda-forge. `env/ci_gfortran.yml` lists the packages,
`env/ci_gfortran.lock.txt` the exact versions, and `env/ci.sh` plays the
part of `env/amarel.sh`. It also works on a laptop or on AWS.

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
compute node (`receipt_node.txt`) with the compiler flags, MPI tiling and
the sha256 of the executable it built (also kept as `executable.sha256`).

The receipt is written for people. The same facts are written for scripts
as `blueprint.lock.yaml`: the blueprint with every pointer replaced by the
commit or sha256 it resolved to. `scripts/verify_run.sh <run_dir>` reads it
and checks that the code copy, the executable, the restart files and the
input data are still exactly what the run used.

**Submitting a run: `scripts/submit_run.sh <app_dir>`**

This is how every job is submitted, on a login node. It:

1. **refuses to run from uncommitted or untracked changes**, so every run
   traces back to a commit (`--allow-dirty` overrides this for a throwaway
   test, and the receipt says so);
2. makes `<app_dir>/run_<date>_<time>/` and **copies the exact code**
   (this repository and ROMS) into its `src/` folder. The job builds and
   runs from that copy, so editing files, switching branches or updating
   `roms/` while a job waits in the queue can't change what it runs;
3. checks the blueprint, writes the receipt, checks the input data, and
   submits `<app_dir>/run_<app>.slurm`.

**Long runs: a chain of segments (`--segments N`)**

A 28-year hindcast cannot run as one job. `scripts/submit_run.sh <app_dir>
--segments N` submits N jobs that share one run directory, one code copy
and one executable. Each job starts only when the one before has finished
successfully, and continues from the restart file it wrote. If a segment
fails, the rest of the chain is cancelled.

Two things keep a chain honest:

- **the executable is built once**, by the first segment, and its sha256 is
  recorded. Every later segment checks it and refuses to run if it differs;
- **every segment records the sha256 of the restart file it writes**
  (`seg_NN/restart.sha256`), and the next segment checks that file before
  reading it. A restart file that was replaced, truncated or regenerated
  stops the chain instead of silently changing the answer.

Chained runs are built with the `PERFECT_RESTART` option, which makes ROMS
save everything it needs to carry on as if it had not stopped. The restart
test below checks that this is true.

## What's where

```
Moana-2.0/
├── roms/                  ROMS source (submodule: a bookmark to one version)
├── Apps/moana/            our model configuration: blueprint and input data manifest
├── env/amarel.sh          the list of cluster modules to load
├── env/ci.sh, env/ci_gfortran.*  the GNU toolchain for the automated test (list + exact lock)
├── env/moana_python.*     the Python environment (package list + exact lock)
├── scripts/build_roms.sh  builds ROMS for any application folder
├── scripts/submit_run.sh  checks, copies the code, writes the receipt, submits (one job or a chain)
├── scripts/record_env.sh  writes the "receipt" for a build or run
├── scripts/check_blueprint.sh  checks an application's blueprint against its files
├── scripts/check_inputs.sh  checks input files against inputs.tsv
├── scripts/verify_run.sh  checks an old run directory against its record
├── scripts/run_lib.sh     small functions the scripts above share
├── scripts/fetch_published_config.sh  fetches the published Moana grid and configuration
├── scripts/ci_upwelling.sh  the automated test: regression and restart tests without SLURM
├── .github/workflows/     runs that test on GitHub for every push
├── CITATION.cff           how to cite this repository
├── scripts/compare_energy.sh  regression check: energy vs. reference, within tolerance
├── scripts/plot_upwelling.py  figures from an UPWELLING test run
├── docs/                  project docs: start at docs/README.md (brief, roadmap, decisions, reference)
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

### Check a restart does not change the answer (restart test)

The hindcast will run as a long chain of jobs, each continuing from the
restart file of the one before. That only reproduces a single long run if
stopping and restarting changes nothing. To test it:

```bash
tests/upwelling/submit.sh --segments 2
```

This runs the same UPWELLING case as two chained jobs (`seg_01/`,
`seg_02/` in the run directory). The second job checks the executable and
the restart file against their recorded sha256, continues from the restart
file, and then compares the energy of the whole chain with the same
single-run reference. `PASS` (at the end of the second job's
`slurm-<jobid>.out`) means two half runs gave the same answer as one full
run. Run it after changing the ROMS version, the modules, or anything about
how runs are chained.

This test is stricter than the regression test: every printed digit must
match (`test.restart_rtol: 0` in the blueprint). It has to be, because a
restart that is not exact changes very little: the same chain built without
`PERFECT_RESTART` moved kinetic energy by 4e-7, which the regression
tolerance of 1e-6 would let through.

### The automated test (GitHub Actions)

Every push and pull request runs `.github/workflows/upwelling.yml` on
GitHub. It checks every blueprint, builds the pinned ROMS with the GNU
toolchain in `env/ci_gfortran.lock.txt`, and runs both tests above (the
regression test against `tests/upwelling/reference_energy_gfortran.txt`,
then the two-segment restart test against that single run). A red cross on a commit
means that commit changes the model's answer or breaks the build.

It does not replace the Amarel test: the hindcast is built with Intel
`ifx`, which only the Amarel test exercises. To run the automated test by
hand (on Amarel, inside a job, not on a login node):

```bash
conda create -n moana_ci --file env/ci_gfortran.lock.txt    # once
conda activate moana_ci
scripts/ci_upwelling.sh
```

### Get the published Moana configuration

```bash
export MOANA_DATA=<input data folder>
scripts/fetch_published_config.sh
```

downloads the authors' archive from Zenodo, checks its sha256, and unpacks
the published grid, `roms.in` and CPP header into
`$MOANA_DATA/published/moana_hindcast_v1.0/`. The grid is listed in
`Apps/moana/inputs.tsv`, so `scripts/check_inputs.sh` reports it `OK`
afterwards.

### Repeating an old run

First check the run directory still holds what the run used:

```bash
scripts/verify_run.sh <app_dir>/run_<date>_<time>
```

The quickest way is then to rebuild from the run's own code copy, `src/`,
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

## Releases and citing

`CITATION.cff` says how to cite this repository (GitHub shows it as "Cite
this repository"). A result that goes into a paper or a report should come
from a tagged release, so the code behind it has a name and a DOI:

1. update `version` and `date-released` in `CITATION.cff` and commit;
2. tag it and push the tag: `git tag -a v0.1.0 -m "..."`, `git push origin v0.1.0`;
3. make a GitHub release from the tag. With the repository switched on at
   <https://zenodo.org/account/settings/github/>, Zenodo archives each
   release and gives it a DOI; add that DOI to `CITATION.cff` and the README.

Run receipts record the commit, so any run made from a tagged commit can be
cited by its release.

How this repository scores against other ocean-model repositories, and the
file that backs each point, is in
[docs/reproducibility_score.md](docs/reproducibility_score.md).

## Simple rules

1. **Commit before you run.** `scripts/submit_run.sh` enforces this.
2. **Submit every run with `scripts/submit_run.sh`**, which keeps a receipt
   and a copy of the code with it.
3. **Don't edit inside `roms/`.** Change our files in `Apps/` instead.
4. **Change modules only in `env/amarel.sh`**, with exact versions, and
   commit that change. Then run the UPWELLING test.
5. **List every input file in `inputs.tsv`**, with its checksum and where
   it came from.
6. **Keep `blueprint.yaml` true.** When a file it names changes name, or the
   ROMS bookmark moves, change the blueprint in the same commit.
7. **Never replace a restart file inside a chain.** Start a new run instead;
   the chain refuses a restart file it did not write.
