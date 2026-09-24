#!/bin/bash
# Submit the UPWELLING toolchain test (see run_upwelling.slurm).
# Usage (on an Amarel login node):  tests/upwelling/submit.sh [--allow-dirty]
#
# Same as  scripts/submit_run.sh tests/upwelling : refuses uncommitted
# changes, copies the code into tests/upwelling/run_<date>_<time>/src,
# writes the receipt there and submits the job.

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
exec "${REPO}/scripts/submit_run.sh" "${REPO}/tests/upwelling" "$@"
