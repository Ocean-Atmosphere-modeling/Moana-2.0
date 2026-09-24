#!/bin/bash
# Record the code versions and software environment for reproducibility.
# Usage:  scripts/record_env.sh [output_file]    (default: stdout)
#
# Captures the Moana-2.0 and ROMS submodule commits (with any uncommitted
# or untracked files flagged), the CPU, loaded modules, the active conda
# environment, and compiler/MPI/NetCDF versions.
# Save the output next to model builds or runs.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [ -n "$1" ]; then
  exec > "$1"
fi

section () { echo ""; echo "## $1"; }
show () { command -v "$1" >/dev/null 2>&1 && { echo "\$ $*"; "$@" 2>&1 | head -5; }; }

echo "# Moana-2.0 environment record"
echo "date:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "host:  $(hostname)"
echo "user:  $(whoami)"
echo "os:    $(uname -sr)"
echo "cpu:   $(awk -F': ' '/^model name/ {print $2; exit}' /proc/cpuinfo)"

section "Git"
# Only report git if ROOT_DIR is itself a repository: a run's code copy
# (run_*/src) sits inside the repository but is not a checkout of it.
if command -v git >/dev/null 2>&1 \
   && [ "$(git -C "$ROOT_DIR" rev-parse --show-toplevel 2>/dev/null)" = "$ROOT_DIR" ]; then
  echo "moana-2.0: $(git -C "$ROOT_DIR" rev-parse HEAD) ($(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD))"
  git -C "$ROOT_DIR" submodule status --recursive
  dirty=$(git -C "$ROOT_DIR" status --porcelain --ignore-submodules=none)
  if [ -n "$dirty" ]; then
    echo "WARNING: uncommitted changes present:"
    echo "$dirty"
    # A "+" before a submodule commit above also means it differs from the pin.
    git -C "$ROOT_DIR" submodule foreach --quiet \
      'git status --porcelain | sed "s|^|  $sm_path: |"'
  fi
else
  # e.g. Amarel compute nodes, or a run's code copy: the code version is
  # recorded by scripts/submit_run.sh on a login node.
  echo "(not a git checkout, or git not available; see receipt.txt)"
fi

section "Loaded modules"
if type module >/dev/null 2>&1; then
  module -t list 2>&1
else
  echo "(module command not available)"
fi

section "Conda environment"
if [ -n "${CONDA_PREFIX:-}" ] && command -v conda >/dev/null 2>&1; then
  echo "env:    ${CONDA_DEFAULT_ENV:-?} (${CONDA_PREFIX})"
  # Same format as env/moana_python.lock.txt; equal hashes = same packages.
  echo "sha256: $(conda list --explicit 2>/dev/null | grep -v '^#' | sha256sum | cut -d' ' -f1)"
else
  echo "(none active)"
fi

section "Toolchain"
for c in ifort ifx gfortran mpif90 mpirun; do show $c --version; done
show nf-config --all
show nc-config --version
show ncks --version
