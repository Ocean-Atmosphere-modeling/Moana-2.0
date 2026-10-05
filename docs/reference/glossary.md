# Glossary

| Term | Meaning |
|---|---|
| 4D-Var | Four-dimensional variational data assimilation: fits the model trajectory over a time window to observations by adjusting initial conditions (and optionally forcing and boundaries) |
| ADR | Architecture Decision Record (see [decisions/](../decisions/)) |
| Background | The model state 4D-Var starts from; here, the Phase 1 forward model |
| Blueprint | `blueprint.yaml`: one file naming everything that defines an application |
| CFSR / CFSv2 | Climate Forecast System Reanalysis and its continuation (atmospheric forcing) |
| CPP option | A compile-time switch in the `.h` header that turns ROMS physics or numerics on or off |
| DataMesh | Oceanum's data platform; our route to GLORYS ([ADR-0001](../decisions/0001-datamesh-for-forcing-and-boundaries.md)) |
| EAUC | East Auckland Current |
| Forward model | The nonlinear ROMS model run freely (no assimilation) |
| GLORYS12v1 | Mercator 1/12° global ocean reanalysis (initial and boundary conditions) |
| `.in` file | ROMS run-parameter file (grid size, time step, files, output) |
| LINZ | Land Information New Zealand (tide gauges) |
| OBC | Open boundary condition |
| PGE | Pressure-gradient error: spurious currents over steep bathymetry in s-coordinates |
| Receipt | `receipt.txt` written by `scripts/submit_run.sh`: the code, modules and inputs a run used |
| ROMS | Regional Ocean Modeling System |
| s-coordinate / sigma layers | Terrain-following vertical levels; Moana 2.0 uses 40 ([ADR-0003](../decisions/0003-use-40-vertical-levels.md)) |
| SC | Southland Current |
| Segment | One job in a chain of restarts (`submit_run.sh --segments N`) |
| TL / AD | Tangent-linear and adjoint models, needed by 4D-Var |
| TPXO | Global tide model (OSU) used for tidal forcing |
| UPWELLING | Stock ROMS test case used here as the toolchain and restart test |
