# Peer Review Report: Final Panel 2, Specialist Reviewer R5 (Control & HVAC Optimisation)

**Manuscript**: "Optimising Binary HVAC Switching in Saudi Residential Buildings with Model Predictive Control and Rule-Constrained PPO" (JKSU-ES, major revision, round 4)
**Files reviewed**: `/home/claude/v4/main.tex` (line numbers below), `supplement.tex`, `RESPONSE_LETTER.md`, the journal's "Comments not resolved by V3", `audit_report.md`, results in `/home/claude/rbrl_p12/results`, code in `/home/claude/rbrl_p12` (read-only), `PROVENANCE.md`.
**Reviewer role**: R5. I cover the formulation, baseline fairness, MPC, the clairvoyant bracket, constraint-violation disclosure, rule-constrained PPO and the title's claim.

---

## Overall assessment

The control content is now careful and mostly correct. The formulation is stated clearly:
- binary actions;
- a pointwise hard occupied ceiling;
- a cold rule on cooling steps only, with free-float unrestricted;
- Eq. 11, the two-block tariff in force;
- the limit-average definition, reconciled explicitly with finite 168 h scoring (L790–796).

The protocol is the same for every arm, and Rule A/C, the fallback and the back-off precedence are disclosed.

On the bracket:
- the optimistic-neighbour proof is valid (I re-derived each step at L1693–1711);
- V_N is labelled as a convention;
- comparisons are kept on one terminal (s_a ≤ B_a under V_N; S5).

Every constraint violation is now reported, including TUNED's held-out cold-rule breaches and the multi-zone MPC's over-temperature. These were panel-1 M1.

Four problems remain at MAJOR level:
1. The new title asserts more than the results support.
2. A stale "three epochs / 7 points" tariff statement survives in §10.3. The response to Comment 6, one of the journal's flagged comments, describes text that is no longer in the manuscript.
3. The new PPO training-length diagnostic is over-read. The response letter says the opposite of what the manuscript now claims.
4. Decision time is still unreported even though it was measured (panel-1 M5 is open).

All four can be fixed in the text without a rerun.

### Comparison fairness

| Baseline | Category | Same info? | Same model & period? | Tuning stated? | Fair? |
|---|---|---|---|---|---|
| THERM (1 °C, fixed) | conventional | zone T only | yes | n/a (assumed deadband, swept in Table 7(c)) | yes, with the deadband caveat stated |
| TUNED (2 switch points) | conventional, tuned | zone T only (less than MPC; stated) | yes | 0.05→0.01 °C grid, Rule A; 0.1 °C row in S2 | yes; the strongest simple baseline |
| Guard hysteresis | rule | zone T | yes | ceiling fitted, Rule A | yes |
| D1 one-step shield | model-based, 1 step | model + current T_out, irradiance (stated L1358) | yes | σ ∈ {0, 0.05, 0.1}, Rule A | yes |
| MPC 0.25–48 h, perfect | MPC | exact model, perfect in-horizon weather (more than TUNED; stated) | yes | λ scan + 2 refinements, Rule A; back-off precedence stated | yes, flagged as idealised |
| MPC 6/24 h, persistence | MPC | exact model, persistence | yes | as above; Riyadh/Taif 24 h at the 0.10 K fallback | mostly; comfort offset 0.07–0.09 K (disclosed) |
| RBRL (PPO in rules), 5 seeds | learning | 1 h perfect T_out forecast | yes; trained on tuning weeks | no hyperparameter search (stated); fixed 2×10⁵ steps | adequate for the null it reports; untuned (m10) |
| E2 (PPO + λ + forecast), 3 seeds | learning | richer forecast | Riyadh only | not Rule-A selected | descriptive only; not tabulated (correct) |
| CLV / B* | oracle | full window | yes, V_N terminal | per-window bisection | yes, as a bracket |

### Control rigour summary

| Aspect | Status | Evidence location | Comment |
|---|---|---|---|
| Formulation | OK | Defs 3–5, Eq. (cop) L903–943, L790–796 | Finite/infinite reconciled. Minor notation issue (m8) |
| Train / evaluation separation | OK | §7 L1516–1531 | Interleaved windows in one TMYx year; disclosed |
| Seeds and variability | OK / WEAK | §5.4, Table 6, T33 | 5 seeds, none dropped. No learning curves (M3) |
| Constraint violations reported | OK | L1628–1644, Table S4 | Complete. Cold-guard derivation is not strictly "by construction" (m1) |
| Robustness (model mismatch, forecast) | WEAK (disclosed) | §8.3, Limitations | Persistence only; no model mismatch; stated |
| Real-time feasibility | MISSING | §9.4 L2344 | Measured (T18) but not reported (M4) |
| Peak / cost metric definition | OK | Eq. 11, Remark 3, Table 4 | Constant marginal price stated; three-layer reporting |
| Ablation of controller components | OK | Table 6, §9.2 | Rules, learner, one-step model, horizon and forecast are isolated |

---

## Findings

### MAJOR

**M1. The title claims that MPC and rule-constrained PPO optimise binary switching. The results support neither as stated.**
- *Location*: L104–105 (`\title`); supplement L25–26; letter L7 and L25.
- *Quoted text*: "Optimising Binary HVAC Switching in Saudi Residential Buildings with Model Predictive Control and Rule-Constrained PPO".
- *What is wrong*: Readers will take "Optimising X with A and B" to mean that A and B are effective optimisers of X. The paper's own findings say otherwise:
  - (i) **PPO.** Inside the rules PPO reproduces the guard hold policy: 5.7 / 7.6% in Riyadh/Jeddah and 8.6–11.0% in Taif. That is 6.8 and 6.0 points *below* a tuned two-parameter thermostat (F4; Table 3; `rbrl_ppo5_v3_*`, `T1v3_heldout.csv`).
  - (ii) **MPC, perfect forecast.** MPC beats TUNED only with a perfect in-horizon forecast (F2 +4.2 to +6.0).
  - (iii) **MPC, persistence forecast.** With persistence the difference is not resolved (F3 −1.9 to +0.9).
  - (iv) **MPC, capacity and step.** The margin falls to 0.4 points at 9,600 kJ/K (`T21v3_riyadh_cth9600.csv` 16.17 vs TUNED 15.8). At a 5-min step TUNED exceeds MPC (25.0 vs 23.8).
  - (v) **TUNED.** The tuned thermostat attains about 70% of the clairvoyant lower end. This is the paper's principal practical finding, and the title does not name it.
- *The defence does not hold*: the letter's argument that "optimising names the task, not a result" (L25) is not how the title reads. The title is also a regression. Panel 1 reviewed the neutral title T3, and the source's own comment records that the pre-registered decision tree selected the neutral branch T3 ("condition A fails, so branch T3 applies", L101).
- *Fix*: Return to a neutral title that names the comparator. For example, T3 itself ("Tuned Thermostats, Rule-Constrained PPO and Receding-Horizon Control for Binary HVAC Scheduling in Saudi Residences"), or "Binary HVAC Switching in Saudi Residential Buildings: A Tuned Thermostat, Model Predictive Control and Rule-Constrained PPO Compared at Matched Comfort". Update the supplement title and letter L7 and L25 to match.

**M2. A stale tariff statement remains in §10.3, and the response to Comment 6 (a journal-flagged comment) describes manuscript text that no longer exists.**
- *Location (manuscript)*: L2413–2417 ("…the charge per on-command by 7 across the derived range and **the tariff by 7 across the three epochs** (Table 7)"); L2435–2438 ("…the on-commands TUNED avoids are the same under **all three epochs**… A percentage quoted against one tariff **epoch**…").
- *What is wrong in the manuscript*:
  - Table 7(a) now has only two tariffs, 0.18 and 0.21 SAR/kWh, giving 12.5 → 11.6, a range of 0.9 points.
  - The "7 points" comes from the withdrawn historical 0.05 SAR/kWh row: `T1v3_heldout.csv` TUNED Riyadh at price 0.05 gives `s_pooled_eq` = 18.58, and 18.6 − 11.6 = 7.0. `T4v3_bound.csv` also still holds a 0.05 row (bound 29.6). `config.py` L40 keeps `TARIFFS = {"historical": 0.05, …}`.
  - PROVENANCE.md has no entry for "the tariff by 7". As written, the Discussion ranks the tariff as a 7-point lever on the evidence of a table that shows 0.9.
- *What is wrong in the letter (Comment 6, L149–157)*:
  - It says "Both remedies are applied".
  - It quotes §3.4 as saying "Model S is a historical schedule, no longer the tariff in force, … used here as a stress-test instantiation …". That sentence is not in main.tex (grep for "historical schedule" and "stress-test" returns nothing).
  - It cites "Table 7(a) (three tariff epochs)" and "18.6, 12.5 and 11.6% under all three epochs".
  - The manuscript in fact applies one remedy only: it reruns at the tariff in force and removes the pre-2018 schedule.
- *Fix*:
  - Replace L2416 with "…and the tariff by about 1 point between the rate in force and the 2027 rate".
  - Replace "all three epochs" / "epoch" at L2436–2438 with "both schedules" / "schedule".
  - Rewrite the Comment 6 response to say that the main analysis was rerun at the tariff in force (the first remedy) and that the historical schedule was removed. Delete the quoted "historical schedule … stress-test" sentence, the 18.6% figure and "three tariff epochs".
  - Alternatively, if the historical tariff is wanted as a stress test, restore it explicitly as a labelled row in Table 7(a) and keep the letter as it is.

**M3. The new PPO training-length diagnostic is over-read, no learning curves are given, and the letter states the opposite of the manuscript.**
- *Location*: §5.4 L1278–1282 ("That shortfall is one of generalisation, not of training length … so a longer run on the same weeks has almost nothing left to gain"); Limitations L2566–2568 ("longer training is not run, but … so it has little to gain"); §9.2 L2195–2197. Letter L218 ("the claim that a longer training run would not help (now 'longer training was not tested')") and L245 ("the earlier statement that a longer training run would not help is removed").
- *Evidence* (`T33_ppo_hold_gap.csv`, training cost at the training rules):
  - The Taif seeds below hold have tuning-week gaps of −0.04, +0.05, 0.00 and +1.44%, and held-out gaps of +0.52, +2.50, +1.09 and +1.81%. The quoted numbers are correct.
  - The inference does not follow, for three reasons:
    - (a) The reference is the hold policy, not the optimum of the training reward. E1 shows that hold itself is 0.4 / 1.4 / **2.3%** above the in-rules optimum in Riyadh/Jeddah/Taif. Matching hold on the training weeks therefore does not mean that nothing is left to learn.
    - (b) A trained policy can beat hold on the training objective. Riyadh seed 43 is **−0.36%** below hold on the tuning weeks (`gap_tune_pct` = −0.357929).
    - (c) Generalisation and training length are not exclusive. Training length (and the untuned hyperparameters, entropy coefficient 0) can change held-out behaviour without changing the tuning-week cost. No learning curve or longer run is shown.
- *Contradiction*: The letter tells the editor that the longer-training claim was removed. The manuscript now makes that claim twice.
- *Fix*:
  - Rephrase L1278–1282 as follows: "On the six tuning weeks three of those four seeds are within 0.05% of the hold policy's training cost and the fourth 1.4%, against an in-rules clairvoyant optimum 2.3% below hold. The shortfall therefore appears on the held-out weeks; whether a longer run or other hyperparameters would change it was not tested."
  - Change Limitations L2566–2568 in the same way.
  - Add the SB3 episode-reward learning curves per seed (five seeds × three cities) to the supplement if they exist.
  - Correct letter L218 and L245 to describe the diagnostic truthfully.

**M4. Computation time per decision is still not reported, although it was measured (panel-1 R5 M5 is not closed).**
- *Location*: §9.4 L2344–2345 ("No claim is made about training cost, decision time or embedded deployability").
- *Evidence*: `results/T18_scalability.csv`:
  - MPC decision: 1,435.6 ms per 672-step window at H = 6 h (2.14 ms per step) and 5,462.9 ms (8.13 ms per step) at H = 24 h.
  - Rule layer: 0.84 µs per decision.
  - Hardware (`T18_environment.json`): 2-core Xeon at 2.1 GHz, 280 MiB peak RSS, no GPU.
- *What is wrong*: The paper's title now features MPC, and the rubric treats unreported per-decision time for an online controller as MAJOR. The numbers are about 10⁵ times below the 900 s step, so reporting them strengthens the paper.
- *Fix*: Add one sentence to §9.4 with per-decision times, hardware and the 900 s budget, plus PPO training wall-clock per seed. T18 may predate the 1,601-node headline grid. If so, re-time at 1,601 nodes (expect roughly 2×) or state the grid used.

### MINOR

**m1. The cold-side guard derivation omits the envelope term, so R2 is not strictly "by construction" even at the nominal parameters.**
- *Location*: Eq. (guard) L1209–1214 ($\epsilon_{\mathrm{cold}}\ge Q_{\mathrm{hvac}}\Delta t/C_{\mathrm{th}}$). The claim appears at L885–887, L1240–1241, L1538–1539 and L2207–2209 ("R1 and R2 exclude both by construction").
- *Evidence*:
  - When the outdoor air is cooler than the zone, the envelope adds to the cooling.
  - From the exact update with the in-season minimum outdoor temperature (EPW days 121–296): Taif T_out,min = 16.0 °C, and a cooling step from 22.40 °C ends at **21.9986 °C**, a drop of 0.4014 K, which exceeds ε_cold = 0.40.
  - Riyadh: 18.6 °C, drop 0.391 K. Jeddah: 24.8 °C, drop 0.363 K.
  - The realised record is zero (Table S4), so this is a guarantee issue, not a results issue.
- *Fix*: Write $\epsilon_{\mathrm{cold}}\ge[Q_{\mathrm{hvac}}+\max_t(\Lambda_i(T_{\min}+\epsilon_{\mathrm{cold}}-T_{\mathrm{out}}^{(t)})-Q_{\mathrm{sol}}^{(t)})^+]\Delta t/C_{\mathrm{th}}$, give the Taif value (0.401 K), and either adopt ε_cold = 0.41 or qualify "by construction" as holding for Riyadh and Jeddah and to within 0.002 K in Taif.

**m2. Multi-zone MPC: fit status, comfort offsets and resolution are missing from the main text.**
- *Location*: L2073–2079; Conclusions L2634–2635.
- *Evidence*:
  - `T31_mz_mpc_*_h24.csv` gives `fit_status` pooled_0.10 for 1×2 at both λ_ij (Table S-MZ marks it, the main text does not).
  - `dT_pooled` is −0.072 / −0.065 (1×2), −0.036 / −0.004 (2×2), and −0.068 / −0.026 (1×4) at λ_ij = 12.5 / 35. MPC-MZ therefore runs up to 0.07 K cooler than THERM, which is part of the drop from 18.3%.
  - Margins over TUNED at λ_ij = 12.5 are 3.6, 4.2 and **2.1** points. The 1×4 margin is below the paper's own 3-point rule.
- *Fix*:
  - Add the fallback mark and the ΔT̃ range in §8.4.
  - State that the 1×4 margin is not resolved by the 3-point rule.
  - Add that the distributed MPC with delayed plan exchange gives no *constraint-satisfaction* guarantee on the coupled plant, not only no optimality guarantee, consistent with the 0.0001 °C·h breach.

**m3. The comfort-offset slope is stated as general but is family-specific.**
- *Location*: Table 3 caption L1778–1780 ("about 1.3 points per 0.01 K"); L2547–2551; F3 discussion L1967–1970.
- *Evidence*:
  - The 1.3 figure is the guard family's.
  - Along the MPC λ family (Table S2), the 24 h controllers move 18.0 → 16.9 (Riyadh), 17.9 → 16.0 (Jeddah) and 17.5 → 16.8 (Taif) for ΔT̃ shifts of −0.058, −0.089 and −0.060 K. That is about 0.1–0.2 points per 0.01 K.
- *Fix*: Say that the slope is family-specific. Applied to F3, the 0.07–0.09 K offset is worth roughly 1–2 points, so "not resolved" stands (Jeddah is borderline at about 3).

**m4. No mechanism is given for the 0.25 h MPC.**
- *Location*: L1977–1978; Table 3.
- *What is wrong*: The 0.25 h MPC closes its horizon with a 24 h rollout of TUNED (`mpc_lambda.rollout`). Even so, it saves −3.9% in Riyadh with **+7.1%** more on-commands than THERM, about 16 points below its base policy. A reader of a "truncated rollout of a base policy" will expect near-TUNED behaviour, and the general disclaimer (L1386–1389) does not explain a deficit of this size.
- *Fix*: Add one sentence on the cause (for example, the λ term near λ* combined with the persistence tail and grid interpolation induces extra switching), or give a short diagnostic.

**m5. The ladder caption mixes scoring rules.**
- *Location*: Fig. 4 caption ("TUNED attains 70–74% of the saving at the bracket's lower end").
- *What is wrong*: TUNED's Rule-C saving (simulator terminal) is divided by CLV's raw V_N saving. Panel-1 m5 is only partly closed: the conclusions now correctly use B_a.
- *Fix*: Use TUNED s_a under V_N against CLV's Rule-C saving (12.7/18.3, 13.2/18.5, 12.9/16.5, i.e. 69, 71 and 78%), or label the figure as approximate.

**m6. The keyword "CO₂ reduction" is not supported.**
- *Location*: L148.
- *What is wrong*: The paper shows that at matched comfort switching control does not change electricity (L2456–2459).
- *Fix*: Replace it with, for example, "switching cost" or "clairvoyant bound".

**m7. Internal drafting comments remain in the LaTeX source.**
- *Location*: L88–103 (title decision tree, "RULING §17", "branch T3 applies"), L117–119, L145, L2054–2055 ("Gate (RULING §12.1): J-MZ by Sat 14 Nov 20:00"), L2410–2411, the unused `\pend` macro (L71); supplement L19 and L27.
- *Note*: Nothing renders; no "PENDING" or "??" appears in either PDF. The comments would, however, ship with a source upload, and L101 contradicts the chosen title.
- *Fix*: Delete them.

**m8. Formulation notation.**
- *Location*: Eq. (cop) L912–917; Def. 6 L1196–1201.
- *What is wrong*:
  - The away-step empty-house ceiling, which binds for the setback arms and the bound, is stated only in prose (L932–934), not in the constraint set.
  - R1 is written with T_max, but every fitted arm uses the ceiling $\overline T$ (L1270, L1350).
- *Fix*: Write the ceiling as $T^{\mathrm{hi}}_t$, as in Eq. (meanconstrained), and R1 as $T\ge\overline T-\epsilon_{\mathrm{hot}}$ with $\overline T=T_{\max}$ in training.

**m9. The MPC infeasibility fallback is undescribed.**
- *Location*: §5.5 (MPC paragraph).
- *What is wrong*: `mpc_lambda.py` applies the TUNED action when no action has a finite planned cost (docstring L33–34). `fallback_steps` = 0 in every T21v3, T31 and T28v3 run I checked.
- *Fix*: Add one clause: "a TUNED fallback for infeasible plans, never triggered".

**m10. The learner is untuned, and the Limitations do not draw the consequence.**
- *Location*: §5.4 L1265 ("no hyperparameter search was made", entropy coefficient 0); Limitations "Scope of the learner".
- *What is wrong*: The Taif shortfall and the null result may depend on these settings.
- *Fix*: Add "with one untuned hyperparameter set" to the Limitations item.

---

## Numbers verified against the CSVs

All of the following match unless noted:
- **Table 3, MPC rows**: every MPC row in all cities, including fit marks, † cells and back-off values: `T21v3_{riyadh,jeddah,taif}.csv`, `T21v3_pers_*.csv`.
  - λ/λ*: 1.002–1.024 (6/24 h perfect); 1.226 / 4.577 (48 h); 13.09 / 2.33 / 6.22 (24 h persistence).
  - Grid refinement 18.16 / 18.50 / 16.65 (`T21v3_conv_*`).
- **Table 3, other arms**: TUNED, guard and D1 (σ = 0, 0.05, 0.1), with s, ΔT̃, on-commands and energy: `T1v3_heldout.csv`, `T_D1_latch_*.csv`.
- **Comfort records**: TUNED cmd-under 0.000674 / 0.006576; TUNED ff-under Taif 0.29, guard 0.34.
- **Statistics**: F1–F4 HL and intervals (gate log P12): +12.64 / +13.71 / +11.84; +6.00 [3.83, 7.48], +4.21, +4.56; F3 −0.09, +0.92, −1.90; F4 −6.65, −6.01, 0.00.
- **Multi-zone**: MPC-MZ 18.26 (1×1), 16.04 / 15.80 (1×2), 15.87 / 16.10 (2×2), 15.69 / 16.05 (1×4); over-temperature 0.000102 (1×4, λ_ij = 35); fallback 0.
- **PPO hold-gap diagnostic**: every figure quoted at L1278–1282 and L2195–2197 (`T33_ppo_hold_gap.csv`).
- **Sensitivities**: capacity (`T21v3_riyadh_cth*`), step (`T21v3_riyadh_dt5/dt30`, `T21v3_{jeddah,taif}_dt30`), λ-scale rows of Table S2.
- **Ratios**: ladder caption ratios (69.5 / 74.0 / 74.3%); conclusion "62–65% of the provable bound" (S5: 12.7/19.7, 13.2/20.2, 12.9/20.8).
- **Discrepancy found**: "tariff by 7 across the three epochs" (M2).

## Response letter

- **Comment 2 (capacity)**: truthful and complete.
- **Comment 3 (split)**: truthful; dates match code (0-based index 121 = 2 May).
- **Comment 8 (time step)**: truthful; Table 8 and S1 match the CSVs.
- **Comment 6 (tariff)**: the action taken (rerun at the tariff in force) is correct and answers the journal. The letter text, however, describes a historical/stress-test passage and a three-epoch table that are not in the manuscript (M2). It must be corrected.
- **Comment A and the editor's instruction**: mostly met. Letter L218 and L245 misstate the training-length text (M3). The new title is defended as claiming no winner, but the wording still implies efficacy (M1).

## Panel-1 closure (R5 items, read after writing the findings above)

| Panel-1 item | Status |
|---|---|
| M1 TUNED cold-rule breaches unreported | **Closed**: L1638–1642, Table S4, L2207–2208 |
| M2 "requires a perfect forecast"; knob precedence | **Closed** (wording "not resolved"; precedence L1370–1372, L1968–1970). Optional refit not done; offset disclosed |
| M3 comfort-offset sign error, in-rules overstatement | **Closed**: L2037–2040, L2046–2048; Remark 5 restricted to the guard's rules |
| M4 PPO generalisation; E2 non-discriminating | **Mostly closed** (Taif scoped, E2 "consistent with, not evidence for", "nearly minimised"). The longer-training claim has **returned** (M3 above) |
| M5 decision time unreported | **Open** (M4 above) |
| m1 λ* definition; m2 Rule A sets comfort; m3 CLV cap knob; m4 "rescored under V_N"; m6 5-min caveats; m7 Taif 48 h mark; m9 nominal-plant qualifier; m10 5.7 vs 5.8; m11 other learners; m12 D1 sensors and noise; m13 rollout outside rules; m14 H = 2,880 / monthly problem; m15 corollary model | **Closed** |
| m5 ratios mix scoring rules | **Partly closed** (conclusions fixed; ladder caption not; m5 above) |
| Other panels' control-relevant MAJOR items: EIC F1 (dates) and F2 ("compressor on-commands"); R4 M3 (Euler statement); DA M5 and M6 | **Closed** (checked L1519–1524; no "compressor on-command" remains; L430–434 checks out, 2·77.2e3/23.75 s = 1.8 h; L1964–1966; Table 6 / §9.2 scoping) |

No placeholders render in main.pdf or supplement.pdf.

## Paper Quality Standard (R5 items)

| ID | Status | Note |
|---|---|---|
| Q2.1 | OK | Shield vs masking, DP vs MILP, PPO vs SAC, GA/SA omission argued by the bound |
| Q2.3 | OK | ≥5 baselines incl. tuned conventional, MPC ladder, learner and oracle; information asymmetries stated |
| Q2.4 | OK | Table 6 isolates the rule layer, learner, one-step model and horizon |
| Q4.2 / Q4.3 | OK / WEAK | Exact paired tests, HL, Holm; no learning curves (M3) |
| Q4.4 (computational) | MISSING | M4 |
| Q8.2 | OK / WEAK | Deadband, identity, step and capacity mechanisms are clear; 0.25 h MPC deficit unexplained (m4) |
| Q11.3–Q11.6 | OK | Algorithm 1 matches the code (budget, ceiling grid, phases, fixed-budget termination); MPC description matches `mpc_lambda.py` except the undisclosed fallback (m9) |

## Verdict (control and optimisation dimension)

**READY AFTER MINOR FIXES**, conditional on the four MAJOR items, all of which are text-only:
1. Neutral title.
2. Delete "three epochs / 7 points" and correct the Comment 6 response.
3. Rephrase the training-length inference and correct the letter.
4. One sentence with the measured decision times.

No new experiment is required.

**Findings: CRITICAL 0 · MAJOR 4 · MINOR 10**
