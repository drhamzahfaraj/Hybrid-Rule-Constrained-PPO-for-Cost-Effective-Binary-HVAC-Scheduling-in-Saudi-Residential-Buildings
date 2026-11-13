# EIC Report — Final verification panel, JKSU-ES major revision, round 4

Reviewer: EIC (Editor-in-Chief, Journal of King Saud University – Engineering Sciences).
Files reviewed: `main.tex` (2,653 lines), `main.pdf` (34 pp), `main_sn.pdf` (36 pp), `supplement.tex/.pdf` (4 pp), `tables/tab_stats.tex`, `RESPONSE_LETTER.md`, the journal's `Comments_not_Resolved_By_V3.docx` (comments 2, 3, 6, 8, A), Phase 0 `audit_report.md`, and results/code in `/home/claude/rbrl_p12` (read only).
Journal profile: `shared/journal_profiles.md` has no JKSU-ES entry. I used the closest one (JKSU-CIS, the same Springer Nature family) together with sn-jnl norms.

**Overall recommendation: Minor revision.** Confidence 4/5.

---

## 1. Page count and format

| Item | Value | Status |
|---|---|---|
| `main_sn.pdf` pages | **36** (limit 37) | Passes. Only one page of headroom remains for filling the MPC-MZ and Zenodo placeholders. |
| `main.pdf` (elsarticle) pages | 34 | For information |
| Abstract length (sn build, words) | **246** (limit 250) | Passes, with little margin. "PPO" and "SAR" are not defined in the abstract (see F11). |
| Keywords | 7 | Springer journals usually allow 4–6. Confirm against the live JKSU-ES guide (F11). |
| Declarations (sn build) | Funding, Author contributions, Data availability, Competing interests, Use of generative AI | **Ethics statement missing from the sn build** (F6). The Funding statement has no grant number (F7). |
| Placeholders | `[PENDING:MPC-MZ, mz_final]` (§8.4, §11) and `[PENDING:Zenodo DOI, F20]` | Known by design, so not counted as defects. |

---

## 2. Comment-by-comment closure table

Ratings: FULLY / PARTIALLY / NOT ANSWERED. The letter-truthfulness column says whether the response letter describes the manuscript accurately.

| # | Journal comment (required action) | Rating | Where the manuscript answers it | Letter truthful? |
|---|---|---|---|---|
| 1 (first round) | [journal comment 1 — text withheld] | **Answered by disclosure.** The validation is not performed, and the manuscript says so plainly. | §10.2 l.2380–2388 (uncalibrated reference, no ASHRAE G14 claim); Limitations items "Single-node…" (l.2458–2467) and "One year, one zone type, simulation only" (l.2517–2525); Supp. S1 "Validation literature" (l.44–54). The corrected Bacher & Madsen reading is at l.2459–2462. | Yes. The letter says plainly that the validation was not done. The journal did not list this comment as unresolved. |
| 2 | [journal comment 2 — text withheld] | **FULLY** (the prescribed wording was not used, with justification) | The phrase "lower bound" appears nowhere in main.tex or supplement.tex (grep). The capacity is now 4,800 kJ/K: Remark 1 l.476–487 and Table 2 l.591. Four-capacity sweep: §8.3 "Thermal capacity" l.2030–2050 and Table 7(d). Why the 77.2/500/1,200 sweep is withdrawn: Supp. S1 "Capacity" l.56–68 and Table S1(b). Abstract l.132–135; Limitations item 4; Conclusions l.2546–2548. | Yes on substance. I checked the excursions arithmetically (7,200 kJ / {77.2, 500, 1,200} = 93.3, 14.4, 6.00 °C) and they are correct. The editor should know the author **declined the prescribed sentence**, and the reason is sound: the old sweep compared configurations with no comfort-feasible schedule. One rounding discrepancy: the letter gives the 4,800 kJ/K margin as 5.7 and the manuscript l.2035 as 5.8 (F3). |
| 3 | [journal comment 3 — text withheld] | **PARTIALLY** | §7 "Evaluation protocol" l.1584–1599; §5.4 and Algorithm 1 (l.1312–1392); TUNED grid l.1407–1412; actual-year spread §10.2 l.2370–2379; Limitations item 13. The protocol is single and consistent. I confirmed in code that PPO trains on `TUNE_W` only (`rbrl_ppo.py` l.269), the ceiling is fitted on `TUNE_W` (l.291), evaluation is on `EVAL_W`, seeds are 42–46, the budget is 2×10⁵ steps (≈298 episodes), and `EVAL_W = WINDOWS[0::2]`. **However, every stated calendar date is one day early** (F1). | **No, on the dates only.** The letter repeats the same wrong dates. Everything else in the letter matches the code. |
| 4 (first round) | [journal comment 4 — text withheld] | **FULLY** | §5.5 l.1394–1497 (TUNED, guard, D1, causal DP-MPC at 0.25–48 h with perfect and persistence forecasts, in-rules variants, CLV, relaxed bound); Proposition 1 (l.690–707) explains why no tariff-aware rule is needed; Tables 3, 5; §8.3. | Yes. D1 14.0/13.5/12.4, RBRL 5.7/7.6/8.6–11.0, HL +6.0/+4.2/+4.6 and persistence −0.1/+0.9/−1.9 all match. |
| 5 (first round) | [journal comment 5 — text withheld] | **FULLY** | grep for `..` finds nothing in main.tex or supplement.tex. | Yes |
| 6 | [journal comment 6 — text withheld] | **FULLY** (both remedies applied) | Model S labelled historical/stress test (§3.4 l.678–689); Remark 3 l.755–790 (884 kWh/month, first block only); §7 "Background load and tariff" l.1575–1582; Table 1 note (step-wise ∘); Table 7(a); 2027 rate at §8.2 l.1957–1961; §10.3 l.2422–2431. grep finds no "18.2", "16.8" or "actual Saudi" in the narrative. | Yes. I verified TUNED at 0.21 SAR/kWh: 11.65/12.69/11.58 (`T1v3_heldout.csv`, tariff=y2027). |
| 7 (first round) | [journal comment 7 — text withheld] | **FULLY** | Title; C4 l.191–199; §4.2 l.858 ("no hardness result is claimed for the multi-zone problem"). grep finds "cost-optimal/effective" only in the GitHub URL (l.2616). | Yes |
| 8 | [journal comment 8 — text withheld] | **FULLY** | Exact (matrix-exponential) update §3.1 l.408–453; actuation condition Remark 1 l.492–540; new §9.3 l.2271–2287 and Table 8; Supp. S1 Table S1(a) (THERM deg-h 0.000/0.000/0.025/4.470); abstract l.135–137; Limitations item 2; Conclusions l.2549–2552. "Unaffected" appears nowhere. | Yes. Every Table 8 cell matches `T2v3_timestep.csv`. One gap: THERM's 0.025 °C·h leak at 30 min is disclosed only in the supplement (F10). |
| 9 (first round) | [journal comment 9 — text withheld] | **FULLY** | §7 "Switching charge" l.1672–1682; Table 4 money layer; Table 7(b); Remark 4; Limitations items 3 and 9. | Yes. TUNED 3.8/11.0, MPC 5.7/16.1 (`T21v3_csw0.025/0.114_riyadh.csv`: 5.74/16.10) and bounds 6.3/17.5 all match. |
| A | [journal comment A — text withheld] | **PARTIALLY** | The tone is now sober and self-critical throughout: no "significantly", "novel", "superior" or "outperform". Remaining problems: "compressor on-commands" / "per start" in the abstract and conclusions (F2); internal jargon ("round-3 protocol", l.2415, F9); E1 used before it is defined (F13); heavy repetition of the same figures and caveats (F14); a 27-word title (F12). | Mostly. The letter says the manuscript "no longer equates [on-commands] with compressor starts", but the abstract (l.125) and conclusions (l.2536) still say "compressor on-commands" (F2). |
| Editor | [editor's instruction — text withheld] | **PARTIALLY → near full** | Accuracy: every number I checked against the CSVs matches (list in §4) except the window dates (F1). Overstatements: withdrawn or narrowed throughout; the remaining exception is F2. Limitations: §10.4 has 13 items, matching the letter. The table of bias directions for each idealisation exists only "in the repository" (l.2437); it belongs in the supplement (F15). | Mostly. The letter's "Limitations now stated" section reproduces §10.4 verbatim; its "(Section 17)" cross-reference does not exist in the sn build (F16). |

---

## 3. Findings

### MAJOR

**F1. MAJOR: the window dates stated for Comment 3 are wrong by one day, in both the manuscript and the letter.**
- **Location:** §7 "Evaluation protocol", main.tex l.1586–1592:
  > "Thirteen windows of 168 h start every 14 days from day-of-year 121 to 289 … The seven held-out windows start on 1 May, 29 May, 26 June, 24 July, 21 August, 18 September and 16 October; the six tuning windows start on 15 May, 12 June, 10 July, 7 August, 4 September and 2 October."

  The same dates appear in RESPONSE_LETTER.md, Comment 3, paragraph 2.
- **Evidence:** The day index is 0-based in the code:
  - `final_tables.py` l.49–52 defines `WINDOWS = list(range(121, 297, 14))` with the comment "1 May = day 120".
  - `headroom._series` uses `h0 = start_day * 24` on the 8,760-row EPW array.
  - EPW data row 2905 (index 2904 = 121×24) of `riyadh.epw` reads `2016,5,2,1,…`, so the first window starts on **2 May**.

  The actual held-out starts are 2 May, 30 May, 27 Jun, 25 Jul, 22 Aug, 19 Sep and 17 Oct. The actual tuning starts are 16 May, 13 Jun, 11 Jul, 8 Aug, 5 Sep and 3 Oct.
- **Why this is MAJOR:** Comment 3 explicitly required the dates of each set [journal comment 3 — text withheld]. No result changes, but the one item the journal asked to pin down is misstated.
- **Fix:** Text only; no rerun.
  - Replace the dates in §7 and in the letter with the dates above.
  - Write "0-based day index 121–289 (day-of-year 122–290)" or simply drop the day-of-year phrase.
  - Correct the window labels in `gen_figs.py` / `make_figs.py` (l.280 / l.169, "1 May" …) and any supplement per-window table that uses them.

**F2. MAJOR: "compressor on-commands" and "per start" remain in the abstract, §8.2 and the conclusions. This contradicts the manuscript's own limitation and the letter's claim.**
- **Location and quoted text:**
  - Abstract l.125–127: "avoids 22–24% of **compressor** on-commands … at the 0.025–0.114 SAR **per start** that wear supports".
  - §8.2 l.1916–1917: "the share of **compressor** on-commands avoided".
  - Conclusions l.2536–2538: "avoids 22–24% of **compressor** on-commands … **per start**".
- **Contradiction:** §3.3 l.646–648 says "Whether each on-command corresponds to a compressor start … is not established here", and Limitations item 3 is headed "On-commands, not compressor starts". The letter (Editor's instruction section, bullet "Compressor starts") says "the manuscript no longer equates them with compressor starts".
- **Why this is MAJOR:** It is an overstatement in the abstract, and the response letter describes it inaccurately.
- **Fix:**
  - Use "supervisory on-commands" in all three places.
  - Use "per on-command" when giving the charge.
  - The derivation in §7 may keep "per start" in its literal sense, i.e. a start life of 10⁵.

### MINOR

**F3. Planner margin at 4,800 kJ/K: 5.8 in the manuscript versus 5.7 in the letter and Table 5.**
- **Location:** main.tex l.2035: "its margin over TUNED is 15.0, **5.8**, 3.8 and 0.4 points".
- **Evidence:** The unrounded difference is 18.2638 − 12.5260 = **5.74** (`T21v3_riyadh.csv`, `T1v3_heldout.csv`). Table 5 gives the pooled Δs as +5.7, and the letter (summary and Comment 2) says 5.7. The 5.8 is the difference of two rounded values.
- **Fix:** Change it to 5.7.

**F4. Audit check G: bold cells.**
- **tab:sensitivity:** The bold cells are on the *Setting* labels (0.18, 0.15, 1.00, 4,800), and the caption l.2215 declares "Bold: reference setting". The Phase 0 flag is a **false positive**, so no change is needed.
- **tab:timestep:** The bold "15 min" row (l.2315) is not explained in the caption (l.2291–2304). Add "Bold: headline step."
- **tab:sensitivity (b):** The cell "−0.0" at c_sw = 0 (l.2231) should read "0.0".

**F5. Tables are not first cited in consecutive order, which Springer requires.**
- Table 7 (tab:sensitivity) is first cited in Remark 1 (l.524), before Tables 3–6 (first cited at l.1481, 1916, 1937, 2127).
- Table 4 (tab:layers) is first cited at l.1916, after its float in the source (l.1883).
- **Fix:** In Remark 1, refer to "Section 9.2" instead of the table. Move the first citation of tab:layers ahead of its float.

**F6. The ethics declaration is dropped from the Springer build.**
- main.tex §15 (l.2603) has "Ethics Approval: … not applicable".
- `main_sn.tex` back matter (l.2555–2606) has Funding, Author contributions, Data availability, Competing interests and Use of generative AI, but no ethics heading.
- **Fix:** Add `\bmhead{Ethics approval and consent to participate}` with "Not applicable", and "Consent for publication: Not applicable", in `to_springer.py`.

**F7. The Funding statement reads as an acknowledgement and has no grant number.**
- l.2601: "The author would like to acknowledge the Deanship … for funding this work."
- **Fix:** "This work was funded by the Deanship of Graduate Studies and Scientific Research, Taif University (project no. …)."

**F8. The affiliation differs between builds.**
- main.tex l.111: "Department of Science and Technology, Ranyah College, Taif, 21944".
- main_sn.pdf p.1: "Department of Sciences and Technology, Ranyah University College, P.O. Box 11099, Taif, 21944".
- **Fix:** Use one form in both builds.

**F9. The phrase "round-3 protocol" (l.2415) is internal jargon, and it invites a provenance question.**
- The setpoint figures (7.1/9.4/14.5% cost) reproduce exactly from `T1v2_heldout.csv` vs `T1v2_heldout_pol24.csv` (7.07/9.38/14.45). They are THERM-only, and THERM has no fitted parameters: its J of 1.118 is identical in v2 and v3. The figure is therefore protocol-independent.
- **Fix:** Say "a separate run of THERM centred at 24 °C (THERM has no fitted parameters, so the protocol does not enter)". The letter's phrase "under the earlier protocol" should be changed the same way, so the editor does not read it as the withdrawn pipeline.

**F10. THERM's 30-min leak is not disclosed in the main text.**
- At 30 min THERM accumulates 0.025 occupied °C·h (Supp. Table S1(a) l.98), yet §9.3 and Table 8 compare the fitted arms (zero over-temperature) with it without mentioning this.
- The leak favours THERM, so the reported −1.2 to −1.5% is conservative. It also shows that condition (9), which admits δ = 1 °C at 30 min, is necessary but not sufficient.
- **Fix:** Add one sentence to §9.3 or the Table 8 caption.

**F11. Abstract abbreviations and keyword count.**
- "PPO" and "SAR" are undefined in the abstract.
- There are 7 keywords.
- **Fix:** Spell out the abbreviations (watch the 250-word limit; the abstract is at 246). Trim to 6 keywords, e.g. merge "constrained reinforcement learning" and "proximal policy optimisation", unless the JKSU-ES guide allows 7.

**F12. The title is 27 words.**
- The source comment at l.102–103 already plans to "drop the subtitle … if the rule is exceeded".
- **Recommendation:** Drop ": Switching-Cost Savings and a Clairvoyant Optimality Bracket". The main title still names what is compared and claims no winner.

**F13. E1 is used before it is defined.**
- "E1" first appears at l.1483 ("E1 (Section 9.2) keeps the simulator terminal") and is defined only parenthetically at l.2191.
- **Fix:** Define it at first use: "E1, the exact λ = 0 dynamic-programming optimum inside the rules".

**F14. Repetition (Comment A asks for it to be reduced).**
- The D1/guard figures (14.0/13.5/12.4 and 5.7/7.6/11.0, plus the 12.8–14.1 … range) are restated in four places: Remark 5 (inside the theory section, before any results; l.1101–1104), §8.3 l.2068–2079, §9.2 l.2193–2196 and the Conclusions.
- The comfort-offset caveat ("0.01 K ≈ 1.3 points") appears at least five times: tab:main caption, Remark 5, §8.3, Limitations, Conclusions.
- Models L and E (§3.4) are formulated but used in no result.
- **Fix:**
  - Keep the D1 numbers in §8.3 only and cross-reference them elsewhere.
  - In Remark 5, state the mechanism without numbers.
  - Give the comfort caveat once, in the Limitations, and point to it.
  - Shorten Models L and E to one sentence each under Proposition 1.

**F15. The table of bias directions for each limitation is only in the repository.**
- l.2437: "The direction in which each idealisation biases the reported percentage is tabulated in the repository."
- The editor asked for the limitations to be "fully explained" in the work.
- **Fix:** Move that table into the supplement as a short table; the supplement is 4 pages, so there is room.

**F16. Letter cross-reference to a section that does not exist in the sn build.**
- The letter quotes Limitations as "… tabulated in the repository (Section 17)". In the sn build the Data availability statement is an unnumbered back-matter heading.
- **Fix:** Write "(Data availability statement)".

**F17. There is no ablation table (author's Paper Quality Standard; audit check E).**
- The ablation is complete but in prose (§9.2): rules off (1/5 admissible seeds, −3.5%), PPO in rules equals the guard, E2 holds the same policy, D1 on PPO gives 12.8–14.1%, and guard vs TUNED gives −6.8/−6.0/−1.4.
- **Recommendation:** Present it as a compact five-row ablation table. This is the author's own standard, not a journal requirement.

*Note, not counted (placeholders are known):* The letter says the pending items are marked "as they are there", with the text "[to be added]" and "[Zenodo DOI to be added before submission]". The PDF actually renders `[PENDING:MPC-MZ, mz final]` and `[PENDING:Zenodo DOI, F20]`. Make the markers match before the letter goes out.

---

## 4. Table audit (check G) and numbers verified against the CSVs

| Table | Cited before it appears? | Values match text/CSV | Bold = true best? |
|---|---|---|---|
| 1 tab:gap | Yes (l.294) | Qualitative | "This work" is a row label, not a value |
| 2 tab:params | Yes (l.472) | 23.75/24.62/22.67 W/K agree with Remark 2 and §3 | None |
| 3 tab:main | Yes (l.1481) | **Checked against CSVs.** TUNED, guard, MPC (all horizons, both forecasts) and CLV values listed below. Fit-status superscripts match `fit_status` (e.g. MPC 2 h Riyadh, 24 h persistence Riyadh/Taif and 48 h Taif are pooled_0.10). | None |
| 4 tab:layers | **After its float in the source** (F5) | On-command and energy columns equal `start_sav_eq` / `energy_sav_eq` (e.g. TUNED 22.83/24.16/21.74; −0.33/+0.47/−0.49). | None |
| 5 tab:stats | Yes (l.1937) | HL, CI and p_adj equal `gate_p12.log` P12 lines (e.g. F2 Riyadh +6.00 [+3.83, +7.48], F4 Taif +0.00 [−3.00, +0.06]). Pooled Δs equals the arm difference in Table 3. | None |
| 6 tab:sota | Yes | Literature | None |
| 7 tab:sensitivity | **Cited in Remark 1 before Tables 3–6** (F5) | (a) 18.58/12.53/11.65; (b) 3.8/11.0 and MPC 5.74/16.10; (d) TUNED −2.78/12.53/16.02/15.82, MPC 12.25/18.26/19.80/16.17, B* at 7,200 = 20.0 (`T17v3_riyadh_cth7200.csv`). All match. | Bold marks the reference setting and the caption says so. **Audit flag is a false positive.** |
| 8 tab:timestep | Yes (l.2275) | All 18 cells equal `T2v3_timestep.csv` (e.g. dt5 MPC 23.80, 801 nodes, pooled_0.10, ΔT −0.078; dt30 MPC λ/λ* 6.27). | Bold 15 min is the headline row, **not declared in the caption** (F4). |

**Other numbers verified:**
- THERM J = 1.118 / 0.993 / 0.614.
- CLV Rule C 18.27/18.51/16.51 against B_CLV 19.58/19.41/20.23, with 2/1/0 windows meeting the target (`T13v3_clv_*_summary.csv`).
- 89 arm and seed rows, all `s_le_B` and `cert_ok` True (`T17v3_Ba.csv`).
- Gate log: "GATE PASSED – all 188 invariants hold".
- Conclusion ratios: 69–74% of CLV and 59–68% of B*, recomputed and correct.
- Setback 18.6/20.1/17.0.
- Setpoint run 7.07/9.38/14.45.

---

## 5. Journal fit and coherence (EIC view)

**Fit.** The paper fits JKSU-ES: building energy, HVAC control and Saudi climate and tariff, with clear relevance to Vision 2030. The self-citation (Faraj 2026, same journal) is now positioned openly (§2.4, Table 1), which the editor will welcome.

**Originality and significance.** The contribution has changed from "a new RL method" to a carefully controlled negative and benchmarking result:
- PPO inside the rules equals the rules' own hold policy.
- A commissioned two-parameter thermostat captures 59–74% of the clairvoyant bracket.
- MPC's margin needs a perfect forecast and a light plant.
- The benefit is wear (on-commands), not the bill.

This is less flashy but more useful to practitioners, and it is honestly reported. Separating on-commands, electricity and money into three layers is a model that other papers in this area could follow.

**Coherence.** Title → abstract → contributions (C1–C6) → results → conclusions are now consistent. Every abstract figure I checked traces to a table, and the conclusions do not over-promise. Two residual tensions:
- The physical unit: "compressor on-commands" versus "on-commands, not compressor starts" (F2).
- The volume of internal labels (Rule A/B/C, F1–F4, E1/E2, D1, B*/B_a, V_N), which makes the paper hard going for a general engineering readership. A notation and arm glossary, as a table in the supplement or main text, would help.

**Length.** 36/37 pages is tight. Doing F14 would free about half a page, which the multi-zone MPC results will need.

---

## 6. Recommendations to the other reviewers

- **Consistency reviewer:** check the window dates across the figure labels and the supplement's per-window tables (F1).
- **Methodology / statistics reviewers:** check that the Rule C "cheapest crossing" convention is applied identically in the multi-zone study once MPC-MZ arrives.
- **Language reviewer:** handle F2, F9, F13 and F14.

---

## 7. Verdict (EIC dimension)

**READY AFTER MINOR FIXES**, on condition that the two MAJOR items, both text-only corrections, are made. No new computation is required.

The journal-listed comments 2, 6 and 8 are fully answered. Comment 3 is answered except for the dates, which are off by one day (F1). Comment A is largely answered (F2, F9, F13, F14 remain). The response letter is truthful everywhere except the dates (F1), the compressor-start statement (F2) and one rounding difference (F3).

**Findings: CRITICAL 0 · MAJOR 2 · MINOR 15.**
