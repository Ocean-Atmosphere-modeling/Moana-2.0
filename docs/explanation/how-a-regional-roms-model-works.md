# How a regional ROMS model works

ROMS solves the ocean equations on a grid. It knows nothing about New Zealand
until it is given files that describe **where** (grid), **what it starts
from** (initial conditions), **what drives it** (open-ocean boundaries,
tides, atmosphere, rivers) and **how to compute** (compile options and run
parameters). Everything after that is checking that the solution is physical.

```
                 ┌──────────────── HOW TO COMPUTE ─────────────────┐
                 │  moana.h        (CPP options: physics, numerics) │
                 │  roms_moana.in  (dt, tiling, files, output)      │
                 └───────────────────────┬──────────────────────────┘
                                         │ build (scripts/build_roms.sh)
                                         ▼
 WHERE                                ┌──────┐                      OUTPUT
 grid  (lon/lat, bathymetry h,     ──▶│      │──▶ his  hourly instantaneous
        land mask; 40 s-levels)       │      │──▶ avg  daily means
                                      │ ROMS │──▶ rst  restart (to continue)
 START FROM                           │      │
 ini   (T, S, u, v, ζ at start)    ──▶│      │           │
                                      │      │           ▼
 WHAT DRIVES IT                       │      │      EVALUATION
 bry   GLORYS T,S,u,v,ζ at edges   ──▶│      │      statistics vs the        
 clim + nudging (sponge)           ──▶│      │      published Moana hindcast     
 tide  TPXO 11 constituents        ──▶│      │      (means, variances,   
 frc   CFSR wind, air T, humidity, ──▶│      │      tides, transports)   
       rain, SW, LW, pressure         │      │
 rivers 42 NZ rivers (climatology) ──▶│      │
                                      └──────┘
```

## The pieces, and why each matters

- **Grid and bathymetry.** Depth `h` steers the flow: boundary currents, shelf
  upwelling, canyons (Kaikōura, Pegasus), tides. The mask decides which cells
  are ocean. Cook Strait is only about 3 cells wide at 5 km, and the paper
  blames that for its low transport.
- **Vertical levels.** ROMS layers follow the seafloor (s-coordinates). A thin,
  stable top layer matters for SST, and for assimilating SST later. Steep
  slopes in s-coordinates create spurious currents (pressure-gradient error),
  which is why the bathymetry is smoothed only where a test at rest shows
  bottom speeds above 1 cm s⁻¹.
- **Open boundaries.** The ocean outside the domain drives the large currents
  (EAUC, Tasman Front, ACC branch). Near the edges, T and S are nudged towards
  GLORYS so the interior and exterior do not drift apart.
- **Tides.** Tides explain more than 98 % of sea-level variance at NZ tide
  gauges and drive mixing on the shelf. Global reanalyses leave them out, so
  they are added at the boundary from TPXO.
- **Atmosphere.** Wind, heat and freshwater fluxes are computed from CFSR
  fields with bulk formulae. Air pressure also pushes sea level down (inverse
  barometer, about −1 cm per hPa).
- **Rivers.** Freshwater changes coastal density, for example the Waihou and
  Piako rivers in the Firth of Thames.
- **Evaluation.** The free run's statistics are compared with the published
  Moana hindcast before it is trusted as a 4D-Var background. Observations
  come in with 4D-Var itself.

Where these are in our setup: [architecture](../02-architecture.md). Values:
[model configuration](../reference/model-config.md).
