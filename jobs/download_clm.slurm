#!/bin/bash
#SBATCH --job-name=download-clm
#SBATCH --partition=p_omg_1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=2-00:00:00        
#SBATCH --output=/projects/f_omg_1/moa/moana/oceanum_input/climatology/logs/%x_%j.log
#
# Based on Suman's scripts/download_bry.slurm. Downloads raw climatology fields (Scripts/download_clm.py);
# the yaml given when submitting decides which dataset and dates:
#
#   sbatch --job-name=clm_uo_vo jobs/download_clm.slurm yaml/clm_jan/download_uo_vo.yaml

source ~/miniforge3/etc/profile.d/conda.sh
conda activate moana_python
cd /home/nn411/Projects/OceanAtm/Moana-2.0

echo "node: $(hostname)   start: $(date)"
/usr/bin/time -v python -u Scripts/download_clm.py "$@"
status=$?                  # keep python's exit status, so SLURM shows FAILED when the download fails
echo "end: $(date)"
exit $status
