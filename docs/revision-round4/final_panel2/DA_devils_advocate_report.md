# Devil's Advocate Review: final panel 2 (JKSU-ES round 4)

Reviewer ID: DA_devils_advocate. Scope: remaining overstatements, rival explanations, cherry-picking (including the Fig. 3 day selection and the Fig. 4 bars), causal overreach, the "so what?" test, the title, abstract, keywords, contributions, the Vision 2030 / Green Riyadh paragraph and the conclusions, plus the response letter.

Files read: main.tex (in full for §1, §2.4, §5.3–5.5, §7–§11; formulation skimmed), fig_traces.tex, fig_ladder.tex, fig_timestep.tex, RESPONSE_LETTER.md, the journal's outstanding comments (docx), PROVENANCE.md (Green Riyadh rows). Panel-1 reports were read only after the findings below were written.

CSVs checked (under /home/claude/rbrl_p12/results):
- T34_greenriyadh_sens.csv: every column of all four rows.
- T35_day_traces.csv: header, plus the window and week on-command counts.
- T1v3_perwindow.csv: Riyadh TUNED s_w for each window.
- T21v3_riyadh_perwindow.csv: 24 h perfect-forecast s_w for each window.
- T17v3_Ba.csv: TUNED s_a and B_a.
- T1v3_heldout.csv, plus its _cth2400/_cth7200/_cth9600/_dt5/_dt30 variants: TUNED and guard s, ΔT̃, start and energy savings.
- riyadh.epw: weekly mean dry-bulb for all 13 windows.

Every number I checked agrees with the manuscript, to within rounding.

---

## Strengths (for fairness)

The manuscript is now unusually candid. The abstract states that the saving is a charge on avoided on-commands and not a bill saving, that MPC's margin needs a perfect forecast, that PPO adds nothing to the hold policy, and that capacity and step change the ordering. The clairvoyant bracket with a provable relaxation bound is a sound and reusable contribution. Most of the previous panel's overstatements are gone (see Panel-1 closure).

## Strongest counter-argument

At matched comfort, the model cannot let any switching policy change electricity. The COP is constant, the price is flat, there is no start-up energy and there are no internal gains (Remark `energy_identity`). The only thing a controller can change is the number of supervisory on-commands. The paper itself says these are "not established as compressor starts" and that "the model's on-command rate is an artefact of that interface, not a field prediction" (l. 2492–2495). It then prices them at a charge it calls "a convention, not a measured wear cost" (l. 1613–1614).

The headline 12.4–13.6% therefore prices an interface artefact at a conventional rate, and every bias the paper lists points upward:
- the charge above the derived range;
- 0.01 °C thresholds (5.7–8.4% on a 0.1 °C grid);
- noise-free sensing;
- an assumed 1 °C comparator deadband (5.7% against 1.25 °C);
- a reference capacity that "probably favours the tuned thermostat";
- the narrow [22, 24] °C band (l. 1489–1490).

These are never combined. A rough composite, a 0.1 °C grid at 0.025–0.114 SAR, is about 2–5% in Riyadh, worth a few SAR per room per season.

The four findings are each predictable without simulation:
- A wider deadband cycles less: on-commands avoided ≈ 1 − δ_THERM/δ_TUNED, as the paper says.
- A perfect-forecast planner beats a myopic rule.
- PPO trained on a reward whose optimum is the hold policy (E1, l. 1273–1277) learns the hold policy.
- At matched comfort electricity is constant, by identity.

What remains new is methodological: the comfort-equalised protocol, the bracket, and the demonstration that the comparator's deadband sets the reported saving. Yet the title advertises "Optimising … with MPC and Rule-Constrained PPO", and the keywords advertise "CO₂ reduction", "Saudi Vision 2030" and "Green Riyadh". The paper's own data show that its controllers change neither electricity nor emissions. Its only CO₂-relevant number, the Green Riyadh one, is a property of the weather and not of any controller.

None of this collapses the paper, which is honest in its body. It does mean that the framing (title, keywords, the national-target paragraph and the abstract's last sentence) now claims more relevance than the evidence carries. These are exactly the kind of statements the editor asked to have rewritten.

---

## Issue list

### CRITICAL
None.

### MAJOR

**M1. Keywords "CO₂ reduction", "Saudi Vision 2030" and "Green Riyadh" are not justified by content. The emissions sentence claims an unmodelled mechanism.**
- Location: keyword block l. 146–149; §10.3 l. 2456–2459; Introduction l. 159.
- Quoted text:
  - "Saudi Vision 2030 \sep Green Riyadh \sep CO$_2$ reduction"
  - "their contribution to emission cuts is indirect, through fewer on-commands"
  - "Better operation of residential air conditioning is therefore one route to the efficiency targets of Saudi Vision 2030".
- What is wrong:
  - CO₂ appears nowhere in the body (grep: only the keyword). No emission factor, emission quantity or CO₂ result exists.
  - The paper's central finding is that the controllers leave electricity unchanged at matched comfort ("within ±1.2% for every arm without setback", l. 1863–1864; Remark energy_identity).
  - In the model an on-command consumes no energy (l. 2536–2537). So "indirect contribution to emission cuts through fewer on-commands" has no mechanism in the paper. The only route the paper mentions is a hypothetical start-up loss of 10–25 Wh, which would give 0.33–0.80% of electricity (l. 2538–2540). That figure is assumed, not modelled.
  - "Green Riyadh" enters through one first-order weather sensitivity that is independent of the controllers (M2).
  - "Saudi Vision 2030" appears in one introductory sentence.
  - The keywords that do describe the findings are absent: tuned thermostat or hysteresis deadband, switching or on-command cost, optimality bound, comfort-equalised baseline.
  - Intro l. 159 opens with "better operation … is one route to the efficiency targets". The paper then finds that better switching yields no efficiency gain. The forward reference to §10.3 does not undo the framing.
- Evidence: grep for CO and emission in main.tex and supplement.tex; Table `tab:layers` energy column; T34_greenriyadh_sens.csv (shows the controllers are irrelevant to the electricity cut).
- Fix:
  - Remove "CO₂ reduction" and "Green Riyadh" from the keywords. Keep "Saudi Vision 2030" only if the journal wants a context keyword.
  - Add "hysteresis thermostat", "switching cost" and "optimality bound" (or "comfort-equalised baseline").
  - Rewrite l. 2457–2459 as: "At matched comfort the controllers studied here change on-commands, not electricity. In this model they therefore make no contribution to emission cuts, beyond an assumed start-up loss of 10–25 Wh per on-command that would be worth 0.3–0.9% of cooling electricity (Section 10.4)."
  - Rewrite l. 159 as: "Residential air conditioning is therefore central to the efficiency targets of Saudi Vision 2030 … Section 10.3 asks how much of that switching control can deliver, against the comfort target and a cooler city."
  - Update the response letter, which does not mention the keyword change at all (see R1).

**M2. The Green Riyadh sensitivity is reported at a looser standard than the paper's own and overstates both of its claims.**
- Location: §10.3 l. 2459–2466; Conclusions l. 2626–2628; Abstract l. 140–142.
- Quoted text:
  - "lowering Riyadh's outdoor temperature by 1.5 and 2 K, the Green Riyadh aim, cuts THERM's cooling electricity on the held-out weeks by 10.5 and 13.7%, while TUNED's raw saving stays at 12.8–13.6%, so a cooler city and better switching add rather than compete".
- What is wrong:
  - (a) "TUNED's raw saving stays" is not comfort-matched, and the comfort offset grows with the shift. In T34_greenriyadh_sens.csv, Tocc_tuned − Tocc_therm is +0.011 K at 0 K, +0.017 at −1 K, +0.030 at −1.5 K and +0.048 K at −2 K.
    - The paper's own rule (l. 2547–2552) says a 0.01 K offset is worth about 1.3 points, and that offsets above about 0.02 K must carry the caveat.
    - At −1.5 and −2 K, roughly 4–6 points of TUNED's "unchanged" raw saving could therefore be warmth.
    - The thresholds are not refitted under Rule A, and the saving is raw (against unshifted THERM), not equalised by Rule C.
    - So "add rather than compete" is not established at the standard every other comparison in the paper must meet.
  - (b) The 10.5–13.7% is an arithmetic identity of the model, not a finding.
    - Λ = 23.75 W/K, so a 2 K shift removes 47.5 W.
    - THERM's mean modelled cooling load on these weeks is 19.60 kWh × 2.985 / 168 h ≈ 348 W.
    - 47.5 / 348 = 13.7%, and 35.6 / 348 = 10.2% at 1.5 K.
    - The percentage is inflated by the omitted internal gains (150–300 W while occupied, "comparable with the modelled envelope load", l. 2541–2542). These are load that does not depend on outdoor temperature. With them included, the same shift would cut roughly 7–11%.
    - A uniform all-hours shift applied to an airport record also overstates a canopy-driven, mostly daytime effect.
  - (c) The cited source (Saudipedia) says "Reducing temperatures by 1.5–2 degrees Celsius in the city", not "air temperature" (l. 159). The −1 K row (−6.2%) was computed but is not reported. That is harmless, but it is a selection.
- Evidence: T34_greenriyadh_sens.csv, columns Tocc_therm, Tocc_tuned, E_therm, dE_therm_pct, s_raw_tuned_pct; Table `tab:params` gives Λ_i = 23.75 W/K.
- Fix:
  - Either refit TUNED by Rule A and score it by Rule C in the shifted weather, or write: "TUNED's raw saving, with the thresholds unchanged, is 12.8–13.6%, but it runs 0.03–0.05 K warmer than THERM there, so whether the two levers add is not resolved."
  - Add: "Because the model has no internal gains, the electricity cut equals Λ·ΔT over the modelled envelope-and-solar load and is an upper estimate."
  - Change "air temperature" at l. 159 to "temperatures in the city", and cite the programme's own document (Royal Commission for Riyadh City) rather than Saudipedia.

**M3. The abstract presents a model identity as an empirical finding and promotes the Green Riyadh aside to its closing sentence.**
- Location: Abstract l. 140–142.
- Quoted text: "Electricity follows the comfort target and the outdoor air (a cooler city, the Green Riyadh aim), not switching control at matched comfort."
- What is wrong:
  - With constant COP, a flat price and zero start-up energy, the model makes electricity at matched mean temperature policy-independent by construction. Remark energy_identity says this is "an identity of the model, not a finding", and the conclusions (l. 2624) say "by an identity of the model".
  - The abstract drops that qualifier, so a reader will take it as a measured result about real split units.
  - Its closing slot also lifts a one-row first-order weather sensitivity (M2) to the level of a headline. This is the abstract's only reach towards the national targets, and it concerns weather, not control. That is the promotional framing Comment A asked to have moderated.
- Fix: "In this model electricity at matched comfort is independent of switching control by construction; it moves with the comfort target and the outdoor air." Drop the parenthetical, or keep "(Green Riyadh)" only if M2's caveats are added in the body.

**M4. "Hard comfort enforcement by construction" is conditional on a nominal capacity that the paper itself judges probably too high, so the "price of the guarantee" buys a guarantee that is probably void at the reference.**
- Location:
  - Gap (i), l. 317–318: "hard comfort enforcement by construction, with the price of that guarantee measured".
  - C1, l. 172–174.
  - §9.2, l. 2199–2209: "What the guards buy is a guarantee under the nominal plant parameters".
  - Conclusions, l. 2620–2621: "The guarantee the guards give costs 6.8 and 6.0 points".
  - Remark rc, l. 472–476.
- What is wrong:
  - ε_cold = 0.40 °C is derived from Q·Δt/C_th = 0.375 °C at 4,800 kJ/K (eq. guard, l. 1210, 1217).
  - Remark rc says the capacity effective at THERM's roughly 6 h cycle is "lower" and that the reference "probably lies above the effective one".
  - At 2,400 kJ/K the cooling excursion is 0.75 °C, almost twice ε_cold. So under the paper's own best judgement of the physics, R2 does not exclude a cooling step below T_min.
  - The guarantee is also void under the sensor errors of "a few tenths of a kelvin" admitted at l. 2511–2513, since ε_hot = 0.20 °C.
  - The "price of the guarantee" (6.8 / 6.0 points) is therefore the price of a nominal-model guarantee. The conclusions state it without that qualifier.
- Fix:
  - In gap (i), C1 and the conclusions, write "hard comfort enforcement under the nominal plant model".
  - Add one sentence to §9.2: "Because ε_cold is derived from the nominal capacity, and the capacity effective over a cycle is probably lower (Remark 1), the guarantee does not survive that uncertainty: at 2,400 kJ/K the per-step cooling excursion (0.75 °C) exceeds ε_cold."
  - If the guard was refitted with re-derived margins in the capacity sweep, say so.

**M5. The abstract's leading figures omit the thermostat-resolution and sensing caveats, which halve them. No compounded "realistic" figure is given, although every listed bias points the same way.**
- Location: Abstract l. 124–128 and 137–138; Conclusions l. 2592–2600.
- Quoted text:
  - "avoids about 22–24% of on-commands … and saves 12.4–13.6% of cost at a reference charge above the range a wear estimate supports, and much less against a wider-deadband comparator"
  - "A clairvoyant schedule and a provable bound place the best attainable saving at about 17–21%".
- What is wrong:
  - The abstract flags the charge and the comparator. It does not flag the 0.01 °C threshold resolution. On the 0.1 °C grid of a real thermostat, the on-commands avoided fall to 10.5–14.7% and the saving to 5.7–8.4% (l. 1893–1896). This is the caveat most relevant to any deployment.
  - The noise-free sensing assumption (l. 2511–2513) concerns the same 0.35 K deadband widening that produces the whole gain. A sensor error of a few tenths of a kelvin is of the same order.
  - "Best attainable … 17–21%" is at the 0.15 SAR reference that the paper says overstates. At the derived charges the Riyadh bound is ≤6.3 to ≤17.5% (Table `tab:sensitivity`(b)).
  - The response letter (l. 214) says "Findings that weaken the paper's own method are stated in the abstract and conclusions". The hardware-resolution finding is in the conclusions only.
- Evidence: T1v3_heldout.csv (fitted on/off points; start_sav_eq 22.8 / 24.2 / 21.7); main text l. 1893–1896; Table `tab:sensitivity`.
- Fix:
  - Add to the abstract: "on the 0.1 °C setpoint grid of a real thermostat it avoids 11–15% of on-commands".
  - Change "place the best attainable saving at about 17–21%" to "… at about 17–21% at the reference charge".
  - Optionally, give in §10.4 one compounded Riyadh figure: TUNED on the 0.1 °C grid at 0.025 and 0.114 SAR.

**M6. The PPO null is fixed by the reward design. The title, C4 and one limitation sentence still frame it as a test of an optimiser.**
- Location: Title l. 104–105; C4 l. 198–199; §5.4 l. 1273–1282; Limitations l. 2564–2568; tex comment l. 88–103.
- Quoted text:
  - Title: "Optimising Binary HVAC Switching … with Model Predictive Control and Rule-Constrained PPO".
  - Limitations: "longer training is not run, but on the tuning weeks the trained policies already sit close to the hold policy's training cost …, so it has little to gain".
- What is wrong:
  - The training reward has no mean-temperature term and is "nearly minimised by holding the previous action until a rule fires" (E1, l. 1273–1277). PPO learning hold is therefore the predicted outcome of the design, not evidence about learning.
  - E2, the only test of that point, is Riyadh-only with three seeds and no Rule A selection, at a multiplier "where the λ term is flat in comfort" (l. 2189–2191).
  - "Little to gain" holds for PPO's own objective. It does not hold for the evaluation metric. Inside the same training rules, the 24 h MPC reaches 11.6 / 14.1 / 10.0% and the ruled bound is ≤14.9 / 15.6 / 16.2%, against PPO's 5.7 / 7.6 / 8.6–11.0% (Table `tab:main`). There is 4–9 points of headroom that no amount of training on this reward can reach. The sentence conflates the two objectives.
  - The title gives billing to the controller that produced a designed null, and omits the tuned thermostat, which carries every practical finding.
  - The source records a pre-registered decision: "condition A fails, so branch T3 applies" (l. 101). T3 is "Tuned Thermostats, Rule-Constrained PPO and Receding-Horizon Control for Binary HVAC Scheduling in Saudi Residences …". The live title is not T3, and "Optimising" is the verb that the excluded "Cost-Optimal" was struck for. The letter (l. 25) argues that "optimising names the task". That is defensible grammatically, but "Optimising X with PPO" reads as a claim about PPO.
- Fix:
  - Use the T3 title, or "Tuned Thermostats, Model Predictive Control and Rule-Constrained PPO for Binary HVAC Switching in Saudi Residential Buildings".
  - In C4 and the abstract, write "PPO, whose cost-only reward inside the rules is minimised by the hold policy, learns that policy in Riyadh and Jeddah and falls below it in Taif".
  - Rewrite the limitation sentence: "longer training is not run; on its own objective the policy is already within 0.05% of the hold policy on the tuning weeks, so longer training could not close the 4–9-point gap to the in-rules MPC and bound, which this reward does not reward".

### MINOR

**m1. Fig. 4 caption repeats a mixed-basis ratio that panel 1 (DA m4) flagged in the conclusions.**
- Location: fig_ladder.tex caption.
- Quoted text: "TUNED attains 70–74% of the saving at the bracket's lower end".
- What is wrong: TUNED's s is Rule-C equalised, but the lower end of the bracket is CLV *raw*, against unshifted THERM. Section 8.1 (l. 1741–1743) forbids this pairing. The actual ratios are 12.53/18.02 = 69.5%, 13.62/18.41 = 74.0% and 12.41/16.69 = 74.3%. The conclusions now use the correct "62–65% of the provable bound" (s_a/B_a from T17v3_Ba.csv: 64.2, 65.2, 62.0%).
- Fix: replace the clause with "TUNED attains 62–65% of the bound at its own mean (B_a)", or use CLV's equalised saving.

**m2. Fig. 4 rung selection omits the D1 shield and the in-rules MPC, the two rungs the text uses to explain the ladder.**
- Location: fig_ladder.tex; §8.3 l. 1952.
- What is wrong:
  - The caption does not state why these five arms were chosen.
  - D1 on the latch (14.0 / 13.5 / 12.4%) exceeds TUNED in Riyadh. It is the rung behind the claim that "an exact one-step model reaches the tuned thermostat".
  - The in-rules 24 h MPC (11.6 / 14.1 / 10.0%) is the rung that shows the headroom PPO leaves inside its own rules (M6).
  - Without them, the figure reads as a monotone ladder from rules to MPC.
- Fix: add the two rungs, or state the selection rule in the caption ("the five arms of the primary families F1–F4").

**m3. Fig. 3 selection is defensible but should disclose what it implies.**
- Location: fig_traces.tex caption.
- Checked: window 233 is the hottest held-out Riyadh week (mean dry-bulb 38.5 °C against 32.6–37.2 °C for the other held-out weeks; riyadh.epw). The rule is a priori, so I see no cherry-picking.
- What it implies:
  - It is TUNED's *worst* held-out week (s_w = 11.1% against a pooled 12.5%; T1v3_perwindow.csv).
  - The MPC margin there (17.4 − 11.1 = 6.3 points; T21v3_riyadh_perwindow.csv) is above the pooled 5.7.
  - The trace shows unshifted THERM, whereas all savings are against shifted THERM.
- Fix: add to the caption "the week in which TUNED's saving is lowest (11.1%) and MPC's margin largest (6.3 points); THERM is shown unshifted".

**m4. Conclusions l. 2608–2610 have an ambiguous antecedent that can reverse the meaning.**
- Quoted text: "while MPC's margin falls from 15.0 to 0.4 points; because the capacity acting over a cycle is probably below the reference, the reference results lean towards the end favourable to it."
- What is wrong: the nearest antecedent of "it" is MPC. The intended referent is the tuned thermostat.
- Fix: "… favourable to the tuned thermostat."

**m5. The keyword "constrained reinforcement learning" contradicts the paper's own description.**
- What is wrong: l. 308–310 say comfort is enforced by "a post-posed shield, rather than through constrained policy optimisation". In common usage, "constrained RL" means CMDP or constrained policy optimisation.
- Fix: "shielded reinforcement learning" or "safe reinforcement learning".

**m6. The abstract's "saves about 25% at 5 min" may be read as a headline figure.**
- Location: l. 135.
- What is wrong: it is at the reference charge, at a 1.78 °C fitted deadband, with ΔT̃ = +0.032 K in Riyadh (above the 0.02 K caveat threshold; T1v3_heldout_dt5.csv). At 5 min its margin over the 24 h MPC is also not resolved (panel 1 m7, still open).
- Fix: "the tuned thermostat's saving roughly doubles at 5 min, where its difference from the 24 h MPC is not resolved, and is slightly negative at 30 min".

**m7. The gap statement says "the gap this paper fills" (l. 317), but item (iii) is met only for single-zone arms.**
- What is wrong: the multi-zone check has no bound, is not tested for significance, and covers one city.
- Fix: "addresses" instead of "fills", or append "for the single-zone case".

**m8. Internal-process comments survive in the LaTeX source.**
- What is there: the title decision tree with "RULING_round4 §6"; "Abstract: <= 250 words once the placeholders are filled"; "Keyword cap to be confirmed"; "Gate (RULING §12.1): J-MZ by Sat 14 Nov 20:00. If missed, replace…"; "fig_tariff is withheld until regenerated"; the unused `\pend` macro "round-3 placeholder" (main.tex l. 71, supplement.tex l. 19).
- No placeholder renders in main.pdf: pdftotext shows no "PENDING", "??" or "TODO".
- Fix: strip these comments before uploading the source.

**m9. The Green Riyadh source is a tertiary encyclopaedia (Saudipedia) used for a quantitative target.**
- What is wrong: the reference report also flags it as NOT_FOUND. It is fine as a pointer but weak for a cited number.
- Fix: cite the Royal Commission for Riyadh City / Green Riyadh programme document. This is folded into M2(c) and counted once.

---

## Ignored alternative explanations

1. **TUNED's gain consumes the comparator's safety margin, not an inefficiency.** THERM's 0.5 °C inset from each band edge can be read as the margin a real installer keeps for sensor error and model uncertainty. TUNED fits its switch points to within 0.29 and 0.36 °C of the edges using noise-free 0.01 °C sensing and the nominal plant. The paper attributes the gain to "a statement about the comparator", which is close to this. It should say plainly that, with realistic sensing, part of the margin TUNED removes would have to be restored.
2. **"In every held-out window" (F1) is mechanical, not evidential.** A wider deadband cycles less in any weather. Seven-of-seven sign agreement and Holm p = 0.047 therefore add no information beyond the mechanism. This is not wrong, but the test should not be read as robustness evidence.
3. **The PPO null is a reward-design outcome (M6),** not a statement about learners inside hard rules.
4. **The Green Riyadh electricity cut is Λ·ΔT over the load (M2),** fixed by the model's having no internal gains.

## Missing stakeholder perspectives
- Occupants and installers: thresholds 0.29–0.36 °C from the band edges, with real sensor error, risk comfort complaints. No sensitivity to sensing noise is run.
- Utility and grid planner: the paper's national-target paragraph addresses emissions, but peak demand (the Saudi grid's binding constraint in summer) is untouched. The study cannot speak to it, because start times are not aggregated.

## Observations (non-defects)
- Every checked number agrees with the CSVs: the Green Riyadh rows, Fig. 3 counts (34 / 27 / 23 per week), Fig. 4 bars, s_a/B_a = 62–65%, the capacity and time-step rows, and the 2027 tariff rows.
- The Vision 2030 / SGI figures (278 Mt, net zero 2060, 7.5 million trees) are quoted from cited sources and not computed. That is fine.
- The bracket and the comfort-equalised protocol are the most durable contribution. A framing that leads with them (title, keywords, C-order) would make the "so what?" answer stronger than the current controller-comparison framing.

---

## Response letter

- **R1 (MINOR, counted with M1).** The letter never mentions the new keywords. L. 38 says "The text keeps the levers apart", yet the keyword line puts "CO₂ reduction" on a paper whose controllers do not move electricity. Disclose the keywords and justify or drop them.
- L. 25 (title): "'optimising' names the task, not a result". See M6. The letter does not mention that the pre-registered neutral branch T3 was set aside.
- L. 214: "Findings that weaken the paper's own method are stated in the abstract and conclusions". This is untrue for the 0.1 °C resolution finding, which is in the conclusions only (M5).
- Comments 2, 3, 6 and 8 are answered truthfully. The dates for Comment 3 match the manuscript (day 121 = 2 May). "Unaffected" and "lower bound" are gone. The tariff in force is used throughout. The time-step response reports the reversal at 30 min.
- Comment A [journal comment A — text withheld]: mostly met. The remaining promotional element is the national-target framing (M1–M3).

---

## Panel-1 closure (DA items only, plus the other panels' CRITICAL/MAJOR items I could verify in the text)

| Panel-1 item | Status |
|---|---|
| DA M1: TUNED mechanism not stated | Closed: l. 1883–1890 and abstract l. 125 |
| DA M2: comparator deadband called "representative" | Closed: "assumed, not measured", l. 1336–1338; abstract "much less against a wider-deadband comparator" |
| DA M3: "compressor"/"per start" | Closed: abstract l. 129–130; Limitations l. 2492 |
| DA M4: "none requiring new hardware" | Closed: recommendation (i) l. 2637–2643 |
| DA M5: "requires a perfect forecast", "light plant" | Closed: l. 1964–1966; "light plant" now refers to 2,400 kJ/K |
| DA M6: PPO null overgeneralised | Mostly closed; residual reframed as M6 above |
| DA M7: SOTA direction | Closed: l. 2133–2136 ("One raises them") |
| DA M8: out-of-protocol setpoint lever | Closed: replaced by a within-ceiling 0.1 K shift on THERM's equalisation curve, l. 2427–2432 |
| DA m3: abstract percentages at the reference charge | Partly: TUNED flagged; bracket not (M5) |
| DA m4: mixed-basis ratio | Closed in the conclusions (62–65%); reappears in the Fig. 4 caption (m1) |
| DA m7: 5-min ordering | Open (m6) |
| DA m8: price of the guarantee | Closed in the conclusions (l. 2620–2621); qualifier needed (M4) |
| R6 CRITICAL: D1 on PPO "lifts them to TUNED's level" | Closed: l. 2041–2045, conclusions l. 2617–2620 |
| R6 MAJOR: two-sided actuation condition / 3.00 in Fig. 1 / commanded under-temperature disclosure | Closed: recommendation (ii) "both sides"; no "3.00" in fig_leap.tex; §8 preamble l. 1638–1642 |
| EIC F1 (dates) / F2 (compressor) | Closed |
| R4 M1/M2/M4: internal gains, outdoor-dependent plant, capacity bias direction | Closed in Limitations and Remark rc |

---

## Verdict (Devil's Advocate dimension)

**NOT READY**, but only by text. No finding needs a rerun, except the optional comfort-matched Green Riyadh refit in M2.

Four of the six MAJOR items concentrate on the new national-target framing: keywords, the emissions sentence, the Green Riyadh paragraph and the abstract's closing sentence. The other two concern the conditional guarantee and the omission of the hardware-resolution caveat from the abstract. With M1–M6 rewritten as proposed (about two hours of editing), this dimension would be READY AFTER MINOR FIXES.

**Findings: CRITICAL 0 · MAJOR 6 · MINOR 9** (plus R1 in the letter, counted with M1).
