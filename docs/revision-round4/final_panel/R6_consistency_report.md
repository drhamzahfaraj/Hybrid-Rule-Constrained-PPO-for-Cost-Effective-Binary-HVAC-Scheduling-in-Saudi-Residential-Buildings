# R6 — Consistency & Contradiction Review (re-review, JKSU-ES round 4)

**Reviewer role:** Reviewer R6 — Consistency & Contradictions (agents/consistency_reviewer_agent.md)
**Mode:** re-review on the revised manuscript; ledger rebuilt from scratch.
**Material read in full:** `main.tex` (all 2,653 lines incl. captions, Algorithm 1, footnotes, declarations), `tables/tab_stats.tex`, `fig_leap.tex`, `supplement.tex`, `RESPONSE_LETTER.md`, the journal's outstanding-comments docx, `audit_report.md`; `gate_p12.log` (188/188 PASS confirmed).
**Ground truth:** `/home/claude/rbrl_p12/results/*.csv` (v3 files; the two known placeholders MPC-MZ and Zenodo DOI are excluded).

**Recommendation (consistency only): NOT READY** — one CRITICAL and three MAJOR contradictions, all fixable by text edits; no rerun needed.

---

## 1. Coverage statement

- Fact Ledger: about 420 checkable statements extracted. These are numbers, settings, names, symbols, claims, promises and limitations from the abstract, sections 1–11, Tables 1–8, Fig. 1–2, Algorithm 1, Supplement S1–S7 and Table S-MZ, and every item in the response letter. About 380 were compared across locations.
- **Numbers checked against the CSVs: more than 300**, including every one of these:
  - **Abstract:** every number (25), checked against T1v3_heldout, T21v3_*, T1v3_heldout_dt5/dt30/cth*, T2v3/T17v3_*_dt*, T17v3_*, T31_mz_*.
  - **Table 3 (tab:main):** every cell, 19 rows × 9 columns plus the THERM, B\* and ruled rows. Sources: T1v3_heldout, T_D1_latch_*, T_D1_ppo_*, rbrl_ppo5_v3_*, T21v3_{city}, T21v3_pers_*, T16v3_r23.8-22.4_*, T16v3_r23.6x-22.4_*, T17v3_{city}, T17v3_ruled_*. Every s, ΔT̃, on, fit-status and back-off value matched.
  - **Table 4 (tab:layers):** all On and Energy cells (start_sav_eq, energy_sav_eq). The SAR cells were reconstructed approximately from J_eq, f and E with the caption's formula, and all agree within the approximation (for example Riyadh TUNED 4.0–19.3 (25.5) against the printed 4–19 (25)).
  - **Table 8 (tab:timestep):** all 21 cells, plus the 5-min and 30-min on-command and electricity figures in §9.3.
  - **The bracket:** CLV raw 18.023/18.410/16.688; bounds 19.958→20.0, 19.827→19.9, 20.924→21.0; the grid series 21.3/20.6/20.2/20.0, 21.2/20.5/20.1/19.8 and 23.8/22.2/21.4/20.9; slacks 0.47/0.42/0.75; B_CLV 19.58/19.41/20.23; CLV Rule C 18.27/18.51/16.51; end temperatures; tol_met 2/1/0; 89 B_a rows all s ≤ B_a.
  - **Table 5:** all 12 HL estimates and intervals, signs, p-values and pooled Δs (T20v3_paired_stats).
  - **Table 7:** every cell (T1v3_heldout, T5v3_switchcost_tuned, T5v3_bound, T4v3_bound, T7v3_deadband, T1v3_heldout_cth*, T21v3_riyadh_cth*, T21v3_csw*).
  - **Supplement:** Tables S1, S2, S3 and S-MZ, and the AMY, orientation and setback figures (T1v3_sens, T23v3_amy_spread, T24v3_orientation, T28v3_*, T17v3sb_*, T31_mz_*, T25v3_cycling_energy, E1v3_hold_dp, rbrl_e2_v3_riyadh).
- **Arithmetic re-derived:** these all hold.
  - Λ_i = 23.75/24.62/22.67; P = 0.670; 0.375/1.25 °C; margin 2.7; ∂E/∂T = −0.191.
  - c̄\* = 0.0424 versus 0.0743 SAR/h (+75%); store 0.89 kWh; leak 6.9/13.3%.
  - Excursions 0.129/0.125/0.096; on-command shares 81.5/55.0/51.2 and 16.9/48.2.
  - Transition counts 4.1e7/2.6e11/8.0e60; SLHA errors 0.2/0.1/0.1%; window dates DOY 121–289.

**Fully consistent:** §5.5 and Table 3 (MPC, D1, guard and ruled cells); §8.1 bracket arithmetic; Tables 5, 7 and 8; Supplement S1–S5 numbers; the setback paragraph; the multi-zone TUNED and guard values; the limitation magnitudes (start-up loss 0.33–0.90%, AMY spread, orientation, hardware grid, per-window refit).

---

## 2. Contradiction Ledger

### (c) New contradictions introduced by the revision

| # | Type | Severity | Location A (quote) | Location B (quote) | Evidence | Likely correct | Fix and all locations to update |
|---|---|---|---|---|---|---|---|
| 1 | C-CLAIM / C-TAB-TXT | **CRITICAL** (Conclusion vs Results) | §11 Conclusions, l.2560–2562: "an exact one-step shield, applied to a latch **or to the trained policies, lifts them to the tuned thermostat's level**" | Table 3, row "D1 on PPO, 5 seeds" (l.1861): Taif "8.0–12.0", against TUNED 12.4 and the D1 latch 12.4; Jeddah "11.2–13.5" against 13.6. The same claim also appears at §9.2 l.2193–2196 ("the range of the D1 latch"), §8.3 l.2078–2079 ("gives the same range") and Remark 5 l.1102–1104 ("reach the same range"). | T_D1_ppo_taif.csv, σ=0, s_pooled_eq by seed: 8.04, 10.42, 8.93, 9.93, 11.97. Every Taif seed is below the latch's 12.41. Seed 42 (8.04) is 4.4 points below TUNED, a shortfall the paper's own 3-point rule counts as resolved, and it is *below* the same seed's rule-layer RBRL (8.61, rbrl_ppo5_v3_taif). Jeddah seed 46: 11.21 against 13.47. | Table 3 | Rewrite all four places, e.g. "lifts them to TUNED's level in Riyadh and Jeddah (12.8–14.1, 11.2–13.5%); in Taif the shielded policies span 8.0–12.0%, below the latch's 12.4%". Remove "the range of the D1 latch" and "same range". The response letter only claims this for the latch (l.115, l.241), which is correct. |
| 2 | C-ALG / C-NUM | **MAJOR** | Remark 1, l.517–520: the two-sided condition (eq. deadband_condition); "the looser form cannot adjudicate the admissibility sweeps it is used for" | (i) Remark 1, l.530–533: "An hourly interval would require $C_{th}\ge Q\Delta t/\delta_{db}=7{,}200$ kJ/K". (ii) Conclusion rec. (ii), l.2584: "Check the actuation condition $Q\Delta t/C_{th}\le\delta_{db}$". (iii) Supplement S1: "$C_{th}\ge Q\Delta t/\delta=1{,}800$ kJ/K", with Table S1 marking 1,800 "marg." and 30 min "adm. yes". | With ε_hot = 0.2 the upper limit is 2 − QΔt/C − 0.2. At 1 h this needs QΔt/C ≤ 0.8, so C ≥ 9,000 kJ/K, not 7,200. At 1,800 kJ/K the upper limit is 0.8 < 1, so the configuration is inadmissible. At 30 min, eq. (guard) gives ε_hot ≥ 2 × 0.129 = 0.258, the upper limit becomes 0.99 < 1, and the condition fails. THERM does leak 0.025 deg-h at 30 min (Table S1; tests/test_f23_timestep.py). §9.3 compares TUNED, held to zero over-temperature, with this leaking THERM without saying so. | Remark 1's two-sided form | Use the two-sided condition throughout: 1 h → "≥ 9,000 kJ/K"; recommendation (ii) gives both bounds; Table S1 marks 1,800 kJ/K "no" and 30 min "no (THERM leaks 0.025 deg-h)". Add one sentence to §9.3 that at 30 min the baseline itself violates the ceiling. |
| 3 | C-TAB-FIG | **MAJOR** | Fig. 1 caption (fig_leap.tex): "2.90 switch-ons per day—within 4% of the **3.00 measured for the clairvoyant optimum (Table~\ref{tab:main})**" | Table 3 prints no on-commands per day for CLV; its CLV row gives "−31.1" (% on-commands, Riyadh). | T17v3_riyadh clv_start_sav 31.115 with THERM 4.102 on/day gives 2.83/day (Jeddah 3.735 × 0.688 = 2.57; Taif 2.33 × 0.739 = 1.72). No 3.00 appears in any v3 file I checked, and a constant 40 °C example is not comparable with held-out weeks anyway. | Results files | Delete the clause or give a sourced value with its conditions. Also, l.1 of the caption says "Proposition~\ref{prop:structure}", which renders as the nonexistent "Proposition 2"; it should be "Observation". |
| 4 | C-SET / reporting accuracy | **MAJOR** | §8 preamble, l.1694–1700: "Commanded under-temperature is zero for every receding-horizon arm except the Riyadh 6 h persistence controller … 0.0006 °C·h … in Taif TUNED and the guard also free-float below the band" (only TUNED's free-float is given). Abstract and C1 call the cold rule "hard". Response letter l.229 lists only the MPC value as disclosed. | T1v3_heldout.csv deg_h_cmd_under: TUNED Jeddah 0.00067, **Taif 0.0066** °C·h (11 times the disclosed MPC value). Also TUNED-SB Riyadh 0.0102 (T28v3_setback_rule); TUNED at 30 min 0.0097 and 0.0025 (T1v3_heldout_dt30); TUNED at 7,200 kJ/K 0.0047; the no-rules PPO seed 0.0065. | — | The CSVs | State it next to the free-float sentence: "TUNED's cooling steps end below the band by 0.0007 and 0.0066 °C·h in Jeddah and Taif (TUNED-SB 0.010 in Riyadh); the optimisers hold this as a hard constraint, the model-free arms do not". Update the response letter l.229. |
| 5 | C-NUM | MINOR | §8.3 l.2035: margin over TUNED "15.0, **5.8**, 3.8 and 0.4 points" | Table 5 F2 Riyadh pooled Δs "**+5.7**"; response letter l.68: "15.0, **5.7**, 3.8 and 0.4" | T20v3 d_pooled = 5.738 (18.264 − 12.526). 5.8 is a difference of rounded values. Likewise F2 Jeddah +4.4 against Table 3's 18.1 − 13.6 = 4.5. | 5.7 | Print 5.7 in §8.3. Add one line to the Table 5 caption: "pooled Δs computed before rounding". |
| 6 | C-CLAIM | MINOR | §8.3 l.2054: "**Elsewhere** the fitted multiplier lies far above λ\*: 1.226 and 4.577 … 13.094, 2.326, 6.218 … 2.089 and 1.801" | Fitted λ/λ\* elsewhere: perfect 0.25–2 h 0.986–1.014; Taif 48 h 1.003; persistence 6 h 1.004/1.007; guard-rule cells 0.60–1.00; training-rule 1 and 6 h ≈ 1.00. | T21v3_*.csv, T21v3_pers_*.csv, T16v3_*.csv lam_over_lam_star | CSVs | Replace "Elsewhere" with "In these cells". |
| 7 | C-SET (provenance) | MINOR | Table 7(a) superscript ^e "energy-only terminal" on 29.6 and 18.6; Remark 3 l.781 "under the energy-only terminal"; §8.1 l.1805 and Table 3 "B\* energy-only 20.0/20.1" | The v3 file for these cells, T4v3_bound.csv, uses `terminal = energy at rated COP + c_sw/1 K per K` (V_N). The energy-only values exist only in round-3 files T4v2_bound.csv and T17v2_{riyadh,jeddah}.csv (same rounded values). | — | Both agree to 0.1 | Either label the 0.05 and 0.21 rows V_N (the v3 source) or state that the energy-only B\* comes from the round-3 runs. Also "B\* is reported under both terminals" (l.1483, l.2484) is not true for Taif ("---" in Table 3); add "(Riyadh and Jeddah)". |
| 8 | C-PROMISE | MINOR | §8.1 l.1792–1793: "$B_a$ is printed where it differs from $B^\ast$ by at least 0.1 point" | No $B_a$ is printed for any causal arm in Table 3, the text or the supplement; only B_CLV is. | T17v3_Ba.csv has print_B_a = True for most arms, e.g. TUNED Riyadh B_a 19.75, Taif guard 21.38. | — | Add a B_a column (or a supplementary table), or change the sentence to "is in the results file T17v3_Ba". |
| 9 | C-REL | MINOR | Conclusion l.2554–2556: TUNED's 12.5/13.6/12.4% "is 69–74% of the best attained schedule … and 59–68% of the provable bound" | §8.1 l.1789–1800 says a saving at an arm's own mean is read against $B_a$, and CLV's Rule-C saving is "never [compared] against $B^\ast$". The ratio mixes TUNED's Rule-C saving under the simulator terminal with the V_N raw bracket at THERM's mean. | T17v3_Ba: TUNED s_a(V_N)/B_a = 12.69/19.75 = 64%, 13.18/20.21 = 65%, 12.89/20.78 = 62%. | §8.1's rule | Quote s_a/B_a (62–65%), or state that the ratio uses different terminals and means. |
| 10 | C-SET (stale) | MINOR | Remark 3 l.773: "Model L **is evaluated** at 0.12 SAR/kWh"; §6.2 l.1554: "for Models L and E, $c_r^L=0.12$ is adopted" | No result in the manuscript or supplement uses Model L or E at 0.12. The response letter l.148 says the three-cost-model comparison is withdrawn. | — | Results | Use "would be evaluated" or delete; keep 0.12 only as the reference for the "falls by a third" argument. |
| 11 | C-SET / C-NOT (stale) | MINOR | Definition (schedule), l.930: "$H=720$ hours for a 30-day month" | Δt = 15 min throughout; Algorithm 1 uses N = 672 steps per 168 h. | 720 steps is an hourly-step remnant; a 30-day month has 2,880 intervals. | Δt = 15 min | "$H=2{,}880$ intervals of 15 min". |
| 12 | C-NAME | MINOR | Abstract l.125 "compressor on-commands"; §8.2 l.1916; Conclusion l.2536; response letter l.27 | §3.3 l.646–648: "whether each on-command corresponds to a compressor start … is not established"; limitation l.2454 "On-commands, not compressor starts"; response letter l.244 "the manuscript no longer equates them with compressor starts". | — | §3.3 | Drop "compressor" in all four places ("supervisory on-commands"). |
| 13 | C-SET | MINOR | §3.2 l.632: linear array, "end zones have one windowed exterior wall while interior zones couple to two neighbours" | Table S-MZ: 1×4 glazed faces "S, S, N, N" (interior rooms glazed) | — | Table S-MZ (as run) | Restate §3.2 to say each room has one glazed face at the azimuths of Table S-MZ. |
| 14 | C-ALG | MINOR | §3.4 l.744: the cost rate's dependence on $E_{cum}$ "requires $E_{\mathrm{cum}}$ to be carried in the agent state" | §5.2 l.1245–1249: $E_{cum}$ is not observed. | — | Both, in context | Add "under Model S" at l.744. |
| 15 | C-PROMISE | MINOR | §4.2 l.921–922: a minimum-dwell rule set "is identified as required work in Section~\ref{subsec:disc_limits}" | The limitation "Scope of the learner" (l.2515) only says R1/R2 impose no minimum dwell; it does not call it required work. | — | — | Add "a minimum-dwell rule set is required work" to that item, or soften l.921. |
| 16 | C-NUM | MINOR | §8.2 l.1924: "the identity holds to within $3\times10^{-5}$ relative" | T25v3_cycling_energy.csv energy_identity_rel: maximum absolute value 3.6×10⁻⁵ | — | CSV | "within $4\times10^{-5}$". |
| 17 | C-REL (unverifiable) | MINOR | §7 l.1673–1675: "a 15-year life at the model's on-command rate gives about 0.114 SAR" | With the paper's own 184-day season (Table 4 caption) and THERM's 4.10 on/day: 2,500/(15 × 184 × 4.10) = 0.22 SAR. A value of 0.114 implies about 1,460 on-commands a year (about 4/day over 365 days) for a cooling-only plant. | The derivation's inputs are not in the code or the manuscript. | — | State the assumed annual on-command count and season length. If it is 184 days, the upper end of the derived range, and every "0.025–0.114" figure (abstract, Table 4, Table 7(b)), must be rechecked. |

### (a) Contradictions from the previous version that are now fixed

These were verified absent or resolved: the "lower bound" air-mass claim (0 hits); "unaffected" by time step; "actual Saudi step-wise tariff"; 18.2% and 16.8%; the NP-hardness claim; the test-year and 30-week description (one protocol, with dates matching DOY 121–289 exactly); the GA/SA results.

### (b) Still present from earlier rounds
None found beyond the items above.

---

## 3. Response letter (truthfulness and completeness)

- **All five journal items (2, 3, 6, 8, A) and the editor's instruction are answered.** Every quoted manuscript sentence I sampled (about 25) appears verbatim. The section, table and remark numbers (Remark 1–5, §§2.4–10.4, Tables 1–8, S1/S2/S-MZ) resolve correctly.
- **The numbers in the letter match the manuscript and the CSVs**, with two exceptions:
  - l.68 gives 5.7 where the manuscript says 5.8 (Ledger #5).
  - l.27 uses "compressor on-commands" while l.244 says the manuscript no longer equates them with compressor starts (Ledger #12).
- **l.229 discloses only the MPC's commanded under-temperature.** TUNED's larger values are not mentioned (Ledger #4).
- **l.36 "all invariants pass" is confirmed:** gate_p12.log reports "GATE PASSED - all 188 invariants hold".
- **l.185 is accurate** (THERM leaks 0.025 at 30 min), but the manuscript body does not say this (Ledger #2).
- **Comment 2:** declining the reviewer's proposed replacement sentence is justified and stated transparently.

## 4. Paper Quality Standard checklist (R6-owned items)

| ID | Status | Note |
|---|---|---|
| Q1.3 terminology and notation | Partial | "compressor on-commands" (#12); Observation cited as "Proposition" (#3); H in hours (#11) |
| Q1.4 no contradictions between sections | Fail | #1, #2 |
| Q1.6 repeated numbers identical | Partial | #5, #16; otherwise every repeated number matched (abstract ↔ body ↔ tables ↔ supplement ↔ letter) |
| Q2.5 contributions supported as stated | Pass, except C4's D1 clause, which holds for the latch only (#1) |
| Q3.3 results answer the claims in the Conclusion | Partial | #1, #9 |
| Q4.7/Q9.6 figures and tables match the text | Partial | #3 |
| Q11.3/Q11.4 pseudocode matches the method | Pass | Algorithm 1 matches §5.4 on budget, rollouts, ceiling grid, R1/R2 and Rule A/C |

## 5. Notes (not defects)

- The unreported files T31_mz_rules_riyadh_{1x2_m1,1x4_m2,2x2_m2,*_mnone}.csv appear to be shared-plant arbitration runs; the Data section says that code path is unreported. They are in the old format, with no fit_status or provenance. Consider moving them to the archive so a reader does not take them for the reported multi-zone results.
- The CLV end-of-window offsets under the energy-only terminal (0.49/0.77 K, l.2481) could not be traced to a v3 file. Treat as unverified.

## 6. Verdict

**Consistency dimension: NOT READY.** It becomes READY once items 1–4 are corrected. These are text and caption edits only; no experiment needs rerunning. The numerical core (Tables 3, 5, 7 and 8, the bracket and the abstract) agrees with the results files to the printed precision.

**Findings by severity: CRITICAL 1 · MAJOR 3 · MINOR 13.**
