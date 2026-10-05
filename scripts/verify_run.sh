#!/bin/bash
# Check that a run directory still holds what the run used.
# Usage:  scripts/verify_run.sh <run_dir>
#
# scripts/submit_run.sh writes blueprint.lock.yaml into every run directory:
# the commits and the sha256 of every configuration, environment and script
# file in the run's code copy (src/). The job adds executable.sha256 and,
# for a chained run, seg_NN/restart.sha256. This script checks all of them
# again, plus the input data if the application has a manifest, so you can
# tell whether an old run directory can be trusted or rebuilt from.
#
# Prints one line per file with OK / MISSING / CHANGED and exits non-zero if
# anything is missing or changed.

set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${HERE}/run_lib.sh"

RUN=${1:?usage: scripts/verify_run.sh <run_dir>}
RUN=$(cd "${RUN}" && pwd)
LOCK=${RUN}/blueprint.lock.yaml
[ -f "${LOCK}" ] || { echo "no ${LOCK} (run submitted before blueprints were added?)"; exit 1; }

bad=0
check () {    # check <sha256> <file> <label>
  if [ ! -f "$2" ]; then
    status=MISSING; bad=1
  elif [ "$(sha256sum "$2" | cut -d' ' -f1)" != "$1" ]; then
    status=CHANGED; bad=1
  else
    status=OK
  fi
  printf '%-8s %s  %s\n' "${status}" "${1:0:12}" "$3"
}

echo "run:       ${RUN}"
echo "moana-2.0: $(bp_get "${LOCK}" code.moana.commit) (committed: $(bp_get "${LOCK}" code.moana.committed))"
echo "roms:      $(bp_get "${LOCK}" code.roms.commit)"
echo ""
echo "## Code copy (src/)"
while read -r path sum; do
  check "${sum}" "${RUN}/src/${path%:}" "src/${path%:}"
done < <(awk '/^files:/ {on = 1; next} on && /^  / {print $1, $2} on && /^[^ ]/ {on = 0}' "${LOCK}")

echo ""
echo "## Executable and restart files"
for f in "${RUN}/executable.sha256" "${RUN}"/seg_*/restart.sha256; do
  [ -f "${f}" ] || continue
  read -r sum name < "${f}"
  check "${sum}" "$(dirname "${f}")/${name}" "${f#"${RUN}"/} -> ${name}"
done
[ -f "${RUN}/executable.sha256" ] || { echo "MISSING  executable.sha256 (job has not built yet, or failed)"; bad=1; }

manifest=${RUN}/src/$(bp_get "${LOCK}" app)/inputs.tsv
if [ -f "${manifest}" ]; then
  echo ""
  echo "## Input data"
  "${HERE}/check_inputs.sh" "${manifest}" || bad=1
fi

echo ""
[ ${bad} -eq 0 ] && echo "PASS: run directory matches its record" \
  || echo "FAIL: files missing or changed (see above)"
exit ${bad}
