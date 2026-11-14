#!/usr/bin/env python3
"""The v3 result-file names and the per-window row selectors (RULING_round4 F16-F18, §4.2, §12.5).

ONE place for the names of the files the round-4 reruns write and the manuscript cites. The
consumers (cycling_energy, stats_v3, gen_tables_v3, invariants class P, verify_numbers,
build_registry) and tests/cited_tables.txt all use these names; if a job writes under another
name, change it HERE (and in the manifest), nowhere else.

Every selector reads through rbrl_io.read_csv (tag-aware, records the input sha) and RAISES on a
missing file or an empty selection: a gate or a table never silently skips a cited source.

Row schema (t1_v2.evaluate; carried by mpc_lambda, rbrl_ppo, shield, setback_arms): per-window
rows have window, J_arm, J_therm0, J_eq, delta_w, bracket_gap, eq_clipped, n_crossings,
J_eq_max, T_arm, T_therm0, dT_w,
fs_arm, fs_eq, E_arm, E_eq, deg_h_over, deg_h_under, deg_h_cmd_under, deg_h_ff_under, T_end,
fallback_steps, fit_status (+ prov_* columns from rbrl_io); summary rows have s_pooled_eq (= s_eq_minJ), s_eq_maxJ, n_eq_multi, s_raw,
dT_pooled, max_abs_dT_w, start_sav_eq, energy_sav_eq, J_arm_mean, J_eq_mean, J_therm0_mean,
deg_h_*, T_end_mean, fallback_steps, n_eq_clipped, max_bracket_gap, fit_status.
"""
from __future__ import annotations
import os
import numpy as np
import rbrl_io as IO

CITIES = ("riyadh", "jeddah", "taif")
CN = {"riyadh": "Riyadh", "jeddah": "Jeddah", "taif": "Taif"}

# job -> file stem(s) under results/ (".csv" implied; {c} = city). Keep in step with
# tests/cited_tables.txt (tests/test_gates_v3.py checks that every stem used here is listed).
V3 = dict(
    T1="T1v3_heldout", T1_PW="T1v3_perwindow",                    # J1 TUNED/guard x 3 tariffs
    T1_SENS="T1v3_sens",                                          # J1 hardware 0.1 K + per-window rows
    T7="T7v3_deadband", T7_PW="T7v3_perwindow",                   # J2
    T5="T5v3_switchcost_tuned",                                   # J2/J20
    T4_BOUND="T4v3_bound",                                        # J19 (bound at 0.05/0.21)
    T5_BOUND="T5v3_bound",                                        # bound at c_sw 0.025/0.114 (J20)
    MPC="T21v3_{c}", MPC_PW="T21v3_{c}_perwindow",                # J3 perfect, 0.25..48 h
    MPC_PERS="T21v3_pers_{c}", MPC_PERS_PW="T21v3_pers_{c}_perwindow",   # J4
    MPC_CONV="T21v3_conv_{c}",                                    # J5 3201 points at the fitted lambda
    MPC_RULED="T16v3_r23.8-22.4_{c}", MPC_RULED_PW="T16v3_r23.8-22.4_{c}_perwindow",   # J6(i) 23.80/22.40
    MPC_GUARD="T16v3_r{g}_{c}", MPC_GUARD_PW="T16v3_r{g}_{c}_perwindow",                 # J6(ii) fitted guard R1/R2
    RBRL="rbrl_ppo5_v3_{c}", RBRL_PW="rbrl_ppo5_v3_{c}_perwindow",       # J11
    D1="T_D1_latch_{c}", D1_PW="T_D1_latch_{c}_perwindow",        # J11/X4
    D1_PPO="T_D1_ppo_{c}",                                        # J11/X4 shield on the saved PPO models
    E2="rbrl_e2_v3_riyadh", E2_PW="rbrl_e2_v3_riyadh_perwindow",  # J12
    CLV="T17v3_{c}", CLV_PW="T17v3_{c}_perwindow",                # J8 + J9 (bound_v2 main)
    DUAL="T17v3_{c}_dualcurves",                                  # J9 dual curves (.json)
    CLV_SB="T17v3sb_{c}", CLV_SB_PW="T17v3sb_{c}_perwindow",      # J15 setback bound + CLV (bound_v2 sb)
    BOUND_RULED="T17v3_ruled_{c}",                                # J10 ruled relaxed bound + CLV in rules
    BA="T17v3_Ba",                                                # J17 B_a per arm, certificates (bound_at)
    STATS="T20v3_paired_stats",                                   # J17 stats_v3
    CYCLING="T25v3_cycling_energy",                               # J23 cycling_energy
    E1="E1v3_hold_dp",                                            # J11 E1: J(hold) vs DP lam=0 in rules
    SB_RULE="T28v3_setback_rule", SB_RULE_PW="T28v3_setback_rule_perwindow",   # J15 TUNED-SB/MANUAL/THERM-SB
    SB_MPC="T28v3_setback_mpc_{c}", SB_MPC_PW="T28v3_setback_mpc_{c}_perwindow",   # J15 MPC-SB
    AMY="T23v3_amy_spread", ORIENT="T24v3_orientation",           # J16 (orientation: Riyadh; other
                                                                  #   cities append _<city>, not cited)
    NORULES="rbrl_norules5_v3", NORULES_PW="rbrl_norules5_v3_perwindow",   # J18
    TIMESTEP="T2v3_timestep",                                     # J24 timestep_table (tab:s-timestep)
)
# auxiliary (not cited, so not in V3 / the manifest): parameter files read by downstream jobs, and
# subsets of cited tables. Producers take these names from here too.
AUX = dict(
    TUNED_PARAMS="tuned_params_v2",        # J1 -> MPC rollout base (mpc_lambda), search audit (.json)
    GUARD_FIT="T26v3_guard_fit",           # J1 guard rows of T1v3_heldout (convenience subset)
    SB_PARAMS="setback_rule_params_v3",    # J15 TUNED-SB parameters -> MPC-SB rollout base (.json)
)


def mpc_stem(forecast="perfect", ruled=False, conv=False, suffix=""):
    """file stem (without _<city>) of an mpc_lambda run: T21v3 / T21v3_pers / T21v3_conv / T16v3,
    plus the scenario suffix (_csw<x>, _ls<x>, _r<R1>-<R2>) before the city."""
    if ruled:   # mpc_lambda writes in-rule runs as T16v3[_pers]_r<R1>-<R2>_<city> (the suffix carries the rules)
        return "T16v3" + ("_pers" if forecast == "persistence" else "") + ("_conv" if conv else "") + suffix
    key = "MPC_PERS" if forecast == "persistence" else ("MPC_CONV" if conv else "MPC")
    return V3[key].replace("_{c}", "") + ("_conv" if (conv and key != "MPC_CONV") else "") + suffix
# J-MZ (mz_r3 / mz_mpc, F19 code; names are those modules' own): Riyadh, independent units
MZ_RULES = "T31_mz_rules_riyadh_{topo}_lij{lij:g}"
MZ_MPC = "T31_mz_mpc_riyadh_{topo}_lij{lij:g}_h{h:g}"
MZ_LAYOUTS = (("1x1", (12.5,)), ("1x2", (12.5, 35.0)), ("2x2", (12.5, 35.0)), ("1x4", (12.5, 35.0)))
MZ_MPC_H = 24.0
CTH_TAGS = {2400.0: "_cth2400", 4800.0: "", 7200.0: "_cth7200", 9600.0: "_cth9600"}  # J13 / J24 (RBRL_TAG)
DT_TAGS = {5.0: "_dt5", 15.0: "", 30.0: "_dt30"}   # J24 control interval (min) -> RBRL_TAG (RBRL_DT_MIN)


# J6(ii): each city's fitted guard thresholds R1-R2 as written in the file names (ruling §21.4)
GUARD_RULES = {"riyadh": "23.6-22.4", "jeddah": "23.62-22.4", "taif": "23.66-22.4"}


def name(key, city=None, tag=""):
    return V3[key].format(c=city, g=GUARD_RULES.get(city, "")) + tag


def read_stem(stem):
    """rows of results/<stem>.csv (any name, e.g. the MZ files); raises when missing or empty."""
    p = f"{IO.R}/{stem}.csv"
    if not os.path.exists(p):
        raise FileNotFoundError(f"cited v3 table missing: {os.path.relpath(p, IO.ROOT)}")
    rows = IO.read_csv(stem, apply_tag=False)
    if not rows:
        raise ValueError(f"{stem}: empty table")
    return rows


def path(key, city=None, tag="", ext=".csv"):
    return f"{IO.R}/{name(key, city, tag)}{ext}"


def read(key, city=None, tag=""):
    """rows of a v3 CSV; FileNotFoundError (never an empty list) when it is missing."""
    p = path(key, city, tag)
    if not os.path.exists(p):
        raise FileNotFoundError(f"cited v3 table missing: {os.path.relpath(p, IO.ROOT)}")
    rows = IO.read_csv(name(key, city, tag), apply_tag=False)
    if not rows:
        raise ValueError(f"{name(key, city, tag)}: empty table")
    return rows


def _pick(rows, what, **kw):
    out = [r for r in rows if all(_eq(r.get(k), v) for k, v in kw.items())]
    if not out:
        raise LookupError(f"{what}: no rows with {kw}")
    return out


def _eq(a, v):
    if a is None:
        return False
    if isinstance(v, float):
        try:
            return abs(float(a) - v) < 1e-9
        except ValueError:
            return False
    return str(a) == str(v)


# arm label -> (summary key, per-window key, row filter). MPC labels: MPC<h> perfect, MPCp<h>
# persistence, MPCr<h> in rules (h in hours, e.g. MPC24, MPC0.25).
def _arm_spec(arm):
    if arm in ("TUNED", "guard"):
        return "T1", "T1_PW", dict(arm=arm, tariff="inforce")
    for pre, s, pw, fc in (("MPCr", "MPC_RULED", "MPC_RULED_PW", None), ("MPCp", "MPC_PERS", "MPC_PERS_PW", "persistence"),
                           ("MPC", "MPC", "MPC_PW", "perfect")):
        if arm.startswith(pre) and arm[len(pre):].replace(".", "", 1).isdigit():
            kw = dict(horizon_h=float(arm[len(pre):]))
            if fc:
                kw["forecast"] = fc
            return s, pw, kw
    if arm == "RBRL":
        return "RBRL", "RBRL_PW", {}
    if arm == "D1":
        return "D1", "D1_PW", {}
    if arm == "E2":
        return "E2", "E2_PW", {}
    raise KeyError(f"unknown arm {arm!r}")


def perwindow(arm, city, tag=""):
    """{window: row} for one arm in one city; seeded arms (RBRL, E2, D1 sigma rows) are returned
    as {window: [rows]} by perwindow_seeds. Raises on a missing file or no rows."""
    if arm == "D1":
        return d1_selected(city, tag)[1]
    _, pw, kw = _arm_spec(arm)
    rows = _pick(read(pw, city, tag), f"{arm} {city}", city=city, **kw)
    out = {}
    for r in rows:
        w = int(float(r["window"]))
        if w in out:
            raise ValueError(f"{arm} {city}: window {w} appears twice (seeded arm? use perwindow_seeds)")
        out[w] = r
    return out


def perwindow_seeds(arm, city, tag=""):
    """{seed: {window: row}} for a seeded arm (RBRL, E2)."""
    _, pw, kw = _arm_spec(arm)
    rows = _pick(read(pw, city, tag), f"{arm} {city}", **kw)
    out = {}
    for r in rows:
        if r.get("city", city) != city:
            continue
        out.setdefault(str(r.get("seed", "")), {})[int(float(r["window"]))] = r
    if not out:
        raise LookupError(f"{arm} {city}: no seeds")
    return out


def summary(arm, city, tag=""):
    """the single summary row of an arm (seeded arms: list of seed rows)."""
    s, _, kw = _arm_spec(arm)
    rows = _pick(read(s, city, tag), f"{arm} {city}", city=city, **kw)
    if arm in ("RBRL", "E2"):
        return rows
    if len(rows) != 1:
        raise ValueError(f"{arm} {city}: {len(rows)} summary rows (expected 1)")
    return rows[0]


def s_w(r):
    """per-window equalised saving (%), s_w = 1 - J_arm/J_THERM(delta_w); used only in tests/stats."""
    return 100.0 * (1.0 - float(r["J_arm"]) / float(r["J_eq"]))


def pooled(rows):
    """Rule C pooled saving (%) over per-window rows: 1 - sum J_arm / sum J_THERM(delta_w)."""
    rows = list(rows)
    return 100.0 * (1.0 - sum(float(r["J_arm"]) for r in rows) / sum(float(r["J_eq"]) for r in rows))


def seed_mean_sw(seeds):
    """{window: mean over seeds of s_w} for a seeded arm (RBRL/E2 enter the statistics as the
    per-window seed mean, as in round 3)."""
    ws = sorted(set.intersection(*[set(v) for v in seeds.values()]))
    return {w: float(np.mean([s_w(v[w]) for v in seeds.values()])) for w in ws}


def d1_selected(city, tag=""):
    """D1 shield on the latch (X4): the sigma row chosen by A4 across sigma in {0, 0.05, 0.10}
    (lowest equalised tuning cost ratio among fitted rows). Returns (summary row, {window: row})."""
    rows = [r for r in _pick(read("D1", city, tag), f"D1 {city}", city=city)
            if r.get("fit_status") not in ("", "none", None) and r.get("tune_ratio") not in ("", None)]
    if not rows:
        raise LookupError(f"D1 {city}: no fitted sigma row")
    best = min(rows, key=lambda r: (float(r["tune_ratio"]), float(r["sigma"])))
    pw = _pick(read("D1_PW", city, tag), f"D1 {city}", city=city, sigma=float(best["sigma"]),
               arm=best["arm"])
    return best, {int(float(r["window"])): r for r in pw}


# ------------------------------------------------------------------ the bound at an arm's mean
DAYS = 7.0


def dual_curves(city, tag=""):
    p = path("DUAL", city, tag, ext=".json")
    if not os.path.exists(p):
        raise FileNotFoundError(f"cited v3 dual curves missing: {os.path.relpath(p, IO.ROOT)}")
    import json
    IO.note_input(p)
    return json.load(open(p))


def lower_cost(city, T, price=0.18, csw=0.15, setback=False, tag=""):
    """max_lam [L*(lam) - lam T / days] over every stored relaxed grid (bound_at.lower_cost on the v3
    dual curves): a valid lower bound on the mean cost of any schedule with pooled clipped mean <= T."""
    cv = dual_curves(city, tag)[f"{city}|{price}|{csw}|{setback}"]
    best = -np.inf
    for k, pts in cv.items():
        if k.startswith("rel"):
            best = max(best, max(L - lam * T / DAYS for lam, L in pts))
    if not np.isfinite(best):
        raise ValueError(f"{city}: no relaxed dual curve")
    return best


def B_a(city, rows, tag=""):
    """(B_a %, T_a): RULING §2.3 B_a = 1 - L*(T_a) / mean_w J_THERM(delta_w^a),w, so s_a <= B_a exactly."""
    rows = list(rows)
    Ta = float(np.mean([float(r["T_arm"]) for r in rows]))
    Jeq = float(np.mean([float(r["J_eq"]) for r in rows]))
    return 100.0 * (1.0 - lower_cost(city, Ta, tag=tag) / Jeq), Ta
