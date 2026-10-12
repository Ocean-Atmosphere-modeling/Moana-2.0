#!/bin/bash
# Download CFSv2 hourly surface fields (NCAR GDEX d094001, 0.205 deg global,
# GRIB2, one file per variable per month) from the open OSDF mirror.
#
# Usage: scripts/fetch_cfsv2.sh [OUT_DIR] [FIRST_YYYYMM] [LAST_YYYYMM]
#   default OUT_DIR: /projects/f_omg_1/moa/moana/Input/atmosphere/cfsv2_global
#   default months:  201709 .. 201912
# Existing files with the right size are skipped. sha256 of every file goes
# to OUT_DIR/SHA256SUMS. Licence: CC BY 4.0 (doi:10.5065/D6N877VB).

set -euo pipefail

OUT=${1:-/projects/f_omg_1/moa/moana/Input/atmosphere/cfsv2_global}
FIRST=${2:-201709}
LAST=${3:-201912}
BASE=https://osdf-director.osg-htc.org/ncar/gdex/d094001
# ROMS bulk fluxes: 10 m wind, 2 m air T, 2 m specific humidity, rain,
# down and up shortwave (net = down - up), down longwave, MSL pressure.
VARS="wnd10m tmp2m q2m prate dswsfc uswsfc dlwsfc prmsl"

mkdir -p "${OUT}"
cd "${OUT}"

ym=${FIRST}
while [ "${ym}" -le "${LAST}" ]; do
  yyyy=${ym:0:4}
  for v in ${VARS}; do
    f=${v}.cdas1.${ym}.grb2
    url=${BASE}/${yyyy}/${f}
    size=$(curl -sIL --retry 3 "${url}" | awk 'tolower($1)=="content-length:"{n=$2} END{print n+0}')
    if [ -s "${f}" ] && [ "$(stat -c %s "${f}")" -eq "${size}" ]; then
      echo "skip ${f}"
      continue
    fi
    echo "get  ${f} ($(( size / 1000000 )) MB)"
    # --retry-all-errors: the mirror sometimes drops connections mid-file
    # (curl error 18); -C - resumes the partial download.
    curl -sSL --retry 10 --retry-delay 10 --retry-all-errors -C - \
      -o "${f}.part" "${url}"
    [ "$(stat -c %s "${f}.part")" -eq "${size}" ] || { echo "size mismatch ${f}" >&2; exit 1; }
    mv "${f}.part" "${f}"
    sha256sum "${f}" >> SHA256SUMS
  done
  # next month
  y=${ym:0:4}; m=$((10#${ym:4:2} + 1))
  [ "${m}" -gt 12 ] && { m=1; y=$((y + 1)); }
  ym=$(printf "%04d%02d" "${y}" "${m}")
done
echo "done: $(ls -1 *.grb2 | wc -l) files, $(du -sh . | cut -f1)"
