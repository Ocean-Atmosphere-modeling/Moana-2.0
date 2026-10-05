#!/bin/bash
# Fetch the published Moana Ocean Hindcast configuration (Souza, 2022,
# https://doi.org/10.5281/zenodo.6484908) and check it is the file we expect.
# Usage:  scripts/fetch_published_config.sh        (needs $MOANA_DATA)
#
# Downloads the Zenodo archive to $MOANA_DATA/published/moana_hindcast_v1.0/,
# checks its sha256, and unpacks the four files it holds:
#
#   nz5km_grd.nc     the 5 km grid, bathymetry and land mask
#   roms.in          the authors' ROMS 3.9 run parameters
#   roms3d.h         the authors' CPP options
#   roms_config.sh   their compiler and library settings
#
# The grid is listed in Apps/moana/inputs.tsv with its sha256, so
# scripts/check_inputs.sh reports OK once this script has run. The archive
# has no licence, so these files are fetched, not committed. Its roms_src/
# folder is empty and the nudging file its README lists is not in it; those
# have to be requested from the authors.
#
# Safe to run again: an archive already there is checked, not downloaded.

set -euo pipefail

URL=https://zenodo.org/api/records/6484908/files/joaometocean/moana_hindcast-v1.0.zip/content
ZIP_SHA256=3a97d0a2f4e27e2b8af4a2c82ba6d8a20bc19e11c363833531cc391b90c7fd75
ZIP=moana_hindcast-v1.0.zip
TOP=joaometocean-moana_hindcast-695d25e/configuration

DEST=${MOANA_DATA:?set MOANA_DATA to the input data folder}/published/moana_hindcast_v1.0
mkdir -p "${DEST}"
cd "${DEST}"

[ -f "${ZIP}" ] || curl --fail --location --silent --show-error --output "${ZIP}" "${URL}"
echo "${ZIP_SHA256}  ${ZIP}" | sha256sum --check \
  || { echo "ERROR: ${DEST}/${ZIP} is not the published archive; delete it and run again"; exit 1; }

unzip -q -o -j "${ZIP}" "${TOP}/*"

sha256sum --check <<'EOF'
4209188ebea9bbbfa42e70c1a77642aba6b0a095376deb59d0ed4e0387efccc1  nz5km_grd.nc
9528daf1986fe090028dc6ffe99c6577f9bb7d107d696633949dcb1f64d9a8af  roms.in
d41db013b7e283a65fea5e498bd8777348b50c559a51f13eacf3a126879743c4  roms3d.h
6ad58db4d7419ade68f849c1317eaf4b8481e0739629a6557dca68551b80739b  roms_config.sh
EOF
echo "Published configuration is in ${DEST}"
