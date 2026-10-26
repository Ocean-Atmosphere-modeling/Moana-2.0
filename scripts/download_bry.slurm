#!/bin/bash
#SBATCH --job-name=download-bry
#SBATCH --partition=p_omg_1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --output=/projects/f_omg_1/moa/moana/oceanum_input/boundary_cond/raw/download_bry_%j.log
#
# Download the raw boundary strips from DataMesh (scripts/download_bry.py).
# Settings (datasource, sides, times, output folder) are in download_bry.yaml.
#
#   sbatch scripts/download_bry.slurm                 # from the repository root, uses download_bry.yaml
#   sbatch scripts/download_bry.slurm other.yaml
#
# DATAMESH_TOKEN must be set in the shell that runs sbatch (sbatch passes the environment to the job).

source ~/miniconda3/etc/profile.d/conda.sh
conda activate moana_python

echo "node: $(hostname)   start: $(date)"
/usr/bin/time -v python -u scripts/download_bry.py "$@"
status=$?                  # keep python's exit status, so SLURM shows FAILED when the download fails
echo "end: $(date)"
exit $status
