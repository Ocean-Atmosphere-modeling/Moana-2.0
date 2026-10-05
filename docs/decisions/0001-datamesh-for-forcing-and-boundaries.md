# ADR-0001: Fetch ocean boundary data through Oceanum DataMesh

**Status:** Accepted · **Date:** 2026-09-29 (first recorded in the todo list) · **Deciders:** ❓ UNKNOWN

## Context
Oceanum is the project's commercial partner, and DataMesh is its data
platform. The model needs GLORYS12v1 (and the nowcast that continues it) for
initial, boundary and nudging fields over the run period. GLORYS was the best of
four global reanalyses for NZ (Souza et al., 2020, cited in the paper).

## Options considered
| Option | Pros | Cons |
|---|---|---|
| DataMesh (`oceanum` Python package) | One query returns the domain subset as xarray; the partner's own platform; same route for later data | Needs a token; not confirmed that it exposes the upstream GLORYS version; datasources can change in place |
| Copernicus Marine directly (`copernicusmarine` toolbox) | Reports the exact product version | Separate account; not the partner's route |

## Decision
Fetch GLORYS through DataMesh. Spot-check one day against Copernicus Marine.

## Consequences
- Every fetch records datasource ID, query, `oceanum` version and fetch date in `inputs.tsv` (P1-M3-T01).
- The token lives in `$DATAMESH_TOKEN` only.
- Risk that a datasource changes in place: [risk R9](../risks.md).
- Whether CFSR and observations also come through DataMesh: ❓ UNKNOWN.
