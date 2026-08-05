# Weather data

The study uses IWEC typical-year EPW files from
https://energyplus.net/weather:

- `SAU_Riyadh.404380_IWEC.epw` — Riyadh, WMO 404380, BWh (hot arid), CDD ~ 3,400
- `SAU_Jeddah.410240_IWEC.epw` — Jeddah, WMO 410240, BSh (hot humid), CDD ~ 2,900

Columns used: field 7 (dry-bulb temperature, C) and field 14 (global horizontal
irradiance, W/m2); the first eight rows are headers.

EPW files are distributed by the U.S. Department of Energy and are not
redistributed here. Copies used by the cross-check code are in
`../reference_implementation/weather/`.
