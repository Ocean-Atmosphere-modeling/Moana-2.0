#!/bin/bash
#SBATCH --job-name=make-bry
#SBATCH --partition=main
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/projects/f_omg_1/moa/moana/oceanum_input/boundary_cond/roms-ready/make_bry_%j.log
#
# Make the ROMS boundary file from the raw DataMesh strips (scripts/make_bry.py).
# Settings (sides, times, output file) are at the top of make_bry.py.
#
#   sbatch scripts/make_bry.slurm        # from the repository root
#
# The log has the read and the fill + interpolation time of each side (from make_bry.py)
# and the total wall time and peak memory (from /usr/bin/time).

source ~/miniconda3/etc/profile.d/conda.sh
conda activate moana_python

echo "node: $(hostname)   cpu: $(lscpu | sed -n 's/^Model name: *//p')   start: $(date)"
/usr/bin/time -v python scripts/make_bry.py
echo "end: $(date)"
