#!/bin/bash
# Submit a ROMS job for one application, with a frozen copy of the code.
# Usage (on an Amarel login node):
#   scripts/submit_run.sh <app_dir> [--allow-dirty]
# e.g.
#   scripts/submit_run.sh tests/upwelling
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
# 3. Writes receipt.txt there (scripts/record_env.sh plus the commits and
#    checksums of the copy). Amarel compute nodes have no git, so this has
#    to happen here.
# 4. If <app_dir>/inputs.tsv exists, checks the input data against it
#    (scripts/check_inputs.sh) and refuses to submit if anything differs.
# 5. Submits <app_dir>/run_<app>.slurm (from the copy) with sbatch.

set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

[ $# -ge 1 ] || { echo "usage: $0 <app_dir> [--allow-dirty]"; exit 1; }
APP=$(realpath --relative-to="${REPO}" "$1")
APP_NAME=$(basename "${APP}")
allow_dirty=0
[ "${2:-}" = "--allow-dirty" ] && allow_dirty=1

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

# 3. Receipt, with the environment the job will load (module scripts use
#    unset variables, hence set +u).
( set +u; source "${REPO}/env/amarel.sh" >/dev/null 2>&1
  "${REPO}/scripts/record_env.sh" ) > "${RUN_DIR}/receipt.txt"
{
  echo ""
  echo "## Code copy used by the job (src/)"
  echo "app:       ${APP}"
  echo "moana-2.0: ${code_commit}"
  echo "roms:      ${roms_commit}"
  if [ -n "${dirty}" ]; then
    echo "WARNING: submitted with --allow-dirty; the commits above are"
    echo "temporary snapshots of uncommitted edits and may not exist later."
  fi
  echo ""
  echo "## Configuration checksums (sha256)"
  (cd "${SRC}" && find "${APP}" -type f | sort | xargs sha256sum)
} >> "${RUN_DIR}/receipt.txt"

# 4. Input data.
if [ -f "${REPO}/${APP}/inputs.tsv" ]; then
  { echo ""; echo "## Input data (${APP}/inputs.tsv)"; } >> "${RUN_DIR}/receipt.txt"
  if ! "${REPO}/scripts/check_inputs.sh" "${SRC}/${APP}/inputs.tsv" \
       >> "${RUN_DIR}/receipt.txt" 2>&1; then
    tail -n 20 "${RUN_DIR}/receipt.txt"
    echo "Refusing to submit: input data do not match ${APP}/inputs.tsv"
    exit 1
  fi
fi

# 5. Submit.
sbatch --chdir="${RUN_DIR}" --output="${RUN_DIR}/slurm-%j.out" \
       --export=ALL,SRC="${SRC}",APP="${APP}" \
       "${SRC}/${JOB}"
echo "Run directory: ${RUN_DIR}"
