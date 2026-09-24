#!/bin/bash
#SBATCH --job-name=roms-upwelling
#SBATCH --partition=main
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#
# Toolchain and regression test: build and run the stock ROMS UPWELLING
# case with the pinned ROMS submodule and the modules in env/amarel.sh. It
# needs no input data (grid, initial conditions and forcing are analytical),
# so it checks that the compiler, MPI and NetCDF work together before
# building MOANA, and that they still give the same answer as before.
#
# This folder is laid out like any application in Apps/ and can be copied
# as a template:
#   upwelling.h             CPP options (what the model includes)
#   roms_upwelling.in       run parameters (grid size, time step, tiling, files)
#   run_upwelling.slurm     this job: build, run, check
#   submit.sh               submits this job (scripts/submit_run.sh)
#   reference_energy.txt    expected energy diagnostics (regression check)
#
# Submit it with tests/upwelling/submit.sh. That writes the receipt on the
# login node (compute nodes have no git), copies the code to
# tests/upwelling/run_<date>_<time>/src and runs this job in that run
# directory. The job builds from src/, so nothing changed in the repository
# after submitting affects it. It puts the build, executable, input file,
# logs and NetCDF output in the run directory, and exits non-zero if the
# build fails, ROMS does not finish cleanly, or the results differ from
# reference_energy.txt.

set -euo pipefail

: "${SRC:?submit with tests/upwelling/submit.sh}"     # set by submit_run.sh
: "${APP:?submit with tests/upwelling/submit.sh}"     # set by submit_run.sh
APP_DIR=${SRC}/${APP}
RUN_DIR=${PWD}                                        # set by submit_run.sh

set +u                                 # module scripts use unset variables
source "${SRC}/env/amarel.sh"
set -u

# Toolchain as seen on the compute node (the full receipt is receipt.txt).
"${SRC}/scripts/record_env.sh" receipt_node.txt

# Build. scripts/build_roms.sh puts Build_romsM/ and romsM in the current directory.
"${SRC}/scripts/build_roms.sh" "${APP_DIR}" -j "${SLURM_NTASKS:-4}" \
  > build.log 2>&1 || { tail -50 build.log; echo "FAIL: build"; exit 1; }
[ -x romsM ] || { tail -50 build.log; echo "FAIL: romsM not created"; exit 1; }

# Inputs: a copy of the .in file (kept with the output) and the ROMS
# variable metadata it refers to as "varinfo.yaml".
cp "${APP_DIR}/roms_upwelling.in" .
ln -sf "${SRC}/roms/ROMS/External/varinfo.yaml" varinfo.yaml

# One MPI rank per tile.
ntile () { awk -v k="$1" '$1 == k && $2 == "==" {print $3}' roms_upwelling.in; }
NP=$(( $(ntile NtileI) * $(ntile NtileJ) ))

# What the results depend on beyond the receipt: compiler flags and tiling
# (ROMS output can change with the domain decomposition).
{
  echo ""
  echo "## Build and run"
  grep -E '^(Fortran compiler|Fortran flags|ROMS Application):' build.log
  echo "tiling:  NtileI=$(ntile NtileI) NtileJ=$(ntile NtileJ) (${NP} MPI ranks)"
  echo "slurm:   job ${SLURM_JOB_ID:-?} on ${SLURM_JOB_NODELIST:-?}"
} >> receipt_node.txt

# Run.
status=0
mpirun -np ${NP} ./romsM roms_upwelling.in > roms.log 2>&1 || status=$?

if [ ${status} -ne 0 ] || ! grep -q 'ROMS: DONE' roms.log \
   || grep -qE 'ERROR:|Abnormal termination' roms.log; then
  tail -50 roms.log
  echo "FAIL: ROMS run (mpirun exit status ${status}), see ${RUN_DIR}/roms.log"
  exit 1
fi

# Regression check: the energy diagnostics ROMS prints every time step
# (step, date, kinetic, potential and total energy, volume) must match the
# reference exactly. The build uses -fp-model precise, so the same code,
# toolchain, CPU type and tiling reproduce them digit for digit.
num='[-+0-9.E]+'
grep -E "^ +[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:.]+ +${num} +${num} +${num} +${num} *$" \
  roms.log > energy.txt || true
if ! diff -q <(grep -v '^#' "${APP_DIR}/reference_energy.txt") energy.txt > /dev/null; then
  diff <(grep -v '^#' "${APP_DIR}/reference_energy.txt") energy.txt | head -20
  echo "FAIL: results differ from ${APP}/reference_energy.txt (see above)."
  echo "If the change is expected (new ROMS version, modules or options),"
  echo "check the run, then update the reference as described in that file."
  exit 1
fi

echo "PASS: UPWELLING built, ran on ${NP} MPI ranks and matched the reference"
echo "Output: ${RUN_DIR}"
ls -l *.nc
