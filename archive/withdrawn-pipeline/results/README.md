# Results summary

Model S, seeds {42,43,44,45,46}, mean +/- std over all five seeds, 30 held-out
test weeks. Two evaluation horizons are reported and must not be conflated.
The cumulative-energy state includes a non-HVAC household base load of
E_base ~ 800 kWh/month, so the step-wise tariff is active (Riyadh 4x4 reaches
~2,710 kWh/month and crosses the 2,000 kWh tier boundary around day 22).

## Monthly billing horizon (720 h) — quoted in the abstract

| City   | Config | THERM (SAR/zone/mo) | RBRL | Saving |
|--------|--------|---------------------|------|--------|
| Riyadh | 1x1    | 64.6 | 52.7 | 18.4 % |
| Riyadh | 1x4    | 68.5 | 55.7 | 18.7 % |
| Riyadh | 2x2    | 67.0 | 54.5 | 18.7 % |
| Riyadh | 4x4    | 73.0 | 59.7 | 18.2 % |
| Jeddah | 1x1    | 58.9 | 49.5 | 16.0 % |
| Jeddah | 1x4    | 61.5 | 51.2 | 16.7 % |
| Jeddah | 2x2    | 60.2 | 50.2 | 16.6 % |
| Jeddah | 4x4    | 65.5 | 54.5 | 16.8 % |

## Weekly horizon (168 h) — daily cost, 4x4

| City   | Model | THERM (SAR/zone/day) | GA   | RBRL | Saving |
|--------|-------|----------------------|------|------|--------|
| Riyadh | L     | 2.05 | 1.86 | 1.73 | 15.6 % |
| Riyadh | E     | 2.13 | 1.93 | 1.80 | 15.5 % |
| Riyadh | S     | 2.42 | 2.16 | 1.98 | 18.2 % |
| Jeddah | L     | 1.85 | 1.67 | 1.58 | 14.6 % |
| Jeddah | E     | 1.92 | 1.73 | 1.64 | 14.6 % |
| Jeddah | S     | 2.17 | 1.93 | 1.81 | 16.6 % |

The monthly and weekly percentages differ by up to ~1.5 pp for the smaller
topologies: only over a full billing month does cumulative consumption traverse
the tariff tiers, changing the marginal price both controllers face.

## Component ablation (4x4, Riyadh, Model S)

`n/r` = not separately recorded in the manuscript.

| Variant             | J/Nz (SAR)    | v_c (%) | f_s | delta vs RBRL |
|--------------------|---------------|---------|-----|---------------|
| THERM (rules only) | 2.42 +/- 0.18 | 0.0     | 5.0 | +22.2 %       |
| GA                 | 2.16 +/- 0.15 | 0.0     | 3.3 | +9.1 %        |
| SA                 | 2.19 +/- 0.16 | 0.0     | n/r | +10.6 %       |
| RL only (no rules) | 2.03 +/- 0.22 | 0.5     | 2.6 | +2.5 %        |
| RBRL, hard rules   | 2.05 +/- 0.15 | 0.0     | 2.8 | +3.5 %        |
| **RBRL full**      | **1.98 +/- 0.13** | **0.0** | **2.5** | — |

## Cost-model mismatch (train on X, evaluate under S)

| Training model | True J/Nz (SAR) | Penalty |
|---------------|------------------|---------|
| Linear (L)    | 2.24 +/- 0.14    | +13.1 % |
| Exponential   | 2.11 +/- 0.13    | +6.6 %  |
| Step-wise (S) | 1.98 +/- 0.13    | —       |

## Robustness

| Axis | Evidence | Spread |
|---|---|---|
| Seeds | 5 seeds, no best-of-n | inter-run variance < 2 % of mean cost |
| Topology | 7 configurations, 1-16 zones | 17.0-18.6 % |
| Climate | hot-arid vs hot-humid | 18.2 % / 16.8 % |
| Season | all 12 months | positive saving every month |
| Thermal capacity | 77.2 -> 500 -> 1200 kJ/K | 18.2 -> 17.4 % |
| Switching cost | c_sw 0 -> 0.30 SAR | monotone trade-off, comfort held |
| Horizon | weekly and monthly | <= 1.5 pp |

Cross-check: the 1x1 Model S RBRL cost of 1.75 SAR/zone/day appears
independently in the cost-model table and in the switching-cost sensitivity
study at the default c_sw.

## Provenance

These values are transcribed from the manuscript's tables. To make the artifact
self-verifying, add the raw run logs or a results JSON emitted by `src/` so each
number traces to an execution.

## Limitations (as stated in the paper — seven items)

1. **Sensible heat only** — latent loads add ~54 % in Jeddah, ~18 % in Riyadh;
   applies to both controllers, so percentage savings are preserved.
2. **Air-mass thermal capacity** — C_th = 77.2 kJ/K; sensitivity across
   77–1200 kJ/K shows <1 pp variation, in the conservative direction.
3. **No occupancy or internal gains** — direction is *two-sided*: omitted evening
   gains (~18:00–23:00) fall in the costliest part of the billing month, while an
   explicit occupancy schedule would permit setback the present formulation
   forgoes.
4. **Perfect 3-step forecast** — the one clearly optimistic idealisation.
5. **Simulation only** — EnergyPlus co-simulation and hardware-in-the-loop
   validation are committed as next steps.
6. **No MPC baseline** — excluded on tractability grounds; GA and SA are included
   as offline optimisation comparators, alongside the DP optimality bound.
7. **Two cities, one building type** — Riyadh and Jeddah bracket the Saudi
   climate extremes but do not cover mild or heating-dominated climates.

Earlier summaries of this repository listed only five of these; items 6 and 7
are also in the manuscript.
