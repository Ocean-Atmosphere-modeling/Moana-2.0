#!/bin/bash
# Install pyroms, pyroms_toolbox, bathy_smoother and the SCRIP extension
# into the active conda environment (moana_pyroms, see env/moana_pyroms.yml).
# Usage:  conda activate moana_pyroms && bash scripts/install_pyroms.sh
#
# pyroms is not in this repository. If pyroms/ is not there, this script
# clones ESMG/pyroms at the commit below. pyroms builds with numpy.distutils,
# thus the env must have Python <= 3.11, numpy < 2 and setuptools < 60.

set -euo pipefail

PYROMS_URL=https://github.com/ESMG/pyroms.git
PYROMS_COMMIT=1370d22

repo=$(cd "$(dirname "$0")/.." && pwd)
src=${repo}/pyroms

[ -n "${CONDA_PREFIX:-}" ] \
  || { echo "install_pyroms.sh: activate the moana_pyroms conda environment first"; exit 1; }
python -c "import numpy.distutils" 2>/dev/null \
  || { echo "install_pyroms.sh: numpy.distutils not found; recreate the env from env/moana_pyroms.yml"; exit 1; }

if [ ! -d "${src}" ]; then
  git clone "${PYROMS_URL}" "${src}"
  git -C "${src}" checkout "${PYROMS_COMMIT}"
fi
echo "pyroms commit: $(git -C "${src}" rev-parse --short HEAD)"

# The three Python packages (editable, so the source stays in pyroms/).
for pkg in pyroms pyroms_toolbox bathy_smoother; do
  pip install --no-build-isolation --no-deps -e "${src}/${pkg}"
done

# SCRIP extension (remapping). nf-config gives the conda NetCDF-Fortran libraries.
# pyscrip.f90 is fixed-form Fortran, but f2py in numpy 1.26 reads all .f90 files
# as free-form and makes a bad wrapper ("undefined symbol: unknown_subroutine_").
# Thus we build in a temporary copy that starts with the f2py "-*- fix -*-" line.
build=$(mktemp -d)
trap 'rm -rf "${build}"' EXIT
cp "${src}"/pyroms/external/scrip/source/* "${build}/"
sed -i '1i ! -*- fix -*-' "${build}/pyscrip.f90"
make -C "${build}" USE_NF_CONFIG=1 SCRIP_EXT_DIR="${src}/pyroms/pyroms" install

python -c "import pyroms, pyroms_toolbox, bathy_smoother; from pyroms import scrip; print('pyroms OK')"
