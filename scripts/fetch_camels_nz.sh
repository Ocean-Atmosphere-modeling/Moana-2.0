#!/bin/bash
# Download CAMELS-NZ (University of Canterbury, doi:10.26021/canterburynz.28827644,
# CC BY 4.0) from figshare and unzip each archive into its own directory.
#
# Usage: scripts/fetch_camels_nz.sh [OUT_DIR] [FILE ...]
#   default OUT_DIR: /projects/f_omg_1/moa/moana/Input/rivers/camels_nz
#   default files:   Readme.txt, daily streamflow, catchment attributes,
#                    shapefiles (~60 MB). Hourly streamflow (657 MB) etc. by
#                    name, e.g. CAMELS_NZ_hourly_Streamflow.zip.
# The figshare API lists each file's URL and MD5; every download is checked
# against it, and the article version goes to OUT_DIR/VERSION.

set -euo pipefail

OUT=${1:-/projects/f_omg_1/moa/moana/Input/rivers/camels_nz}
shift || true
FILES=${*:-Readme.txt CAMELS_NZ_daily_Streamflow.zip \
CAMELS_NZ_Catchment_Atrributes.zip CAMELS_NZ_Shapefiles.zip}
API=https://api.figshare.com/v2/articles/28827644
PY=${PY:-$HOME/miniconda3/envs/moana_python/bin/python}

mkdir -p "${OUT}"
cd "${OUT}"
curl -sS --retry 5 "${API}" > article.json
"${PY}" -I -c '
import json, sys
a = json.load(open("article.json"))
v, d = a["version"], a["published_date"]
open("VERSION", "w").write(f"figshare 28827644 version {v}, published {d}\n")
for f in a["files"]:
    print(f["name"], f["download_url"], f.get("supplied_md5") or f["computed_md5"])
' > files.txt
cat VERSION

for name in ${FILES}; do
  read -r _ url md5 < <(grep "^${name} " files.txt) || { echo "no file ${name}" >&2; exit 1; }
  if [ -s "${name}" ] && [ "$(md5sum "${name}" | cut -d' ' -f1)" = "${md5}" ]; then
    echo "skip ${name}"
  else
    echo "get  ${name}"
    curl -sSL --retry 10 --retry-all-errors -o "${name}.part" "${url}"
    [ "$(md5sum "${name}.part" | cut -d' ' -f1)" = "${md5}" ] || { echo "md5 mismatch ${name}" >&2; exit 1; }
    mv "${name}.part" "${name}"
  fi
  case "${name}" in
    *.zip) d=${name%.zip}; rm -rf "${d}"; mkdir "${d}"; unzip -q "${name}" -d "${d}" ;;
  esac
done
echo "done: $(du -sh . | cut -f1) in ${OUT}"
