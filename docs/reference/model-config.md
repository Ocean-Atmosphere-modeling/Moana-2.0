# Model configuration

**Last updated:** 2026-10-05

Grid, CPP options and run parameters, side by side for three sources:

- **Paper**: Souza et al. (2023), [markdown copy](../hindcast_paper/MoanaHindcast.md) §2.1.
- **Published files**: the authors' `roms3d.h`, `roms.in` and `nz5km_grd.nc`
  from Zenodo [10.5281/zenodo.6484908](https://doi.org/10.5281/zenodo.6484908)
  (GitHub `joaometocean/moana_hindcast`, commit 695d25e). These are fetched by
  `scripts/fetch_published_config.sh`. Unmodified copies sit in `Apps/moana/`;
  their sha256 match the ones the script checks.
- **Moana 2.0**: what this repository uses. The `moana.h` and `roms_moana.in`
  files are not written yet (P1-M2-T01, T02). Only the rows linking an ADR are
  decided; "Start from published" means the published value is the starting
  point and the final choice is made in P1-M2.

Where the paper and the published files disagree, the files are what actually
ran. Every disagreement is also in [risks.md](../risks.md).

## Grid (`nz5km_grd.nc`)

Read from the file with xarray on 2026-10-05.

| Item | Value |
|---|---|
| sha256 | `4209188ebea9bbbfa42e70c1a77642aba6b0a095376deb59d0ed4e0387efccc1` (matches `Apps/moana/inputs.tsv`) |
| Size (ρ-points) | `xi_rho` 397 × `eta_rho` 467, so `Lm = 395`, `Mm = 465` |
| Longitude | 161.03–184.97° E |
| Latitude | 51.98–31.03° S |
| Depth `h` | 10–6000 m (`hraw` also stored) |
| Wet ρ-points | 174,292 |
| Vertical info stored in the file | 40 s-levels, `theta_s = 6.5`, `theta_b = 2.0`, `Tcline = 100`, `hc = 100` (informational only: ROMS takes these from the `.in` file) |
| Also stored | `visc_factor`, `diff_factor`, `angle`, `f`, `pm`, `pn` |
| Made by | `pyroms.grid.write_grd`, 2019-01-07 |

A second copy with an extra coastline (`lon_coast`, `lat_coast`) is at
`/projects/f_omg_1/moa/moana/grd_moana5km.nc`. Its `h`, `mask_rho`, `lon_rho`
and `lat_rho` are identical to the published grid, but its sha256 differs
(`988cd1ae…`) and it is not in `inputs.tsv`. `Moana_grid.ipynb` reads this copy.

## Target settings

| Setting | Paper | Published files | Moana 2.0 |
|---|---|---|---|
| ROMS version | 3.9 | 3.9 (`roms_src/` empty in archive) | 4.x pinned in `roms/` ([ADR-0005](../decisions/0005-roms-version.md)) |
| Grid | ≈ 5 km, 467 × 397 | `Lm = 395`, `Mm = 465` | Published grid ([ADR-0002](../decisions/0002-start-from-published-moana-config.md)) |
| Vertical levels `N` | 50 | 50 (`.in`); grid file stores 40 | **40** ([ADR-0003](../decisions/0003-use-40-vertical-levels.md)) |
| `Vtransform` / `Vstretching` | Souza et al. (2015) stretching | 2 / 5 | 2 / 5 |
| `THETA_S`, `THETA_B`, `TCLINE` | 6, 2, — | 6.0, 2.0, 250 m (`.in`); 6.5, 2.0, 100 m (grid file) | ❓ UNKNOWN (P1-M1-T03) |
| Tracer advection | H: split 3rd-order upstream; V: 4th-order centred | `TS_U3HADVECTION`, `TS_C4VADVECTION` (CPP) and `Hadvection == SU3`, `Vadvection == C4` (`.in`) | `.in` keywords (CPP flags removed in ROMS ≥ 3.8); start from published |
| Vertical mixing | GLS k-kl (≈ MY2.5) | `MY25_MIXING` on, `GLS_MIXING` off (so `GLS_P/M/N` in the `.in` have no effect); `KANTHA_CLAYSON`, `N2S2_HORAVG` | ❓ UNKNOWN ([risk R4](../risks.md)) |
| Horizontal mixing | Tracers along isopycnals; momentum along s | `TS_DIF2` + `MIX_ISO_TS` (`TNU2 = 25`); `UV_VIS2` + `MIX_S_UV` (`VISC2 = 5`) | Start from published |
| Bottom drag | — | `UV_QDRAG`, `RDRG2 = 1.0e-3` | ❓ |
| Time step | — | `DT = 100 s`, `NDTFAST = 44` | Start from published values |
| Tiling | — | `NtileI = 10`, `NtileJ = 10` | Tune in P1-M7-T02 |
| Free-surface boundary | Chapman (implicit) | `Cha` on all edges | Start from published |
| 2D momentum boundary | Flather | `Fla` on all edges | Start from published |
| 3D momentum boundary | Clamped | `RadNud` on all edges (`ad_LBC` uses `Cla`) | ❓ UNKNOWN ([risk R4](../risks.md)) |
| T/S boundary | Radiation + nudging | `RadNud` on all edges | Start from published |
| Nudging | 1 d⁻¹ at edge → 0 over ≈ 200 km | `TNUDG = ZNUDG = M2NUDG = M3NUDG = 1 d`, `OBCFAC = 10`, nudging file; climatology on for 3D momentum and T/S | Start from published, built for 40 levels (P1-M3-T04) |
| Tides | TPXO 7.8.1, 11 constituents | `SSH_TIDES`, `UV_TIDES`, `ADD_FSOBC`, `ADD_M2OBC`; `RAMP_TIDES` off | Start from published |
| Surface fluxes | Bulk, CFSR | `BULK_FLUXES`, `LONGWAVE_OUT`, `SOLAR_SOURCE`, `EMINUSP`; `DIURNAL_SRFLUX` off | Start from published; TL/AD check in P1-M2-T04 |
| Inverse barometer | Yes | `ATM_PRESS`, `PRESS_COMPENSATE` | Start from published |
| Rivers | 42, climatology | `LuvSrc = T`, `LtracerSrc = T T`, file `nz5km_N50_rivers.nc` | Start from published, built for 40 levels (P1-M6-T01) |
| Output | Hourly instantaneous + daily mean | `NHIS = 36` (1 h), `NAVG = 864` (1 d), `NRST = 864` with `LcycleRST = T` | Start from published |
| Restart | — | `PERFECT_RESTART` off | **On**, required by the repo's segment chains (see [REPRODUCIBILITY.md](../../REPRODUCIBILITY.md)) |
| Period | 1993-01-01 → 2020-12-31, 1993 spin-up | The `.in` is one mid-chain segment: `NTIMES = 26784` (31 days), files named `NZB_31/…_202012.nc`, `TIME_REF = 20100101` | (yet to decide), inside 1993–2020 ([ADR-0006](../decisions/0006-published-hindcast-as-benchmark.md)) |

## All CPP options in the published `roms3d.h`

Defined: `CURVGRID`, `PROFILE`, `SPHERICAL`, `MASKING`, `AVERAGES`,
`NO_LBC_ATT`, `SOLVE3D`, `UV_ADV`, `UV_COR`, `UV_QDRAG`, `DJ_GRADPS`,
`RI_SPLINES`, `TS_U3HADVECTION`, `TS_C4VADVECTION`, `SALINITY`, `NONLIN_EOS`,
`SPLINES_VDIFF`, `SPLINES_VVISC`, `UV_VIS2`, `MIX_S_UV`, `TS_DIF2`,
`MIX_ISO_TS`, `MY25_MIXING`, `N2S2_HORAVG`, `KANTHA_CLAYSON`, `ANA_BSFLUX`,
`ANA_BTFLUX`, `ANA_DQDSST`, `BULK_FLUXES`, `SOLAR_SOURCE`, `LONGWAVE_OUT`,
`EMINUSP`, `ATM_PRESS`, `PRESS_COMPENSATE`, `SSH_TIDES`, `UV_TIDES`,
`ADD_FSOBC`, `ADD_M2OBC`, `RADIATION_2D`.

Explicitly off: `STATIONS`, `PERFECT_RESTART`, `VISC_GRID`, `DIFF_GRID`,
`UV_SADVECTION`, `GLS_MIXING`, `DIURNAL_SRFLUX`, `QCORRECTION`, `RAMP_TIDES`.

The ROMS 4.x name of each option is filled in by P1-M0-T07. The TL/AD support
of each option is filled in by P1-M2-T04.

## Input files named in the published `roms.in`

| Role | `.in` keyword | Published file name | Rebuilt by |
|---|---|---|---|
| Grid | `GRDNAME` | `nz5km_grd_N50.nc` (archive holds `nz5km_grd.nc`) | P1-M1 |
| Initial / restart | `ININAME` | `nz5km_rst_202011.nc` | P1-M3-T02 |
| Boundary | `BRYNAME` | `nz5km_N50_bnd.nc` | P1-M3-T03 |
| Climatology | `CLMNAME` | `nz5km_N50_clim.nc` | P1-M3-T04 |
| Nudging coefficients | `NUDNAME` | `nz5km_nudg_N50.nc` (missing from archive) | P1-M3-T04 |
| Rivers | `SSFNAME` | `nz5km_N50_rivers.nc` (missing from archive) | P1-M6-T01 |
| Tides | `TIDENAME` | `nz5km-tide.nc` | P1-M4-T01 |
| Atmospheric forcing | `FRCNAME` | `nz5km_N50_meteo.nc` (one file) | P1-M5-T02 |

Every 3D file named `_N50` has 50 levels and cannot be used with the
40-level model as it is.

## Published build settings (`roms_config.sh`)

For NeSI Mahuika (`/nesi/project/mocean02574/...`): `ROMS_APPLICATION=ROMS3D`,
`USE_MPI=on`, `USE_NETCDF4=on`, `USE_LARGE=on`, `USE_ARPACK=on`,
`UPDATE_VARINFO=on`, `FC=ifort`, NetCDF 4.4.1 (intel-2017a). Our build is
`scripts/build_roms.sh` with the modules in `env/amarel.sh`
([environment](environment.md)).
