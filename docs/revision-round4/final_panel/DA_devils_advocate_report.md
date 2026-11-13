# Devil's Advocate Review: final verification panel, round 4

Reviewer: DA_devils_advocate. Scope: overstated conclusions, rival explanations, cherry-picking, causal overreach, the "so what?" test, and a line-by-line check of the title, abstract, contributions and conclusions against the evidence. I also checked whether the response letter describes the manuscript truthfully.

Files read: main.tex (in full for sections 1, 2, 3.3, 5, 7 to 11), RESPONSE_LETTER.md, the journal's outstanding-comments docx, and tables/tab_stats.tex.

Numbers checked against /home/claude/rbrl_p12/results:
- T1v3_heldout{,_dt5,_dt30,_cth2400,_cth7200,_cth9600}.csv
- T20v3_paired_stats.csv
- T21v3_riyadh.csv and T21v3_pers_{riyadh,jeddah,taif}.csv
- rbrl_e2_v3_riyadh.csv and rbrl_ppo5_v3_riyadh.csv
- T2v3_timestep.csv
- T1v2_heldout_pol24.csv and T1v2_perwindow_pol24.csv
- T26v3_guard_fit.csv
- gate_p12.log (GATE PASSED, 188 invariants)

Every headline number in the abstract that I checked matches the CSVs: 22.8/24.2/21.7 on-commands; 12.5/13.6/12.4; −2.8/15.8; 25.0/24.8/25.7; −1.2/−1.5/−1.2; the margin 15.0 → 0.4; F1 to F4 Hodges–Lehmann estimates and intervals; SAR 4–19/5–19/2–10; the setpoint run's 7.1/9.4/14.5%. The problems are in interpretation, not arithmetic.

---

## Strongest counter-argument

The paper's main positive finding is that a tuned two-parameter thermostat avoids 22–24% of on-commands. A sceptic would say that this is the textbook fact that a wider hysteresis cycles less, and that it depends entirely on the comparator chosen.

The fitted TUNED switch points in the results files are simply THERM with a wider deadband:

| Setting | Fitted deadband (°C) | Cost saving |
|---|---|---|
| 15 min | 1.35, 1.36, 1.32 (23.71/22.36, 23.70/22.34, 23.64/22.32) | 12.5, 13.6, 12.4% |
| 5 min | 1.78, 1.78, 1.79 | about 25% |
| 30 min | 0.98, 0.94, 0.99, i.e. THERM's own 1.0 | −1.2 to −1.5% |
| 2,400 kJ/K | 0.96 | −2.8% |
| 9,600 kJ/K | 1.66–1.74 | 15.8% |

The widest admissible width is set by the paper's own actuation condition, eq. (forcing/deadband condition) at main.tex l. 508–509: band minus per-step excursion Q·Δt/C.

The one-line prediction "on-commands avoided ≈ 1 − δ_THERM/δ_TUNED" reproduces the reported on-commands avoided in all 18 city × configuration cells (15/5/30 min; 2,400/7,200/9,600 kJ/K) to within 2.1 points on average and 4.1 points at worst. Examples: 15 min Riyadh 25.9 vs 22.8 reported; 5 min 43.8 vs 43.1; 30 min −2.0 vs −2.4; 9,600 kJ/K 42.5 vs 39.8.

So the large "capacity and actuation-step dependence" that the abstract presents as a strong sensitivity is fully explained by one mechanism. Commissioning means widening the deadband to what the band and the per-step overshoot allow, and the gain depends on the comparator having a fixed 1.0 °C deadband.

That deadband is called "representative hardware" for the stock (l. 1398–1399), yet the paper also says it is unmeasured (l. 2267–2268). Against a 1.25 °C comparator, TUNED saves only 5.7% (Table sensitivity c). Priced at the supported 0.025 SAR per start, the money is 2–5 SAR per room per season.

On this reading, what survives is methodological, and it is worth publishing:
1. Learned and planned controllers must be judged against a commissioned (widened-deadband) rule.
2. PPO inside the rules has nothing to learn under its own reward.
3. Perfect-forecast lookahead adds 4–6 points, and only on parts of the parameter space.
4. A provable bracket shows how much headroom remains.

The abstract, contributions and conclusions should be rewritten around that message. At present they describe the TUNED result and its sensitivities without naming the mechanism.

---

## Issue list

### MAJOR

**M1. The mechanism of the TUNED saving is not stated, and the step and capacity dependence is presented as an unexplained sensitivity.**
- Location: Abstract l. 124–137; C4 l. 191–196; §8.2 "The tuned thermostat" l. 1934–1949; §9.3 l. 2274–2287; Conclusions l. 2536–2552.
- Quoted text: "Commissioning the two switch points avoids 22.8, 24.2 and 21.7% …"; "Both depend strongly on capacity and actuation step".
- What is wrong: the only explanation given is l. 2284–2285 ("A finer step lets fitted thresholds place each switch more precisely while THERM keeps its 1 °C deadband"). That buries a mechanism which predicts every TUNED cell from the fitted deadband alone. Readers will take the 22–24% as a property of "tuning". It is a property of the δ_THERM/δ_TUNED ratio, and that ratio is set by Q·Δt/C.
- Evidence: fitted on/off points in T1v3_heldout*.csv (table above); the 1 − 1/δ prediction against start_sav_eq agrees within 2.1 points mean and 4.1 points maximum over 18 cells.
- Fix:
  - In the abstract and §8.2, describe TUNED as THERM with its deadband widened from 1.0 to 1.32–1.36 °C, the widest the band and the 15-min excursion admit.
  - Say that the on-commands avoided follow about 1 − δ_THERM/δ_TUNED.
  - Explain the 5/30-min and capacity rows by the same rule: the admissible width is 1.78 °C at 5 min and about 1.0 °C at 30 min or 2,400 kJ/K.
  - Add the fitted widths to Table timestep.

**M2. The comparator deadband, the single largest driver, is asserted to be representative without evidence, and the abstract omits it.**
- Location: l. 1398–1400; l. 2264–2268; Abstract.
- Quoted text: "a 1 °C deadband … which is simultaneously the definition above and a representative hardware deadband for the split units in this stock"; "The adopted δ_db=1 °C sits near the upper end of the admissible interval [0.375,1.25] °C, the direction that favours the baseline".
- What is wrong:
  - l. 2267 says "The deadband of the installed stock is not measured". The two statements contradict each other, and no citation supports "representative".
  - "Favours the baseline" is judged against a cap the paper itself calls an artefact of sampling the comparator at 15 min (l. 2265–2267). A continuously sampling thermostat is not capped there, so a real thermostat could be wider still and TUNED's advantage would shrink.
  - The deadband moves the saving by 35 points (l. 2398), more than anything else, yet the abstract does not mention it.
- Evidence: Table sensitivity (c): 40.2 / 23.4 / 12.5 / 5.7% at δ = 0.5 / 0.75 / 1.0 / 1.25.
- Fix:
  - Delete "representative hardware deadband for the split units in this stock", or cite a measurement.
  - Delete "the direction that favours the baseline", or qualify it as "within the interval admissible at a 15-min sampling step".
  - Add to the abstract: "against a thermostat with a 1 °C deadband (5.7% against 1.25 °C)".

**M3. "Compressor on-commands", "per start" and "wear" contradict the manuscript's own limitation, and the response letter misstates this.**
- Location: Abstract l. 125, 127, 142; §8.2 l. 1916; Conclusions l. 2536–2538 and 2568; C6 l. 203–206; Response letter l. 244 and l. 27.
- Quoted text: abstract "avoids 22–24% of compressor on-commands … per start that wear supports … The benefit is reduced cycling and wear". Letter l. 244: "The model counts supervisory on-commands, and the manuscript no longer equates them with compressor starts."
- What is wrong:
  - §3.3 (l. 646–648) and Limitations (l. 2454–2457) say that whether an on-command is a compressor start "is not established" and that the on-command rate "is an artefact of that interface, not a field prediction".
  - The abstract, results and conclusions still say "compressor on-commands" and price them "per start". So the letter's statement at l. 244 is untrue as the manuscript stands.
  - "Benefit is … wear" is causal: wear is neither modelled nor measured.
  - C6's "showing that … the benefit is avoided cycling and wear, not a lower electricity bill" presents a modelling identity as a finding. With constant COP and zero start energy, energy at matched mean is equal by construction (Remark energy identity; l. 1921–1924, "identity holds to within 3×10⁻⁵").
- Fix:
  - Delete "compressor" at l. 125, 1916 and 2536.
  - Write "per on-command (standing for a start)".
  - Change the closing abstract sentence to: "The cost difference is a charge on avoided on-commands, assumed to stand for wear; electricity is unchanged by construction at matched comfort."
  - In C6, change "showing" to "reporting", and state the identity.
  - Correct letter l. 27 and l. 244.

**M4. Recommendation (i), "none requiring new hardware", and the "so what?" test.**
- Location: Conclusions l. 2581–2584; §3.3 l. 640–642.
- Quoted text: "three recommendations follow, none requiring new hardware. (i) Commission the thermostat … on hardware that can resolve the thresholds".
- What is wrong:
  - The evidence is for a supervisory 15-min on/off layer, "as a smart plug or an infrared command … would" (l. 641). That is added hardware, not the unit's own thermostat.
  - The thresholds are fitted to 0.01 °C. At the 0.1 °C resolution of real hardware the saving falls to 5.7–8.4% (l. 1941–1946).
  - "On hardware that can resolve the thresholds" and "none requiring new hardware" contradict each other.
  - The benefit is 2–19 SAR per room per season at the supported charges, and about 1–9 SAR at 0.1 °C resolution by proportion. No cost of commissioning or of a smart plug is set against it, so the recommendation to act has no economic basis.
- Fix:
  - Drop "none requiring new hardware".
  - Restate (i) as a benchmarking recommendation for researchers: "judge any learner or planner against a thermostat whose deadband has been widened to the band, not against the factory deadband".
  - Either add one sentence comparing the per-season value with a commissioning or smart-plug cost, or state explicitly that no deployment benefit is claimed.

**M5. "Requires a perfect in-horizon forecast and a light plant" is overgeneralised and confounded.**
- Location: C4 l. 194–196; §8.3 l. 2006; Response letter l. 120 and 240.
- Quoted text: "The margin over the tuned thermostat therefore requires a perfect in-horizon forecast."
- What is wrong, first: only one imperfect forecast was tested, and it is the weakest one (persistence). Showing that persistence fails does not show that a perfect forecast is required; an NWP-grade forecast is untested.
- What is wrong, second: the F3 arm is confounded by comfort.
  - The 24 h persistence controllers in Riyadh and Taif are fitted at the 0.10 K fallback, at ΔT̃ = −0.076 and −0.086 K (T21v3_pers_riyadh.csv, T21v3_pers_taif.csv), with λ/λ* = 13.1 and 6.2.
  - By the paper's own figure of about 1.3 points per 0.01 K, that offset is of the order of the margin being tested.
  - The best persistence arm, at 6 h, saves 14.4 and 14.0% at ΔT̃ ≈ 0 (T21v3_pers_*.csv). That is +1.9 and +1.6 points over TUNED: not resolved, but on the positive side.
- What is wrong, third: "a light plant" contradicts l. 483, which calls the 4,800 kJ/K reference a "heavy-construction room". At 7,200 kJ/K the margin is still 3.8 points, which is resolved by the 3-point rule.
- Fix:
  - Write: "with a persistence forecast its margin is not resolved; forecasts between persistence and perfect were not tested, and the 24 h persistence arms are fitted at the 0.10 K fallback and sit 0.04–0.09 K cooler".
  - Replace "light plant" with "at capacities up to about 7,200 kJ/K".
  - Update the letter to match.

**M6. The PPO null is overgeneralised, and the causal explanation is not supported.**
- Location: Abstract l. 137–138; C4 l. 197–199; §5.4 l. 1340–1353; §9.2 l. 2186–2196; Conclusions l. 2558.
- Quoted text: "Rule-constrained PPO converges to the rules' hold policy, even with a comfort term and a forecast"; "what the policies lacked is a one-step model of the plant, not anything a longer training run would supply".
- What is wrong, first: E2 is Riyadh only, with 3 seeds (l. 1350; rbrl_e2_v3_riyadh.csv has 3 rows). The abstract and conclusions generalise it to all three cities.
- What is wrong, second: the paper itself explains why E2 could not tell anything apart. Its λ is taken near λ*, where "the λ term is flat in comfort" (l. 2188–2189). The cost-only reward is "minimised by holding the previous action until a rule fires" (l. 1340–1342), and Corollary C2 predicts hold. So convergence to hold shows that PPO found the optimum of the objective it was given. It is not evidence about learning.
- What is wrong, third: no longer-training experiment was run, so "not anything a longer training run would supply" is untested.
- What is wrong, fourth: "D1 on PPO" replaces the rule layer with the shield (l. 1422). Its 12.8–14.1% therefore measures D1, not the policies, which, being hold policies, reduce to the D1 latch.
- Fix:
  - Write: "PPO inside the rules learns the hold policy that its reward makes optimal (Corollary 1); a comfort-weighted variant tested in Riyadh with three seeds, at a multiplier where that term is nearly flat, does the same."
  - Delete the "longer training run" clause.
  - Describe D1-on-PPO as showing that the shield, not the policy, sets the level.

**M7. The state-of-the-art comparison misreads the direction of one difference and sets unlike quantities side by side.**
- Location: Table sota l. 2152; text l. 2163–2169.
- Quoted text: "The figures here differ in three ways that each lower them: … the saving is priced on on-commands at a charge that the wear derivation places at or below the reference."
- What is wrong:
  - The figures are computed at the 0.15 SAR reference, which is above the derived range. The paper itself says 0.15 "overstates the saving" (l. 1678–1679). So the third difference raises the figures; it does not lower them.
  - The table puts this work's wear-charge saving, with about 0 change in electricity, in one "Saving" column beside published energy or cost savings, which invites a like-for-like reading.
- Fix:
  - Correct the sentence: two of the differences lower the figures and the third raises them.
  - Add "energy ≈ 0%; 3.8–11.0% at the derived charge" to the "This work" row, or a Basis note "priced on-commands at 0.15 SAR; electricity unchanged".

**M8. "The setpoint is what reduces electricity" rests on an out-of-protocol run that breaches comfort.**
- Location: Abstract l. 142–143; §10.3 l. 2414–2420; Conclusions l. 2568–2570; Letter l. 242.
- Quoted text: "the setpoint is what reduces electricity"; "In a separate run under the round-3 protocol … moving THERM from a 23 to a 24 °C centre cuts its cost by 7.1, 9.4 and 14.5%".
- Checked: the cost figures reproduce from T1v2_perwindow_pol24.csv: 7.07, 9.38 and 14.45%.
- What is wrong:
  - A 24 °C-centred thermostat switches on at 24.5 °C, above T_max = 24 °C. THERM's occupied mean in that run is 23.77–23.92 °C (T_therm0), and the TUNED row in T1v2_heldout_pol24.csv records 1.475 occupied degree-hours over the band. So the "lever" is infeasible under the paper's hard comfort constraint.
  - It comes from a superseded protocol.
  - It is close to a restatement of the energy identity (Remark 2).
  - "More than any scheduler here achieves at a fixed comfort level" compares a comfort change with comfort-matched arms, which by construction save about 0 electricity.
- Fix: remove the clause from the abstract. In §10.3 and the conclusions, either rerun under the v3 protocol with the band shifted to [23, 25] °C and say so, or state that the run breaches the [22, 24] °C band and is outside the protocol.

### MINOR

**m1. The comfort-offset argument runs in the wrong direction (l. 2072–2075).** The text says the training-rule runs "are 0.04–0.12 K cooler than the guard, which at about 1.3 points per 0.01 K is enough to account for their apparent advantage". A cooler mean would lower an arm's saving along the guard family, not raise it. The advantage comes from the 0.14–0.20 K higher on-threshold, i.e. a wider band (the M1 mechanism). Fix: attribute the advantage to the wider on-threshold. Also note that the "1.3 points per 0.01 K" slope is itself the deadband-width effect, because a warmer guard has a wider deadband.

**m2. Planner margin at the reference capacity: 5.8 vs 5.7.** The manuscript gives 5.8 (l. 2035); the response letter (l. 68) and tab_stats (pooled Δs +5.7) give 5.7. The CSV gives 18.2638 − 12.5260 = 5.74. Fix: use 5.7 in l. 2035.

**m3. Abstract percentages at the overstating reference are not flagged.** The bracket (18.0–20.0% etc.), the capacity figures (−2.8/15.8) and the step figures (25%, −1.2%) are all at c_sw = 0.15 SAR, but only the SAR figure is labelled. At the derived charges the Riyadh bound is ≤6.3 to ≤17.5% (Table sensitivity b). Fix: add "(percentages at the 0.15 SAR reference)" once in the abstract.

**m4. Conclusions l. 2554–2556 divide unlike quantities.** "69–74% of the best attained schedule" divides TUNED's Rule-C saving by CLV's raw saving, which has a different denominator. l. 1799–1800 forbids pairing CLV's figures across denominators. Fix: use CLV's equalised saving (18.3/18.5/16.5), which gives 68–75%, or state the mixed basis.

**m5. Taif claims pick the favourable end.**
- l. 1951–1953 ("does not leave less to win … the bound is 21.0%, the highest") cites the loosest bound (bracket 4.3 points wide). Taif's attained CLV, 16.7%, is the lowest of the three cities.
- l. 2354–2357 ("which a fixed pair cannot follow and a planner can") holds only with a perfect forecast: the persistence 24 h controller gives 10.8%, below TUNED's 12.4%. The week-to-week mechanism is asserted, not shown.
- Fix: cite both ends of the bracket, and qualify "a planner can" with "given a perfect forecast".

**m6. The wear derivation omits its days per year (l. 1672–1679).** 0.114 SAR implies about 4.0 on-commands per day over 365 days (2,500/(15 × 365 × 4.0)). The SAR-per-season layer and the cooling-only model use a 184-day season. On that basis straight-line depreciation is 2,500/(15 × 184 × 4.10) ≈ 0.22 SAR, so "0.15 exceeds the unit's straight-line depreciation" (l. 1678, 1928) depends on an unstated assumption. Both endpoints are averages, not marginal wear costs. Fix: state the operating days assumed and that the range is a convention.

**m7. The headline step choice is a degree of freedom that changes the ordering, not only the size.** At 5 min TUNED matches the 24 h planner (not resolved, Riyadh). At 30 min TUNED is below THERM. The abstract gives the TUNED numbers but not that the planner's margin vanishes at 5 min. Fix: add "at 5 min its margin over the planner is not resolved". Justify 15 min by an external fact, such as smart-plug or IR command practice or anti-short-cycle timers, not only by the actuation condition, which 5 min also satisfies.

**m8. The price of the guarantee is dropped from the conclusions.** Gap item (i) (l. 325–326) promises "hard comfort enforcement … with the price of that guarantee measured". The arm the conclusions recommend, TUNED, has no guarantee (l. 2202–2204), and the guard that provides it costs 6.0–6.8 points, about half of TUNED's saving (F4). The conclusions say neither. Fix: add one sentence to the conclusions.

### OBSERVATION
- The title is accurate and claims no winner. It still gives billing to PPO, which is a null, but the subtitle is honest.
- C2 and the bound proof are scoped correctly. The bracket is a sound, reusable contribution and could lead the contributions list.
- The 1.0 °C comparator deadband is the most valuable field measurement (l. 2268). I agree, and it deserves a place in the abstract.

---

## Response letter assessment

The letter is unusually candid and is truthful on Comments 1, 3, 6, 7 and 9. It does not adopt the editor's wording on Comment 2, but it justifies why; the old sweep is withdrawn and the new one is reported. On Comment 8 it reports the time-step sensitivity in full, including the reversal at 30 min.

Inaccurate or overstated items:
- l. 244: "no longer equates them with compressor starts". Untrue while "compressor on-commands" remains in the abstract, §8.2 and the conclusions (M3).
- l. 120 and 240: the "requires a perfect in-horizon forecast" key sentence is overstated (M5).
- l. 68: margin 5.7 vs 5.8 in the manuscript (m2).
- l. 242: the setpoint "lever" is reported without noting that it breaches the band (M8).
- l. 243: says recommendation (i) is qualified for hardware, but leaves "none requiring new hardware" in place (M4).

Comment A (moderate categorical statements) is not fully met. Remaining categorical lines: l. 142–143, l. 2006, l. 2080–2082 ("not lookahead and not learning"), l. 2195–2196, and l. 2402 ("Only the controller class is algorithmic").

---

## Verdict (Devil's Advocate dimension)

**NOT READY.** No finding collapses the paper, and every number checked agrees with the CSVs.

Eight MAJOR items remain where the abstract, contributions or conclusions overstate or misframe the evidence: the mechanism and comparator for TUNED, "compressor"/"wear", the recommendation, "requires a perfect forecast", the PPO generalisation, the SOTA direction and the setpoint claim. The editor explicitly asked for exactly this kind of statement to be rewritten.

All of them except M8 are text-level fixes. M8 can be fixed by deleting the claim.

Findings: CRITICAL 0, MAJOR 8, MINOR 8 (plus 3 observations).
