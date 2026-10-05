# Environment

**Last updated:** 2026-10-05

Where each part of the software environment is defined. The files are the
home of the facts; this page only points to them. How they fit together is
explained in [REPRODUCIBILITY.md](../../REPRODUCIBILITY.md).

| What | Where | Notes |
|---|---|---|
| Cluster | Amarel (Rutgers) | Compute nodes have no git: submit from a login node |
| ROMS source | `roms/` submodule, commit in `Apps/moana/blueprint.yaml` | Upstream [myroms/roms](https://github.com/myroms/roms) |
| Modules (compiler, MPI, NetCDF, NCO) | `env/amarel.sh` | Intel oneAPI `ifx`, Intel MPI, NetCDF-C/Fortran; exact versions in the file |
| Build | `scripts/build_roms.sh <app_dir>` | Reads `MOANA_FORT`, `MOANA_MPI` from `env/amarel.sh` |
| Python tools | `env/moana_python.yml`, `env/moana_python.lock.txt` | Conda env `moana_python` |
| CI toolchain | `env/ci.sh`, `env/ci_gfortran.yml`, `env/ci_gfortran.lock.txt` | gfortran, MPICH, conda-forge NetCDF |
| CI workflow | `.github/workflows/upwelling.yml` | Runs `scripts/ci_upwelling.sh` on every push |
| Input data folder | `$MOANA_DATA` | ❓ UNKNOWN: not set in `env/amarel.sh` yet (P1-M0-T08) |
| DataMesh token | `$DATAMESH_TOKEN` | Never in git, job scripts or receipts |
| Published (NeSI) build | `Apps/moana/roms_config.sh` | Reference only; see [model-config](model-config.md#published-build-settings-roms_configsh) |
