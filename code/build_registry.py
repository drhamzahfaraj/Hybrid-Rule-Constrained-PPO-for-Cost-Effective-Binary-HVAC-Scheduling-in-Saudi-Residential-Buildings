#!/usr/bin/env python3
"""Build VALUES_REGISTRY.md: every reported number, where it lives, what made it.

Why this exists
---------------
The manuscript went through a major revision in which about forty reviewer
findings were closed, several result files were superseded, and some numbers
moved more than once. When the next round of feedback arrives, the question is
always the same: where does this number come from, which script made it, which
check guards it, and is the file I am looking at still the current one?

This script answers that from the data itself. Every value in the registry is
READ FROM ITS RESULT FILE when the registry is built, never typed in, so the
registry cannot drift from the data. If a value is regenerated, rebuild the
registry and the document follows.

Run:  python3 build_registry.py      ->  VALUES_REGISTRY.md (repository root)
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import csv, json, os, sys, datetime, glob, statistics as st

ROOT = _ROOT + ""
RES = f"{ROOT}/results"
OUT = _os.path.join(ROOT, "..", "VALUES_REGISTRY.md")   # repository root


# ------------------------------------------------------------------ loading
def load(name):
    p = f"{RES}/{name}"
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return list(csv.DictReader(f))


def pick(rows, **kw):
    """The single row matching every key=value (string comparison)."""
    hits = [r for r in rows if all(str(r.get(k)) == str(v) for k, v in kw.items())]
    if len(hits) != 1:
        raise LookupError(f"{kw}: {len(hits)} matches")
    return hits[0]


def f(x, nd=1):
    return f"{float(x):.{nd}f}"


# ------------------------------------------------------------------ the spec
# Each entry: (manuscript location, quantity, value-producing function,
#              source file, generating script, check that pins it)
# The value function receives nothing and returns a string; any exception is
# reported in the registry as MISSING rather than silently skipped.
def spec():
    T1 = load("T1_heldout_three_cities.csv")
    T14 = load("T14_perwindow_summary.csv")
    T17 = load("T17_bound_convergence.csv")
    T17sb = load("T17_bound_convergence_sb.csv")
    T20 = load("T20_paired_stats.csv")
    T22 = load("T22_latent2.csv")
    T23 = load("T23_amy_spread.csv")
    T24 = load("T24_orientation.csv")
    T16 = load("T16_mpc_ruled_summary.csv")
    T7 = load("T7_deadband.csv")
    T5 = load("T5_switchcost.csv")
    T4 = load("T4_tariff_heldout.csv")
    TS = load("taif_cap_scan.csv")
    P5 = load("rbrl_ppo5.csv")
    N5 = load("rbrl_norules5.csv")
    MPC = {}
    for c in ("riyadh", "jeddah", "taif"):
        for r in load(f"T21_g1601_{c}_mpc_summary.csv") or []:
            MPC[(c, float(r["horizon_h"]))] = r
    M801 = {(r["city"], float(r["horizon_h"])): r
            for r in load("T21_g801_mpc_summary.csv") or []}

    def tuned(city):
        r = [x for x in T1 if x["city"] == city and x["controller"].startswith("tuned")
             and x["tariff"] == "inforce"]
        assert len(r) == 1, (city, len(r))
        return r[0]

    def stat(comp, city_cost):
        """T20 row for a comparison, disambiguated by the THERM mean cost."""
        for r in T20:
            if r["comparison"] == comp and abs(float(r["mean_cost_b"] if comp.endswith("THERM") else r["mean_cost_a"]) - city_cost) < 0.03:
                return r
        raise LookupError(comp)

    therm = {"riyadh": 1.1183, "jeddah": 0.9926, "taif": 0.6139}
    tuned_J = {c: float(tuned(c)["J_mean"]) for c in therm}

    def stat_mpc(city, hh):
        for r in T20:
            if r["comparison"] == f"TUNED vs MPC {hh} h" and abs(float(r["mean_cost_a"]) - tuned_J[city]) < 1e-3:
                return r
        raise LookupError(f"{city} {hh}")

    def seeds_exact(city):
        rs = [r for r in P5 if r["city"] == city]
        J = [float(r["J"]) for r in rs]
        m = st.mode([round(j, 4) for j in J])
        return f"{sum(1 for j in J if round(j,4)==m)}/{len(J)} seeds at J={m}"

    def taif_family():
        ok = [r for r in TS if abs(float(r["dT"])) <= 0.03 and float(r["deg_h_over"]) <= 1e-9]
        s = [float(r["sav"]) for r in ok]
        return f"{len(ok)} admissible ceilings, {min(s):.1f}–{max(s):.1f}%"

    def amy(city, years):
        tr = {r["year"]: float(r["sav"]) for r in T23 if r["city"] == city and r["kind"] == "TRANSFER"}
        v = [tr[y] for y in years]
        return f"{min(v):.1f}–{max(v):.1f}%"

    def lat(city):
        s = float(pick(T22, city=city, model="sensible")["sav"])
        l = float(pick(T22, city=city, model="latent")["sav"])
        return f"{l - s:+.1f} pts"

    def bound_conv(city):
        rs = sorted([r for r in T17 if r["city"] == city and r["arm"] == "OPT"], key=lambda r: int(r["n_grid"]))
        return " → ".join(f"{float(r['bound_sav']):.2f}% @{r['n_grid']}" for r in rs)

    S = []
    A = S.append

    # ---------------- headline
    for c, nm in (("riyadh", "Riyadh"), ("jeddah", "Jeddah"), ("taif", "Taif")):
        A(("Abstract; Table `tab:main`", f"TUNED saving, {nm}",
           lambda c=c: f"{f(tuned(c)['cost_sav_mean_pct'],2)} ± {f(tuned(c)['cost_sav_sd_pct'],2)}%",
           "T1_heldout_three_cities.csv", "run_final.py", "invariants.py (A, I); verify_numbers.py"))
    for c, nm in (("riyadh", "Riyadh"), ("jeddah", "Jeddah"), ("taif", "Taif")):
        A(("Abstract; `tab:main` CLV row", f"Attainable clairvoyant saving (per-window matched), {nm}",
           lambda c=c: f"{f(pick(T14, city=c, arm='OPT')['att_sav'],2)} ± {f(pick(T14, city=c, arm='OPT')['att_sd'],2)}%",
           "T14_perwindow_summary.csv", "perwindow.py", "invariants.py (bracket class); verify_numbers.py"))
        A(("`tab:main` bound row", f"Lagrangian bound, grid-converged, {nm} (published value outward-rounded)",
           lambda c=c: bound_conv(c),
           "T17_bound_convergence.csv", "bound_converge.py", "invariants.py (bound class)"))
        A(("`tab:main` setback rows", f"Setback attainable (per-window) / converged bound, {nm}",
           lambda c=c: f"{f(pick(T14, city=c, arm='OPT+sb')['att_sav'],2)}% / " + " → ".join(f"{float(r['bound_sav']):.2f}% @{r['n_grid']}" for r in sorted([r for r in T17sb if r['city']==c], key=lambda r:int(r['n_grid']))),
           "T14_perwindow_summary.csv; T17_bound_convergence_sb.csv", "perwindow.py; bound_converge.py", "verify_numbers.py"))

    # ---------------- statistics
    for c, nm in (("riyadh", "Riyadh"), ("jeddah", "Jeddah"), ("taif", "Taif")):
        A(("Abstract; §Robustness statistics", f"TUNED vs THERM, {nm}: Wilcoxon p, BCa 95% CI, windows favouring TUNED",
           lambda c=c: (lambda r: f"p={float(r['wilcoxon_p']):.3f}, CI [{f(r['sav_a_lo'])}, {f(r['sav_a_hi'])}]%, sign {7-int(r['sign_pos'])}/7")(stat("TUNED vs THERM", therm[c])),
           "T20_paired_stats.csv", "stats_paired.py", "invariants.py (M); verify_numbers.py (I)"))
    for c, nm in (("riyadh", "Riyadh"), ("jeddah", "Jeddah")):
        for hh in (24, 48):
            A(("Abstract; §Ablation statistics; Conclusions finding 4", f"TUNED vs MPC-{hh}h, {nm}: diff, CI, p",
               lambda c=c, hh=hh: (lambda r: f"diff {float(r['diff_pts']):+.2f} pts, CI [{f(r['diff_lo'])}, {f(r['diff_hi'])}], p={float(r['wilcoxon_p']):.3f}")(stat_mpc(c, hh)),
               "T20_paired_stats.csv", "stats_paired.py (reads T21)", "invariants.py (K)"))

    # ---------------- MPC
    for c, nm in (("riyadh", "Riyadh"), ("jeddah", "Jeddah"), ("taif", "Taif")):
        for hh in (6.0, 24.0, 48.0):
            A(("`tab:abl_component` MPC rows; §Ablation", f"MPC {hh:.0f} h, {nm} (1601 grid, per-window, 0.01 K caps)",
               lambda c=c, hh=hh: f"{f(MPC[(c,hh)]['sav'],2)} ± {f(MPC[(c,hh)]['sav_sd'],2)}%, n_win={MPC[(c,hh)]['n_win']}, worst dT {float(MPC[(c,hh)]['worst_dT']):+.3f} K",
               f"T21_g1601_{c}_mpc_summary.csv", "mpc_perwindow.py --ngrid 1601", "invariants.py (K); verify_numbers.py"))
    for c, nm in (("riyadh", "Riyadh"), ("jeddah", "Jeddah"), ("taif", "Taif")):
        A(("`tab:abl_component` footnote (grid convergence)", f"MPC 24 h on 801 grid (control run), {nm}",
           lambda c=c: f"{f(M801[(c,24.0)]['sav'],2)}% (vs {f(MPC[(c,24.0)]['sav'],2)}% @1601)",
           "T21_g801_mpc_summary.csv", "mpc_perwindow.py --ngrid 801", "mpc_final.py (convergence printout)"))
    A(("2×2 table; finding 4", "MPC 24 h inside rules R1–R2, Riyadh",
       lambda: f"{f(pick(T16, ruled='True')['sav'],2)}% (unruled {f(pick(T16, ruled='False')['sav'],2)}%)",
       "T16_mpc_ruled_summary.csv", "mpc_ruled.py (1601, refined caps)", "verify_numbers.py"))

    # ---------------- PPO
    for c, nm in (("riyadh", "Riyadh"), ("jeddah", "Jeddah")):
        A(("Abstract; Corollary 1 discussion; `tab:abl_component`", f"RBRL five-seed identity with hysteresis, {nm}",
           lambda c=c: seeds_exact(c), "rbrl_ppo5.csv + rbrl_ppo5_perwindow.csv", "rbrl_ppo.py --seeds 5",
           "manual: per-window |J_RBRL − J_hyst| = 0 (see triage doc)"))
    A(("`tab:abl_component` no-rules row", "PPO without rule layer, Riyadh, 5 seeds",
       lambda: (lambda s: f"{st.mean(s):+.2f} ± {st.stdev(s):.2f}%, negative in {sum(x<0 for x in s)}/5")([float(r['sav']) for r in N5]),
       "rbrl_norules5.csv", "rbrl_ppo.py --norules --nomatch --seeds 5", "—"))

    # ---------------- sensitivity
    for row in T7:
        A(("`tab:sensitivity`(c) deadband", f"Deadband {row['deadband']} K: TUNED saving",
           lambda row=row: f"{f(row['tuned_sav'],1)}% (admissible: {row['admissible']})",
           "T7_deadband.csv", "deadband.py", "verify_numbers.py"))
    for row in T4:
        A(("`tab:sensitivity`(a) tariff", f"Tariff {row['schedule']} ({row['price']} SAR/kWh): TUNED / OPT",
           lambda row=row: f"{f(row['tuned_sav'],1)}% / {f(row['opt_sav'],1)}%, switching share {row['sw_share_pct']}%",
           "T4_tariff_heldout.csv", "t4_heldout.py", "verify_numbers.py"))
    for row in T5:
        A(("`tab:sensitivity`(b) switch-on cost", f"c_sw = {row['c_sw']} SAR: DP / rule saving",
           lambda row=row: f"{row['dp_sav_pct']}% / {row['rule_sav_pct']}%",
           "T5_switchcost.csv", "run_final.py", "verify_numbers.py"))
    for row in (load("T25_cycling_energy.csv") or []):
        A(("§Limitations cycling energy", f"Per-start loss {row['wh_per_start']} Wh: TUNED-vs-THERM energy saving",
           lambda row=row: f"{float(row['energy_saving_pct']):+.2f}%",
           "T25_cycling_energy.csv", "cycling_energy.py", "—"))
    A(("§Ablation Taif note", "Taif admissible ceiling family",
       taif_family, "taif_cap_scan.csv", "taif_match.py", "verify_numbers.py"))

    # ---------------- second-pass studies
    for c, nm in (("riyadh", "Riyadh"), ("jeddah", "Jeddah"), ("taif", "Taif")):
        A(("§Case Studies latent para; §Limitations", f"Latent effect on saving, {nm}",
           lambda c=c: lat(c), "T22_latent2.csv", "latent2.py", "invariants.py (N); verify_numbers.py (I)"))
    A(("§Case Studies latent para", "Jeddah: time over ASHRAE 55 humidity-ratio limit / coil at latent cap",
       lambda: f"{pick(T22, city='jeddah', model='latent')['w_over_pct']}% / {pick(T22, city='jeddah', model='latent')['lat_capped_pct']}%",
       "T22_latent2.csv", "latent2.py", "invariants.py (N)"))
    for row in T24:
        A(("§Robustness orientation", f"Orientation {row['orientation']}: saving (starts removed/day)",
           lambda row=row: f"{f(row['sav'],2)}% ({float(row['therm_fs'])-float(row['rule_fs']):.2f})",
           "T24_orientation.csv", "orientation.py (0.02 K tune grid)", "verify_numbers.py (I)"))
    for c, nm, ys in (("riyadh", "Riyadh", ("2013", "2018", "2021")),
                      ("jeddah", "Jeddah", ("2011", "2017", "2023")),
                      ("taif", "Taif", ("2013", "2012", "2021"))):
        A(("§Robustness weather year", f"AMY transferred-threshold saving, {nm} (mild/median/hot years {', '.join(ys)})",
           lambda c=c, ys=ys: amy(c, ys), "T23_amy_spread.csv", "amy_spread.py (ERA5 via amy_fetch.py)", "invariants.py (O)"))
    return S


# ------------------------------------------------------------------ catalogue
# Status of every results file. CURRENT = the source of a printed number.
# SUPERSEDED = kept for the record; must not be the source of a printed figure.
CATALOGUE = [
    # file, status, generator, what it is / what replaced it
    ("T1_heldout_three_cities.csv", "CURRENT", "run_final.py", "THERM/TUNED/guard per city, held-out means — the headline"),
    ("T2_timestep.csv", "CURRENT", "run_final.py", "Actuation-interval sweep, `tab:timestep`(a)"),
    ("T3_capacity.csv", "CURRENT", "run_final.py", "Thermal-capacity sweep, `tab:timestep`(b)"),
    ("T4_tariff_heldout.csv", "CURRENT", "t4_heldout.py", "Three tariff epochs, `tab:sensitivity`(a)"),
    ("T4_tariff.csv", "SUPERSEDED", "run_final.py", "Single-window tariff sweep → replaced by T4_tariff_heldout.csv"),
    ("T5_switchcost.csv", "CURRENT", "run_final.py", "c_sw sweep, `tab:sensitivity`(b)"),
    ("T6_per_window.csv", "CURRENT", "run_final.py", "Per-window THERM/TUNED, `fig:season`"),
    ("T7_deadband.csv", "CURRENT", "deadband.py", "Comparator deadband sweep, `tab:sensitivity`(c)"),
    ("T8_mpc.csv", "SUPERSEDED", "mpc.py", "Aggregate-matched MPC → T15 → T21"),
    ("T9_ceilings.csv", "CURRENT", "ceilings.py", "Occupied-ceiling search per arm"),
    ("T10_latent.csv", "SUPERSEDED", "latent_adopted.py", "Broken latent study (GHI on vertical glazing, no matching, RH 103.8%) → T22"),
    ("latent.csv", "SUPERSEDED", "latent.py", "Earliest latent study → T22"),
    ("T11_meanbound.csv", "CURRENT", "dp_meanconstrained.py", "Lagrangian bound at λ*, aggregate matching"),
    ("T12_tariff_clairvoyant.csv", "SUPERSEDED", "—", "Clairvoyant under tariffs, pointwise cap → T14"),
    ("T13_attainable.csv", "SUPERSEDED", "(retired)", "Aggregate-λ attainable, ±15.63 window dispersion → T14 per-window"),
    ("T14_perwindow.csv / _summary.csv", "CURRENT", "perwindow.py", "Per-window matched clairvoyant + bound — the bracket in `tab:main`"),
    ("T15_mpc_perwindow.csv / _summary.csv", "SUPERSEDED", "mpc_perwindow.py (801, 0.05 K caps)", "Coarse-grid MPC → T21_g1601"),
    ("T16_mpc_ruled.csv / _summary.csv", "CURRENT", "mpc_ruled.py (1601, refined)", "Rule-constrained MPC — the 2×2 cell"),
    ("T17_bound_convergence.csv", "CURRENT", "bound_converge.py", "Bound at 1601/3201/6401 points; published bound outward-rounded from finest"),
    ("T18_scalability.csv / T18_environment.json", "CURRENT", "scalability_disclosure.py", "Timings + full environment disclosure"),
    ("T19_coordination.csv", "CURRENT", "coordination.py", "Multi-zone coordination scan (no admissible match found; not in manuscript)"),
    ("T20_paired_stats.csv", "CURRENT", "stats_paired.py", "Wilcoxon / sign / BCa / TOST for all paired comparisons"),
    ("T21_g1601_{city}_mpc_*.csv", "CURRENT", "mpc_perwindow.py --ngrid 1601", "MPC 6/24/48 h, the quoted arm"),
    ("T21_g801_mpc_*.csv", "CURRENT (control)", "mpc_perwindow.py --ngrid 801", "Grid-convergence control under identical protocol"),
    ("T22_latent2.csv", "CURRENT", "latent2.py", "Rebuilt latent study (POA, saturation clamp, per-window matching)"),
    ("T23_amy_spread.csv", "CURRENT", "amy_spread.py", "15 real years (ERA5): hot/median/mild, RETUNED + TRANSFER"),
    ("T23_amy_retune_fine.csv", "CURRENT", "amy_retune_fine.py", "RETUNED at 0.02 K for collapsed city-years"),
    ("T25_cycling_energy.csv", "CURRENT", "cycling_energy.py", "Per-start transient-loss sensitivity (§Limitations)"),
    ("T24_orientation.csv", "CURRENT", "orientation.py (0.02 K)", "Four cardinal orientations, Riyadh"),
    ("rbrl_ppo5.csv / _perwindow.csv", "CURRENT", "rbrl_ppo.py --seeds 5", "RBRL five seeds × three cities"),
    ("rbrl_norules5.csv / _perwindow.csv", "CURRENT", "rbrl_ppo.py --norules --nomatch --seeds 5", "No-rules ablation, five seeds"),
    ("rbrl_ppo.csv / rbrl_norules.csv", "SUPERSEDED", "rbrl_ppo.py --seeds 3", "Three-seed runs → five-seed files"),
    ("taif_cap_scan.csv", "CURRENT", "taif_match.py", "Taif ceiling family (6.2–8.6%)"),
    ("sw_share.csv", "CURRENT", "sw_share.py", "Switching share, one definition for both sensitivity panels"),
    ("setback_isocomfort.csv", "LEGACY", "(no current generator)", "Iso-comfort setback, pre per-window protocol → T14 SETBACK arm"),
    ("final_ppo.csv, ppo_ablate.csv, budget.csv, alpha*.csv, baselines.csv, capacity.csv, csw_sweep.csv, integrator*.csv, tariffs.csv, rerun_part*.csv, replacement_table.csv, fixtest.csv", "LEGACY", "various (run_all.py, rerun.py, …)", "Earlier pipeline; none is the source of a printed figure"),
]

LOOKUP = [
    ("Is the headline saving real / significant?", "T1_heldout_three_cities.csv; T20_paired_stats.csv", "run_final.py; stats_paired.py", "§Results, §Robustness (statistics paragraph)"),
    ("Is the comparator (THERM) fair? What deadband?", "T7_deadband.csv", "deadband.py", "`tab:sensitivity`(c); §Limitations"),
    ("What is the best achievable? Is the bound valid?", "T14_perwindow_summary.csv; T17_bound_convergence.csv", "perwindow.py; bound_converge.py; verify_optimality.py", "§Results `subsec:bound`; `tab:main`"),
    ("Does MPC beat the rule? Horizon dependence? Grid convergence?", "T21_g1601_*; T21_g801_*; T16_mpc_ruled_summary.csv; T20", "mpc_perwindow.py; mpc_ruled.py; mpc_final.py", "§Ablation; 2×2; Conclusions finding 4"),
    ("Does PPO add anything? Seeds?", "rbrl_ppo5*.csv; rbrl_norules5*.csv", "rbrl_ppo.py; verify_corollary.py", "Corollary 1 + Remark `rem:cor_scope`; `tab:abl_component`"),
    ("Corollary 1 proof / scope", "—", "verify_corollary.py (constructive test)", "§Optimal Schedule, proof + `rem:cor_attain` + `rem:cor_scope`"),
    ("Tariff dependence / cost models", "T4_tariff_heldout.csv; sw_share.csv", "t4_heldout.py; tariff_path.py (path-independence)", "Proposition `prop:path`; `tab:sensitivity`(a)"),
    ("Switch-on cost c_sw justification", "T5_switchcost.csv", "run_final.py", "§Simulation Setup (wear derivation + documented search)"),
    ("Latent load / humidity / ASHRAE 55", "T22_latent2.csv", "latent2.py (selftest reproduces headline)", "§Case Studies humidity para; §Limitations"),
    ("Weather: one TMY year only?", "T23_amy_spread.csv; T23_amy_retune_fine.csv; amy/amy_summary.csv", "amy_fetch.py; amy_retry.py; amy_spread.py; amy_retune_fine.py", "§Robustness 'Weather year'"),
    ("Orientation", "T24_orientation.csv", "orientation.py", "§Robustness"),
    ("Actuation interval / thermal capacity admissibility", "T2_timestep.csv; T3_capacity.csv", "run_final.py; degree_hours_cause.py", "`tab:timestep`; `rem:dt_acc`"),
    ("Taif anomalies", "taif_cap_scan.csv", "taif_match.py", "§Ablation Taif note"),
    ("Cycling energy / C_D", "T25_cycling_energy.csv", "cycling_energy.py", "§Limitations 'No per-start energy penalty'"),
    ("Calibration (ASHRAE G14)", "—", "—", "§Robustness 'Calibration status'"),
    ("Computational cost / scalability", "T18_scalability.csv; T18_environment.json", "scalability_disclosure.py", "§Discussion scalability"),
    ("Multi-zone / inter-zone coupling", "T19_coordination.csv", "multizone.py (selftest); coordination.py", "§Results 'Four withdrawals' → cites Faraj 2026"),
]


def main():
    lines = []
    w = lines.append
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    w("# Values Registry")
    w("")
    w(f"Generated {now} by `build_registry.py` from the files in `results/`. "
      "**Do not edit by hand** — every value below is read from its result file when "
      "this document is built, so it cannot disagree with the data. After any re-run, "
      "rebuild with `python3 build_registry.py`.")
    w("")
    w("Manuscript: *Rule-Constrained PPO for Binary HVAC Scheduling in Saudi Residential "
      "Buildings: Cost Savings, Their Governing Parameters, and an Optimality Bracket* "
      "(JKSU-ES, major revision, resubmission due 23 Nov 2026).")
    w("")
    w("## How to verify everything")
    w("")
    w("```bash")
    w("cd code")
    w("python3 invariants.py       # gate: exits non-zero on any failure; run before any table")
    w("python3 verify_numbers.py   # re-derives every printed figure from its CSV")
    w("python3 verify_optimality.py  # backward check of the clairvoyant schedule")
    w("python3 build_registry.py   # rebuilds this document")
    w("```")
    w("")
    w("## 1. Reviewer question → where to look")
    w("")
    w("| Question | Data | Script | Manuscript |")
    w("|---|---|---|---|")
    for q, d, s, m in LOOKUP:
        w(f"| {q} | {d} | {s} | {m} |")
    w("")
    w("## 2. Every reported value, by manuscript location")
    w("")
    w("| Location | Quantity | Value | Source file | Generator | Pinned by |")
    w("|---|---|---|---|---|---|")
    missing = 0
    for loc, q, fn, src, gen, chk in spec():
        try:
            v = fn()
        except Exception as e:
            v = f"**MISSING** ({type(e).__name__}: {e})"
            missing += 1
        w(f"| {loc} | {q} | {v} | `{src}` | `{gen}` | {chk} |")
    w("")
    w("## 3. Result-file catalogue")
    w("")
    w("**CURRENT** files are the source of printed numbers. **SUPERSEDED** files are kept "
      "for the record and must never be cited as a source. **LEGACY** files belong to the "
      "withdrawn pipeline.")
    w("")
    w("| File | Status | Generator | Content / replacement |")
    w("|---|---|---|---|")
    for fl, stt, gen, what in CATALOGUE:
        w(f"| `{fl}` | {stt} | `{gen}` | {what} |")
    w("")
    # weather data
    w("## 4. External data")
    w("")
    w("| Data | Location | Source | Notes |")
    w("|---|---|---|---|")
    w("| TMYx weather (headline) | `riyadh.epw`, `jeddah.epw`, `taif.epw` | climate.onebuilding.org SRC-TMYx 2009–2023 | WMO 404380 / 410240 / 410360 |")
    n_amy = len(glob.glob(f"{ROOT}/amy/*_20*.csv"))
    w(f"| Actual years (spread study) | `amy/{{city}}_{{year}}.csv` ({n_amy} files) | ERA5 reanalysis via Open-Meteo archive API | Fetched 11 Nov 2026; selection in `amy/amy_selected.json`; used for spread only |")
    w("")
    w("## 5. Declared limitations (not fixable from simulation)")
    w("")
    w("- Installed-stock thermostat deadband: decides the sign of the result (`T7_deadband.csv`); needs field measurement.")
    w("- Field validation: none; model is an uncalibrated reference model (ASHRAE G14 statement in §Robustness).")
    w("- Taif comfort matching: bisection non-monotone (plant cannot correct under-temperature); Taif reported at family level.")
    w("")
    w("## 6. Revision history pointers")
    w("")
    w("What each revision changed, and why, is recorded in the manuscript's own "
      "earlier-version notes and in the response to the reviewers (confidential "
      "correspondence, not published here). The withdrawn pipeline is preserved in "
      "`archive/withdrawn-pipeline/`. The paper source is in `paper/`.")
    w("")
    if missing:
        w(f"> ⚠ {missing} value(s) could not be read — see MISSING entries above.")
    open(OUT, "w").write("\n".join(lines) + "\n")
    print(f"-> {OUT}  ({len(spec())} values, {missing} missing)")
    return missing


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
