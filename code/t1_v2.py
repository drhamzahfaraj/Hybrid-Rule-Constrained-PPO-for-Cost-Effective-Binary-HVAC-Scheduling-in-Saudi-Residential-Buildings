#!/usr/bin/env python3
"""Round-4 protocol for the causal rule arms (RULING_round4 Sec. 2).

Rule A4 every arm's comfort parameter is fitted on the 6 tuning windows only, by
        final_tables.fit_param / tune_rule (zero deg_h_over and zero deg_h_cmd_under in
        every tuning window; pooled |clipped mean - THERM's| <= 0.03 K, one fallback 0.10 K;
        fit_status column in every arm row).
Rule B  matching uses the clipped occupied mean max(T, T_min).
Rule C  on each held-out window the comparator THERM(delta_w) is shifted so its
        clipped mean equals the arm's; saving s = 1 - sum J_arm / sum J_THERM(delta_w).

Usage (append --cth X for the C_th sweep; needs RBRL_TAG):
        python3 t1_v2.py t1        -> results/T1v3_heldout/_perwindow, T26v3_guard_fit, tuned_params_v2.json
        python3 t1_v2.py t7        -> results/T7v3_deadband/_perwindow
        python3 t1_v2.py csw       -> results/T5v3_switchcost_tuned        (names: v3_names.py)
"""
from __future__ import annotations
import sys, os, json, csv, time
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
if __name__ == "__main__" and "--cth" in sys.argv:        # F21: --cth X == RBRL_CTH=X; must be set
    _i = sys.argv.index("--cth")                             # before headroom binds C_TH at import
    __import__("os").environ["RBRL_CTH"] = str(float(sys.argv[_i + 1])); del sys.argv[_i:_i + 2]
import config as CFG
import final_tables as F
import rbrl_io as IO
import v3_names as V

R = "/home/claude/rbrl/results"
K = F.MEAN_KEY
import headroom as _HB
GUARD_HOT, GUARD_OFF = CFG.EPS_HOT, CFG.RULE_OFF       # R1 margin below the cap; R2 (config)


PRICE = CFG.PRICE
CSW_GRID = CFG.C_SW_GRID       # J20 / ruling 12.5: {0, 0.025, 0.05, 0.10, 0.114, 0.15, 0.20, 0.30, 0.60}


def tune_cols(fit):
    """tuning-side columns of a Fit: A4 objective (equalised tuning cost ratio) and saving, pooled
    dT, max |dT_w|, comparator clipping and candidate counts."""
    i = fit.info
    return dict(tune_obj=i.get("tune_obj"), tune_saving=i.get("tune_saving"),
                tune_eq_clipped=i.get("tune_eq_clipped"), tune_dT=i.get("tune_dT"),
                tune_max_abs_dT_w=i.get("tune_max_abs_dT_w"), tune_n_cand=i.get("n_cand"),
                tune_n_adm_0p03=i.get("n_adm_0p03"), tune_n_adm_0p10=i.get("n_adm_0p10"))


def therm_d(city, w, pv, db):
    return F.therm_shift_run(city, w, pv, 0.0, db)


def fit_tuned(city, pv, th=None, db=1.0):
    """TUNED by Rule A4 (final_tables.tune_rule). th is not needed (the target is THERM's pooled
    clipped mean on TUNE_W, from the comparator family); kept for the call signature."""
    return F.tune_rule(city, pv, F.TUNE_W, db=db)


def guard_caps():
    return [round(c, 2) for c in np.arange(_HB.BAND_HI - 0.50, _HB.BAND_HI + 0.0001, 0.01)]


def fit_guard(city, pv, th=None, db=1.0):
    """guard hysteresis (on at cap - GUARD_HOT, off at GUARD_OFF): ceiling by Rule A4 over
    guard_caps() (ascending). Returns (Fit or None, fit_status)."""
    run = lambda cap, w: F.rule_run(city, w, pv, cap - GUARD_HOT, GUARD_OFF)
    best = F.fit_param(guard_caps(), run, F.TUNE_W, city=city, price_v=pv, db=db)
    return best, (best.fit_status if best else "none")


def evaluate(city, pv, arm_runs, th, db=1.0):
    """arm_runs: {w: sim dict} on EVAL_W. Returns (summary, per-window rows)."""
    pw = []
    for w in F.EVAL_W:
        a = arm_runs[w]
        e = F.equalise(city, w, pv, a[K], db=db)
        pw.append(dict(window=w, J_arm=a["J"], J_therm0=th[w]["J"], J_eq=float(e["J"]),
                       delta_w=e["delta"], bracket_gap=e["bracket_gap"], eq_resid=e["resid"],
                       eq_clipped=e["clipped"], n_crossings=int(e["n_crossings"]),
                       J_eq_max=float(e["J_eq_max"]),
                       T_arm=a[K], T_therm0=th[w][K], dT_w=a[K] - th[w][K], fs_therm0=th[w]["f_s"],
                       fs_arm=a["f_s"], fs_eq=float(e["f_s"]), E_arm=a["E"], E_eq=float(e["E"]),
                       deg_h_over=a["deg_h_over"], deg_h_under=a["deg_h_under"],
                       deg_h_cmd_under=a.get("deg_h_cmd_under", float("nan")),
                       deg_h_ff_under=a.get("deg_h_ff_under", float("nan")),
                       T_end=a["T_end"], fallback_steps=int(a.get("fallback_steps", 0)),
                       s_w=100.0 * (1 - a["J"] / float(e["J"]))))
    J = np.array([r["J_arm"] for r in pw]); Jq = np.array([r["J_eq"] for r in pw])
    J0 = np.array([r["J_therm0"] for r in pw])
    s = dict(n_eval=len(pw), fit_windows="TUNE_W",
             s_pooled_eq=F.pooled_saving(J, Jq), s_raw=F.pooled_saving(J, J0),
             # Rule C crossing-choice range (RULING §13.4): min-J crossing = s_pooled_eq
             s_eq_minJ=F.pooled_saving(J, Jq),
             s_eq_maxJ=F.pooled_saving(J, [r["J_eq_max"] for r in pw]),
             n_eq_multi=int(sum(r["n_crossings"] > 1 for r in pw)),
             dT_pooled=float(np.mean([r["dT_w"] for r in pw])),
             max_abs_dT_w=float(max(abs(r["dT_w"]) for r in pw)),
             start_sav_eq=F.pooled_saving([r["fs_arm"] for r in pw], [r["fs_eq"] for r in pw]),
             energy_sav_eq=F.pooled_saving([r["E_arm"] for r in pw], [r["E_eq"] for r in pw]),
             fs_therm0_mean=float(np.mean([r["fs_therm0"] for r in pw])),
             J_arm_mean=float(J.mean()), J_eq_mean=float(Jq.mean()), J_therm0_mean=float(J0.mean()),
             deg_h_over=float(sum(r["deg_h_over"] for r in pw)),
             deg_h_under=float(sum(r["deg_h_under"] for r in pw)),
             deg_h_cmd_under=float(sum(r["deg_h_cmd_under"] for r in pw)),
             deg_h_ff_under=float(sum(r["deg_h_ff_under"] for r in pw)),
             T_end_mean=float(np.mean([r["T_end"] for r in pw])),
             fallback_steps=int(sum(r["fallback_steps"] for r in pw)),
             n_eq_clipped=int(sum(bool(r["eq_clipped"]) for r in pw)),
             max_bracket_gap=float(max(r["bracket_gap"] for r in pw)))
    # (no mean +/- sd of per-window savings: RULING_round4 §2.3)
    if s["n_eq_clipped"]:
        print(f"!! {city}: {s['n_eq_clipped']} held-out window(s) outside the THERM(delta) bracket "
              f"[-0.4, 0.4] K: comparator clipped (eq_clipped in the per-window rows)", flush=True)
    return s, pw


EPW_INPUTS = [f"{IO.ROOT}/{c}.epw" for c in F.CITIES]


def write(name, rows, inputs=()):
    """All CSV output goes through rbrl_io (atomic, locked, RBRL_TAG-aware, key union,
    provenance columns + .meta.json; empty tables and fit_status == 'none' rows refused)."""
    return IO.write_csv(name, rows, inputs=list(EPW_INPUTS) + list(inputs))


def run_t1():
    summ, perw, guard_rows, params = [], [], [], {}
    for tname in ("inforce", "y2027", "historical"):
        pv = F.TARIFFS[tname]
        for city in F.CITIES:
            t0 = time.time()
            th = {w: F.therm_run(city, w, pv) for w in F.WINDOWS}
            bt = fit_tuned(city, pv, th)
            arms = {}
            if bt:
                arms["TUNED"] = ({w: F.rule_run(city, w, pv, bt[1], bt[2]) for w in F.EVAL_W},
                                 dict(on=round(float(bt[1]), 3), off=round(float(bt[2]), 3),
                                      fit_status=bt.fit_status), bt)
                params[f"{city}|{tname}|TUNED"] = arms["TUNED"][1]
            else:
                summ.append(dict(tariff=tname, price=pv, city=city, arm="TUNED", fit_status="none"))
            if tname == "inforce":
                bg, gstat = fit_guard(city, pv, th)
                if bg:
                    cap = bg[1]
                    arms["guard"] = ({w: F.rule_run(city, w, pv, cap - GUARD_HOT, GUARD_OFF)
                                      for w in F.EVAL_W},
                                     dict(cap=cap, on=round(cap - GUARD_HOT, 3), off=GUARD_OFF,
                                          fit_status=gstat), bg)
                    params[f"{city}|{tname}|guard"] = arms["guard"][1]
                else:
                    summ.append(dict(tariff=tname, price=pv, city=city, arm="guard", fit_status="none"))
            for arm, (runs, prm, fit) in arms.items():
                s, pw = evaluate(city, pv, runs, th)
                row = dict(tariff=tname, price=pv, city=city, arm=arm, params=json.dumps(prm),
                           fit_status=fit.fit_status, **tune_cols(fit), **s)
                summ.append(row)
                for r in pw:
                    perw.append(dict(tariff=tname, city=city, arm=arm, fit_status=fit.fit_status, **r))
                print(f"{tname:10s} {city:7s} {arm:6s} {prm}  s_eq={s['s_pooled_eq']:+.2f}%  "
                      f"s_raw={s['s_raw']:+.2f}%  dT={s['dT_pooled']:+.4f}  "
                      f"max|dT_w|={s['max_abs_dT_w']:.3f}  starts={s['start_sav_eq']:+.1f}%  "
                      f"E={s['energy_sav_eq']:+.1f}%  ({time.time()-t0:.0f}s)", flush=True)
    write(V.name("T1"), summ)
    write(V.name("T1_PW"), perw)
    if any(r["arm"] == "guard" and r.get("fit_status") != "none" for r in summ):
        write(V.AUX["GUARD_FIT"], [r for r in summ if r["arm"] == "guard"])
    IO.write_json(V.AUX["TUNED_PARAMS"], params, inputs=EPW_INPUTS)


def run_t7():
    rows, perw = [], []
    for city in F.CITIES:
        for db in (0.50, 0.75, 1.00, 1.25):
            th = {w: therm_d(city, w, PRICE, db) for w in F.WINDOWS}
            bt = fit_tuned(city, PRICE, th, db=db)
            if not bt:
                rows.append(dict(city=city, deadband=db, on="", off="", fit_windows="TUNE_W",
                                 fit_status="none"))
                print(city, db, "no admissible rule (fit_status none)", flush=True); continue
            runs = {w: F.rule_run(city, w, PRICE, bt[1], bt[2]) for w in F.EVAL_W}
            s, pw = evaluate(city, PRICE, runs, th, db=db)
            rows.append(dict(city=city, deadband=db, on=round(float(bt[1]), 3),
                             off=round(float(bt[2]), 3), fit_status=bt.fit_status, **tune_cols(bt),
                             therm_fs=float(np.mean([th[w]["f_s"] for w in F.EVAL_W])), **s))
            for r in pw:
                perw.append(dict(city=city, deadband=db, arm="TUNED", fit_status=bt.fit_status, **r))
            # guard hysteresis, ceiling refitted against THIS comparator (Rule A4)
            bg, gstat = fit_guard(city, PRICE, th, db=db)
            rows[-1].update(guard_fit_status=gstat)
            if bg:
                grun = lambda cap, w: F.rule_run(city, w, PRICE, cap - GUARD_HOT, GUARD_OFF)
                gs, gpw = evaluate(city, PRICE, {w: grun(bg[1], w) for w in F.EVAL_W}, th, db=db)
                rows[-1].update(guard_cap=bg[1], guard_s_eq=gs["s_pooled_eq"], guard_s_raw=gs["s_raw"])
                for r in gpw:
                    perw.append(dict(city=city, deadband=db, arm="guard", fit_status=gstat, **r))
            print(f"{city:7s} db={db:.2f} rule {bt[1]:.2f}/{bt[2]:.2f} {bt.fit_status} "
                  f"s_eq={s['s_pooled_eq']:+.2f}% s_raw={s['s_raw']:+.2f}%  "
                  f"guard={rows[-1].get('guard_s_eq')} ({gstat})", flush=True)
    write(V.name("T7"), rows)
    write(V.name("T7_PW"), perw)


def run_csw():
    rows = []
    c_sw0 = F.C_SW
    try:
        for c in CSW_GRID:
            F.C_SW = c                               # read at call time by rule_run
            for city in F.CITIES:
                th = {w: F.therm_run(city, w, PRICE) for w in F.WINDOWS}
                bt = fit_tuned(city, PRICE, th)
                if not bt:
                    rows.append(dict(c_sw=c, city=city, on="", off="", fit_status="none")); continue
                runs = {w: F.rule_run(city, w, PRICE, bt[1], bt[2]) for w in F.EVAL_W}
                s, _ = evaluate(city, PRICE, runs, th)
                rows.append(dict(c_sw=c, city=city, on=round(float(bt[1]), 3),
                                 off=round(float(bt[2]), 3), fit_status=bt.fit_status,
                                 **tune_cols(bt), **s))
                print(f"c_sw={c:.3f} {city:7s} rule {bt[1]:.2f}/{bt[2]:.2f} {bt.fit_status} "
                      f"s_eq={s['s_pooled_eq']:+.2f}%", flush=True)
    finally:
        F.C_SW = c_sw0                               # restored even if a fit raises (S15)
    write(V.name("T5"), rows)


if __name__ == "__main__":
    _HB.check_scenario_tag()
    {"t1": run_t1, "t7": run_t7, "csw": run_csw}[sys.argv[1]]()
