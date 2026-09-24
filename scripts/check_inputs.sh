#!/bin/bash
# Check model input files against an application's data manifest.
# Usage:  scripts/check_inputs.sh <app_dir>/inputs.tsv
#
# The manifest (inputs.tsv, tab-separated, "#" lines are comments) has one
# line per input file:
#
#   sha256  path  source  version_or_date  made_by
#
# path is absolute, or relative to $MOANA_DATA. source says where the file
# came from (URL, product name), version_or_date which version or download
# date, and made_by the script (in this repository) that made or fetched
# it. Get the checksum with:  sha256sum <file>
#
# Prints each file with OK / MISSING / CHANGED and exits non-zero if any
# file is missing or its contents differ from the manifest.

set -uo pipefail

manifest=${1:?usage: scripts/check_inputs.sh <app_dir>/inputs.tsv}
[ -f "${manifest}" ] || { echo "no such manifest: ${manifest}"; exit 1; }

bad=0
n=0
while IFS=$'\t' read -r sum path source version made_by; do
  [[ -z "${sum}" || "${sum}" == \#* ]] && continue
  n=$((n + 1))
  case "${path}" in
    /*) file=${path} ;;
    *)  file=${MOANA_DATA:?set MOANA_DATA to the input data folder}/${path} ;;
  esac
  if [ ! -f "${file}" ]; then
    status=MISSING; bad=1
  elif [ "$(sha256sum "${file}" | cut -d' ' -f1)" != "${sum}" ]; then
    status=CHANGED; bad=1
  else
    status=OK
  fi
  printf '%-8s %s  %s  [%s, %s, %s]\n' "${status}" "${sum:0:12}" "${file}" \
    "${source}" "${version}" "${made_by}"
done < "${manifest}"

echo "${n} input file(s) listed in ${manifest}"
[ ${bad} -eq 0 ] || echo "ERROR: input files missing or changed (see above)"
exit ${bad}
