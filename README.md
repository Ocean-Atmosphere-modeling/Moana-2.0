# Moana-2.0
Adding data assimilation to an ocean model for the New Zealand region in a private sector partnership

## Reproducibility

- **ROMS source** is the `roms` git submodule, pinned to a specific commit of
  [myroms/roms](https://github.com/myroms/roms). Clone with
  `git clone --recurse-submodules <url>` (or run `git submodule update --init`).
  To upgrade ROMS: `cd roms && git fetch && git checkout <commit>`, then
  commit the new pointer in this repo.
- **Software modules** are declared with pinned versions in `env/amarel.sh`;
  run `source env/amarel.sh` before building or running.
- **Environment record**: `scripts/record_env.sh [file]` writes the repo and
  ROMS commits, loaded modules, and compiler/MPI/NetCDF versions. Save it
  alongside every build or run.
- **Configuration** (CPP headers, `.in` files, build/job scripts) lives in
  `Apps/<application>/`. Build products and NetCDF files are git-ignored.
