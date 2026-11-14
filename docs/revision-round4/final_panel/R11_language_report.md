# Reviewer R11: Language and Coherence (final panel, round 4)

Scope: every sentence of `main.tex` (2,653 lines, including the input file `tables/tab_stats.tex`), `supplement.tex` and `RESPONSE_LETTER.md`. I started from the Phase 0 audit checks B, D and I. Line numbers refer to `main.tex` unless the location names another file. The two placeholders that are open by design (MPC-MZ and the Zenodo DOI) are not reported.

## 1. Summary

Readability has improved a great deal. The prose is plain and mostly free of AI-typical inflation. The audit found no typos and no doubled words; its "MATH MATH" and "on on" hits are artefacts of stripping maths and citations. There are no contractions, and only two em dashes appear in running text. Spelling is consistently British "-ise"; the US spellings left in the response letter all occur inside quotations of the journal. Most of the 110 audit I-findings ("space before ','" and "sentence starts lower-case") are artefacts of removing `\cite`/`\ref`. Audit item D1 ("no roadmap") is a false positive: a roadmap is at lines 209–218.

The three problems that matter most:

1. **Repeated disclosures (MAJOR).**
   - The point that the dwelling never crosses a tariff boundary is stated 9 times (lines 331–333, 363–366, 679, 709–712, 744, 769–771, 1246–1247, 1579–1582, 2427–2428).
   - The point that pre-cooling is dominated is stated 6 times (565–567, 725–728, 745–753, 1136–1138, 1292–1306, 2359–2361).
   - The point that free-float drift "no action can prevent" is stated 4–5 times.

   The response letter says that "each disclosure is made once in full, with cross-references elsewhere". That is not yet true.
2. **Long sentences packed with numbers in the abstract, conclusions and Section 8.3 (MAJOR).** The abstract carries about 45 numbers in 237 words. "The planner", "saves −2.8%" and "(single zone 12.5%; not resolved)" are cryptic. The first paragraph of the conclusions (lines 2536–2556) is about 250 words with about 40 numbers, and it largely repeats the abstract.
3. **Leftover categorical or promotional phrasing and internal jargon (MINOR, but Comment A names these explicitly).**
   - Categorical: "therefore requires intelligent, adaptive control" (line 161); "non-negotiable" (982); "closes the question" (1293); "cannot beat" (2047); "the correct one" (2411); "the most valuable field measurement for testing this study" (2268).
   - Internal jargon: "round-3 protocol" and the file names `T1v2_…` (2415–2416). "Compressor on-commands" (125, 1916, 2536) undoes the careful on-command/compressor-start distinction made at lines 646–648 and 2454–2457.

**Is Comment A met?** Partly.
- Typography and punctuation: **met**.
- Moderating categorical or promotional statements: **mostly met**. About eight phrases remain (listed below).
- Reducing repetition: **not met**. See item 1.
- Sentence flow: **not met in the abstract, the conclusions, Section 8.3 and Section 8.1**.

**Effort:** about half a day of editing. No new analysis is needed.

## 2. Section linkage table

| Section / subsection | Opens by linking to | Closes by leading to | Status | Suggested bridge sentence |
|---|---|---|---|---|
| 1 Introduction / 1.1 / 1.2 | context → motivation | roadmap (209–218) | OK | Fix "its limitations" → "their limitations" (line 217) |
| 2 Literature Review | announces "four components of the gap" (223–225) | Gap → Sect. 3 | WEAK | The four components (binary actuation, hard comfort, optimality reference, Saudi coverage) do not match the subsection order (Saudi Context; Control Approaches; Binary/Multi-zone/Tariffs; Gap). Either reorder or write: "Section 2.1 sets the Saudi context, 2.2 the control approaches, 2.3 binary actuation, multi-zone coupling and tariffs, and 2.4 the gap." |
| 3 Problem Formulation | links to the gaps (377–381) ✓ | bridge to Sect. 4 (800) ✓ | OK | The title overlaps with Sect. 4 ("Constrained Formulation"). Consider renaming it "System and Cost Models", as the roadmap says. |
| 4 Optimal Schedule | no intro paragraph; goes straight to 4.1 | 1136–1139 → Sect. 5 ✓ | WEAK | Add after 803: "This section casts the problem over an infinite horizon (4.1), relates its single-zone core to SLHA (4.2), states the monthly constrained problem (4.3) and derives the optimality conditions and the corollary on the rule layer (4.4)." |
| 4.4 Observation 2 (`prop:structure`) | cited at 797, 904, 909 and 995 before it is stated at 1004 | — | WEAK | Move the Observation before Remark 4 (`rem:csw`), or replace the early citations with "(Observation 2, below)". |
| 5 Controllers | links to O1–O3 (1144–1149) ✓ | "applied to the three climates characterised next" (1499) ✓ | OK | — |
| 6 Case Studies | one-line purpose ✓ | no closing bridge | OK/WEAK | End 6.2 with: "Section 7 sets out how these sites are simulated and how every arm is selected and scored." |
| 7 Simulation Setup | no link sentence | no bridge to 8 | WEAK | Open with: "The controllers of Section 5 are evaluated on the sites of Section 6 under one protocol, set out here." |
| 8 Results | conditions + roadmap (1688–1702) ✓ | 8.4 → 9 | OK | — |
| 9 Analysis | intro (2119–2121) ✓ | 9.4 Scalability ends without a bridge | OK/WEAK | — |
| 10 Discussion | no intro paragraph | 10.4 → 11 ✓ | WEAK | Add: "This section interprets the city differences (10.1), the robustness of the results (10.2) and the factors that govern the saving (10.3), and lists the limitations (10.4)." |
| 11 Conclusions | restates the problem ✓ | recommendations ✓ | OK, but repeats the abstract | See the redundancy table, item R6 |
| Supplement S1–S6 | descriptive cross-references ("main text, Actuation Step") | — | WEAK | Use section and table numbers ("Section 9.3, Table 8") so readers can navigate. |

Terminology introduced before use:
- "E1" first appears at line 1483 without definition; it is only implicitly defined at 2191.
- "the planner" (abstract, 2043, 2465) is never defined as a synonym of the receding-horizon controller.
- The method has four names: "RBRL" (1145), "rule-constrained PPO" (title, abstract), "PPO inside the rules" and "hybrid rule-RL" (168). Choose one (suggestion: "rule-constrained PPO (RBRL)", defined once in the introduction).
- Acronyms never expanded in the text: HVAC, PPO (only in the keywords), RC, SAC, TD3, DDPG, DQN, MADDPG, DRL, FPTAS, GA, SA, SBC, TMYx, IWEC, EPW, ACH, VAV. COP and SHGC are expanded only in Table 2. CDD is used at 1514 but expanded at 2373.

## 3. Redundancy and repetition table

| # | Content repeated | Locations | Keep in | Action |
|---|---|---|---|---|
| R1 | The modelled dwelling never crosses a tariff boundary / stays in the first block | 331–333, 363–366 (Table 1 note), 679 (twice in one paragraph: "stress test" ×2), 709–712, 744, 769–771 (Remark 3), 1246–1247, 1579–1582, 2427–2428 | Remark 3 (769–771) and the Table 1 note | Elsewhere use one clause plus "(Remark 3)". In 679, delete "and the account modelled here reaches none of its boundaries (Section 7), so it enters only as a stress test of the formulation". In 744, delete "the dwelling modelled here crosses none of them". |
| R2 | Pre-cooling is dominated / the bill does not depend on timing | 565–567, 725–728, 745–753, 1136–1138, 1292–1306, 2359–2361 | 725–740 (Prop. 1 consequences) for the tariff argument; 1296–1306 for the leakage arithmetic | Delete 745–753 (it restates 714–728 almost word for word). Cut 1292–1296 to "Proposition 1 and Remark 2 rule out a pre-cooling rule here; the only route back is physical:". In 1136–1138 and 2359–2361, replace with a cross-reference. |
| R3 | "free-float drift below the band, which no action can prevent, is measured" | 960–963, 982, 1307–1308, 1324–1325, 1721–1723 | 960–963 (Def. 4) and Rule B (1627–1629) | Delete the repetitions at 982, 1307–1308 and 1325. |
| R4 | Rule layer "consistent with but not implementing" complete cycles; corollary does not hold under diurnal drift | 907–922, 988, 1087–1093, 1119–1125, 1127–1134 | 907–922 and Remark 5 | Reduce 988 and 1119–1125 to one sentence each with a reference. |
| R5 | The capacity and actuation-step dependence with full numbers | Abstract, C4, 8.3 (2030–2050), 9.3, 10.2, 10.3 (2402–2405), 10.4 items 2 and 4, Conclusions | Full numbers in 8.3, 9.3 and the abstract; the limitation items | In 10.2 (2385–2387) and 10.3 (2402–2405), use a cross-reference without repeating the numbers. |
| R6 | Conclusions paragraph 1 repeats the abstract almost verbatim; the TUNED 12.5/13.6/12.4 figures appear twice in that paragraph (2539–2540 and 2554) | Abstract and 2536–2556 | — | Rewrite the conclusions as findings and implications, with fewer numbers (see line edits C1–C3). |
| R7 | "in preference to the older IWEC files" | 1522–1523, 1543, 2641 | 2641 (Data) | Delete it at 1543. |
| R8 | "knife edge" idiom | 1438–1439, 2058, Table 8 caption 2300 | — | Replace with "is sensitive to λ" (see the line edits). |
| R9 | The comfort-offset caveat (0.01 K ≈ 1.3 points) | Table 3 caption, 1104–1107, 2074–2075, 2501–2505, 2563–2565, letter | Limitations item 10 + Table 3 caption | Elsewhere use "(comfort-offset caveat, Section 10.4)". |

## 4. Line-edit list

Severity codes: MA = MAJOR, mi = MINOR. Items are in section order, with the priority sections first.

### Abstract (lines 121–143)

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| A1 | 121–122 | "is posed as constrained optimisation with hard comfort, a charge per on-command" | "is posed as a constrained optimisation problem with hard comfort constraints, a charge per on-command" | grammar (article; incomplete noun phrase) | mi |
| A2 | 125 | "avoids 22–24% of compressor on-commands" | "avoids 22–24% of on-commands" | coherence (contradicts 646–648 and Limitation 3) | mi |
| A3 | 127 | "at the 0.025–0.114 SAR per start that wear supports" | "at the 0.025–0.114 SAR per start that a wear estimate supports" | wording | mi |
| A4 | 132–137 | "Both depend strongly on capacity and actuation step: in Riyadh the tuned thermostat saves −2.8% at half and 15.8% at twice the reference capacity (the planner's margin from 15.0 points to 0.4), and across cities about 25% at a 5-min step, 12.4–13.6% at 15 min and −1.2 to −1.5% at 30 min, where the planner keeps 6.6–11.4%." | Split into two sentences: "Both results depend strongly on thermal capacity: in Riyadh the tuned thermostat's saving ranges from −2.8% at half to 15.8% at twice the reference capacity, and the receding-horizon controller's margin over it shrinks from 15.0 to 0.4 points. They also depend on the actuation step: the tuned thermostat saves about 25% at 5 min, 12.4–13.6% at 15 min and −1.2 to −1.5% at 30 min, where the receding-horizon controller still saves 6.6–11.4%." | flow; undefined term ("planner"); number density | MA (with A5–A6) |
| A5 | 140–142 | "the tuned thermostat saves 11.7–13.6% (single zone 12.5%; not resolved)" | "the tuned thermostat saves 11.7–13.6%, against 12.5% for a single zone; the differences are not resolved" | clarity | mi |
| A6 | 142–143 | "The benefit is reduced cycling and wear, not a lower bill; the setpoint is what reduces electricity." | "The benefit is reduced cycling and wear, not a lower bill; only a warmer setpoint reduces electricity use." | flow | mi |
| A7 | 138–140 | "A clairvoyant schedule and a provable bound bracket the saving at …" | "A clairvoyant schedule and a provable bound place the best achievable saving between 18.0 and 20.0% (Riyadh), …" | ambiguity ("the saving" of what?) | mi |

### Introduction (lines 156–218)

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| I1 | 160 | "the challenge is particularly acute" | "the share is larger" | tone (cliché) | mi |
| I2 | 160 | "\cite{AlHomoud2021}, \cite{Krarti2020}" (also 167 and 386) | "\cite{AlHomoud2021,Krarti2020}" | punctuation / citation style | mi |
| I3 | 161 | "Achieving the efficiency targets of Saudi Vision 2030 therefore requires intelligent, adaptive control of residential HVAC systems" | "Better operation of residential air conditioning is therefore one route to the efficiency targets of Saudi Vision 2030" | tone (categorical/promotional, and at odds with the finding that a tuned thermostat captures most of the saving) | mi |
| I4 | 165–166 | "…with no tariff awareness and no inter-zone coordination. It cycles on a fixed deadband, and every switch-on command adds wear that it does not price; under the Saudi block tariff it also has no view of the price." | "…with no inter-zone coordination. It cycles on a fixed deadband, and every switch-on adds wear that it does not price." | redundancy (tariff blindness stated twice) | mi |
| I5 | 167–168 | Hybrid rule-RL sentence + Xu2025 | Keep here; delete the near-duplicate at 265–267 or cross-reference it | redundancy | mi |
| I6 | 173–207 | "Six contributions are made. (C1)~… (C6)~…" as one run-on paragraph; C4 is a single sentence of about 90 words | Set as an `enumerate` list. Split C4: "(C4) A controlled comparison of … across thermal capacities. It shows that the receding-horizon controller's margin over the tuned thermostat requires a perfect in-horizon forecast and a light plant and changes with the actuation step; that an exact one-step shield matches the tuned thermostat; and that PPO inside the rules converges to the rules' hold policy, even with a comfort term and a forecast." | flow; long sentence | mi |
| I7 | 217 | "interprets the findings and its limitations" | "interprets the findings and states their limitations" | grammar (agreement) | mi |
| I8 | 216 | "ablates and benchmarks" | "compares the results with published figures and reports the ablations and sensitivities" | jargon | mi |

### Section 2 Literature review

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| L1 | 223–225 | "The review covers the four components of the gap: …" | Add the subsection roadmap shown in the linkage table, or order the subsections by the four components | linkage | mi |
| L2 | 296 | "and the relationship is best stated directly." | delete | tone (filler) | mi |
| L3 | 300–302 | "\emph{soft} … \emph{no} optimality certificate" | Drop the emphatic italics | tone (adversarial emphasis on prior work) | mi |
| L4 | 306–307 | "observes that formal constraint enforcement would provide stronger safety properties than its top-$k$ projection heuristic does" | "…than its top-$k$ projection heuristic" | redundancy ("does") | mi |
| L5 | 324–325 | "What remains unaddressed by either study, and is therefore the gap this paper fills:" | "Neither study addresses three points, which form the gap this paper fills:" | flow | mi |

### Section 3 Problem formulation

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| P1 | 446 | "a bound the room-air capacity violates at an hourly step" | "a bound that an air-only capacity (about 77 kJ/K) violates at an hourly step" (the main text never defines a "room-air capacity") | linkage (undefined referent) | mi |
| P2 | 450 | "Third, the step size now affects only…" | "Third, the step size affects only…" | wording ("now" refers to the revision history) | mi |
| P3 | 472 | "Table 2 states the assembly transmittances and areas … Both are at the SBC 2018 prescriptive maximum" | "…The two transmittances are at the SBC 2018 prescriptive maximum" | pronoun reference ("Both" picks up areas too) | mi |
| P4 | 472 | One paragraph of about 200 words mixing parameters, infiltration and legal enforcement; "Code compliance is a legal fact rather than an idealisation" | Split after "…(slightly more than one face of fabric)." Then write "Compliance is mandatory: …" | flow; tone (defensive) | mi |
| P5 | 517 | "The distinction is not academic:" | "The distinction matters:" | tone (idiom) | mi |
| P6 | 528 and 1569 | "a margin of 2.7" | "a factor of 2.7" (0.375 against 1.0 is a ratio) | word choice | mi |
| P7 | 545–546 | "One structural property of the plant bounds every claim made below and is worth stating before the results." | "One structural property of the plant bounds every claim made below." | tone (filler) | mi |
| P8 | 679 | "---the non-HVAC background load of Section 7 plus HVAC---" | Use commas or parentheses (one of only two em-dash pairs in the prose) | punctuation | mi |
| P9 | 679 | The paragraph says "stress-test instantiation" and then "enters only as a stress test of the formulation" | Delete the second (see R1) | redundancy | mi |
| P10 | 714–715 | "together they settle what a tariff structure can and cannot buy a scheduler here" | "together they fix what a tariff structure can offer a scheduler here" | tone | mi |
| P11 | 729–730 | "Third, the scope must be stated carefully, because…" | "Third, the proposition and its second consequence fail under different conditions." | tone (filler) | mi |
| P12 | 744 | "Two properties deserve precision: the marginal price is …, so the bill is … convex …; what makes the problem hard is …. The relevant property for this work is rather that…" | "Two properties matter. First, the marginal price is a non-decreasing step function, so the bill is convex and representable in a linear programme; the difficulty lies in the binary actions and the switching term, not the tariff. Second, the per-step cost rate depends on the accumulated state $E_{\mathrm{cum}}$, which takes the problem outside the SLHA class and requires $E_{\mathrm{cum}}$ in the agent state." | flow; announced structure not delivered | mi |
| P13 | 745–753 | "Because the bill depends on cumulative consumption alone … the same total costs the same whenever it is drawn. … moreover constant over the realised range." | Delete; it restates 714–728 (R2) | redundancy | MA (with R1–R2) |

### Section 4

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| O1 | 808 | "months repeat, the building is never demolished at a planning horizon" | "months repeat and no planning horizon ends the building's operation" | wording | mi |
| O2 | 833 | "and identifies precisely which features" | "and identifies which features" | tone | mi |
| O3 | 907–908 | "Insight (i) must be stated precisely: the rule layer is weaker…" | "The rule layer is weaker than the structural result that motivates insight (i)." | tone (filler) | mi |
| O4 | 915–920 | One sentence of about 70 words ("They impose no minimum dwell … with no guarantee.") | Split after "…no complete-cycle structure at all." Then: "The rule layer thus enforces O1 by construction and is consistent with Observation 2 without implementing it; complete cycles are left to the learned policy's switching term, with no guarantee." | flow | mi |
| O5 | 982 | "this is non-negotiable, and free-float drift below the band, which no action can prevent, is measured." | "this is a hard constraint; free-float drift below the band is measured (Definition 4)." | tone; redundancy (R3) | mi |
| O6 | 1024 | Corollary title of 21 words | "[Optimality of the rule-induced hysteresis under constant disturbance]" | style | mi |
| O7 | 1035–1036 | "hysteresis---continue the previous action throughout $\mathcal{F}$---attains" | "hysteresis (continue the previous action throughout $\mathcal{F}$) attains" | punctuation | mi |
| O8 | 1127 | "The corollary is tight, not general" | "The corollary is narrow" ("tight" has a technical meaning for bounds) | word choice | mi |

### Section 5 Controllers

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| M1 | 1292–1293 | "because Proposition 1 closes the question. It is not merely that pre-cooling fails to pay…" | "because Proposition 1 and Remark 2 rule it out under every cost model used here." Keep the leakage arithmetic (1296–1306) | tone (categorical); redundancy (R2) | mi |
| M2 | 1296–1297 | "The condition under which pre-cooling would become rational is worth stating, since it is a physical one, not a tariff one:" | "Pre-cooling would pay only under a physical condition, not a tariff one:" | tone (filler) | mi |
| M3 | 1307–1308, 1324–1325 | "free-float drift below the band, which no action can prevent, is measured, not excluded" / "which no action can prevent" | delete (R3) | redundancy | mi |
| M4 | 1397 | "used across Saudi residential buildings" | "common in Saudi residential buildings" | tone (overgeneralisation) | mi |
| M5 | 1398–1400 | "which is simultaneously the definition above and a representative hardware deadband for the split units in this stock" | "which matches a representative hardware deadband for split units in this stock" | wording | mi |
| M6 | 1438–1440 | "Close to $\lambda^\ast$ the result sits on a knife edge: … at any grid" | "Close to $\lambda^\ast$ the result is sensitive to $\lambda$: in Riyadh, neighbouring admissible multipliers give 24 h savings that differ by 1.4–1.8 points at both grid resolutions" | tone (idiom); unclear "at any grid" | mi |
| M7 | 1461, 1793, 1802, 2063; letter l.119 | "0.5 point", "0.1 point", "0.75 point" | "0.5 points", etc. (line 1777 already uses "points") | grammar (consistency) | mi |
| M8 | 1473, 1612 ff., 1915 ff. | Run-in heads set with `\emph{…}` while 454, 1575 and 1584 use `\paragraph{…}` | Use one style throughout | typography | mi |
| M9 | 1483 | "E1 (Section 9.2) keeps the simulator terminal" | "E1, the λ = 0 dynamic-programming optimum inside the rules (Section 9.2), keeps…" | term used before definition | mi |

### Sections 6–7

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| S1 | 1543 | "in preference to the older IWEC files" | delete (R7) | redundancy | mi |
| S2 | 1554 | "is adopted as a mid-range flat rate" | "is adopted as an illustrative flat rate" (it is not stated what range 0.12 is the middle of) | clarity | mi |
| S3 | 1555 | One sentence of about 80 words (ASHRAE 55 → Bienvenido → Krarti) | Split after "(… Section 10.4)." Then: "Bienvenido-Huertas et al. validate this use … . Its upper limit reflects Saudi practice: …" | flow | mi |
| S4 | 1564 | Section 7 opens without a link | Add the bridge sentence from the linkage table | linkage | mi |

### Section 8 Results (long sentences dense with numbers)

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| R-1 | 1800–1817 | One paragraph with about 45 numbers (bracket, B*, CLV, end temperatures, 89 rows) | Split into three: (a) the bracket and its width; (b) the energy-only B* and CLV against B_CLV; (c) end temperatures and the s_a ≤ B_a check. Move the end-of-window temperatures to the supplement. | flow | mi |
| R-2 | 1916 | "the share of compressor on-commands avoided" | "the share of on-commands avoided" | coherence (A2) | mi |
| R-3 | 1963–1983 | Setback paragraph of about 230 words with about 40 numbers | Break it before "Switching off at departure…" and before "The mechanism is…". Consider moving the vacation-week figures to the supplement. | flow | mi |
| R-4 | 2009–2013 | "In whole points, the perfect-forecast controller saves −4, 10†, 7, 15, 18 and 18 at … ($^\dagger$comfort matched by ceiling back-off b = 0.21, …)" | These are already in Table 3. Replace with "Savings rise with horizon up to 6 h and change by less than 3 points beyond it (Table 3)." | redundancy; number density | mi |
| R-5 | 2014–2015 | "and loses money in Riyadh (−3.9%)" | "and costs more than the baseline in Riyadh (−3.9%)" | tone (informal) | mi |
| R-6 | 2030–2050 | Capacity paragraph of about 250 words | Split before "The on-commands TUNED avoids…" and before "On a light plant…". → R6: "15.0, 5.8, 3.8 and 0.4 points" disagrees with Table 5 (F2 pooled Δs Riyadh +5.7) and with the CSVs (T21v3_riyadh.csv s_pooled_eq 18.2638 − T1v3_heldout.csv 12.5260 = 5.74). The letter (l.68) says 5.7. Use 5.7. | flow; consistency | mi |
| R-7 | 2047 | "On a light plant a commissioned thermostat cannot beat a 1 °C deadband" | "On the light plant tested (2,400 kJ/K) the commissioned thermostat does not beat a 1 °C deadband" (also update the quotation in letter l.72) | tone (categorical; Comment A) | mi |
| R-8 | 2057–2058 | "Near $\lambda^\ast$ the saving is knife-edged" | "Near $\lambda^\ast$ the saving is sensitive to λ" (R8) | tone | mi |
| R-9 | 2111–2112 | "neighbouring rooms stay within about a degree of each other" | → R6: reconcile with "mean spread 0.03–0.08 K" (2110). If the degree refers to instantaneous differences, say so. | consistency | mi |

### Section 9

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| N1 | 2145–2146 (Table 6) | "whole commercial bldg", "multi-zone resid." | "whole commercial building", "multi-zone residential" | style (abbreviation) | mi |
| N2 | 2195–2196 | "what the policies lacked is a one-step model of the plant, not anything a longer training run would supply" | "what the policies lacked is a one-step model of the plant; longer training was not tested and is not expected to supply it" | tone (claim beyond the evidence) | mi |
| N3 | 2198–2199 | "\emph{The price of the guarantee.} TUNED, free of the guards, against the guard hysteresis: the guard costs…" | "\emph{The price of the guarantee.} Compared with TUNED, which has no guard bands, the guard hysteresis costs…" | grammar (fragment) | mi |
| N4 | 2268–2269 | "and it is the most valuable field measurement for testing this study" | "measuring it is the field test most likely to confirm or overturn these results" | tone (promotional); wording | mi |

### Section 10 Discussion and Limitations

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| D1 | 2346 | No intro paragraph | Add the bridge sentence from the linkage table | linkage | mi |
| D2 | 2370–2383 | Telegraphic run-ins "Seeds: …; Weather: …; Calibration: …" inside running prose | Use full sentences or the `\emph{}` run-in style used elsewhere | flow / consistency | mi |
| D3 | 2402 | "Only the controller class is algorithmic. The actuation step moves it further:" | "Only the controller class is algorithmic. The actuation step moves the saving further:" | pronoun reference | mi |
| D4 | 2411 | "The narrower band is the correct one for this stock" | "The narrower band is appropriate for this stock" | tone (categorical) | mi |
| D5 | 2414–2416 | "In a separate run under the round-3 protocol (repository files T1v2_heldout_pol24.csv and T1v2_perwindow_pol24.csv)" | "In a separate run under an earlier version of the protocol (repository file …), not comparable in detail with the figures above," | internal jargon (the reader has no "round 3") | mi |
| D6 | 2440 and 2571 | "six measured choices" | "six modelling choices" (they are assumptions, not measurements) | word choice | mi |
| D7 | 2456–2457 | "and the model's on-command rate is an artefact of that interface, not a field prediction" | fine; keep. Make 125, 1916 and 2536 consistent with it (A2) | coherence | — |

### Section 11 Conclusions and back matter

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| C1 | 2536–2556 | One paragraph of about 250 words and about 40 numbers, repeating the abstract and stating TUNED's 12.5/13.6/12.4% twice | Split into "First, …" (on-commands, electricity, SAR), a new paragraph on dependence (capacity, step) and a sentence on the bracket. State each number once. Drop the bracketed hardware-grid figures here (they are in Limitations item 5). | redundancy; flow | MA (with R6) |
| C2 | 2536 | "of compressor on-commands" | "of on-commands" | coherence (A2) | mi |
| C3 | 2569–2570 | "cuts the thermostat's electricity by about 8–16% for one degree warmer" | "cuts the thermostat's electricity by about 8–16% when its setpoint is raised by one degree" | clarity | mi |
| C4 | 2593–2595 | "Conceptualisation, … Formal Analysis, … Writing – Original Draft, Writing – Review & Editing, Visualisation" | Use CRediT's fixed role names: "Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Writing – original draft, Writing – review & editing, Visualization" | style (taxonomy names) | mi |
| C5 | 2601 | "The author would like to acknowledge the Deanship…" | "The author acknowledges the Deanship … for funding this work (grant no. …)." | tone (wordiness) | mi |
| C6 | 448, 1292 | "toward" | "towards" (UK variety; the supplement at l.189 already uses "towards") | variety | mi |

### Supplement

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| SP1 | S1 l.49–51 | "Shi et al. … Wang et al." with no citation | Add the reference numbers or a short reference list | referencing | mi |
| SP2 | S1 l.74–77 | "fixed deadband (Table S1(a)): TUNED saves about 25% … (main text, Actuation Step)." | "…fixed deadband (Table S1(a)). TUNED saves about 25% … (main text, Section 9.3)." | punctuation (two colons in one sentence); cross-reference | mi |
| SP3 | S1 l.120 | "the room-air capacity violates it in all of them" | "the air-only capacity of 77.2 kJ/K violates it in all of them" | linkage | mi |
| SP4 | Table S2 l.168 | "$7.8^{b}$" | Define b in the caption | caption | mi |
| SP5 | Table S2 l.170 | "$12.4$--$12.4$" | "12.4 (both)" | typography | mi |
| SP6 | Table S2 l.178 | "--- , $0.21$" | "---, $0.21$" | spacing | mi |
| SP7 | S5 l.231–233 | "Taif 2013 …, 2018 …, 2017 …" then "Taif's mild years 2013 and 2018" | → R6. If the order is hottest, median, mildest, then 2013 is the hottest, not a mild year. Correct either the order or the sentence (main l.2376 says "two mildest years"). | consistency | mi |

### Response letter

| # | Location | Original | Correction | Rule | Sev. |
|---|---|---|---|---|---|
| RL1 | l.212 | "Repetition. Each disclosure is made once in full, with cross-references elsewhere." | Either carry out R1–R4, or soften to "Repetition was reduced; the main disclosures are stated in full once and summarised elsewhere." As it stands, the claim is not true (R1: 9 occurrences; R2: 6). | truthfulness (Comment A) | MA |
| RL2 | l.27 | "Every result is read first as compressor on-commands avoided" | "…as on-commands avoided" (l.244 says that the manuscript no longer equates the two) | coherence | mi |
| RL3 | l.68 | "its margin over TUNED is 15.0, 5.7, 3.8 and 0.4 points" | Correct as it stands (CSV: 5.74). The manuscript (l.2035) says 5.8 and should be changed to 5.7. → R6 | consistency | mi |
| RL4 | l.72 | Quotes "cannot beat a 1 °C deadband" | Update the quotation if R-7 is applied | coherence | mi |
| RL5 | l.119 | "at most 0.5 point" | "at most 0.5 points" | grammar | mi |
| RL6 | l.258 | "(Section 17)" | Consistent with the manuscript (Data and Code Availability is numbered 17). Consider leaving the back-matter declarations unnumbered and citing "Data and Code Availability" by name. | style | mi |
| RL7 | l.216 | "Comment A … Changes in the manuscript: throughout." | After the edits above, list concrete examples: the deleted duplicates, the split abstract sentences, and the softened phrases (I3, O5, M1, R-7, N2, N4, D4) | completeness of the response | mi |

Checked and fine in the letter: section, table and remark numbers (Sections 3.1–11, Tables 1–8, Remarks 1–5); the count of thirteen limitation items; the quotations from Sections 7, 9.3 and 10.2 (verbatim); the removal of "unaffected", "lower bound", "actual Saudi step-wise tariff", "NP-hard" and "significantly" (grep: none in main.tex or supplement.tex); no doubled full stops (grep).

## 5. Tone profile (main.tex)

- AI-typical or inflated words. Only a few survive:
  - "precisely" ×3
  - "essential" ×2 (one is justified: "the corollary is false without it")
  - "non-negotiable" ×1
  - "closes the question" ×1
  - "worth stating" ×2
  - "deserve precision" ×1
  - "the correct one" ×1
  - "knife edge/knife-edged" ×3
  - "settle/settled" ×2

  None of the following appear: "novel", "crucial", "comprehensive", "leverage", "seamless", "significantly", "Furthermore", "Additionally".
- Connector-led sentences: "Moreover" ×1, used mid-sentence. Low.
- Em dashes in prose: 2 pairs (lines 679 and 1035–1036). The table "---" entries are fine.
- Filler or meta phrases: about 7 ("is worth stating", "must be stated carefully/precisely", "the relationship is best stated directly", "The distinction is not academic").
- Spelling variety: British -ise throughout (about 80 forms). Two US forms: "toward" ×2 in prose. CRediT role names should take the taxonomy's US spelling. The response letter's US forms occur only inside journal quotations.
- Rhythm: the prose favours long, semicolon-chained sentences, and in the results these carry 3-city number triplets. Repeated paragraph openers flagged by the audit (I228–234, "The …" ×3) are acceptable.
- Hyphenation pairs flagged by the audit (A21–A59) are mostly the correct compound-modifier versus noun use ("single-zone analysis" / "the single zone"). Real inconsistencies: "stepwise" in the label only (fine); "step-size" (446) against "step size" (450) as nouns → "step size".

## 6. Paper Quality Standard checklist (R11 items)

| ID | Item | Status |
|---|---|---|
| Q1.1 | Sections and subsections linked both ways | PARTIAL: Sections 4, 7 and 10 lack openers; Section 2's announced structure does not match its subsections; Observation 2 is cited before it is stated |
| Q1.2 | Roadmap matches the structure | PASS (lines 209–218; fix "its" → "their"). The audit's D1 MAJOR is a false positive. |
| Q6.1 | Formal tone, no contractions | PASS, apart from the informal idioms listed above |
| Q6.2 | No duplication or redundancy | FAIL: R1, R2, R6 |
| Q6.4 | Writing-quality checklist applied | PARTIAL |
| Q6.5 | No typos or grammar errors; one variety | PASS with minor items (point/points, agreement at 217, "toward") |
| Q6.6 | Natural language, no AI tone | PASS with minor items |

## 7. Verdict (language and coherence)

**NOT READY**, but close: no new analysis is needed, only about half a day of editing. Under the review standard, MAJOR language or coherence findings block acceptance. The blocking findings are the structural repetition of the tariff and pre-cooling disclosures (R1/R2 → P13), the abstract and conclusions that are dense with numbers and largely repeat each other (A4, C1/R6), and the letter's untrue claim that repetition was removed (RL1). Once these are fixed, together with the eight categorical or promotional phrases, Comment A is met.

Findings by severity: **CRITICAL 0 · MAJOR 4** (R1/R2+P13 redundancy, A4 abstract flow, C1/R6 conclusions, RL1 letter claim) **· MINOR 78** (line edits, linkage and supplement items).

Items for R6 (consistency), not analysed here:
- 5.8 against 5.7 (l.2035 against Table 5 and the CSVs).
- The order of the Taif actual years (S5).
- "Within about a degree" against a spread of 0.03–0.08 K (l.2112).
- "Climate Zone 2" (l.238) against "Climate Zone A/B" (l.1553).
- Python 3.13.18 / NumPy 2.5.3 version strings (l.1567).
- Footnote b undefined in Table S2.
