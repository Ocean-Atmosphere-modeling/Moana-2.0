#!/bin/bash
#SBATCH --job-name=make-clm
#SBATCH --partition=p_omg_1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=/projects/f_omg_1/moa/moana/oceanum_input/climatology/logs/%x_%j.log
#
# Based on Suman's scripts/make_bry.slurm. Make one ROMS climatology file from the raw DataMesh
# files (Scripts/make_clm.py). The variable is given when submitting:
#
#   sbatch --job-name=make_u jobs/make_clm.slurm u        # u, v, temp, salt or zeta
#
# The log has the time of each record (from make_clm.py)
# and the total wall time and peak memory (from /usr/bin/time).

source ~/miniforge3/etc/profile.d/conda.sh
conda activate moana_python
cd /home/nn411/Projects/OceanAtm/Moana-2.0

echo "node: $(hostname)   cpu: $(lscpu | sed -n 's/^Model name: *//p')   start: $(date)"
/usr/bin/time -v python -u Scripts/make_clm.py "$@"
echo "end: $(date)"