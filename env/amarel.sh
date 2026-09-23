#!/bin/bash
# Moana-2.0 software environment on Amarel (Rutgers).
# Usage:  source env/amarel.sh
#
# This is the single place to declare the modules the project depends on.
# Pin exact versions (name/version, never a bare name) so builds are
# reproducible, and commit any change to this file.

module purge

module load nco/5.3.9

# ROMS toolchain -- uncomment/adjust once chosen (see `module spider <name>`):
# module load intel/18.0.5         # or gcc/...
# module load openmpi/2.1.1        # or mvapich2/...
# module load netcdf-c/4.10.0
# module load netcdf-fortran/4.6.3
