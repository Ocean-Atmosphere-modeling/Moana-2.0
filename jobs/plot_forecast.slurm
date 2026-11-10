#!/bin/bash
#SBATCH --job-name=plot-fc
#SBATCH --partition=p_omg_1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/projects/f_omg_1/moa/moana/Nikki_run/%x_%j.log
#
# Plots and animations of a ROMS forecast run (Scripts/plot_forecast.py). Run directory and part
# (maps, anim, cmems, points, log or all) are given when submitting, usually after the run finishes:
#
#   sbatch --dependency=afterok:<ROMS job id> --job-name=plot-anim jobs/plot_forecast.slurm /projects/f_omg_1/moa/moana/Nikki_run anim
#
# The log has the script's output and the total wall time and peak memory (from /usr/bin/time).

source ~/miniforge3/etc/profile.d/conda.sh
conda activate moana_python
cd /home/nn411/Projects/OceanAtm/Moana-2.0

echo "node: $(hostname)   cpu: $(lscpu | sed -n 's/^Model name: *//p')   start: $(date)"
/usr/bin/time -v python -u Scripts/plot_forecast.py "$@"
echo "end: $(date)"