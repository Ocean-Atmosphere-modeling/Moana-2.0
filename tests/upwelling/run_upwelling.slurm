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
#   blueprint.yaml          what defines the application, in one file
#   upwelling.h             CPP options (what the model includes)
#   roms_upwelling.in       run parameters (grid size, time step, tiling, files)
#   run_upwelling.slurm     this job: build, run, check
#   submit.sh               submits this job (scripts/submit_run.sh)
#   reference_energy*.txt   expected energy diagnostics, one file per compiler
#   reference_figures/      figures from the reference run (see README.md)
#   README.md               how to run this test and what the results should look like
#
# Submit it with tests/upwelling/submit.sh. That writes the receipt on the
# login node (compute nodes have no git), copies the code to
# tests/upwelling/run_<date>_<time>/src and runs this job in that run
# directory. The job builds from src/, so nothing changed in the repository
# after submitting affects it. It puts the build, executable, input file,
# logs and NetCDF output in the run directory, and exits non-zero if the
# build fails, ROMS does not finish cleanly, or the results differ from
# the reference.
#
# Restart test: "submit.sh --segments 2" runs the same case as a chain of
# jobs, each starting from the restart file the one before wrote (segment
# folders seg_01/, seg_02/). The energy of the whole chain must match the
# same single-run reference in every printed digit (test.restart_rtol in
# the blueprint), so a restart that changes the answer fails.
# Each segment refuses to start if the executable or the restart file it is
# about to read is not the one the chain recorded (sha256).

set -euo pipefail

: "${SRC:?submit with tests/upwelling/submit.sh}"     # set by submit_run.sh
: "${APP:?submit with tests/upwelling/submit.sh}"     # set by submit_run.sh
SEGMENT=${SEGMENT:-1}                                 # set by submit_run.sh --segments
NSEGMENTS=${NSEGMENTS:-1}
APP_DIR=${SRC}/${APP}
RUN_DIR=${PWD}                                        # set by submit_run.sh
IN=roms_upwelling.in

set +u                                 # module scripts use unset variables
source "${SRC}/${MOANA_ENV:-env/amarel.sh}"
set -u
source "${SRC}/scripts/run_lib.sh"

SEG_DIR=$(seg_dir "${RUN_DIR}" "${SEGMENT}" "${NSEGMENTS}")
mkdir -p "${SEG_DIR}"
cd "${SEG_DIR}"

# Toolchain as seen on the compute node (the full receipt is receipt.txt).
"${SRC}/scripts/record_env.sh" receipt_node.txt

# Build once, in the run directory (scripts/build_roms.sh puts Build_romsM/
# and romsM in the current directory), and record the executable's sha256.
# Later segments must find that same executable. A chained run is built with
# PERFECT_RESTART so the restart file holds everything ROMS needs to carry on
# as if it had not stopped (see the blueprint).
if [ "${SEGMENT}" -eq 1 ]; then
  [ "${NSEGMENTS}" -eq 1 ] \
    || export MOANA_CPP_FLAGS=$(bp_get "${APP_DIR}/blueprint.yaml" compile_time.chained_cpp_flags)
  ( cd "${RUN_DIR}"
    "${SRC}/scripts/build_roms.sh" "${APP_DIR}" -j "${SLURM_NTASKS:-4}" \
      > build.log 2>&1 || { tail -50 build.log; echo "FAIL: build"; exit 1; }
    [ -x romsM ] || { tail -50 build.log; echo "FAIL: romsM not created"; exit 1; }
    sha256sum romsM > executable.sha256 )
elif ! ( cd "${RUN_DIR}" && sha256sum --check --quiet executable.sha256 ); then
  echo "FAIL: romsM is not the executable segment 1 built (executable.sha256)"
  exit 1
fi

# Inputs: a copy of the .in file (kept with the output) and the ROMS
# variable metadata it refers to as "varinfo.yaml".
cp "${APP_DIR}/${IN}" .
ln -sf "${SRC}/roms/ROMS/External/varinfo.yaml" varinfo.yaml

# Chained run: split NTIMES evenly, write a restart file at the end of each
# segment, and start every segment after the first from the restart file of
# the one before, after checking it is the file that segment recorded.
restart_in="(none: first segment)"
if [ "${NSEGMENTS}" -gt 1 ]; then
  total=$(in_get "${IN}" NTIMES)
  if [ $(( total % NSEGMENTS )) -ne 0 ]; then
    echo "FAIL: NTIMES=${total} does not divide into ${NSEGMENTS} segments"; exit 1
  fi
  in_set "${IN}" NTIMES $(( total / NSEGMENTS ))
  in_set "${IN}" NRST   $(( total / NSEGMENTS ))
  if [ "${SEGMENT}" -gt 1 ]; then
    prev=$(seg_dir "${RUN_DIR}" $(( SEGMENT - 1 )) "${NSEGMENTS}")
    if ! ( cd "${prev}" && sha256sum --check --quiet restart.sha256 ); then
      echo "FAIL: restart file of segment $(( SEGMENT - 1 )) is missing or changed (${prev}/restart.sha256)"
      exit 1
    fi
    restart_in=$(cut -d' ' -f1 "${prev}/restart.sha256")
    in_set "${IN}" NRREC   -1
    in_set "${IN}" ININAME "../$(basename "${prev}")/$(in_get "${IN}" RSTNAME)"
  fi
fi

# One MPI rank per tile.
NP=$(( $(in_get "${IN}" NtileI) * $(in_get "${IN}" NtileJ) ))

# What the results depend on beyond the receipt: the executable, compiler
# flags and tiling (ROMS output can change with the domain decomposition).
{
  echo ""
  echo "## Build and run"
  grep -E '^(Fortran compiler|Fortran flags|ROMS Application|Added CPP Options):' "${RUN_DIR}/build.log"
  echo "executable: sha256 $(cut -d' ' -f1 "${RUN_DIR}/executable.sha256")"
  echo "tiling:  NtileI=$(in_get "${IN}" NtileI) NtileJ=$(in_get "${IN}" NtileJ) (${NP} MPI ranks)"
  echo "segment: ${SEGMENT} of ${NSEGMENTS}, NTIMES=$(in_get "${IN}" NTIMES), restart read: sha256 ${restart_in}"
  echo "slurm:   job ${SLURM_JOB_ID:-?} on ${SLURM_JOB_NODELIST:-?}"
} >> receipt_node.txt

# Run.
status=0
mpirun -np ${NP} "${RUN_DIR}/romsM" "${IN}" > roms.log 2>&1 || status=$?

if [ ${status} -ne 0 ] || ! grep -q 'ROMS: DONE' roms.log \
   || grep -qE 'ERROR:|Abnormal termination' roms.log; then
  tail -50 roms.log
  echo "FAIL: ROMS run (mpirun exit status ${status}), see ${SEG_DIR}/roms.log"
  exit 1
fi

# The energy diagnostics ROMS prints every time step (step, date, kinetic,
# potential and total energy, volume).
num='[-+0-9.E]+'
grep -E "^ +[0-9]+ [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:.]+ +${num} +${num} +${num} +${num} *$" \
  roms.log > energy.txt || true

if [ "${NSEGMENTS}" -gt 1 ]; then
  # Record the restart file for the next segment to check.
  sha256sum "$(in_get "${IN}" RSTNAME)" > restart.sha256
  echo "restart written: sha256 $(cut -d' ' -f1 restart.sha256)" >> receipt_node.txt
  if [ "${SEGMENT}" -lt "${NSEGMENTS}" ]; then
    echo "Segment ${SEGMENT} of ${NSEGMENTS} finished; restart file recorded in ${SEG_DIR}/restart.sha256"
    exit 0
  fi
  # Last segment: join the energy lines of the whole chain. Each segment
  # after the first prints its starting step again, read back from the
  # restart file; that line replaces the one the segment before printed, so
  # the restart file itself is compared with the reference too.
  cat "${RUN_DIR}"/seg_*/energy.txt | awk '
    !($1 in line) { order[++n] = $1 }
    { line[$1] = $0 }
    END { for (i = 1; i <= n; i++) print line[order[i]] }' > "${RUN_DIR}/energy.txt"
  cd "${RUN_DIR}"
fi

# Regression check: the energy diagnostics must match the reference for this
# compiler within the tolerance given in that file (scripts/compare_energy.sh).
# The last digits can differ between CPU types and machines, so exact digits
# are only expected on the same node type; a real change is far larger.
#
# A chained run is held to test.restart_rtol instead (0: every printed digit),
# because a restart that is not exact moves the energy by less than the
# regression tolerance. On a machine where a single run does not reproduce
# the reference digit for digit, set RESTART_REFERENCE to the energy.txt of a
# single run made there and the chain is compared with that instead
# (scripts/ci_upwelling.sh does this).
REF=$(bp_get "${APP_DIR}/blueprint.yaml" "test.reference.${MOANA_FORT}")
[ -n "${REF}" ] || { echo "FAIL: no test.reference.${MOANA_FORT} in the blueprint"; exit 1; }
ref_file=${APP_DIR}/${REF}
rtol=()
if [ "${NSEGMENTS}" -gt 1 ]; then
  rtol=("$(bp_get "${APP_DIR}/blueprint.yaml" test.restart_rtol)")
  [ -z "${RESTART_REFERENCE:-}" ] || { ref_file=${RESTART_REFERENCE}; REF="single run ${RESTART_REFERENCE}"; }
fi
"${SRC}/scripts/compare_energy.sh" "${ref_file}" energy.txt "${rtol[@]}" \
  > compare.txt 2>&1 || compare_status=$?
{ echo ""; echo "## Regression check (${REF})"; cat compare.txt; } >> "${SEG_DIR}/receipt_node.txt"
if [ "${compare_status:-0}" -ne 0 ]; then
  cat compare.txt
  echo "FAIL: results differ from ${REF} (see above)."
  if [ "${NSEGMENTS}" -gt 1 ]; then
    echo "A chained run must match a single run exactly. If the single-run test"
    echo "passes on this machine, stopping and restarting changed the answer."
  else
    echo "If the change is expected (new ROMS version, modules or options),"
    echo "check the run, then update the reference as described in that file."
  fi
  exit 1
fi

if [ "${NSEGMENTS}" -gt 1 ]; then
  echo "PASS: UPWELLING run as ${NSEGMENTS} chained segments on ${NP} MPI ranks matched the single run (tolerance ${rtol[0]})"
else
  echo "PASS: UPWELLING built, ran on ${NP} MPI ranks and matched the reference within tolerance"
fi
echo "Output: ${RUN_DIR}"
ls -l "${SEG_DIR}"/*.nc
