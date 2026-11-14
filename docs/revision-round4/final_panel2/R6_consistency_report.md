# Reviewer R6: Consistency & Contradictions (final panel 2, round 4)

**Reviewer role:** R6, Consistency & Contradiction reviewer (agents/consistency_reviewer_agent.md), re-review mode.
**Material:** main.tex (2,718 lines; main.pdf, main_sn.pdf), supplement.tex (+pdf), RESPONSE_LETTER.md, audit_report.md, reference_report.md. Results: /home/claude/rbrl_p12/results (CSVs, gate_p12.log). PROVENANCE.md was used only to locate files. Every value below was recomputed from the CSV itself.

**Recommendation (consistency only): NOT READY.** There are 0 CRITICAL and 7 MAJOR findings. All are text-only fixes and none needs a rerun. Every headline number (abstract, Tables 3, 4, 6, 7, 8, Figs. 3–5, Tables S1–S7) matches the result files. The remaining problems are statements that contradict other statements, plus two places where the response letter does not describe the manuscript truthfully.

---

## 1. Coverage statement

- **Read in full:** abstract, keywords, §1–§11, declarations and data statement; Tables 1–8; Figs. 1–5 (all generated .tex, plotted coordinates and captions); Algorithm 1; Eqs. 1–17 and the unnumbered displays; Remarks 1–5, Proposition 1, Corollary 1 with proof, Observations 1–2; Supplement S1–S10 (Tables S1–S7, S-MZ); the response letter in full. The Springer build (main_sn.tex) was diffed against main.tex. Abstract and numbers are identical; only one LaTeX comment differs.
- **Fact ledger:** about 520 checkable entries. These comprise about 430 numbers, 40 settings, 20 names and counts, 15 notation items, and about 15 claims, promises and limitations each.
- **Number verification:** about 450 printed values compared directly with the CSVs (≫ the 80 required). Coverage:
  - **Abstract:** every number (22–24%, 12.4–13.6%, 4–6 points, about 25%, below THERM at 30 min, 17–21%).
  - **Table 3:** every cell of every row (`T1v3_heldout`, `T21v3_{c}`, `T21v3_pers_{c}`, `T16v3_r*`, `T_D1_latch_*`, `T_D1_ppo_*`, `rbrl_ppo5_v3_*`, `T17v3_*`, `T17v2_*`, `T17v3_ruled_*`), including fit-status and † marks against `fit_status` and `knob`.
  - **Table 4:**
    - on-command and energy columns for all 7 arms × 3 cities;
    - SAR values recomputed for TUNED Riyadh: 184·[c·0.9298 − 0.18·0.0093] = 4 / 19 / 25.
  - **Table 6:** all 27 cells.
  - **Table 7:**
    - (a)–(d), every cell (`T5v3_switchcost_tuned`, `T7v3_deadband`, `T1v3_heldout_cth*`, `T21v3_riyadh_cth*`, `T4v3_bound`, `T5v3_bound`);
    - the on-command share column, recomputed from fs and J.
  - **Table 8:** all cells (`T2v3_timestep`, `T17v3_*_dt5/dt30/cth7200`).
  - **Fig. 3:** checked against `T35_day_traces`:
    - 10/8/7 on-commands in the two days and 34/27/23 in the week;
    - outdoor range 31.6–44.5 °C;
    - MPC range 22.00–23.99 °C.
  - **Fig. 4:** all 15 bar values, both bracket ends, "70–74%", "4.4–5.7" and "−1.6 to 1.0".
  - **Fig. 5:** all 9 plotted points.
  - **Text values:**
    - §5.4 E1 and hold-gap figures (`E1v3_hold_dp`, `T33_ppo_hold_gap`);
    - E2 (`rbrl_e2_v3_riyadh`) and the no-rules seed;
    - λ/λ\* values;
    - grid refinement (`T21v3_conv_*`);
    - the bound grid series and slacks (`T17v3_*` `bound_rel*`/`bound_unrel*`);
    - CLV and B_CLV;
    - setback and MANUAL (`T28v3_*`);
    - multi-zone (`T31_mz_*`);
    - Green Riyadh (`T34`), actual years (`T23v3`), orientation (`T24v3`), setpoint slope (`T32`), start-up energy (`T25v3`);
    - F1–F4 (`T20v3_paired_stats`);
    - B_a, the 89 rows and "62–65%" (`T17v3_Ba`);
    - vacation weeks.
  - **Supplement:** S1, S2 (every row incl. `T1v3_sens`, `T21v3_ls*`), S3, S4 (every row), S5, S6 evidence column, S7 (all 36 HL/CI/p cells), S-MZ.
- **Gate:** gate_p12.log ends "GATE PASSED – all 188 invariants hold", as the data statement says.
- **Placeholders:** none in main.pdf, main_sn.pdf or supplement.pdf. `\pend` is defined but never used.

**Result of the number check:** no printed result disagrees with its CSV, apart from the rounding items listed under MINOR (m3, m4, m6).

---

## 2. Contradiction ledger

### MAJOR

| # | Type | Severity | Location A (quote) | Location B (quote) | Location C… | Likely correct | Fix and all locations to update |
|---|---|---|---|---|---|---|---|
| M1 | C-LIM / C-NUM (direction) | MAJOR | **Remark 1, l.472–475:** "the reference value probably lies above the effective one, towards the capacities at which the tuned thermostat **gains least**" | **Abstract, l.133–134:** "thermal capacity, whose reference value probably **favours** the tuned thermostat". **§8.3, l.2012–2015:** "the reference results lean towards the end favourable to TUNED" | **§10.4, l.2502–2505**, **Conclusions, l.2608–2610**, **Table S6, row "Reference capacity"** ("probably overstates") and the letter (l.31, 71, 77) all agree with B. | **B, from the data.** TUNED's saving *rises* with capacity: −2.8 / 12.5 / 16.0 / 15.8% at 2,400 / 4,800 / 7,200 / 9,600 kJ/K (`T1v3_heldout_cth*`, s_pooled_eq 12.526, 16.016, 15.815; cth2400 −2.778). MPC's margin over TUNED *falls*: 15.0 / 5.7 / 3.8 / 0.4 (`T21v3_riyadh_cth*` 12.245, 18.264, 19.802, 16.168). A reference that lies above the effective capacity sits where TUNED gains **most** and MPC's lead is smallest. | Remark 1: replace "towards the capacities at which the tuned thermostat gains least" with "towards the capacities at which the tuned thermostat gains most and MPC's margin over it is smallest, so the reference results probably favour the tuned thermostat". This was the round-1 R4 M4 item, and it is now closed everywhere except here. |
| M2 | C-TAB-TXT / C-NUM | MAJOR | **§10.3, l.2413–2416:** "...the charge per on-command by $7$ across the derived range and **the tariff by $7$ across the three epochs** (Table~\ref{tab:sensitivity})". **l.2436–2438:** "the on-commands TUNED avoids are the same under **all three epochs** while the percentage falls as the bill grows (Section 8.2). A percentage quoted against one tariff epoch..." | **Table 7(a), l.2232–2234:** only **two** tariff rows: 0.18 (in force) 12.5 and 0.21 (2027) 11.6, so the printed tariff effect is **0.9** points. **Remark 3, l.738–739:** "TUNED and the bound are repeated at the announced 2027 rate". **§8.2** gives only the 2027 rate. | **Letter, Comment 6, l.149:** "the pre-2018 four-tier schedule has been **removed from the analysis altogether**". But l.151 of the letter says "under all three epochs while its cost saving is **18.6**, 12.5 and 11.6%", and l.157 cites "Table 7(a) (three tariff epochs)". | **The table.** "7" equals 18.584 − 11.650. It uses the `tariff=historical` row of `T1v3_heldout.csv` (TUNED s 18.58 / 19.88 / 17.98), which the manuscript no longer prints anywhere. The `fig_tariff` input is also commented out (l.2410–2411). | Choose one option and apply it everywhere. **(a)** Write "the tariff by about $1$ point between the schedule in force and the 2027 schedule" and "the same under both schedules" (l.2416, l.2436–2437). Then drop the 18.6 and "three epochs" from the letter (l.151, l.157). **(b)** Restore the pre-2018 row in Table 7(a), labelled as a withdrawn historical stress test. In that case the letter's "removed from the analysis altogether" must be changed. |
| M3 | C-DECL (letter vs manuscript) | MAJOR | **Letter, Comment 6, "Changes in the manuscript", l.154:** "Section 3.4 'Electricity Cost Models': Model S '**is a historical schedule, no longer the tariff in force, and it is used here as a stress-test instantiation of the step-wise cost class**...'" | **main.tex l.655:** "Model~S ... is instantiated with the Saudi residential tariff **in force since January~2018**". The quoted sentence does not occur anywhere in main.tex or supplement.tex (grep "stress", "historical schedule": no hit). | Letter l.149 ("removed altogether") vs l.151 (18.6%) vs l.157 ("three tariff epochs"); see M2. | The manuscript (Model S is the in-force tariff). | Delete the false quotation in letter l.154 and quote l.655 instead. Make l.149–157 consistent with whichever option of M2 is chosen. This is on Comment 6, one of the four comments the journal marked unresolved, so the letter must be exact here. |
| M4 | C-CLAIM / C-LIM | MAJOR | **§10.3, l.2443–2446:** "MPC and the clairvoyant bound already choose the whole temperature path inside the band at every step, **coupled rooms included**, and neither pre-cools" | **§9.4, l.2352–2354:** "That is why the bracket of Section 8.1 is a **single-zone result** and why the multi-zone study **has no bound**." **§8.4, l.2065–2068:** the multi-zone controller is "a non-cooperative distributed MPC ... with no optimality guarantee and no bound, because the joint dynamic programme is intractable". | **§10.4, l.2573–2574:** "the multi-zone study is one city, independent units, ... and no bound". **Table S-MZ caption:** "no bound exists for these layouts". | B and C. No bound or clairvoyant schedule exists for coupled rooms, and the multi-zone MPC optimises each room against delayed neighbour plans rather than the joint path. | Replace with: "In the single zone, MPC and the clairvoyant bound already choose the whole temperature path inside the band at every step; in the coupled dwellings the distributed MPC does so room by room. None of them pre-cools." |
| M5 | C-SET / C-CITE (code compliance) | MAJOR | **§3.1, l.458:** "**The two transmittances are at the SBC 2018 prescriptive maximum** of $U_{\mathrm{wall}}=0.45$ and $U_{\mathrm{win}}=2.8$". **Table 2, l.582:** "$U_{\mathrm{win}}$ ... (SBC 2018 prescriptive max) 2.8". | **§6.2, l.1485:** "SBC 2018 mandates opaque-wall U-value ≤0.45 ... and window SHGC ≤0.25 ... Table 2 meets **both**: $U_{\mathrm{wall}}=0.45$ and SHGC = 0.25 exactly, with $U_{\mathrm{win}}=2.8$ **consistent with double glazing**." This section lists no window-U requirement. | — | Cannot be decided from the paper. The two sections disagree on whether a window U-value of 2.8 is a code limit. | Check the SBC 602 (2018) residential fenestration U-factor table for the relevant zones, then do one of two things. **If 2.8 is the code maximum:** add it to §6.2's list of mandated values, so that three values are met exactly. **If it is not:** relabel Table 2 as "assumed (double glazing)" and rewrite l.458 so that only U_wall is said to be at the maximum. In either case, state the climate zone for Taif, which §6.2 omits; §6.2 names only Zone A (Jeddah) and Zone B (Riyadh). |
| M6 | C-DECL (letter vs manuscript) | MAJOR | **Letter, Comment A, l.218:** "the claim that a longer training run would not help (**now 'longer training was not tested'**)". **Letter, editor section, l.245:** "the earlier statement that a longer training run would not help **is removed**". | **main.tex §5.4, l.1281–1282:** "so a longer run on the same weeks has **almost nothing left to gain**". **§10.4, l.2566–2568:** "longer training is not run, but ... the trained policies already sit close to the hold policy's training cost ..., so it **has little to gain**". The phrase "longer training was not tested" occurs nowhere. | The letter's own transcript of Limitation 12 (l.279) repeats "so it has little to gain", which contradicts its l.218 and l.245. | **The manuscript.** Its claim is evidenced: `T33_ppo_hold_gap` Taif tuning gaps are −0.04, 0.047, 0.0 and 1.44%, and held-out gaps 0.52–2.50%, as printed. | Fix the letter, not the paper. Replace l.218 and l.245 with: "the claim is now restricted to the tuning weeks and supported by the gap to the hold policy there (within 0.05% for three of the four Taif seeds that fall short, 1.4% for the fourth)". |
| M7 | C-CLAIM (figure caption vs text) | MAJOR | **Fig. 1 caption, fig_leap.tex l.59–60:** "This geometry is what Corollary~\ref{cor:rules_sufficient} **rests on**." | **main.tex l.978–979** (Observation 2): "The corollary below **does not rely on it**." **Corollary proof, Step 1, l.1016–1017:** "No merging argument is needed." | — | B. The proof uses only the bounded widths $w_k\le W$ under constant drift, not the complete-cycle structure. | Caption: "Corollary 1 does not depend on this structure; it uses only the constant-drift widths." Or drop the sentence. Also change "switch-ons per day" to "on-commands per day" in the same caption (l.56), to match the paper's terminology. |

### MINOR

| # | Type | Location(s) and quote | Problem and evidence | Fix |
|---|---|---|---|---|
| m1 | C-SET | **Remark 1, l.516–518:** "At 30 min, and equally at 2,400 kJ/K and 15 min, the upper limit of (8) is $0.99$ °C and fails narrowly". Repeated: Table 7 caption l.2221–2222; §9.3 l.2288–2289; Table 8 caption l.2306–2307; S1 l.63–65 and l.81–82. Letter l.181 quotes the un-centred formula with "0.375 to 1.25 °C at 15 min". | Remark 1 applies the *centred* tightening (l.499–503) to obtain 1.25 at 15 min: un-centred it would be 2 − 0.375 − 0.129 = 1.50. It also applies the centred form to THERM at 1 h ("14,400 ... for a deadband centred on the band as THERM's is"). At 30 min it switches to the un-centred 0.99. The centred limit for THERM there is 2·min(1 − 0.75, 1 − 0.258) = **0.50** °C, so by the paper's own rule THERM fails by 0.5 K, not "narrowly". The letter's formula, read literally, does not give 1.25. | State which form is meant at each step. Either say "by the un-centred form (0.99 °C); by the centred form that applies to THERM, 0.50 °C", or adopt one form throughout. Consider reporting THERM's commanded under-temperature at 30 min, since its cooling steps can overshoot 22.5 by up to 0.75 K. |
| m2 | C-NUM (scope) | **Conclusions, l.2593–2594:** "avoids $22$–$24\%$ of on-commands **in every held-out window**" | Per window, TUNED avoids 18.2–27.9% (`T1v3_perwindow`, 1 − fs_arm/fs_eq; e.g. Taif 18.2, 18.7; Jeddah 27.9). 22–24% is the pooled figure. | "avoids $22$–$24\%$ of on-commands pooled, and fewer on-commands in every held-out window". |
| m3 | C-NUM rounding | **Conclusions, l.2599:** "on a 0.1 °C setpoint grid it avoids $11$–$15\%$ of on-commands" | `T1v3_sens` hw_0.1K start_sav_eq is 10.506 / 13.178 / 14.714. §8.2 prints 10.5, 13.2, 14.7; 10.5 does not round to 11. | Print "$10.5$–$14.7\%$" or "about $10$–$15\%$". |
| m4 | C-NUM rounding | **§8.3, l.2021:** "$13.094$" | `T21v3_pers_riyadh` lam_over_lam_star = 13.094603, so the value is 13.095 at three decimals (truncated rather than rounded). | Print 13.095. |
| m5 | C-NUM | **§3.1, l.458:** infiltration "contributing $10.77$–$12.72$ W/K (**slightly more than one face of fabric**)" | One face is 11.90 W/K. Riyadh (11.85) and Taif (10.77) are *less*; only Jeddah (12.72) is more. | "(about one face of fabric)". |
| m6 | C-NUM rounding rule | **Table S5** B_a and **§8.1, l.1752–1753** B_CLV (19.6 / 19.4 / 20.2) | B\* is "rounded up to 0.1" (l.1723), and PROVENANCE says B_a is rounded outward. Table S5 nevertheless uses nearest rounding. From `T17v3_Ba`: TUNED Riyadh 19.746 → printed 19.7 (up: 19.8); Jeddah 20.209 → 20.2 (20.3); CLV Jeddah B_CLV 19.411 → 19.4 (19.5); Taif 20.227 → 20.2 (20.3). No inequality is affected. | Round B_a and B_CLV up, as for B\*, or state in the Table S5 caption that they are rounded to nearest. |
| m7 | C-NAME | **Supplement S5, l.249–250:** "In Taif's **mild years 2013 and 2018**" | Earlier in the same paragraph the order is "mildest, median, hottest" = 2013 (CDD 712.7), 2018 (883.3), 2017 (1,034.4) (`T23v3_amy_spread`). That ordering is correct but not chronological. 2018 is the *median* year, not a "mild" one. The main text (l.2391) says "two milder years", which is acceptable. The free-float values 6.7–6.9 and 2.6–3.0 °C·h match. | "In Taif's mildest (2013) and median (2018) years ...". Add "(ordered by CDD, not by date)" after the year list. |
| m8 | C-SET (unflagged fallback) | **§8.4, l.2073–2075; Conclusions, l.2634–2635:** MPC-MZ "saves 16.0, 15.9 and 15.7% (15.8, 16.1 and 16.1% at 35 W/K)" | Both 1×2 cells were fitted at the 0.10 K fallback (Table S-MZ 16.0^b, 15.8^b; `T31_mz_mpc_riyadh_1x2_*` fit_status pooled_0.10). The body text does not say so, although it flags every other fallback. | Add "(the $1\times2$ cells at the $0.10\,$K fallback)". |
| m9 | C-CITE (check) | **§6.1, l.1454:** "Jeddah (**BSh**, ...)". **l.1461:** "Taif (BSh ...)". | Jeddah is conventionally Köppen BWh (hot desert), not BSh, and "hot-humid" is the cited classification. Taif is usually given as BWh or BSh. This cannot be resolved from the paper; flagged for the integrity check. | Verify both against Köppen–Geiger (e.g. Beck et al. 2018) and correct if needed. |
| m10 | C-CLAIM (keyword) | **Keywords, l.148:** "CO$_2$ reduction" | §10.3, l.2456–2459: "At matched comfort the controllers ... change on-commands, not electricity, so their contribution to emission cuts is indirect". A CO₂ keyword overstates what the paper shows. | Replace with e.g. "on/off actuation" or "thermostat commissioning". |
| m11 | C-NAME | **§2.1, l.237–238:** "Climate Zone 2" (Olawale). **§6.2, l.1485:** "Climate Zone A (Jeddah) and Zone B (Riyadh)". | These are two zoning schemes with no mapping between them, and Taif's zone is not stated (see M5). | Give the SBC zone for all three cities and, if needed, map Olawale's "Zone 2". |
| m12 | C-NUM | **Supplement Table S7, Jeddah F3:** "[$-0.0$, $+1.9$]" | hl_lo = −0.0396 (`T20v3_paired_stats`). "−0.0" hides the fact that the interval only just includes zero, which the text relies on (l.1962–1964). | Print "$-0.04$". |
| m13 | Typesetting | **main_sn.pdf, references [Mousa2016] and [Mousa2017]:** "IEEE, ??? (2016)", "Springer, ??? (2017)" | The publisher address field is missing for the sn-mathphys style. main.pdf (elsarticle) is clean. | Add `address` to both bib entries, or drop `publisher` for the Springer build. |
| m14 | Source hygiene | main.tex comments, e.g. l.88–103 (title decision tree), l.117–119, l.2054–2055 ("Gate ... by Sat 14 Nov 20:00"), l.2410; supplement l.27, l.409–410 | These do not print, but they will be visible if the LaTeX source is uploaded to the journal. | Strip internal comments before submission. |
| m15 | Repository doc vs paper | `pubrepo_new/docs/PROVENANCE.md` §1–§2 | It still calls the paired-statistics table "Supplementary Table S8" and `fig_timestep` "Fig. 4"; the paper prints S7 and Fig. 5. The data statement points readers to the repository. | Regenerate PROVENANCE.md with the current numbering. |

### Explained differences checked and *not* reported

These were checked and found to be explained or correct:

- **F2 margins:** 5.7 / 4.4 / 4.5 (Fig. 4, Table S7) against the Hodges–Lehmann estimates 6.0 / 4.2 / 4.6 (§8.3). Different statistics, both labelled.
- **"D1 within 1.4 points of TUNED":** 13.951 − 12.526 = 1.42 from unrounded values. The rounded cells give 1.5, but the rounding rule is declared.
- **"5.5, 3.4, 6.2" persistence costs** (unrounded 5.53 / 3.42 / 6.18). The rounded cells give 5.6 / 3.5 / 6.1; the rule is declared.
- **B\* 19.9 (Jeddah) against the grid list "19.8":** 19.827 rounded up gives 19.9, which is stated.
- **Bound slacks:** 0.47 / 0.42 / 0.75.
- **Abstract "22–24%" from 21.7:** within normal rounding.
- **Fig. 1 "2.83 on-commands/day":** 4.10 × (1 − 0.311).
- **Running example "75% more":** 0.0744 / 0.0425 = 1.75.
- **Window dates against zero-based day 121:** correct; this closes EIC F1.

---

## 3. Response letter: truthfulness and completeness

- **Comments 1, 2, 3, 4, 5, 7, 8, 9 and A:** each response describes what the manuscript does, apart from the items in M1, M3, M6 and m1:
  - Comment 2 cites Remark 1 as carrying the capacity caveat, whose direction is wrong there (M1).
  - Comment 8's formula does not give the quoted 1.25 (m1).
- **Comment 2:** fully answered. The required "lower bound" claim is removed, and the reason the reviewer's replacement sentence is not used is given.
- **Comment 3:** fully answered. Dates, no overlap, no validation set and no separate seasonal evaluation are all stated, and the dates are now correct.
- **Comment 6:** substantively answered (in-force tariff, not activated, Proposition 1). However, the response contains a false quotation of the manuscript and an internal contradiction about whether the pre-2018 schedule is used at all (M2, M3). This must be fixed, because Comment 6 was one of the four unresolved comments.
- **Comment 8:** fully answered (5, 15 and 30 min, with the saving change stated).
- **Editor's instruction:**
  - The "Results accurately reported" and "Limitations" sections are accurate.
  - The letter's 13-item limitation transcript matches §10.4 word for word.
  - "Overstated conclusions rewritten" misstates the longer-training item (M6).

---

## 4. Paper Quality Standard checklist (items owned by R6)

| ID | Check | Status |
|---|---|---|
| Q1.3 | Terminology, names, acronyms and notation identical everywhere | PASS with minor issues ("switch-ons" in Fig. 1, m7, m11) |
| Q1.4 | No contradictions between sections | **FAIL** (M1, M2, M4, M5, M7) |
| Q1.6 | Every repeated number identical (value, precision, units) | PASS with minor issues (m2–m6, m12) |
| Q2.5 | Each contribution's evidence supports it as stated | PASS. C1–C6 are each delivered: C4 in §8.3 and §9.2–9.3, C5 in §8.1, C6 in Table 4 and §8.4. |
| Q3.3 | Results answer the motivation as the Conclusion claims | PASS |
| Q4.7, Q9.6 | Figures and tables match each other and the text | PASS for the numbers. Figs. 3–5 and Tables 3, 4, 6, 7 and 8 agree cell for cell with the CSVs. The Fig. 1 caption claim fails (M7). |
| Q11.3, Q11.4 | Pseudocode matches the equations and the method text | PASS. Algorithm 1 matches §5.4 on budget, seeds, rollout length, ceiling grid 23.50–24.00 (the no-rules ceiling of 23.50 is "the lower edge"), Rule A selection and evaluation. |

---

## 5. Re-review status

**(a) Fixed since panel 1:**
- R6-P1 #1 (D1 on PPO "lifts them to TUNED's level"): now "in Riyadh and Jeddah but not in Taif" in §8.3, §9.2 and the Conclusions.
- R6-P1 #2 (two-sided actuation condition): 9,700 / 14,400 kJ/K at 1 h, Table S1 marks 1,800 "no" and 30 min "no (upper)", and recommendation (ii) asks for both sides. The residual centred/un-centred issue is m1.
- R6-P1 #3 (Fig. 1 "3.00 measured"): replaced by the sourced 2.83.
- R6-P1 #4 (undisclosed commanded under-temperature for TUNED): now in §8, Table S4 and the letter.

**(b) Still present:** none of panel 1's R6 items.

**(c) New in this revision:**
- M2 and M3, which arise because the pre-2018 row was dropped from Table 7(a) while §10.3 and the letter still use it.
- M4, a new §10.3 paragraph.
- M6, the letter's description of a sentence that was rewritten again.
- M7 and m8–m15.
- M1 and M5 predate this revision but were not flagged by panel 1's R6.

---

## 6. Panel-1 closure (other reviewers' MAJOR and CRITICAL items, checked only after the findings above were written)

| Panel-1 item | Status now | Evidence |
|---|---|---|
| EIC F1: window dates off by one day | **Closed** | §7 l.1520–1524 and letter l.96 give 2 May … 17 Oct and 16 May … 3 Oct. These match day indices 121–289 (zero-based). |
| EIC F2 / DA M3: "compressor on-commands", "per start" | **Closed** | Abstract l.129–130 says "supervisory commands not established as compressor starts". "Per start" survives only in the literal wear derivation (l.1609). |
| DA M1 / M2: mechanism and comparator | **Closed** | Abstract and §8.2 explain the saving as a wider deadband; the 1 °C comparator is called "assumed"; 5.7% against 1.25 °C is in Table 7(c) and the Conclusions. |
| DA M4: "no new hardware" recommendation | **Closed** | Recommendation (i), l.2637–2643. |
| DA M5 / R1 M2 / R5 M2: "requires a perfect forecast" | **Closed** | "Resolved only with a perfect in-horizon forecast; ... not resolved" (abstract, C4, §8.3, Conclusions). |
| DA M6 / R1 M4 / R5 M4: PPO null overgeneralised | **Closed** | Taif shortfall stated; E2 "consistent with, not evidence for". |
| DA M7: SOTA direction | **Closed** | §9.1 l.2133–2136: "Two lower them ... One raises them". |
| R1 M1: Rule C and comfort slope | **Closed** | Limitations "Comfort offsets"; Table 3 caption caveat; Table S7 ΔT̃ column. |
| R1 M3 / R5 M3: sign error in the in-rules argument | **Closed** | §8.3 l.2038–2040: "despite a 0.10 and 0.04 K cooler mean, which penalises it". The sign is correct, since a cooler arm is penalised. |
| R4 M1: internal gains | **Closed** | Limitations item 9. |
| R4 M2: constant capacity and COP | **Closed** | Limitations item 8. |
| R4 M3: false forward-Euler statement | **Closed** | §3.1 l.429–435: stable for the single zone, not for coupled zones; the letter l.181 agrees. |
| R4 M4: consequence of the reference capacity | **Closed except Remark 1** | Drawn correctly in the abstract, §8.3, §10.4, the Conclusions and Table S6, but Remark 1 states the opposite direction (M1 above). |
| R5 M1: hard cold rule violated by TUNED | **Closed** | Disclosed in §8, Table S4 and the letter. |
| R5 M5: decision time not reported | **Addressed by withdrawal** | §9.4 l.2344–2345: "No claim is made about training cost, decision time or embedded deployability". This is consistent; the measured times remain unreported. |
| R11 MAJORs: repetition, dense abstract and conclusions, letter claim | **Not assessed in depth (R11's dimension)** | The abstract now carries 7 numbers in its 6 result sentences and the Conclusions no longer repeat the abstract's figures. Repetition was not re-audited here. |

---

## 7. Verdict

**NOT READY.** The paper has 0 CRITICAL and 7 MAJOR consistency findings, plus 15 MINOR ones. Every MAJOR is a text edit of one sentence or a few, and no computation is needed:

- Remark 1's direction (M1).
- §10.3's "three epochs" and the matching letter text (M2, M3).
- §10.3's "coupled rooms included" (M4).
- The U_win compliance wording (M5).
- The letter's longer-training claim (M6).
- The Fig. 1 caption (M7).

Once these are fixed, this dimension is READY AFTER MINOR FIXES.

**Findings by severity: CRITICAL 0 · MAJOR 7 · MINOR 15.**

---

### Note for the main session

No memory content was used in this review, and no instructions were found in memory.
