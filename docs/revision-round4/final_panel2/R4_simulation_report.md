# R4_simulation report: building energy simulation (final panel 2, round 4)

**Reviewer role:** Specialist Reviewer R4, building energy simulation
**Scope:** whether the plant model is fit for the claims made; boundary conditions (weather, tariff, comfort); train/test separation; actuation step and hardware resolution; multi-zone model; the Green Riyadh sensitivity; Limitations; journal Comments 2, 6 and 8; and the response letter for those comments.
**Files read:** main.tex (all), supplement.tex (all), RESPONSE_LETTER.md (all), the journal's outstanding comments (.docx), audit_report.md, my agent file, and the code paths `hvac.read_epw`, `hvac.vertical_irradiance`, `greenriyadh_sens.py` and `config.py`.

## 1. Overall assessment

The simulation experiment is now described honestly and is internally coherent.

- **Exact discretisation.** The first-order RC model is stepped exactly (matrix exponential with zero-order-hold forcing). The actuation condition is two-sided (eq. 8), and every number in Remark 1 that I re-derived is correct:
  - excursion 0.375 K at 15 min;
  - 1.50 K at 1 h;
  - 0.75 K at 2,400 kJ/K;
  - ε_hot = 0.129 K;
  - required capacity ≈ 9,700 kJ/K for an hourly step (14,400 kJ/K for a centred deadband);
  - τ = 56.1 h;
  - ∂E/∂T = −0.191 kWh/day/K.
- **Sensitivities.** Capacity is swept over 2,400–9,600 kJ/K and the actuation step over 5/15/30 min (60 min shown to be inadmissible). Every arm is refitted. The direction of the capacity bias is stated in the abstract, Remark 1, §8.3, the Limitations and Table S6.
- **Calibration status.** The model is labelled an uncalibrated reference model, and absolute figures are disclaimed. That is the correct remedy, since no ASHRAE Guideline 14 calibration is possible.
- **Earlier claims withdrawn.** The tariff in force (Eq. 11, 0.18/0.30 SAR/kWh at 6,000 kWh) and the 2027 repricing are used. "Lower bound", "unaffected" and "actual Saudi step-wise tariff" no longer appear anywhere (checked by grep).
- **Numbers.** Every simulation number I checked matches the CSVs (§3).

Two problems remain:
- **M1.** The tariff passage and the response to Comment 6 still refer to a third, pre-2018 "epoch" that the manuscript no longer reports. The letter also quotes manuscript text that does not exist.
- **M2.** The new Green Riyadh sensitivity is reported in the Conclusions without the caveats it needs. Its one known bias, the omitted internal gains, inflates the percentage, and this is not stated.

Both can be fixed in the text.

## 2. Simulation credibility summary

| Aspect | Status | Evidence location | Comment |
|---|---|---|---|
| Model fidelity vs claims | OK / WEAK | §3.1, Remark 1, Table 2, Limitations | Single node, no internal gains, constant capacity and COP, sensible only. All of these are disclosed. Claims are restricted to relative on-command comparisons at a 15-min step. Internal gains are the one omission whose direction could be estimated cheaply and is not (m5). |
| Calibration / validation (G14 stats) | MISSING (disclosed) | §10.2 | Uncalibrated reference model; "Absolute figures are not predictions for a real dwelling". Acceptable as labelled. |
| Weather & period | OK | §6.1, §7, Data section | TMYx with WMO IDs and periods of record. Hourly values are held over sub-hourly steps (stated, l.1505). Solar transposition is at mid-hour with the correct EPW convention (`hvac.py` l.117). The cooling season is 1 May–31 Oct. ERA5 actual years are used for spread, with the dataset mix disclosed. |
| Tariff & peak definition | OK / WEAK | Eq. 11, Remark 3, Table 7(a) | Tariff in force and 2027 rate. No peak claim is made. "Three epochs" in §10.3 is unsupported (M1). The denominator of *s* is not the household bill (m3). |
| Comfort metric | OK | §7 "Comfort", Rule B, Table S4 | Hard occupied ceiling; degree-hours over and commanded/free-float under-temperature are reported. The node temperature lumps air and fabric (disclosed, l.378). That the headline is occupied 24/7 is not stated (m6). |
| Train/test separation | OK | §7 protocol, Algorithm 1 | 13 non-overlapping fortnightly windows, alternately assigned. Dates are correct (2 May … 17 Oct, 0-based index 121–289). No validation set; the held-out windows are used once. Interleaving within one TMYx year is disclosed. |
| Sensitivity / uncertainty | OK | Tables 7, 8, S1, S2, S6; §10.2 | Capacity, step, deadband, charge, tariff, hardware grid, admission rule, orientation and actual years. Internal gains and COP are not swept (disclosed). |
| Reproducibility of model | OK | Data section | Code, Zenodo DOI, SHA-256-verified weather fetch, results files with provenance hashes. |

## 3. Numbers verified against the CSVs (all match unless stated)

- **Headline TUNED** (`T1v3_heldout.csv`, inforce):
  - *s* = 12.53 / 13.62 / 12.41;
  - on-commands avoided 22.8 / 24.2 / 21.7;
  - energy −0.33 / +0.47 / −0.49;
  - commanded under-temperature 0 / 0.00067 / 0.0066;
  - Taif free-float 0.29.
- **2027 rate:** *s* = 11.65 / 12.69 / 11.58, giving the 11.6 / 12.7 / 11.6 in the text.
- **Historical rate (0.05 SAR/kWh):** 18.58 / 19.88 / 17.98. This row is in the CSV but not in the manuscript; see M1.
- **Capacity:**
  - 2,400 kJ/K: −2.78 / −1.43 / −1.26, Riyadh on-commands −4.0 (`T1v3_heldout_cth2400.csv`);
  - 7,200 kJ/K: 16.02 / 16.71 / 17.72, ΔT̃ +0.033 / +0.040 / +0.121;
  - 9,600 kJ/K: 15.82 / 15.83 / 16.04, ΔT̃ −0.019 / +0.029 / −0.018;
  - Riyadh on-commands 34.6 and 39.8 at 7,200 and 9,600 kJ/K;
  - MPC-24 at 7,200 kJ/K 19.8 (`T2v3_timestep.csv`).
- **Actuation step** (`T1v3_heldout_dt5/dt30.csv`, `T2v3_timestep.csv`):
  - 5 min: TUNED 24.97 / 24.78 / 25.68, on-commands 43.1 / 41.9 / 43.0, energy ≤ +0.88%, fitted deadbands 1.78 / 1.78 / 1.79;
  - 30 min: TUNED −1.23 / −1.53 / −1.20, on-commands −2.4 / −2.8 / −2.2, deadbands 0.98 / 0.94 / 0.99, commanded under-temperature 0.0097 / 0.0025;
  - MPC-24: 23.8 (801 nodes, 0.10 K fallback, ΔT̃ −0.078) at 5 min, and 6.56 (λ/λ* = 6.27) / 11.42 / 11.28 at 30 min;
  - B*: 27.3; 10.9 / 13.9 / 14.7.
- **Hardware 0.1 °C grid** (`T1v3_sens.csv`): 5.75 / 7.40 / 8.37; on-commands 10.5 / 13.2 / 14.7; Riyadh at 23.6/22.4 equals the guard.
- **Comfort-target lever** (`T32_setpoint_sens.csv`): energy −0.85 / −1.41 / −2.33% for a +0.109 / 0.109 / 0.117 K warmer mean.
- **Green Riyadh** (`T34_greenriyadh_sens.csv`):
  - THERM energy −10.50% at −1.5 K and −13.68% at −2.0 K;
  - TUNED raw saving 12.81 and 13.60 (12.90 unshifted);
  - TUNED's mean 0.030 and 0.048 K warmer than THERM.
- **Multi-zone** (`T31_mz_*`):
  - TUNED 12.43 / 11.7 / 13.6;
  - MPC-MZ 16.04 (fallback 0.10 K, ΔT̃ −0.072) / 15.87 (ΔT̃ −0.036) / 15.69 (ΔT̃ −0.068);
  - 1×4 at λ_ij = 35: over-temperature 0.000102;
  - 1×1 instance: 18.26.
- **Account energy:** THERM uses 2.80 kWh/day for 4.10 on-commands/day. *J* = 2.80 × 0.18 + 4.10 × 0.15 = 1.119 SAR/day, which reproduces the 55.0% on-command share and the ≈84 kWh/month. The mean load implied by the duty cycle (≈350 W) agrees with Λ(T_out − T) + Q_sol.

## 4. Findings

### MAJOR

**M1. A third tariff "epoch" is used in the text and the letter but appears nowhere in the manuscript, and the Comment 6 response quotes text that does not exist (Comment 6).**

*Location and quoted text:*
- §10.3, l.2413–2416: "In Riyadh the comparator's deadband moves the saving by 35 points …, the charge per on-command by 7 across the derived range and **the tariff by 7 across the three epochs** (Table~\ref{tab:sensitivity})."
- §10.3, l.2436: "the on-commands TUNED avoids are the same **under all three epochs**".
- RESPONSE_LETTER.md, Comment 6, l.149: "the pre-2018 four-tier schedule has been removed from the analysis altogether".
- The same response, l.151: "TUNED avoids the same 22.8% of on-commands in Riyadh under all three epochs while its cost saving is 18.6, 12.5 and 11.6%."
- The same response, l.154: "Section 3.4 … Model S 'is a historical schedule, no longer the tariff in force, and it is used here as a stress-test instantiation of the step-wise cost class, not a representation of current Saudi prices'".
- The same response, l.157: "Table 7(a) (three tariff epochs)".

*What is wrong:*
- Table 7(a) has two rows: 0.18 (in force) and 0.21 (2027). The 18.6% figure is the `historical` 0.05 SAR/kWh row of `T1v3_heldout.csv` (Riyadh *s* = 18.58), and it is not reported anywhere in main.tex or supplement.tex. Grep for "historical", "pre-2018" and "stress-test" returns nothing relevant.
- Across the two tariffs actually reported, the tariff moves TUNED by 0.9 points (12.5 → 11.6), not 7. The ranking of levers in §10.3 ("deadband 35 … class 13 … charge 7 … tariff 7") therefore rests on a number the reader cannot find.
- In the manuscript, Model S *is* the tariff in force (§3.4, Eq. 11). The sentence the letter quotes from §3.4 does not exist and contradicts it.
- The letter also says the pre-2018 schedule was removed "altogether", then cites its result.
- Comment 6 is one of the four comments the journal flagged as unresolved. The editor will check this response line by line.

*Fix (choose one):*
- (a) Restore a third row in Table 7(a), "0.05 (pre-2018 first tier; historical, stress test), 81.5% share, TUNED 18.6, B* —", and say once, in Remark 3, that it is historical. Then keep "three epochs" and "7".
- (b) Remove the historical epoch everywhere. In §10.3 write "and the tariff by 0.9 points between the schedule in force and the 2027 schedule", and "the same under both schedules". In the letter, delete "18.6," and "three epochs", replace "Table 7(a) (three tariff epochs)" with "Table 7(a) (in-force and 2027 schedules)", and replace the quoted Model S sentence with the actual §3.4 text ("instantiated with the Saudi residential tariff in force since January 2018 …").

Option (b) matches the letter's own statement that the old tariff was removed. In either case the letter must quote only text that is in the manuscript.

**M2. The Green Riyadh result appears in the Conclusions without its caveats, and its known bias is not stated.**

*Location and quoted text:*
- §10.3, l.2460–2466: "lowering Riyadh's outdoor temperature by 1.5 and 2 K, the Green Riyadh aim, cuts THERM's cooling electricity on the held-out weeks by 10.5 and 13.7% … The shift is applied to an airport weather year with the plant and thresholds unchanged; it is a first-order sensitivity, not a model of the urban heat island."
- Conclusions, l.2626–2628: "air 1.5–2 K cooler (the Green Riyadh aim) lowers it by 10.5–13.7% in Riyadh." No caveat is given here.
- Abstract, l.140–142, and keywords, l.148: "Green Riyadh", "CO$_2$ reduction".

*What is wrong.* The §10.3 caveat (uniform shift, plant and thresholds unchanged, not a heat-island model) is correct but incomplete:
1. *Missing internal gains inflate the percentage.* The percentage is ΔL/L of one room's cooling load. The model's mean load is ≈350 W, all envelope and glazing (computed from 2.80 kWh/day × COP 2.985 / 24 h). The Limitations give internal gains of 150–300 W, which do not change with outdoor temperature. With them, the same 35.6 W (= 23.75 W/K × 1.5 K) reduction would be roughly 7% rather than 10.5%. The reported figure is therefore an upper estimate, by a factor of order 1.3–1.5.
2. *Constant COP biases the other way.* A real unit's efficiency rises in cooler air, which would enlarge the saving. The net direction should be stated as uncertain, or both effects named.
3. *The aim is not a uniform shift.* The programme's 1.5–2 °C is a city-scale, near-surface aim that is unlikely to be uniform across hours and months. A uniform all-hours shift of a station record is a stylised reading of it.
4. *Scale.* The percentage is of one cooled room's HVAC electricity, not of household or national electricity (the 800 kWh/month background is unchanged). The keyword "CO$_2$ reduction" and the Introduction's link to the 278 Mt target suggest a result the paper does not compute. By the paper's own identity, the controllers studied do not change electricity at matched comfort.

*Fix:*
- Extend the §10.3 caveat: "The percentage is of one room's cooling electricity in a model without internal gains, which, being independent of outdoor temperature, would reduce it (to about 7% at 1.5 K for 150 W); a constant COP omits the efficiency gain in cooler air. It is a first-order sensitivity, not a model of the urban heat island or of the programme's realised effect."
- Carry the clause "(one room's cooling electricity; first-order, uniform shift)" into the Conclusions sentence.
- Replace the keyword "CO$_2$ reduction" with e.g. "thermostat commissioning" or "actuation step", or delete it.
- Give one Limitations sub-clause, or one Table S6 row, for the shift.

### MINOR

**m1. The capacity bias is stated for TUNED but not for MPC's own saving (Comment 2).**
- *Location:* Table S6, row "Reference capacity … probably overstates" (TUNED only). Abstract: "whose reference value probably favours the tuned thermostat".
- *Evidence:* MPC-24 also falls at 2,400 kJ/K: 12.2% against 18.3% (Table 7(d)). The reference therefore probably overstates MPC's saving against THERM as well, while it understates MPC's margin over TUNED.
- *Fix:* add a Table S6 row, "Reference capacity, MPC-24 saving: probably overstates; 12.2% at 2,400 kJ/K". In §8.3, after "lean towards the end favourable to TUNED", add "and both arms' savings against THERM are probably overstated."

**m2. Two sentences on the direction of the capacity bias are ambiguous (Comment 2).**
- *Remark 1, l.472–475:* "so the reference value probably lies above the effective one, towards the capacities at which the tuned thermostat gains least". This can be read as placing the *reference* towards low capacities, which is the opposite of what is meant. Fix: "so the effective capacity probably lies below the reference, towards the capacities at which the tuned thermostat gains least."
- *Conclusions, l.2608–2610:* "…MPC's margin falls from 15.0 to 0.4 points; because the capacity acting over a cycle is probably below the reference, the reference results lean towards the end favourable to it." Here "it" could mean MPC's margin or TUNED. Fix: "favourable to the tuned thermostat".

**m3. The denominator of *s* is the room's cost, not the bill, but Remark 3 implies the bill (Comment 6).**
- *Location:* Remark 3, l.726–728: "The fixed charge … enlarges the bill and so reduces every percentage saving quoted here."
- *Evidence:* *J* = room HVAC energy cost + on-command charges = 1.119 SAR/day. The 800 kWh/month background, VAT and the fixed charge are not in the denominator, so the fixed charge cannot change any percentage quoted.
- *Fix:*
  - Remark 3: "…does not alter the optimal policy or any percentage here, which is relative to the room's cooling energy cost plus on-command charges; expressed against the household bill every saving would be far smaller."
  - State the denominator once in §7 next to eq. (26).

**m4. Tariff realism for larger dwellings (Comment 6).**
- *Location:* Remark 3 and §7 "Background load and tariff".
- *What is missing:* the modelled account is one cooled room plus 800 kWh. A large Saudi villa with many units can exceed 6,000 kWh/month in summer. It would then face the 0.30 (0.33) SAR/kWh second block, which by the logic of Table 7(a) dilutes the percentage further.
- *Fix:* add one sentence: "A dwelling that crosses the 6,000 kWh boundary in summer faces a higher marginal price, which by Proposition 1 does not change the optimal schedule but lowers the percentage saving (Table 7(a))."

**m5. Internal gains: the direction could be estimated, and the background load implies them.**
- *Location:* Limitations, "No per-start energy and no internal gains"; Table S6, "not established".
- *Point 1:* the 800 kWh/month of non-HVAC electricity billed to the account is dissipated as heat in the dwelling. The billing model thus implies internal gains that the thermal model omits; say so.
- *Point 2:* under the paper's own constant-rate abstraction, the hysteresis cycle frequency is f = L(Q−L)/(C·δ·Q) and energy E ∝ L, so f/E ∝ (Q − L). Raising the mean load from ≈0.35 to ≈0.5–0.65 kW would raise THERM's on-commands by about 30–45%. It would also lower the on-command share of cost, and with it the percentage saving, by roughly a tenth (first-order estimate).
- *Fix (either):*
  - give this estimate as the direction ("probably overstates the percentage slightly; raises SAR"); or
  - run the one-row sensitivity. `greenriyadh_sens.py` already shows the pattern: wrap `headroom.series` to add G/(SHGC·A_gl) = G/0.5 W m⁻² to the irradiance for G = 150 and 300 W, then refit TUNED by Rule A.

**m6. That the headline is occupied all day is not stated.**
- *Location:* §7 "Comfort": "On every occupied step…". The set H_occ is defined (l.924), but the headline occupancy is never given. Only the setback arms state a timetable (08:00–14:00 away).
- *Fix:* "In the headline and every sensitivity, every step is occupied; only the setback arms use the timetable of Section 8.2."

**m7. The multi-zone MPC comparison with 18.3% ignores its cooler matched comfort.**
- *Location:* §8.4, l.2073–2078 and Conclusions l.2634–2635: "a non-cooperative distributed MPC saves 15.7–16.1%, against 18.3% in the single zone".
- *Evidence:* `T31_mz_mpc_*`: the 1×2 cell is fitted at the 0.10 K fallback (shown only in Table S-MZ), and the three layouts run ΔT̃ = −0.072, −0.036 and −0.068 K. By the paper's own comfort-offset slope (about 1.3 points per 0.01 K), that penalises MPC by several points.
- *Fix:* in §8.4 give the fallback mark and the ΔT̃ values. Write "below the single-zone 18.3%, partly at a cooler matched mean (comfort-offset caveat)". Make the same qualification in the Conclusions.

**m8. Plant COP: the known direction is not in Table S6, and an unreported variant is mentioned.**
- *Location:* Limitations, "Plant data". Table S6, "Single node; constant capacity and COP…: not established".
- *What is wrong:* the COP of 2.985 is below the SASO T1 minimum, and the text itself says a higher COP raises the percentage. The level effect is therefore known: probably understates. Only the temperature dependence is unestablished.
- *What is wrong (continued):* "An outdoor-dependent COP … is implemented in the repository but not reported" still invites a selective-reporting question (panel-1 M2, partly closed).
- *Fix:* add a Table S6 row, "COP below SASO T1 minimum: understates". Either report the COP-variant row in Table 7 or delete the sentence that mentions it.

**m9. Green Riyadh mixes the raw and equalised metrics.**
- *Location:* §10.3, l.2463: "TUNED's raw saving stays at 12.8–13.6%".
- *What is wrong:* the reader will compare this with the equalised 12.5%. The unshifted raw value is 12.9%, and in the shifted runs TUNED sits 0.030–0.048 K warmer than THERM.
- *Fix:* "(raw saving, 12.9% unshifted; TUNED 0.03–0.05 K warmer than THERM, thresholds not refitted)".

**m10. A stale tier width in the supplement (Comment 6).**
- *Location:* supplement.tex l.135–136: "the discrete bill is path-dependent at the order of one interval's consumption ($0.17\,$kWh here, against tier widths of $2{,}000\,$kWh)".
- *What is wrong:* 2,000 kWh is the withdrawn four-tier schedule. The tariff in force has a single boundary at 6,000 kWh.
- *Fix:* "…against a single boundary at 6,000 kWh".

**m11. The response letter misdescribes the PPO training-length text (cross-dimension; noted for R5/R6).**
- *Location:* RESPONSE_LETTER.md l.218 says the claim is "now 'longer training was not tested'". Line 245 says "the earlier statement that a longer training run would not help is removed".
- *What the manuscript says:* l.1281–1282, "a longer run on the same weeks has almost nothing left to gain"; Limitations l.2567–2568, "so it has little to gain".
- *Fix:* align the letter with the new diagnostic, e.g. "replaced by a diagnostic on the tuning weeks (Section 5.4)".

**m12. Solar time (very minor).**
- *Location:* `hvac.vertical_irradiance`.
- *What is wrong:* the hour angle uses clock time at mid-hour, with no longitude or equation-of-time correction. Riyadh is 1.7° east of the UTC+3 meridian, a shift of up to about 25 min.
- *Fix:* the effect on the results is negligible. State it in the repository, or add one clause in §6.1.

**m13. Springer build (outside my dimension).**
- *Location:* main_sn.pdf, reference list.
- *What is wrong:* the Springer build prints "???" in two references (Mousa 2016 IEEE and Mousa 2017 Springer: missing publisher address). The Elsevier main.pdf is clean.

**Placeholders.** No `\pend{…}` call and no "PENDING" text remain in main.pdf, supplement.pdf or main_sn.pdf. Only the `\newcommand` definitions remain in the .tex sources. Two leftover drafting comments (`%% Gate (RULING §12.1)…` and the title decision tree) are LaTeX comments and are not printed.

## 5. Judgement on the journal comments in my dimension

**Comment 2 (thermal capacity): answered, with a justified departure from the requested wording.**
- The "lower bound" claim is gone everywhere (grep).
- The editor's replacement sentence [journal comment 2 — text withheld] is not used. The reason is correct and verifiable: at 1 h, 77.2 / 500 / 1,200 kJ/K give excursions of 93.3 / 14.4 / 6.0 K (2,000 × 3,600 / C), all far wider than the 2 K band, so the withdrawn sweep compared infeasible configurations.
- The new sweep reports what the editor wanted, the direction of the bias. It turns out to be large: TUNED −2.8 → 15.8%, MPC margin 15.0 → 0.4 points.
- The direction is stated consistently in the abstract, Remark 1, §8.3, the Limitations, the Conclusions and Table S6.
- Remaining: m1 (the MPC-saving direction) and m2 (two ambiguous sentences).
- Recommendation: keep the letter's explanation. It would help to add one explicit sentence: "In the rebuilt model the saving *rises* with capacity up to 7,200 kJ/K, so the requested statement would no longer be true."

**Comment 6 (tariff): substantively answered in the manuscript, inaccurately described in the letter.**
- The tariff in force is Eq. 11. Remark 3 shows the dwelling never leaves the first block, Table 1 marks the step-wise tariff ∘, and the 2027 rate is reported.
- The phrase "actual Saudi step-wise tariff" and the 18.2% and 16.8% figures are gone.
- Remaining:
  - M1, a phantom third epoch, plus a quotation in the letter that is not in the manuscript. This must be fixed before submission.
  - m3, m4 and m10.

**Comment 8 (time step): fully answered.**
- Forward Euler is replaced by the exact update. The stability sentence is now correct: 2C/Λ = 1.8 h for the single zone at 77.2 kJ/K, failing only for the coupled topologies. Panel-1 M3 is closed.
- A 5 / 15 / 30 / 60-min study is reported with every arm refitted, and comfort is reported per step (THERM 0 / 0 / 0.025 / 4.47 deg-h; TUNED commanded under-temperature at 30 min).
- The study shows that the savings change materially; "unaffected" is withdrawn.
- The sweep isolates actuation rather than integration error, which is the right reading once the integrator is exact. The text says so (l.439, and §9.3 on comparator sampling).
- No further work is needed.

## 6. The response letter (my comments)

- **Comment 2:** truthful. Every number matches the CSVs, and every quoted passage exists.
- **Comment 6:** not fully truthful (M1). The quoted §3.4 text is absent, "three tariff epochs" and "18.6" refer to unreported results, and "removed … altogether" contradicts the 18.6% quoted two paragraphs later.
- **Comment 8:** truthful. The figures (25.0 / 24.8 / 25.7; −1.2 / −1.5 / −1.2; 0.0097 / 0.0025; THERM 0.025 / 4.470) and the quoted key sentence match the manuscript and the CSVs.
- **Comment 1:** truthful about the absence of validation.
- **"Limitations now stated":** matches §10.4 word for word. It still omits the Green Riyadh caveat (M2).

## 7. Panel-1 closure (R4 dimension and related items)

Checked after my own findings were written.

| Panel-1 item | Status now |
|---|---|
| R4 M1: internal gains not bounded | **Closed (text).** The Limitations item now covers the headline ("their effect on the headline savings is not established"). An estimate or a run is still suggested (m5). |
| R4 M2: COP variant, reason mismatch | **Partly closed.** The capacity-derate reason is gone and "capacity held constant" is stated. The variant is still "implemented but not reported" (m8). |
| R4 M3: false Euler stability sentence | **Closed.** §3.1 l.430–436 and S1 now give the single zone 1.8 h and coupled topologies 85.8–185.1 kJ/K. |
| R4 M4: direction of the capacity bias | **Closed.** Abstract, Remark 1, §8.3, Limitations, Conclusions, Table S6. |
| R4 m1–m5 (5.8→5.7 rounding, weather staircase, comparator sampling, hardware for the guard and noise-free sensing, "conservative" band) | Closed (5.7; l.1505; Limitations "Tied to the 15-min step"; "Thermostat resolution"; l.1488). |
| R6 CRITICAL: D1 on PPO "lifts them to TUNED's level" | **Closed.** Conclusions l.2617–2619 now refer to "on a latch", and §8.3 gives Taif 8.0–12.0%. |
| R6 MAJOR 2: two-sided actuation condition | **Closed.** 9,700 kJ/K; S1 marks 1,800 "no" and 30 min "no (upper)"; recommendation (ii) asks for both sides. |
| R6 MAJOR 3: Fig. 1 "3.00" and "Proposition 2" | **Closed** (not present in fig_leap.tex). |
| R6 MAJOR 4: TUNED commanded under-temperature | **Closed** (§8 preamble, Table S4, letter). |
| EIC F1: window dates off by one day | **Closed** (2 May … 17 Oct; 16 May … 3 Oct; "zero-based day indices"). |
| EIC F2 / DA M3: "compressor on-commands" | **Closed** ("compressor" appears only in the disclaimers). |
| DA M1/M2: deadband mechanism; "representative" | **Closed** (wider-deadband mechanism in the abstract and §8.2; "assumed, not measured"; "representative" removed). |
| R1 M2: "requires a perfect forecast / light plant" | **Closed** ("resolved only with a perfect in-horizon forecast"; "light plant" withdrawn). |
| R5 M5: decision time unreported | **Not closed:** §9.4 says "No claim is made about … decision time". This is R5's dimension. |
| New since panel 1 | M1 (tariff epochs and letter), M2 (Green Riyadh caveats), m11 (letter vs the training-length diagnostic). |

## 8. Paper Quality Standard rows owned

| ID | Status | Note |
|---|---|---|
| Q2.1 | PASS | RC single node justified as control-oriented; alternatives (four-state, EnergyPlus, HIL) named and declined with reasons. |
| Q4.1 / Q4.6 | PASS | "Every figure is simulated"; no invented values found (§3). |
| Q4.4 / Q4.5 | PASS / WEAK | Three climates, actual years, orientations. One building type and one zone type, disclosed. |
| Q8.3 | PASS | Results in on-commands, kWh, SAR per room per season and K. |
| Profile: calibration | PASS (labelled reference model) | ASHRAE G14 stated as not computable; no calibration claim. |

## 9. Verdict for the building-simulation dimension

**NOT READY: one round of text edits needed. No new simulation is required.** Fixing M1 (tariff epochs and the Comment 6 letter) and M2 (Green Riyadh caveats in §10.3, the Conclusions and the keywords) makes this dimension **READY AFTER MINOR FIXES**. The minor items are one-line edits; m5 optionally takes one short run.

**Findings: CRITICAL 0 · MAJOR 2 · MINOR 13**
