# Moana-2.0 — `nikki` branch

Preparing inputs for the Moana 2.0 ROMS run (January–March 2026) on Amarel.

## Setup

- Conda environment: `moana_python`
- Datamesh token: `DATAMESH_TOKEN`
- Data files (`*.nc`, `Data/`) and logs are not tracked by git

## Atmospheric forcing (ECMWF IFS)

```bash
sbatch jobs/download_atm.sh
```

Output: `Data/atm_ifs_raw_2026-01-01_90D.nc` (3-hourly, 2025-12-31 15:00 → 2026-04-01 00:00)

## Climatology (CMEMS)

Scripts from the `suman` branch.

```bash
sbatch jobs/download_clm_test.slurm   # 1. download raw CMEMS data
python Scripts/clm/make_clm.py temp   # 2. interpolate to ROMS grid (u, v, temp, salt)
```

## Files

| Folder | Contents |
|---|---|
| `Scripts/atm/` | Atmospheric download script |
| `Scripts/clm/` | Climatology scripts (from `suman`) |
| `yaml/` | Settings for each script |
| `jobs/` | Slurm job files |
| `Notebooks/` | Exploration and checks |
