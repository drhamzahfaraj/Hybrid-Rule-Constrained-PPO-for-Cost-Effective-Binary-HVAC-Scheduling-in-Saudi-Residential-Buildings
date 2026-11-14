# R4_simulation: Building Energy Simulation Specialist, final verification panel (round 4)

Reviewer role: Specialist Reviewer R4, Building Energy Simulation (agents/building_simulation_reviewer_agent.md)
Scope: how well the plant model supports the claims (RC model, capacity choice and its sensitivity, COP, internal and solar gains), weather and windows (TMYx vs actual years), tariff, comfort metric, train/test weather separation, actuation-step study and 0.1 °C hardware resolution, multi-zone model, completeness of Limitations, and the journal's Comments 2 and 8.
Read: main.tex (all of Sections 3, 6, 7, 8.3, 8.4, 9.2, 9.3, 10, 11, abstract), supplement.tex (S1, S2, S5, S6, S-MZ), RESPONSE_LETTER.md (Summary, Comments 1, 2, 3, 6, 8, 9), the journal's outstanding-comments docx, and code in /home/claude/rbrl_p12 (config.py, headroom.py, mz_r3.py, mz_mpc.py, amy_fetch.py, amy_spread.py, rbrl_ppo.py), read only.

## Overall assessment

The rebuilt simulation is much more defensible than the version the journal reviewed. Forward Euler is replaced by the exact zero-order-hold solution. The capacity (4,800 kJ/K, 50 kJ m⁻² K⁻¹ over 96 m², τ = 56 h) is derived and swept from 2,400 to 9,600 kJ/K with every arm refitted. The actuation condition Q·Δt/C ≤ δ_db is derived and checked. The step is swept at 5, 15, 30 and 60 min, and the manuscript now says plainly that the savings change materially with it. The tariff is the one in force, and the account is shown to stay in the first block. Tuning and held-out windows are separated and listed by date. The model is labelled as an uncalibrated reference, with no ASHRAE G14 claim. The Limitations section is long and mostly candid.

Every number I checked against the CSVs matches, with one rounding slip. Four MAJOR issues remain:
- two plant-fidelity gaps that the Limitations do not fully explain (internal gains; outdoor-dependent capacity and COP);
- a false statement about forward-Euler stability, in the very passage that answers Comment 8;
- the reference capacity is, on the authors' own argument, an upper estimate of the capacity that acts at the cycle period, yet the text does not draw the consequence for the headline.

Each MAJOR issue can be fixed in the text alone. Optional runs are suggested where they would close the point outright.

## Simulation credibility summary

| Aspect | Status | Evidence location | Comment |
|---|---|---|---|
| Model fidelity vs claims | WEAK | Sec. 3.1, Remark 1, Table 2, Sec. 10.4 | Single node, sensible only. No internal gains (M1). Constant Q and COP (M2). No opaque-wall solar and one exposed face (m7). Comfort is checked on the lumped node temperature (m14). Claims are limited to relative on-command savings, which is appropriate. |
| Calibration / validation (G14) | MISSING, declared | Sec. 10.2, S1 | Correctly labelled as an uncalibrated reference. No absolute claims. Acceptable. |
| Weather & period | OK | Sec. 6.1, S5 | TMYx with WMO IDs and years. Plane-of-array transposition stated. Actual years from ERA5. Hourly forcing is held over sub-steps without disclosure (m2). The actual-year CDD base is undefined (m10). |
| Tariff & peak definition | OK | Sec. 3.4, Remark 3, Sec. 7 | In-force tariff, 884 kWh/month, first block, constant marginal price. No peak claim is made. |
| Comfort metric | OK, with caveats | Sec. 7 "Comfort", Rules A–C | Hard ceiling, commanded under-temperature, clipped mean. Matching to 0.03 K is below sensor accuracy (m4). Band contradiction (m5). |
| Train/test separation | OK | Sec. 7 "Evaluation protocol" | 6 tuning and 7 held-out non-overlapping windows. PPO is trained on TUNE_W only (verified in rbrl_ppo.py:269). Actual-year transfer is tested for TUNED. |
| Sensitivity / uncertainty | WEAK | Tables 7, 8, S1, S2, S5 | Capacity, step, deadband, c_sw, tariff, orientation and actual years are covered. Internal gains and outdoor-dependent plant performance are not (M1, M2). |
| Reproducibility of model | OK | Data & Code section, gate log | Gate passes 188/188 invariants (gate_p12.log). Stale multi-zone files sit in results/ (m12). |

## Verification against results files

All of the following match to the printed precision:
- **Capacity sweep** (`T1v3_heldout_cth{2400,7200,9600}.csv`, `T21v3_riyadh_cth*.csv`): TUNED −2.78/12.53/16.02/15.82 (Riyadh); Jeddah −1.43 → 15.83; Taif −1.26 → 16.04; Jeddah and Taif at 7,200 kJ/K: 16.71, 17.72. MPC-24: 12.25/18.26/19.80/16.17. On-commands: −4.04/22.83/34.64/39.81. ΔT at 7,200: 0.033/0.040/0.121; at 9,600: −0.019/+0.029/−0.018. Planner at 9,600: ΔT −0.0445 K, energy −2.51%, on-commands avoided 42.35 → 40.74.
- **Step sweep** (`T1v3_heldout_dt5/dt30.csv`, `T21v3_*_dt30.csv`, `T21v3_riyadh_dt5.csv`, `T2v3_timestep.csv`, `T17v3_*_dt*.csv`):
  - TUNED: 24.97/24.78/25.68 at 5 min and −1.23/−1.53/−1.20 at 30 min.
  - On-commands: 43.1/41.9/43.0 at 5 min and −2.4/−2.8/−2.2 at 30 min.
  - MPC-24: 23.80 at 5 min (pooled_0.10, ΔT −0.078); 6.56/11.42/11.28 at 30 min.
  - B*: 27.3; 10.9/13.9/14.7; 20.0/19.9/21.0; at 7,200 kJ/K, 20.0.
  - TUNED reaches 25.0/27.3 = 92% of the Riyadh bound at 5 min.
- **0.1 °C hardware grid** (`T1v3_sens.csv`, variant hw_0.1K): 5.75/7.40/8.37% saving and 10.5/13.2/14.7% on-commands avoided, all at 23.6/22.4.
- **Deadband** (`T7v3_deadband.csv`): 40.2/23.4/12.5/5.7 (Riyadh); THERM 7.37/5.22/4.10/3.45 on-commands per day.
- **Orientation** (`T24v3_orientation.csv`): 13.3/12.7/12.5/12.2. **Actual years** (`T23v3_amy_spread.csv`): Riyadh rows match S5.
- **Multi-zone rules** (`T31_mz_rules_riyadh_*_lij*.csv`): every TUNED and guard cell of Table S-MZ matches.
- **Physics checks by hand**:
  - Q·Δt/C = 0.125/0.375/0.75/1.5 K.
  - τ = 4,800/23.75 → 56.1 h.
  - Store 4,800 × 2 K / 2.985 → 0.893 kWh.
  - Infiltration 0.6 ACH × 64 m³ at 24 °C indoor air → 11.85/12.72/10.77 W/K.
  - SASO EER conversions 3.46/2.43.
  - ∂E/∂⟨T⟩ = 24 × 0.670 × 23.75/2000 = 0.191 kWh/day/K.

One mismatch, m1 below.

## Findings

### MAJOR

**M1. No internal gains, and the omission is neither swept nor bounded.**
- *Location:* Sec. 7, l.1573: "The RC model has no occupancy or internal gains." Limitations, l.2495–2500: "Occupancy, lighting and appliance gains are excluded, which flatters any setback's recovery."
- *What is wrong:* For a 4×4×4 m occupied room, sensible gains from two occupants plus lighting and appliances are of order 150–300 W. The single-face envelope load is Λ(T_out − T) ≈ 23.75 × 12 ≈ 285 W in a Riyadh cooling-season mean. The omitted gains are therefore of the same order as the whole modelled load. They change the free-float time, which S1 gives as 8.0 h at the median and 4.3 h at the 95th-percentile load, and they change the on/off phase lengths. These are the quantities that, through Q·Δt/C, make TUNED's saving swing from −2.8% to 15.8% in the capacity sweep.
- *What the Limitations say:* only the effect on setback recovery. They say nothing about the headline TUNED/MPC comparison, whose direction is not established.
- *Evidence:* no internal-gain term in eq. (1) or in the code (grep for internal gain or q_int in /home/claude/rbrl_p12 returns nothing). No sweep exists in results/.
- *Fix (one of):*
  - (a) Run Riyadh TUNED and MPC-24 under Rule A with a constant sensible gain of 150 and 300 W, or an occupancy-scheduled gain, and add the rows to Table 7.
  - (b) Rewrite the Limitations item: "Internal gains of the order of the envelope load are omitted. They shorten free-float and lengthen on-phases, and their effect on the headline TUNED and MPC savings has not been established. The headline is for a room without internal gains."

**M2. Constant capacity and COP. The outdoor-dependent variant was implemented, is not reported, and the stated reason does not match the implementation.**
- *Location:* Limitations, l.2486–2494: "An outdoor-dependent COP is implemented in the repository but not reported, because derating of capacity and efficiency act in opposite directions on the margin between planning and rule-based arms."
- *What is wrong:*
  - (i) The repository's variant (headroom.py:270–281, `RBRL_COP=badescu`) changes COP only. The code says "Capacity is held at Q_HVAC (a stated simplification)". The reason given for not reporting it (capacity derating) therefore describes a model that was not run.
  - (ii) The results are most sensitive to Q·Δt/C. Derating a DX split unit by roughly 10–20% at 40–46 °C outdoors is, in the hottest hours, equivalent to raising C by 11–25%. Within the swept range, that shift moves the planner's margin by points.
  - (iii) The agent standard treats missing outdoor-temperature performance curves behind an energy or peak claim as MAJOR. Here the claim is about on-commands, but the mechanism is the same.
  - (iv) "Implemented but not reported" invites a selective-reporting question.
- *Fix:* report the implemented COP variant as one row of Table 7 for TUNED (and MPC-24 if feasible). Either add a capacity-derate row (`rebuild_tables.py` already contains Q_r[1 − 0.010(T − 35)]) or delete the capacity clause. Then state the direction found, or state that it is untested.

**M3. False statement on forward-Euler stability, in the passage that answers Comment 8.**
- *Location:* Sec. 3.1, l.445–447: "Forward Euler is stable only for Δt<2C_th/(Λ_i+Λ_iz,i), a bound the room-air capacity violates at an hourly step."
- *Evidence:* For the single zone, the headline topology then and now, Λ_iz = 0, so 2C/Λ = 2 × 77,200/23.75 s = 6,501 s = 1.81 h > 1 h. On the old model's τ = 0.65 h the bound is 1.3 h > 1 h. The hourly Euler step was therefore stable for the single zone, which is what the journal itself accepted ([journal comment 8 — text withheld]).
  - Supplement S1, l.127–131, gives the bound as C > 196.6–237.6 kJ/K "across the topologies". That range corresponds to μ_max ≈ 109–132 W/K and so holds only for the larger multi-zone grids. A single zone needs only 42.8 kJ/K.
  - For coupled zones, the bound in the main text should use the spectral radius of diag(Λ) + L, not Λ_i + Λ_iz,i.
- *Why MAJOR:* the editor will check this sentence against their own premise. As written it contradicts the editor and misstates the earlier model.
- *Fix:* "Forward Euler is stable for Δt < 2C/μ_max, with μ_max the largest eigenvalue of diag(Λ)+L_iz. At the room-air capacity this held for the single zone at 1 h (2C/Λ = 1.8 h) but fails for the larger grids (S1). Stability was never the issue; accuracy and the actuation condition are." Make S1 say which topologies the 196.6–237.6 kJ/K range covers.

**M4. The reference capacity is, by the authors' own argument, an upper estimate of the capacity that acts at the cycle period, but the consequence for the headline is not drawn.**
- *Location:*
  - Remark 1, l.493–497: "ISO 13786's areal capacity is a 24 h quantity, and the capacity effective at the cycle period is lower".
  - Sec. 8.3, l.2028–2030, and Limitations, l.2457–2463.
  - Abstract, l.124–127, and Conclusions, l.2536–2549, lead with 22–24% and 12.5/13.6/12.4% at 4,800 kJ/K.
- *What is wrong:* THERM cycles about 4.1 times a day, a period of about 6 h. The ISO 13786 periodic areal capacity at 6 h is markedly smaller than at 24 h for heavy layers, because the penetration depth scales with √period. The effective capacity therefore lies below 4,800 kJ/K, towards the 2,400 kJ/K point where TUNED saves −2.8% (Riyadh), −1.4% (Jeddah) and −1.3% (Taif) (`T1v3_heldout_cth2400.csv`). The manuscript reports this dependence honestly but never says which way the reference choice leans. This is the same kind of misreading of direction that Comment 2 objected to.
- *Fix:*
  - (a) Compute the ISO 13786 κ at the THERM cycle period (about 6 h) for a stated heavy construction, and state where the resulting C falls within [2,400, 9,600].
  - (b) In any case, add to the abstract or conclusions and to the single-node Limitations item: "The reference capacity is the 24 h ISO value; the capacity acting at the cycle period is lower, so the reference results lean towards the favourable end for TUNED."
  - Optionally, a two-node (air plus mass) check in Riyadh would settle whether the single node misses the faster air dynamics that Bacher and Madsen found.

### MINOR

**m1. Rounding slip in the capacity margin.**
- *Location:* Sec. 8.3, l.2035: "so its margin over TUNED is $15.0$, $5.8$, $3.8$ and $0.4$ points".
- *Evidence:* T21v3_riyadh.csv s = 18.2638 and T1v3_heldout.csv s = 12.5260, so the margin is 5.74. The response letter (Comment 2) says 5.7.
- *Fix:* change to 5.7, and compute differences from unrounded values everywhere.

**m2. Hourly weather is held as a staircase, which the text does not disclose.**
- *Location:* l.408–409: "Within one actuation interval the exogenous forcing (outdoor temperature, solar irradiance and the binary command) is held constant".
- *Evidence:* config.py:56 says "the hourly EPW is held over whole steps". At 15 and 5 min, T_out and irradiance are therefore piecewise-constant per hour, not per interval, and are not interpolated.
- *Assessment:* This is acceptable, and it keeps the forcing identical across the step sweep, which cleanly isolates actuation. It should still be stated.
- *Fix:* in Sec. 7 add "hourly EPW values are held constant over the 4 (12, 2) intervals of each hour; no sub-hourly interpolation."

**m3. The step study changes the baseline's sampling too, and the 30-min case is called admissible although THERM leaks.**
- *Location:* Sec. 9.3, l.2271–2289; Table S1(a): "30 & 0.750 & yes & 0.025".
- *What is wrong:*
  - THERM is a 1 K hysteresis sampled every Δt, not a continuously sensing factory thermostat. Its effective swing and cycling rate therefore change with Δt as well. The step sweep moves controller and comparator together, so "tied to the 15-min step" also means "tied to a comparator sampled at 15 min". Only the deadband-cap consequence is stated (l.2306–2308).
  - At 30 min the condition holds (0.75 ≤ 1 ≤ 1.05) but THERM leaks 0.025 °C·h while the arms must record zero. Condition (13) is therefore necessary but not sufficient for equal comfort obligations.
- *Fix:* add one Limitations sentence: "The comparator is a 1 K hysteresis evaluated at the actuation step; a factory thermostat that senses continuously is not represented, and the saving against it is not established." Mark the 30-min row "admissible by (13); THERM leaks 0.025 °C·h".

**m4. Hardware resolution is applied to TUNED only, and sensor accuracy is not discussed.**
- *Location:* Sec. 8.2, l.1940–1947; Limitations, l.2468–2472.
- *What is wrong:*
  - The guard and RBRL ceilings are also fitted on a 0.01 °C grid (Riyadh 23.80/23.60, Jeddah 23.82/23.62, Taif 23.86/23.66; `T1v3_heldout.csv`). Jeddah's and Taif's are off the 0.1 °C grid.
  - On the 0.1 °C grid, Riyadh TUNED is the guard hysteresis (5.75%, identical to the guard; `T1v3_sens.csv`). The F4 finding "the guard costs 6.8 points" therefore does not survive hardware resolution in Riyadh, and in Taif the guard (11.0%) beats hardware TUNED (8.4%).
  - Comfort matching at 0.03 K and Rule C at 0.002 K sit far below typical thermostat sensor accuracy (±0.3–0.5 K). Exact noise-free sensing is assumed for every arm, not only MPC (l.2474).
- *Fix:* state both points in the "Thermostat resolution" item, and qualify F4 in Sec. 9.2: "on a 0.1 °C grid TUNED coincides with the guard in Riyadh".

**m5. Comfort band described as both swept and unswept, and "conservative" points the wrong way.**
- *Location:* Sec. 6.2, l.1556: "the narrower band adopted here is therefore conservative with respect to that literature, and the band width is treated as a sensitivity, not assumed (Section~\ref{subsec:disc_band})".
- *Evidence:* Sec. 10.3, l.2404–2406: "the band was not swept under the protocol, so no figure is given". The same paragraph says a narrower band makes THERM cycle more "so the saving rises". A narrower band is therefore favourable to the reported saving, not conservative.
- *Fix:* "...the narrower band raises the reported saving through the baseline's cycling (Section 10.3) and was not swept."

**m6. Energy bound in Remark 2 is double-counted.**
- *Location:* Remark 2, l.562–564: "can move ⟨T_i⟩ by at most that width, bounding the energy it can save relative to a thermostat at the band centre at roughly 0.38 kWh/day."
- *What is wrong:* Relative to the band centre, the largest warm shift is 1 K, which gives 0.191 kWh/day. The 0.38 figure is the full 2 K width.
- *Fix:* "relative to a thermostat at the band centre, at most about 0.19 kWh/day (0.38 across the full band)".

**m7. Opaque-wall solar and roof exposure are absent and not listed.**
- *Location:* eq. (1), Sec. 7 l.1569–1572 (solar through glazing only), Limitations.
- *What is wrong:* Sol-air gain through a U = 0.45 wall of 14 m² in Riyadh adds tens of watts at peak. A top-floor room would add a roof face. Both raise the load and shorten free-float, which is the same mechanism as M1.
- *Fix:* one clause in the "One year, one zone type" item: "an intermediate-floor room, opaque-wall solar neglected".

**m8. "Compressor on-commands" and "per start" conflict with the paper's own limitation.**
- *Location:* abstract l.125 ("22–24% of compressor on-commands", "per start that wear supports"); l.1916; Conclusions l.2536–2538.
- *What is wrong:* Limitations l.2453–2456 say the events are on-commands, not compressor starts.
- *Fix:* "supervisory on-commands", or add "(each assumed to be a start)" at the point where it is priced.

**m9. The setpoint-lever figures in the Discussion and Conclusions come from a different model configuration.**
- *Location:* Sec. 10.3, l.2414–2420 ("cuts its cost by 7.1, 9.4 and 14.5% and its electricity by about 8, 10 and 16%"); Conclusions l.2574 ("about 8–16% for one degree warmer").
- *Evidence:* The source file `T1v2_heldout_pol24.csv` has a Riyadh THERM cost J_therm0_mean of 1.475, against 1.118 in the headline `T1v3_heldout.csv`. A 24 °C baseline should be cheaper, not dearer, so this is not the headline plant and protocol. By the paper's own duty identity at the current plant, 1 K is worth 0.191 kWh/day against about 2.79 kWh/day of HVAC electricity (fs_therm0 4.10/day × 0.15 SAR = 0.615 SAR/day; 0.503 SAR/day of energy at 0.18 SAR/kWh), which is about 6.8% in Riyadh, not about 8%.
- *Fix:* recompute at the current plant (one THERM run at a 24 °C centre per city), or quote the duty-identity values.

**m10. Actual-year study: the CDD definition and data provenance are unstated.**
- *Location:* Sec. 10.2, l.2371–2378; S5.
- *What is wrong:*
  - Years are ranked by CDD at base 24 °C (amy_fetch.py:174). The text says only "cooling degree-days", next to the CDD₁₈ of Sec. 6.1 (Riyadh 3,693 vs AMY 1,707–2,231 in `T23v3_amy_spread.csv`).
  - ERA5 at 0.25° is not the station record behind TMYx, so "transfer" mixes year-to-year spread with dataset bias.
  - Some selected years (for example Riyadh 2013, 2019 and 2021, inside TMYx's 2009–2022 window) may supply TMYx months.
- *Fix:* state the base (24 °C), the ERA5/station caveat, and whether any test year supplied a TMYx cooling-season month.

**m11. The 5-min "match" between TUNED and MPC-24 carries a comfort offset beyond the paper's own caveat threshold.**
- *Location:* Sec. 9.3, l.2279: "its cost saving doubles to about 25%, matches the Riyadh 24 h controller (a difference not resolved)".
- *Evidence:* TUNED ΔT = +0.032 K (`T1v3_heldout_dt5.csv`) against MPC-24 −0.078 K at the 0.10 K fallback (`T21v3_riyadh_dt5.csv`). The gap of 0.11 K is far above the 0.02 K threshold of the "Comfort offsets" item, and at about 1.3 points per 0.01 K it is not small.
- *Fix:* attach the caveat in the sentence, as Table 8 footnote b already does.

**m12. Stale multi-zone files in the ground-truth results folder.**
- *Location:* `/home/claude/rbrl_p12/results/T31_mz_rules_riyadh_{1x2,2x2,1x4}_{m1,m2,mnone}.csv`.
- *What is wrong:* These files have no fit_status or provenance columns. They are shared-plant runs (m1, m2) and independent-unit runs (mnone) from an earlier protocol. They give TUNED 6.8–10.2%, with TUNED below the guard in 2×2 m2, against 11.7–13.6% reported for the same layouts. The code now refuses shared-plant runs ("DROPPED (RULING §5, D2)", mz_r3.py:98).
- *Fix:* move them to archive_r3/, or add a note in the repository README. Optionally say in Limitations that a shared-plant variant was explored under an earlier protocol and dropped.

**m13. Exact on-grid comfort checking is proven for the single zone only.**
- *Location:* l.448–452: "for a single zone the trajectory's extremes are its endpoints".
- *What is wrong:* For coupled zones the within-interval trajectory need not be monotone. The multi-zone comfort record is therefore an on-grid check.
- *Assessment:* With λ_ij/C ≈ 2.6 × 10⁻⁶ s⁻¹ the effect is negligible.
- *Fix:* state it in Sec. 8.4.

**m14. The comfort temperature is the lumped node temperature.**
- *Location:* Sec. 7 "Comfort"; Sec. 3.1 l.393–395 ("T_i(t) be the air temperature" while C_th lumps air, furnishings and fabric).
- *What is wrong:* The constrained quantity is a capacity-weighted node temperature, neither air nor operative temperature. With a separate air node, a full 2 kW on-step would pull air temperature well below the node. Remark 1 and the Limitations come close to saying this ("a plant with a separate air node would cycle faster") but never say what the comfort metric is.
- *Fix:* one sentence: "Comfort is evaluated on the single node's temperature, which stands for air and participating fabric together."

## Journal Comments 2 and 8

**Comment 2 (capacity): answered in substance, with a residual (M4).**
- The "lower bound" claim is gone (grep finds no "lower bound" or capacity "conservative" in main.tex). 77.2 kJ/K survives only in S1, as the reason the old sweep was inadmissible.
- The authors decline the editor's proposed sentence and say why: the 77.2/500/1,200 kJ/K configurations had per-interval excursions of 93.3/14.4/6.0 K, which I verified (Q·Δt/C at 2 kW, 1 h). That reason is valid, and adopting the sentence would have repeated a comparison between infeasible configurations.
- The replacement sweep is broader, every arm is refitted, and the result is reported even though it weakens the paper. I verified it.
- The residual risk is the same kind of interpretive error the editor flagged: the direction of bias of the reference capacity is not stated (M4).
- The letter truthfully describes the manuscript, apart from 5.7 vs 5.8 (m1).

**Comment 8 (time step): answered, with one factual error to fix (M3).**
- The integration error is removed by the exact solution, not just reduced, so a semi-implicit comparison is unnecessary. This is a stronger remedy than the editor asked for, and correct given zero-order-hold forcing.
- A step sweep was run at 5, 15, 30 and 60 min, every arm refitted, with THERM's comfort record per step. The savings change materially, and the manuscript and letter both say so; "unaffected" is withdrawn.
- The capacity change (τ from 0.65 h to 56 h) is argued from ISO 13786, not chosen to escape the question, and the letter is open that the step still matters through actuation.
- Remaining items: M3, the false Euler sentence. Also m2 (hourly staircase forcing undisclosed), m3 (the comparator's sampling changes with Δt, and the 30-min row is called admissible although THERM leaks) and m11 (comfort offset in the 5-min comparison).
- The letter's numbers for Comment 8 all match the CSVs.

## Paper Quality Standard rows (owned items)

| ID | Status | Note |
|---|---|---|
| Q2.1 Modelling choices justified | Partial | Single node justified against the literature, with Bacher and Madsen's rejection disclosed. No two-node check (M4). |
| Q4.1/Q4.6 Simulated labelled; no invented values | Pass | All checked values trace to CSVs. One rounding slip (m1). One superseded-model figure (m9). |
| Q4.4/Q4.5 Generalisation across climates, seasons and years | Pass, limited | 3 cities, 7 seasonal windows, 3 actual years per city (TUNED only), 4 orientations. |
| Q8.3 Practical units | Pass | Results are given in SAR per room per season, kWh/month, on-commands per day, and °C·h. |
| Building Energy & Control profile | Partial | Labelled as a reference model, with no G14 claim. The comfort metric is defined. No BOPTEST, which is disclosed. Internal-gain and plant-curve gaps remain (M1, M2). |

## Verdict for the building-simulation dimension

**NOT READY** as submitted. All four MAJOR items can be closed with text edits: correct the Euler sentence (M3); state the direction of bias of the reference capacity (M4); write Limitations items for internal gains (M1) and outdoor-dependent plant performance (M2), or run the one-row sensitivities for those two. Once those are done, this dimension would be READY AFTER MINOR FIXES.

Findings: CRITICAL 0, MAJOR 4, MINOR 14.
