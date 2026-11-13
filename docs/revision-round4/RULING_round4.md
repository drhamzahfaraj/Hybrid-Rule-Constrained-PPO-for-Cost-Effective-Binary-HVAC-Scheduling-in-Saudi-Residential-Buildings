# RULING — JKSU-ES major revision, round 4 (binding)

Editorial Synthesizer, 12 Nov 2026. Deadline 23 Nov 2026. Page limit 35 (current build 40 pp elsarticle / 41 pp sn-jnl, `main.log` l.1465).
Editor's instruction: report results accurately, rewrite overstated conclusions, explain the limitations fully.

**Inputs read:** CONTEXT, TEAM_BRIEF, SYNTHESIS_and_PLAN (round-3 ruling), ERROR_BOARD (rows 13–158), and all 22 reports (R1, R4, R5, DA_R6, the six SPEC_*, and the twelve TEAM_*).
**Also checked:** `status.py`; `main.tex` title, abstract, section map, `\pend` lines and Funding l.2842; `logs_T21v2_jeddah` timings; `origin/main` tree of the public repo.
**Files changed:** none, except this one.

**Binding scope.** This ruling supersedes SYNTHESIS_and_PLAN where they conflict. Everything else in it stands. The superseded items are listed below.

| Round-3 item | Superseded by |
|---|---|
| (a) Rule A: per-window ±0.03 K test, with the fallback "printed" | §2.2: one selection rule for every arm, one fallback, and a `fit_status` column |
| (b)2 "MPC never does worse than TUNED on the Lagrangian" | Withdrawn (E-control1-1). Wording in §7.2 |
| (b)4 and loophole fix 6: the sub-band predicate (u=0 may end below T_min only if T∞,0 < T_min) | §2.1 corrected cold rule |
| (c) CLV scored one-sided, pooled, against unshifted THERM | §2.3: CLV scored under Rule C like every arm. Bound reported as B(T_a) per arm |
| (d) latent fallback date 17 Nov | Fallback taken now (§5, C31) |
| Title wording in (e) | §6 decision tree |

---

## 0. Decision and the five things that matter

**Decision: MAJOR REVISION stands.** Resubmission is feasible by 23 Nov, provided the five items below are done. They are listed in order of importance.

1. **One protocol for every arm (§2), then rerun everything printed.**
   - Today the MPC, the guard and RBRL are admitted on a pooled fallback that TUNED never gets.
   - Rule arms are rejected for under-temperature; MPC is not.
   - The cold-coasting predicate traps legitimate recoveries.
   - Every downstream table consumed the pre-refinement TUNED.
2. **The headline has reversed.** MPC beats TUNED at every horizon (15.6–19.2 % vs 4.0–13.1 %). The manuscript still argues the opposite in about 40 places. The pre-committed rule (b)7 is triggered and must be executed.
3. **Attribution is untested.** "Lookahead" and "Not Learning" are not supported yet.
   - The 6 h horizon already gives 81–85 % of the 48 h gain.
   - The PPO reward has no λ term, so the PPO collapse is the correct optimum of its own objective.
   - The cheap decisive experiments in §4 settle the title. The title is pre-registered in §6.
4. **Three CRITICAL disclosures, owned by specialists, cannot be outvoted:**
   - what a "start" is physically (E-hvac1-1);
   - the dependence of the MPC-over-TUNED gap on the assumed thermal capacity (E-bldg3-1);
   - the perfect-model, perfect-forecast idealisation now flatters the winning arm (E-control3-1).
5. **Extensions.** Setback goes in only through a gate. COP, the 24 °C scenario, RBRL-SB and multi-zone stay out of the paper. Five to six pages must be cut.

**Specialist CRITICALs that are accepted in their own domain and not outvotable:**
- E-hvac1-1 (HVAC)
- E-bldg3-1 (building physics)
- E-control3-1, E-control2-3 (control)
- E-cs2-1 (CS/RL)
- E-opt2-4 (optimisation)
- E-sw-1 (software)
- E-DA-1 = E-R1-1 (methods core)

---

## 1. Consensus table (board rows deduplicated into clusters)

Severity is the highest given by any reviewer, except where the cluster records a downgrade. Verdicts: **A** = ACCEPT, **P** = PARTIAL, **R** = REJECT. "Fix ref" points to §2–§7.

| # | Defect cluster | Sev | Raised by (board IDs / reports) | Verdict | One-line reason / fix ref |
|---|---|---|---|---|---|
| C1 | Rule A asymmetric. TUNED is per-window only, with no fallback. Guard (Taif), all 10 MPC cells, RBRL and MPC-MZ use the pooled fallback. The text claims the table flags it; it does not | **CRIT** | E-DA-1, E-R1-1, E-opt3-2, E-control1-2, R5-4, CTL1-3, E-cs2-5, DA-11 | **A** | Same hysteresis family gives 4.0 % vs 11.0 % in Taif purely by admission branch. §2.2 |
| C2 | Comfort admissibility differs by arm: rules use over+under, MPC uses over only. Jeddah TUNED leaks under-temperature held out. Text says "over" | MAJ | E-R1-2, E-sw3-1, E-opt3-1, CTL1-14 | **A** | §2.1: over pointwise plus *commanded* under for all arms |
| C3 | Cold-coasting predicate is not Markov: dead states, so THERM, guard and the MPC recovery in Taif fall outside the DP/bound domain. T21v2/T17v2/T27 predate it anyway | MAJ | E-R5-2, E-opt1-2, E-opt2-1, E-main-3 | **A** | §2.1 corrected rule. Rerun MPC, CLV, bound |
| C4 | Mixed provenance. Downstream used pre-refinement TUNED params. Results predate code. T28 lacks `away_on`. T20v2, T5v2, T22v2 stale | MAJ | E-sw-2, E-opt2-3, E-hvac2-1, E-hvac3-4, E-cs2-8, E-R1-3, E-control3-4, E-building2-3 | **A** | R5-14 is correct that T21v2 is barely affected by the base params, but every table is rerun under §2 anyway. §3 F1–F2 |
| C5 | Refined tuner: is it legitimate? Resolution dependence; noise floor 2–3.4 pts; stale search audit; thresholds below hardware resolution | MAJ | E-main-1, DA-9, E-cs3-5, E-opt3-4, E-opt3-8 | **P** | Legitimate: no held-out leakage (R1, opt-3), so the "unverified legitimacy" suspicion is rejected. Disclose the procedure. Add a 0.1 K hardware-resolution row. Resolution rule: no ranking below 3 pts |
| C6 | Deadband sign and AMY collapse are tolerance artefacts. The −2.2 % was a grid artefact. l.2680 misattributes the guard's −3.4 % to TUNED | MAJ | E-main-2, E-R1-6, E-opt3-3 | **A** | Withdraw every deadband-sign claim. Rerun T7 under §2 |
| C7 | MPC gain mechanism unidentified. "Lookahead" unsupported; "Not Learning" confounded with "not informed / not asked" | **CRIT** | E-cs2-1, E-DA-3, E-control3-3, E-DA-5, C3-2 | **A** | X1–X4 in §4. Title per §6 |
| C8 | Perfect in-horizon forecast and perfect plant model now favour the winner. "No forecast-error study needed" is inverted | **CRIT** | E-control3-1, E-DA-4, E-bldg3-2 | **A** | Persistence MPC is REQUIRED (X1). Disclosure in §7.2 |
| C9 | PPO null is by construction: the reward has no λ term, so hold is the λ=0 optimum. Corollary's reach misdescribed. About 7 pts of room inside the rules (MPC-in-rules 13.4 vs 6.0). "Rules alone determine the cost" is false | **CRIT** | E-control2-3, E-csrl-3, E-cs2-2, E-control1-4, CTL1-8 | **A** | E2 experiment (X3). SPEC_control §6.3 replacement text |
| C10 | The in-rule clairvoyant (T27) is used as an *upper* bound, but it is an attained replay. It also uses R1 = 23.80 while the arms use fitted R1 | **CRIT** | E-opt2-4, E-control2-1, E-control2-2 | **A** (E-control2-1: **P**) | Run the ruled relaxed bound or delete the sentence. Comparing within the *training* rule set is legitimate if labelled so (SPEC_control §6.4) |
| C11 | RBRL ≡ guard: 8/10 bit-identical. "Nine of ten / 0.3 % / SD 0.21" stale. Taif is not identical (8.6 vs 11.0, different branch) | MAJ | E-cs3-1, E-cs2-3, E-csrl-2, DA-17 | **A** | Report as collapse to hold; seed SD carries no information. Taif re-capped under §2 |
| C12 | "Invalid-action masking [Huang2022]" is wrong. The layer is a post-sampling override (shield). No bias | MAJ | E-csrl-1 | **A** | Text only (SPEC_cs_rl §4) |
| C13 | No-rules ablation: stale counts, "quadratic" vs linear penalty, misread as proof that the rules are needed | MAJ | E-cs2-4, DA-14 | **A** | Report from the file: 4 of 5 seeds violate; seed 46 has 0 °C·h and 6.4 %. Write "linear". Interpret as this configuration's optimisation failure. No rerun |
| C14 | Rollout improvement guarantee claimed; it does not hold (truncated, persistence tail, grid, base mismatch) | MAJ | E-control1-1, R5-16, CTL1-2 | **A** | §7.2 wording. Optional exact-tail oracle (O6) |
| C15 | λ knife edge: fitted λ = 1.004–1.024 λ*, with λ* = ΛHp/COP. The Lagrangian is flat in level there, so the MPC is a start-minimiser and per-window parity is unattainable | MAJ | E-R5-1, CTL1-3, R5-10 | **A** | Disclose the identity, the λ/λ* column and a sensitivity row (X8). Quadratic regulariser (R5-1 iv): **R** for this revision |
| C16 | MPC > "attainable" CLV, caused by CLV over-cooling (one-sided coarse λ_w) and two conventions | MAJ | E-main-5, E-DA-2, E-control1-7, CTL1-5 | **A** | CLV refit two-sided, scored under Rule C. Lower end = best attained schedule (§2.3) |
| C17 | Bound not shown to cover warmer arms; the "every controller below the bound" invariant is missing; same-target per-window checks give false alarms | MAJ | E-opt2-2, CTL1-6 | **A** | B(T_a) per arm plus the shifted dual certificate (§2.3) |
| C18 | Bracket text stale and mislabelled: "grid-converged", "duality gap", proof sketch incomplete, `\pend` l.1897 | MAJ | E-opt2-5, F-3, F-8 | **A** | SPEC_optimisation §5.1 text |
| C19 | Terminal value prices stored heat but not the saved start, so the window end is rewarded for oracles. Bracket inflated by up to 1.9/2.2/3.5 pts | MAJ | E-opt1-1 | **P** | Disclosure and a T_end column are REQUIRED. Uniform re-scoring is OPTIONAL (O4); it becomes REQUIRED if CLV T_end − THERM T_end > 0.3 K pooled |
| C20 | Gate G1 MPC convergence run absent; true grid spacing in Taif is coarser than stated | MAJ | E-control3-5, E-control1-3, R5-5, E-sw2-5 | **A** | X7. Print h per city |
| C21 | Manuscript describes the withdrawn ceiling-MPC; every printed MPC finding is reversed; 56 h mechanism | MAJ | E-R5-3, E-control1-5, DA §3.3 | **A** | §7 |
| C22 | Stats stale. Holm p = 0.047 is the attainable floor. Families undeclared. BCa vs HL | MAJ | E-R1-3, R5-13, R1-m5, E-cs2-8, DA-15 | **A** | §2.4 |
| C23 | Two saving conventions (pooled vs mean ± sd of s_w) | MAJ | E-R1-4, CTL1-16 | **A** | Pooled s only (§2.3) |
| C24 | The MPC/DP-over-TUNED gap depends on C_th: 18.7 → 0.3 pts from 2400 to 9600 kJ/K (old table). Effective capacity at cycle period is about half. "Bias largely cancels" is false. G14 mislabel | **CRIT** | E-bldg3-1, E-bldg3-3, E-bldg3-6 | **A** | X5 C_th sweep under protocol, REQUIRED. Disclosure in §7.2 |
| C25 | Equipment interface unspecified. u = 2 kW for 15 min out of the lumped node; a real split unit cycles on return air. "Starts" saved are supervisory on-commands, not shown to be compressor starts. 4 starts/day is a model artefact | **CRIT** | E-hvac1-1, E-hvac2-5, E-bldg3-3 | **A** | Disclosure and renaming REQUIRED (§7.2-a). Two-node sensitivity OPTIONAL but recommended (O1) |
| C26 | "Energy moves −0.3..+0.5 %" is a terminal-store artefact. Matched arms use identical energy, so saving = c_sw × Δon-commands. Cycling-energy table reads v1 | MAJ | E-hvac2-4, E-hvac2-2, E-sim-7 | **A** | Decomposition column; port `cycling_energy.py` |
| C27 | c_sw: sweep stale; abstract prints interpolated 7.7 %; 0.15 SAR/start exceeds whole-unit straight-line depreciation; ranking across c_sw unsupported | MAJ | E-hvac2-1, E-hvac2-3, E-hvac2-5, DA-12 | **P** | Keep 0.15 as the *computational reference*, because the PPO models were trained at 0.15. The abstract and conclusions lead with the derived range 0.025–0.114 from rerun T5. State that 0.15 exceeds whole-unit depreciation. Run MPC-24 at 0.025/0.114 (X10) or delete l.1773 |
| C28 | Unsourced 2 kW; COP 2.985 below SASO MEPS; no internal gains; tiny energy term inflates percentages | MAJ | E-hvac1-5, E-building2-4, E-building2-5, E-hvac1-7, F-9 | **P** | Disclosures REQUIRED with bias directions. Q sweep OPTIONAL (O2). Do not raise COP now (cascade) |
| C29 | Comparator sampled at 15 min, so the 1.25 K deadband ceiling is an artefact | MAJ | E-hvac1-6 | **P** | Disclose. Sub-stepped THERM OPTIONAL (O3) |
| C30 | ε_cold derivation fails at negative net load (Taif guard 0.339 °C·h) | MAJ | E-control2-4 | **A** | Under-temperature columns for every arm; qualify "by construction". D1 shield (X4) gives the model-exact alternative |
| C31 | Latent study: free dehumidification, capacity inflation, whole-dwelling moisture in one room, own unrefined tuner, stale and sign-wrong text | MAJ | E-hvac3-1..4, -8, E-sim-1..3, -10, E-DA-7 | **A** | Fallback taken now: withdraw the claims, two sentences in Limitations, rebuild S1 or delete it. No latent numbers in the paper |
| C32 | Setback: baseline cools the empty house; no MANUAL arm; vacation windows; cap never binds; mechanism is starts, not envelope; stale T28; TUNED-SB not nested; Taif = no setback; tail occupancy misaligned; constant capacity flatters recovery; no internal gains | MAJ | E-DA-6, E-bldg1-3, E-bldg1-4, E-building2-2/3/6, E-hvac1-2/3, E-bldg3-9, E-opt3-5, E-control3-4, R5-7/CTL1-11, E-cs3-4 | **A** | Gate in §5 |
| C33 | COP(T_out) option: no capacity derating; train/score mismatch; terminal at rated COP; identity breaks; source unverified; no results | MAJ | E-hvac3-7, E-bldg3-8, E-sim-6, E-sw-6, CTL1-12 | **A** | REPOSITORY |
| C34 | 24 °C scenario: TUNED ≡ THERM by construction; unequal pointwise vs deg-h allowance; hard-coded bands; asymmetric band | MAJ | E-main-6, E-building2-1, E-sim-8, E-R1-5, E-sw3-2, E-sw-3, E-sw-5 | **A** | DROP. building-2's "in paper if reframed" is rejected as a minority view on a non-critical item |
| C35 | RBRL-SB: no results; BC filter admits forbidden actions; unruled teacher; train/deploy cap mismatch; margin below one step; no empty-house R2; information mismatch | MAJ | E-cs3-3, E-csrl-4, E-cs2-7, E-control2-5, E-cs3-4 | **A** | DROP from paper. Replaced by E2 (X3) |
| C36 | Multi-zone: two writers to one file; λ-batch coupling in the code of record (mz_mpc l.88); setback terminal; R1 void under arbitration; phantom starts; impossible 2×2 plan; design cannot exhibit coupling; ranking flips with the plant model; "coordinated" mislabel | **CRIT** (E-sw-1) | E-sw-1, E-sw3-3, E-sw-8, E-cs3-2, E-hvac2-6, E-hvac3-5, E-hvac1-4, E-bldg1-1, E-sim-4, E-bldg1-2, E-bldg3-7, E-control1-6, CTL1-10, E-DA-8 | **A** | §5. mz_r3 λ-mean coupling (E-sw-9, E-control3-2, E-cs2-6) is downgraded to MINOR (dead code, per E-cs2-6a and E-control3-2a): delete the code. E-sw3-3 keeps it MAJOR for mz_mpc l.88 |
| C37 | AMY/orientation use the old convention. ERA5 is 1 h late. Source vs year confounded. "Held-out" weeks are interleaved within months | MAJ | E-bldg3-4, E-bldg3-5, E-sim-5, E-sim-9, R1-m4 | **A** | Rerun under protocol with the ERA5 shift fixed (X11), or remove the numbers. Write "interleaved held-out weeks" |
| C38 | Software: hard-coded band and R1/R2; TAG not applied; non-atomic writes; DictWriter crash; four c_sw sources; runner never reconciles; gates read v1 only; silent fallbacks | MAJ | E-sw-3..7, -10, S11–S14, E-sw2-3/4/5/6/10, E-control2-6 | **A** | §3 |
| C39 | Repo: EPWs tracked although the text says they are not redistributed (and already public on origin/main, commit d00a6e4); repo is a pre-round-3 snapshot; CI broken; models excluded; README/CITATION stale | MAJ | E-sw2-1, -2, -7, -8, -9 | **A** | §3 F20. EPW decision belongs to the author (§8) |
| C40 | Body contradicts title; revision-history phrases; `\pend` placeholders; abstract about 400 words; 40–41 pp | MAJ | DA §3, E-bldg1-5, DA-10, DA-16 | **A** | §7 |
| C41 | Funding statement unverified (thanks DGSSR, but the author said no external funding) | — | DA ledger l.2842 | **A** | Author decision (§8) |
| C42 | `queue.py` shadowed stdlib | CRIT (fixed) | E-main-4 | **A** (closed) | Keep test 1 |

No CRITICAL or MAJOR cluster is rejected outright. The rejected sub-points are: the suspicion that the refined tuner is illegitimate (C5); the quadratic λ regulariser (C15); building-2's in-paper COP and 24 °C rows (C33, C34); and the MAJOR rating of the dead-code λ-mean coupling (C36).

---

## 2. The single protocol (applies to EVERY arm and oracle)

Arms covered: THERM, THERM(δ), TUNED, guard, RBRL, D1-shielded latch, MPC (all horizons and forecast modes, in-rules), E2-PPO, CLV, bound, and the setback arms. The rules below are exact, and the code must implement them in **one** helper module (`final_tables` / `protocol`).

### 2.1 Comfort (both sides)
- **Upper, pointwise, for all arms and all oracles.** On every occupied step, the post-step T_{k+1} ≤ HI = 24.0 °C.
  - Metric `deg_h_over` = Σ_occ max(0, T_{k+1} − HI)·Δt.
  - No deg-h budget anywhere: delete `F.DEGH_ALLOW`.
  - Away steps (setback only): T_{k+1} ≤ AWAY_MAX = 30 °C for every arm. Rule-arm away thresholds are tied to it (on at AWAY_MAX − 0.2). Report `T_max_away`.
- **Lower: the corrected cold rule.** *Cooling may never end a step below T_min; free-float is unrestricted.*
  - Formally: u_k = 1 ⇒ T_{k+1} ≥ T_min = 22.0 °C at **every** step, occupied or away. u_k = 0 has no lower limit.
  - Delete the T∞,0 predicate everywhere.
  - Sub-band states can then arise only by free drift with T∞,0 < T_min. That closes the cold-coasting loophole by construction (R5-2, E-opt1-2) and keeps the relaxation proof, because the predicate is state-independent.
  - In optimisers (DP, MPC, CLV, bound): a hard constraint on u = 1 transitions.
  - In model-free arms (THERM, TUNED, guard, RBRL, setback rules): a measured quantity.
- **Metrics emitted by every simulator path** (`setback.sim`, `sim_hyst_batch`, `mpc_lambda`, `r3_dp.replay`, `rbrl_ppo.evaluate`):
  - `deg_h_cmd_under` = Σ over steps with u=1 and T_{k+1} < T_min of (T_min − T_{k+1})·Δt;
  - `deg_h_ff_under` = the same over u = 0 steps, occupied only;
  - `deg_h_over`, `T_end`, `T_max_away`, `fallback_steps`.

### 2.2 Selection on tuning windows (Rule A4; one rule, one fallback, `fit_status`)
For every causal arm and every parameter family:
- TUNED (on, off); guard and RBRL ceiling; MPC λ (per city, horizon, forecast mode); D1 margin σ; TUNED-SB (lead L, away thresholds); E2 post-training ceiling if one is used.

**Admissible candidate p** if all of the following hold:
1. On **each** w ∈ TUNE_W: `deg_h_over_w(p) = 0` and `deg_h_cmd_under_w(p) = 0`.
2. Pooled over TUNE_W: |T̃̄(p) − T̃̄_THERM| ≤ 0.03 K, with T̃ = max(T, T_min) (Rule B).

**Objective:** minimise the **equalised tuning cost ratio** Σ_w J_w(p) / Σ_w J_THERM(δ_w(p)),w (Rule C applied on TUNE_W).
- Precompute J_THERM(δ) per tuning window once, on the δ grid of §2.3.
- This aligns selection with evaluation and removes the reward for being warmer (R1 m3).

**One fallback, identical for all arms:** if no candidate meets condition 2, relax it to ≤ 0.10 K pooled.

**`fit_status` ∈ {`pooled_0.03`, `pooled_0.10`, `none`}.** It is written in every arm CSV and printed in every table footnote. `none` rows are refused by the writer and never tabulated; they are reported in words as "no admissible parameter".

**Sensitivity, supplement only:** TUNED and guard refitted under the old per-window ±0.03 K criterion, plus TUNED at a 0.1 K hardware grid (C5). The headline uses A4.

**Oracles:**
- CLV: λ_w per held-out window, refined by bisection to |T̃̄_w − T̃̄_THERM,w| ≤ 0.002 K (two-sided), then scored by Rule C. `fit_status = oracle`.
- Bound: no selection (§2.3).

### 2.3 Evaluation and the saving convention (Rule C; one convention)
- **Comparator per held-out window:** THERM(δ_w), on at 23.5 + δ, off at 22.5 + δ.
  - Scan δ ∈ [−0.4, 0.4] in 0.002 K steps.
  - Interpolate J linearly between the bracketing δ, at the arm's T̃-mean.
  - Record `bracket_gap` (K and SAR). The invariant is on bracket_gap; `resid` is vacuous (R1 m1).
- **The only saving printed:** s = 1 − Σ_w J_arm,w / Σ_w J_THERM(δ_w),w, over the 7 held-out windows.
  - s_raw (vs unshifted THERM), pooled ΔT̃, max|ΔT_w| and all §2.1 metrics are printed beside it in the main table or the supplement.
  - Per-window s_w appears only inside tests.
  - No "mean ± sd" of savings anywhere.
- **CLV** uses exactly this convention (supersedes round-3 (c)).
- **Bound:**
  - The headline is B* = 1 − L*(T̃*)/Σ_w J_THERM(0),w, with L* from the relaxed DP (rounded outward to 0.1), at THERM's pooled mean T̃*.
  - For **each** arm a, print B_a = 1 − L*(T̃̄_a)/Σ_w J_THERM(δ_w^a),w. Then s_a ≤ B_a holds exactly (any λ ≥ 0 is valid). Print B_a only where it differs from B* by ≥ 0.1 pt.
  - Per-window invariant: the shifted dual certificate J_a,w ≥ J^bd_w − λ_w(T̃_a,w − T̃_THERM,w)/7 (CTL1-6).
- **Bracket wording:**
  - lower end = "best attained schedule at THERM's mean" = max(CLV, any arm with |ΔT̃| ≤ 0.002 K);
  - upper end = "provable bound under the model";
  - gap = "duality gap plus relaxation slack plus replay suboptimality".
  - Never "grid-converged", never "attainable optimum".
- **Terminal pricing:** unchanged, and identical in every path (price·(T_N − T0)·C/COP_rated). Report the pooled T_end per arm (C19).
- **Cost decomposition columns:** on-commands per day and Δ%, terminal-priced energy, and the c_sw·Δon-commands share of the saving.

### 2.4 Statistics (one family structure, pre-declared)
- **Unit:** per-window equalised saving difference d_w between two arms (n = 7, same windows).
- **Tests:** exact two-sided Wilcoxon signed-rank, exact sign test, and the exact Hodges–Lehmann estimate with a 95.3 % CI (3rd smallest and largest of the 28 Walsh averages). No bootstrap, no BCa.
- **Primary families**, each = one contrast × 3 cities, Holm within the family:

  | Family | Contrast |
  |---|---|
  | F1 | TUNED vs THERM |
  | F2 | MPC-24 (perfect) vs TUNED |
  | F3 | MPC-24 (persistence) vs TUNED |
  | F4 | guard vs TUNED (price of guarantee) |
  | F5 | E2-PPO vs guard (only if X3 runs) |

  - State that 0.047 is the attainable Holm floor at n = 7 with 3-member families.
  - Lead with the HL estimate and CI; the p-value is secondary.
  - Never write "significantly" for 6/7.
- **Descriptive only, no p-values:** horizon sweep, C_th sweep, c_sw, deadband, tariff, setback, D1, in-rules arms, RBRL–guard identity (count of identical windows).
- **Resolution rule:** pooled differences < 3 pts between arms are "not resolved" whatever the test says (noise floor E-cs3-5, staircase CTL1-16).

---

## 3. Code fixes, in order (each with an acceptance test)

**Drop-ins** are in `/tmp/claude-0/-home-claude/301fe72e-19a5-59f9-9248-860c3b01a75c/scratchpad/`:
- `rbrl_io.py`
- `jobq2.py`
- `tests/test_fast.py` (7 pass + 1 strict xfail + 3 slow)
- `t_vec.py` (`sim_hyst_batch` prototype)

**F0 has to happen first, before any edit:**
- Kill the stale jobs: `bound_v2 csw`, `rbrl_sb`, `setback_arms mpc taif`, `setback_arms rule`, `t1_v2 csw`, both `mz_mpc` jobs, and `jobq_runner`. All of them use the superseded protocol.
- **Keep `rbrl_ppo.py --cities taif` training running.** PPO training is protocol-independent and the models are saved; only the cap fit is redone.
- `git init /home/claude/rbrl`, then commit.

| # | Fix | Location (from reports) | Acceptance test |
|---|---|---|---|
| F1 | Runner: dependency-aware, idempotent, admission control MAXJ = 2, env scrub, OMP = 1 | replace `jobq_runner.py:16,25-27,33` and `jobq.txt` until-loops with `jobq2.py` + `jobs/round4.jsonl` | jobq2 smoke test; stale RUN rows re-queued; DONE iff rc = 0 and outputs have mtime ≥ start |
| F2 | Atomic, provenance-stamped, tag-aware writes; key union; refuse empty or `fit_status = none` rows | `t1_v2.py:85-93, 136`; `rbrl_ppo.py:226, 271-276`; `setback_arms.py:185`; `mpc_lambda.py:355, 362` (log + `--lam-from` tag) → `rbrl_io.write_csv/write_json/read_json` | test_fast `test_writer_*`; test 18: every cited CSV has `prov_code_sha` = current |
| F3 | Weather cache (read-only arrays) | `headroom.py:61-66` (SPEC_software Fix 2) | test 13: identical and read-only; `rule_run` bit-identical |
| F4 | Vectorised hysteresis `sim_hyst_batch` (also emits the §2.1 metrics and T_end) | `final_tables.py` (from `t_vec.py`); setback variant with occ/lo/hi vectors | test 12: 50 random (on, off) pairs equal `S.sim` to ≤ 1e-12 (measured 2.8e-14). Only then does `tune_rule` use it |
| F5 | **Corrected cold rule** (§2.1) | `r3_dp.py:96-99` (lagrangian, relaxed and unrelaxed) and replay l.112-131 (`_lerp`, fallback counter, R5-8); `mpc_lambda.py:183, 186-191, 236-237, 243-244`; `setback.sim:83` (metric split). Repo-only: `mz_mpc.py:88` (per-λ mask), `:105` | (a) unit test: pre-cool then coast below band is infeasible in MPC and CLV; (b) `in_domain()` = True for THERM and guard in Taif w121/w289; (c) `fallback_steps = 0` in every MPC/CLV cell; (d) test 14: relaxed L ≤ unrelaxed L ≤ replay J + λ(mean − T*) |
| F6 | **One admissibility helper** `F.admissible(r, w)` (§2.1/2.2), `fit_status`, one fallback, delete DEGH_ALLOW | `final_tables._degh_ok:136-137`, l.150, 176, 199; `t1_v2.fit_guard:39-51`, l.164-170, run_t7/run_csw; `mpc_lambda.fit_lambda:303-306, 312-321`; `rbrl_ppo.py:235-245`; `setback_arms.py:135, 138-167` | AST/grep test: no admissibility comparison outside the helper; test 7 extended; `fit_status` column present in every arm CSV |
| F7 | **Selection on equalised tuning cost** (A4 objective); precompute J_THERM(δ) per tuning window | `final_tables.tune_rule:166-206`, `fit_param`; `search_audit.py:54-78` (rerun on final params; fail on a cheaper admissible neighbour) | test 5 (THERM as candidate gives saving 0); nesting sanity: at comparator deadband 1.25 K, TUNED ≥ 0 (THERM_1.25 is in the family, E-opt3-3); search audit passes |
| F8 | Band, R1/R2 and c_sw/price from one config; R1/R2 as arguments | `rbrl_ppo.py:35, 160, 230`; `mpc_lambda.py:140`; `r3_dp.py:61`; `rbrl_ppo.evaluate` (H.C_SW → F.C_SW); `mz_r3.py:38` (repo) | test 3 passes (remove the xfail); test 17 (every `S.sim` call passes c_sw) |
| F9 | MPC: `forecast={perfect, persistence}` (in-horizon t̂(j) = t(j−96), current T_out measured, irradiance persisted); IW cache keyed (k, j, u) in persistence mode; fallback = TUNED action; base TUNED read through `IO.read_json` (sha recorded); columns λ, λ/λ*, T_end, fallback_steps, fit_status, grid h; horizons accept 0.25/1/2; delete the dead ROLLC cache and move `mpc_run` to tests; fix the docstrings ("golden-section" → 2×8-point refinement; delete the machine-precision claim) | `mpc_lambda.py:44-129, 147-148, 176-216, 223-247, 303-321`; control-3 §4 implementation note | test 9 (batch = single); test 15 (vs legacy at default); **persistence with forecast := truth reproduces the perfect run bit-for-bit**; spacing printed per city |
| F10 | CLV: two-sided λ_w refinement to 0.002 K; Rule C scoring; T_end | `clv_refine.py`/`r3_dp.replay`; `bound_v2.py` | invariant: CLV ≤ B* pooled, and CLV passes the per-window certificate |
| F11 | Bound: relaxed, pooled and per-window; store L_raw(λ); B_a per arm; Taif grid h ≤ the Riyadh h (F-4); assert AWAY_MAX ≤ setback grid edge (`r3_dp.py:54`, F-6); **ruled relaxed bound** with RULE_ON ≥ every in-rule arm's R1 and RULE_OFF ≤ its R2 (F-10) | `r3_dp.lagrangian(relaxed=True[, ruled=True])`, `bound_v2.py`, `bound_at.py` (write a CSV) | invariants: every arm s_a ≤ B_a; certificate margins ≥ 0 (print the minimum); ruled bound ≥ in-rules MPC; relaxed ≤ unrelaxed row |
| F12 | PPO E2 env: reward −(cost + (λ/n_occ)·max(T′, T_min) + PEN·dh), copied from `rbrl_sb.SBEnv.step` l.137 with SETBACK off; obs adds the perfect T_out forecast at +1, +2, +3, +6 h and irradiance at +1, +3 h; train and evaluate under the same R1/R2 (CSRL-7); Monitor logging; ent_coef 0.01; reward normalisation; `numpy_policy` check on visited float32 states | `rbrl_ppo.py:85-99` (`_obs`), `107-121` (step), `124-147`, `214-217` | E1 sanity: with λ = 0 the env optimum equals hold (DP λ=0 on TUNE_W, J(hold) ≤ 1.01·J_DP); learning curves saved; equivalence on visited states |
| F13 | D1 exact one-step shield: force on iff T∞,0 + (T − T∞,0)a > HI; force off iff T∞,1 + (T − T∞,1)a < T_min; margin σ fitted by A4 | new function beside `t1_v2.fit_guard`; applies to the latch and the saved PPO models | TUNE_W: zero over and zero cmd-under by construction; σ ∈ {0, 0.05, 0.1} K row |
| F14 | Setback: iterated tuner; candidate set includes "no setback" (nesting); away thresholds tied to AWAY_MAX; MANUAL arm (off 08:00, on 14:00, no lead) and THERM-SB arm; tail occupancy indexed j + 96 (R5-7) | `setback_arms.py:37, 80-84, 135, 149-167`; `mpc_lambda.py:199-214` | TUNED-SB tuning cost ≤ TUNED's; test 16 (all-occupied MPC-SB = MPC); `T_max_away` reported |
| F15 | ERA5 1 h shift; pin `models=`; AMY/orientation through the protocol helpers | `amy_fetch.py:56-64, 115-130`; `amy_spread.py:57-86`; `orientation.py:50-75` | GHI centroid within ±0.5 h of solar noon |
| F16 | Cycling-energy port to v3 files (terminal-priced) | `cycling_energy.py:20-25` | Reproduces E-hvac2-2 per-start figures from v3 |
| F17 | stats_v3 per §2.4 | `stats_v2.py` | Matches R1's recomputation method on unchanged rows |
| F18 | Gates: P11 and every class fail on a missing file; delete v1 classes L–O; `verify_numbers` reads v3 CSVs (delete hard-coded 7.62); registry auto-status; LaTeX tables generated and `\input` | `invariants.py:356-537`; `verify_numbers.py:26-112`; `build_registry.py:55-74, 216-254`; `gen_tables_v2.py`; main.tex l.1945, 2149 | 0 printed values without a CURRENT source; invariant count printed from the saved run |
| F19 | Multi-zone hygiene (repository): delete `mz_r3.py:341-507`; mz_mpc fixes (1)–(6) of R5-6; AZ 2×2 fix | `mz_r3.py`, `mz_mpc.py`, `multizone.py` | Only if the author insists (§5) |
| F20 | Release: `\.epw$` in EXCL (and history per §8); CI (Python 3.13, `-m "not slow"`, paper path); models into Zenodo; README/CITATION rewritten; push the v3 code | `sync_repo.py`, `.github/workflows/ci.yml`, README, CITATION.cff | Fresh-clone test R-24 (TEAM_sw_2) |

**Gate T0** (before any job in §4): F1–F9 merged; fast tests green; tests 9, 12, 13, 14 green; F5 (a)–(c) green. Tag the code `p4`.

---

## 4. Rerun plan (DAG, CPU estimates, schedule, cut-points)

### 4.1 Cost basis
- From `logs_T21v2_jeddah`, the λ-fit plus held-out evaluation took 189 / 321 / 581 s (6 / 24 / 48 h) under about 4× load.
- PPO took about 4300–4900 s per seed under the same load.
- The estimates below are core-hours on an unloaded core, with a 1.5× margin. With 2 cores, wall-clock ≈ ΣCPU/2 + serialisation.

### 4.2 Jobs

| ID | Job | Status | Deps | CPU-h |
|---|---|---|---|---|
| J1 | T1v3: TUNED and guard, 3 cities × 3 tariff epochs (A4); TUNED 0.1 K grid row; per-window sensitivity row | **REQ** | T0 | 0.3 |
| J2 | T7v3 deadband, T5v3 c_sw (TUNED), T4v3 tariff | **REQ** | J1 | 0.5 |
| J3 | T21v3: MPC perfect forecast, H ∈ {0.25, 1, 2, 6, 24, 48} h × 3 cities (X2 inside) | **REQ** | J1 | 2.0 |
| J4 | **X1** persistence ("tomorrow = yesterday") MPC at H = 6 and 24 h × 3 cities, λ refitted by A4 under persistence; plus an upper-band back-off b ∈ {0.05, 0.1, 0.2, 0.3} K row fitted by A4 | **REQ** (back-off row Rec) | J1 | 1.3 |
| J5 | **X7** MPC-24 at 1601 points (perfect), 3 cities; accept if pooled \|Δs\| < 0.1 pt | **REQ** | J3 | 0.8 |
| J6 | In-rules MPC at H ∈ {1, 6, 24} h: (i) training rules 23.80/22.40, 3 cities; (ii) at each city's fitted guard R1/R2; base policy = guard | **REQ** (ii Rec) | J1 | 1.5 |
| J7 | **X8** λ sensitivity: MPC-24 at λ*·{0.99, 1.01, 1.05}, Riyadh and Taif | **REQ** (cheap) | J3 | 0.3 |
| J8 | CLV refit (F10), 3 cities | **REQ** | T0 | 1.0 |
| J9 | Relaxed bound, pooled and per-window, L_raw stored, B_a per arm, 3 cities (Taif finer) | **REQ** | T0 | 3.0 |
| J10 | **X6** ruled relaxed bound at 23.80/22.40, 3 cities | **REQ-or-delete** (else delete l.1530–1535 and the "SAC/DQN not needed" argument) | T0 | 1.5 |
| J11 | RBRL re-cap under A4 (saved models, numpy policy), 3 cities × 5 seeds; **E0** diagnostics (hold-deviation rate, logit gap); **E1** DP at λ = 0 inside the rules; **X4** D1 shield on the latch and on the saved models | **REQ** | J1 + J11a | 1.5 |
| J11a | Taif PPO training (already running; keep it) | **REQ** | — | ≈3 (remaining) |
| J12 | **X3 = E2**: λ-reward PPO + 6 h forecast in state, inside 23.80/22.40, λ = the in-rule MPC-6 λ from J6(i); Riyadh, 3 seeds × 2×10⁵ steps | **REQ** (cut-point CP2) | J6 | 4.0 |
| J13 | **X5** C_th ∈ {2400, 4800, 9600} kJ/K: THERM, TUNED, guard, MPC-1h, MPC-24 (perfect), refitted by A4, 3 cities (Riyadh minimum) | **REQ** (Riyadh) / Rec (Jeddah, Taif) | J3 | 2.0 |
| J14 | **X10** MPC-24 at c_sw 0.025 and 0.114, Riyadh | **REQ-or-delete l.1773** | J3 | 0.3 |
| J15 | **X9** setback: TUNED-SB (nested refit), MANUAL, THERM-SB, MPC-SB (24 h) × 3 cities; setback CLV and relaxed bound (6401); vacation re-pooling (windows 177/205/233 as fully occupied; no compute) | **REQ if setback is printed** | J1, F14 | 7.5 |
| J16 | **X11** AMY and orientation under protocol with the ERA5 shift fixed | **REQ if printed** (supplement) | J1, F15 | 0.5 |
| J17 | stats_v3, generated tables, invariants, verify, registry | **REQ** | all printed | 0.3 |
| — | **Latent**: fallback taken now; no runs | **REQ** (text) | — | 0 |

| ID | Optional job | CPU-h |
|---|---|---|
| O1 | Two-node (air + mass) sensitivity: THERM, TUNED and the MPC-24 command sequence driven through a 2-node plant with the unit's own 1-min return-air thermostat (1 K differential); count real compressor starts (E-hvac1-1 option 2). Dev about 0.5 day | 1 |
| O2 | Q_HVAC sweep {2.0, 3.3} kW | 0.5 |
| O3 | Sub-stepped THERM for the deadband sweep | 0.5 |
| O4 | Uniform terminal with a pro-rata start charge (REQ if the C19 trigger fires) | 3 |
| O5 | E2 at 10⁶ steps | 15 |
| O6 | Exact-tail oracle MPC | 0.5 |
| O7 | D2 MPC distillation behind the D1 shield | 3 |
| O8 | Multi-zone minimum (§5) | 5 + 1 day dev |

**Required total ≈ 31 CPU-h, about 16 h wall on 2 cores.** Compute is not the constraint; development and verification time are.

### 4.3 Dependency DAG

```
F0 ─ F1..F9 ─ T0 ─┬─ J1 ─┬─ J2
                  │      ├─ J3 ─┬─ J5, J7, J13, J14
                  │      ├─ J4
                  │      ├─ J6 ── J12 (E2)
                  │      ├─ J11 (needs J11a)
                  │      ├─ J15 (needs F14)
                  │      └─ J16 (needs F15)
                  ├─ J8 ─┐
                  ├─ J9 ─┼─ B_a needs every arm's T̃̄_a ─ J17 ─ G1/G2
                  └─ J10─┘
J11a (running) ──────────── J11
```

### 4.4 Schedule (wall clock) and cut-points

| Date | Work | Compute (2 cores, via jobq2) |
|---|---|---|
| Thu 12 Nov | F0; F1–F9 dev; tests; **T0 by 23:00** | J11a only; overnight J1 → J2, J3, J8, J9 |
| Fri 13 | F10–F14 dev; check J1/J3 | J4, J5, J6, J7, J10, J11, J13, J14; overnight J12, J15 |
| Sat 14 | F15–F18; gate scripts on v3 | J15 (continued), J16, J17 draft. **CP1 20:00: G1** = J1, J3, J4, J5, J8, J9, J11 pass invariants. Title decision (§6) on X1/X2/X4/X5 |
| Sun 15 | Text starts (sections not driven by numbers) | **CP2 20:00**: setback gate (§5); E2 gate (J12 done or the claim is scoped); G2 = all printed CSVs v3 with provenance |
| Mon 16 – Wed 18 | Text T1–T16 + §7 disclosures; generated tables; page cuts | Optional O1–O3 in background only if G2 passed. **CP3 Mon 12:00**: if J13 is incomplete → scoping disclosure only (the CRITICAL is still met by disclosure + old-table caveat) |
| Thu 19 | Build ×2; V1–V5 (round-3 Phase 3) on v3; page count | — |
| Fri 20 | Verification panel (§9) | spot reruns ≤ 2 CPU-h |
| Sat 21 | Apply re-check fixes; EPW decision executed; push, tag, Zenodo DOI | — |
| Sun 22 | Buffer; response letter regenerated from v3 | — |
| Mon 23 | Submit | — |

**Drop order if time runs short:**
1. All O*.
2. J16: AMY/orientation leave the paper; one sentence remains.
3. J15: setback goes to the repository, with one sentence and no numbers.
4. J4 back-off row.
5. J7: state the λ* identity without the sensitivity row.
6. J10: delete the in-rule upper-bound sentence.
7. J14: delete l.1773.
8. J12: scope every PPO claim to "PPO on a λ-free reward"; title per §6.

**Never dropped:** J1, J2, J3 (including 0.25 and 1 h), J4 at 24 h, J5, J8, J9, J11, J13 for Riyadh, J17, and the latent fallback text.

---

## 5. Extension verdicts

| # | Extension | Verdict | Conditions / reason |
|---|---|---|---|
| 1 | Occupancy setback (TUNED-SB, MPC-SB) | **IN PAPER, conditional (gate CP2, Sun 15 Nov 20:00)**; otherwise REPOSITORY + 1 sentence | Majority conditional-in (control-1/2/3, cs-1/3, building-1/2/3, hvac-2, sw-3, DA, R1); REPOSITORY from R5, cs-2, sw-2, opt-3, hvac-1 *until rerun*. All of the following must hold: (i) J15 complete for 3 cities (Taif may report "no setback admissible"); (ii) TUNED-SB nested and refitted by A4; (iii) MANUAL and THERM-SB rows present; MPC-SB attributed as MPC-SB − TUNED-SB; vacation-re-pooled row; (iv) setback CLV and bound rerun under the corrected cold rule (the old λ* = 0 rows are deleted); (v) energy, on-commands and T_max_away columns; mechanism text = on-commands avoided during vacancy, energy ≤ ~1 %; (vi) disclosures: assumed timetable known to MPC-SB; constant capacity and no internal gains flatter recovery; cap non-binding (replace the 24–32 °C sentence with the float paragraph). Budget ≤ 0.4 pp table + 0.3 pp text |
| 2 | Outdoor-dependent COP | **REPOSITORY** (one Limitations sentence on the bias direction, no number) | No derating; train/score mismatch; terminal at rated COP; identity breaks; source unverified; no results |
| 3 | National 24 °C policy | **DROP** (repository at most, untagged runs deleted) | TUNED ≡ THERM by construction; unequal ceilings; hard-coded bands; asymmetric band; no confirmed primary source for "national guidance" |
| 4 | RBRL-SB | **DROP** from the paper; repository marked EXPERIMENTAL/UNREPORTED | No results; BC filter bug; unruled teacher; cap mismatch. Its λ-reward env is reused for E2 (J12), which tests the same question on the headline problem |
| 5 | Multi-zone | **REPOSITORY**; shared plant and RBRL-MZ **DROP** | See below |
| 6 | Loophole fixes | **IN PAPER** as methods sentences, with no history | Stated as §2.1 (corrected cold rule, which replaces the T∞,0 predicate) and as the TUNED search procedure (coarse 0.05 K, then iterated 0.01 K, plus a 0.1 K hardware row) |

### Multi-zone: editorial recommendation and the author's wish

The author wants MPC and the methodology applied to the single-zone, 2-room and 4-room cases.

**Recommendation (honest):** do not put multi-zone results in this paper. Every one of the 16 reviewers who ruled on it said REPOSITORY or DROP. Hvac-3 alone would accept one robustness sentence for independent units. The reasons are substantive, not just space:
- The current design gives every zone the same band, thresholds and timetable, and λ_ij is low. Adjacent zones therefore differ by ≤ 1.3 K and exchange ≤ 16 W per wall. T31 is an orientation-diversity check (already T24), not a coupling test (E-bldg1-2).
- There is no optimality reference: the paper itself argues that the multi-zone DP is intractable (l.2444–2457).
- MPC-MZ is a non-cooperative Jacobi scheme, not "coordinated".
- The shared plant matches no equipment.
- No MPC-MZ result exists.

The principle "apply the methodology to all cases" is best served by keeping the general formulation (§3, l.714–724 already says the numerical study is single-zone) and pointing to the repository.

**Minimal defensible presence if the author insists.**

| Option | Location | Page cost | Content |
|---|---|---|---|
| (a) Recommended if insisting | **Supplementary table S-MZ + one body sentence** | ≈ 0.1 pp body | Riyadh only; independent per-room units (m = none) only; arms THERM, TUNED, guard, MPC-MZ labelled "non-cooperative distributed MPC with one-step-delayed plan exchange (no optimality guarantee)"; topologies 1-zone, 1×2, 2×2 (with the fixed azimuths); 1×4 only if renamed "pinwheel" or given S, S, N, N; dwelling-mean A4/B/C matching plus per-zone mean and spread; λ_ij sweep {12.5, 35} W/K; statement that no bound exists |
| (b) Body | ≤ 0.5 pp | 0.5 pp + rewrite of ≈ 16 passages (DA §3.6 list) | Same content as (a). Must be paid for by extra cuts beyond §7.3 |

**Required fixes before any multi-zone number is printed:**
- F19: delete `mz_r3.py:341-507`; mz_mpc (1)–(6) per R5-6, including the per-λ mask at l.88, the corrected cold rule at l.105, the grid lower edge, MZ-fitted TUNED in the rollout, and C_SW/price from config.
- The protocol of §2 on the dwelling mean.
- The batch-invariance test (test 10) passes.
- Gate by **Fri 20 Nov 12:00**. If it is missed, option (a) falls back to a repository sentence.
- Compute ≈ 5 CPU-h plus one development day, taken from the O* budget, never from REQUIRED jobs.

---

## 6. Title decision tree (pre-registered; decided at CP1/CP2 from v3 numbers)

**Quantities** (pooled s, protocol §2). Δ(X) = s(X) − s(TUNED), averaged over cities, with per-city checks.

| Label | Condition |
|---|---|
| **A** (MPC wins) | Δ(MPC-24 perfect) ≥ 3 pts in ≥ 2 cities, with F2 unanimous 7/7 in those cities, **and** Δ(MPC-24 persistence) ≥ 3 pts in ≥ 2 cities |
| **L** (lookahead, not one-step model) | Δ(MPC-1h) ≤ ⅓ Δ(MPC-24) **and** Δ(D1 shield) ≤ ⅓ Δ(MPC-24), in ≥ 2 cities |
| **F** (forecast-robust) | Δ(persistence MPC-24) ≥ ½ Δ(perfect MPC-24) |
| **K** (capacity-robust) | Riyadh MPC-24 − TUNED ≥ 3 pts at both 2400 and 9600 kJ/K |
| **N** (PPO null survives) | E2 run and its gain over guard ≤ 0.2 × (in-rule MPC-6 − guard) |
| **N′** | E2 gain ≥ 0.8 × that reference: the RBRL null is a reward-design artefact and must be stated as such |

**Outcomes:**

| Branch | Condition | Title |
|---|---|---|
| T1 | A ∧ L ∧ F ∧ K ∧ N | "Lookahead Beats Rule-Constrained PPO and a Tuned Thermostat in Binary HVAC Scheduling for Saudi Residences: Switching-Cost Savings and a Clairvoyant Optimality Bracket" |
| T2 | A ∧ K, but ¬L (one-step/model effect) or ¬F | "Model-Based Receding-Horizon Control Beats a Tuned Thermostat and Rule-Constrained PPO in Binary HVAC Scheduling for Saudi Residences: Switching-Cost Savings and a Clairvoyant Optimality Bracket" (if ¬F, the abstract must say "with a perfect in-horizon forecast") |
| T3 (neutral fallback) | ¬A, ¬K, N′, E2 not run, or any gate unmet | "Tuned Thermostats, Rule-Constrained PPO and Receding-Horizon Control for Binary HVAC Scheduling in Saudi Residences: Switching-Cost Savings and a Clairvoyant Optimality Bracket" |

**Fixed rules:**
- Never "Not Learning". Even under N it is one learner.
- Never "Cost-Optimal".
- "Switching-cost" stays, because the c_sw-priced quantity is the switching on-command (§7.2-a).
- Check the JKSU-ES title-length rule. If it is exceeded, drop the subtitle after the colon.
- If E2 is not run, every PPO statement reads "PPO trained on a cost-only (λ-free) reward reproduces that reward's optimum, the guard hysteresis; whether a comfort-aware learner recovers the in-rule room is untested".
- If ¬K, the abstract states that the MPC margin depends on the assumed thermal capacity.

---

## 7. Manuscript change list

Line numbers refer to the current `main.tex`; they will drift as earlier edits land.

### 7.1 Claims to delete or rewrite

| Lines | Current claim | Action |
|---|---|---|
| 88–90 | Title "Lookahead, Not Learning…" | §6 |
| 101–140 | Abstract: 9/10 seeds; Corollary "explains why"; 9.3 ± …; 7.7 % at 0.114; RBRL 5.7; MPC p = 0.94 / "significantly below" / 48 h draws level; bracket 18.1/19.8; energy −0.3..+0.5; 0.10 SAR/zone/day; deadband sign reverses | Rewrite to ≤ 250 words from v3. Lead with the derived c_sw range. MPC result per §6. PPO per C9. Bracket per §2.3. No deadband sign. "Wear charge, not bill" |
| 143–146 | Keywords | Add "model predictive control"; respect the keyword cap |
| 163 | MPC-cannot-be-deployed motivation | Delete (contradicted by l.2433–2442) |
| 173, 175 | C3 "proves why none was there"; C5 "grid-converged"; MPC missing from the contributions | C3: "consistent with, under constant drift". C5: "provable relaxation bound". Add the MPC finding |
| 215, 277, 288–290 | MPC 5.9–8.4 % "modest"; "band dominates, learned component a few tenths" | v3 numbers; ranking deadband > controller class ≈ band > c_sw, tariff (DA-10) |
| 280, 1263–1266 | "hard action masking", "invalid-action masking [Huang2022]" | "post-sampling override (shield) [Alshiekh2018]"; Huang2022 only as contrast |
| 441 | Agent "exploits" the implicit model | "available to the agent; the trained policy does not use it" |
| 583–595, 2039, 2486–2488, 2654 | "No pre-cooling in any cost-optimal schedule"; matched "within 0.03 K"; energy moves | Qualify: no-setback, constant COP. Setback leads pull down. Equalisation per §2.3. Energy identity |
| 1169–1242 | Remarks cor_attain ("immaterial"), cor_scope (0.59 %, 6.3 vs 5.8), "never beats it" | Corollary hypothesis "at the mean of the maximal-width cycle" in the statement. Replace cor_scope with SPEC_control §6.3 "Room inside the rules" (v3 numbers). "Never beats it" holds only under constant drift |
| 1388–1390, 2697–2698 | "R2 22.40 excludes TUNED's 22.35" | v3 thresholds; state that the exclusion is a property of the method |
| 1436–1441, 1803–1806 | "Rules alone determine the cost"; "prediction the ablation confirms"; "seed dispersion is a finding" | SPEC_cs_rl §4 text; E2 result |
| 1494–1504 | TUNED "exhaustive 0.05 grid"; CLV "10 mK"; "no controller rewarded for ending warm" | Real search procedure. Actual spacing. Terminal disclosure (§7.2-g) |
| 1515–1523, 2123–2130 | Withdrawn ceiling-MPC description and footnote | New 8-line MPC methods paragraph: λ device + λ* identity, rollout terminal (no guarantee), restricted grid + exact first step, corrected cold rule, A4, forecast modes |
| 1530–1535, 2695 `\pend` | In-rule clairvoyant "upper-bounds every policy" | Ruled relaxed bound (J10) or delete |
| 1601–1636, 2714–2729 | Latent study numbers and claims | Delete. Two sentences in Limitations ("latent axis untested at adequate fidelity") |
| 1667, 1691–1695, 1714–1726 | "Mean ± std over five seeds"; Rule A text; BCa / stats | §2 protocol text (A4, B, C, fit_status), §2.4 statistics |
| 1756–1773 | c_sw derivation, 2.7–7.6 %, "~4 starts/day", "ranking unchanged" | v3 T5; 0.15 > whole-unit depreciation; on-commands; J14 or delete |
| 1822–1825, 1831–1912 (incl. `\pend` l.1897) | Guard under 0.350; bracket section | v3; SPEC_optimisation proof text incl. min-over-bracket, successor comparison, domain D; B_a; "duality gap + relaxation slack + replay suboptimality" |
| 1916–2045 (tab:main, setback, withdrawals) | Every cell stale; setback "largest lever, envelope gain"; "commissioning captures half" | One generated unified table (DA §4). Setback per §5. Delete the withdrawals paragraph (keep the label) |
| 2088–2106 (tab:sota) | 9.3/18.1/≤ 19.8; "agreement within three points" | v3; metric column; reframe |
| 2113–2195 (tab:abl, no-rules) | Stale rows; 6 Taif windows; ceiling-MPC; "every seed violates"; "quadratic" | Regenerate; C13 wording; HL CI labelled "TUNED − arm" (DA-13) |
| 2209–2308 | 2×2 "factorial"; "a day of lookahead is worth nothing"; 56 h; p = 0.94; forecast argument; Taif cap explanation | Delete. Replace with the causal ladder (THERM → TUNED → D1 → MPC-0.25/1/6/24/48 → persistence → in-rules MPC → E2 → CLV/bound) and X1–X5 results |
| 2323–2410 | Deadband rhetoric; old c_sw panel; withdrawn footnote | One Riyadh sensitivity table (tariff, c_sw, deadband), v3 |
| 2433–2442 | Timings 8.6/2.1 ms | From T18v3 for the reported arms, including 48 h |
| 2476–2602 | Robustness; orientation/AMY old convention; "shared bias largely cancels"; "G14 reference model" | One paragraph. AMY/orientation in the supplement from J16 or removed. Delete "cancels" (contradicted by C_th/Q/orientation). G14 wording fixed |
| 2613, 2666–2699 (`\pend` 2677/2678/2699) | "Neither parameter is algorithmic"; limitations count; `\pend` | DA-10 ranking; T4v3 values; F4 HL |
| 2747–2779 | COP direction "favours conclusions"; cycling energy; internal-gains sentence; forecast items | §7.2 disclosures |
| 2793 `\pend` | AMY zero-saving years | From J16 or delete |
| 2805–2826 | "Presented RBRL"; "architectural not informational"; 56 h; recommendation (i) | Mirror the new abstract. Recommendations scoped to this model instance |
| 2842 | Funding | §8 |
| 2857–2897 | "Reference implementation of everything"; 105 invariants / 15 classes; verifier claims; EPW not redistributed | Facts after F18/F20. EPW per §8 |
| Whole file | Revision-history phrases (DA §3.2 list) | Delete (round-3 ruling stands) |

### 7.2 Required new disclosures (body text; ≈ 0.6 pp in total, mostly in Methods and Limitations)

**a. Actuation interface (E-hvac1-1).**
> "u_k = 1 means the unit is commanded to deliver its full sensible capacity for the 15-min step (a supervisory on-command, e.g. a smart-plug or IR command at a low setpoint); the model lumps air and mass in one node, so the unit's internal return-air cycling is not represented. The counted and priced events are on-commands; whether each corresponds to a compressor start depends on the equipment's own thermostat and is not established here."

Remove "compressor start" from the abstract, C3/C4 and the cost model, or keep it only with this qualifier. If O1 runs, add one sentence with its compressor-start ratio.

**b. On-commands vs energy decomposition.**
> "At equal mean temperature every arm uses the same terminal-priced energy (duty-cycle identity); the saving equals c_sw × on-commands avoided."

Add the decomposition columns.

**c. Bill vs wear split.** State the absolute bill saving (≈ 0) and the wear charge separately, per room-day. "Not a reduction in the electricity bill." Also state that 0.15 SAR exceeds the unit's straight-line depreciation.

**d. Perfect model and forecast** (control-3 wording, edited):
> "The receding-horizon controller plans on the plant's own model with the true in-horizon weather and exact state; Table X reports it with a persistence forecast. Model mismatch is untested; TUNED needs no model."

**e. Single-node RC and capacity sensitivity.**
> "The ordering MPC > TUNED and its size depend on the effective thermal capacity (Table X, 2400–9600 kJ/K); ISO 13786 κ is a 24-h quantity and the effective capacity at the cycle period is lower."

Correct the Bacher & Madsen statement (higher-order models were selected), and the G14 wording.

**f. λ* identity.**
> "The fitted multiplier lies within 2.5 % of λ* = ΛHp/COP, the marginal envelope cost of 1 K, where the Lagrangian is indifferent to temperature level; the MPC therefore minimises on-commands and its comfort level is set by Rule C equalisation (sensitivity in Table S-x)."

Also add the per-cell λ/λ* column.

**g. Terminal-value window effect.**
> "The terminal store is priced at re-cooling energy without a start charge, so an oracle that knows the window end can end warm and save up to one on-command per window (≤ 1.9/2.2/3.5 pts envelope); causal arms cannot exploit this. Pooled T_end per arm is reported."

If O4 triggers, report the rescored bracket.

**h. Also required:**
- Rollout guarantee wording (SPEC_control §2.3): no closed-loop dominance is guaranteed.
- Pooled fallback and `fit_status` in every footnote.
- The resolution rule (< 3 pts not resolved).
- "Interleaved held-out weeks from one TMYx year."
- 2 kW and COP 2.985 unsourced and below SASO MEPS, with the bias direction.
- No internal gains (flatters setback recovery).
- 15-min comparator sampling caps the deadband sweep.
- Learners outside the rule layer untested.
- No BOPTEST benchmark.
- Latent axis untested.
- Single-zone only; multi-zone in the repository.

### 7.3 Page plan to ≤ 35 pp (target ≈ 32, leaving slack for the class conversion)

DA §4 is adopted, with these differences: no multi-zone; setback is conditional; the MPC ablation rows, D1 and E2 live in the unified table.

| Section | Now (pp) | Target | Main actions |
|---|---|---|---|
| Title / abstract / keywords | 0.8 | 0.5 | ≤ 250 words |
| 1 Introduction | 1.3 | 1.0 | Contributions in 8 lines; delete l.163 |
| 2 Literature | 3.0 | 2.0 | Merge §2.3–2.4 |
| 3 Formulation | 6.0 | 3.8 | Remarks rc_valid, cth_sens, dt_acc, tab:timestep, Models E/S and path_discrete → supplement (one sentence each stays) |
| 4 SLHA / Corollary | 4.0 | 2.8 | slha_abstraction and cor_attain → supplement; cor_scope → "Room inside the rules" (4–6 lines) |
| 5 Methods (RBRL, MPC, D1, comparators) | 4.0 | 3.3 | tab:ppo into text; MPC paragraph +0.3; D1/E2 +0.1 |
| 6 Case studies | 1.3 | 0.7 | Latent cut to Limitations |
| 7 Setup / protocol | 2.0 | 1.8 | §2 protocol; stats; c_sw in 5 lines |
| 8 Results | 3.0 | 4.6 | Unified generated table (0.8); bracket (0.5); causal ladder + X1–X5 (1.2); C_th mini-table (0.3); setback block (0.7, conditional) |
| 9 Ablation / sensitivity / scalability | 4.0 | 1.8 | Delete the 2×2 inline table; one Riyadh sensitivity table; tab:sota 6 rows + 1 |
| 10 Discussion + Limitations | 6.0 | 3.4 | Robustness in one paragraph (fig_season, orientation, AMY → supplement); fig_tariff regenerated; Limitations bullet list ≤ 1.4 pp including §7.2 |
| 11 Conclusions | 1.0 | 0.6 | Three findings, three scoped recommendations |
| Declarations + data | 1.3 | 0.9 | Delete stale verifier claims |
| References | 3.3 | 3.0 | Drop citations used only in cut passages; add Bertsekas2020, Alshiekh2018, Drgoňa2020 |
| **Total** | **≈ 41** | **≈ 30.2** (+0.7 setback = 30.9) | Slack ≈ 4 pp |

Revision-history deletions (≈ 0.8 pp) are inside these cuts. If setback misses CP2, its 0.7 pp is released. The multi-zone option (b) would consume 0.5 pp of the slack.

---

## 8. Decisions that belong to the author

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | **Title** | T1 / T2 / T3 per the §6 tree | Accept the pre-registered tree now, before the numbers arrive. If any condition is in doubt, T3 (neutral) |
| D2 | **Multi-zone** | Repository only / supplement table + 1 sentence / ≤ 0.5 pp body | **Repository only** + one Limitations sentence. If insisting: the supplement option with all §5 conditions by Fri 20 Nov 12:00 |
| D3 | **Funding statement** | The manuscript l.2842 thanks Taif DGSSR "for funding this work"; the author earlier said there was no external funding | If no grant exists: "This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors." If DGSSR did fund it, supply the grant/project number. Do not leave it unverified. The executor must not invent a number |
| D4 | **EPW files in git history** | (a) Read the actual TMYx (climate.onebuilding.org) licence: if redistribution is permitted, change the paper text to "redistributed under ⟨licence⟩ with attribution" and keep the files. (b) If not: `git rm --cached` + `git filter-repo --path-glob '*.epw' --invert-paths` + force-push main | **Check the licence first (a).** If it is not permissive, do (b) before the Zenodo archive, which is permanent. Verified today: `origin/main` already serves `reference_implementation/weather/{riyadh,jeddah}.epw` (commit d00a6e4), so the current text "not redistributed" is false either way. Rewriting history breaks existing clones and links: say so in the README |
| D5 | Setback in the paper | Conditional in (gate CP2) / repository | Conditional in, and accept the gate's outcome |
| D6 | c_sw reference value | Keep 0.15 as the computational reference, lead with 0.025–0.114 / switch every table to 0.114 | **Keep 0.15** (PPO models were trained at 0.15) and lead with the derived range; state that 0.15 overstates |
| D7 | Latent study | Take the fallback now / attempt a capacity-map coil fix | **Fallback now** (4 MAJOR model defects; no time to fix and verify) |
| D8 | Two-node compressor-start sensitivity (O1) | Run / disclosure only | Disclosure is required regardless; run O1 only if G2 passes by 15 Nov |
| D9 | Stopping stale jobs (F0) and keeping Taif PPO training | Approve / defer | Approve now: every stale job writes superseded-protocol files |
| D10 | Pre-commitment | Report X1–X5/E2 whichever way they fall | Required for Minor/Accept. A reversal reported honestly is acceptable; a claim kept on a handicapped arm is not |
| D11 | Release of saved PPO models (size) | Zenodo / omit | Zenodo, needed for re-evaluation without retraining |
| D12 | Abstract and keyword limits | Confirm the live JKSU-ES/Springer limits | Confirm before T1 |

---

## 9. Verification protocol (re-review mode, Fri 20 Nov; spot reruns ≤ 2 CPU-h)

| Fix / result | Primary re-checker | Second | Pass criterion |
|---|---|---|---|
| §2 protocol code (F5–F7), A4 provenance, fit_status, cold rule | R1 (methods) | TEAM_sw_3 (numerics), TEAM_opt_3 (tuner/search audit) | One `admissible()`; A4 identical across arms; F5 (a)–(d) tests green; search audit passes |
| MPC: T21v3, persistence, horizons, convergence, λ*, in-rules, D1 | R5 | SPEC_control, TEAM_control_3 | `fallback_steps` = 0; conv \|Δs\| < 0.1; λ/λ* printed; rollout wording |
| CLV, bound, B_a, certificate, ruled bound, terminal T_end | SPEC_optimisation | TEAM_opt_2 | All invariants pass with the minimum margin printed; proof text complete |
| RBRL re-cap, E0/E1, E2, shield text | SPEC_cs_rl | TEAM_cs_3, TEAM_cs_2 | E1 sanity; learning curves; outcome classified per §6 N/N′ |
| Statistics (T20v3) and every p/HL in the text | R1 | DA/R6 | Families as declared; floor stated; no "significantly" for 6/7 |
| C_th sweep and single-node disclosures | TEAM_building_3 | R4 | K evaluated; disclosure text present |
| Interface, on-commands, c_sw, cycling, bill vs wear | SPEC_hvac | TEAM_hvac_2 | §7.2 a–c present; no unqualified "compressor start" |
| Setback block (if printed) | SPEC_building_energy | SPEC_hvac, TEAM_control_3 | All §5 conditions (i)–(vi) |
| Latent removal, AMY/orientation (if printed) | TEAM_hvac_3 | R4 | No latent numbers; ERA5 shift fixed |
| Gates, provenance, registry, generated tables, repo/CI/EPW | SPEC_software | TEAM_sw_2 | Test 18 green; 0 un-sourced printed values; fresh-clone test |
| Whole manuscript: contradictions, title per tree, overstatement sweep, page count, revision-history sweep | DA/R6 | EIC (R1 lead) | DA §3 ledger cleared; ≤ 35 pp; abstract ≤ limit |
| Multi-zone (only if D2 ≠ repository) | SPEC_building_energy | SPEC_control, SPEC_hvac, SPEC_software | §5 conditions; test 10 green |

**Expected outcome after execution:** MINOR REVISION, with Accept possible. The condition is that the paper reports X1–X5 and E2 as they fall and leads with the derived c_sw range and the on-command interpretation.

---

### Notes for the main session
- **Memory:** none was used beyond the brief.
- **Verified this session:** the public `origin/main` already contains two EPW files (commit d00a6e4).
- **Running at 08:21:** Taif PPO, `bound_v2 csw`, `rbrl_sb`, `setback_arms` ×2, `t1_v2 csw`, `mz_mpc` ×2 and `jobq_runner`. Load is about 11 on 2 cores.

---

## 10. Author decisions (recorded 2026-11-12, binding on the executor)

| # | Decision | Author's answer | Consequence |
|---|---|---|---|
| D1 | Title | **Decide by results** (pre-registered tree §6) | Title fixed at CP1/CP2 from v3 numbers; T3 if any condition is in doubt. "Not Learning" and "Cost-Optimal" are out. |
| D2 | Multi-zone | **Main body + supplementary + repository** (overrides the editorial recommendation) | Option (b) of §5: ≤ 0.5 pp body (one compact table/paragraph, Riyadh, independent per-room units, 1-zone / 1×2 / 2×2 / 1×4 with fixed azimuths; MPC-MZ labelled "non-cooperative distributed MPC, no optimality guarantee"; no bound) **plus** full supplementary table S-MZ **plus** repository. All F19 fixes, the §2 protocol on the dwelling mean, and batch-invariance test 10 are required before any number is printed. Gate Fri 20 Nov 12:00; if missed, fall back to supplement + one body sentence. The ≈16 passages that say no multi-zone result is reported (DA §3.6) must be rewritten. The extra 0.5 pp is paid for by cuts beyond §7.3. Shared-plant (m-limited) and RBRL-MZ stay dropped. |
| D3 | Funding | **Use the funding statement of the author's 2026 JKSU-ES paper** (doi 10.1007/s44444-026-00131-0): "…acknowledge the Deanship of Graduate Studies and Scientific Research, Taif University for funding this work." | Applied in main.tex (Funding section, singular author), plus the 2026 paper's ethics statement and "no competing interests" wording. The earlier "no external funding" note is superseded. |
| D4 | EPW files | **Check the TMYx licence first** | Executor reads the climate.onebuilding.org licence; permissive → keep files and change text to "redistributed under ⟨licence⟩ with attribution"; not permissive → purge from history before Zenodo, after telling the author. |
| D5–D12 | Remaining | Recommended options adopted (author did not object) | Setback conditional on CP2; c_sw 0.15 reference + 0.025–0.114 lead; latent fallback now; two-node run optional; stale jobs stopped (done 08:40; Taif PPO had already timed out, seed 42 only, models on disk); report decisive experiments whichever way they fall; PPO models to Zenodo; confirm live abstract/keyword limits. |

**D4 resolved (2026-11-12):** climate.onebuilding.org states "Copyright © 2014-2026 Climate.OneBuilding. All Rights Reserved" with no redistribution licence. The author approved the purge: remove both .epw files from repository history (git filter-repo) and force-push on Sat 21 Nov, before the Zenodo archive; README explains how to download the files and that history was rewritten; paper text keeps "not redistributed" and cites Lawrie & Crawley (2026).

## 11. Accelerated schedule (author request 2026-11-12 08:41: finish, review and submit earlier)

Gates, protocol and drop order are unchanged; only dates move. Text work runs in parallel with the fixes (manuscript editor applies every number-independent §7 change now, with \pend{} for numbers).

| When (Riyadh) | Work |
|---|---|
| Thu 12 | F1–F9 + gate T0; manuscript editor applies §7 non-numeric edits; overnight J1 → J2, J3, J8, J9 |
| Fri 13 | F10–F14; J4–J7, J10, J11, J13, J14; overnight J12 (E2), J15 |
| Sat 14 | F15–F18; J16, J17; **CP1 + CP2 merged (20:00)**: G1, title, setback and E2 gates |
| Sun 15 | Fill \pend from v3 CSVs; generated tables; page cuts; build |
| Mon 16 | Verification panel (§9); apply re-check fixes |
| Tue 17 | EPW purge + push + tag + Zenodo DOI; response letter; final build; **submit** |
| Wed 18 – Mon 23 | Buffer only |

## 12. Corrections from validation (V-consistency, 2026-11-12 09:00) — supersede earlier text where they conflict

| # | Correction |
|---|---|
| 12.1 | **Multi-zone is REQUIRED (D2):** F19 is a required fix (not "only if the author insists"); multi-zone compute is a required job **J-MZ** (Riyadh, independent units, 1-zone/1×2/2×2/1×4-fixed; THERM, TUNED, guard, MPC-MZ under the §2 protocol on the dwelling mean), not O8. §7.2h is extended to state the multi-zone scope. **Gate moves to Sat 14 20:00 (with CP1/CP2)**; fallback if missed = supplement table + one body sentence. |
| 12.2 | **DAG edges added:** J8 (CLV) after F10; J9/J10 (bound) after F11; J14 after J2. J8–J10 move from Thu night to Fri after F10/F11. |
| 12.3 | **Taif RBRL (λ-free headline arm):** J11a is NOT running (timed out, seed 42 only). New job **J11a′**: seeds 43–46 for Taif with the pre-F12 env (`git` tag `p3-ppo-env` taken before any F12 edit), one job per seed (< 2 h each), ≈ 4 CPU-h; cap fit redone under F6. Runs now in background. |
| 12.4 | **CP3** stays: Mon 16 12:00. J13 for Riyadh remains never-dropped; the title tree's K branch reads J13 Riyadh. |
| 12.5 | **No cited CSV without a regenerating job:** add jobs J18 rbrl_norules5 (5 seeds, λ-free, no rules; J11 env), J19 tariff-bound column (bound_v2 tariff, after F11), J20 c_sw sensitivity on the table's grid {0, 0.025, 0.05, 0.10, 0.114, 0.15, 0.30, 0.60} (rules + MPC, after F6/F22), J21 fig_season/T6 per-window, J22 decision-time timings (T18v3), J23 cycling energy (F16), J24 timestep table, J25 search audit on final params, J26 12801-node bound grid row. Anything still uncovered at CP2 is deleted from the paper/supplement. |
| 12.6 | **New fixes:** **F21** C_th as a config/CLI parameter through headroom/final_tables/setback/mpc_lambda/r3_dp (needed by J13); **F22** mpc_lambda CLI options `--csw`, `--lam-scale`, `--rule-on/--rule-off`, and rollout base TUNED read for the matching c_sw. Both belong to gate T0. |
| 12.7 | **Minor fixes:** CLV fit_status value "oracle" added to the list; statistics family F5 (Riyadh-only) is a single-city family without Holm; EPW purge date = Tue 17 (§11 supersedes §10's Sat 21); verification panel = Mon 16 (§11); D12 abstract/keyword check scheduled Sun 15; t1_v2.evaluate emits the §2.1 metrics and drops s_w_mean/s_w_sd; rbrl_ppo:246 and equalise must not fall back silently (fit_status + clipped flag); test isolation (test_fast.py:80 global IO.R) fixed. |

## 13. Editorial ruling on Rule C (V-code-24/25, 2026-11-12 13:00)

Finding: THERM's clipped occupied mean is non-monotone in the shift δ (all 39 city-windows; drops ≤ 0.083 K), so a target mean can be reached at several δ (up to 13), and J_THERM(δ_w) differs by up to 6 % between crossings. Bisection picks one arbitrarily; mz_r3 used a running-max envelope instead.

**Ruling (binding, one shared helper for single- and multi-zone):**
1. **Conservative crossing.** For each window, the comfort-equalised comparator cost is the *minimum* J_THERM over all crossings of the arm's target mean on the piecewise-linear δ-grid curve (every segment that brackets the target, linearly interpolated). The baseline thermostat is credited with its cheapest setting that delivers the same comfort; savings can only be understated by this choice.
2. **Clipping** is tested against the curve's true minimum and maximum over the scan, not its end points; a target outside [min, max] takes the nearest extreme and is flagged `clipped` (and counted).
3. **One implementation** `F.equalise` / `F.therm_curve` used by selection (A4), evaluation (Rule C), shield, multi-zone (dwelling mean) and AMY/orientation. mz_r3's envelope search is deleted.
4. **Disclosure and sensitivity.** Methods states the rule in one sentence; the supplement reports, per city, the pooled saving range across crossings (min-J vs max-J) for TUNED and MPC-24 as a sensitivity row.
5. Gate T0 is re-declared met only after this helper is committed and V-code passes it; then tag p4.
6. **Disclosure (added after implementation, 2a78a7d):** under the min-J rule the unshifted thermostat scored against its own curve has held-out saving −0.78 % (Riyadh), −0.11 % (Jeddah), 0.00 % (Taif). This is the size of the rule's conservatism and is reported in Methods (one clause) and in the supplement sensitivity row beside the min-J/max-J range (TUNED: Riyadh 12.53–13.70 %, Jeddah 13.62–14.40 %, Taif 12.41 %). Test (e) is restated as: A4 nests THERM (TUNED objective ≤ THERM's) — accepted.

## 14. CLV bracket wording (V-code-44, 2026-11-12 13:15) — binding

CLV meets the 0.002 K match in only 4/14 Riyadh/Taif windows (the λ-optimal schedule's mean jumps 0.1–0.3 K at the critical λ); otherwise the closest schedule no warmer than THERM is kept (`clv_tol_met`=False, residual recorded). Therefore:
1. The bracket is printed as **[raw CLV saving vs unshifted THERM, 1 − ΣJ_CLV/ΣJ_THERM(0); B*]**, labelled "best attained schedule no warmer than THERM" (same denominator and constraint as B*).
2. The Rule C CLV saving is printed only as a per-arm pair with **B_CLV** (bound at CLV's own mean), never against B*.
3. Disclose the 4/14 match rate and the 0.1–0.3 K jump; per-window `tol_met` and residual go to the supplement.
4. Invariants added: raw CLV saving ≤ B*; Rule C CLV saving ≤ B_CLV.
5. Post-processing only (gen_tables_v3, invariants, verify_numbers, manuscript §2.3 wording); no rerun.

## 15. MPC grid and λ reporting (V-res-1/2, 2026-11-12 14:05) — binding

Riyadh MPC-24: at fixed λ, 801→1601 nodes moves s by 0.25–0.60 pt, 1601→3201 by 0.05–0.10 pt; neighbouring admissible λ (1.009 vs 1.051 λ*) move s by 1.4–1.8 pt at any grid. Hence:
1. **Headline MPC grid = 1601 nodes** (code default; tag p6). J5 = 3201 nodes at the *fitted* λ (`--lam-from`), accept |Δs| < 0.1 pt at fixed λ.
2. **Every MPC saving is printed with its λ range**: the J7 runs at λ*·{0.99, 1.01, 1.05} are extended to all three cities and to H ∈ {6, 24} h; the paper prints "s (range over admissible λ within ±5 % of λ*)" and λ/λ*.
3. **Horizon sweep** is printed descriptively (whole points, with fit_status and dT per row); no horizon-trend claim beyond "0.25 h is negative; ≥ 6 h is best". Differences < 3 pt between horizons are "not resolved".
4. All MPC jobs (J3, J4, J6, J7, J13, J14) rerun at 1601 on p6; non-MPC jobs rerun on p6 for one provenance tag.

## 16. Second MPC comfort knob: occupied-ceiling back-off (p6 reruns, 2026-11-12) — binding

Finding: the λ device is near bang-bang. With a linear comfort term and near-linear energy in T, the λ-optimal schedule rides either the top or the bottom of the band, so the pooled clipped mean jumps across THERM's target between two λ scan values. Example: Jeddah MPC-6 persistence, 23.35 K for λ ≤ 0.21 and 22.77 K for λ ≥ 0.29 (logs_J4_pers_jeddah.txt). No λ is admissible even at 0.10 K, so the cell gets fit_status none. Same for Jeddah 0.25/1 h perfect and Riyadh 1 h perfect. The same mechanism stops the CLV meeting 0.002 K on most windows (F10: `clv_tol_met` recorded).

**Ruling:**
1. **When it applies.** Only when the λ scan *and* its bisection leave no admissible λ at 0.10 K. Cells with an admissible λ are untouched; their code path and numbers are those of p6.
2. **The knob.** The MPC planner's occupied upper limit becomes HI − b, with b ≥ 0. This is J4's back-off device. Comfort is still scored against HI.
3. **Which λ.** λ is fixed at the **largest admissible λ on the warm side** of the jump, i.e. the cost-optimal schedule just short of it.
   - Lowering the ceiling can only cool the schedule, so only the warm side can be brought onto the target.
   - The cool side is already below the target. Backing off from it moves it further away, so the coordinator's "cool side" wording is superseded.
4. **Fitting b.** b is chosen by the same A4 rule (`F.select_rows`): coarse grid 0–0.6 K in 0.05 K steps; then bisection of the pooled mean between the bracketing b values; then ±0.005 K refinement until the choice no longer moves. b lies on a 0.005 K lattice.
5. **Reporting.** fit_status keeps the §2.2 set. Every MPC row gains the columns `knob` ∈ {lambda, backoff} and `backoff` (b, K).
   - Table footnotes name back-off cells: "λ device bang-bang; comfort met by ceiling back-off b = … K".
   - The same knob serves the in-rules, persistence and setback (MPC-SB) variants.
6. **Scope of the change.** Only `mpc_lambda.py` and `tests/test_core_mpc.py` change (commit 989b324 on master). Every other file stays identical to tag p6, so non-MPC results stamped p6 remain valid. MPC jobs whose cell was `none` are rerun on the new code.

**§16 editorial decision (2026-11-12 15:05):** back-off cells are printed as MPC results — the protocol admits the cheapest comfort-matched setting and must not be overridden when the outcome is unfavourable — marked † ("comfort matched by occupied-ceiling back-off b; λ device alone cannot reach the matched comfort level") with b reported. A negative saving in such a cell is a finding (the λ-MPC cannot track an intermediate comfort level cheaply), stated in Results and Limitations. Provenance: p7 (989b324) differs from p6 only in mpc_lambda.py and tests; non-MPC results stay stamped p6; MPC jobs whose p6 output contains any fit_status=none row are rerun on p7 (admissible cells are bit-identical by test). test 18 accepts {p6, p7} with this diff-stat recorded.
**§16 addendum (V-code-46):** MPC-SB rows lack knob/backoff columns. p6 J15 outputs stand if their logs show no "no admissible" cell; if any MPC-SB cell is none, apply the one-line label fix in setback_arms.py (knob/backoff from M.KNOB), tag p7.1, record the diff, and rerun only that city's J15 MPC job.

## 17. Title outcome (pre-registered §6 applied, 2026-11-12 15:45, p6 results)

Δ = s(arm) − s(TUNED); TUNED 12.53 / 13.62 / 12.41 % (Riyadh / Jeddah / Taif).
- MPC-24 perfect: 18.26 / 18.06 / 16.94 → Δ = +5.7 / +4.4 / +4.5 (≥ 3 in all cities).
- MPC-24 persistence: 12.74 / 14.64 / 10.76 → Δ = +0.2 / +1.0 / −1.7 (≥ 3 in no city).
Condition **A fails** (it requires both perfect and persistence MPC-24 ≥ 3 pts in ≥ 2 cities) → **¬A → T3 (neutral fallback)**, independent of L, F, K, N. F also fails (persistence Δ < ½ perfect Δ in every city).
**Title:** "Tuned Thermostats, Rule-Constrained PPO and Receding-Horizon Control for Binary HVAC Scheduling in Saudi Residences: Switching-Cost Savings and a Clairvoyant Optimality Bracket" (drop the subtitle if over the JKSU-ES length rule). Abstract must state that MPC's margin over the tuned thermostat requires a perfect in-horizon forecast and is not resolved (< 3 pts) under a persistence forecast.

## 18. Rerun follow-ups on p8 (2026-11-12 16:55)
p8 = p7 + amy_spread.py stale-cache fix (J16 crash). diff p6..p8: mpc_lambda.py, tests/test_core_mpc.py, amy_spread.py only. Run on p8 after the p6 queue drains: J13 (t1 + MPC at C_th 2400/9600, env RBRL_TAG=_cth2400/_cth9600 — they failed on p6 for the missing tag), J16_amy, J16_orient, and every MPC job whose p6 output has a fit_status=none row (back-off knob). test 18 accepts {p6, p8} with this diff recorded.
**§18 update (17:05):** follow-ups move to **p9** = p8 + mz_mpc.py duplicate-key fix (JMZ_mpc crashed after fitting). diff p6..p9: mpc_lambda.py, tests/test_core_mpc.py, amy_spread.py, mz_mpc.py. All JMZ_mpc_* jobs were removed from the p6 queue and run on p9 (after the p6 JMZ_rules jobs, whose tuned json they read). test 18 accepts {p6, p9}.

## 19. E2 outcome and comfort-offset disclosure (V-res-3/4, 2026-11-12 17:25) — binding
1. **E2 converges to the rule layer's hold policy** (on 23.80 / off 22.40): seed 43 identical to hold in 7/7 held-out windows, seed 42 in 5/7; hold alone scores 14.06 % at dT +0.097 K. At equal rules and comfort E2 − hold = −1.8 / −0.04 / −1.6 pt. E1 confirms hold is the λ-reward's optimum (ratio 1.0043 Riyadh). **§6 branch N holds** (PPO null survives with a comfort-aware reward and a forecast); N′ is not triggered. The 12–14 % figures are NOT printed beside comfort-matched arms; text: "E2 converges to the rule layer's hold policy; near λ* the λ term is flat in comfort (E-R5-1), and E1 shows hold is the reward's optimum." Optional number: E2 with the §2.2 post-training ceiling fit (expected ≈ guard).
2. **Comfort-offset sensitivity disclosure.** Rule C does not cancel savings differences between settings at different comfort levels: along the hold family (off 22.40) on = 23.60/23.70/23.80 gives 5.75/10.50/14.06 % at dT +0.036/+0.055/+0.097 K (≈ 1.3 pt per 0.01 K). Every row prints its dT; pooled_0.10 rows are footnoted with this sensitivity; differences between arms whose dT differ by more than ~0.02 K are interpreted with this caveat in Results and Limitations.
3. bound_at.py is re-run after the p9 follow-ups to include E2 and the back-off cells.

## 20. Journal-comment closure plan (author approved 2026-11-12 17:35)
1. **Comment 8 (time-step):** new fix F23 (actuation interval Δt as a config setting, headline Δt = 15 bit-identical to p9) and job J24 (Δt = 5/15/30 min: TUNED, MPC-24, B*; plus C_th 7200 row) → supplement tab:s-timestep. Validated by V-code before running; results stamped p10 with the diff recorded.
2. **Results integration:** manuscript editor fills every \pend from CSVs (p6 + p9 + p10).
3. **Response letter:** rewritten point-by-point (Comments 2, 3, 6, 8, A and the editor's instruction) against the final manuscript, quoting each comment, stating the change and its location, and disclosing what changed since the previous letter (title T3, forecast-dependent MPC margin, E2 = hold, savings mostly wear, comfort-offset sensitivity).
4. **Independent verification:** a fresh review panel (re-review mode) checks the letter against the manuscript and every number against its CSV; then a final language and coherence pass (Comment A).

## 21. Integration findings (editor report 2026-11-12 18:05) — binding decisions
1. **Runner bug:** jobq2 adopted two killed jobs (J8_9_bound_taif, J10_ruled_bound_taif) as DONE rc=0 with empty logs and no output. Fix jobq2 adoption (require non-empty outputs/log and a real rc) and give every job an `outputs` list; rerun both Taif jobs.
2. **c_sw sweep suspect:** TUNED's held-out ΔT̃ and on-commands are identical at every non-zero c_sw (params column empty) — investigate whether TUNED is refitted per c_sw (J2/J20 require a refit); fix and rerun J2_csw and J14 if so.
3. **C19 trigger fired** (CLV ends 0.49 K Riyadh / 0.77 K Jeddah warmer than THERM > 0.3 K): O4 becomes REQUIRED — uniform terminal value with a pro-rata start charge in r3_dp (CLV, bound, ruled bound, setback bound); rerun J8–J10, J15 bounds, J19, bound_at. Implemented after F23 lands (both touch r3_dp).
4. **Missing producers — run:** D1/X4 shield evaluation (latch + saved PPO models, σ ∈ {0, 0.05, 0.1}), T1v3_sens (0.1 K grid + per-window rows), T5v3_bound (bound at c_sw 0.025/0.114), J6(ii) in-rules MPC at each city's fitted guard R1/R2, THERM self-score for all cities. **Delete from paper:** J21 per-window figure and T18v3 timings (no producer; not required by any reviewer comment).
5. **Text corrections:** CLV tolerance met in **2/21** windows (1/1/0), not 4/14. "0.25 h is negative" → "0.25 h saves at most 1 % and loses money in Riyadh (−3.9 %)". E1 → "hold is within 0.4 / 1.4 / 2.3 % of the λ = 0 DP optimum (Riyadh / Jeddah / Taif)". MANUAL is a reference, not an admitted arm (occupied over-temperature 21.8 / 9.8 / 3.3 °C·h on return).
6. **Grid convergence (amends §15.1):** at fixed λ, 1601→3201 moves MPC-24 by 0.10 / 0.45 / 0.29 pt; acceptance becomes "grid uncertainty ≤ 0.5 pt, disclosed", which is below the 3-pt resolution rule.
7. **λ range (amends §15.2):** the λ*·{0.99, 1.01, 1.05} runs are not comfort-matched (ΔT̃ −0.18…+0.38 K), so they are NOT printed as a saving range. Main text prints λ/λ* and states the knife-edge sensitivity (Riyadh: neighbouring admissible λ differ by 1.4–1.8 pt, V-res-1); the J7 rows go to the supplement with their ΔT̃.
8. **Pages:** sn-jnl is at 35 pp before the p9/p10 cells; the editor cuts ≥ 1 page (Literature to the §7.3 target; move remaining remarks) before final fill.

## 22. O4 terminal and p10 (V-code-49..53, 2026-11-12 18:25) — binding
1. p10 = 818f270 (F23 Δt, jobq2 fix, §21.4 producers, O4 terminal). Running r21 (35 jobs) in /home/claude/rbrl_p10 with p6+p9 results staged; R21_bound_at and J24_table are held (jobs/r21_final.jsonl) until the p9 queue drains and the final p9 arm files are re-staged, then run last.
2. **O4 disclosure (V-code-50):** the end-of-week charge V_N = [price·C/(3.6e6·COP) + c_sw/1 K]·(T_N − T0) is a convention (heat left above the start temperature is charged as the fraction x/1 K of one THERM deadband cycle, i.e. one start per 1 K). Methods states it; the bracket prints B* under both terminals (energy-only, from p6/p9, and O4); main-table savings use the simulator terminal while the bracket and B_a use O4 — stated in the table note. E1 keeps the simulator terminal (PPO's own objective), stated.
3. c_sw sweep confirmed (V-code-51): TUNED is refitted per c_sw; 23.71/22.36 for every c_sw > 0 because comfort limits bind; 23.54/22.39 at c_sw = 0. Stated in the sensitivity note.

## 23. Multi-zone MPC λ search (V-res-5, 2026-11-12 20:40) — binding
mz_mpc scanned 13 λ values and ran at 401 nodes, so 1x1 MPC-MZ gave 16.3 % vs single-zone MPC-24 18.26 % (−2.56 pt from the λ pick, −0.61 pt from the grid); plant and Rule C are identical. All p9 MPC-MZ results are withdrawn. mz_mpc now reuses mpc_lambda.fit_lambda (full λ list, bisection, refinement, back-off knob) at 1601 nodes; acceptance: 1x1 MPC-MZ = single-zone MPC-24 to 1e-6. All JMZ_mpc jobs rerun (jobs/mz_final.jsonl). Until then no multi-zone MPC number is printed.

## 24. Three-layer reporting (author decision, 2026-11-12; recorded by the manuscript editor)
Every result is presented in three layers, in this order, throughout the abstract, results tables, text, discussion and conclusions:
1. **Physical headline:** compressor on-commands (starts) avoided, % against the comfort-equalised thermostat (`start_sav_eq`). Price-free; it leads.
2. **Energy alongside:** % change in electricity (`energy_sav_eq`), stated plainly as about unchanged (within about ±2 %), so readers see the benefit is cycling and wear, not the bill.
3. **Money, derived as a range:** SAR per room per cooling season (May–October, 184 days) at c_sw = 0.025 / 0.114 / 0.15 SAR per start (0.15 marked as the computational reference, which overstates), at the in-force tariff. It is computed from the per-window starts and energy columns (formula in the table note), never typed by hand.
The cost saving (`s_pooled_eq`) stays the protocol's ranking metric but no longer leads. Discussion and Conclusions add one sentence: the lever that does reduce electricity is the setpoint itself. Raising THERM from 23 to 24 °C cuts energy by about 8–16 % and cost by 7–15 %. This comes from a separate repository run under the round-3 protocol (`T1v2_heldout_pol24.csv`, `T1v2_perwindow_pol24.csv`).
**§23 acceptance PASSED (21:28):** 1x1 MPC-MZ on p11 gives λ 0.242875, pooled_0.03, knob lambda, s_pooled_eq 18.263835 % — identical to single-zone MPC-24 (T21v3_riyadh). Remaining MPC-MZ cells may be cited when their chains finish.

## 25. Page budget (author decision, 2026-11-12 22:58)
The author allows up to 2 pages beyond the 35-page target: the sn-jnl build may reach **37 pages** maximum. Use the room for the time-step finding (Comment 8: TUNED saves ~25 % at Δt = 5 min vs 12.5 % at 15 min — abstract, Results, Limitations) and to keep the horizon sweep and Table S-MZ summary in the body where they serve the argument; no other expansion.
**§20 note (23:20):** J24_mpc_dt5_riyadh ran correctly but wrote under the T21v3_conv stem (801 ≠ headline 1601 nodes), so jobq2 marked it FAIL on its declared outputs; the files were copied to the declared names (same run, provenance meta kept).

## 26. Time-step study complete (J24, 2026-11-13 01:15) — binding numbers
Source: `rbrl_p10/results/T2v3_timestep.csv` (J24_table) and `T17v3_Ba.csv` (R21_bound_at), both produced by jobq2 at p10. The J24_mpc_dt5 state was set DONE by hand after the §25-note copy (override recorded in its .jobq state).

| Δt / C_th | Riyadh TUNED / MPC-24 / B* | Jeddah TUNED / MPC-24 / B* | Taif TUNED / MPC-24 / B* |
|---|---|---|---|
| 5 min / 4800 | 25.0 / 23.8 (801 nodes, pooled_0.10) / 27.3 | 24.8 / – / – | 25.7 / – / – |
| 15 min / 4800 (headline) | 12.5 / 18.3 / 20.0 | 13.6 / 18.1 / 19.9 | 12.4 / 16.9 / 21.0 |
| 30 min / 4800 | −1.2 / 6.6 / 10.9 | −1.5 / 11.4 / 13.9 | −1.2 / 11.3 / 14.7 |
| 15 min / 7200 | 16.0 / 19.8 / 20.0 | 16.7 / – / – | 17.7 / – / – |

**Reading (to print):** the saving of every arm depends on the actuation step. At Δt = 5 min a tuned thermostat matches MPC and reaches ~92 % of the bound; at 30 min the thermostat can no longer beat THERM, while MPC keeps 6.6–11.4 %. B* is the relaxed-dual bound rounded up (Riyadh 7200: 19.92 at 12801 nodes → 20.0, coincides with the headline by rounding).
**Riyadh Δt = 30 min MPC disclosure (λ/λ* = 6.27):** λ ≤ 0.21 holds the room ~0.24 K warmer than THERM (pooled 23.14 vs ~22.9 °C; inadmissible); at λ ≥ 0.29 it jumps to 22.88 °C. The coarse step widens the §15 knife edge, and the cheapest admissible λ is 1.51 (J 0.972 vs 0.932 at the inadmissible 0.21). The 6.6 % is the protocol result and a conservative value; print it with this footnote; no protocol change.
**Not run (state as such):** MPC and B* at Δt = 5 min for Jeddah/Taif, and at C_th 7200 for Jeddah/Taif — TUNED only, by design (the table requires MPC/B* for Riyadh only).

## 27. Fill report (manuscript editor, 2026-11-13)
Backups: `*_before_fill_1113.tex`. Source: `rbrl_p10/results` (p10 staging). Filled: Taif CLV tol 0/7 (T17v3_taif_perwindow `clv_tol_met`; total 3/21, not §21.5's 2/21: the O4 rerun gives Riyadh 2); Taif CLV raw 16.7, ΔT̃ −0.025, on −26.1, B* (V_N) ≤21.0, B_CLV 20.2, CLV Rule C 16.5, slack 0.75 (T17v3_taif); ruled bounds ≤15.6 / ≤16.2 and ruled CLV 13.8 / 12.3 (T17v3_ruled_jeddah/taif); setback bounds 27.6 / 28.8 and setback CLV 25.3 / 23.9 (T17v3sb_*); c_sw bounds ≤6.3 / ≤17.5 (T5v3_bound, Riyadh); B_a: 71 rows, all s_le_B and cert_ok True (T17v3_Ba); J24 table (§26) in the main text (new subsection "Actuation Step", tab:timestep) and in Supplementary Table S1. Taif energy-only B* was never produced, so it is printed as "---" (not computed). Prose rewritten: the Taif bracket is 4.3 points wide, not ~2; Taif MPC-24 (16.9, simulator terminal) is above CLV raw 16.7, so the text gives the V_N comparison (MPC 16.3 vs CLV 16.5); the C_th 7200 vs 9600 order is reported as not resolved, with on-commands avoided rising monotonically. Correction to §26: at Δt = 30 min, λ ≤ 0.21 runs 0.20–0.23 K warmer on the tuning windows (log: 23.12–23.14 vs 22.91 °C), not 0.24 K. Left as \pend: MPC-MZ (mz_final), Zenodo DOI, and the invariant count. The gate run on a scratch copy of the p10 results gave 70 checks (classes A–H, P) with 10 FAIL: the stale P9b (0.002 K CLV match, superseded by §14) and P11 (0.1 pt, superseded by §21.6) criteria, and P1/P2–P10 looking for `T16v3_<city>.csv`, which p10 does not have. invariants.py needs a fix before a count can be printed. Builds: main 34 pp, main_sn 36 pp (≤37), supplement 4 pp; no undefined references.

## 28. Gate and B_a coverage at p12 (2026-11-13 01:40) — binding
1. **Name bug (V-code-57):** v3_names registered J6(i) in-rules MPC as `T16v3_<city>`; mpc_lambda writes `T16v3_r23.8-22.4_<city>`. Consequences: bound_at silently skipped the in-rules MPC arm (logged "missing (not evaluated)"), and the invariant gate aborted P1/P2–P10 on a missing file. The manuscript's in-rules values were read from the correct files and are unchanged (11.63/14.06/10.04 and 6.74/4.36/10.55 %). Fixed at **p12 (280f533)**: MPC_RULED renamed, MPC_GUARD (J6(ii)) added and evaluated by bound_at as ruled arms.
2. **Gate tolerances updated to the ruling:** P9b → CLV no warmer than THERM, raw CLV ≤ B*, Rule C CLV ≤ B_CLV (§14); P11 → |Δs| ≤ 0.5 pt (§21.6); P2 tests |bracket_gap| (signed since §13); P1 treats the CLV/bound summary as oracle.
3. **Persistence-forecast cold rule:** Riyadh MPC 6 h persistence realises 0.0006 °C·h commanded under-temperature over 7 windows (the plan meets the rule on the forecast). Disclosed in Results; gate P4 bounds forecast arms at 1e-3 °C·h, perfect-forecast arms stay at 1e-9.
4. **Result:** bound_at rerun on p12 → 89 rows, all s_a ≤ B_a, all certificates ≥ 0 (min margin printed in the log), every in-rules MPC row ≤ the ruled bound. Gate: **188 invariants, 9 classes (A–H, P), all pass** (`rbrl_p12/results/gate_p12.log`). Manuscript updated (71 → 89 rows; invariant count filled; cold-rule disclosure).
5. p12 is the final staging for every non-MZ result; the p11 MPC-MZ outputs are staged into p12 when the mz_final chains finish, then the gate is rerun.

## 29. Contradiction fixes (manuscript editor, 2026-11-13)
Backups: `review_round4/*_before_contra_1113.*`. Text only; no code or results touched. Every number re-read from the printed tables of main.tex and, where noted, from `rbrl_p12/results`.
1. **TUNED vs bracket (Conclusions, finding 1).** "the tuned thermostat recovers about 70–75% of what a schedule no warmer than the thermostat could save" → "the tuned thermostat's 12.5, 13.6 and 12.4% is 69–74% of the best attained schedule no warmer than the thermostat and 59–68% of the provable bound" (12.5/18.0, 13.6/18.4, 12.4/16.7; 12.5/20.0, 13.6/19.9, 12.4/21.0). No other occurrence in abstract, discussion, supplement or letter.
2. **Remark 3 (2027 rate).** "Every arm is therefore reported at the rate in force and repeated at the announced 2027 rate" → "Every arm is therefore reported at the rate in force, and TUNED and the bound are repeated at the announced 2027 rate (Table 7(a); the receding-horizon controller is not)".
3. **Electricity ±0.5 %.** Abstract "changes by under 0.5%" → "stays within ±0.5%"; Conclusions "changes by less than 0.5%" → "stays within ±0.5%" (TUNED energy −0.33/+0.47/−0.49 %, T1v3_heldout).
4. **Prose differences (printed-value arithmetic).** §8.3 D1 "within 1.4 points of TUNED" → "within 1.5 points" (14.0−12.5); §8.3 persistence cost at 24 h "5.5, 3.4 and 6.2" → "5.6, 3.5 and 6.1"; §8.3 capacity margin "15.0, 5.7, 3.8 and 0.4" → "15.0, 5.8, 3.8 and 0.4" (18.3−12.5); §9.2 price of the guarantee "the guard costs 6.6 and 6.0 points" (HL, mixed with a pooled Taif figure) → "6.8 and 6.0 points pooled (Hodges–Lehmann 6.6 and 6.0)". All other "X points" differences checked and consistent (bracket widths 2.0/1.5/4.3; D1→MPC 4.3/4.6/4.5; 6 h persistence 0.7/1.9; guard-rules Jeddah 3.2; F2/F3 HL values; 15.0→0.4; Discussion whole-point figures 35/13/7/7). Not changed (generated table): Table 5 "Pooled Δs" column prints unrounded differences (F2 Riyadh +5.7 vs 18.3−12.5 = 5.8; F4 Riyadh −6.8).
5. **Sensitivity list.** Limitations item 1 "specific to five choices (deadband, band, interval, charge, tariff)" and Conclusions finding 3 "(deadband, band, charge, tariff, capacity)" → one list in both: "six measured choices: the comparator's deadband, the actuation interval, the charge per on-command, the tariff, the assumed thermal capacity and the thermostat's setpoint resolution", plus "the comfort band, which was not swept" (§10.3 states it was not swept). Limitations cites Tables 7 and 8 and Supplementary Tables S1 and S2.
6. **Comfort protocol in the formulation.** Definition 2 "safe if Tmin ≤ T ≤ Tmax for all i, t" → ceiling pointwise on occupied steps and u=1 ⇒ T(t+1) ≥ Tmin; free-float has no lower limit. eq. (cop): two-sided "Tmin ≤ T ≤ Tmax (comfort, hard)" → "T(t+1) ≤ Tmax ∀ t ∈ H_occ (ceiling, hard)" and "u=1 ⇒ T(t+1) ≥ Tmin (cold rule, hard)"; following text rewritten (both hard; free-float reported, no credit in the clipped mean; away steps use the empty-house limit); "comfort constraint" → "ceiling constraint" for the inter-zone sentence; O1 now "every occupied t"; C1 "hard comfort on both sides" → "a hard occupied ceiling and a hard cold rule (… free-float is unrestricted)". Methods (§7 Comfort) already matched §2.1.
7. **Multi-zone and 30 min.** Abstract "the tuned thermostat's saving is unchanged" → "saves 11.7–13.6% (single zone 12.5%; not resolved)"; Conclusions "saving is unchanged (11.7–13.6%)" → "saves 11.7–13.6%, against 12.5% in the single zone, differences that are not resolved". "nothing at 30 min" → "−1.2 to −1.5% at 30 min" in the abstract, Limitations item 2, §10.3 ("from about 25% to −1.2 to −1.5%"), Conclusions ("at 30 min it issues 2.2–2.8% more on-commands than the equalised baseline and saves −1.2 to −1.5%") and Supplement S1 (T1v3_heldout_dt30: −1.23/−1.53/−1.20 %; starts −2.4/−2.8/−2.2 %). Abstract tightened to ≈243 words (rendered count, was ≈257).
8. **D1 description.** Remark 5 "An exact one-step shield on a latch, also inside those rules" → D1 "does not use those rules: it replaces their fixed margins by the plant's exact one-step prediction, forcing the unit on when a further idle step would end above its own fitted ceiling less σ and off when a cooling step would end below Tmin+σ"; PPO "when the shield replaces their rule layer". Methods D1 definition made exact (no R1/R2 guard bands; own ceiling fitted per σ ∈ {0, 0.05, 0.10} K; replaces the rule layer on PPO; shield.py). Same correction in §8.3 "Within the guard's own rules, the D1 shield…" and C4 "inside the rules an exact one-step shield" → "an exact one-step shield in place of the rules' fixed margins". Supplement title placeholder → "Supplementary Material for: " + main title.
Letter updated where it quotes or restates these sentences (summary D1 and multi-zone bullets, Comment 2 abstract quote, Comment 8 abstract quote, Limitations items 1–2). Builds: main 34 pp, main_sn 36 pp (≤ 37), supplement 4 pp; no undefined references; PENDING only MPC-MZ and Zenodo DOI.

## 30. Final verification panel — synthesis and binding fix list (2026-11-13 03:00)
Panel (isolated subagents): EIC, R1 methodology, R4 simulation, R5 control, R6 consistency, R11 language, DA. Reports in `final_panel/`. Verdicts: EIC and R5 READY AFTER MINOR FIXES; R1, R4, R6, R11, DA NOT READY — all on wording, framing and disclosure. ~900 printed numbers checked against `rbrl_p12/results`: all match except the 5.8/5.7 rounding. No reviewer requires a rerun. Gate 188/188.

**Binding decisions**
D1. **Rounding rule:** every difference in prose is computed from unrounded CSV values and printed to one decimal, as in Table 5 (so the capacity margin is 5.7). Recheck every prose difference changed in §29 under this rule.
D2. **Setpoint sentence (DA M8, R1, R4):** the 23→24 °C "8–16 %" figure comes from a round-3 run that breaches the 24 °C ceiling; withdraw it everywhere (abstract, Discussion, Conclusions, letter, §24 note). Replace with the protocol-valid result from THERM's own Rule C curve on the held-out windows (computed 2026-11-13, `therm_curve_full`, scratchpad/setpt.py): each 0.1 K warmer occupied mean lowers THERM's electricity by about 0.9 / 1.4 / 2.3 % (Riyadh / Jeddah / Taif), inside the 24 °C ceiling. The comfort target, not the switching policy, governs electricity.
D3. **TUNED mechanism (DA M1/M2):** state in abstract, C4, Discussion and Conclusions that TUNED's gain is a wider effective deadband (1.32–1.36 °C at 15 min), the widest the actuation condition allows; the saving depends on the comparator's 1 °C deadband, which is assumed, not measured; against a 1.25 °C comparator TUNED saves 5.7 % (verify from the deadband table/CSV).
D4. **Cold rule (R5 M1, R6 M4):** the cold rule is enforced by construction for MPC with a perfect forecast only. Thermostat arms meet it by threshold placement, not by guarantee. Report commanded under-temperature for every arm (supplement table from the per-window CSVs: TUNED Jeddah 0.0007, Taif 0.0066; TUNED-SB Riyadh 0.0102 °C·h, plus Δt / C_th / MZ cases). Main text gives one sentence with the maximum; Definition 2 wording says "a cooling step is designed not to end below T_min" for rule arms. Letter l.229 is updated.
D5. **D1 on PPO, Taif (R6 CRITICAL):** rewrite every "lifts PPO to the latch/TUNED level" claim: true in Riyadh/Jeddah, not in Taif (8.0–12.0 % vs latch 12.4 %; seed 42 below its own rule-layer result).
D6. **Overstatements to rewrite (R1 M1–M4, R5 M2–M4, DA M5–M7):**
 - "no part of it is a setpoint difference" → state the 1.3 pt per 0.01 K sensitivity against Rule A's ±0.03 K tolerance, and that refitting under the per-window criterion moves TUNED by up to 8.4 pt and reverses F4 in Taif (Table S2); MPC was not refitted under that criterion.
 - "requires a perfect forecast and a light plant" → "with the one imperfect forecast tested (persistence) the margin over TUNED is not resolved; the persistence arms run 0.07–0.09 K cooler at the 0.10 K fallback; the back-off knob is tried only when no λ is admissible". Drop "light plant" (it contradicts l.483 "heavy construction"; say "at the reference capacity").
 - Fix the sign error at l.2073–2076: a cooler mean lowers the saving, so the offset cannot explain the training-rule MPC's lead over the guard (+5.9 / +6.5 pt). State the lead and moderate "neither lookahead nor learning adds".
 - PPO: "converges to the hold policy" → Riyadh/Jeddah; Taif four of five seeds are 1.0–2.4 pt below hold; E2 is Riyadh only, 3 seeds, where hold is within 0.4 % of its reward optimum, so it cannot separate learning failure from success; drop "not anything a longer training run would supply"; state that E2 is not selected by Rule A.
 - SOTA paragraph: 0.15 SAR raises, not lowers, the figures; say so.
 - Recommendation (i) "none requiring new hardware" → state that it assumes a 15-min control layer with 0.01 °C thresholds; give the 0.1 °C-grid result beside it.
 - Reference capacity (R4 M4): say the cycle-period effective capacity is likely below the 24 h ISO value, which points towards 2,400 kJ/K where TUNED is negative, so the reference results lean favourable to TUNED (abstract + Limitations).
D7. **Terminology:** "compressor on-commands", "per start", "compressor starts" → "on-commands" (and "per on-command") everywhere in abstract, §8.2, Conclusions and letter; wear is described as the c_sw charge on on-commands.
D8. **Window dates (EIC F1):** zero-based day index; held-out windows start 2 May, 30 May, 27 Jun, 25 Jul, 22 Aug, 19 Sep, 17 Oct; tuning 16 May, 13 Jun, 11 Jul, 8 Aug, 5 Sep, 3 Oct. Verify with the code (`final_tables.WINDOWS`, `H.series`) before printing; fix §7 and the letter.
D9. **Simulation text (R4):** correct the forward-Euler statement (single-zone 1 h step was stable, limit 2C/Λ = 1.81 h; the 196.6–237.6 kJ/K range concerns the multi-zone grids only — verify); Limitations add: no internal gains modelled (≈150–300 W, comparable to the envelope load; effect on the comparison not bounded), constant capacity and COP (no derating; the outdoor-COP path in the code is unreported); hourly weather held constant within sub-steps; the Δt study also changes THERM's sampling.
D10. **Actuation condition two-sided (R6 M2):** Remark 1, recommendation (ii), Supplement S1/Table S1 use the two-sided form; disclose THERM's 0.025 °C·h at 30 min in §9.3.
D11. **Fig. 1 caption:** replace "3.00 … (Table 3)" by the CSV value (2.83 per day Riyadh) with its source; "Proposition" → "Observation 2".
D12. **Decision time (R5 M5):** report 2–8 ms per decision against the 900 s step (T18_scalability.csv) in one sentence. (§21.4 deleted T18v3 timings for lack of a producer; cite only if this CSV is a current producer output — verify provenance, else omit.)
D13. **Language (R11):** cut repeated disclosures to one full statement + short back-references (tariff boundary ×9, pre-cooling ×6, "which no action can prevent" ×4–5); de-densify the abstract (define "the planner" or say MPC; expand PPO, SAR) and the first Conclusions paragraph (no repeated TUNED figures); remove internal jargon ("round-3 protocol", file names); "six measured choices" → "six modelling choices"; add opening paragraphs to Sections 4, 7, 10; apply the R11 line-edit list; title may stay (27 words) unless the editor can shorten without changing T3's meaning — do not change the title.
D14. All remaining MINOR items in the seven reports are applied unless they conflict with D1–D13; the editor lists any not applied with a reason.

## 31. Panel fixes applied (manuscript editor, 2026-11-13)
Backups: `review_round4/*_before_panel_1113.*` (main.tex, supplement.tex, RESPONSE_LETTER.md, to_springer.py, tab_stats.tex, fig_leap.tex). Text, tables and captions only; no code or results touched. Every new number re-read from `rbrl_p12/results` (files named below) except the D2 setpoint slope (see D2). Builds: main.pdf 34 pp, main_sn.pdf **36 pp** (last page: left column full, right column empty, about half a page free for MPC-MZ), supplement 6 pp (Tables S4–S7 added); no errors, no undefined references. Abstract 248 rendered words (elsarticle), 247 (sn). PENDING markers left: MPC-MZ (2 main, 7 supplement) and Zenodo DOI (1). Letter number check: 243 unit-bearing numbers (130 distinct), all present in main.tex/supplement.tex/tab_stats.tex; the only other unmatched tokens are section numbers and the journal's 0.65 h.

### Binding decisions
- **D1 rounding.** Prose differences recomputed from unrounded CSV values: capacity margin 5.8→**5.7** (18.2638−12.5260); D1 vs TUNED "within 1.5"→**1.4** points (13.951−12.526); persistence cost at 24 h 5.6/3.5/6.1→**5.5/3.4/6.2** (T21v3 vs T21v3_pers); guard-rules Jeddah shortfall 3.2→**3.3** (4.361−7.624); training-rule lead over guard printed as **5.9/6.4** (not 6.5; 14.058−7.624). Tab:stats caption: "Pooled Δs is computed before rounding". Others in §29.4 re-checked and unchanged (6.8/6.0, 4.3/4.6/4.5, 0.7/1.9, 15.0…0.4, 35/13/7/7).
- **D2 setpoint.** Withdrawn everywhere: abstract ("the setpoint is what reduces electricity"), §10.3 (round-3 run, file names, 7.1/9.4/14.5%, 8/10/16%), Conclusions (8–16%), letter (bill bullet). Replaced by THERM's own equalisation curve on the held-out windows, inside the 24 °C ceiling: each 0.1 K warmer mean lowers THERM's electricity by about **0.9/1.4/2.3%** (abstract last sentence, §10.3 first paragraph replaced, Conclusions finding 4, letter). Provenance: these three values are taken from §30 D2 (coordinator's `setpt.py`, 2026-11-13); no CSV holds them and the editor's attempt to re-run the THERM curve read-only was refused by the environment's permission policy, so they are **not independently re-verified** here.
- **D3 TUNED mechanism.** Abstract ("widens the deadband to 1.32–1.36 °C, near the widest a 15-min step admits"; "falls to 5.7% against a 1.25 °C comparator"), C4 ("The tuned thermostat's gain is a wider effective deadband"), §8.2 TUNED paragraph (switch points widen 1 °C to 1.35/1.36/1.32 °C; on-commands avoided ≈ 1−δ_THERM/δ_TUNED; comparator's assumed deadband), §9.2 Sensitivities (deadband "assumed, not measured"; 5.7% at 1.25 °C; "favours the baseline" and "most valuable field measurement" removed), §9.3 (fitted width 1.78–1.79 °C at 5 min, 0.94–0.99 °C at 30 min), Conclusions finding 1. §5.5 THERM: "representative hardware deadband for the split units in this stock" → "assumed, not measured". Sources: T1v3_heldout*.csv params; T7v3_deadband (5.737 at 1.25 °C). Wording note: "the widest" softened to "near the widest", because at 15 min the fitted 1.32–1.36 °C is below the non-centred limit of (8) (≈1.50 °C); at 5/30 min and 2,400/9,600 kJ/K it is within 0.05 °C of it.
- **D4 cold rule.** Definition 4 (eq. cop) unchanged (hard for the schedule); §7 Comfort: optimisers hard; rule-layer arms and D1 designed to meet it from nominal parameters; TUNED meets it on tuning windows by Rule A and threshold placement, not by guarantee. §8 preamble: one sentence with TUNED 0.0007/0.0066, TUNED-SB 0.0102 (headline maximum) and 0.024 °C·h at most in any sensitivity run. New **Supplementary Table S4** lists every non-zero `deg_h_cmd_under` (T1v3_heldout, _dt5, _dt30, _cth2400, _cth7200, T7v3_deadband, T1v3_sens, T24v3_orientation, T23v3_amy_spread, T28v3_setback_rule, T21v3_pers_riyadh, T31_mz_rules_riyadh_2x2_lij12.5/35, rbrl_norules5_v3). §4.2 "enforces O1 by construction (for the nominal plant parameters…)". §9.2 price of guarantee mentions the cold side. Letter: summary bullet and editor's "Comfort records" bullet (old l.229).
- **D5 D1 on PPO, Taif.** Remark 5, §8.3 "Inside the rules", §9.2 "learned component", Conclusions finding 3 and letter summary: D1 on PPO reaches the latch's level in Riyadh/Jeddah (12.8–14.1, 11.2–13.5%) but gives 8.0–12.0% in Taif, below the latch's 12.4%, and for three of five seeds below their own rule-layer result (seed 42: 8.0 vs 8.6%) (T_D1_ppo_taif, rbrl_ppo5_v3_taif). "the range of the D1 latch", "same range", "lifts them to the tuned thermostat's level" removed.
- **D6 overstatements.** (i) §8.2 "so no part of it is a setpoint difference" → "removes the first-order energy effect … a residual dependence remains (comfort-offset caveat)"; §7 Statistics: the 3-point threshold "does not absorb comfort offsets"; Limitations item 10: 3 points ≈ 0.02 K < 0.03 K tolerance; per-window refit moves TUNED by up to 8.4 points and reverses F4 in Taif; MPC not refitted, robustness of F2/F3 untested; Table S2 gains an "F4 under that criterion" row (−4.0/−6.3/+3.8) and a note that MPC was not refitted. (ii) "requires a perfect in-horizon forecast (and a light plant)" → "resolved only with a perfect in-horizon forecast; with the one imperfect forecast tested … not resolved; persistence arms 0.09/0.07/0.09 K cooler, Riyadh/Taif at the 0.10 K fallback; back-off tried only when no λ admissible at 0.10 K" (C4, §8.3, abstract, Conclusions, letter Summary/Comment 4/Comment 7/overstated list); "light plant" dropped (C4) and §8.3 now "On the light plant tested (2,400 kJ/K)"; knob precedence stated in §5.5. (iii) Sign error §8.3 "enough to account for their apparent advantage" deleted; replaced by "exceeds the fitted guard by 5.9 and 6.4 points … despite a 0.10 and 0.04 K cooler mean, which penalises it; this compares different rule sets"; "neither lookahead nor learning adds" restricted to the guard's own fitted thresholds (Remark 5, §8.3, Conclusions, letter). (iv) PPO: "converges to the hold policy" → Riyadh/Jeddah reproduce, Taif four of five seeds 1.0–2.4 below (abstract, C4, §5.4, §9.2, Conclusions, letter); §5.4 "is minimised by" → "is nearly minimised (within 0.4/1.4/2.3% … E1)"; E2 "Riyadh only, 3 seeds, not selected by Rule A, not comfort-matched, within 0.16 on-commands/day and 2.6% of cost of hold, consistent with, not evidence for, a learning null" (rbrl_e2_v3_riyadh: fs_minus_hold 0.163/−0.020/0.102; J_arm/J_hold −0.3…+2.6%); "not anything a longer training run would supply" deleted; C3 names E2 and MANUAL as outside the protocol. (v) SOTA §9.1: two differences lower the figures, one (0.15 SAR pricing) raises them (TUNED 3.8–11.0% at the derived charge); Table 6 "This work" basis adds "on-commands priced at 0.15 SAR, electricity ≈0". (vi) Recommendation (i): "none requiring new hardware" removed; now a benchmarking recommendation, plus "assumes a supervisory 15-min layer and thresholds resolved to 0.01 °C (5.7–8.4% on a 0.1 °C grid); no commissioning or hardware cost is set against 2–19 SAR". (vii) Capacity lean: Remark 1, §8.3, Limitations item 4, abstract ("probably above the capacity acting per cycle"), Conclusions finding 2, letter Comment 2.
- **D7 terminology.** "compressor on-commands" → "on-commands" (abstract, §8.2, Conclusions, letter); "per start" → "per on-command" everywhere except the literal start-life derivation in §7; C6 "showing … the benefit is avoided cycling and wear" → "reporting that … the cost difference is a charge on avoided on-commands, which by an identity of the model leaves electricity unchanged"; Remark 2 states the identity; "wear" now "assumed to stand for wear".
- **D8 window dates.** Verified from final_tables.py (`WINDOWS = range(121, 297, 14)`, EVAL_W = [0::2], TUNE_W = [1::2]) and headroom._series (`h0 = start_day*24`, zero-based): held-out 2 May, 30 May, 27 Jun, 25 Jul, 22 Aug, 19 Sep, 17 Oct; tuning 16 May, 13 Jun, 11 Jul, 8 Aug, 5 Sep, 3 Oct. §7 "from day-of-year 121 to 289 … 1 May…" → "zero-based day indices 121 to 289 (1 January is day 0) … 2 May …"; Table S3 caption; letter Comment 3. Not edited (code): the window labels "1 May…" in gen_figs.py/make_figs.py (no figure using them is in the manuscript).
- **D9 simulation text.** §3.1 Euler sentence → "stable only for Δt < 2C/μ_max … at the air-only 77.2 kJ/K an hourly step met it for the single zone (2C/Λ = 1.8 h) but not for the coupled topologies … the issue was accuracy and actuation, not stability"; S1 range 196.6–237.6 kJ/K could not be reproduced and is replaced by values computed from Table 2's conductances (λij = 12.5 W/K): single zone 40.8–44.3 kJ/K, coupled 1×2…4×4 85.8–185.1 kJ/K. Limitations: internal gains (≈150–300 W, comparable with the envelope load, effect not established) and opaque-wall solar / intermediate floor (item 9); constant capacity and COP, the COP-only repository variant, "effect not established" (item 8; the wrong capacity-derating reason deleted); hourly weather held constant within sub-steps (§7); the Δt study also changes THERM's sampling (§9.3 and Limitations item 2).
- **D10 two-sided condition.** Remark 1: ε_hot defined as the one-interval warming excursion; hourly interval needs ≈9,700 kJ/K by (8) and 14,400 kJ/K for a centred deadband (was 7,200); 30 min and 2,400 kJ/K fail the upper limit narrowly (0.99 °C). Recommendation (ii) "check both sides of (8)". Supplement S1 text and Table S1: 30 min "no (upper)", 1,800 "no", 2,400 "no (upper)" (the last is the editor's own application of the two-sided form at the same Δt/C ratio as 30 min; Table 7 caption and §8.3 note it). §9.3 and Table 8 caption disclose THERM's 0.025 °C·h at 30 min (first held-out Riyadh week) and that it favours THERM.
- **D11 Fig. 1.** "Proposition" → "Observation"; "within 4% of the 3.00 measured for the clairvoyant optimum" → "on the held-out Riyadh weeks the clairvoyant schedule issues 2.83 on-commands per day (THERM's 4.10 less the 31.1% of Table 3)" (T17v3_riyadh clv_start_sav 31.115; fig_leap.tex is marked generated — gen_figs.py should carry the same caption at the next regeneration).
- **D12 decision time.** Not added. T18_scalability.csv was written by scalability_disclosure.py using the superseded `mpc.mpc_run` (not mpc_lambda), with no provenance metadata, so per D12 it is omitted; §9.4 keeps "No claim is made about … decision time". R5 M5 therefore remains open (see below).
- **D13 language.** Tariff-boundary disclosure reduced (deleted in §2.4 qualifications sentence, Model S paragraph, after Prop. 1 → "(Remark 3)", the 744 paragraph, the whole 745–753 paragraph, §10.3 → "(Remark 3)"; kept in Remark 3, Table 1 note, §5.2 clause, §7). Pre-cooling: 745–753 deleted, 1136–1138 and §10.1 → cross-reference, §5.3 cut to one sentence plus the leakage arithmetic. "which no action can prevent" deleted at O1, §5.3 and §5.4 (kept in Def. 4). Comfort-offset caveat: full statement in Limitations item 10 and Table 3 caption, cross-references elsewhere; D1 numbers removed from Remark 5. Abstract rewritten (MPC, PPO, SAR spelled out; "the planner" no longer used; shorter sentences). Conclusions: four short findings, TUNED figures stated once. Internal jargon removed ("round-3 protocol", file names). "six measured choices" → "six modelling choices". Openers added to Sections 4, 7 and 10; §2 opener now announces the subsection order. R11 line edits applied: A1–A7 (A4 split), I1–I4, I7, I8, L1–L5, P1–P13, O1–O8, M1–M7, M9, S1–S4, R-1 (paragraph split; end temperatures to Table S5), R-2, R-4 (whole-point list replaced), R-5, R-6, R-7, R-8, R-9, N1–N4, D1–D6, C1–C6, SP1–SP7, RL1–RL7. Title unchanged.
- **D14.** MINOR items applied unless listed below.

### MAJOR / CRITICAL findings, by report
- **EIC** F1 (dates) → D8. F2 (compressor/per start) → D7.
- **R1** M1 → D6(i) and tab:stats ΔT̃_a−ΔT̃_b column (new, from T1v3_heldout/T21v3/T21v3_pers) with fallback marks. M2 → D6(ii). M3 → D6(iii). M4 → D6(iv).
- **R4** M1 (internal gains) → D9, Limitations item 9 (option b; no run). M2 (capacity/COP) → D9, Limitations item 8 (option: reason corrected; no run). M3 (Euler) → D9. M4 (capacity lean) → D6(vii).
- **R5** M1 → D4. M2 → D6(ii) plus knob precedence in §5.5 (back-off refit of the persistence cells not run). M3 → D6(iii). M4 → D6(iv). **M5 not closed** (D12: no current-producer timing; see above).
- **R6** #1 CRITICAL → D5. #2 → D10. #3 → D11. #4 → D4.
- **R11** R1/R2/P13 repetition, A4 abstract, C1 conclusions, RL1 letter claim → D13 (letter's repetition bullet rewritten to what was done, with examples).
- **DA** M1, M2 → D3. M3 → D7. M4 → D6(vi). M5 → D6(ii). M6 → D6(iv) and D5 ("D1-on-PPO measures the shield, not the policy"). M7 → D6(v). M8 → D2.

### Other changes (MINOR, applied)
EIC F4 (Table 8 "Bold: headline step"; Table 7(b) "−0.0" → "0.0"), F5 (early citations of Table 7 in Remark 1, §3.4, Remark 3, Remark 4, §7 replaced by Section 9.2; Table 4 cited with Table 3 before its float), F6 (Ethics heading renamed "Ethics Declaration" so to_springer emits "Ethics approval and consent to participate"; consent for publication added), F7 (Funding reworded; **no grant number — author to supply**), F8 (affiliation unified in both builds: Department of Sciences and Technology, Ranyah University College, Taif University, P.O. Box 11099), F9, F10, F11 (6 keywords; PPO/SAR/MPC defined in abstract), F13, F14, F15 (Supplementary Table S6, bias directions), F16, F17 (Supplementary Table S7, ablation), letter placeholders now "[PENDING: …]". to_springer.py: running head "Lookahead, Not Learning, in Binary HVAC Scheduling" (contradicted the T3 title) → "Binary HVAC Scheduling in Saudi Residences". R1 m1 (Holm "by a city"), m5, m6, m7 (H = 2,880 intervals), m8, m9 (setback comparator stated in §8.2 and Table 4 caption), m11 (no-rules grid edge), m12 (provenance stated: THERM's comfort record is one week from a separate THERM run; legacy 4 K-band gate checks disclosed in Data section), m13 ("no resolved saving"; THERM self-score not computed at sensitivity settings), m14 (Algorithm 1 terminal line), m15. R4 m2, m3, m4, m5, m6 (0.19 kWh/day), m7, m10 (CDD base 24 °C, ERA5 caveat, S5 order), m11, m13, m14. R5 m1 (λ* = Λ·168 h·p/COP), m2, m3 (CLV cap knob, knob precedence), m4, m5 (conclusions use s_a/B_a = 62–65%, T17v3_Ba), m6, m7, m9, m11, m12, m13, m14, m15. R6 #5, #6, #7 (Table 7(a) 29.6/18.6 relabelled V_N: T4v3_bound terminal = O4; energy-only B* labelled "earlier run", Riyadh and Jeddah), #8 (B_a for principal arms in new Table S5), #9, #10, #11, #13, #14, #15, #16 (4×10⁻⁵, T25v3 max 3.6e-5), #17 (1,460 on-commands/yr; 0.22 SAR for a 184-day season; range called a convention; "exceeds straight-line depreciation" removed). DA m1–m6, m8. Limitations item 7: the unverifiable "0.49 and 0.77 K" CLV end offsets (not in any p12 file) replaced by "markedly warmer". Supplement: vacation-week setback figures moved from §8.2 to S8. Space recovered for the page budget by shortening Models L/E, the Table 2 note, Remark 3, the RL literature paragraph (figures now in Table 6), the rollout guarantee, the climate degree-day aside, the multi-zone method paragraph (details in S7) and the Data list.

### MINOR items not applied, with reason
- EIC F12 / R11 title shortening: D13 (title not changed).
- R1 M1(3) and R5 M2(c): refit MPC-24 under the per-window criterion / refit the persistence cells with back-off — new runs; stated as untested instead.
- R4 M1(a)/M2 optional sensitivity runs (internal gains, COP/capacity derating) — new runs; stated as not established.
- R4 M4(a) ISO 13786 κ at a 6 h period, and a two-node check — new computation; direction stated instead.
- R4 m12 / R6 note: stale `T31_mz_rules_riyadh_*_m1/m2/mnone.csv` in results — results folder is read-only; the Data section already marks shared-plant arbitration as unreported.
- R1 m12 regenerate THERM's per-step degree-hours from v3 code on held-out windows — code run not permitted; provenance disclosed instead.
- R5 M5 decision time — D12.
- DA m3: one "(at the 0.15 SAR reference)" note covers the abstract's cost savings; repeating it for the bracket, capacity and step figures would exceed 250 words.
- DA m7: the abstract does not add "at 5 min its margin over MPC is not resolved" (word limit; stated in §9.3); no external fact found to justify 15 min beyond the actuation condition.
- R11 I6 (C1–C6 as an enumerate list) — page budget; C4 split into sentences instead. R11 M8 (one run-in heading style) and Observation 2 cited before it is stated — typographic/structural, left for copy-editing. R11 "Climate Zone 2" vs "A/B" — the first is Olawale et al.'s own zoning, the second the SBC's; left as cited.
- Remaining overfull boxes in main_sn (eqs. stepwise, corollary limit, reward) pre-date this pass.

## 31A. Release gate, provenance lineage, last fills (2026-11-13 08:00) — binding
1. **Provenance lineage:** the code of record is the tag lineage p6, p9, p10, p11, p13, p16 (`build_registry.GATE_TAGS`); every cited file must be stamped by exactly one of these code shas. Each tag's change is recorded in §15–§32. p14 (tests only), p15 (gate logic, manifest) and p17 (lineage list) produce no results. Manifest: 8 never-produced entries removed (MPC at c_sw 0/0.05/0.1/0.3/0.6 — printed "---"; T6v3_per_window, T18v3_scalability, T29v3_search_audit); T4_tariff.csv frozen (only fig_tariff.tex reads it, not \input). Provenance gate 4/4; registry 148 CURRENT + 1 FROZEN.
2. **Two printed values corrected** by the provenance check: Jeddah MPC 1 h guard rules 1.6 → 1.5 (file 1.549986); "10–15 %" → "11–15 %" on-commands on the 0.1 °C grid (min 10.506).
3. **MPC-MZ filled** (T31_mz_mpc_riyadh_*_h24): 1x1 18.3 (reproduces T21v3 exactly), 1x2 16.0^b / 15.8^b, 2x2 15.9 / 16.1, 1x4 15.7 / 16.1 (λ_ij 12.5 / 35); on-commands avoided 28–32 %; energy within ±0.7 %. Disclosed: occupied over-temperature 0.0001 °C·h (1x4 λ_ij 35) and commanded under-temperature ≤ 0.00003 °C·h (2x2), from the one-step-delayed plan exchange. Margin over TUNED not tested.
4. **Text added at the author's request:** finite-horizon paragraph after Definition (infinite schedule); setback "pre-arrival lead is not pre-cooling"; Discussion paragraph "where could a controller save money" (temperature-dependent COP, time-of-use price, multi-speed/inverter units — none modelled); Limitations sentence (TOU, demand, min dwell, COP(T_out), multi-speed; setback single-zone only).
5. **Tests:** p14 fixes the two failures caused by §28 (fixture lacks MPC_GUARD and the §14 CLV columns; manifest lacks the guard-rule files). Fast suite 188 passed / 5 skipped on a clean release copy; gate 188/188.

## 32. PPO training length (2026-11-13 08:20) — binding
Author asked whether the solver should decide the training length. `ppo_hold_gap.py` (p16, `T33_ppo_hold_gap.csv`) scores each saved headline model and the hold policy with the training cost at the training rules on TUNE_W and EVAL_W. Riyadh/Jeddah seeds within ±0.45 % / ≤0.86 % of hold on TUNE_W; Taif seeds 42–45 within 0.05 % on TUNE_W, 46 at +1.44 %; on EVAL_W Taif 42/44/45/46 are +0.52/+2.50/+1.09/+1.81 %. Reading: the Taif shortfall is generalisation from six tuning weeks, not training length; a longer run on the same weeks has almost nothing to gain (E1 bounds the in-rule gain at 0.4/1.4/2.3 %). The proposed 5-seed × 4-chunk extended run is NOT made (would cost ~5 CPU-h and cannot change the reading); stated in §5 (reward subsection; Taif four seeds: within 0.05 % on TUNE_W except 46), §9.2 and Limitations (all seeds: within 0.9 % on TUNE_W except Taif 46 at 1.4 %); letter item 12 updated.

## 33. National context: Vision 2030, SGI, Green Riyadh (2026-11-13 08:40) — binding
Author asked to relate the work to Vision 2030 (CO2, green energy) and to the Riyadh cooling project. Rule: no overclaim — at matched comfort the controllers change on-commands, not electricity, so their emission contribution is indirect. Added: Introduction sentence (SGI >278 Mt/yr by 2030, net zero 2060 [SGI2021 fact sheet]; Green Riyadh >7.5 M trees, −1.5 to −2 °C [GreenRiyadh2019, Saudipedia]); §10.3 paragraph; one Conclusions clause; letter bullet. Quantified link from `greenriyadh_sens.py` (p19, `T34_greenriyadh_sens.csv`): outdoor dry-bulb lowered by 1.0/1.5/2.0 K on the Riyadh held-out weeks, plant/thresholds unchanged → THERM cooling electricity −6.2/−10.5/−13.7 %, TUNED raw saving 13.7/12.8/13.6 % (12.9 % at 0 K), on-commands avoided 23–25 %, TUNED occupied over-temperature 0. Stated as a first-order sensitivity on an airport TMYx year, not an urban-heat-island model. Lineage now p6, p9, p10, p11, p13, p16, p19.
