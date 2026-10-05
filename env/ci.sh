#!/bin/bash
# Moana-2.0 software environment for the automated test (GitHub Actions),
# or any Linux machine without the Amarel modules.
# Usage:  conda activate moana_ci && source env/ci.sh
#
# The toolchain (gfortran, MPICH, NetCDF-Fortran) comes from the moana_ci
# conda environment: env/ci_gfortran.yml lists the packages and
# env/ci_gfortran.lock.txt the exact versions. This file only checks that
# the environment is active and tells scripts/build_roms.sh which compiler
# to use.

for tool in gfortran mpif90 mpirun nf-config; do
  command -v ${tool} >/dev/null 2>&1 \
    || { echo "env/ci.sh: ${tool} not found; activate the moana_ci conda environment first"; return 1 2>/dev/null || exit 1; }
done

# Compiler and MPI for scripts/build_roms.sh (FORT and which_MPI).
export MOANA_FORT=gfortran
export MOANA_MPI=mpich
