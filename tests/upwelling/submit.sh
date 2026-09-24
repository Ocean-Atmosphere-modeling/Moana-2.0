#!/bin/bash
# Submit the UPWELLING toolchain test (see run_upwelling.slurm).
# Usage (on an Amarel login node):  tests/upwelling/submit.sh
#
# Amarel compute nodes have no git, so the receipt with the code versions
# (scripts/record_env.sh) is written here, before the job is submitted.
# Everything for one test goes in tests/upwelling/run_<date>_<time>/.

set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
RUN_DIR=${REPO}/tests/upwelling/run_$(date +%Y%m%d_%H%M%S)
mkdir -p "${RUN_DIR}"

# Receipt with the environment the job will load (module scripts use unset
# variables, hence set +u).
( set +u; source "${REPO}/env/amarel.sh" >/dev/null 2>&1
  "${REPO}/scripts/record_env.sh" "${RUN_DIR}/receipt.txt" )

sbatch --chdir="${RUN_DIR}" --output="${RUN_DIR}/slurm-%j.out" \
       --export=ALL,REPO="${REPO}" \
       "${REPO}/tests/upwelling/run_upwelling.slurm"
echo "Run directory: ${RUN_DIR}"
