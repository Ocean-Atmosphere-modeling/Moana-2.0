#!/bin/bash
# Check an application's blueprint against the files it points to.
# Usage:  scripts/check_blueprint.sh <app_dir> [roms_commit]
#
# <app_dir>/blueprint.yaml names everything that defines the application:
# the ROMS commit, the CPP header, the .in file, the job script, the input
# data manifest and the test references. This script checks that
#
#   - the required keys are there and "name" is the folder name;
#   - the ROMS commit equals the pinned roms/ submodule (pass roms_commit
#     where there is no git, e.g. in a run's code copy; otherwise it is
#     read from the submodule);
#   - the header, .in file, job script, manifest and references exist and
#     follow the naming scripts/build_roms.sh and submit_run.sh expect.
#
# Prints one line per check with OK / TODO / ERROR and exits non-zero on any
# ERROR. In a blueprint with "state: draft" a file that is not written yet
# is a TODO, not an error.

set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${HERE}/run_lib.sh"

APP_DIR=${1:?usage: scripts/check_blueprint.sh <app_dir> [roms_commit]}
APP_DIR=$(cd "${APP_DIR}" && pwd)
BP=${APP_DIR}/blueprint.yaml
[ -f "${BP}" ] || { echo "ERROR    no blueprint: ${BP}"; exit 1; }
ROOT=$(cd "${HERE}/.." && pwd)

bad=0
ok ()   { printf 'OK       %s\n' "$*"; }
todo () { printf 'TODO     %s\n' "$*"; }
err ()  { printf 'ERROR    %s\n' "$*"; bad=1; }

for key in schema_version name state code.roms.location code.roms.commit \
           compile_time.header run_time.input run_time.job \
           inputs.manifest run.segments; do
  [ -n "$(bp_get "${BP}" "${key}")" ] || err "missing key: ${key}"
done

name=$(bp_get "${BP}" name)
state=$(bp_get "${BP}" state)
[ "${name}" = "$(basename "${APP_DIR}")" ] && ok "name: ${name}" \
  || err "name is '${name}' but the folder is '$(basename "${APP_DIR}")'"
case "${state}" in
  draft|validated) ok "state: ${state}" ;;
  *) err "state must be draft or validated, not '${state}'" ;;
esac

# ROMS pin.
want=$(bp_get "${BP}" code.roms.commit)
have=${2:-$(git -C "${ROOT}/roms" rev-parse HEAD 2>/dev/null || true)}
if [ -z "${have}" ]; then
  todo "ROMS commit not checked (no git here)"
elif [ "${want}" = "${have}" ]; then
  ok "ROMS commit: ${want}"
else
  err "ROMS commit is ${want} in the blueprint but roms/ is at ${have}"
fi

# Files, and the names the build and submit scripts derive from the folder.
file () {    # file <key> <expected name, or "">
  local key=$1 expect=$2 value
  value=$(bp_get "${BP}" "${key}")
  [ -n "${value}" ] || return 0
  if [ -n "${expect}" ] && [ "${value}" != "${expect}" ]; then
    err "${key} is '${value}', the scripts expect '${expect}'"
  elif [ -f "${APP_DIR}/${value}" ]; then
    ok "${key}: ${value}"
  elif [ "${state}" = "draft" ]; then
    todo "${key}: ${value} is not written yet"
  else
    err "${key}: ${value} does not exist"
  fi
}
file compile_time.header "${name}.h"
file run_time.input      "roms_${name}.in"
file run_time.job        "run_${name}.slurm"
[ "$(bp_get "${BP}" inputs.manifest)" = "none" ] && ok "inputs.manifest: none" \
  || file inputs.manifest "inputs.tsv"
for compiler in ifx gfortran; do
  file "test.reference.${compiler}" ""
done

rtol=$(bp_get "${BP}" test.restart_rtol)
[ -z "${rtol}" ] || { [[ "${rtol}" =~ ^[0-9.eE+-]+$ ]] && ok "test.restart_rtol: ${rtol}" \
  || err "test.restart_rtol must be a number, not '${rtol}'"; }

segments=$(bp_get "${BP}" run.segments)
[[ "${segments}" =~ ^[1-9][0-9]*$ ]] && ok "run.segments: ${segments}" \
  || err "run.segments must be a positive whole number, not '${segments}'"

[ ${bad} -eq 0 ] || echo "ERROR: ${BP} does not match the application (see above)"
exit ${bad}
