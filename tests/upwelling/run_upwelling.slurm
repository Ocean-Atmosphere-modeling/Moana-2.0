#!/bin/bash
#SBATCH --job-name=roms-upwelling
#SBATCH --partition=main
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#
# Toolchain smoke test: build and run the stock ROMS UPWELLING case with the
# pinned ROMS submodule and the modules in env/amarel.sh. It needs no input
# data (grid, initial conditions and forcing are analytical), so it checks
# that the compiler, MPI and NetCDF work together before building MOANA.
#
# Submit it with tests/upwelling/submit.sh, which writes the code-version
# receipt on the login node (compute nodes have no git), then runs this job
# in a fresh tests/upwelling/run_<date>_<time>/ directory. The job puts the
# build, executable, input file, logs and NetCDF output there, and exits
# non-zero if the build fails or ROMS does not finish cleanly.

set -euo pipefail

: "${REPO:?submit with tests/upwelling/submit.sh}"   # set by submit.sh
RUN_DIR=${PWD}                                       # set by submit.sh
NTILEI=2
NTILEJ=2

set +u                                 # module scripts use unset variables
source "${REPO}/env/amarel.sh"
set -u

# Toolchain as seen on the compute node (the full receipt is receipt.txt).
"${REPO}/scripts/record_env.sh" receipt_node.txt

# Build. build_roms.sh puts Build_romsM/ and romsM in the current directory.
"${REPO}/Apps/moana/build_roms.sh" -app UPWELLING -j "${SLURM_NTASKS:-4}" \
  > build.log 2>&1 || { tail -50 build.log; echo "FAIL: build"; exit 1; }
[ -x romsM ] || { echo "FAIL: romsM not created"; exit 1; }

# Stock input file, with MPI tiling and absolute paths set for this run.
sed -e "s|^\( *NtileI *==\).*|\1 ${NTILEI}|" \
    -e "s|^\( *NtileJ *==\).*|\1 ${NTILEJ}|" \
    -e "s|ROMS/External/|${REPO}/roms/ROMS/External/|" \
    "${REPO}/roms/ROMS/External/roms_upwelling.in" > roms_upwelling.in

# Run.
status=0
mpirun -np $((NTILEI * NTILEJ)) ./romsM roms_upwelling.in > roms.log 2>&1 \
  || status=$?

if [ ${status} -ne 0 ] || ! grep -q 'ROMS: DONE' roms.log \
   || grep -qE 'ERROR:|Abnormal termination' roms.log; then
  tail -50 roms.log
  echo "FAIL: ROMS run (mpirun exit status ${status}), see ${RUN_DIR}/roms.log"
  exit 1
fi

echo "PASS: UPWELLING built and ran on $((NTILEI * NTILEJ)) MPI ranks"
echo "Output: ${RUN_DIR}"
ls -l *.nc
