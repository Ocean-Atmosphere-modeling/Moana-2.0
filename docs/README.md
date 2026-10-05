# Moana 2.0: Start here

> A reproducible 5 km ROMS forward model of New Zealand waters, rebuilt from the published Moana hindcast, to be the background model for ROMS 4D-Var. Built with Oceanum as commercial partner.

**Last updated:** 2026-10-05

## Status at a glance
| Phase | Goal | Status | Target date | Exit criteria met |
|---|---|---|---|---|
| P1 | Forward model: 5 km, 40 levels, pinned ROMS 4.x; statistics checked against the published hindcast | 🔄 | (yet to decide) | 0/5 |
| P2 | ROMS 4D-Var on the forward model | 🔲 | (yet to decide) | (criteria yet to decide) |

P1 progress: M0 Foundations 3/10 tasks done; M1 Grid 1/4 done (published
grid adopted); M2–M9 not started. Details: [roadmap](01-roadmap.md).

## Next three actions
| Task ID | Action | Owner | Blocked by |
|---|---|---|---|
| P1-M0-T06 | Ask the authors for the nudging file, rivers file, `roms_src/` and input scripts | (yet to decide) | — |
| P1-M0-T08 | Choose `$MOANA_DATA`, set it in `env/amarel.sh`, move the grid there | (yet to decide) | — |
| P1-M1-T03 | Choose `THETA_S`, `THETA_B`, `TCLINE` for the 40-level grid | (yet to decide) | — |

## Where to find things
| I want to… | Go to |
|---|---|
| Understand why this project exists | [Brief](00-brief.md) |
| See what's planned and what's done | [Roadmap](01-roadmap.md) |
| Understand how the system fits together | [Architecture](02-architecture.md) |
| Know why we chose X | [Decisions](decisions/) |
| Run something | [How-to guides](how-to/) |
| Look up a dataset, parameter, or path | [Reference](reference/) |
| Understand the background | [Explanation](explanation/) |
| Find a past model run | [Run log](experiments/run-log.md) |
| See what's risky or undecided | [Risks](risks.md) |
| See what changed recently | [Devlog](devlog.md) |
| Reproduce a run | [REPRODUCIBILITY.md](../REPRODUCIBILITY.md) |
| Read the original paper | [Moana hindcast (markdown)](hindcast_paper/MoanaHindcast.md) |
| See the old todo list | [Archive](archive/BUILD_TODO.md) |
