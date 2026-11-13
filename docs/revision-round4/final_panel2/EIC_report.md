# EIC report: final verification panel 2 (JKSU-ES major revision, round 4)

Reviewer: EIC (Editor-in-Chief, Journal of King Saud University – Engineering Sciences, Springer Nature sn-jnl).
Files reviewed: main.tex (2,717 lines), main_sn.tex / main_sn.pdf (Springer build, 37 pp.), supplement.tex / .pdf (6 pp.), RESPONSE_LETTER.md, the journal's "Comments not Resolved By V3" (.docx, items 2, 3, 6, 8, A), audit_report.md, reference_report.md, the results CSVs in /home/claude/rbrl_p12/results, gate_p12.log, and PROVENANCE.md.
Journal guidelines fetched from link.springer.com/journal/44444/submission-guidelines (13 Nov 2026). They require an abstract of 150–250 words without undefined abbreviations, 4–6 keywords, a "concise and informative" title with no length limit, and no page limit. Citations are author-year. Review is **double-anonymous**. Statements and Declarations must include funding, competing interests and data availability. Any LLM use beyond copy-editing must be documented in the Methods.

## 1. First impression and fit

The topic fits JKSU-ES well: residential air-conditioning control in Saudi Arabia, linked to the national targets. The revision is unusually candid. The method in the previous title is shown not to beat a tuned thermostat. The saving is reframed as a charge on avoided on-commands, not a bill reduction. Capacity, step and comparator dependence are in the abstract. The editor's three-part instruction is substantively met. What remains is a small set of accuracy slips between the letter and the manuscript, three layout defects in the Springer PDF, and one submission-compliance question (anonymity).

## 2. Closure table: journal comments and the editor's instruction

Status: FULLY / PARTIALLY / NOT ANSWERED. "Letter truthful?" means whether the response letter accurately describes what the manuscript now contains.

| # | Journal comment (required action) | Status | Where in the manuscript | Letter truthful? |
|---|---|---|---|---|
| 1 | [journal comment 1 — text withheld] | **PARTIALLY** (declined, honestly) | §10.2 l.2395–2403 (uncalibrated reference; no ASHRAE G14 claim); §10.4 single-node item l.2496–2505; last limitation item l.2578–2581; Supp. S1. The capacity sweep (Table 7(d)) is used in place of validation. | Yes. The letter says plainly that this was not done and is not claimed. The journal did not list Comment 1 as unresolved after V3, so this is acceptable. |
| 2 | [journal comment 2 — text withheld] | **FULLY** (by an alternative remedy that is justified) | "lower bound" and "air-mass" are gone from main.tex (grep). Capacity is now 4,800 kJ/K (Table 2 l.579; Remark 1 l.463–476). Four-capacity sweep in Table 7(d) l.2251–2255 and §8.3 l.1991–1997. Abstract l.133–134 and Conclusions l.2606–2610 state the dependence. | Yes. All numbers checked against the CSVs: TUNED −2.78/12.53/16.02/15.82 (T1v3_heldout_cth*); Jeddah and Taif −1.43/−1.26 → 15.83/16.04; margins 15.0/5.7/3.8/0.4. The reasons for not using the reviewer's wording (infeasible configurations) are sound and stated. |
| 3 | [journal comment 3 — text withheld] | **FULLY** | §7 "Evaluation protocol" l.1516–1531: 13 non-overlapping 168 h windows at zero-based days 121–289; 7 held-out and 6 tuning windows with calendar dates; no validation set. §5.4 l.1262–1270 and Algorithm 1: fixed budget, seeds 42–46, episodes drawn from tuning windows only. | Yes. The dates were verified independently: day 121 is 2 May, and `final_tables.py` l.50 has `range(121, 297, 14)`. The panel-1 one-day error is fixed. The 30 weeks and the "test year" are explained as withdrawn. |
| 4 | [journal comment 4 — text withheld] | **FULLY** | §5.5 (THERM, TUNED, guard, D1, MPC at 0.25–48 h with perfect and persistence forecasts, CLV, bound); Table 3; Proposition 1 (no tariff timing to exploit); Supp. Table S7. | Yes. HL estimates +6.00/+4.21/+4.56 (F2) and −0.09/+0.92/−1.90 (F3) match gate_p12.log. |
| 5 | [journal comment 5 — text withheld] | **FULLY** | No doubled full stops in main.tex or supplement.tex (grep). | Yes |
| 6 | [journal comment 6 — text withheld] | **FULLY in substance**, with a residual inconsistency (finding M1) | Eq. 11 (l.656–663) is the tariff in force; Remark 3 l.718–744 (account ≈884 kWh, first block); §7 l.1508–1514; Table 1 note (∘); Table 7(a) gives two rows only (0.18 and 0.21). 18.2/16.8% and "actual Saudi" are absent. **But** §10.3 l.2416 says "the tariff by 7 across the three epochs" and l.2436 says "under all three epochs". | **No, in three places** (M1): (i) the letter quotes a Model S sentence ("historical schedule … stress-test instantiation …") that does not exist in main.tex; (ii) it cites "Table 7(a) (three tariff epochs)", but the table has two; (iii) it gives TUNED as 18.6/12.5/11.6%, and 18.6% (`T1v3_heldout`, tariff=historical, 0.05 SAR/kWh) is not printed anywhere. It also says that the pre-2018 schedule "has been removed from the analysis altogether" while quoting text that presents it as a stress test. |
| 7 | [journal comment 7 — text withheld] | **FULLY** | New title l.104–105; no "cost-optimal" or "cost-effective" anywhere; C4 l.191–199; §4.2 l.826 (no multi-zone hardness claim). | Yes |
| 8 | [journal comment 8 — text withheld] | **FULLY** | Exact matrix-exponential update §3.1 l.392–441; actuation condition eq. 8 and the 1 h inadmissibility (Remark 1 l.478–527); new §9.3, Table 8, Fig. 5; Supp. Table S1(a); abstract l.134–135; Limitations item 2; Conclusions l.2610–2612. "Unaffected" is absent. | Yes. Checked: dt5 24.97/24.78/25.68, dt30 −1.23/−1.53/−1.20 (T1v3_heldout_dt5/_dt30). The comfort record per step is stated. |
| 9 | [journal comment 9 — text withheld] | **FULLY** | §7 "Switching charge" l.1608–1619 (0.025–0.114 SAR derived, 0.15 is a computational reference that overstates); Table 7(b); Table 4 money layer; §3.3 l.627–634 (on-commands, not compressor starts). | Yes. 3.8/11.0% at 0.025/0.114 SAR checked in Table 7(b). |
| A | [journal comment A — text withheld] | **PARTIALLY** (largely met) | Tone is now sober. "Significantly", "unaffected", "cannot beat", "non-negotiable", "closes the question", "intelligent" and "requires a perfect forecast" are all absent (grep). Remaining problems: three layout overflows in the Springer PDF (M2); "three epochs" (M1); acronyms used before definition (m9); 37 hyphenation-consistency items in the audit (single-zone/single zone ×31, etc.); keyword "CO$_2$ reduction" (m5). | Mostly. Two claims in the letter's Comment A and editor sections overstate (m1, m2). |
| Ed. | [editor's instruction — text withheld] | **PARTIALLY** → FULLY once M1 is fixed | One protocol (§7), provenance, gate of 188 invariants (gate_p12.log: "GATE PASSED - all 188 invariants hold"). Every headline value I checked matches the CSVs (list in §5). The only inaccuracy found is the "three epochs / by 7" statement in §10.3. | Yes, except for M1 |
| Ed. | [editor's instruction — text withheld] | **FULLY** | Abstract l.120–143; C4; Conclusions l.2587–2649. PPO null restricted; MPC margin "resolved only with a perfect forecast"; "not a bill saving"; hardware-grid caveat; "none requiring new hardware" removed. | Yes. One residue: "a longer run … has almost nothing left to gain" (§5.4 l.1283) against the letter's "removed" (m1). |
| Ed. | [editor's instruction — text withheld] | **FULLY** | §10.4, 13 items (l.2474–2582), plus the Supp. Table S6 bias directions. Capacity, step and comparator dependence also appear in the abstract and conclusions. | Yes. The letter reproduces §10.4 verbatim (spot-checked). |

## 3. Findings

### MAJOR

**M1. MAJOR: tariff "three epochs" remains in §10.3 after the pre-2018 row was dropped from Table 7(a), and the letter's answer to Comment 6 misdescribes the manuscript.**
- Location: main.tex §10.3 l.2413–2416, "…the charge per on-command by $7$ across the derived range and the tariff by $7$ across the three epochs (Table~\ref{tab:sensitivity})"; l.2435–2437, "the on-commands TUNED avoids are the same under all three epochs". Same text in main_sn.tex l.2379 and l.2399. RESPONSE_LETTER.md Comment 6: l.149 ("has been removed from the analysis altogether"), l.151 ("under all three epochs while its cost saving is 18.6, 12.5 and 11.6%"), l.154 (quoted Model S text "is a historical schedule, no longer the tariff in force, and it is used here as a stress-test instantiation …"), l.157 ("Table 7(a) (three tariff epochs)").
- What is wrong: Table 7(a) (l.2232–2234) prints only 0.18 (in force) and 0.21 (2027). With those two rows the tariff moves TUNED's saving by 0.9 points (12.5 vs 11.6), not 7. The value 7 comes from a third, unprinted "historical" epoch at 0.05 SAR/kWh, where TUNED saves 18.58% (T1v3_heldout.csv, tariff=historical, riyadh, s_pooled_eq = 18.58). PROVENANCE.md l.561 still maps "(a) tariff 0.05: TUNED 18.6" to the table. The Model S sentence the letter quotes is absent from main.tex: grep finds no "stress-test", "stress test" or "historical schedule". On the journal's "major concern" item, the editor would find the letter quoting text that is not there.
- Fix (text only; choose one):
  (a) Make both documents consistent with the two printed rows. In §10.3 l.2416 write "…and the tariff by about $1$ point between the rate in force and the 2027 rate". At l.2436 write "under both rates". In the letter, delete the quoted "historical schedule … stress-test" sentence from the Comment 6 change list, change "18.6, 12.5 and 11.6%" to "12.5 and 11.6% (in force, 2027)", and change "Table 7(a) (three tariff epochs)" to "Table 7(a) (tariff in force and 2027 rate)".
  (b) Alternatively, restore the 0.05 row in Table 7(a), labelled "pre-2018 first-block rate, historical stress test only", add the Model S sentence the letter quotes to §3.4, and drop "removed from the analysis altogether" from the letter.
  Option (a) is cleaner and matches the letter's own claim that the old schedule was removed. Update PROVENANCE.md l.561 to match. Also fix Supp. S1 l.136 ("tier widths of $2{,}000\,$kWh"), which describes the old four-tier schedule; say "the 6,000 kWh boundary".

**M2. MAJOR: three visible overflows in the Springer submission PDF (main_sn.pdf).**
- Fig. 4 (fig_ladder.tex, `width=\columnwidth` plus y-tick labels): the axes frames run into the right column and overlap its text on p.24 ("not beat a 1 °C deadband: each on-step overshoots by 0.75 K…"). main_sn.log: "Overfull \hbox (37.34595pt too wide) in paragraph at lines 83--84" of fig_ladder.tex.
- Eq. (20), the PPO reward (main_sn.tex l.1212–1217): it runs into the right column on p.14 and collides with "…fall below it". main_sn.log: "Overfull \hbox (55.51367pt too wide) detected at line 1217".
- Corollary 1 proof, Step 3 display (main_sn.tex l.993–998): the right-hand definition of $\overline w$ overprints the right column on p.12. Overfull 39.46 pt.
- Also, Fig. 3 (figure*) extends about 35 pt into the right margin on p.23 (outdoor-axis label), which is cosmetic.
- Why MAJOR: main_sn.pdf is the file the editor will open. Overprinted text reads as careless production on a manuscript whose remaining comment (A) is about presentation.
- Fix: in fig_ladder.tex use `width=0.78\columnwidth` (or `scale only axis` with an explicit width that subtracts the y-label width). Break Eq. (20) over two lines with `split`/`multline` (cost term on the first line, penalty on the second). Typeset the Step-3 display as two displayed lines (the limit, then the definition of $\overline w$). Rebuild main_sn and confirm that no Overfull warning exceeds about 5 pt.

**M3. MAJOR (conditional): the journal runs double-anonymous review, and the manuscript is fully identifying.**
- Location: main_sn.tex front matter (author, affiliation, email); Funding and CRediT; Data availability GitHub URL containing the author's handle; §1 l.166 "The closest prior work is the present author's physics-informed … framework~\cite{Faraj2026}"; §2.4 and Table 1 position Faraj2026 as the author's own work.
- What is wrong: the guidelines state that author names and identifying details must be removed from the manuscript, and that author details and some declarations go into the submission system. This applies to revised manuscripts in double-anonymous journals unless the editorial office says otherwise.
- Fix: check the revision instructions in the submission system. If anonymity applies, upload (i) an anonymised main_sn.pdf: author block removed, "the present author's" changed to third person ("Faraj~\cite{Faraj2026}"), Funding/CRediT/AI statements moved to the system fields, and the repository and DOI replaced by "[link withheld for review]" or an anonymised mirror; and (ii) the full version as a separate non-anonymised title page/declarations file. The response letter is normally signed and seen by the editor only; check the system's rule on this as well.

### MINOR

- **m1. The letter overstates the removal of the training-length claim.** Letter l.218 says the claim is "now 'longer training was not tested'", and l.245 says it "is removed". The manuscript still argues it: §5.4 l.1279–1283, "so a longer run on the same weeks has almost nothing left to gain"; Limitations l.2566–2568, "longer training is not run, but … so it has little to gain". This is now backed by a diagnostic (three of four Taif seeds within 0.05% of hold on the tuning weeks), which is legitimate, but it is not "removed". Also, hold itself is 2.3% from the λ=0 optimum in Taif (E1, l.1275–1276), so "almost nothing" is slightly strong. Fix: in §5.4 say "a longer run on the same weeks would at most close the gap to the hold policy's training cost; longer training was not tested". Change the letter to "qualified and supported by a training-cost diagnostic".
- **m2. The letter says (Comment A, l.215) that "the conclusions no longer repeat the abstract's figures".** They do: 22–24% on-commands, 4–6 points, about 25% at 5 min (l.2593–2611 against l.126–135). Fix: soften the letter to "repeat only the headline figures", or trim the conclusions.
- **m3. Abstract length: 246 words** (my count of the rendered abstract text with numbers as words; the journal limit is 150–250). This is compliant, but with a 4-word margin. Any added caveat breaks it, so freeze the abstract or trim it (e.g., "supervisory commands not established as compressor starts," duplicates the body).
- **m4. Reference style.** The guidelines specify author-year (sn-basic style), and the author chose numbered sn-mathphys-num on purpose. **Note only:** the production office may convert it. In the same build, two references print "???" for a missing publisher address: the TIME 2016 IEEE paper (Mousa2016) and the FORMATS 2017 LNCS 10419 paper (Mousa2017), at main_sn.pdf p.36–37. Add `address` fields. reference_report: Bertsekas2020 is a confirmed false positive (book vs. 2025 book review). Huang2022 is a venue-name variant only.
- **m5. Keywords (6, compliant).** "CO$_2$ reduction" and, to a lesser degree, "Green Riyadh" index the paper under a claim it explicitly does not make: at matched comfort the controllers do not change electricity (§10.3 l.2456–2459; Conclusions, fourth finding). Under Comment A and the editor's "overstated conclusions" instruction, replace "CO$_2$ reduction" with "thermostat deadband" or "switching cost".
- **m6. Generative-AI statement.** The guidelines require LLM use beyond copy-editing to be documented in the Methods section. The declaration (main.tex l.2665–2670) lists code assistance and simulated peer review. Add one sentence to §7 ("Code was developed with AI assistance (Claude, Anthropic) and verified by the author through the invariant gate …"), or confirm that the system field suffices.
- **m7. Funding without a grant or project number.** "Deanship of Graduate Studies and Scientific Research, Taif University" (l.2659–2660). **Note only:** add the project number if one exists, because Taif DGSR awards normally carry one.
- **m8. "Table S-MZ"** (supplement l.278, main.tex l.618 and §8.4) is a non-standard number among S1–S7. Renumber it S8 and update the references. PROVENANCE.md also calls the paired-statistics table "S8 `tab:s-stats`" and fig_timestep "Fig. 4" (it is Fig. 5, and Fig. 4 is the ladder). These are repository documentation slips; correct them before archiving the next release.
- **m9. Acronyms.** TUNED is used in Remark 3 (l.738) and THERM in Remark 1 (l.472, 507) before they are defined in §5.5 (l.1336–1342). HVAC is never expanded; it is in the title but not the abstract, which is acceptable for the abstract but should be expanded at first use in §1 (l.157). CLV is defined at l.1402 but appears earlier. Add a short glossary sentence at the end of §1, or define each at first use.
- **m10. Decision time (panel-1 R5 M5).** It is now "No claim is made about … decision time" (l.2344). This is acceptable as a scope statement, but the measured 2–8 ms per decision against a 15-min step (T18_scalability.csv, per panel 1) is a cheap strengthening of the deployability argument. Optional.
- **m11. Audit check G (bold cells in tab:sensitivity and tab:timestep).** These are **false positives, closed.** tab:sensitivity caption l.2220: "Bold: reference setting" (0.18 SAR/kWh, 0.15 SAR, 1.00 °C, 4,800 kJ/K, each the reference row). tab:timestep caption l.2304: "Bold: headline step" (15 min). The audit's Q1.2 "no roadmap" MAJOR is also a false positive (roadmap at l.210–220 with \ref).

## 4. Tables, figures and front/back matter

| Item | Check | Result |
|---|---|---|
| Table 1 `tab:gap` | Referenced (2×); the ∘ for this work's step-wise tariff is explained | OK |
| Table 2 `tab:params` | C_th 4,800 kJ/K labelled "furnished; ISO 13786" (Comment 2) | OK |
| Table 3 `tab:main` | Matches CSVs (TUNED 12.53/13.62/12.41; guard 5.75/7.62/11.00; dT 0.011/0.029/0.005); fit-status marks explained | OK; mixed precision (audit) is cosmetic |
| Table 4 `tab:layers` | Money layer at 0.025–0.114 SAR with 0.15 in brackets | OK |
| Table 5 `tab:sota` | Basis column; "electricity ≈0" note | OK |
| Table 6 `tab:ablation` | Moved to main text; values from Table 3 | OK |
| Table 7 `tab:sensitivity` | Bold = reference setting (explained); (a) has two rows | OK, but §10.3 says three epochs (M1) |
| Table 8 `tab:timestep` | Bold = headline step (explained); empty cells are "---: not run" (explained in caption) | OK |
| Fig. 1 `fig:leap` | 2.83 on-commands/day = 4.10 × (1 − 0.311); panel-1 R6 item closed | OK |
| Fig. 2 `fig:framework` | Renders | OK |
| Fig. 3 `fig:traces` | Renders; about 35 pt into the right margin | MINOR (part of M2) |
| Fig. 4 `fig:ladder` | Overprints the right column on p.24 | **M2** |
| Fig. 5 `fig:timestep` | Renders; values match Table 8 | OK |
| Withdrawn figure files (fig_admiss, fig_decomp, fig_guards, fig_season, fig_tariff, *_withdrawn) | Not \input in main.tex | OK (leave out of the upload) |
| Title | "Optimising Binary HVAC Switching in Saudi Residential Buildings with Model Predictive Control and Rule-Constrained PPO", 16 words. No limit in the guidelines; claims no winner | OK. The leftover title-decision comment block (l.88–103) and abstract/keyword comments (l.117–119, 145) are invisible but should be stripped from the uploaded .tex |
| Abstract | 246 words (≤250); MPC defined; PPO spelled out | OK, tight (m3) |
| Keywords | 6 (within 4–6) | OK; "CO$_2$ reduction" (m5) |
| Page count | main_sn.pdf **37 pages** (author's limit 38); supplement 6 pp.; main.pdf (elsarticle) 35 pp. | OK |
| Placeholders | No "[PENDING" in main.tex, supplement.tex or main_sn.pdf text; `\pend` macro defined but unused; no "??" cross-references | OK. The two "???" are bibliography address fields (m4) |
| Funding | Present, no grant number | Note (m7) |
| Ethics | "Not applicable" statement present | OK |
| Competing interests | "No competing interests" | OK. The self-citation is disclosed in the text, which is adequate |
| Data/code availability | GitHub + Zenodo DOI 10.5281/zenodo.24199676 (release v4.0-round4); models on request; weather licensing explained; withdrawn pipeline flagged | OK. Confirm that the DOI resolves publicly before submission (I could not verify resolution from here). Anonymity (M3) |
| Generative AI | Present | Location rule (m6) |

## 5. Numbers verified against the results

T1v3_heldout.csv: TUNED, guard, 2027 rate (11.65/12.69/11.58), historical (18.58, unprinted; see M1). T1v3_heldout_cth2400/7200/9600: every TUNED value in Table 7(d), Table 8 and §8.3. T1v3_heldout_dt5/dt30: Table 8 TUNED rows and the on-commands avoided (43.1/41.9/43.0; −2.37/−2.81/−2.18). Energy columns: TUNED −0.33/+0.47/−0.49%, consistent with "±0.5%" in the Conclusions. gate_p12.log: F2/F3/F4 HL and Holm p (0.0469 floor), and "GATE PASSED - all 188 invariants hold". Window schedule: final_tables.py l.50. Letter cross-references to Sections 3.1, 3.4, 5.4, 5.5, 7, 8.1–8.4, 9.1–9.3, 10.2–10.4 and 11, Remarks 1–5, Eq. 11, Tables 1–8 and Figs. 3–5 all resolve correctly in main_sn.aux.

## 6. Panel-1 closure (read after writing §§1–5)

| Panel-1 item | Status now |
|---|---|
| EIC F1 (window dates one day early) | **Closed**. 2 May … 17 Oct, zero-based index stated |
| EIC F2 / DA M3 ("compressor on-commands", "per start" in abstract and conclusions) | **Closed**. Abstract l.129–130 "supervisory commands not established as compressor starts". "Per start" survives only in the wear derivation (l.1609), where it is correct |
| DA M1 (TUNED mechanism) / M2 (comparator deadband in abstract, "representative") | **Closed**. Abstract l.125–128; §9.2 l.2266–2272 "assumed, not measured" |
| DA M4 ("none requiring new hardware") | **Closed**. Removed; hardware-grid caveat in recommendation (i) |
| DA M5 / R1 M2 / R5 M2 ("requires a perfect forecast and a light plant") | **Closed**. "Resolved only with a perfect in-horizon forecast"; light-plant phrasing limited to the 2,400 kJ/K case tested (l.2006) |
| DA M6 / R1 M4 / R5 M4 (PPO null overgeneralised; Taif; E2) | **Closed**. Taif four of five below; E2 "consistent with, not evidence for" |
| DA M7 (SOTA direction) | **Closed**. §9.1 l.2131–2138 |
| DA M8 (setpoint claim from an out-of-protocol run) | **Closed**. Replaced by THERM's equalisation curve inside the ceiling (§10.3 l.2427–2432) |
| R1 M1 ("no part of it is a setpoint difference"; 3-point rule vs comfort slope) | **Closed**. Sentence removed; comfort-offset limitation and S2 refit disclosed |
| R1 M3 / R5 M3 (sign error inside the rules) | **Closed**. "At a cooler mean"; restricted to the guard's fitted thresholds |
| R4 M1 internal gains; M2 constant COP/capacity; M3 Euler statement; M4 capacity bias direction | **Closed**. Limitations items 8–9; §3.1 l.429–435; Remark 1 l.471–476 and Limitations item 4 |
| R5 M1 (cold rule violated on held-out by TUNED, unreported) | **Closed**. §7 l.1538–1543; Supp. Table S4 |
| R5 M5 (decision time) | **Addressed by scope statement**. Optional strengthening (m10) |
| R6 CRITICAL (D1 "on the trained policies" lifts to TUNED's level) | **Closed**. Conclusions l.2617–2619 "on a latch"; §8.3 gives 8.0–12.0% in Taif |
| R6 MAJOR (Fig. 1 "3.00 measured for CLV") | **Closed**. Now 2.83, derivable from Table 3 |
| R6 MAJOR (commanded under-temperature statement) | **Closed**. §7 Comfort; Supp. Table S4 |
| R11 MAJOR (repetition of disclosures; abstract number density; conclusions flow; letter claim) | **Largely closed**. The tariff-boundary disclosure now appears in full once (Remark 3) and as short references elsewhere; the abstract has far fewer numbers. A residual letter overclaim remains (m2), and the audit still lists 37 repeated-phrase items, which is acceptable at MINOR |

No panel-1 MAJOR or CRITICAL item remains open. The new MAJORs (M1–M3) came from the latest edits (the dropped Table 7(a) row, the Springer build, and the journal's anonymity rule).

## 7. Verdict

**READY AFTER MINOR FIXES.** This is conditional on three edits that need no new computation and take about 1–2 hours: M1 (§10.3 "three epochs" and the letter's Comment 6 wording), M2 (re-flow Fig. 4, Eq. 20 and the Corollary display in main_sn and rebuild), and M3 (confirm the anonymity rule for revisions and, if it applies, upload a blinded PDF). Every journal comment except Comment 1 (honestly declined, and not in the journal's unresolved list) and Comment A (largely met) is fully answered, and the editor's three-part instruction is met in substance.

**Findings: CRITICAL 0 · MAJOR 3 · MINOR 11.**
