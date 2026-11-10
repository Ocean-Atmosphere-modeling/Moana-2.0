#!/bin/bash
# Build ROMS for one application, from the pinned "roms" submodule.
#
# Usage:  scripts/build_roms.sh <app_dir> [-j N] [-g] [-noclean]
#
#   <app_dir>   application folder holding <app>.h, e.g. Apps/moana
#               (the header may be in <app_dir> or <app_dir>/Include)
#   -j N        compile with N parallel jobs (default 1)
#   -g          debug build (romsG, slow, with checks)
#   -noclean    keep already compiled objects
#
# The build goes in the directory you run this from: Build_romsM/ and romsM.
# Run it from a run directory, not from Apps/moana.
#
# Environment hooks (all optional):
#   MOANA_FORT, MOANA_MPI   compiler and MPI family; set by env/amarel.sh
#                           (ifx + oneapi) or env/ci.sh (gfortran + mpich).
#                           If unset, env/amarel.sh is sourced here.
#   MOANA_CPP_FLAGS         extra CPP options, e.g. -DPERFECT_RESTART for a
#                           chained run (see Apps/moana/blueprint.yaml).
#   ROMS_APPLICATION        override the name taken from the folder name.

# ---- 1. Arguments ---------------------------------------------------------
if [ $# -lt 1 ] || [ ! -d "$1" ]; then
  echo "Usage: $0 <app_dir> [-j N] [-g] [-noclean]"; exit 1
fi
APP_DIR=$(cd "$1" && pwd); shift

JOBS=1; DEBUG=0; CLEAN=1
while [ $# -gt 0 ]; do
  case "$1" in
    -j)       JOBS=$2; shift 2 ;;
    -g)       DEBUG=1; shift ;;
    -noclean) CLEAN=0; shift ;;
    *)        echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ---- 2. Where things are --------------------------------------------------
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)   # repository top
export MY_ROMS_SRC=${ROOT}/roms                          # pinned submodule
export COMPILERS=${MY_ROMS_SRC}/Compilers
export BINDIR=${PWD}                                     # executable goes here

# ---- 3. Toolchain ---------------------------------------------------------
if [ -z "${MOANA_FORT}" ]; then
  source "${ROOT}/env/amarel.sh"
fi
export FORT=${MOANA_FORT}
export which_MPI=${MOANA_MPI}
export USE_MPI=on
export USE_MPIF90=on
export USE_LARGE=on
export USE_NETCDF4=on        # nc-config / nf-config must be on PATH
export STATIC=on
export EXEC=on

# ---- 4. Application: name, header, extra CPP options ----------------------
export ROMS_APPLICATION=${ROMS_APPLICATION:-$(basename "${APP_DIR}" | tr '[:lower:]' '[:upper:]')}
HEADER=$(echo "${ROMS_APPLICATION}" | tr '[:upper:]' '[:lower:]').h

if   [ -f "${APP_DIR}/${HEADER}" ];         then export MY_HEADER_DIR=${APP_DIR}
elif [ -f "${APP_DIR}/Include/${HEADER}" ]; then export MY_HEADER_DIR=${APP_DIR}/Include
else
  echo "Header ${HEADER} not found in ${APP_DIR} or ${APP_DIR}/Include"; exit 1
fi
export MY_ANALYTICAL_DIR=${MY_HEADER_DIR}
export MY_CPP_FLAGS=${MOANA_CPP_FLAGS:-}

# ---- 5. Build directory and executable name -------------------------------
if [ ${DEBUG} -eq 1 ]; then
  export USE_DEBUG=on
  export BUILD_DIR=${BINDIR}/Build_romsG; EXE=${BINDIR}/romsG
else
  export BUILD_DIR=${BINDIR}/Build_romsM; EXE=${BINDIR}/romsM
fi
export SCRATCH_DIR=${BUILD_DIR}       # old name for BUILD_DIR
mkdir -p "${BUILD_DIR}"

# ---- 6. Compile -----------------------------------------------------------
echo "ROMS source:   ${MY_ROMS_SRC} ($(git -C "${MY_ROMS_SRC}" describe --tags --always))"
echo "Application:   ${ROMS_APPLICATION}"
echo "Header:        ${MY_HEADER_DIR}/${HEADER}"
echo "Compiler:      ${FORT} with ${which_MPI} MPI"
echo "Extra CPP:     ${MY_CPP_FLAGS:-(none)}"
echo "Build dir:     ${BUILD_DIR}"
echo "Executable:    ${EXE}"
echo

cd "${MY_ROMS_SRC}" || exit 1
if [ ${CLEAN} -eq 1 ]; then
  make clean
fi
make -j "${JOBS}" || { echo "FAIL: make"; exit 1; }

[ -x "${EXE}" ] || { echo "FAIL: ${EXE} was not created"; exit 1; }
echo
echo "Built ${EXE}"
echo "Fortran flags: $(make -s print-FFLAGS | cut -d ' ' -f 3-)"
