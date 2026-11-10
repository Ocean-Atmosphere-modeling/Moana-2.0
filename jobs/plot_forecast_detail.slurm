#!/bin/bash
#SBATCH --job-name=detail
#SBATCH --partition=p_omg_1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/projects/f_omg_1/moa/moana/Nikki_run/%x_%j.log
#
# Detailed presentation plots and animations of a ROMS forecast run (Scripts/plot_forecast_detail.py):
# header with valid time and a spin-up/forecast badge, timeline bar, coastline and data sources.
# Run directory, part (overview, maps, change, anim, anim_temp, anim_salt, cmems, points, log or all)
# and output folder are given when submitting, usually after the run finishes:
#
#   sbatch --dependency=afterok:<ROMS job id> --job-name=detail-anim jobs/plot_forecast_detail.slurm \
#          /projects/f_omg_1/moa/moana/Nikki_run anim <output folder>
#
# The log has the script's output and the total wall time and peak memory (from /usr/bin/time).

source ~/miniforge3/etc/profile.d/conda.sh
conda activate moana_python
cd /home/nn411/Projects/OceanAtm/Moana-2.0

echo "node: $(hostname)   cpu: $(lscpu | sed -n 's/^Model name: *//p')   start: $(date)"
/usr/bin/time -v python -u Scripts/plot_forecast_detail.py "$@"
echo "end: $(date)"