# R1_methodology — Final verification panel 2 (JKSU-ES round 4)

Role: methodology reviewer (agents/methodology_reviewer_agent.md). Scope: design and evaluation protocol (tuning vs held-out windows, Rule A/B/C, admissibility), statistics and every "resolved / not resolved" claim against the paper's own rule, the ablation (Table 6) against Q2.4, reproducibility, Algorithm 1 vs equations vs Methods, and the new additions (PPO training-length diagnostic, cooler-city sensitivity, setpoint sensitivity, Fig. 3 selection rule, Fig. 4 bars).

Read: main.tex (all 2,717 lines, as of 20:21 on 13 Nov), fig_traces.tex, fig_ladder.tex, fig_timestep.tex, tables/tab_stats.tex, supplement.tex (structure, S2, S7), RESPONSE_LETTER.md (all), the journal's outstanding comments (docx), audit_report.md. Code read (read-only): rbrl_ppo.py (ZoneEnv.reset/step), ppo_hold_gap.py, greenriyadh_sens.py, setpoint_sens.py, fig_day_traces.py, stats_v3.py (Holm), final_tables.py (windows).

**CSV values checked (all match the manuscript unless a finding says otherwise):**
T1v3_heldout.csv (TUNED/guard s, ΔT̃, on, energy; the hidden `historical` 0.05 SAR/kWh rows); rbrl_ppo5_v3_{riyadh,jeddah,taif}.csv (every seed's s, ΔT̃, ceiling); T33_ppo_hold_gap.csv (all 15 rows); E1v3_hold_dp.csv; T34_greenriyadh_sens.csv; T32_setpoint_sens.csv; T35_day_traces.csv (Fig. 3: λ, counts 34/27/23, band 22.00–23.99); fig_ladder.tex bar values vs T1v3/T21v3; T20v3_paired_stats.csv (every cell of Table S7, incl. F5); T_D1_latch_*.csv and T_D1_ppo_*.csv (σ = 0 is the Rule-A choice in every city; Taif D1-on-PPO 8.04/10.42/8.93/9.93/11.97); T16v3_r*.csv (in-rules MPC, 5.886/6.434-point margins, Jeddah 4.361 at λ/λ* 0.601); rbrl_norules5_v3.csv (one admissible seed, cap 23.50, −3.54); T1v3_heldout_{dt5,dt30,cth2400,cth7200,cth9600}.csv and T21v3_riyadh_{dt5,dt30,cth*}.csv, T21v3_{jeddah,taif}_dt30.csv (Table 8, Table 7(d), fitted deadbands 1.78–1.79 and 0.94–0.99); T21v3_csw*.csv; T1v3_sens.csv (self-scores −0.78/−0.11/0.00; hardware grid; per-window refit); gate_p12.log (188/188 PASS). No placeholder survives in main.pdf, supplement.pdf or main_sn.pdf (`\pend` is defined but never used; no "??" or undefined references).

---

## Summary assessment

The protocol is now specified well. Thirteen non-overlapping 168 h windows (day indices 121–289, checked against `final_tables.py`) are assigned alternately to tuning and held-out sets. One admissibility rule with a stated fallback applies to every arm. The comparator is equalised per window by the cheapest crossing. The paired tests are exact and the families are pre-declared, with the HL estimate leading. A 3-point resolution rule is stated. Every number I traced matches its CSV, and the panel-1 methodology MAJORs are closed (see the closure section).

Four problems remain, and all are text or table fixes; no rerun is needed:
- The headline learner result ("falls below it in Taif") and the 30-min result breach the paper's own 3-point rule.
- The new training-length diagnostic is worded more strongly than its own data and script allow, and the response letter says the claim it makes was removed.
- A third, historical tariff epoch, deleted from Table 7, is still used in the Discussion and in the letter's answer to journal Comment 6.
- Table 6 does not yet meet the ablation specification Q2.4.

Recommendation (methodology): Minor/Major revision. Confidence 4/5.

---

## MAJOR

### M1. Differences below the paper's own 3-point threshold are reported as directional findings, including in the abstract and conclusions

- **Rule (Sec. 7, l.1600–1604):** "Pooled differences of less than 3 points between arms are treated as not resolved, whatever a test says."
- **Violations:**
  1. **PPO in Taif.** Abstract l.136–137: "reproduces their hold policy in two cities and falls below it in Taif". The same wording is in C4 l.199, Conclusions l.2614–2615, the Fig. 4 caption ("in Taif its seeds reach down to 8.6% against the guard's 11.0%") and the letter (summary; Comment 4; Comment 7; "Overstated conclusions" bullet 5).
     - Evidence: rbrl_ppo5_v3_taif.csv s_pooled_eq is 8.608 / 11.002 / 9.616 / 9.000 / 10.050 against the guard's 11.002 (T1v3_heldout.csv). The shortfalls are 0.95–2.39 points, all below 3.
     - Two of the four seeds (42, 45) were fitted at ceiling 23.84, not the guard's 23.86. They are therefore not compared with the same hold policy.
     - The seeds' held-out ΔT̃ is +0.050 to +0.093 K (dT_pooled), against the guard's +0.056. Table 3 prints "---" for these values.
  2. **30-min step.** Abstract l.135: "slightly less than the comparator at 30 min". Sec. 9.3 l.2285–2287: "TUNED no longer beats THERM … saves −1.2 to −1.5%".
     - Evidence: T1v3_heldout_dt30.csv gives −1.23 / −1.53 / −1.20.
     - THERM's Rule-C self-score is −0.8% at 15 min (T1v3_sens.csv self_score) and was not computed at 30 min.
     - At 2,400 kJ/K the same situation is reported correctly (l.2009–2011: "the small negative savings are not resolved from zero"). The 30-min case should be treated the same way.
     - The on-command count (+2.2 to +2.8%) is a raw count and can stay.
  3. **Hardware grid.** l.1897–1898: "the guard exceeds TUNED in Taif". The values are 11.00 against 8.37 (T1v3_sens.csv hw_0.1K), a 2.6-point gap.
  4. **D1 on PPO in Taif.** l.2044–2045: "for three of the five seeds below their own rule-layer results (seed 42: 8.0 against 8.6%)". The gaps are 0.6–0.7 points.
  5. **Multi-zone MPC.** Conclusions l.2634–2635: MPC "saves 15.7–16.1%, against 18.3% in the single zone". The gap is 2.2–2.6 points. In the same sentence the TUNED comparison is labelled "not resolved"; this one is not.
- **Fix:**
  - Abstract and C4/Conclusions: "PPO inside hard rules reproduces their hold policy in Riyadh and Jeddah; in Taif four of five seeds deviate from it and save 1.0–2.4 points less, a difference below the 3-point resolution threshold."
  - Abstract: "…and has no resolved saving at 30 min (−1.2 to −1.5%, while issuing 2–3% more on-commands)".
  - Sec. 9.3: "no longer has a resolved saving over THERM".
  - l.1898: "the guard then saves more than TUNED in Taif (not resolved)".
  - l.2044: delete the clause or add "(not resolved)".
  - Conclusions l.2635: add "(differences not resolved)".
  - Table 3: print the RBRL and D1-on-PPO ΔT̃ ranges (Taif RBRL +0.050 to +0.093 K).
  - Apply the same wording to the Fig. 4 caption and the letter.

### M2. The PPO training-length diagnostic says more than its data and its own script support, and the letter says the claim was removed

- **Location:** Sec. 5.4 l.1278–1282: "That shortfall is one of generalisation, not of training length: … so a longer run on the same weeks has almost nothing left to gain." Limitations, "Scope of the learner", l.2566–2568: "longer training is not run, but … so it has little to gain."
- **What is wrong:**
  1. **The available gain is not "almost nothing".** The gain a longer run could make on the training weeks is bounded by E1's margin, not by the gap to hold. `ppo_hold_gap.py` says so itself: "cannot gain from longer training on TUNE_W by more than E1's DP margin". E1 is computed on the same six tuning weeks (E1v3_hold_dp.csv, windows = TUNE_W). There, hold lies above the λ = 0 DP optimum by 0.43%, 1.36% and 2.33% (ratio_hold_dp 1.0043 / 1.0136 / 1.0233). In Taif that margin is the same size as the held-out shortfall the diagnostic is meant to explain (gap_eval_pct 0.52 / 2.50 / 1.09 / 1.81, T33_ppo_hold_gap.csv).
  2. **The training set is only six weeks.** `ZoneEnv.reset` (rbrl_ppo.py l.107–110) draws one of six fixed weeks and always starts at 23 °C, so the 298 training episodes are repeats of six deterministic weekly trajectories. A generalisation gap is the expected result of that design. The design is stated only as "each episode draws its start date from the six tuning windows". Neither the Limitations nor the response to Comment 3 say that the learner sees six weeks (about 1,000 h) of weather.
  3. **The letter contradicts the manuscript.**
     - The Comment A tone bullet says the claim "that a longer training run would not help" is "now 'longer training was not tested'". That phrase does not occur in main.tex (grep finds 0 hits).
     - "Overstated conclusions" bullet 5 says "the earlier statement that a longer training run would not help is removed".
     - The letter's own quotation of Limitation 12 retains "so it has little to gain".
- **Numbers verified:** Taif seeds' tune gaps (−0.04, +0.05, 0.00, +1.44%) and held-out gaps (0.5–2.5%) match l.1279–1282. "Within 0.9% except one Taif seed (1.4%)" (l.2195–2197) matches: Riyadh is at most 0.45% and Jeddah at most 0.86%.
- **Fix:**
  - l.1278–1282: "On the six tuning weeks three of those four seeds are within 0.05% of the hold policy's training cost (the fourth 1.4%), and they fall 0.5–2.5% above it only on the held-out weeks. The shortfall therefore appears on weather not seen in training. A longer run on the same weeks could gain at most E1's margin (0.4, 1.4 and 2.3%), and longer training was not tested."
  - Limitation 12: replace "so it has little to gain" with "it could gain at most E1's margin on those weeks", and add "PPO is trained on six weekly weather sequences, so its held-out behaviour is a test of generalisation from six weeks".
  - Make both letter passages match the new text.

### M3. A historical third tariff epoch, removed from Table 7, is still used in the Discussion and in the letter's answer to journal Comment 6

- **Location:** Sec. 10.3 l.2413–2416: "…the charge per on-command by 7 across the derived range and the tariff by 7 across the three epochs (Table~\ref{tab:sensitivity})". l.2436: "the on-commands TUNED avoids are the same under all three epochs".
- **What is wrong:**
  - Table 7(a) has two rows, 0.18 → 12.5 and 0.21 → 11.6. On the table, the tariff moves the saving by 0.9 points, not 7.
  - The 7 points come from a `historical` 0.05 SAR/kWh run, T1v3_heldout.csv rows tariff=historical with s = 18.58 / 19.88 / 17.98. That tariff is defined nowhere in the revised manuscript. It is the kind of pre-2018 instantiation that journal Comment 6 asked to be removed or labelled as a stress test.
  - The letter, Comment 6, says three things the manuscript does not do:
    1. "Table 7(a) (three tariff epochs)".
    2. "its cost saving is 18.6, 12.5 and 11.6%".
    3. It quotes Sec. 3.4 as saying Model S "is a historical schedule, no longer the tariff in force, and it is used here as a stress-test instantiation". That sentence is not in main.tex (0 hits for "stress-test" or "historical schedule"), and it contradicts Sec. 3.4, l.655, where Model S "is instantiated with the Saudi residential tariff in force since January 2018".
  - The same letter answer also says "the pre-2018 four-tier schedule has been removed from the analysis altogether". This misstates the manuscript on an item the journal listed as not resolved.
- **Fix:** take one of two routes.
  - (a) Delete "and the tariff by 7 across the three epochs" (replace it with "and the 2027 repricing by about 1"), change l.2436 to "under both schedules", and in the letter delete the stress-test quotation, "three tariff epochs" and "18.6".
  - (b) Restore the historical row in Table 7(a), labelled as a stress test with its rate and terminal, and define it in Sec. 3.4.
  - Route (a) is consistent with the letter's claim that the pre-2018 schedule is removed.

### M4. Table 6 does not meet the ablation specification (Q2.4) of the quality standard

- **Location:** Sec. 9.2 "Component Ablation and Sensitivity", Table~\ref{tab:ablation}, l.2140–2209.
- **What is wrong, item by item against Q2.4:**
  1. There is no dedicated `\subsection{Ablation Study}` with `\label{sec:ablation}`. The ablation shares a subsection with the sensitivities.
  2. The table is a single-column `table` at `\columnwidth`, but Q2.4 item 4 and Q9.1 require a full-width `table*` in this two-column template.
  3. There is no "Removed / replaced component" column and no Δ against the full model.
  4. No row is marked as the full model "(ours)". RBRL appears only as "PPO inside the training rules".
  5. Only one metric (s) is given, whereas the main table reports s, ΔT̃ and on-commands.
  6. There is no bold best value per column.
  7. Seeds are shown as ranges, not as mean ± std over the five runs (Q4.2).
  8. The rows are not "one change at a time" from a single full model. For example, the D1 latch differs from the guard in both guard bands and ceiling fit, and TUNED differs from RBRL in rules, learner and switch points. The table regroups ladder arms rather than ablating one configuration.
  9. The analysis does not rank the components by contribution.
  - Item 6 of the specification (a Discussion link) is partly met: Sec. 10.3, "controller class by 13", and Conclusions ¶3.
- **Fix, using existing CSVs only:**
  - Make Table 6 a `table*` with columns: Variant | Removed / replaced component | s (%) | ΔT̃ (K) | On-commands avoided (%) | Δs vs full model (points), per city or in three city blocks.
  - Use "RBRL (rules + PPO, ours)" as the full model.
  - One-change rows: "w/o rules" (rbrl_norules5_v3), "w/o learner (hold = guard hysteresis)", "rules → D1 one-step shield" (T_D1_ppo), and "+ 24 h horizon inside the same rules" (T16v3 at the training and guard rules).
  - Keep TUNED, the D1 latch and E2 as reference rows below a rule.
  - Give the seeds as mean ± std with n = 5, bold the best per column, and mark the fallback cells.
  - Rename the subsection "Ablation Study" with `\label{sec:ablation}` and move the sensitivities to their own subsection.
  - Add one sentence ranking the contributions: one-step model (+7 to +8 points over the guard in Riyadh and Jeddah) > horizon (+4 to +5 over D1) > learner (0 in Riyadh and Jeddah, −1 to −2 in Taif, not resolved) > rules (needed for admissibility in this configuration).

---

## MINOR

**m1. The Holm statement is not true in every case, and error control is per family only.**
- Location: Sec. 7, l.1596–1599: "0.047 is the smallest Holm-adjusted p attainable, reached by a city only when all seven of its windows agree in sign; one discordant window removes significance".
- What is wrong: `stats_v3.py` Holm-adjusts the Wilcoxon p. One discordant window of rank 1 or 2 gives an exact two-sided p of 0.031 or 0.047. If that city ranks third in its family, its Holm-adjusted p is max(0.047, 1 × p) = 0.047. No current family is affected (every resolved contrast is 7/0 or 0/7 in T20v3), but the sentence is false as a general statement.
- Also, Holm is applied within each three-city family, and the twelve contrasts are not jointly controlled.
- Fix: "…reached by a city whose seven windows agree in sign (and, for the Wilcoxon test, by one with a single discordant window of small rank when the other two cities are unanimous)", and add "error control is per family".

**m2. A clause in Remark 1 states the direction of the capacity bias backwards.**
- Location: Remark 1, l.472–474: "so the reference value probably lies above the effective one, towards the capacities at which the tuned thermostat gains least".
- What is wrong: TUNED gains more at higher capacity (−2.8 / 12.5 / 16.0 / 15.8%). A reference above the effective value therefore sits towards the capacities at which TUNED gains most, and at which MPC's margin over TUNED is smallest. That is what the abstract (l.133–134) and Sec. 8.3 (l.2013–2015) say.
- Fix: "…towards the capacities at which MPC's margin over the tuned thermostat is smallest".

**m3. TUNED's deadband exceeds the interval the paper calls admissible.**
- Location: l.1885–1887: TUNED's deadband 1.35/1.36/1.32 °C is "close to the widest that the band and the 15-min excursion admit (Remark~\ref{rem:rc})". Remark 1 gives 0.375 ≤ δ ≤ 1.25 °C.
- What is wrong: 1.25 °C is the limit for a deadband centred on the band. The off-centre upper limit of eq. (8) is 2 − 0.375 − 0.129 ≈ 1.50 °C. TUNED's off points (22.32–22.36 °C) also lie within QΔt/C = 0.375 K of T_min, which is why it records commanded under-temperature (T1v3_heldout.csv: 0.00067 and 0.0066 °C·h).
- The deadband sweep (Table 7(c)) holds the centred comparator to 1.25 °C, while TUNED is admitted empirically at up to 1.46 °C (T7v3_deadband.csv, 23.76/22.30 against the 1.25 °C comparator).
- Fix: state both limits (1.25 centred, about 1.50 off-centre), and note that the comparator sweep is held to the centred limit while TUNED's admission is empirical (Rule A).

**m4. Fig. 4 (fig_ladder.tex): a label collision and a mixed-measure ratio.**
- The bar labelled "Guard rules" is the guard hysteresis (5.7 / 7.6 / 11.0). In Table 3, "guard rules" denotes MPC confined to the guard's thresholds (6.7 / 4.4 / 10.5). Relabel the bar "Guard hysteresis".
- The caption's "TUNED attains 70–74% of the saving at the bracket's lower end" divides a Rule-C, simulator-terminal saving by CLV's raw V_N saving (69.5 / 74.0 / 74.3%). Sec. 8.1 (l.1741–1743) forbids this pairing, and panel 1 (m3) removed it from the Conclusions.
- Fix: drop the ratio, or quote s_a/B_a (62–65%) as the Conclusions do.

**m5. Fig. 3 (fig_traces.tex): the selection rule and the comparator are under-specified.**
- "Hottest" is defined in code as the highest mean outdoor temperature over the window (fig_day_traces.py l.31); the caption should say so.
- THERM is drawn unshifted (δ = 0), while every saving uses THERM(δ_w); say so.
- "Day 0 is warm-up" suggests day 0 is excluded from scoring, but every scored window runs N = 672 steps from T_0 = 23 °C, including day 0. Use "day 0 is not shown".

**m6. Table 3 omits comfort offsets for the seed rows.** The RBRL (Taif) and D1-on-PPO rows print "---" for ΔT̃, although the CSVs have them (Taif RBRL +0.050 to +0.093 K). Print the ranges, since the caption's comfort-offset caveat applies to them (see also M1).

**m7. Algorithm 1 (Q11.3/Q11.4).**
- The audit's H flags are mostly false positives:
  - J_w is used in Rule A (l.1553), though written J_{arm,w} in Eq. (saving).
  - The algorithm writes r_{N−1}, not r_N.
  - d_0 is defined in the \Require line.
- Real gaps:
  1. The operator 𝓡(·;T̄) is not defined in the text. Definition 4 states R1 with T_max, and the ceiling T̄ appears only in the guard paragraph (l.1349–1351) and l.1270. Define R1 as T ≥ T̄ − ε_hot, with T̄ = T_max in training.
  2. T^(0) = 23 °C and greedy (argmax) evaluation appear only in the algorithm. State both in Sec. 5.4 and in the protocol, where T_0 has no value.
  3. Name the SB3 defaults that apply (n_epochs 10, GAE λ 0.95), or say "SB3 defaults".
  4. Use one symbol, J_{arm,w} or J_w, throughout.

**m8. C3 and Rule A say "a single fallback", but MPC has a third device.** MPC alone has the occupied-ceiling back-off b (l.1370–1373, † cells), which no other arm has. Name it in C3 (l.184–187) and Rule A (l.1554–1556).

**m9. The cooler-city sensitivity uses a different protocol from the headline.**
- Location: l.2460–2466.
- The run uses thresholds that are not refitted (T34 fit_status "fixed"), a raw saving against unshifted THERM (12.9% at ΔT_out = 0, against the headline equalised 12.5%), and THERM's occupied mean moving by up to −0.018 K.
- The text labels it "raw" and "first-order", which is accurate, but it should say that Rule A/C was not applied.
- The setpoint sensitivity (T32) is on the held-out windows as stated; it was verified (0.85 / 1.41 / 2.33%; 0.109–0.117 K).

**m10. Reproducibility.**
- The trained PPO models (29 MB) are not in the Zenodo archive (l.2678–2680). PPO retraining is not bit-reproducible across hardware or library versions, and every RBRL, D1-on-PPO and T33 number depends on these exact files (T33 records their hashes). Archive them.
- The gate "retains some checks written for the band of an earlier version". State how many of the 188 invariants are legacy.

**m11. E2 uses three seeds, below Q4.2's ≥ 5 for RL.** E2 is not tabulated and is described as "consistent with, not evidence for" a null, which is appropriate. State the seed count as a limitation of that test in Sec. 9.2.

---

## New additions: protocol and accuracy

| Addition | Same protocol? | Described accurately? |
|---|---|---|
| PPO training-length diagnostic (T33) | Same simulator and windows, training rules (cap 24.0), training cost. Appropriate. | Numbers are accurate. The inference is overstated (M2). |
| Cooler-city (T34) | No. Thresholds fixed, raw saving, no Rule C. | Labelled "raw"; numbers accurate (10.5 / 13.7%, 12.8–13.6%). Say that Rule A/C was not applied (m9). |
| Setpoint (T32) | THERM's own curve on held-out windows. Appropriate. | Accurate (0.9 / 1.4 / 2.3%; 0.10–0.12 K). |
| Fig. 3 trace | Rule-A-fitted TUNED and MPC λ (0.2429 from T21v3_riyadh); THERM unshifted. | Counts and ranges accurate. Selection criterion and comparator not stated (m5). |
| Fig. 4 bars | Values equal Table 3 to 4 decimals. | Label collision and mixed ratio (m4). Taif PPO shortfall stated as directional (M1). |
| Fig. 5 / Table 8 | Every arm refitted. | Accurate. 30-min "slightly less" (M1). |

## Statistical-reporting completeness

Adequate. The tests are exact and their choice is justified for n = 7. HL estimates with exact 95.3% intervals lead the p-values. Families are pre-declared with Holm within each family, the p floor is disclosed, and comfort offsets are shown beside each contrast. Nulls are reported (F3, F4 Taif, multi-zone). There is no sign of selective reporting. Remaining gaps:
- m1 (Holm wording and per-family control).
- The comfort slope of about 1.3 points per 0.01 K means Rule A's 0.03 K tolerance spans about ±4 points, more than the 3-point rule. This is disclosed in Limitations; it is not recalibrated.

## Methodological fallacies check

- **Overfitting / generalisation:** six training weeks (M2), disclosed only partly.
- **Confirmation bias:** none found. The paper reports results against its own method.
- **Multiple comparisons:** per-family only (m1).
- **Simpson-type aggregation:** pooled savings are the stated estimand, and per-window signs are given.

## Response letter: truthfulness and completeness (methodology items)

- **Comment 3 (split):** fully answered, and true to the manuscript and code (windows 121–289 every 14 days, alternate assignment, no validation set). It should add that PPO trains on six weekly sequences only (M2).
- **Comment 8 (time step):** answered and true. The step sweep is refitted, and "unaffected" is withdrawn. The 30-min wording needs aligning (M1).
- **Comment 6 (tariff):**
  - Not truthful in three places: the quoted "stress-test" sentence is absent; "three tariff epochs" in Table 7(a) is wrong; and "18.6, 12.5 and 11.6%" quotes a run that is no longer in the paper (M3).
  - The substantive remedy (rerun at the tariff in force) is done.
- **Comment A / editor:** two statements about training length are untrue (M2). "Every difference … from unrounded values" holds for the values I checked.
- **Comment 2:** "In Jeddah and Taif TUNED moves from −1.4 and −1.3% to 15.8 and 16.0%" is consistent with the CSVs.

## Panel-1 closure (read after writing the findings above)

R1 (panel 1) MAJORs:
- **M1** (Rule C "no part … setpoint difference"; threshold vs admission noise): **closed**. The sentence is replaced (l.1766–1768). The per-window refit and the untested F2/F3 robustness are disclosed (l.2552–2556), and Table S7 has the ΔT̃ column.
- **M2** ("requires a perfect forecast and a light plant"): **closed** (C4, l.195–197; Sec. 8.3, l.1964–1966).
- **M3** (sign error in the in-rules comfort argument): **closed** (l.2036–2040: "despite a 0.10 and 0.04 K cooler mean, which penalises it; this compares different rule sets"; the claim is restricted to the guard's own thresholds).
- **M4** (PPO "converges"): **mostly closed**. The wording is now "reproduces … falls below it in Taif", and E2 and MANUAL are named as exceptions in C3. The residual issue is that "falls below" is itself unresolved under the 3-point rule (M1 here).

Panel-1 minors:
- **Closed:** m2 (5.7; 5.5/3.4/6.2), m3 in the Conclusions (62–65% of B_a), m4, m5, m6, m7 (H = 2,880), m8, m9, m10 (setpoint rerun on held-out windows, T32), m11 (grid-edge stated), m14, m15 (no "compressor on-commands").
- **Open:**
  - m1: the reworded Holm sentence is still not exact (m1 here).
  - m3: the mixed ratio has reappeared in the Fig. 4 caption (m4 here).
  - m13: 30-min "slightly less" (M1 here).
  - m12: partly closed; THERM's step-comfort records are labelled as coming from a separate run.

Other panel-1 MAJOR/CRITICAL items checked in passing:
- EIC F1 (dates off by one): **closed**. 2 May = day 121 is correct for a non-leap year.
- EIC F2 ("compressor on-commands"): **closed**.
- R6 CRITICAL (D1 "lifts the trained policies to TUNED's level"): **closed** (l.2041–2045, l.2617–2619 now restrict it to Riyadh and Jeddah).
- R6 M2 (one-sided actuation condition): **closed** (l.518–524, "≈9,700 kJ/K").
- R6 M4 (commanded under-temperature of TUNED): **closed** (l.1638–1642).
- R6 M7 (the 0.05 SAR/kWh epoch with energy-only terminal): the row was removed from Table 7, but the Discussion and the letter still use it (**new M3**).

## Deterministic audit, judgement on its MAJOR flags

- D1 (no roadmap): **false positive**. The roadmap is at l.210–220 with `\ref{sec:…}`.
- G (bold in tab:sensitivity, tab:timestep): **acceptable**. Bold marks the reference setting, and both captions say so ("Bold: reference setting", "Bold: headline step").
- H (Algorithm symbols J_w, d_0, r_N): **mostly a false positive**. The real gaps are listed in m7.

---

## Verdict (methodology dimension): **NOT READY**

All four MAJOR items are text or table edits, and the existing CSVs support each fix (M4 needs Table 6 rebuilt from files already present). No new simulation is required. Once M1–M4 are fixed, the methodology dimension would be READY AFTER MINOR FIXES.

**Findings: CRITICAL 0 · MAJOR 4 · MINOR 11.**
