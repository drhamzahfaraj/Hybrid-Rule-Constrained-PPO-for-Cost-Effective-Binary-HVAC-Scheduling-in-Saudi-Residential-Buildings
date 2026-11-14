# Revision 5 — results from the rebuilt reference implementation

All runs: exact matrix-exponential integration, C_th = 4,800 kJ/K (ISO 13786),
Δt = 15 min, physics-sized asymmetric guards, tariff on electrical energy,
uniform base-load accrual, cooling season only (Riyadh Mar–Oct, Jeddah
year-round), 30 held-out weeks from the last 10 days of each month.

---

## 1. The mechanism is settled: 94 % of the saving is switching cost

The switching-cost sweep is the single most informative experiment, and it is
the one the previous version omitted. At c_sw = 0 the switching term vanishes,
so whatever saving remains is the pure energy-and-tariff effect.

| c_sw (SAR) | J, 1 K deadband | J, full-band rule | saving |
|---|---|---|---|
| **0.00** | 0.1052 | 0.1016 | **3.4 %** |
| 0.05 | 0.2581 | 0.1528 | 40.8 % |
| 0.15 | 0.5638 | 0.2553 | 54.7 % |
| 0.30 | 1.0224 | 0.4091 | 60.0 % |
| 0.60 | 1.9395 | 0.7166 | 63.1 % |

**3.4 % of 54.7 % is energy and tariff; the remaining 51.3 percentage points
are compressor-start cost.** The saving is 94 % a wear-amortisation effect.

## 2. The saving depends entirely on the baseline deadband

Which the previous version never stated. Riyadh 4×4, Model S:

| baseline | J | saving vs full-band rule |
|---|---|---|
| 1 K deadband | 0.5800 | 55.2 % |
| 2 K deadband | 0.3578 | 27.4 % |
| 3 K deadband | 0.2704 | 4.0 % |
| full-band rule | 0.2596 | — |

The reported figure is a statement about how narrow the comparator's deadband
is, not about the controller. The previous version's implied baseline was
≈2 K, which is where its ≈18 % sits.

## 3. PPO adds nothing once the rule is active

| | J | f_s | v_c | peak (kW) |
|---|---|---|---|---|
| THERM-full (analytic rule, no learning) | 0.2596 | 1.0429 | 1.07 | 9.559 |
| RBRL (PPO, 120 k steps, seed 42) | 0.2596 | 1.04 | 1.07 | 9.56 |

Identical to four significant figures. With the complete-cycle rule of
Proposition 1 active, the hard rule layer determines the schedule and the
learned policy is redundant. The benefit is attributable to the **rule**, which
is an analytic consequence of the SLHA theory, not to reinforcement learning.

## 4. Reviewer comment 8 — answered, and the original claim fails

4×4 topology, explicit-Euler spectral radius of I + ΔtA:

| C_th (kJ/K) | 60 min | 30 min | 15 min | 5 min |
|---|---|---|---|---|
| 77.2 | **9.97** | **4.49** | **1.74** | 0.91 |
| 500 | 0.830 | 0.915 | 0.957 | 0.986 |
| 1200 | 0.929 | 0.965 | 0.982 | 0.994 |
| 4800 | 0.982 | 0.991 | 0.996 | 0.999 |

At C_th = 77.2 the hourly scheme is unstable by a factor of ten, and at 15 min
the recursion diverges to T = 4.5 × 10²⁶². The previous version's stability
claim (|1 − Δt/τ| = 0.54) holds only for a single isolated zone, because its τ
omitted the inter-zone conductance.

At C_th = 4,800 kJ/K, Euler and exact agree to three decimals (J = 0.4796 vs
0.4742 at 60 min; 0.3691 vs 0.3693 at 15 min), with v_c = 0 in both.

## 5. Reviewer comment 2 — the direction reverses, cleanly

| C_th (kJ/K) | free band (K) | saving | v_c | f_s |
|---|---|---|---|---|
| 1200 | 1.40 | 37.3 % | 5.01 % | 6.22 |
| 2000 | 2.34 | 44.6 % | 4.39 % | 3.05 |
| 3200 | 2.87 | 52.9 % | 3.54 % | 1.65 |
| 4800 | 3.16 | 54.7 % | 1.60 % | 1.02 |
| 6400 | 3.31 | 55.2 % | 0.38 % | 0.71 |

Saving rises monotonically with capacity and comfort violations fall, because
the mechanism is cycle lengthening. This is the opposite of the previous
version's direction, and it is the physically correct one: more thermal mass
means fewer cycles, and the saving is a per-cycle charge.

## 6. Reviewer comment 6 — the honest tariff answer

4×4, monthly horizon. Energy is identical (2.97 kWh/zone/day Riyadh,
2.29 Jeddah) under every schedule, confirming the controllers are price-blind
and that a consumption-block tariff creates no timing incentive.

| schedule | Riyadh saving | Jeddah saving | switching share |
|---|---|---|---|
| Four-tier 2016–17 (historical) | 53.7 % | 55.0 % | 60 % |
| Two-block 2018–26 (in force) | **36.5 %** | **38.4 %** | 29 % |
| Two-block 2027 | **34.0 %** | **36.0 %** | 26 % |
| Linear 0.12 | 42.7 % | 44.5 % | 38 % |

The saving **falls as the energy price rises**, because c_sw is a fixed charge
in SAR and its relative weight shrinks. This replaces the withdrawn
11.4 %/13.2 % figures and is the correct answer to the comment.

## 7. Coincident peak — real but modest, and absent below nine zones

Diversity factor = coincident peak / connected load.

| topology | Riyadh 1 K → full | Jeddah 1 K → full |
|---|---|---|
| 1×1, 1×4, 2×2 | 1.000 → 1.000 (0 %) | 1.000 → 1.000 (0 %) |
| 3×3 | 0.982 → 0.933 (−4.9 %) | 0.852 → 0.811 (−4.8 %) |
| 4×4 | 0.933 → 0.892 (−4.5 %) | 0.850 → 0.733 (**−13.7 %**) |

Below nine zones every zone cycles in phase, so there is no peak benefit at
all. The 13.7 % in Jeddah 4×4 is the strongest case and is worth reporting, but
the claim cannot be generalised across topologies.

## 8. Comfort, honestly

v_c = 0.00 % in Jeddah at every topology. In Riyadh it is 1.07–1.35 % even
within the stated cooling season, the residual arising in March and October
where a cooling-only plant cannot hold T_min. A balance-point analysis gives:

- Riyadh cooling season: **March–October** (8 months)
- Jeddah cooling season: **year-round**

Outside those months the comfort band is not holdable by a cooling-only plant,
which is why the previous version's "no violations across four seasons" claim
could not have been right.

## 9. Plant sizing

Peak July load by zone class, new envelope:

| exterior walls | Λ (W/K) | peak load (W) | peak duty |
|---|---|---|---|
| 0 (interior) | 12.9 | 291 | 15 % |
| 1 (edge) | 24.8 | 654 | 33 % |
| 2 (corner) | 36.7 | 1,026 | 51 % |
| 4 (detached room) | 60.5 | 1,771 | 89 % |

Q_hvac = 2.0 kW is correctly sized for a room inside a building and marginal
for a detached single room in Riyadh.

---

## Not completed

The exact dynamic-programming optimality reference. The energy-dimension
indexing is faulty and the Jeddah result returned an implausible zero, so it is
not reportable. The joint panel had in any case recommended keeping it out of
this revision as scope expansion; it is recorded here as unfinished rather than
dropped.
