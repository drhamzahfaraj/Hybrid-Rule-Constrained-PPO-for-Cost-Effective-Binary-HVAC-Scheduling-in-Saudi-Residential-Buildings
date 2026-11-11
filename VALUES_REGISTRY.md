# Values Registry

Generated 2026-11-11 23:18 by `build_registry.py` from the files in `results/`. **Do not edit by hand** — every value below is read from its result file when this document is built, so it cannot disagree with the data. After any re-run, rebuild with `python3 build_registry.py`.

Manuscript: *Rule-Constrained PPO for Binary HVAC Scheduling in Saudi Residential Buildings: Cost Savings, Their Governing Parameters, and an Optimality Bracket* (JKSU-ES, major revision, resubmission due 23 Nov 2026).

## How to verify everything

```bash
cd code
python3 invariants.py       # gate: exits non-zero on any failure; run before any table
python3 verify_numbers.py   # re-derives every printed figure from its CSV
python3 verify_optimality.py  # backward check of the clairvoyant schedule
python3 build_registry.py   # rebuilds this document
```

## 1. Reviewer question → where to look

| Question | Data | Script | Manuscript |
|---|---|---|---|
| Is the headline saving real / significant? | T1_heldout_three_cities.csv; T20_paired_stats.csv | run_final.py; stats_paired.py | §Results, §Robustness (statistics paragraph) |
| Is the comparator (THERM) fair? What deadband? | T7_deadband.csv | deadband.py | `tab:sensitivity`(c); §Limitations |
| What is the best achievable? Is the bound valid? | T14_perwindow_summary.csv; T17_bound_convergence.csv | perwindow.py; bound_converge.py; verify_optimality.py | §Results `subsec:bound`; `tab:main` |
| Does MPC beat the rule? Horizon dependence? Grid convergence? | T21_g1601_*; T21_g801_*; T16_mpc_ruled_summary.csv; T20 | mpc_perwindow.py; mpc_ruled.py; mpc_final.py | §Ablation; 2×2; Conclusions finding 4 |
| Does PPO add anything? Seeds? | rbrl_ppo5*.csv; rbrl_norules5*.csv | rbrl_ppo.py; verify_corollary.py | Corollary 1 + Remark `rem:cor_scope`; `tab:abl_component` |
| Corollary 1 proof / scope | — | verify_corollary.py (constructive test) | §Optimal Schedule, proof + `rem:cor_attain` + `rem:cor_scope` |
| Tariff dependence / cost models | T4_tariff_heldout.csv; sw_share.csv | t4_heldout.py; tariff_path.py (path-independence) | Proposition `prop:path`; `tab:sensitivity`(a) |
| Switch-on cost c_sw justification | T5_switchcost.csv | run_final.py | §Simulation Setup (wear derivation + documented search) |
| Latent load / humidity / ASHRAE 55 | T22_latent2.csv | latent2.py (selftest reproduces headline) | §Case Studies humidity para; §Limitations |
| Weather: one TMY year only? | T23_amy_spread.csv; T23_amy_retune_fine.csv; amy/amy_summary.csv | amy_fetch.py; amy_retry.py; amy_spread.py; amy_retune_fine.py | §Robustness 'Weather year' |
| Orientation | T24_orientation.csv | orientation.py | §Robustness |
| Actuation interval / thermal capacity admissibility | T2_timestep.csv; T3_capacity.csv | run_final.py; degree_hours_cause.py | `tab:timestep`; `rem:dt_acc` |
| Taif anomalies | taif_cap_scan.csv | taif_match.py | §Ablation Taif note |
| Cycling energy / C_D | T25_cycling_energy.csv | cycling_energy.py | §Limitations 'No per-start energy penalty' |
| Calibration (ASHRAE G14) | — | — | §Robustness 'Calibration status' |
| Computational cost / scalability | T18_scalability.csv; T18_environment.json | scalability_disclosure.py | §Discussion scalability |
| Multi-zone / inter-zone coupling | T19_coordination.csv | multizone.py (selftest); coordination.py | §Results 'Four withdrawals' → cites Faraj 2026 |

## 2. Every reported value, by manuscript location

| Location | Quantity | Value | Source file | Generator | Pinned by |
|---|---|---|---|---|---|
| Abstract; Table `tab:main` | TUNED saving, Riyadh | 9.25 ± 1.59% | `T1_heldout_three_cities.csv` | `run_final.py` | invariants.py (A, I); verify_numbers.py |
| Abstract; Table `tab:main` | TUNED saving, Jeddah | 9.26 ± 1.43% | `T1_heldout_three_cities.csv` | `run_final.py` | invariants.py (A, I); verify_numbers.py |
| Abstract; Table `tab:main` | TUNED saving, Taif | 4.56 ± 3.62% | `T1_heldout_three_cities.csv` | `run_final.py` | invariants.py (A, I); verify_numbers.py |
| Abstract; `tab:main` CLV row | Attainable clairvoyant saving (per-window matched), Riyadh | 18.09 ± 1.74% | `T14_perwindow_summary.csv` | `perwindow.py` | invariants.py (bracket class); verify_numbers.py |
| `tab:main` bound row | Lagrangian bound, grid-converged, Riyadh (published value outward-rounded) | 18.95% @1601 → 19.35% @3201 → 19.56% @6401 | `T17_bound_convergence.csv` | `bound_converge.py` | invariants.py (bound class) |
| `tab:main` setback rows | Setback attainable (per-window) / converged bound, Riyadh | 25.77% / 26.44% @1601 → 26.69% @3201 → 26.90% @6401 | `T14_perwindow_summary.csv; T17_bound_convergence_sb.csv` | `perwindow.py; bound_converge.py` | verify_numbers.py |
| Abstract; `tab:main` CLV row | Attainable clairvoyant saving (per-window matched), Jeddah | 17.83 ± 1.89% | `T14_perwindow_summary.csv` | `perwindow.py` | invariants.py (bracket class); verify_numbers.py |
| `tab:main` bound row | Lagrangian bound, grid-converged, Jeddah (published value outward-rounded) | 18.83% @1601 → 19.12% @3201 → 19.30% @6401 | `T17_bound_convergence.csv` | `bound_converge.py` | invariants.py (bound class) |
| `tab:main` setback rows | Setback attainable (per-window) / converged bound, Jeddah | 25.77% / 26.67% @1601 → 26.91% @3201 → 27.15% @6401 | `T14_perwindow_summary.csv; T17_bound_convergence_sb.csv` | `perwindow.py; bound_converge.py` | verify_numbers.py |
| Abstract; `tab:main` CLV row | Attainable clairvoyant saving (per-window matched), Taif | 14.97 ± 6.87% | `T14_perwindow_summary.csv` | `perwindow.py` | invariants.py (bracket class); verify_numbers.py |
| `tab:main` bound row | Lagrangian bound, grid-converged, Taif (published value outward-rounded) | 19.07% @1601 → 19.76% @3201 → 19.95% @6401 | `T17_bound_convergence.csv` | `bound_converge.py` | invariants.py (bound class) |
| `tab:main` setback rows | Setback attainable (per-window) / converged bound, Taif | 21.49% / 25.88% @1601 → 26.80% @3201 → 26.93% @6401 | `T14_perwindow_summary.csv; T17_bound_convergence_sb.csv` | `perwindow.py; bound_converge.py` | verify_numbers.py |
| Abstract; §Robustness statistics | TUNED vs THERM, Riyadh: Wilcoxon p, BCa 95% CI, windows favouring TUNED | p=0.016, CI [8.4, 10.6]%, sign 7/7 | `T20_paired_stats.csv` | `stats_paired.py` | invariants.py (M); verify_numbers.py (I) |
| Abstract; §Robustness statistics | TUNED vs THERM, Jeddah: Wilcoxon p, BCa 95% CI, windows favouring TUNED | p=0.016, CI [8.0, 10.1]%, sign 7/7 | `T20_paired_stats.csv` | `stats_paired.py` | invariants.py (M); verify_numbers.py (I) |
| Abstract; §Robustness statistics | TUNED vs THERM, Taif: Wilcoxon p, BCa 95% CI, windows favouring TUNED | p=0.031, CI [2.5, 7.8]%, sign 6/7 | `T20_paired_stats.csv` | `stats_paired.py` | invariants.py (M); verify_numbers.py (I) |
| Abstract; §Ablation statistics; Conclusions finding 4 | TUNED vs MPC-24h, Riyadh: diff, CI, p | diff +0.86 pts, CI [-1.6, 5.3], p=0.938 | `T20_paired_stats.csv` | `stats_paired.py (reads T21)` | invariants.py (K) |
| Abstract; §Ablation statistics; Conclusions finding 4 | TUNED vs MPC-48h, Riyadh: diff, CI, p | diff -1.55 pts, CI [-4.1, 2.1], p=0.219 | `T20_paired_stats.csv` | `stats_paired.py (reads T21)` | invariants.py (K) |
| Abstract; §Ablation statistics; Conclusions finding 4 | TUNED vs MPC-24h, Jeddah: diff, CI, p | diff +3.39 pts, CI [0.6, 5.5], p=0.047 | `T20_paired_stats.csv` | `stats_paired.py (reads T21)` | invariants.py (K) |
| Abstract; §Ablation statistics; Conclusions finding 4 | TUNED vs MPC-48h, Jeddah: diff, CI, p | diff -0.24 pts, CI [-1.1, 0.7], p=1.000 | `T20_paired_stats.csv` | `stats_paired.py (reads T21)` | invariants.py (K) |
| `tab:abl_component` MPC rows; §Ablation | MPC 6 h, Riyadh (1601 grid, per-window, 0.01 K caps) | -4.04 ± 4.57%, n_win=7, worst dT -0.056 K | `T21_g1601_riyadh_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` MPC rows; §Ablation | MPC 24 h, Riyadh (1601 grid, per-window, 0.01 K caps) | 8.39 ± 3.53%, n_win=7, worst dT -0.095 K | `T21_g1601_riyadh_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` MPC rows; §Ablation | MPC 48 h, Riyadh (1601 grid, per-window, 0.01 K caps) | 10.80 ± 3.27%, n_win=7, worst dT -0.061 K | `T21_g1601_riyadh_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` MPC rows; §Ablation | MPC 6 h, Jeddah (1601 grid, per-window, 0.01 K caps) | -4.70 ± 2.72%, n_win=7, worst dT -0.023 K | `T21_g1601_jeddah_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` MPC rows; §Ablation | MPC 24 h, Jeddah (1601 grid, per-window, 0.01 K caps) | 5.87 ± 3.73%, n_win=7, worst dT -0.032 K | `T21_g1601_jeddah_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` MPC rows; §Ablation | MPC 48 h, Jeddah (1601 grid, per-window, 0.01 K caps) | 9.51 ± 1.67%, n_win=7, worst dT -0.041 K | `T21_g1601_jeddah_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` MPC rows; §Ablation | MPC 6 h, Taif (1601 grid, per-window, 0.01 K caps) | -18.24 ± 4.28%, n_win=7, worst dT -0.104 K | `T21_g1601_taif_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` MPC rows; §Ablation | MPC 24 h, Taif (1601 grid, per-window, 0.01 K caps) | 2.87 ± 6.16%, n_win=6, worst dT -0.067 K | `T21_g1601_taif_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` MPC rows; §Ablation | MPC 48 h, Taif (1601 grid, per-window, 0.01 K caps) | 4.34 ± 6.08%, n_win=6, worst dT -0.124 K | `T21_g1601_taif_mpc_summary.csv` | `mpc_perwindow.py --ngrid 1601` | invariants.py (K); verify_numbers.py |
| `tab:abl_component` footnote (grid convergence) | MPC 24 h on 801 grid (control run), Riyadh | 9.66% (vs 8.39% @1601) | `T21_g801_mpc_summary.csv` | `mpc_perwindow.py --ngrid 801` | mpc_final.py (convergence printout) |
| `tab:abl_component` footnote (grid convergence) | MPC 24 h on 801 grid (control run), Jeddah | 8.72% (vs 5.87% @1601) | `T21_g801_mpc_summary.csv` | `mpc_perwindow.py --ngrid 801` | mpc_final.py (convergence printout) |
| `tab:abl_component` footnote (grid convergence) | MPC 24 h on 801 grid (control run), Taif | 5.97% (vs 2.87% @1601) | `T21_g801_mpc_summary.csv` | `mpc_perwindow.py --ngrid 801` | mpc_final.py (convergence printout) |
| 2×2 table; finding 4 | MPC 24 h inside rules R1–R2, Riyadh | 3.12% (unruled 8.39%) | `T16_mpc_ruled_summary.csv` | `mpc_ruled.py (1601, refined caps)` | verify_numbers.py |
| Abstract; Corollary 1 discussion; `tab:abl_component` | RBRL five-seed identity with hysteresis, Riyadh | 4/5 seeds at J=1.0576 | `rbrl_ppo5.csv + rbrl_ppo5_perwindow.csv` | `rbrl_ppo.py --seeds 5` | manual: per-window |J_RBRL − J_hyst| = 0 (see triage doc) |
| Abstract; Corollary 1 discussion; `tab:abl_component` | RBRL five-seed identity with hysteresis, Jeddah | 5/5 seeds at J=0.9354 | `rbrl_ppo5.csv + rbrl_ppo5_perwindow.csv` | `rbrl_ppo.py --seeds 5` | manual: per-window |J_RBRL − J_hyst| = 0 (see triage doc) |
| `tab:abl_component` no-rules row | PPO without rule layer, Riyadh, 5 seeds | +0.05 ± 5.27%, negative in 3/5 | `rbrl_norules5.csv` | `rbrl_ppo.py --norules --nomatch --seeds 5` | — |
| `tab:sensitivity`(c) deadband | Deadband 0.5 K: TUNED saving | 32.1% (admissible: yes) | `T7_deadband.csv` | `deadband.py` | verify_numbers.py |
| `tab:sensitivity`(c) deadband | Deadband 0.75 K: TUNED saving | 3.4% (admissible: yes) | `T7_deadband.csv` | `deadband.py` | verify_numbers.py |
| `tab:sensitivity`(c) deadband | Deadband 1.0 K: TUNED saving | 9.2% (admissible: yes) | `T7_deadband.csv` | `deadband.py` | verify_numbers.py |
| `tab:sensitivity`(c) deadband | Deadband 1.25 K: TUNED saving | -2.2% (admissible: yes) | `T7_deadband.csv` | `deadband.py` | verify_numbers.py |
| `tab:sensitivity`(c) deadband | Deadband 1.5 K: TUNED saving | -69.7% (admissible: no) | `T7_deadband.csv` | `deadband.py` | verify_numbers.py |
| `tab:sensitivity`(a) tariff | Tariff historical (0.05 SAR/kWh): TUNED / OPT | 13.6% / 22.7%, switching share 81.5% | `T4_tariff_heldout.csv` | `t4_heldout.py` | verify_numbers.py |
| `tab:sensitivity`(a) tariff | Tariff inforce (0.18 SAR/kWh): TUNED / OPT | 9.3% / 14.7%, switching share 55.0% | `T4_tariff_heldout.csv` | `t4_heldout.py` | verify_numbers.py |
| `tab:sensitivity`(a) tariff | Tariff y2027 (0.21 SAR/kWh): TUNED / OPT | 8.6% / 13.3%, switching share 51.2% | `T4_tariff_heldout.csv` | `t4_heldout.py` | verify_numbers.py |
| `tab:sensitivity`(b) switch-on cost | c_sw = 0.0 SAR: DP / rule saving | 19.25% / 13.96% | `T5_switchcost.csv` | `run_final.py` | verify_numbers.py |
| `tab:sensitivity`(b) switch-on cost | c_sw = 0.05 SAR: DP / rule saving | 19.25% / 13.96% | `T5_switchcost.csv` | `run_final.py` | verify_numbers.py |
| `tab:sensitivity`(b) switch-on cost | c_sw = 0.15 SAR: DP / rule saving | 19.25% / 13.96% | `T5_switchcost.csv` | `run_final.py` | verify_numbers.py |
| `tab:sensitivity`(b) switch-on cost | c_sw = 0.3 SAR: DP / rule saving | 19.25% / 13.96% | `T5_switchcost.csv` | `run_final.py` | verify_numbers.py |
| `tab:sensitivity`(b) switch-on cost | c_sw = 0.6 SAR: DP / rule saving | 19.25% / 13.96% | `T5_switchcost.csv` | `run_final.py` | verify_numbers.py |
| §Limitations cycling energy | Per-start loss 0 Wh: TUNED-vs-THERM energy saving | -0.37% | `T25_cycling_energy.csv` | `cycling_energy.py` | — |
| §Limitations cycling energy | Per-start loss 10 Wh: TUNED-vs-THERM energy saving | -0.13% | `T25_cycling_energy.csv` | `cycling_energy.py` | — |
| §Limitations cycling energy | Per-start loss 20 Wh: TUNED-vs-THERM energy saving | +0.11% | `T25_cycling_energy.csv` | `cycling_energy.py` | — |
| §Limitations cycling energy | Per-start loss 30 Wh: TUNED-vs-THERM energy saving | +0.34% | `T25_cycling_energy.csv` | `cycling_energy.py` | — |
| §Limitations cycling energy | Per-start loss 50 Wh: TUNED-vs-THERM energy saving | +0.78% | `T25_cycling_energy.csv` | `cycling_energy.py` | — |
| §Limitations cycling energy | Per-start loss 100 Wh: TUNED-vs-THERM energy saving | +1.78% | `T25_cycling_energy.csv` | `cycling_energy.py` | — |
| §Ablation Taif note | Taif admissible ceiling family | 7 admissible ceilings, 6.2–8.6% | `taif_cap_scan.csv` | `taif_match.py` | verify_numbers.py |
| §Case Studies latent para; §Limitations | Latent effect on saving, Riyadh | +0.4 pts | `T22_latent2.csv` | `latent2.py` | invariants.py (N); verify_numbers.py (I) |
| §Case Studies latent para; §Limitations | Latent effect on saving, Jeddah | +3.7 pts | `T22_latent2.csv` | `latent2.py` | invariants.py (N); verify_numbers.py (I) |
| §Case Studies latent para; §Limitations | Latent effect on saving, Taif | -4.6 pts | `T22_latent2.csv` | `latent2.py` | invariants.py (N); verify_numbers.py (I) |
| §Case Studies latent para | Jeddah: time over ASHRAE 55 humidity-ratio limit / coil at latent cap | 84.97% / 20.11% | `T22_latent2.csv` | `latent2.py` | invariants.py (N) |
| §Robustness orientation | Orientation north: saving (starts removed/day) | 7.21% (0.53) | `T24_orientation.csv` | `orientation.py (0.02 K tune grid)` | verify_numbers.py (I) |
| §Robustness orientation | Orientation east: saving (starts removed/day) | 5.66% (0.47) | `T24_orientation.csv` | `orientation.py (0.02 K tune grid)` | verify_numbers.py (I) |
| §Robustness orientation | Orientation south: saving (starts removed/day) | 9.52% (0.69) | `T24_orientation.csv` | `orientation.py (0.02 K tune grid)` | verify_numbers.py (I) |
| §Robustness orientation | Orientation west: saving (starts removed/day) | 11.32% (0.88) | `T24_orientation.csv` | `orientation.py (0.02 K tune grid)` | verify_numbers.py (I) |
| §Robustness weather year | AMY transferred-threshold saving, Riyadh (mild/median/hot years 2013, 2018, 2021) | 9.4–10.4% | `T23_amy_spread.csv` | `amy_spread.py (ERA5 via amy_fetch.py)` | invariants.py (O) |
| §Robustness weather year | AMY transferred-threshold saving, Jeddah (mild/median/hot years 2011, 2017, 2023) | 9.1–9.4% | `T23_amy_spread.csv` | `amy_spread.py (ERA5 via amy_fetch.py)` | invariants.py (O) |
| §Robustness weather year | AMY transferred-threshold saving, Taif (mild/median/hot years 2013, 2012, 2021) | 1.5–4.3% | `T23_amy_spread.csv` | `amy_spread.py (ERA5 via amy_fetch.py)` | invariants.py (O) |

## 3. Result-file catalogue

**CURRENT** files are the source of printed numbers. **SUPERSEDED** files are kept for the record and must never be cited as a source. **LEGACY** files belong to the withdrawn pipeline.

| File | Status | Generator | Content / replacement |
|---|---|---|---|
| `T1_heldout_three_cities.csv` | CURRENT | `run_final.py` | THERM/TUNED/guard per city, held-out means — the headline |
| `T2_timestep.csv` | CURRENT | `run_final.py` | Actuation-interval sweep, `tab:timestep`(a) |
| `T3_capacity.csv` | CURRENT | `run_final.py` | Thermal-capacity sweep, `tab:timestep`(b) |
| `T4_tariff_heldout.csv` | CURRENT | `t4_heldout.py` | Three tariff epochs, `tab:sensitivity`(a) |
| `T4_tariff.csv` | SUPERSEDED | `run_final.py` | Single-window tariff sweep → replaced by T4_tariff_heldout.csv |
| `T5_switchcost.csv` | CURRENT | `run_final.py` | c_sw sweep, `tab:sensitivity`(b) |
| `T6_per_window.csv` | CURRENT | `run_final.py` | Per-window THERM/TUNED, `fig:season` |
| `T7_deadband.csv` | CURRENT | `deadband.py` | Comparator deadband sweep, `tab:sensitivity`(c) |
| `T8_mpc.csv` | SUPERSEDED | `mpc.py` | Aggregate-matched MPC → T15 → T21 |
| `T9_ceilings.csv` | CURRENT | `ceilings.py` | Occupied-ceiling search per arm |
| `T10_latent.csv` | SUPERSEDED | `latent_adopted.py` | Broken latent study (GHI on vertical glazing, no matching, RH 103.8%) → T22 |
| `latent.csv` | SUPERSEDED | `latent.py` | Earliest latent study → T22 |
| `T11_meanbound.csv` | CURRENT | `dp_meanconstrained.py` | Lagrangian bound at λ*, aggregate matching |
| `T12_tariff_clairvoyant.csv` | SUPERSEDED | `—` | Clairvoyant under tariffs, pointwise cap → T14 |
| `T13_attainable.csv` | SUPERSEDED | `(retired)` | Aggregate-λ attainable, ±15.63 window dispersion → T14 per-window |
| `T14_perwindow.csv / _summary.csv` | CURRENT | `perwindow.py` | Per-window matched clairvoyant + bound — the bracket in `tab:main` |
| `T15_mpc_perwindow.csv / _summary.csv` | SUPERSEDED | `mpc_perwindow.py (801, 0.05 K caps)` | Coarse-grid MPC → T21_g1601 |
| `T16_mpc_ruled.csv / _summary.csv` | CURRENT | `mpc_ruled.py (1601, refined)` | Rule-constrained MPC — the 2×2 cell |
| `T17_bound_convergence.csv` | CURRENT | `bound_converge.py` | Bound at 1601/3201/6401 points; published bound outward-rounded from finest |
| `T18_scalability.csv / T18_environment.json` | CURRENT | `scalability_disclosure.py` | Timings + full environment disclosure |
| `T19_coordination.csv` | CURRENT | `coordination.py` | Multi-zone coordination scan (no admissible match found; not in manuscript) |
| `T20_paired_stats.csv` | CURRENT | `stats_paired.py` | Wilcoxon / sign / BCa / TOST for all paired comparisons |
| `T21_g1601_{city}_mpc_*.csv` | CURRENT | `mpc_perwindow.py --ngrid 1601` | MPC 6/24/48 h, the quoted arm |
| `T21_g801_mpc_*.csv` | CURRENT (control) | `mpc_perwindow.py --ngrid 801` | Grid-convergence control under identical protocol |
| `T22_latent2.csv` | CURRENT | `latent2.py` | Rebuilt latent study (POA, saturation clamp, per-window matching) |
| `T23_amy_spread.csv` | CURRENT | `amy_spread.py` | 15 real years (ERA5): hot/median/mild, RETUNED + TRANSFER |
| `T23_amy_retune_fine.csv` | CURRENT | `amy_retune_fine.py` | RETUNED at 0.02 K for collapsed city-years |
| `T25_cycling_energy.csv` | CURRENT | `cycling_energy.py` | Per-start transient-loss sensitivity (§Limitations) |
| `T24_orientation.csv` | CURRENT | `orientation.py (0.02 K)` | Four cardinal orientations, Riyadh |
| `rbrl_ppo5.csv / _perwindow.csv` | CURRENT | `rbrl_ppo.py --seeds 5` | RBRL five seeds × three cities |
| `rbrl_norules5.csv / _perwindow.csv` | CURRENT | `rbrl_ppo.py --norules --nomatch --seeds 5` | No-rules ablation, five seeds |
| `rbrl_ppo.csv / rbrl_norules.csv` | SUPERSEDED | `rbrl_ppo.py --seeds 3` | Three-seed runs → five-seed files |
| `taif_cap_scan.csv` | CURRENT | `taif_match.py` | Taif ceiling family (6.2–8.6%) |
| `sw_share.csv` | CURRENT | `sw_share.py` | Switching share, one definition for both sensitivity panels |
| `setback_isocomfort.csv` | LEGACY | `(no current generator)` | Iso-comfort setback, pre per-window protocol → T14 SETBACK arm |
| `final_ppo.csv, ppo_ablate.csv, budget.csv, alpha*.csv, baselines.csv, capacity.csv, csw_sweep.csv, integrator*.csv, tariffs.csv, rerun_part*.csv, replacement_table.csv, fixtest.csv` | LEGACY | `various (run_all.py, rerun.py, …)` | Earlier pipeline; none is the source of a printed figure |

## 4. External data

| Data | Location | Source | Notes |
|---|---|---|---|
| TMYx weather (headline) | `riyadh.epw`, `jeddah.epw`, `taif.epw` | climate.onebuilding.org SRC-TMYx 2009–2023 | WMO 404380 / 410240 / 410360 |
| Actual years (spread study) | `amy/{city}_{year}.csv` (45 files) | ERA5 reanalysis via Open-Meteo archive API | Fetched 11 Nov 2026; selection in `amy/amy_selected.json`; used for spread only |

## 5. Declared limitations (not fixable from simulation)

- Installed-stock thermostat deadband: decides the sign of the result (`T7_deadband.csv`); needs field measurement.
- Field validation: none; model is an uncalibrated reference model (ASHRAE G14 statement in §Robustness).
- Taif comfort matching: bisection non-monotone (plant cannot correct under-temperature); Taif reported at family level.

## 6. Revision history pointers

What each revision changed, and why, is recorded in the manuscript's own earlier-version notes and in the response to the reviewers (confidential correspondence, not published here). The withdrawn pipeline is preserved in `archive/withdrawn-pipeline/`. The paper source is in `paper/`.

