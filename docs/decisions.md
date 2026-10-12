# Decisions

**Last updated:** 2026-10-09

One entry for each decision. Status: Proposed, Accepted, Replaced or Rejected.
Add new entries at the bottom.

## D1 Use DataMesh data only

**Status:** Proposed · **Date:** 2026-10-09 · **Who:** Suman

**Decision:** All model input data comes from Oceanum DataMesh:

- Ocean initial and boundary data: CMEMS GLOBAL_ANALYSISFORECAST_PHY_001_024.
- Atmosphere: ERA5.
- Tides: TPXO9.

**Reason:** Oceanum is the project partner. Oceanum agreed to give us the ocean and atmosphere data on DataMesh.

**Result:**

- The run must start on or after 2022-06-01. The ocean data starts on that date.
- DataMesh does not have all ERA5 fields now. M6 is blocked until Oceanum adds them ([data.md](data.md#atmosphere)).
- DataMesh has no river data (M7-T1).
- We do not copy the Moana paper. Its run is 1993–2020, before our ocean data starts.

## D2 Forward model only

**Status:** Proposed · **Date:** 2026-10-09 · **Who:** Suman

**Decision:** The roadmap covers the forward model run only.

**Reason:** First, we must have a good forward model run.

**Result:** The roadmap has no data assimilation (4D-Var) milestones.

## D3 Simple docs in ASD-STE100

**Status:** Proposed · **Date:** 2026-10-09 · **Who:** Suman

**Decision:** The docs have six pages and the paper. We write them in ASD-STE100 Simplified Technical English.

**Reason:** Simple pages are easy to read and easy to keep correct.

**Result:**

- We deleted the old docs on 2026-10-09. We did not keep the paper-copy plan, its decisions or its data notes.
- Rules for writing:
  - Write one topic in each sentence.
  - Write a maximum of 20 words in an instruction and 25 words in a description.
  - Use the active voice. Use the imperative in instructions.
  - Use one word for one meaning.
  - Write a maximum of 6 sentences in a paragraph.
  - Use tables and lists where possible.
