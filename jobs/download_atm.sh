#!/bin/bash
#SBATCH --job-name=atm_download
#SBATCH --partition=main
#SBATCH --time=06:00:00
#SBATCH --mem=16G
#SBATCH --output=atm_download_%j.log

source ~/miniforge3/etc/profile.d/conda.sh
conda activate moana_python
python -u /home/nn411/Projects/OceanAtm/Moana-2.0/Scripts/download_atm.py