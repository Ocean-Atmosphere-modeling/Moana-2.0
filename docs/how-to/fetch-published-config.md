# How to fetch the published Moana configuration

**Goal:** the published grid, `roms.in`, `roms3d.h` and `roms_config.sh` in `$MOANA_DATA/published/moana_hindcast_v1.0/`, checksums verified.
**Time:** ❓ UNKNOWN (one download from Zenodo)

## Prerequisites
- Internet access from the node you run on
- A data folder for `$MOANA_DATA` (❓ UNKNOWN: not chosen yet, P1-M0-T08)

## Steps
1. Set the data folder and fetch.
   ```bash
   export MOANA_DATA=<input data folder>
   scripts/fetch_published_config.sh
   ```
2. Check the grid against the manifest.
   ```bash
   scripts/check_inputs.sh Apps/moana/inputs.tsv
   ```

## Check it worked
The script ends with `Published configuration is in …`, and `check_inputs.sh`
reports the grid `OK`.

## If it goes wrong
| Symptom | Likely cause | Fix |
|---|---|---|
| `set MOANA_DATA to the input data folder` | `MOANA_DATA` not set | Export it |
| `… is not the published archive` | Partial or different download | Delete the zip and run again |
| `check_inputs.sh` says `MISSING` | Grid is somewhere else (for example `Apps/moana/`) | Move it to `$MOANA_DATA/published/moana_hindcast_v1.0/` |

The archive has no licence: don't commit these files ([risk R12](../risks.md)).
What is in them: [model configuration](../reference/model-config.md).
