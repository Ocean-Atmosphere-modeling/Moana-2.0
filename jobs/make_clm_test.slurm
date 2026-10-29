#!/bin/bash
#SBATCH --job-name=clm_make_test
#SBATCH --partition=main
#SBATCH --time=04:00:00
#SBATCH --mem=32G
#SBATCH --output=/scratch/nn411/clm_test/clm_make_%j.log

source ~/miniforge3/etc/profile.d/conda.sh
conda activate moana_python
cd /home/nn411/Projects/OceanAtm/Moana-2.0
for v in zeta; do
    echo "=== $v: $(date) ==="
    python -u Scripts/make_clm.py $v
done
echo "done: $(date)"