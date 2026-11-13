# Methods notes: what every results column means

Definitions of the column names in `results/*.csv`, taken from the code that writes them
(file and function in brackets; all paths under `code/`). Units: J in SAR per day, E in kWh
(electricity) per day, f_s and "starts" in on-commands per day, temperatures in °C, offsets in K,
degree-hours in °C·h summed over the windows of the row. "Held-out" = the seven evaluation
windows (day indices 121, 149, …, 289; `final_tables.EVAL_W`); "tuning" = the six windows in
between (`final_tables.TUNE_W`). Each window is 168 h at Δt = 15 min unless a tag says otherwise.

For where each printed number comes from, see [`PROVENANCE.md`](PROVENANCE.md).

## 1. Shared protocol terms

| Term | Meaning (source) |
|---|---|
| THERM | the reference thermostat: 1 °C hysteresis centred at 23 °C (on at 23.5, off at 22.5), no fitted parameter (`headroom.THERM_SET`, `bound_v2.therm_eval`) |
| THERM(δ) | THERM with both thresholds shifted by δ ∈ [−0.4, 0.4] K, step 0.002 K (`final_tables.DELTAS`); the comparator curve of Rule C |
| clipped mean T̃ | mean over occupied steps of max(T, band floor): cold excursions earn no warm credit (`setback.sim`, key `T_mean_occ_clip`, `final_tables.MEAN_KEY`) |
| Rule A (A4) | selection on the tuning windows: admissible on every tuning window, pooled \|T̃ − T̃_THERM\| ≤ 0.03 K, else ≤ 0.10 K, lowest tuning cost ratio, ties to the lowest candidate index (`final_tables._select_core`) |
| Rule C | equalisation on each held-out window: the arm is compared with THERM(δ_w) at the δ_w whose clipped mean equals the arm's, the cheapest such crossing (`final_tables.rule_c`, `final_tables.equalise`) |
| admissible | zero occupied over-temperature and zero cooling-caused under-temperature on the window, and the away-time ceiling respected (`final_tables.admissible`) |
| V_N (O4 terminal) | end-of-week value used by the bound, the CLV and `T17v3_Ba`: energy at rated COP plus c_sw per 1 K of T_N − T0, i.e. J + c_sw (T_end − T0)/7 per day on top of the simulator's energy terminal (`r3_dp.uniform_J`) |
| λ, λ\* | mean-temperature multiplier of the MPC/DP stage cost; λ\* = Λ · 168 h · p / COP, the natural scale (`mpc_lambda.lam_star`) |

## 2. fit_status values (`final_tables.FIT_STATUSES`)

| Value | Meaning | Table mark |
|---|---|---|
| `pooled_0.03` | selected by Rule A4 with pooled tuning offset ≤ 0.03 K | ᵃ |
| `pooled_0.10` | no candidate met 0.03 K; selected at the single fallback ≤ 0.10 K | ᵇ |
| `none` | no admissible candidate; such rows are refused by `rbrl_io` and never written (listed in the `.meta.json` under `refused_rows`) | "no admissible parameter" |
| `oracle` | clairvoyant schedule (CLV): multiplier bisected per held-out window | ᵒ |
| `fixed` | parameter set by the caller, not selected (λ = X·λ\*, no-rules PPO with fixed cap, THERM self-score, setpoint shifts, MANUAL/THERM-SB, E1/E2) | ᶠ |
| `reference` | THERM itself in the multi-zone files | — |

## 3. Summary-row columns (one row per arm/city; `t1_v2.evaluate`, reused by `mpc_lambda`, `shield`, `rbrl_ppo`, `t1_sens`, `amy_spread`, `mz_r3`, `setback_arms`)

| Column | Definition |
|---|---|
| `s_pooled_eq` | **the reported saving**: 100 (1 − Σ_w J_arm,w / Σ_w J_eq,w) over the held-out windows, J_eq,w = cost of THERM(δ_w) at the cheapest Rule C crossing (`final_tables.pooled_saving`) |
| `s_eq_minJ` | same as `s_pooled_eq` (cheapest crossing) |
| `s_eq_maxJ` | the saving against the dearest crossing (Rule C crossing-choice range, RULING §13.4) |
| `n_eq_multi` | held-out windows with more than one crossing |
| `s_raw` | 100 (1 − Σ J_arm / Σ J_THERM) against unshifted THERM (not comfort-matched) |
| `dT_pooled` | mean over held-out windows of T̃_arm,w − T̃_THERM,w (K): the residual comfort offset (≈ 1.3 points of saving per 0.01 K) |
| `max_abs_dT_w` | largest \|T̃_arm,w − T̃_THERM,w\| over held-out windows |
| `start_sav_eq` | on-commands avoided, % = 100 (1 − Σ f_arm / Σ f_eq); printed with the opposite sign as "on" in tab:main |
| `energy_sav_eq` | electricity saved, % = 100 (1 − Σ E_arm / Σ E_eq) (negative = more) |
| `fs_therm0_mean`, `J_therm0_mean` | THERM (unshifted) on-commands/day and cost/day, held-out mean |
| `J_arm_mean`, `J_eq_mean` | arm and equalised-THERM cost/day, held-out mean |
| `deg_h_over` | occupied degree-hours above the ceiling (must be 0 for admissible arms) |
| `deg_h_cmd_under` | degree-hours below T_min at the end of COOLING steps (cold rule; 0 required on tuning windows, reported on held-out windows; Table S4) |
| `deg_h_ff_under` | degree-hours below T_min on free-float (u = 0) occupied steps (allowed, reported) |
| `deg_h_under` | occupied under-temperature = cmd + ff on occupied steps |
| `T_end_mean` | mean end-of-window temperature |
| `fallback_steps` | MPC steps where no action had finite planned cost and the TUNED rule's action was applied |
| `n_eq_clipped` | held-out windows where the arm's mean lay outside THERM(±0.4 K) and the comparator was clipped |
| `max_bracket_gap` | largest mean difference of the two THERM(δ) runs interpolated by Rule C (signed since §13) |
| `n_eval`, `fit_windows` | number of evaluation windows; which windows were used for selection (`TUNE_W`) |
| `tune_obj`, `tune_saving` | selected candidate's tuning cost ratio Σ J / Σ J_THERM-at-target, and 100 (1 − tune_obj) |
| `tune_dT`, `tune_max_abs_dT_w` | pooled and worst per-window tuning offset of the selected candidate |
| `tune_eq_clipped` | tuning windows where the chosen candidate lies outside THERM(±0.4 K) |
| `tune_n_cand`, `tune_n_adm_0p03`, `tune_n_adm_0p10` (or `n_cand`, `n_adm_cond1`, `n_adm_0p03`, `n_adm_0p10`) | candidates scanned; admissible on every tuning window; meeting 0.03 K; meeting 0.10 K |
| `params` | JSON of the selected parameters (rule: `on`/`off` switch points R1/R2; guard: also `cap`) |
| `on`, `off` | fitted switch-on / switch-off thresholds R1/R2 (°C); R1 − R2 is the fitted deadband |
| `tariff`, `price` | `inforce` 0.18 SAR/kWh, `historical` 0.05 (pre-2018), `y2027` 0.21 |

## 4. Per-window columns (`*_perwindow.csv`)

`window` (start day index), `J_arm`, `J_therm0`, `J_eq` (equalised THERM), `J_eq_max` (dearest
crossing), `delta_w` (the Rule C shift δ_w, K), `eq_resid` (mean mismatch at the crossing),
`eq_clipped`, `n_crossings`, `bracket_gap`, `T_arm`, `T_therm0` (clipped means), `dT_w`,
`fs_arm`, `fs_eq`, `fs_therm0`, `E_arm`, `E_eq`, the `deg_h_*` metrics, `T_end`,
`fallback_steps`, and `s_w` = 100 (1 − J_arm/J_eq) (per-window saving, used only by the
statistics). The three-layer money in tab:layers is
184 · [c_sw (mean f_eq − mean f_arm) + 0.18 (mean E_eq − mean E_arm)] over these rows.

## 5. MPC files (`T21v3_*`, `T16v3_*`, `T31_mz_mpc_*`; `mpc_lambda.py`, `mz_mpc.py`)

| Column | Definition |
|---|---|
| `horizon_h`, `forecast` | planning horizon (h); `perfect` (true in-horizon weather) or `persistence` (yesterday's weather) |
| `n_grid`, `grid_h_min`, `grid_h_max` | temperature-grid nodes of the dynamic programme (headline 1601) and its spacing range (K) |
| `ruled`, `rule_on`, `rule_off` | MPC inside rule thresholds R1/R2 (training rules 23.80/22.40, or each city's guard thresholds) |
| `lam`, `lam_star`, `lam_over_lam_star` | fitted multiplier, its natural scale λ\*, and the ratio |
| `lam_scale` | set when λ was fixed at X·λ\* (`fit_status = fixed`, files `_ls<X>`) |
| `relaxed_pooled` | pooled tuning offset reached at the fitted λ |
| `knob`, `backoff` | which comfort device met Rule A: `lambda`, or `backoff` with the occupied-ceiling back-off b (K) the planner uses (comfort still scored against 24 °C; RULING §16; † in tab:main) |
| `tuned_on`, `tuned_off`, `tuned_src`, `tuned_sha` | the TUNED rule used for the terminal rollout and fallback, its source file and sha |
| `c_sw`, `c_th` | charge per on-command (SAR) and thermal capacity (kJ/K) of the run |
| `T31_mz_mpc_*` only: `topology`, `nz`, `lam_ij`, `units`, `label`, `rollout_rule`, `n_lams`, `T_zone_spread_mean`, `T_clip_z<i>_mean` | room layout, rooms, inter-room conductance (W/K), independent units, controller description (non-cooperative distributed MPC, one-step-delayed plan exchange), the per-room TUNED rule used for the terminal rollout (JSON), number of λ values scanned, mean spread of room temperatures, per-room clipped means; one λ (comfort weight) is shared by the rooms and the saving is on the dwelling-mean clipped temperature |

## 6. Bound and clairvoyant files (`T17v3_*`, `T4v3_bound`, `T5v3_bound`; `bound_v2.py`)

| Column | Definition |
|---|---|
| `therm_J`, `target` | THERM's mean cost (V_N terminal) and pooled clipped mean (the comfort target) |
| `terminal` | text of the terminal convention (O4 uniform terminal) |
| `bound_rel<N>`, `lam_rel<N>`, `h_max_rel<N>` | relaxed Lagrangian dual bound (saving %, upper bound) at N grid nodes, its maximising λ and grid spacing |
| `bound_unrel<N>`, `rel_le_unrel_<N>_min_gap` | unrelaxed values (convergence rows only) and the check relaxed ≤ unrelaxed |
| `bound_reported` | **B\***: the minimum over relaxed grids, rounded **up** to 0.1 point (`up01`) |
| `bound_reported_grid` | grid at which that minimum occurred |
| `clv_fit_status` | `oracle` |
| `clv_s_pooled` | CLV saving under Rule C (comparator at the CLV's own mean), V_N terminal |
| `clv_s_raw` | CLV saving against unshifted THERM (printed as "CLV, raw") |
| `clv_dT_pooled`, `clv_max_abs_dT_w` | CLV comfort offset from THERM |
| `clv_n_tol_met` | windows where \|T̃_CLV,w − T̃_THERM,w\| ≤ 0.002 K was attained (Table S3) |
| `clv_start_sav`, `clv_T_end_mean` | CLV on-commands avoided (%) and end temperature |
| `clv_B_a`, `clv_le_B_a`, `clv_le_bound_pooled` | bound at the CLV's own mean and the checks s_CLV ≤ B_CLV, s_CLV ≤ B\* |
| `clv_cert_min_margin`, `clv_le_bound_all_windows` | minimum per-window dual-certificate margin (must be ≥ 0) |
| per-window: `bound_J_w`, `bound_s_w`, `lam_w`, `grid_h_w`, `clv_lam`, `clv_cap`, `clv_J`, `clv_T`, `clv_resid`, `clv_tol_met`, `clv_fs`, `clv_E`, `clv_cert_margin`, `clv_J_eq`, `clv_s_w` | the same per window; `clv_cap` is the occupied-cap knob of the CLV fit; `clv_resid` = T̃_CLV,w − T̃_THERM,w |
| `*_dualcurves.json` | the stored dual function L(λ) per relaxed grid (pooled and per window), used to evaluate the bound at any mean |

## 7. B_a (`T17v3_Ba.csv`; `bound_at.py`)

| Column | Definition |
|---|---|
| `arm`, `source`, `kind` | arm key (e.g. `arm=TUNED tariff=inforce`, `horizon_h=24.0 forecast=perfect c_sw=0.15`), its per-window file, and `free` / `sb` (setback bound) |
| `B_star` | B\* of the city |
| `T_a` | the arm's pooled clipped mean (held-out) |
| `s_a` | the arm's saving **rescored onto V_N**, comparator recomputed at T_a by Rule C |
| `B_a` | 100 (1 − L\*(T_a) / mean_w J_THERM(δ_w^a)): the bound at the arm's own mean, so s_a ≤ B_a exactly |
| `s_le_B` | s_a ≤ B_a |
| `cert_min_margin`, `cert_ok` | minimum per-window shifted dual certificate J_a,w − [J^bd_w − λ_w (T̃_a,w − T̃_THERM,w)/7] and whether it is ≥ 0 |
| `s_a_file` | the arm file's own saving (simulator terminal), for comparison |
| `B_a_ruled`, `s_le_B_ruled`, `cert_min_margin_ruled` | the same against the ruled bound, for in-rules arms |
| `print_B_a` | whether the row is printed in Table S5 |

## 8. Statistics (`T20v3_paired_stats.csv`; `stats_v3.py`)

`family` (F1 TUNED vs THERM, F2 MPC-24 perfect vs TUNED, F3 MPC-24 persistence vs TUNED,
F4 guard vs TUNED), `contrast`, `arm_a`, `arm_b`, `fit_status_a/b`, `n` (= 7), `hl`, `hl_lo`,
`hl_hi` (Hodges–Lehmann estimate of d_w = s_w(a) − s_w(b) and its exact CI: 3rd smallest and
largest of the 28 Walsh averages), `hl_coverage` (0.953), `s_pooled_a/b`, `d_pooled`
(s_pooled_a − s_pooled_b, unrounded), `mean_diff`, `n_pos`, `n_neg`, `unanimous` (7/7 only),
`p_wilcoxon` (exact two-sided signed-rank), `p_sign` (exact binomial), `resolution`
("resolved" requires \|d_pooled\| ≥ 3 points), `holm`, `family_size`, `p_adj` (Holm within the
three-city family), `p_floor` (smallest attainable p: 0.0156, Holm 0.047), `at_floor`.

## 9. Other files

| File / columns | Definition |
|---|---|
| `T_D1_latch_<c>`, `T_D1_ppo_<c>` (`shield.py`): `sigma`, `cap`, `forced_on`, `forced_off`, `conflict_steps`, `tune_target`, `tune_ratio`, `tune_max_deg_h_over`, `tune_max_deg_h_cmd_under`, `model` | exact one-step shield with safety margin σ (K) and fitted ceiling `cap`; steps forced on/off; steps where both predicates held; tuning target mean and cost ratio; worst tuning-window comfort metrics; the saved PPO model shielded |
| `rbrl_ppo5_v3_<c>`, `rbrl_norules5_v3` (`rbrl_ppo.py`): `seed`, `steps`, `cap` | PPO seed, training steps, occupied ceiling of the rule layer (no-rules: fixed at 24 °C) |
| `T28v3_setback_*` (`setback_arms.py`): `vacation`, `T_max_away`, `s_pooled_eq_vac_occupied` | window contains vacation days; highest away-time temperature (≤ 30 °C); the saving if vacation weeks are scored as occupied |
| `T31_mz_rules_*` (`mz_r3.py`): `topology`, `nz`, `lam_ij`, `units`, `T_zone_spread_mean`, `T_clip_z<i>_mean` | room layout, rooms, inter-room conductance (W/K), independent units, mean spread of room temperatures, per-room clipped means; the saving is on the dwelling-mean clipped temperature |
| `T2v3_timestep` (`timestep_table.py`): `row`, `dt_min`, `c_th`, `overshoot_K`, `adm`, `tag`, `arm`, `s`, `dT`, `source` | configuration, step, capacity, per-step excursion Q Δt / C_th, THERM's admissibility under condition (8), file tag, arm (TUNED / MPC-24 / B\*), saving copied from `source` |
| `T1v3_sens` (`t1_sens.py`): `variant` | `hw_0.1K` (TUNED on a 0.1 K grid), `per_window_0.03` (old per-window criterion), `self_score` (THERM against its own curve) |
| `T23v3_amy_spread` (`amy_spread.py`): `year`, `kind`, `cdd`, `ok` | ERA5 actual year (or `TMYx`), `TRANSFER` (headline thresholds applied) or `RETUNED`, cooling degree-days |
| `T24v3_orientation`: `orientation`, `azimuth`, `therm_*` | façade orientation of the glazed wall |
| `T25v3_cycling_energy` (`cycling_energy.py`): `wh_per_start`, `tau_eff_min`, `E_tp_arm`, `E_tp_eq`, `energy_identity_rel`, `d_starts_per_day`, `energy_saving_pct` | energy charged per start; equivalent start-up time; terminal-priced energy; identity check; starts avoided per day; energy saving when each start also costs that energy |
| `T32_setpoint_sens` (`setpoint_sens.py`): `point`, `delta`, `mean0`, `mean`, `dmean_K`, `deg_h_occ`, `energy_pct`, `cost_pct`, `starts_pct` | THERM shifted by +0.1, +0.2 K or the largest admissible shift on its own curve: % change in electricity, cost and on-commands |
| `E1v3_hold_dp` (`rbrl_e2.py`): `J_hold`, `J_dp`, `L_relaxed`, `ratio_hold_dp`, `ratio_hold_bound`, `hold_is_optimum` | inside the rules, the hold policy's cost against the λ = 0 DP optimum and the relaxed bound; hold is "optimal" within 1 % |
| `prov_code_sha`, `prov_impl`, `prov_env`, `prov_inputs`, `prov_utc` (every CSV; `rbrl_io.py`) | code sha of the producing process (sha256 of every top-level `.py`, 12 hex), producer script, `RBRL_*` environment, sha of every input read, write time. The full record (argv, git rev, Python/numpy versions, `code_changed_during_run`, refused rows) is in `<file>.meta.json` |

Files without the `v3` / `T31` / `T32` / `T_D1` / `E1v3` prefix (e.g. `T1_heldout_three_cities.csv`,
`T17v2_*`, `T2_timestep.csv`, `T3_capacity.csv`, `T4_tariff.csv`) are round-2/round-3 outputs
kept for the record; `VALUES_REGISTRY.md` lists them under "Not cited", except the few the
manuscript still uses, which `PROVENANCE.md` names explicitly.
