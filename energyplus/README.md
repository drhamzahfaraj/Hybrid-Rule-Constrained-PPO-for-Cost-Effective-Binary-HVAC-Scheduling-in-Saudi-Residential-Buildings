# EnergyPlus Validation (Future Work)

Planned validation protocol:
1. Create IDF models matching RC parameters (4×4×4m, SBC 2018)
2. Compare RC vs EnergyPlus hourly temperatures (target RMSE < 1°C)
3. Apply RBRL schedules to EnergyPlus and measure actual savings gap

Literature precedent: Bacher & Madsen (2011) showed 0.3–0.5°C RC prediction error.
Deng et al. (2022) confirmed <5% error vs EnergyPlus for binary on/off.

Requires: EnergyPlus 23.2+, eppy, geomeppy
