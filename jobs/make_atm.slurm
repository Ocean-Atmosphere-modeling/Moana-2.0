#!/bin/bash
#SBATCH --job-name=make-atm
#SBATCH --partition=p_omg_1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/projects/f_omg_1/moa/moana/oceanum_input/atm_forcing/logs/%x_%j.log
#
# Same layout as jobs/make_clm.slurm. Make the ROMS atmospheric forcing file from the raw IFS
# file (Scripts/atm/make_atm_forcing.py). The yaml (INPUT, OUTPUT, REF_TIME) is given when submitting:
#
#   sbatch jobs/make_atm.slurm yaml/make_atm_forcing.yaml
#
# The log has the script's output and the total wall time and peak memory (from /usr/bin/time).

source ~/miniforge3/etc/profile.d/conda.sh
conda activate moana_python
cd /home/nn411/Projects/OceanAtm/Moana-2.0

echo "node: $(hostname)   cpu: $(lscpu | sed -n 's/^Model name: *//p')   start: $(date)"
/usr/bin/time -v python -u Scripts/atm/make_atm_forcing.py "$@"
echo "end: $(date)"