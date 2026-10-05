#!/bin/bash
# Submit a ROMS job for one application, with a frozen copy of the code.
# Usage (on an Amarel login node):
#   scripts/submit_run.sh <app_dir> [--allow-dirty] [--segments N]
# e.g.
#   scripts/submit_run.sh tests/upwelling
#   scripts/submit_run.sh tests/upwelling --segments 2
#
# 1. Refuses to run from uncommitted or untracked changes (in this
#    repository or in roms/), so every run traces back to a commit.
#    --allow-dirty overrides this for quick experiments: committed files
#    plus uncommitted edits to tracked files are used (untracked files are
#    not), and the receipt says so.
# 2. Makes <app_dir>/run_<date>_<time>/ and copies the exact code into its
#    src/ folder (this repository and ROMS). The job builds and runs from
#    that copy, so later edits, checkouts or submodule updates cannot change
#    a job that is waiting in the queue.
# 3. Checks <app_dir>/blueprint.yaml against the copy
#    (scripts/check_blueprint.sh) and refuses to submit if they disagree.
# 4. Writes receipt.txt there (scripts/record_env.sh plus the commits and
#    checksums of the copy), and the same facts as blueprint.lock.yaml for
#    scripts to read. Amarel compute nodes have no git, so this has to
#    happen here.
# 5. If <app_dir>/inputs.tsv exists, checks the input data against it
#    (scripts/check_inputs.sh) and refuses to submit if anything differs.
# 6. Submits <app_dir>/run_<app>.slurm (from the copy) with sbatch. With
#    --segments N (default: run.segments in the blueprint) it submits a chain
#    of N jobs that share the run directory, the code copy and one
#    executable; each starts when the one before has finished successfully
#    and continues from its restart file. The job script does the chaining
#    (see tests/upwelling/run_upwelling.slurm).

set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

usage="usage: $0 <app_dir> [--allow-dirty] [--segments N]"
[ $# -ge 1 ] || { echo "${usage}"; exit 1; }
APP=$(realpath --relative-to="${REPO}" "$1")
APP_NAME=$(basename "${APP}")
shift
source "${REPO}/scripts/run_lib.sh"
allow_dirty=0
segments=$(bp_get "${REPO}/${APP}/blueprint.yaml" run.segments 2>/dev/null || true)
while [ $# -gt 0 ]; do
  case "$1" in
    --allow-dirty) allow_dirty=1; shift ;;
    --segments)    segments=${2:-}; shift 2 || { echo "${usage}"; exit 1; } ;;
    *) echo "${usage}"; exit 1 ;;
  esac
done
segments=${segments:-1}
[[ "${segments}" =~ ^[1-9][0-9]*$ ]] || { echo "--segments needs a positive whole number"; exit 1; }

JOB=${APP}/run_${APP_NAME}.slurm
[ -f "${REPO}/${JOB}" ] || { echo "no job script ${JOB}"; exit 1; }

# 1. Clean tree?
dirty=$(git -C "${REPO}" status --porcelain --ignore-submodules=none)
if [ -n "${dirty}" ] && [ ${allow_dirty} -eq 0 ]; then
  echo "Refusing to submit: uncommitted or untracked changes:"
  echo "${dirty}"
  echo "Commit them first (or pass --allow-dirty for a throwaway test)."
  exit 1
fi

# 2. Frozen copy of the code. "git stash create" makes a commit of the
#    working tree without touching it (empty output = tree is clean).
snapshot () { local c; c=$(git -C "$1" stash create); echo "${c:-$(git -C "$1" rev-parse HEAD)}"; }
code_commit=$(snapshot "${REPO}")
roms_commit=$(snapshot "${REPO}/roms")

RUN_DIR=${REPO}/${APP}/run_$(date +%Y%m%d_%H%M%S)
SRC=${RUN_DIR}/src
mkdir -p "${SRC}/roms"
git -C "${REPO}" archive "${code_commit}" | tar -x -C "${SRC}"
git -C "${REPO}/roms" archive "${roms_commit}" | tar -x -C "${SRC}/roms"

# 3. Blueprint: must agree with the copy the job will use.
if ! "${SRC}/scripts/check_blueprint.sh" "${SRC}/${APP}" "${roms_commit}" \
     > "${RUN_DIR}/blueprint_check.txt" 2>&1; then
  cat "${RUN_DIR}/blueprint_check.txt"
  echo "Refusing to submit: ${APP}/blueprint.yaml does not match the application"
  exit 1
fi

# 4. Receipt, with the environment the job will load (module scripts use
#    unset variables, hence set +u).
( set +u; source "${REPO}/env/amarel.sh" >/dev/null 2>&1
  "${REPO}/scripts/record_env.sh" ) > "${RUN_DIR}/receipt.txt"
{
  echo ""
  echo "## Code copy used by the job (src/)"
  echo "app:       ${APP}"
  echo "segments:  ${segments}"
  echo "moana-2.0: ${code_commit}"
  echo "roms:      ${roms_commit}"
  if [ "${code_commit}" != "$(git -C "${REPO}" rev-parse HEAD)" ] \
     || [ "${roms_commit}" != "$(git -C "${REPO}/roms" rev-parse HEAD)" ]; then
    echo "WARNING: submitted with --allow-dirty; the commits above are"
    echo "temporary snapshots of uncommitted edits and may not exist later."
  elif [ -n "${dirty}" ]; then
    echo "NOTE: submitted with --allow-dirty; only untracked files differed"
    echo "(listed above) and they are not in src/."
  fi
  echo ""
  echo "## Configuration checksums (sha256)"
  (cd "${SRC}" && find "${APP}" -type f | sort | xargs sha256sum)
  echo ""
  echo "## Blueprint check (${APP}/blueprint.yaml)"
  cat "${RUN_DIR}/blueprint_check.txt"
} >> "${RUN_DIR}/receipt.txt"
rm "${RUN_DIR}/blueprint_check.txt"

# The same facts for scripts to read (scripts/verify_run.sh): the blueprint
# with every pointer replaced by the commit or sha256 it resolved to. The
# job adds the executable (executable.sha256) and, for a chained run, each
# restart file (seg_NN/restart.sha256).
{
  echo "# Resolved blueprint, written by scripts/submit_run.sh. Do not edit."
  echo "schema_version: 1"
  echo "name: ${APP_NAME}"
  echo "app: ${APP}"
  echo "submitted: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "code:"
  echo "  moana:"
  echo "    location: $(git -C "${REPO}" remote get-url origin 2>/dev/null || echo unknown)"
  echo "    commit: ${code_commit}"
  echo "    committed: $([ -z "${dirty}" ] && echo true || echo false)"
  echo "  roms:"
  echo "    location: $(bp_get "${SRC}/${APP}/blueprint.yaml" code.roms.location)"
  echo "    commit: ${roms_commit}"
  echo "run:"
  echo "  segments: ${segments}"
  echo "files:"
  (cd "${SRC}" && find "${APP}" env scripts -type f | sort | xargs sha256sum) \
    | awk '{printf "  %s: %s\n", $2, $1}'
} > "${RUN_DIR}/blueprint.lock.yaml"

# 5. Input data.
if [ -f "${REPO}/${APP}/inputs.tsv" ]; then
  { echo ""; echo "## Input data (${APP}/inputs.tsv)"; } >> "${RUN_DIR}/receipt.txt"
  if ! "${REPO}/scripts/check_inputs.sh" "${SRC}/${APP}/inputs.tsv" \
       >> "${RUN_DIR}/receipt.txt" 2>&1; then
    tail -n 20 "${RUN_DIR}/receipt.txt"
    echo "Refusing to submit: input data do not match ${APP}/inputs.tsv"
    exit 1
  fi
fi

# 6. Submit: one job per segment, each waiting for the one before. If a
#    segment fails, the rest of the chain is cancelled.
job=
for seg in $(seq 1 "${segments}"); do
  after=()
  [ -z "${job}" ] || after=(--dependency="afterok:${job}" --kill-on-invalid-dep=yes)
  job=$(sbatch --parsable "${after[@]}" \
               --chdir="${RUN_DIR}" --output="${RUN_DIR}/slurm-%j.out" \
               --export=ALL,SRC="${SRC}",APP="${APP}",SEGMENT="${seg}",NSEGMENTS="${segments}" \
               "${SRC}/${JOB}")
  job=${job%%;*}
  echo "Submitted batch job ${job} (segment ${seg} of ${segments})"
done
echo "Run directory: ${RUN_DIR}"
