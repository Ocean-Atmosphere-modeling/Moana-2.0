#!/bin/bash
# Run the UPWELLING tests without SLURM: the automated test on GitHub Actions
# (.github/workflows/upwelling.yml), or by hand on any Linux machine.
# Usage:  conda activate moana_ci && scripts/ci_upwelling.sh [run_dir]
#
# Runs the same job script as on Amarel (tests/upwelling/run_upwelling.slurm)
# with the GNU toolchain in env/ci.sh, straight from this checkout (no frozen
# code copy and no receipt.txt: on GitHub the commit is the record):
#
#   1. checks the blueprint;
#   2. regression test: build, run, compare with the gfortran reference;
#   3. restart test: the same case as two chained segments must match the
#      single run from step 2 in every printed digit.
#
# Results go in run_dir (default tests/upwelling/run_ci, ignored by git):
# single/ and chained/. Exits non-zero if any step fails.

set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RUN=${1:-${REPO}/tests/upwelling/run_ci}

export SRC=${REPO}
export APP=tests/upwelling
export MOANA_ENV=env/ci.sh
JOB=${REPO}/${APP}/run_upwelling.slurm

"${REPO}/scripts/check_blueprint.sh" "${REPO}/${APP}"

rm -rf "${RUN}"
mkdir -p "${RUN}/single" "${RUN}/chained"

echo ""
echo "== Regression test: one run =="
( cd "${RUN}/single" && SEGMENT=1 NSEGMENTS=1 bash "${JOB}" )

echo ""
echo "== Restart test: two chained segments =="
# Compared with the single run just made on this machine, not with the
# reference file, so a last-digit difference between machines cannot fail it.
export RESTART_REFERENCE=${RUN}/single/energy.txt
for seg in 1 2; do
  ( cd "${RUN}/chained" && SEGMENT=${seg} NSEGMENTS=2 bash "${JOB}" )
done
