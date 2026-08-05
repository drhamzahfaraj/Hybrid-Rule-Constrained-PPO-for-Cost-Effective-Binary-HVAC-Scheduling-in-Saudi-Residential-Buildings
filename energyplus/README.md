# EnergyPlus co-simulation (future work)

Planned validation protocol, as committed in the paper's Limitations:

1. Build IDF models geometry-matched to the RC parameters (4x4x4 m zones,
   SBC 2018 envelope).
2. Compare RC and EnergyPlus hourly zone temperatures (target RMSE < 1 C).
3. Apply RBRL schedules within EnergyPlus and measure the realised savings gap
   under full envelope, solar and infiltration physics.
4. Follow with a hardware-in-the-loop test on a residential split unit.

Literature precedent: Bacher and Madsen (2011) report 0.3-0.5 C RC prediction
error against measured data; Deng et al. (2022) report under 5 % deviation
against EnergyPlus for binary on/off systems in cooling-dominated climates.

Requires: EnergyPlus 23.2+, eppy, geomeppy.
