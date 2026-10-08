# Moana-2.0

Adding data assimilation to an ocean model for the New Zealand region in a private sector partnership.

Moana Project:
- Moana (Māori word for "ocean")
- 5 year coastal initiative project designed to improve understanding of New Zealand's coastal ocean circulation, and support it's seafood industry and surrounding marine ecosystem health
  - Key focus areas: marine heatwaves (increasing in frequency and intensity), larval tracking (essential to sustainably manage seafood), ocean circulation, storm surges, and coastal flooding
  - Goals: produce hindcasts, forecasts, and particle tracking models of the region 
- Observational component is the "Te Tiro Moana – Eyes on the Ocean" which aims to (1) use affordable technology to get more observations of the coastal ocean, and (2) make existing observations available to everyone
  - New Zealand has one of the largest ocean territories, but has very little coastal ocean data
  - The project developed a small temperature sensor which can be attached to commerical fishing gear, so fisherman data c    an be input into the ocean model
  - In addition to creating an observational device, this section collects and arrange historical and near real-time tempe    rature and salinity observations

Formal website is available at [Moana Project Website](https://www.moanaproject.org/).

[![Watch the video](https://video.squarespace-cdn.com/content/v1/5fc42b2e3d7b346e5e153624/275bcb1c-15d3-4500-86c5-87d288dda9c2/thumbnail)](https://www.moanaproject.org/project-overview)

| Requirement | What it allows | Why |
|---|---|---|
| Hindcast output to validate against | 1994–2020 | Moana hindcast on THREDDS covers 1993–2020; 1993 was its spin-up |
| Same boundary source as the hindcast | ≤ 2018 | The hindcast used GLORYS for 1993–2018 but Mercator nowcasts for 2019–2020 |
| IC, BC and nudging from Copernicus GLORYS12v1 | any year | Copernicus serves 1993 to 2026-08-25 |
| Atmosphere: CFSR, as in the paper | ≤ 2010 | NCAR's CFSR ends 2011-01-01 03:00; from 2011 only CFSv2 exists, and how the hindcast joined the two is unknown (risk R6) |
| Tides (TPXO) and rivers (climatology) | any year | Neither depends on the year |
| Independent observations | ≥ 2008 | Argo floats are well established by then; LINZ tide-gauge data is online from 2008 |