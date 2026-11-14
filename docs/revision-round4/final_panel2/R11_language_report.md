# Reviewer R11: Language and Coherence (final panel 2, round 4)

Scope: I read every sentence of `main.tex` (2,718 lines), the four figure-caption files (`fig_leap`, `fig_traces`, `fig_ladder`, `fig_timestep`), `supplement.tex` and `RESPONSE_LETTER.md`. My starting point was the Phase 0 audit (checks B, D and I). The journal's Comment A comes from the attached docx. Unless a location names another file, line numbers refer to `main.tex`. I read the change log `LANGUAGE_PASS_1113.md` and the panel-1 report only after I had finished my own findings. The build is clean: there are no undefined references, and the PDF contains no "??" and no "PENDING".

## 1. Summary

**Readability is good.** The prose is plain and British throughout. US forms appear only in the CRediT role names, which are fixed terms. None of the usual AI vocabulary occurs (Moreover, Furthermore, crucial, robust as praise, comprehensive, notably, delve, novel). Running text has no contractions and no em dashes. Almost all of the audit's I-findings are artefacts of stripping `\cite`, `\ref` and maths ("space before ','", "sentence starts lower-case", "MATH MATH", "on on"); I found no real typos. The audit's D1 MAJOR ("no `\ref` roadmap") is a **false positive**. The roadmap is at lines 210–220, and it uses `\ref{sec:…}` for every section. Section 5 below assesses it.

**The three most important problems:**

1. **A stale passage about the tariff "epochs" (MAJOR, also reported to R6).** Section 10.3, lines 2413–2416 and 2434–2438, still says "the tariff by 7 across the three epochs (Table 7)" and "the same under all three epochs". Table 7(a) now has two rows (0.18 and 0.21 SAR/kWh), which move TUNED from 12.5 to 11.6%, a change of 0.9 points and not 7. The 7 points came from the pre-2018 row: `results/T4v3_bound.csv` and `T4_tariff*.csv` hold price 0.05, 0.18 and 0.21, and that row was removed. Supplement S1 (line 136) has a similar relic: "against tier widths of 2,000 kWh", which is the four-tier tariff the journal objected to in Comment 6.
2. **The response letter describes text that is no longer in the manuscript (MAJOR × 2).**
   - **Comment 6.** The letter quotes Section 3.4 as calling Model S "a historical schedule, no longer the tariff in force … a stress-test instantiation". That sentence is not in `main.tex`. The letter also cites "Table 7(a) (three tariff epochs)" and reports "under all three epochs … 18.6, 12.5 and 11.6%", while two lines earlier it says the pre-2018 schedule "has been removed from the analysis altogether".
   - **Comment A.** The letter claims that:
     - results "are no longer restated with their figures in the theory sections, the Discussion or the Limitations";
     - "the conclusions no longer repeat the abstract's figures";
     - "internal labels and file names were removed from the text";
     - the longer-training claim is "now 'longer training was not tested'".

     None of these is fully true (items RL2–RL5 below).
3. **Residual repetition and some formula-like phrasing (MINOR individually).**
   - The capacity caveat ("the reference results lean towards the end favourable to TUNED") appears in four places.
   - "Charge on avoided on-commands … not a lower electricity bill" appears five times.
   - The Taif sentence "does not leave less to win in percentage terms" is repeated word for word in §8.2 and §10.1.
   - §5.4 and Remark 5, which are method and theory sections, report results.
   - The list of exclusions (time-of-use tariff, minimum on/off time, temperature-dependent COP) is given in §3.4, §10.3 and §10.4.
   - Families F1–F4 are cited in the results, but the protocol (§7) never assigns those labels.
   - The roadmap is eight identical "Section X verbs …" sentences.

**Effort:** about 1–2 hours of editing. No new analysis is needed.

## 2. Section linkage table

| Section / subsection | Opens by linking to | Closes by leading to | Status | Suggested bridge sentence |
|---|---|---|---|---|
| 1 Introduction | Context; last sentence of ¶1 points to §10.3 | Roadmap (210–220) | OK | Merge the roadmap into 3 sentences (L5) |
| 1.1 Motivation | Thermostat → MPC/RL → closest prior work | Points to §2.4 | OK | — |
| 1.2 Contributions | "Six contributions are made." | Roadmap | OK | C3 uses E2/MANUAL before they are defined (L4) |
| 2 Literature Review | One-sentence plan (225–227) ✓ | §2.4 → §3 "Closing those gaps" ✓ | OK | — |
| 2.4 Research Gap | Table 1 | Three-point gap | WEAK | "Neither study addresses three points" has no clear antecedent (L10) |
| 3 Problem Formulation | "Closing those gaps…" ✓ | 754 "the following section formalises…" ✓ | OK | Title overlaps §4's "Constrained Formulation"; the roadmap calls it "the thermal and cost models". Rename to "Thermal and Cost Models" (L11) |
| 3.2 Zone Configurations | Points to §8.4 | — | OK | — |
| 4 Optimal Schedule | Subsection plan (759–763) ✓ | 1077–1080 → §5 opens on O1–O3 ✓ | OK | Observation 2 is still cited (Remark 4, l.960) before it is stated (l.970) |
| 5 Controllers | Links to O1–O3 ✓ | 1438 "applied to the three climates characterised next" ✓ | OK | — |
| 5.4 Reward/PPO | — | Algorithm 1 | WEAK | ¶ 1273–1290 reports results (seed behaviour, generalisation shortfall); cut to a forward reference (D4) |
| 6 Case Studies | Purpose sentence ✓ | No closing bridge (§7 opens by linking back) | OK | — |
| 7 Simulation Setup | Links back to §5 and §6 ✓ | Ends on the switching-charge caveat | OK | Assign the labels F1–F4 here (L20) |
| 8 Results | Settings, then comfort records; plan in the last sentence ✓ | — | WEAK | The opening ¶ is a run of comfort disclosures. The multi-zone sentence breaks the antecedent of "it" in the next sentence (L22) |
| 8.1–8.3 | ✓ | 8.3 ends with a summary sentence ✓ | OK | — |
| 8.4 Multi-Zone | "Whether the single-zone ordering survives…" ✓ | No lead to §9 | OK/WEAK | Acceptable; §9 has its own plan |
| 9 SOTA and Ablation | Plan sentence ✓ | — | OK | — |
| 9.4 Scalability | "No claim is made about…" | Points to [Faraj2026] | WEAK | Open with what the section does: "The single-zone dynamic programme of MPC has 1,601 grid states and two actions per step; training cost, decision time and embedded deployability are not measured." |
| 10 Discussion | Plan sentence matches 10.1–10.4 ✓ | — | OK | — |
| 10.1 Climate and Headroom | "The difference between the cities…" | No lead to 10.2 | WEAK | 3 sentences, half of which repeat §8.2 (D7). Merge into §10.3 or extend |
| 10.3 What Governs the Saving | ✓ | Green Riyadh ¶ ✓ | **Stale content** | Lines 2416 and 2436 (M1) |
| 10.4 Limitations | Points to Table S6 | — | OK | Items 2, 4 and 5 restate §8–9 (D2, D5, D6) |
| 11 Conclusions | Recap + "Four findings" ✓ | Recommendations + field validation ✓ | OK | The 4th finding carries 4 topics (L44) |

## 3. Redundancy and repetition table

| # | Content repeated | Locations | Keep in | Action |
|---|---|---|---|---|
| D1 | "The cost saving is a charge on avoided on-commands, assumed to stand for wear, not a lower electricity bill" | Abstract 129–130; C6 203–206; Remark 2 564–567; §8.2 1871–1873; §7 1618–1619; Concl. 2623–2625; Rec. (iii) | Remark 2 (full), Abstract, Conclusions | §8.2: "…so the cost difference is the on-command charge (Remark 2)." C6: drop "which by an identity of the model leaves electricity unchanged". §7: delete the last sentence (1618–1619) |
| D2 | "Because the capacity acting over a cycle is probably below the reference, the reference results lean towards the end favourable to TUNED" | Remark 1 472–475; §8.3 2012–2015; §10.4 item 4 2502–2505; Concl. 2608–2610 (with ambiguous "it") | Remark 1 and §8.3 | §10.4: "…both results depend strongly on it (Section 8.3, Remark 1)." Concl.: fix the pronoun (L45) |
| D3 | "Inside the guard's own fitted thresholds neither lookahead nor learning adds a resolved margin" + "one-step shield matches TUNED" | Remark 5 1062–1063; §8.3 2046–2048; C4 197–199; Concl. 2616–2619 | §8.3; C4 and Conclusions as summaries | Remark 5: end at "…Section 8.3 measures that room with causal controllers." and delete the clause "part of it is … neither adds a resolved margin" |
| D4 | PPO seeds learn hold in Riyadh/Jeddah and fall below it in Taif; the training-length argument | §5.4 1277–1282; §9.2 2180–2197; §10.4 item 12 2566–2568; Abstract; C4; Concl. | §9.2 (results) | §5.4: replace 1277–1282 with "Section 9.2 reports how close the trained seeds come to that policy." §10.4 item 12: "longer training was not run (Section 9.2)." This also removes the categorical "almost nothing left to gain" (RL5) |
| D5 | The TUNED result on a 0.1 °C grid (5.7, 7.4, 8.4%) | §8.2 1893–1896; §10.4 item 5 2507–2509; Rec. (i) 2641–2642; Concl. 2599 | §8.2 | §10.4 item 5: "…restricted to the 0.1 °C steps of a real thermostat it saves much less (Section 8.2)…" |
| D6 | "Not transferable to other control steps" | §9.3 2294–2296; §10.4 item 2 2485–2488; Concl. 2611–2612 | §9.3 | §10.4 item 2: delete the first sentence and keep the comparator-sampling sentence |
| D7 | "Taif's lower load does not leave less to win in percentage terms" | §8.2 1905; §10.1 2371–2372; and §6.1 1466–1468 | §8.2 | §10.1: "Taif's load varies more, so the switch points that win its saving (Section 8.2) may move from week to week…" |
| D8 | List of exclusions (time-of-use or demand price, minimum on/off time, temperature-dependent COP, inverter units) and "the conclusions do not extend to them" | §3.4 713–714; §10.3 2451–2452; §10.4 item 13 2575–2577; §10.4 item 8 (COP) | §10.4 item 13 | §3.4: "…(Section 10.4)."; §10.3: "None of these is modelled (Section 10.4)" is enough. Delete "and that the conclusions of this paper do not extend to them" at 714 |
| D9 | "MPC plans on the plant's own model with the exact state" | §5.5 1393–1394; §8.3 1988–1989; §10.4 item 6 | §5.5, §10.4 | §8.3: delete 1988–1989 |
| D10 | Model L/E rate (0.12) is illustrative and unused | §3.4 652; Remark 3 733–735; §6.2 1486 | §3.4 | §6.2: delete the sentence "It is not the consumption-weighted average…", which Remark 3 already makes |
| D11 | SBC compliance "at assembly level" | §3.1 458; §6.2 1485 | §6.2 | §3.1: delete "The code constrains assemblies … at assembly level only." and keep the pointer to §6.2 |
| D12 | "Closest/nearest prior work is the author's own" | §1.1 166; §2.4 289–290 | §2.4 | §1.1: "…framework [Faraj2026], which Section 2.4 positions against the present study." |
| D13 | Comfort band "was not swept" | §6.2 1488; §10.3 2423; §10.4 item 1 2480; Concl. 2630 | §10.3, §10.4 | §6.2: delete "and was not swept"; Concl.: keep |
| D14 | "Rule layer enforces O1 by construction" | 885, 1089, 1240–1241, 2209 | §5 intro, §9.2 | Delete the stand-alone sentence "R1 and R2 enforce O1 by construction, not by training." (1240–1241), which ends a paragraph about pre-cooling |
| D15 | "With the one imperfect forecast tested, the margin … is therefore not resolved" | §8.3 1964–1966, directly after "not resolved (F3)" | first statement | Delete the repeated sentence and keep "forecasts between persistence and perfect were not tested." Update the letter's "key sentence" (Comment 4) to match |
| D16 | TUNED/THERM numbers in the supplement S1 "Actuation interval" ¶ | S1 l.77–83 and main §9.3 | main §9.3 | Acceptable in a supplement; optional trim |

## 4. Line-edit list

Rules: typo / grammar / punctuation / tone / redundancy / linkage / terminology / truthfulness. Severity: MA = MAJOR, mi = MINOR.

### Manuscript (main.tex)

| # | Location | Original | Correction | Rule | Sev |
|---|---|---|---|---|---|
| M1 | §10.3, 2413–2416 | "…the charge per on-command by $7$ across the derived range and the tariff by $7$ across the three epochs (Table~\ref{tab:sensitivity})." | "…the charge per on-command by $7$ across the derived range and the 2027 repricing by about $1$ (Table~\ref{tab:sensitivity})." | coherence (stale; Table 7(a) has two rows: 12.5 → 11.6) → R6 | **MA** |
| M2 | §10.3, 2435–2438 | "…the on-commands TUNED avoids are the same under all three epochs while the percentage falls as the bill grows (Section~…). A percentage quoted against one tariff epoch is not comparable with one quoted against another." | "…the on-commands TUNED avoids are the same at the 2018 and 2027 rates while the percentage falls as the bill grows (Section 8.2). A percentage quoted at one tariff is not comparable with one quoted at another." | coherence (stale) | **MA** (with M1) |
| L1 | Abstract 121–123 | "On/off cooling of Saudi split units is posed as…" | "On/off cooling by residential split units in Saudi Arabia is posed as…" | flow (the abstract opens without a subject context) | mi |
| L2 | Abstract 125–128 | "Tuning its two switch points widens the deadband: it avoids about 22–24% of on-commands with electricity essentially unchanged and saves 12.4–13.6% of cost at a reference charge above the range a wear estimate supports, and much less against a wider-deadband comparator." | "Tuning the thermostat's two switch points widens its deadband. The tuned thermostat avoids about 22–24% of on-commands with electricity essentially unchanged, and saves 12.4–13.6% of cost at a reference charge per on-command above the range a wear estimate supports; against a wider-deadband comparator it saves much less." | flow (one 45-word sentence; "it" switches referent) | mi |
| L3 | Abstract 128–130 | "The saving is a charge on avoided on-commands, supervisory commands not established as compressor starts, and not a lower electricity bill." | "The saving prices avoided on-commands (supervisory commands, not established as compressor starts); it is not a lower electricity bill." | grammar (an appositive inside a list) | mi |
| L3a | Abstract 135 | "…saves about 25% at 5 min and slightly less than the comparator at 30 min." | "…saves about 25% at a 5-min step and costs slightly more than the comparator at 30 min." | clarity ("saves less than the comparator" reads as a positive saving) | mi |
| L3b | Abstract 136–137 | "Proximal policy optimisation inside hard rules reproduces their hold policy in two cities and falls below it in Taif." | "Proximal policy optimisation (PPO) constrained by hard rules reproduces the rules' own hold policy in Riyadh and Jeddah and falls below it in Taif." | pronoun ("their"); vague "two cities"; ties to the title's "Rule-Constrained PPO" | mi |
| L3c | Abstract 140–142 | "Electricity follows the comfort target and the outdoor air (a cooler city, the Green Riyadh aim), not switching control at matched comfort." | "At matched comfort, electricity use is set by the comfort target and the outdoor air, as in the cooler city that Green Riyadh aims for, not by switching control." | word order; parenthetical | mi |
| L4 | C3, 184–186 | "(E2 and the MANUAL setback reference, which are not comfort-matched, are reported outside it)" | Delete the parenthesis (E2 and MANUAL are undefined at this point; §9.2 and §8.2 state their status) | linkage (forward jargon) | mi |
| L4a | C6, 203–206 | "…reporting that at matched mean temperature the cost difference is a charge on avoided on-commands, which by an identity of the model leaves electricity unchanged, and a Riyadh check…" | "…which shows that at matched mean temperature the cost difference is the on-command charge alone; and a Riyadh check…" | grammar ("reporting that" dangles); redundancy D1 | mi |
| L5 | Roadmap 210–220 | Eight sentences of the form "Section~X verbs …" | "Section 2 reviews the literature. Sections 3 and 4 define the thermal and cost models and formalise the constrained problem and its optimality conditions; Section 5 sets out the controllers, Section 6 the three climates and Section 7 the protocol. Section 8 reports the results and Section 9 compares them with published figures and gives the ablation, sensitivities, actuation step and scalability. Section 10 discusses the findings and their limitations, and Section 11 concludes." | rhythm (repeated sentence opener). **The roadmap is adequate and matches the 11 sections in order**; this is style only | mi |
| L6 | 163 | "…switches on when a room exceeds an upper setpoint and off when it returns, …" | "…switches on when a room exceeds an upper setpoint and off when it falls to a lower one, …" | clarity | mi |
| L7 | 165–166 | "…during exploration~\cite{Xu2025}. Hybrid approaches combine hard safety rules with RL~\cite{Xu2025}." | "…during exploration, which hybrid approaches prevent by combining hard safety rules with RL~\cite{Xu2025}." | redundancy (same citation twice in a row) | mi |
| L8 | 164 / 267 / 839; fig_leap caption | "switch-on command", "per switch-on", "switch-on cost", "switch-ons per day" | "on-command" throughout (defined at l.631) | terminology (the letter claims one name per concept) | mi |
| L9 | 258–260 | "PPO matches SAC at lower cost in an empirical comparison, which is the ground for adopting it here." | "…in an empirical comparison~\cite{Manjavacas2024}, which is why it is adopted here." and expand SAC (soft actor–critic) at first use; also DQN at l.1432 and CDD at l.1453 | tone; undefined acronyms | mi |
| L10 | 317 | "Neither study addresses three points, which form the gap this paper fills:" | "Neither that paper nor the others in Table 1 addresses the following three points, which form the gap this paper fills:" | linkage (antecedent of "Neither study" unclear) | mi |
| L11 | §3 title, 364 | "Problem Formulation" | "Thermal and Cost Models" (matches roadmap l.211 and avoids overlap with §4 "Constrained Formulation") | linkage | mi |
| L12 | Remark 1, 472–475 | "…so the reference value probably lies above the effective one, towards the capacities at which the tuned thermostat gains least; the results are therefore repeated…" | "…so the effective capacity probably lies below the reference value, in the range where the tuned thermostat gains least; the reference results therefore probably favour TUNED, and they are repeated…" | ambiguity ("towards…" can attach to either value; read one way it contradicts §8.3, §10.4 and the Abstract) → R6 | mi |
| L13 | 488 | "But \eqref{eq:forcing_condition} is only necessary." | "Condition~\eqref{eq:forcing_condition} is, however, only necessary." | style (a sentence that opens with "But" and an equation reference) | mi |
| L14 | 716 | "…and requires $E_{\mathrm{cum}}$ in the agent state." | "…and would require $E_{\mathrm{cum}}$ in the agent state; under the tariff in force it does not (Section 5.2)." | coherence with §5.2 (E_cum is not observed) | mi |
| L15 | 793 | "look-ahead" | "lookahead" (as at 1062, 2046, 2617); also supplement l.284 | terminology | mi |
| L16 | 873 | "No controller here solves the monthly problem~\eqref{eq:cop} itself: it states the objective, in line with the tariff's monthly reset, that the controllers approximate on a receding basis and that is evaluated on $168\,$h windows." | "No controller here solves the monthly problem~\eqref{eq:cop} (Section 4.3) itself. That problem states the objective, matched to the tariff's monthly reset; the controllers approximate it on a receding basis, and it is evaluated on 168 h windows." | pronoun; forward reference | mi |
| L17 | 1087–1088 | "The rule-constrained PPO controller (RBRL, rule-based reinforcement learning)" | "The rule-constrained PPO controller (RBRL)". Then use one name for this arm everywhere: Table 3 "RBRL, 5 seeds"; Table 6 "PPO inside the training rules"; Fig. 4 "Rule-constrained PPO"; Abstract and Concl. "PPO inside/under hard rules". Choose "RBRL (rule-constrained PPO)" in tables and figures | terminology (the expansion "rule-based" ≠ title's "rule-constrained") | mi |
| L18 | 1100–1102 | "…would remove the forced steps from the gradient but, with two actions, leaves the optimum unchanged." | "…would remove the forced steps from the gradient but, with two actions, would leave the optimum unchanged." | grammar (mood) | mi |
| L19 | 1219–1221 | "Cooling is about $2.9$ times the fastest warming, so $\epsilon_{\mathrm{cold}}=0.40$ and $\epsilon_{\mathrm{hot}}=0.20$ are adopted, so the agent acts on…" | "Cooling is about 2.9 times the fastest warming, so ε_cold = 0.40 and ε_hot = 0.20 °C are adopted; the agent then acts on…" | grammar (double "so") | mi |
| L19a | 334 / 472 / 739 | THERM and TUNED are used (472 "THERM's cycle"; 739 "TUNED and the bound") before they are defined in §5.5 | At first use (472): "…the period of the baseline thermostat's cycle (THERM, Section 5.5)…"; at 739: "the tuned thermostat (TUNED, Section 5.5)" | terminology (defined after use) | mi |
| L20 | §7 Statistics, 1592–1595 | "The primary families, each one contrast in three cities with Holm's correction within the family, are TUNED against THERM, MPC (24 h, perfect) against TUNED, MPC (24 h, persistence) against TUNED, and the guard against TUNED;" | "…are F1, TUNED against THERM; F2, MPC (24 h, perfect) against TUNED; F3, MPC (24 h, persistence) against TUNED; and F4, the guard against TUNED;" | linkage (F1–F4 are used at 1881, 1897, 1961, 1964, 2201 and 2554 but never assigned; at 1897 "the guard's shortfall F4" precedes even §9.2) | mi |
| L21 | 1556 | "each table states which applies (\texttt{fit\_status})" | "each table marks which applies" | tone (internal label; the letter says these were removed) | mi |
| L21a | 616 | "(\texttt{mz\_r3.py}, Section~\ref{sec:data})" | "(repository code, Section 12)" | internal file name in the body | mi |
| L22 | §8 opening, 1634–1640 | "…The multi-zone controller, which plans each room…, records 0.0001… The threshold arms meet it only on the tuning windows:" | Move the multi-zone sentence to §8.4 (or the end of the paragraph), and write "The threshold arms meet the cold rule only on the tuning windows:" | pronoun reference ("it" now refers back across the multi-zone sentence) | mi |
| L23 | 1600–1601 | "…treated as not resolved, whatever a test says," | "…treated as not resolved, regardless of the test result," (likewise supplement Table S7 caption "whatever the test") | tone (colloquial) | mi |
| L24 | 1616–1617 | "it lies above the derived range and overstates the saving against it, since the saving rises with $\csw$." | "it lies above the derived range and so overstates the saving relative to that range, because the saving rises with $\csw$." | clarity ("against it") | mi |
| L25 | 1749–1751 | "In an earlier run of the bound under the simulator's energy-only terminal $B^\ast$ was 20.0 and 20.1%…" | "Under the simulator's energy-only terminal, $B^\ast$ is 20.0 and 20.1% in Riyadh and Jeddah (not computed for Taif)." (keep the provenance note in the Data section) | tone (reads like a lab notebook) | mi |
| L26 | 1911–1914 | "…TUNED saves 11.6, 12.7 and 11.6%, while the on-commands it avoids are unchanged, because a higher energy price dilutes a saving whose mechanism is a fixed charge per on-command." | "…TUNED saves 11.6, 12.7 and 11.6% while avoiding the same on-commands: a higher energy price dilutes a saving whose mechanism is a fixed charge per on-command." | logic ("because" attaches to "unchanged") | mi |
| L27 | 1951 | "E2-PPO" | "E2" (as everywhere else) | terminology | mi |
| L28 | 1964–1966 | "With the one imperfect forecast tested, the margin over the tuned thermostat is therefore not resolved; forecasts between…" | "Forecasts between persistence and perfect were not tested." (D15) | redundancy | mi |
| L29 | 1988–1989 | "Both modes plan on the plant's own model with the exact state, so neither measures model mismatch." | Delete (D9; stated in §5.5 and §10.4 item 6) | redundancy | mi |
| L30 | 2019 | "In the following cells the fitted multiplier lies far above $\lambda^\ast$: $\lambda/\lambda^\ast=1.226$ and…" | "In the following cells the fitted multiplier lies well above $\lambda^\ast$ (by 23% to a factor of 13):" | tone (1.226 is not "far") | mi |
| L31 | 2070 | "With rules alone, TUNED on the dwelling mean saves…" | "Among the threshold rules, TUNED saves, on the dwelling mean, …" | clarity ("rules" also names the rule layer) | mi |
| L32 | 2186–2187 | "Inside the rules hold is nearly optimal for the cost-only reward" | "Inside the rules, the hold policy is nearly optimal for the cost-only reward" | punctuation; jargon | mi |
| L33 | §9.4, 2344–2345 | "No claim is made about training cost, decision time or embedded deployability; the single-zone dynamic programme…" | See the bridge in the linkage table | linkage (abrupt negative opener) | mi |
| L34 | §10.1, 2370–2377 | Whole subsection | Merge into §10.3 as its first paragraph, or delete the repeated Taif clause (D7) | redundancy; orphan (92 words, no onward link) | mi |
| L35 | 2440–2441 | "…has nothing to be sold into; a time-varying price would change that." | "…offers nothing to arbitrage; a time-varying price would change that." | idiom | mi |
| L36 | 2443 | "A controller could save money rather than on-commands only by changing the electricity itself." | "A controller could lower the electricity bill, rather than the on-command charge, only by changing the electricity drawn." | clarity (on-commands are priced in money too) | mi |
| L37 | 2444–2445 | "MPC and the clairvoyant bound already choose the whole temperature path inside the band at every step, coupled rooms included," | Delete "coupled rooms included" or write "MPC, including the multi-zone MPC, and the single-zone clairvoyant bound…" (the bound is single-zone, §9.4) | coherence → R6 (flagged in the pass log, still open) | mi |
| L38 | §10.4 item 2, 2485–2488 | "\emph{Tied to the 15-min step.} The savings depend on the actuation step … not transferable to other control steps (Section~…)." | "\emph{Tied to the 15-min step} (Section 9.3). The comparator is a 1 °C hysteresis evaluated at the actuation step; …" | redundancy D6 | mi |
| L39 | §10.4 item 4, 2501–2505 | "…The capacity is assumed, and both results depend strongly on it (Section~…); because the capacity acting at the period of THERM's cycle is probably below … favourable to TUNED." | "…The capacity is assumed, and both results depend strongly on it, probably in TUNED's favour at the reference value (Remark 1, Section 8.3)." | redundancy D2 | mi |
| L40 | §10.4 item 5, 2507–2509 | "…restricted to the 0.1 °C steps of a real thermostat it saves 5.7, 7.4 and 8.4% instead of the headline figures, …" | "…restricted to the 0.1 °C steps of a real thermostat it saves much less (Section 8.2), …" | redundancy D5 | mi |
| L41 | §10.4 item 7, 2522–2523 | "…and in an earlier run under that terminal CLV ended its windows markedly warmer than THERM." | "…and under that terminal CLV ends its windows warmer than THERM." (or give the number) | tone (vague intensifier; lab-notebook phrasing) | mi |
| L42 | §10.4 item 12, 2564–2568 | "…learners acting outside R1–R2 are untested; longer training is not run, but on the tuning weeks the trained policies already sit close to the hold policy's training cost (Section~…), so it has little to gain." | "…learners acting outside R1–R2 are untested, and longer training was not run (Section 9.2)." | run-on; ambiguous "it"; categorical (see RL5) | mi |
| L43 | §5.4, 1273–1282 | "…That shortfall is one of generalisation, not of training length: … so a longer run on the same weeks has almost nothing left to gain." | Replace with "Section 9.2 reports how close the trained seeds come to that policy." and keep the evidence in §9.2 (D4) | redundancy; results in the method section; categorical | mi |
| L44 | Concl. 4th finding, 2623–2635 | One paragraph covering electricity identity, comfort and outdoor air, the money caveat, setback, and multi-zone | Split it: keep the electricity, comfort and outdoor-air content as "Fourth"; move setback and multi-zone into a short closing sentence pair: "Occupancy setback and multi-room dwellings were also examined: setback raises…; with independent units in two- and four-room dwellings…" | flow | mi |
| L45 | Concl. 2609–2610 | "…the reference results lean towards the end favourable to it." | "…the reference results probably favour the tuned thermostat." | pronoun ("it" can refer to MPC) | mi |
| L46 | Concl. 2626–2628 | "…and with the outdoor air: air $1.5$–$2\,$K cooler…" | "…and with the outdoor air: a city $1.5$–$2\,$K cooler…" | repetition ("air: air") | mi |
| L47 | Data section, 2680 | "It comprises the thermal model, …" | "The repository comprises the thermal model, …" | pronoun (antecedent is "the trained PPO models") | mi |
| L48 | Data section, 2684–2690 | "A gate of 188 numerical invariants … the feasibility class retains some checks written for the band of an earlier version of the model." | "A test suite of 188 numerical invariants … runs before any table is produced and exits non-zero on any failure." Move the earlier-band remark to the repository README | jargon ("gate"); development note | mi |
| L49 | Source 88–103, 117–119, 145, 2054–2055, 2410–2411; l.71 `\pend` | Internal comments (title decision tree, "once the placeholders are filled", "Gate (RULING §12.1)…", "fig_tariff is withheld…"), and the unused `\pend` macro | Strip them from the submitted `.tex` (JKSU-ES receives the source) | housekeeping; no placeholders render | mi |
| L50 | Repeated triads | "for three reasons" (424), "in three ways" (547, 1946, 2132), "Three consequences" (689), "three design inputs" (872), "Two properties" (716) | Keep where they organise content. Rephrase two of them, e.g. 547 "The identity constrains the results as follows." and 2132 "Its figures differ from these in three respects: two lower them…" | tone (enumeration habit) | mi |
| L51 | 1466–1468 | "Its load is the smallest of the three while its headroom is not, so Taif leaves the least to schedule in absolute terms." | "Its load is the smallest of the three, so it leaves the least to schedule in absolute terms, although its headroom in percentage terms is not the smallest (Section 8.2)." | logic ("so" does not follow from "headroom is not") | mi |

### Supplement (supplement.tex)

| # | Location | Original | Correction | Rule | Sev |
|---|---|---|---|---|---|
| S1 | S1 "Stability…", l.135–136 | "($0.17\,$kWh here, against tier widths of $2{,}000\,$kWh)" | "($0.17\,$kWh here, against a first block of $6{,}000\,$kWh)" | coherence (relic of the withdrawn four-tier tariff; Comment 6) | mi (→ letter RL1) |
| S2 | S8 title, l.306 | "Comfort records and the bound at each arm's own mean" | "Comfort records, vacation weeks and the bound at each arm's own mean" (main §8.2 sends readers here for vacation weeks) | linkage | mi |
| S3 | Table S-MZ caption, l.284 | "look-ahead … $1601$ nodes" | "lookahead … $1{,}601$ nodes" | terminology; number format | mi |
| S4 | Table S-MZ / main §8.4 | 1×2 MPC-MZ cells carry ᵇ (0.10 K fallback) in S-MZ; the main text gives 16.0/15.8 without the mark | Add "(the 1×2 cells at the 0.10 K fallback)" in §8.4 | → R6 | mi |
| S5 | Table S7 caption | "whatever the test" | "regardless of the test result" | tone | mi |

### Response letter (RESPONSE_LETTER.md)

| # | Location | Original | Correction | Rule | Sev |
|---|---|---|---|---|---|
| RL1 | Comment 6, l.149, 151, 154, 157 | (a) l.154 quotes Section 3.4: Model S "is a historical schedule, no longer the tariff in force, and it is used here as a stress-test instantiation…". This text is not in `main.tex`, where Model S is instantiated with the tariff in force. (b) l.151: "under all three epochs while its cost saving is 18.6, 12.5 and 11.6%". (c) l.157: "Table 7(a) (three tariff epochs)". These contradict l.149 ("removed from the analysis altogether"). | (a) Replace the quote with the actual sentence (l.655): "It is instantiated with the Saudi residential tariff in force since January 2018, a two-block schedule in which the marginal price rises once, at 6,000 kWh per billing month." (b) "TUNED avoids the same 22.8% of on-commands in Riyadh at the 2018 and 2027 rates while its cost saving falls from 12.5 to 11.6%." (c) "Table 7(a) (tariff in force and 2027 rate)". Also fix main M1/M2 and supplement S1 so the letter's claim "removed altogether" is true | truthfulness | **MA** |
| RL2 | Comment A "Repetition", l.215 | "results given in Sections 8 and 9 are no longer restated with their figures in the theory sections, the Discussion or the Limitations" | Either apply D4/D5/L38–L43 (Remark 5 and §5.4 still give results; §10.4 items 5 and 9 and §10.1 give figures), or soften: "are restated in the theory sections, Discussion and Limitations only where a qualification needs the figure" | truthfulness | **MA** (with RL3–RL5) |
| RL3 | same, l.215 | "the conclusions no longer repeat the abstract's figures" | Untrue: 22–24%, 4–6 points and 25% appear in both. Write "the conclusions state each figure once and add the implications" | truthfulness | (MA group) |
| RL4 | "Flow", l.217 | "internal labels and file names were removed from the text" | Untrue (`fit_status`, `mz_r3.py`; the latter two in the Data section are legitimate). Apply L21/L21a, or narrow the claim to "from the results sections" | truthfulness | (MA group) |
| RL5 | "Tone", l.218; and l.245 | "the claim that a longer training run would not help (now 'longer training was not tested')"; "the earlier statement that a longer training run would not help is removed" | The phrase "longer training was not tested" does not occur. Main l.1282 says "a longer run … has almost nothing left to gain" and §10.4 says "so it has little to gain". Apply L42/L43, or quote the actual text | truthfulness (Comment A asks to moderate categorical statements) | (MA group) |
| RL6 | Comment 4, l.123 | Key sentence "With the one imperfect forecast tested, the margin … is therefore not resolved; …" | If L28 is applied, quote "Forecasts between persistence and perfect were not tested." | consistency | mi |
| RL7 | Comment A "Flow", l.217 | "one name is used for each concept" | True for MPC and on-command; not yet for the PPO arm (L17), on-command vs switch-on (L8), E2 vs E2-PPO (L27). Apply those edits | truthfulness | mi |
| RL8 | Summary of changes, l.39 | "A gate of 188 numerical invariants … (the feasibility class retains some checks written for the band of an earlier version…)" | Mirror L48 | tone | mi |

The rest of the letter reads naturally. The sentences are plain and every point answers the comment it follows; Comments 2, 3 and 8 are answered fully and truthfully as far as language and description are concerned. The Limitations block (l.266–280) matches §10.4 word for word, so any edit under L38–L42 must be mirrored there.

## 5. Specific questions from the coordinator

**Is the Introduction roadmap adequate?** Yes. The roadmap at lines 210–220 names all eleven sections in the order delivered, and each with `\ref{sec:…}`. Its descriptions match the content, including the §9 additions (actuation step, scalability) and §10 (findings and limitations). The audit's D1 MAJOR is a false positive of the script. The only weaknesses are stylistic:
- eight sentences with the same opener (L5);
- §3 is described as "defines the thermal and cost models", which suits its content better than its title "Problem Formulation" (L11).

**Section openings and transitions.** These are good overall:
- Sections 2, 3, 4, 5, 7, 8, 9 and 10 each open with a plan or a link back.
- §5 closes forward ("the three climates characterised next").
- §3 closes forward ("the following section formalises…").

The weak spots are §9.4 (abrupt negative opener), §10.1 (short, half of it repeated, no onward link), the §8 opening paragraph (a run of comfort disclosures with a broken pronoun) and §5.4/Remark 5 (results inside method or theory).

**Terminology.**
- *MPC* is consistent after the pass. It is defined at 165 and again in the abstract, which is acceptable.
- *THERM/TUNED* are used before they are defined at 472 and 739 (L19a).
- *Rule-constrained PPO/RBRL* is not consistent: there are four names for one arm, and the acronym's expansion ("rule-based reinforcement learning") differs from the title's "Rule-Constrained" (L17).
- The *on-command vs switch-on* distinction is mostly kept, with four leftovers (L8).
- *F1–F4* are never introduced (L20).
- *lookahead/look-ahead*: L15.

**Abstract.** It now reads as connected prose, and the number count is moderate (about 12 figures in 238 words, within the author's "few numbers" decision). Four sentences still need repair: L2 (a 45-word sentence in which "it" changes referent), L3, L3a ("slightly less than the comparator" is misleading for a negative saving) and L3c. L3b also links the abstract to the title's "rule-constrained PPO". No AI tone.

## 6. Tone profile

- AI-typical terms (§A list): **0**. Filler phrases ("it is worth noting", "in order to"): **0**.
- Connector-led sentences (Moreover/Furthermore/Additionally): **0**.
- "therefore": 21 (down from 27); "thus": 2. This is acceptable, but four of them follow an obvious link (e.g. 741 and 1901), and those can go.
- Em dashes in running text: **0**. The audit's 49 are table "---" cells.
- Colloquial phrasing: "whatever a test says" (×2 plus the supplement), "sold into", "far above", "markedly", "an earlier run" (×2).
- Spelling variety: British (-ise, -our, modelled). The only US forms are the CRediT terms "Conceptualization" and "Visualization", which are fixed.
- Rhythm: enumerated triads are a habit (L50); in Remark 1, Remark 2 and §3.4, paragraph openers repeat "The…" (audit I-findings 225–230); sentence length varies.

## 7. Paper Quality Standard checklist (my items)

| ID | Check | Status |
|---|---|---|
| Q1.1 | Sections and subsections linked both ways | PASS with minor fixes (§9.4, §10.1, §8 opening) |
| Q1.2 | Roadmap matches the structure | PASS (audit D1 is a false positive); style fix L5 |
| Q6.1 | Formal tone, no contractions | PASS (fix the colloquialisms in L23, L35 and L41) |
| Q6.2 | No duplication or redundancy | PARTIAL: D1–D15 open, and the M1/M2 stale passage |
| Q6.4 | Writing-quality checklist applied | PASS |
| Q6.5 | No typos, grammar or punctuation errors; one variety | PASS with minor fixes (L18, L19, L26, L32) |
| Q6.6 | Natural academic language, no AI tone | PASS |

## 8. Verdict on journal Comment A

**Partly met as it stands, and fully met after the edits above.**

Met:
- **Punctuation and typography:** no doubled stops or typos remain, there are no contractions, and spelling is British throughout.
- **Moderating categorical or promotional statements:** met, except for the training-length claim (L42/L43, RL5) and two intensifiers (L30, L41).
- **Sentence flow:** improved markedly. The remaining knots are in the abstract (L2/L3/L3a/L3c), the §8 opening paragraph and the 4th conclusion.

Not yet met:
- **Reducing repetition:** improved, but not complete. The "charge on avoided on-commands" disclosure, the capacity caveat, the PPO-learns-hold result and the exclusions list each still appear 3–5 times (D1–D8). The §10.3 tariff-epoch passage now contradicts its own table (M1/M2).
- **The response letter** overstates what was done for Comment A (RL2–RL5) and misquotes the manuscript for Comment 6 (RL1). Comment 6 itself is the editor's most serious tariff concern, so this needs fixing before resubmission.

## 9. Panel-1 closure (R11 MAJOR items)

| Panel-1 item | Status now |
|---|---|
| R1/R2 + P13: tariff-boundary disclosure ×9 and pre-cooling ×6 | **Largely closed.** The boundary now has a full statement in Remark 3 and one clause each in 4 other places. Pre-cooling has 3 distinct roles plus one back-reference. What remains is the exclusions list (D8) and the stale "three epochs" (M1/M2), which is new |
| A4: abstract dense with numbers, "the planner" | **Closed** (about 12 figures, no "planner"). Four minor flow edits remain (L2–L3c) |
| C1/R6: conclusions repeat the abstract, ~40 numbers | **Mostly closed.** Now four findings and recommendations, each number stated once. The 4th finding is overloaded (L44); some abstract figures recur, which is normal |
| RL1: letter claims "each disclosure once" | **Reopened in new form.** The softened claim is now accurate for the disclosures, but new claims (no figures restated, conclusions do not repeat the abstract, labels removed, longer-training wording) are not accurate (RL2–RL5); a Comment 6 misquote is added (RL1) |
| Panel-1 minor: categorical phrases ("non-negotiable", "closes the question", "cannot beat", "the correct one", "most valuable field measurement", "knife edge", "requires intelligent, adaptive control", "round-3 protocol", file names) | All removed except "a longer run … has almost nothing left to gain" (L43) and `fit_status`/`mz_r3.py` (L21/L21a) |
| §2 opening ("four components of the gap") | Closed |
| §4 opening paragraph missing | Closed (759–763) |
| Observation 2 cited before it is stated | Still open (deliberately deferred; acceptable with numbered labels) |

## 10. Verdict

**NOT READY.** No new analysis is needed; this is an editing job of about 1–2 hours. Under the review standard, a MAJOR coherence or truthfulness finding blocks acceptance. The blocking items are:
- M1/M2: the stale tariff-epoch passage in §10.3, together with supplement S1;
- RL1: the misquoted Section 3.4 and the "three epochs" claims in the Comment 6 response;
- RL2–RL5: overclaims in the Comment A response.

Once these are fixed, and preferably the redundancy edits D1–D9 and the terminology edits L8, L17 and L20 as well, the manuscript is ready for typesetting from a language standpoint, and Comment A is met.

Findings by severity: **CRITICAL 0 · MAJOR 3** (M1/M2 stale tariff epochs; RL1 Comment 6 misquote; RL2–RL5 Comment A overclaims) **· MINOR 79** (D1–D16 redundancy, L1–L51 manuscript line edits, S1–S5 supplement, RL6–RL8 letter).

Items for R6 (contradictions noted, not analysed):
- M1/M2 (7 points vs 0.9);
- L12 (direction in Remark 1);
- L37 (bound described as covering coupled rooms);
- S4 (multi-zone fallback mark missing in the main text);
- L14 (E_cum "required" in the state but not observed).
