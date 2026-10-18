# Moana-2.0
Adding data assimilation to an ocean model for the New Zealand region in a private sector partnership

## Quick start

```bash
git clone --recurse-submodules git@github.com:Ocean-Atmosphere-modeling/Moana-2.0.git
cd Moana-2.0
source env/amarel.sh
```



Project documentation (roadmap, data, decisions) starts at
[docs/README.md](docs/README.md).

### Step 1: Raw Input data download from oceanum datamesh server
#### Configure Yaml file with your shopping list
 It's a simple one step of downloading all the data you need to run ROMS forward model, by editing the IDs corresponding to the IC/BC/Atm/Tides in a yaml file, which the python script refer for downloading the data.
 
Edit `download_input.yaml` (path is set at the top of `main()` in the script):
 
| key          | meaning                                                            |
|--------------|--------------------------------------------------------------------|
| `name`       | label used in the output filename                                  |
| `DATASOURCE` | DataMesh datasource id (find it with `--list`)                     |
| `VARIABLES`  | variable names **as the datasource uses them** (e.g. `[uo, vo]`)   |
| `VAR_NAME`   | short tag for the filename                                         |
| `DATE`       | start date, `YYYY-MM-DD`                                           |
| `PERIOD`     | time span from `DATE`, e.g. `1D`, `31D` (all steps in range kept)  |
| `OUTPUT_DIR` | where the file is written (created if missing)                     |
| `GRID`       | ROMS grid file; bbox taken from its `lon_rho`/`lat_rho` (+0.5°). `null` → use `NZ_BBOX` |
 
#### Run the download engine
 
```bash
python get_datamesh_ic.py --list     # search the catalog for datasource ids
python get_datamesh_ic.py            # download using the config
```
 
Output: `OUTPUT_DIR/<name>_<VAR_NAME>_raw_<DATE>.nc`