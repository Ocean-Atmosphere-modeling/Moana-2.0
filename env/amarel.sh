#!/bin/bash
# Moana-2.0 software environment on Amarel (Rutgers).
# Usage:  source env/amarel.sh
#
# This is the single place to declare the modules the project depends on.
# Pin exact versions (name/version, never a bare name) so builds are
# reproducible, and commit any change to this file.
#
# On Amarel the NetCDF-Fortran module is only built for the Intel oneAPI
# compiler (ifx) with Intel MPI, so that is the ROMS toolchain.
# MOANA_FORT and MOANA_MPI below tell scripts/build_roms.sh to use it.

module purge

# ROMS toolchain (load order matters: netcdf-* depend on oneapi + impi).
module load oneapi/2025.3.0
module load impi/2021.17
module load netcdf-c/4.10.0
module load netcdf-fortran/4.6.3

# Pre/post-processing tools.
module load nco/5.3.9

# Compiler and MPI for scripts/build_roms.sh (FORT and which_MPI).
export MOANA_FORT=ifx
export MOANA_MPI=oneapi
