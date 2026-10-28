#!/bin/bash
#SBATCH --job-name=clm_download_test
#SBATCH --partition=main
#SBATCH --time=06:00:00
#SBATCH --mem=16G
#SBATCH --output=/scratch/nn411/clm_test/clm_download_%j.log

source ~/miniforge3/etc/profile.d/conda.sh
conda activate moana_python
python -u /home/nn411/Projects/OceanAtm/Moana-2.0/Scripts/download_clm.py /home/nn411/Projects/OceanAtm/Moana-2.0/yaml/download_clm_test.yaml