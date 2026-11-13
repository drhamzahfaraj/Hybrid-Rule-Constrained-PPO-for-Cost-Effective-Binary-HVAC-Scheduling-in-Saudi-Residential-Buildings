# Peer Review Report: R5_control

**Reviewer Role**: Specialist Reviewer R5, Control & HVAC Optimisation
**Manuscript**: "Tuned Thermostats, Rule-Constrained PPO and Receding-Horizon Control for Binary HVAC Scheduling in Saudi Residences: Switching-Cost Savings and a Clairvoyant Optimality Bracket" (JKSU-ES, major revision, round 4)
**Material reviewed**: /home/claude/v4/main.tex (2,653 lines), tables/tab_stats.tex, supplement.tex (control-relevant parts), RESPONSE_LETTER.md, the journal's outstanding comments (2, 3, 6, 8, A), audit_report.md. Results in /home/claude/rbrl_p12/results (gate_p12.log: 188/188 PASS). Code read: mpc_lambda.py, r3_dp.py (lagrangian, replay, clv_fit, dual_max, step_ok, grid_for), final_tables.py (rule_c, equalise, admissible, _select_core), shield.py, bound_at.py, rbrl_ppo.py, rbrl_e2.py (hold checks), headroom.py (constants, cop_series).
**Known open items, not reported as defects**: the MPC-MZ cells and the Zenodo DOI.

---

## Overall Assessment

This revision is much stronger and more honest than the earlier versions I would expect to have seen. The comparison is now built the right way:
- a tuned version of the conventional controller (TUNED) is the reference every other claim is measured against;
- one selection rule (Rule A, on the tuning windows) and one scoring rule (Rule C, equalisation on held-out windows) apply to every arm;
- the MPC ladder separates model, forecast and horizon;
- a clairvoyant schedule and a relaxation bound bracket what any schedule can do;
- the paper states openly that PPO adds nothing inside the rules and that the planner's margin depends on forecast, capacity and step.

I checked the code against the paper on the points my brief named. The descriptions mostly match: the MPC DP and rollout terminal, persistence forecast, the cold rule in `step_ok`, the optimistic-neighbour bound and its proof, Rule C's minimum-J crossing, the D1 shield's force conditions, and PPO's settings. I checked about 120 numbers against the CSVs and almost all are correct.

Five problems remain:
1. A model-free arm breaks the "hard" cold rule on held-out weeks, and the paper does not report it.
2. Two headline interpretive claims are stronger than the evidence:
   - (a) the planner's margin "requires a perfect forecast". This rests on persistence-forecast cells that are comfort-mismatched by 0.07 to 0.09 K at the 0.10 K fallback.
   - (b) "neither lookahead nor learning adds" inside the rules. This rests partly on an argument whose sign is reversed.
3. The E2 experiment cannot discriminate the hypothesis it is used for, and the PPO "converges to hold" claim is generalised beyond the cities where it holds.
4. Decision time is withheld even though it was measured.

None of these needs new research. All are fixable by rewording plus a few numbers already in the results files. One fix is optional but recommended: refitting the persistence cells with the back-off knob.

---

## Comparison Fairness Table

| Baseline | Category | Same info? | Same model & period? | Tuning stated? | Fair? |
|---|---|---|---|---|---|
| THERM (1 K deadband) | conventional | Zone T only | Yes (same RC plant, same 7 held-out weeks) | Fixed by definition; deadband swept (Table 7c) | Yes, used only as the equalised comparator |
| TUNED (2 switch points) | conventional, tuned | Zone T only | Yes | Yes: 0.05 K grid refined to 0.01 K, Rule A; 0.1 K hardware row given | Yes; generous (0.01 K grid), disclosed as an upper estimate |
| Guard hysteresis | rule-based | Zone T only | Yes | Ceiling by Rule A | Yes |
| D1 shield (latch / on PPO) | model-based, one step | Exact model plus current outdoor T and irradiance (shield.py `next_T` uses `t_out[k]`, `irr[k]`) | Yes | σ ∈ {0, 0.05, 0.10} and ceiling by Rule A; σ=0 has the lowest tuning objective in all cities (T_D1_latch_*.csv) | Yes; the sensor needs differ from TUNED's (see m12) |
| MPC 0.25 to 48 h, perfect forecast | MPC / optimisation | Perfect in-horizon weather plus exact model and state (disclosed) | Yes | λ by Rule A (25-point scan plus refinement); back-off knob only as a last resort | Information advantage disclosed. The comfort device is a knife edge (λ/λ* 1.00 to 13.1); see M2 |
| MPC, persistence forecast | MPC / optimisation | Measured current T_out plus yesterday's weather; exact model and state | Yes | As above, but 2 of 3 cities at the 0.10 K fallback | Partially. Comfort-mismatched against TUNED by 0.07 to 0.09 K (M2) |
| MPC in training / guard rules | MPC within RBRL's action set | Perfect forecast | Yes | As above; the rollout base policy is TUNED, which lies outside the rules (m13) | Partially (M3) |
| RBRL (PPO in rules, 5 seeds) | learning | 1 h exact forecast | Yes; trained on tuning windows only (rbrl_ppo.py L269) | No hyperparameter search (disclosed); fixed 2×10⁵ steps; ceiling by Rule A | Stated. Small budget, no learning curves (M4) |
| E2 (PPO with λ term and forecasts) | learning | Perfect +1/+2/+3/+6 h forecasts | Riyadh only, 3 seeds, `fit_status=fixed` | ent 0.01, reward normalisation | Not comfort-matched (disclosed); cannot discriminate its hypothesis (M4) |
| CLV / B* / B_a | oracle | Whole window clairvoyant | Yes; V_N terminal | Per-window λ bisection plus cap knob (m3) | Correctly labelled as oracles |
| Other learners (SAC, DQN), GA/SA, MILP | — | — | — | Not run | The GA/SA argument is acceptable. The argument for omitting other learners is a non sequitur (m11) |

## Control Rigour Summary

| Aspect | Status | Evidence location | Comment |
|---|---|---|---|
| Formulation (states, actions, constraints, objective) | OK, with gaps | Def. 4 eq. (cop) L934–976; Def. 2 L823–827; L1601–1610 | Hard ceiling, cold rule on cooling steps and unrestricted free float are stated consistently and implemented identically (`r3_dp.step_ok` is shared by the DP, CLV, bound and MPC). Remaining issues: H=720 "hours" versus 15-min steps; the "monthly problem" is never solved (m14) |
| Train / evaluation separation | OK | L1586–1599; rbrl_ppo.py L269; final_tables Rule A | 6 tuning and 7 held-out non-overlapping weeks, interleaved in one TMYx year (disclosed). Journal comment 3 is answered |
| Seeds and variability | OK / WEAK | L1333–1345, L2180–2186 | 5 seeds, none discarded. No learning curves; E2 has 3 seeds in one city (M4) |
| Constraint violations reported | WEAK | L1691–1700 | Over-temperature is zero for every fitted arm (verified). Commanded under-temperature by TUNED and TUNED-SB on held-out weeks is not reported (M1) |
| Robustness (model mismatch, forecast error) | WEAK, but disclosed | L1455–1457, L2473–2478 | Persistence is tested. Model mismatch is untested and stated as such. Capacity and step sweeps are a partial substitute |
| Real-time feasibility | MISSING (data exist) | L2331 | Decision time was measured (T18_scalability.csv) but not reported (M5) |
| Peak / cost metric definition | OK | Table 4 L1883–1913; Remark 2 | Cost, energy and on-commands are separated. No peak or demand tariff, and none is claimed |
| Ablation of controller components | OK | L2174–2204; D1 ladder; Table 3 | Rule layer, learner, one-step model, horizon and forecast are each isolated. E2 is weak (M4) |

---

## Findings

### MAJOR

**M1. The "hard" cold rule is violated on held-out weeks by the recommended model-free arm, and this is not reported.**
- *Location*: Section 8 opening, L1693–1700; Table 3 (tab:main); Section 4.3 eq. (cop) L946–948 and L957–959; response letter L229.
- *Quoted text*: "Commanded under-temperature is zero for every receding-horizon arm except the Riyadh 6 h persistence controller … $0.0006\,^\circ$C·h". The formulation calls the cold rule "hard" and says "no cost saving justifies … a cooling step ending below $T_{\min}$".
- *What is wrong*: The paper discloses the one MPC exception, but not the larger exceptions in the arm it recommends commissioning.
- *Evidence* (`deg_h_cmd_under`, held-out):
  - T1v3_heldout.csv: TUNED Jeddah 0.000674 and Taif 0.006576. The Taif value is 10× the disclosed MPC value.
  - T28v3_setback_rule.csv: TUNED-SB Riyadh 0.010242.
  - T1v3_heldout_dt30.csv: TUNED Riyadh 0.009687 and Jeddah 0.002532.
  - T1v3_heldout_cth7200.csv: TUNED Riyadh 0.004693 and Taif 0.001716.
  - T1v3_heldout_dt5.csv: TUNED Taif 0.001063.
  - T31_mz_rules_riyadh_2x2_lij12.5/35.csv: TUNED 0.000157 and 0.000445.
  - Rule A only guarantees zero on the *tuning* windows (final_tables.admissible).
- *Fix*:
  - Report commanded under-temperature per arm (a column or a footnote in Table 3, and a sentence in Section 8).
  - State that the cold rule is hard for the optimisers, D1 and the rule-layer arms, but is met by TUNED only on the tuning windows. TUNED breaches it on held-out weeks by up to 0.0066 °C·h at 15 min and 0.0102 °C·h for TUNED-SB.
  - Mirror this in the price-of-the-guarantee paragraph (L2198–2204): the guards' guarantee is not only about over-temperature. Update letter L229.

**M2. "The margin over the tuned thermostat requires a perfect in-horizon forecast" is overstated. The persistence comparison (F3) is confounded by comfort offset and by the comfort device.**
- *Location*: C4 L194–196; Section 8.3 L2003–2006; abstract L131–132; Conclusions L2544–2546; letter L19, L120, L240; Table 5 F3.
- *Quoted text*: "The margin over the tuned thermostat therefore requires a perfect in-horizon forecast."
- *Evidence* (T21v3_pers_*.csv):
  - MPC-24 persistence is fitted at the 0.10 K fallback in Riyadh and Taif: ΔT̃ = −0.076 and −0.086 K, against TUNED's +0.011 and +0.005 (T1v3_heldout.csv). In Jeddah it is −0.037 against +0.029. These offsets are 0.066 to 0.091 K.
  - By the paper's own caveat (L1835–1837, L2502), "a 0.01 K … is worth about 1.3 points". That makes these offsets larger than every F3 difference (−1.6 to +1.0 points).
  - The fitted multipliers sit far from indifference: λ/λ* = 13.09, 2.33 and 6.22. The paper itself attributes this to the device: "partly at a cooler matched comfort", L2026.
  - The back-off knob that rescued the 1 h and 2 h perfect-forecast cells at 0.03 K was never tried. mpc_lambda.fit_lambda (L416–443) enters `fit_backoff` only when no λ is admissible *even at 0.10 K*. The paper does not disclose this precedence (λ at 0.03 K, then λ at 0.10 K, then back-off). Table 3's † note (L1840–1841) implies back-off is used whenever "the λ device alone cannot reach the matched comfort level".
- *What is wrong*: F3 shows that a persistence MPC *with this comfort device and this selection order* does not resolve a margin. It does not show that the margin *requires* a perfect forecast.
- *Fix*:
  - (a) Reword C4, Section 8.3, the abstract, the conclusions and the letter to: "with a persistence forecast the margin is not resolved; in Riyadh and Taif that arm is matched at the 0.10 K fallback, 0.07–0.09 K cooler than TUNED, so the comparison carries the comfort-offset caveat".
  - (b) State the knob precedence in Section 5.5 and Rule A.
  - (c) Preferably, refit the two fallback persistence cells with back-off at 0.03 K and report them beside F3.

**M3. Inside-the-rules argument: the comfort-offset correction is applied with the wrong sign, and "neither lookahead nor learning adds" is overstated.**
- *Location*: Section 8.3 "Inside the rules" L2072–2082; Remark 5 L1103–1105; Conclusions L2559–2563; letter L241.
- *Quoted text*: "the training-rule runs are 0.04–0.12 K cooler than the guard, which at about 1.3 points per 0.01 K is enough to account for their apparent advantage."
- *What is wrong*:
  - The manuscript's convention (L2502–2503) is that a *warmer* mean is worth more saving. A cooler arm should therefore *understate* its saving, so the offset cannot "account for" an advantage.
  - In the training rules the 24 h planner saves 11.6 / 14.1 / 10.0% at ΔT̃ −0.061 / −0.003 / −0.064 K, against the guard's 5.7 / 7.6 / 11.0% at +0.036 / +0.035 / +0.056 K (T16v3_r23.8-22.4_*.csv, T1v3_heldout.csv). That is +5.9 and +6.5 points in Riyadh and Jeddah, above the 3-point resolution, *despite* being cooler.
  - The in-rules clairvoyant schedule reaches 12.9 / 13.8 / 12.3% (T17v3_ruled_*.csv). Lookahead therefore does find room inside PPO's own (training) rule set at matched comfort. The guard can match comfort only by lowering its ceiling, and PPO without a mean term cannot.
  - The guard-rule comparison (6.7 / 4.4 / 10.5 against 5.7 / 7.6 / 11.0) is the only clean "no resolved margin" result. It also involves a Jeddah cell at the 0.10 K fallback with λ/λ* = 0.60 (T16v3_r23.62-22.4_jeddah.csv), which falls 3.2 points *below* a policy (hold) that is inside its own feasible set. That points to the comfort device, not to an absence of room.
- *Fix*:
  - Delete or correct the sentence at L2073–2076.
  - Restrict "does not beat the guard" to the guard-rule set and flag the Jeddah fallback cell.
  - Replace "neither lookahead nor learning adds to it" (L1104, L2081–2082, L2559–2563, letter L241) with a statement that matches the data. Within the training rules a planner or clairvoyant gains about 6 points over the guard in Riyadh and Jeddah at matched comfort; within the guard's own narrowed rules no resolved gain was found; the one-step shield recovers TUNED's level.

**M4. The PPO "converges to hold" claims are generalised beyond the evidence, and E2 cannot discriminate learning failure from learning success.**
- *Location*: Abstract L137–138; C4 L197–199; Section 5.4 L1340–1353; Section 9.2 L2180–2196; Conclusions L2558–2559; letter L29, L239.
- *Evidence*:
  - (i) Taif: the cost-only seeds do not reproduce hold. Seeds 42 and 45 share cap 23.84 yet score 8.61 and 9.00. Seeds 44, 46 and 43 share cap 23.86 and score 9.62, 10.05 and 11.00, and only seed 43 equals the guard (rbrl_ppo5_v3_taif.csv). Four of five Taif seeds are 1.0 to 2.4 points *worse* than hold.
  - (ii) E2 runs only in Riyadh, with 3 seeds, at λ ≈ λ*. There the in-rules optimum of the λ=0 reward is within 0.4% of hold (E1v3_hold_dp.csv: 0.945278 / 0.941264). The paper itself says the λ term is "flat in comfort" near λ* (L2188). So a learner that *succeeds* would also return hold, and E2 cannot support "the PPO null survives a comfort-aware reward" (L2192–2193).
  - (iii) E2 is not exactly hold. `fs_minus_hold` is +0.163, −0.020 and +0.102 on-commands/day, `min_logit_gap` is down to 7×10⁻⁴, and ΔT̃ spans 0.078–0.126 K across seeds (rbrl_e2_v3_riyadh.csv).
  - (iv) "what the policies lacked is a one-step model of the plant, not anything a longer training run would supply" (L2195–2196) is untested. The budget is fixed at 2×10⁵ steps and no learning curves are shown.
  - (v) "the training reward … is minimised by holding" (L1341–1342) conflicts with E1: hold is 0.4 / 1.4 / 2.3% above the DP optimum, and the code's own criterion `hold_is_optimum` (≤1%) is False for Jeddah and Taif.
- *Fix*:
  - Scope the claim: "in Riyadh and Jeddah the cost-only seeds reproduce hold; in Taif four of five seeds fall 1.0–2.4 points below it; E2 (Riyadh, 3 seeds) stays within 0.16 on-commands/day of hold".
  - Present E2 as consistent with, not evidence for, a learning null, because hold is near-optimal for its reward in Riyadh. Alternatively, run E2 where hold is furthest from the optimum (Taif, 2.3%) or at a λ for which the in-rules optimum departs from hold.
  - Remove the longer-training sentence or add learning curves.
  - Change "is minimised by" to "is nearly minimised (within 0.4–2.3%) by".

**M5. Decision time against the 15-min control interval is not reported, although it was measured.**
- *Location*: Section 9.4 L2331–2333 ("No claim is made about training cost, decision time or embedded deployability").
- *Evidence*: T18_scalability.csv. MPC per-decision time is 2.14 ms at 6 h and 8.13 ms at 24 h; the rule layer takes 0.84 µs; the hardware is a 2-core 2.1 GHz Xeon with 280 MiB peak RSS (T18_environment.json). This is about 10⁵ times below the 900 s interval. The control rubric treats an unreported computation time for an online controller as MAJOR.
- *Fix*: Add one sentence giving the per-decision times, the hardware and the 900 s budget, and give PPO training wall-clock per seed. This also strengthens the paper's practical case.

### MINOR

- **m1. λ* is defined wrongly in the text.** L1435 reads "$\lambda^\ast=\Lambda_iH_p/\mathrm{COP}$". $H_p$ is undefined and reads as the prediction horizon, and the price is missing. The code uses Λ·168 h·p/(1000·COP), the *window* length (mpc_lambda.lam_star L126–129). Replace it with $\lambda^\ast=\Lambda_i\,(168\,\mathrm h)\,p/\mathrm{COP}$, in SAR per K per window.
- **m2. Wrong attribution of comfort setting.** L1437–1438 says "its comfort level is set by the equalisation of Rule C". Comfort is set by Rule A selection on the tuning windows; Rule C only scores. Reword.
- **m3. Undocumented knobs.**
  - The CLV description (L1464–1471) omits the second knob, an occupied-ceiling cap bisection (r3_dp.clv_fit L358–393). Add it.
  - The MPC back-off precedence is also undocumented (see M2).
- **m4. "holds exactly" needs qualifying.** L1792–1793 says "$s_a\le B_a$ then holds exactly". This holds only after each arm is rescored on V_N, which bound_at.py does. Table 3's $s$ values use the simulator terminal. Say "with each arm rescored on $V_N$".
- **m5. Ratios mix scoring rules.** L2554–2556: "69–74% of the best attained schedule … 59–68% of the provable bound" divides TUNED's Rule-C saving (simulator terminal) by the raw V_N figures for CLV and B*. That is the mixing the paper forbids at L1798–1800. Use $B_{\mathrm{TUNED}}$ from T17v3_Ba.csv, or label the ratio as approximate.
- **m6. The 5-min MPC comparison needs caveats.** L2279–2280 ("matches the Riyadh 24 h controller (a difference not resolved)"): the 5-min MPC uses 801 nodes, which the code's own note calls unconverged (0.25–0.60 pt, mpc_lambda L132–133). It sits at ΔT̃ −0.078 against TUNED's +0.032. Add both caveats.
- **m7. Fallback marks missing from the horizon list.** L2009–2013 omits the fallback marks. Taif 48 h "19" is fitted at 0.10 K with ΔT̃ +0.089 (T21v3_taif.csv) and exceeds the clairvoyant lower end (16.7%). Mark it.
- **m8.** The wording "is minimised by holding" at L1341 is covered under M4(v).
- **m9. The safety guarantee is conditional on the nominal plant.**
  - L1306–1308 and L2202–2204 say R1/R2 enforce O1 "by construction". This holds only for the nominal $C_{th}$ and $Q_{hvac}$: $\epsilon_{cold}=0.40\ge Q\Delta t/C=0.375$ K only at 4,800 kJ/K, and the cooling excursion is 0.75 K at 2,400 kJ/K.
  - $\epsilon_{hot}$ is derived from the TMYx peak load.
  - Qualify the claim "under the nominal plant parameters".
- **m10. Response letter disagrees with the manuscript.** Letter L68 gives the margin as "15.0, 5.7, 3.8 and 0.4"; the manuscript (L2035, abstract) gives "15.0, 5.8, 3.8 and 0.4". Harmonise.
- **m11. Non sequitur for omitting other learners.** L1493–1496: the ruled bound "caps every policy any such learner could represent". The cap (14.9 / 15.6 / 16.2%) is about 9 points above PPO's 5.7 / 7.6%, so it does not answer whether another learner would do better. Reword: the cap bounds the attainable gain; other learners are untested.
- **m12. Deployability.** State D1's sensor needs (exact model plus current outdoor temperature and irradiance) beside TUNED's (zone temperature only). Add one sentence on measurement noise: switch points fitted at 0.01 K and guard bands of 0.2 to 0.4 K are sensitive to typical ±0.2–0.5 K thermistor error.
- **m13. Rollout base policy outside the rules.** The in-rules MPC's terminal rollout and fallback use TUNED, whose off point (22.36 °C) lies below R2. This affects the rollout (mpc_lambda L195, L255); the fallback is rule-corrected (L303–304). The tail is therefore priced under a policy outside the rule set. Disclose it, or roll out the guard.
- **m14. Formulation notation.**
  - Def. 3 L928–930 gives "H=720 hours for a 30-day month", but the step is 15 min (2,880 steps).
  - L905 says "the monthly billing problem (cop) is optimised and repeated indefinitely", but no controller or oracle solves a monthly problem; all are evaluated on 168 h windows.
  - Align the notation and the description.
- **m15. Corollary exposition is internally inconsistent.** Within the corollary's constant-rate abstraction, Step 2 makes energy policy-independent at every mean. Yet L1110–1117 argues that "the corollary is false without [comfort matching] … switching off early raises the mean temperature, which reduces energy", which holds only under the exact T-dependent dynamics. Clarify which model each statement uses.

---

## Numbers verified against the CSVs (all match unless noted)

- **Table 3, TUNED / guard / RBRL / D1 / D1-on-PPO.** All $s$, ΔT̃ and on-command values in all cities (T1v3_heldout, rbrl_ppo5_v3_*, T_D1_*).
- **Table 3, every MPC row** (perfect, persistence, training rules, guard rules), including the † cells and back-off values 0.21 / 0.205 / 0.25 / 0.345 / 0.345 (T21v3_*, T21v3_pers_*, T16v3_*).
- **Fitted multipliers.** λ/λ* for the 6 and 24 h perfect cells (1.002–1.024), the 48 h cells (1.226 and 4.577), persistence 24 h (13.09, 2.33, 6.22) and in-rules 24 h (2.089 and 1.801).
- **Grid refinement.** 0.10 / 0.45 / 0.29 points (T21v3_conv_*).
- **CLV.** Rule-C savings 18.3 / 18.5 / 16.5 against B_CLV 19.6 / 19.4 / 20.2; tolerance met in 2 / 1 / 0 windows (T13v3_clv_*_summary).
- **Bound.** Relaxed sequences and slack 0.47 / 0.42 / 0.75 (T17v3_*); ruled bound 14.9 / 15.6 / 16.2 and CLV-in-rules 12.9 / 13.8 / 12.3 (T17v3_ruled_*).
- **Table 5.** All HL estimates, intervals and p-values (gate P12).
- **Table 8 and timestep text.** 5 / 15 / 30 min TUNED; MPC at 5 min (801 nodes) and 30 min; B* 27.3 / 10.9 / 13.9 / 14.7; on-commands at 30 min −2.2 to −2.8%.
- **Capacity sweep.** 2,400 / 7,200 / 9,600 kJ/K and the stated ΔT̃.
- **Setback arms.** TUNED-SB, MPC-SB, MANUAL.
- **Multi-zone rule arms.** All seven layouts.
- **E1.** Ratios 0.4 / 1.4 / 2.3%.
- **E2.** λ = 0.2416 = 1.004 λ* (in-rules 6 h).
- **No-rules ablation.** −3.5%.
- **Free-float figures.** 0.96, 0.29 and 0.34 °C·h.

Only discrepancy found: letter "5.7" against manuscript "5.8" (m10).

## Response letter

- **Comments 2, 3, 6 and 8**: fully and truthfully answered. Each answer matches what the manuscript and code now do. The PPO split is confirmed in the code. Every MPC and TUNED cell is computed at the tariff in force. The step sweep is real and refitted.
- **Comment A**: addressed.
- **Editor's instruction**:
  - Mostly met.
  - Overstated conclusions remain, for M2, M3 and M4. The letter repeats them verbatim (L19, L29, L120, L239–241).
  - The disclosure list (L229) mentions the MPC cold-rule exception but not TUNED's (M1).

## Paper Quality Standard (items owned by R5)

| ID | Status | Note |
|---|---|---|
| Q2.1 | OK | Design choices justified against named alternatives (masking against shield, DP against MILP, PPO against SAC) |
| Q2.3 | OK / WEAK | ≥5 baselines including tuned conventional, MPC ladder, learner and oracle. Persistence-MPC tuning confounded (M2) |
| Q2.4 | OK / WEAK | Components isolated (rules, learner, one-step model, horizon, forecast). E2 non-discriminating (M4) |
| Q4.2 / Q4.3 | OK | Exact paired Wilcoxon and sign tests, Hodges–Lehmann with exact CIs, Holm correction; n=7 floor stated |
| Q4.4 (computational) | MISSING | M5 |
| Q8.2 | OK / WEAK | Mechanisms explained well (equalisation identity, deadband, step, capacity). In-rules mechanism argued with the wrong sign (M3) |
| Q11.3–Q11.6 | OK | Algorithm 1 matches rbrl_ppo.py (budget, ceiling grid, three phases, termination by fixed budget). MPC/DP description matches mpc_lambda.py except λ* (m1) and the knob precedence (M2, m3) |

## Verdict for the control and optimisation dimension

**READY AFTER MINOR FIXES**, conditional on the five MAJOR items being handled by rewording and by reporting numbers already in the results files. Optionally, refit the two fallback persistence cells with the back-off knob. No new experiment is strictly required.

**Findings: CRITICAL 0 · MAJOR 5 · MINOR 14** (m8 is folded into M4, so 14 distinct minor items).
