# Reviewers' Report — final verification panel (round 4)

**Manuscript:** *Optimising Binary HVAC Switching in Saudi Residential Buildings with Model Predictive Control and Rule-Constrained PPO* (JKSU-ES, major revision)
**Date:** 13 November 2026
**Panel:** seven independent reviewers (separate agents; none saw the drafting): Editor-in-Chief (EIC), Methodology (R1), Building Simulation (R4), Control & HVAC (R5), Consistency (R6), Language & Coherence (R11), Devil's Advocate (DA). Full reports: `review_round4/final_panel2/*_report.md`.

## 1. Verdicts

| Reviewer | Verdict | Critical | Major | Minor |
|---|---|---|---|---|
| EIC | Ready after minor fixes | 0 | 3 | 11 |
| R1 Methodology | Not ready (text only) | 0 | 4 | 11 |
| R4 Building simulation | Not ready (text only) | 0 | 2 | 13 |
| R5 Control & HVAC | Ready after minor fixes | 0 | 4 | 10 |
| R6 Consistency | Not ready (text only) | 0 | 7 | 15 |
| R11 Language & coherence | Not ready (editing only) | 0 | 3 | 79 |
| DA Devil's advocate | Not ready (wording) | 0 | 6 | 9 |

**Editorial decision:** minor revision before submission. No reviewer found an error in any result: every number checked (several hundred, across all reports) matches the stamped results files, the 188-invariant gate passes, and no placeholder remains. All major findings are wording, framing, disclosure or layout. Every major and critical item of panel 1 is closed except two (decision time, PPO training-length wording), both addressed below.

## 2. Journal comments — closure (EIC)

| Comment | Status |
|---|---|
| 1 Validation | Partially (validation honestly declined; not in the journal's unresolved list) |
| 2 Thermal capacity | Fully (justified alternative to the suggested wording) |
| 3 Protocol and dates | Fully (dates match the code) |
| 4 Baselines | Fully |
| 5 Formatting | Fully |
| 6 Tariff | Fully in the manuscript; **letter inaccurate** (see M-A) |
| 7 Title / multi-zone | Fully |
| 8 Time step | Fully |
| 9 Charge per on-command | Fully |
| A Language | Partially → fully after the fixes below |
| Editor's instruction | Fully after M-A |

## 3. Consensus major findings (and the fix decided)

| # | Finding | Raised by | Fix |
|---|---|---|---|
| M-A | §10.3 still says the tariff moves the saving "by 7 across the three epochs"; Table 7(a) now has two rows (0.9 pt). Letter (Comment 6) quotes a deleted "historical/stress-test" sentence, "three tariff epochs" and 18.6 %; Supplement S1 mentions "2,000 kWh tier widths". | R1, R4, R5, R6, R11, EIC | Rewrite §10.3 to the two in-force schedules; correct the letter and S1. |
| M-B | Letter overclaims: says the longer-training claim was removed and conclusions no longer repeat the abstract's figures. | R6, R11, EIC, R5 | Make the letter describe the manuscript exactly. |
| M-C | PPO training-length diagnostic over-read ("almost nothing left to gain"): hold is 0.4–2.3 % above the in-rule optimum; PPO trains on six fixed weeks. | R1, R5, DA | Soften to what the data show; state the six-week training set and the E1 margin. |
| M-D | The paper's own 3-point rule: "PPO falls below hold in Taif", "slightly less than the comparator at 30 min" and three smaller cases stated as directions though < 3 pt. | R1 | Reword as "not resolved" where < 3 pt (abstract, C4, Conclusions, captions, letter). |
| M-E | Green Riyadh paragraph: TUNED's 12.8–13.6 % there is a raw (not comfort-matched) saving; "add rather than compete" not shown; no internal gains inflates the cut; source says "temperatures". | R4, DA | Add caveats; drop "add rather than compete"; describe as first-order. |
| M-F | Keyword "CO2 reduction" unsupported. | DA, R4, R5, EIC | **Author decision:** replaced by "energy efficiency". |
| M-G | Title implies MPC and PPO optimise the switching. | R5, DA | **Author decision:** title kept. |
| M-H | Springer PDF overflows: Fig. 4 over the right column (p. 24), Eq. 20 (p. 14), Corollary 1 step 3 (p. 12); Fig. 3 into the margin. Author also reports overlaps. | EIC, author | Fix every figure/equation width; check every page visually. |
| M-I | Double-anonymous review: manuscript names the author, affiliation, funder and repository. | EIC | **Author decision:** produce a blinded manuscript; keep the full copy. |
| M-J | Ablation table (Table 6) does not meet the ablation standard (no removed-component/Δ columns). | R1 | Rebuild from existing results with component and Δ-vs-TUNED columns. |
| M-K | Remark 1 states the capacity-bias direction backwards relative to §8.3/§10.4/Conclusions. | R6, R1 | Make all four agree (reference value lies above the effective one, which favours TUNED). |
| M-L | §10.3 says the bound covers "coupled rooms"; it is single-zone. | R6 | Correct. |
| M-M | §3.1 calls U_win = 2.8 "the SBC prescriptive maximum" and §6.2 "consistent with double glazing". | R6 | Correct to what the code states. |
| M-N | Fig. 1 caption "Corollary … rests on" this geometry; the text says otherwise. | R6 | Align caption with text. |
| M-O | Decision time measured but unreported (panel-1 open item). | R5 | Report from a stamped timing run, or state it is not reported. |
| M-P | "Hard comfort by construction" holds only at the nominal capacity; cold-guard derivation omits the envelope term (Taif 0.4014 K > 0.40). | DA, R5 | Qualify "under the nominal plant"; state the realised record (zero). |
| M-Q | Abstract: closing sentence presents a model identity as a finding; the 0.1 °C hardware caveat is missing; four sentences need repair. | DA, R11 | Repair within ≤ 250 words, keeping the author's few-numbers rule. |

## 4. Selected minor findings
Fig. 3 caption should say the week is the hottest held-out week and TUNED's weakest; Fig. 4 caption ratio mixes scoring rules; THERM/TUNED used before definition; four names for the PPO arm; "switch-on" vs "on-command"; F1–F4 families not assigned in §7; §3 title vs roadmap; internal drafting comments in the .tex source; repetition still at 3–5 places (on-command charge, capacity caveat, PPO-hold result); AI-use declaration required by the guidelines (**author decision: not declared**).

## 5. References
59 entries. 47 match Crossref on title, every author, year, journal, volume and pages after correcting the full given names of co-authors in 13 entries (initials were right; given names were wrong) and two venue names. The 11 without a DOI (standards, tariff sources, SGI, Green Riyadh, TMYx, Stable-Baselines3, Pang & Liu 2011) were each verified at the source. Bertsekas (2020) is a book; Crossref's match is a review of it (false positive).

## 6. Fixes applied (manuscript editor, 13 November)

| # | Status | Note |
|---|---|---|
| M-A | Fixed | §10.3 two schedules (0.9 pt), S1 boundary, letter Comment 6 rewritten |
| M-B | Fixed | Letter describes the manuscript exactly; quotations re-checked |
| M-C | Fixed | Six-week training set, E1 bound, "not tested" (§5.4, §9.2, Limitations, letter) |
| M-D | Fixed | "Not resolved" wording in abstract, C4, §8–§9, Conclusions, Fig. 4, letter |
| M-E | Fixed | Caveats added, "add rather than compete" dropped, first-order upper estimate |
| M-F | Fixed | Keyword "energy efficiency" |
| M-G | Not applied | Author decision: title kept |
| M-H | Fixed | 0 Overfull boxes in all builds; all float/equation pages of main_sn.pdf inspected |
| M-I | Fixed | make_blind.py → main_sn_blind.pdf, supplement_blind.pdf; only the self-citation in the reference list remains |
| M-J | Fixed (partly against the full Q2.4 spec) | Table 6 rebuilt with component and Δ-vs-TUNED columns; no mean ± std/bold (ranges kept) |
| M-K | Fixed | Remark 1 direction aligned with §8.3, §10.4, Conclusions |
| M-L | Fixed | Single-zone bound vs distributed MPC |
| M-M | Fixed | U_win "assumed, double glazing" as in the code |
| M-N | Fixed | fig_leap.tex caption; same change noted for rbrl/gen_figs.py |
| M-O | Fixed by statement | No stamped timing file; §9.4 and letter say decision time is not reported and why |
| M-P | Fixed | "Under the nominal plant"; envelope-term and capacity limits stated |
| M-Q | Fixed | Abstract 244 words with 0.1 °C caveat and model-identity wording |
| AI statement | Removed | Author decision: "Declaration of Generative AI Use" section deleted from all builds |
