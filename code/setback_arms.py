#!/usr/bin/env python3
"""Causal occupancy-setback arms (round 3, lever 1).

The occupancy timetable (away 08:00-14:00 Sunday-Thursday, setback.occupancy)
is known in advance, as a programmable thermostat's schedule is, so a causal
controller may use it. Arms:

  TUNED-SB  a programmable two-threshold thermostat: occupied switch points
            (on, off); while away, cooling only above the away ceiling, tied to
            AWAY_MAX (on at AWAY_MAX - 0.2, off 0.8 K below; ruling Sec. 2.1);
            occupied thresholds resume L steps before the occupants return
            (pre-return lead). (on, off, L) by Rule A4 with an ITERATED tuner whose
            family includes "no setback" (nesting TUNED; F14).
  MANUAL    THERM's thresholds while occupied, off at 08:00, on at 14:00, no lead
            (fixed; the household habit, SPEC_building_energy F-4).
  THERM-SB  THERM's thresholds while occupied, away ceiling tied to AWAY_MAX, no
            lead (fixed).
  MPC-SB    the receding-horizon controller of mpc_lambda with the occupancy
            bands in its horizon and the mean term on occupied steps only;
            lam fitted by Rule A4, terminal rollout = the fitted TUNED-SB rule,
            tail schedule indexed j + 96 (R5-7).
  T_max_away is reported for every arm; the vacation windows 177/205/233 are
  flagged and re-pooled as fully occupied (s_pooled_eq_vac_occupied, no compute).

Comparator: THERM (no occupancy input, holds 22.5-23.5 all day), equalised per
held-out window to the arm's clipped OCCUPIED mean (Rule C, occupied steps of
the timetable). Saving s = 1 - sum J_arm / sum J_THERM(delta_w).

Usage: python3 setback_arms.py rule            -> results/T28v3_setback_rule.csv (+_perwindow)
       python3 setback_arms.py mpc <city> <h>  -> results/T28v3_setback_mpc_<city>.csv (names: v3_names)
"""
from __future__ import annotations
import sys, csv, json, time
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
if __name__ == "__main__" and "--cth" in sys.argv:        # F21: --cth X == RBRL_CTH=X; must be set
    _i = sys.argv.index("--cth")                             # before headroom binds C_TH at import
    __import__("os").environ["RBRL_CTH"] = str(float(sys.argv[_i + 1])); del sys.argv[_i:_i + 2]
import config as CFG
import headroom as H
import setback as S
import final_tables as F
import r3_dp as D
import t1_v2 as T1V2
import rbrl_io as IO
import v3_names as V

K = F.MEAN_KEY
R = "/home/claude/rbrl/results"
LO, HI = H.BAND_LO, H.BAND_HI
AWAY_ON, AWAY_OFF = CFG.AWAY_ON, CFG.AWAY_OFF    # tied to AWAY_MAX (ruling Sec. 2.1)
PRICE = CFG.PRICE
T0 = CFG.T0                # C_th: F.C_TH at call time (F21; RBRL_CTH / --cth)


def steps_to_occ(occ):
    """for each step, number of steps until the next occupied step (0 if occupied)."""
    n = len(occ); out = np.zeros(n, int); nxt = 10 ** 6
    for k in range(n - 1, -1, -1):
        nxt = 0 if occ[k] else nxt + 1
        out[k] = nxt
    return out


def sb_policy(on_, off_, L, occ_ext, away_on=None):
    """away_on: the empty-house ceiling (default AWAY_ON, tied to AWAY_MAX; inf = off while away,
    MANUAL); cooling resumes above it and stops 0.8 K below it. L = NO_SB: no setback."""
    d = steps_to_occ(occ_ext)
    a_on = AWAY_ON if away_on is None else away_on
    a_off = a_on - 0.8
    def pol(T, prev, k):
        if d[k] <= L:                                  # occupied, or within the lead
            return 1 if T >= on_ else (0 if T <= off_ else prev)
        return 1 if T >= a_on else (0 if T <= a_off else prev)
    return pol


def ctx(city, w):
    N, occ, lo, hi = F._ctx(city, w, True)
    hi = np.where(occ, hi, CFG.AWAY_MAX)
    return N, occ, lo, hi, H.price_flat(N, PRICE)


ENV_MAX = CFG.AWAY_MAX     # empty-house safety limit


def run_rule(city, w, on_, off_, L, away_on=None):
    N, occ, lo, hi, price = ctx(city, w)
    hi = np.where(occ, hi, ENV_MAX)
    occ_ext = S.occupancy(N + 200)
    return S.sim(sb_policy(on_, off_, L, occ_ext, away_on), city, F.FACES, F.C_TH, price, lo, hi, occ,
                 168, w, T0, c_sw=F.C_SW)


def therm_sb(city, w, delta):
    """THERM(delta) scored on the timetable's occupied steps."""
    N, occ, lo, hi, price = ctx(city, w)
    return S.sim(S.hyst_abs(H.THERM_SET + 0.5 + delta, H.THERM_SET - 0.5 + delta), city, F.FACES, F.C_TH, price, lo, hi, occ,
                 168, w, T0, c_sw=F.C_SW)


def equalise_sb(city, w, target, step=0.002):
    """Rule C (shared helper F.equalise, RULING §13): THERM scored on the occupied steps."""
    return F.equalise(city, w, PRICE, target, step=step, setback=True)


def evaluate_sb(city, runs):
    pw = []
    for w in F.EVAL_W:
        a = runs[w]; th0 = therm_sb(city, w, 0.0)
        e = equalise_sb(city, w, a[K])
        pw.append(dict(window=w, J_arm=a["J"], J_eq=e["J"], J_therm0=th0["J"], delta_w=e["delta"],
                       eq_resid=e["resid"], eq_clipped=e["clipped"], T_arm=a[K], T_therm0=th0[K],
                       fs_therm0=th0["f_s"],
                       n_crossings=int(e["n_crossings"]), J_eq_max=float(e["J_eq_max"]),
                       fs_arm=a["f_s"], fs_eq=e["f_s"], E_arm=a["E"], E_eq=e["E"],
                       deg_h_over=a["deg_h_over"], deg_h_under=a["deg_h_under"],
                       deg_h_cmd_under=a.get("deg_h_cmd_under", float("nan")),
                       deg_h_ff_under=a.get("deg_h_ff_under", float("nan")),
                       T_max_away=a.get("T_max_away", float("nan")),
                       T_end=a["T_end"], fallback_steps=int(a.get("fallback_steps", 0)),
                       s_w=100.0 * (1 - a["J"] / e["J"])))
    s = dict(n_eval=len(pw), fit_windows="TUNE_W",
             s_pooled_eq=F.pooled_saving([r["J_arm"] for r in pw], [r["J_eq"] for r in pw]),
             s_raw=F.pooled_saving([r["J_arm"] for r in pw], [r["J_therm0"] for r in pw]),
             dT_pooled=float(np.mean([r["T_arm"] - r["T_therm0"] for r in pw])),
             start_sav_eq=F.pooled_saving([r["fs_arm"] for r in pw], [r["fs_eq"] for r in pw]),
             energy_sav_eq=F.pooled_saving([r["E_arm"] for r in pw], [r["E_eq"] for r in pw]),
             deg_h_over=float(sum(r["deg_h_over"] for r in pw)),
             deg_h_under=float(sum(r["deg_h_under"] for r in pw)),
             deg_h_cmd_under=float(sum(r["deg_h_cmd_under"] for r in pw)),
             deg_h_ff_under=float(sum(r["deg_h_ff_under"] for r in pw)),
             T_max_away=float(np.nanmax([r["T_max_away"] for r in pw])),
             T_end_mean=float(np.mean([r["T_end"] for r in pw])),
             fallback_steps=int(sum(r["fallback_steps"] for r in pw)),
             n_eq_clipped=int(sum(bool(r["eq_clipped"]) for r in pw)))
    if s["n_eq_clipped"]:
        print(f"!! {city}: {s['n_eq_clipped']} held-out window(s) outside the THERM(delta) bracket: "
              f"comparator clipped (eq_clipped)", flush=True)
    return s, pw


NO_SB = 10 ** 6            # lead that keeps the occupied thresholds all day: "no setback" (nesting)
VAC_W = (177, 205, 233)    # held-out windows in the school summer vacation (SPEC_building_energy F-4)


def _rows_sb_batch(city, windows, cands):
    """per-candidate lists of per-window sim dicts of setback rules (on, off, L, away_on), one
    vectorised sim_hyst_batch per window (setback variant: lead_mask, away thresholds AWAY_ON /
    -0.8; equal to run_rule, test 12 setback); None where condition 1 fails on some window."""
    on = np.array([c[0] for c in cands], float); off = np.array([c[1] for c in cands], float)
    L = np.array([c[2] for c in cands]); a_on = np.array([c[3] for c in cands], float)
    out = [[] for _ in cands]
    for w in windows:
        N, occ, lo, hi, price = ctx(city, w)
        mask = F.lead_mask(S.occupancy(N + 200), L, N)
        r = F.sim_hyst_batch(city, w, PRICE, on, off, occ=occ, lo=lo, hi=hi, active=mask,
                             on_away=a_on, off_away=a_on - 0.8)
        ok = F.admissible(r, w)
        for i in range(len(cands)):
            if out[i] is not None:
                out[i] = out[i] + [{k: (v[i] if np.ndim(v) else v) for k, v in r.items()}] if ok[i] else None
    return out


def fit_rule(city, windows=None, tuned=None, max_rounds=20):
    """TUNED-SB by Rule A4 (F.select_rows; setback comparator THERM scored on the timetable's
    occupied steps), ITERATED (F14): a joint coarse grid of (on, off, lead) plus the "no setback"
    candidates (lead NO_SB: the occupied thresholds all day, among them TUNED's own pair, so the
    family nests TUNED), then rounds of [lead (0..24 steps and NO_SB) at fixed (on, off)] and
    [0.01 K refinement of (on, off) at fixed lead] until a full round leaves the incumbent
    unchanged. The away thresholds are tied to AWAY_MAX (on at AWAY_MAX - 0.2, off 0.8 K below;
    ruling Sec. 2.1), not fitted. Every candidate list puts the incumbent FIRST (ties keep it).
    tuned: TUNED's (on, off) (default F.tune_rule on the same windows). Returns (Fit or None,
    fit_status); Fit.info["n_rounds"]."""
    windows = list(F.TUNE_W if windows is None else windows)
    a0 = AWAY_ON
    if tuned is None:
        t = F.tune_rule(city, PRICE, windows)
        tuned = (t[1], t[2]) if t is not None else (H.THERM_SET + 0.5, H.THERM_SET - 0.5)
    rows = {}

    def select(cands):
        new = [c for c in dict.fromkeys(cands) if c not in rows]
        if new:
            rows.update(zip(new, _rows_sb_batch(city, windows, new)))
        cands = list(dict.fromkeys(cands))
        return F.select_rows(cands, [rows[c] for c in cands], city, PRICE, windows, setback=True)

    pairs = [(round(on_, 2), round(off_, 2)) for on_ in np.arange(LO + 1.30, HI - 0.0499, 0.05)
             for off_ in np.arange(LO, HI - 1.199, 0.05) if on_ - off_ >= 0.4 - 1e-9]
    tp = (round(float(tuned[0]), 2), round(float(tuned[1]), 2))
    c1 = [(tp[0], tp[1], NO_SB, a0)] + [(o, f, L, a0) for o, f in pairs for L in list(range(0, 25, 2)) + [NO_SB]]
    best = select(c1)
    if best is None:
        return None, "none"
    for n_round in range(1, max_rounds + 1):
        inc = best[1]
        on_, off_, L, a = inc
        best = select([inc] + [(on_, off_, l, a) for l in list(range(0, 25)) + [NO_SB]])
        on_, off_, L, a = best[1]
        best = select([best[1]] + [(round(x, 2), round(y, 2), L, a)
                                   for x in np.arange(on_ - 0.05, on_ + 0.0501, 0.01)
                                   for y in np.arange(off_ - 0.05, off_ + 0.0501, 0.01)
                                   if x - y >= 0.4 - 1e-9 and x <= HI + 1e-9 and y >= LO - 1e-9])
        if best[1] == inc:
            break
    else:
        raise RuntimeError(f"TUNED-SB {city}: iterated tuner did not converge in {max_rounds} rounds")
    best.info["n_rounds"] = n_round
    best.info["tuned_pair"] = tp
    return best, best.fit_status


def fixed_arms():
    """the setback arms with no fitted parameter (fit_status "fixed"):
    MANUAL    THERM's thresholds while occupied; switched OFF at departure (08:00) and ON at the
              return (14:00), no lead, no away ceiling (the household's manual habit; F-4 (a));
    THERM-SB  a programmable thermostat at THERM's thresholds with the away thresholds tied to
              AWAY_MAX (on at AWAY_MAX - 0.2), no lead."""
    on0, off0 = H.THERM_SET + 0.5, H.THERM_SET - 0.5
    return {"MANUAL": (on0, off0, 0, float("inf")), "THERM-SB": (on0, off0, 0, AWAY_ON)}


def vacation_repool(pw, alt):
    """F-4 (b), no compute: the held-out windows VAC_W (summer vacation) re-pooled as fully
    occupied, i.e. the per-window setback rows replaced on those windows by the arm's
    all-occupied counterpart `alt` ({window: row with J_arm, J_eq}). Returns the pooled saving."""
    J, Jq = [], []
    for r in pw:
        w = int(float(r["window"]))
        src = alt[w] if w in VAC_W else r
        J.append(float(src["J_arm"])); Jq.append(float(src["J_eq"]))
    return F.pooled_saving(J, Jq)


def _alt_rows(key, city, **kw):
    """all-occupied per-window rows ({window: row}) of the matching non-setback arm, read from its
    v3 file; None (stated) when the file is not there yet."""
    import os
    stem = V.V3[key].format(c=city)
    if not os.path.exists(f"{IO.R}/{stem}{IO.tag()}.csv"):
        print(f"vacation re-pool: {stem} not found; column left empty", flush=True)
        return None
    out = {}
    for r in IO.read_csv(stem):
        if r.get("city", city) == city and all(str(r.get(k)) == str(v) for k, v in kw.items()):
            out[int(float(r["window"]))] = r
    return out if all(w in out for w in VAC_W) else None


def main_rule():
    summ, perw, params = [], [], {}
    for city in F.CITIES:
        t0 = time.time()
        best, status = fit_rule(city)
        arms = {}
        if best is None:
            print(f"{city:7s} TUNED-SB: no admissible parameter (fit_status none)", flush=True)
        else:
            on_, off_, L, a = best[1]
            params[city] = dict(on=float(on_), off=float(off_), lead_steps=int(L), away_on=float(a),
                                setback=L != NO_SB, fit_status=status, n_rounds=best.info["n_rounds"])
            arms["TUNED-SB"] = (best[1], status, T1V2.tune_cols(best))
        for name, p in fixed_arms().items():
            arms[name] = (p, "fixed", {})
        tuned_alt = _alt_rows("T1_PW", city, arm="TUNED", tariff="inforce")
        # MANUAL / THERM-SB all-occupied = THERM itself (its own comparator: saving 0 on those windows)
        for name, (p, st, tc) in arms.items():
            runs = {w: run_rule(city, w, *p) for w in F.EVAL_W}
            s, pw = evaluate_sb(city, runs)
            alt = tuned_alt if name == "TUNED-SB" else {w: dict(J_arm=r["J_therm0"], J_eq=r["J_therm0"])
                                                        for w, r in ((int(r["window"]), r) for r in pw)}
            s["s_pooled_eq_vac_occupied"] = vacation_repool(pw, alt) if alt else ""
            prm = dict(on=float(p[0]), off=float(p[1]), lead_steps=int(p[2]), away_on=float(p[3]))
            summ.append(dict(city=city, arm=name, params=json.dumps(prm), fit_status=st, **tc, **s))
            perw += [dict(city=city, arm=name, fit_status=st, vacation=int(r["window"]) in VAC_W, **r) for r in pw]
            print(f"{city:7s} {name:8s} {prm} {st} s_eq={s['s_pooled_eq']:+.2f}% s_raw={s['s_raw']:+.2f}% "
                  f"vac-occ={s['s_pooled_eq_vac_occupied']} E={s['energy_sav_eq']:+.1f}% "
                  f"starts={s['start_sav_eq']:+.1f}% T_max_away={s['T_max_away']:.2f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    T1V2.write(V.name("SB_RULE"), summ); T1V2.write(V.name("SB_RULE_PW"), perw)
    IO.write_json(V.AUX["SB_PARAMS"], params, inputs=T1V2.EPW_INPUTS)


def main_mpc(city, horizons):
    import mpc_lambda as M
    prm = IO.read_json(V.AUX["SB_PARAMS"])[city]      # sha lands in this run's provenance
    M.SETBACK[0] = (prm["on"], prm["off"], prm["lead_steps"], prm.get("away_on", AWAY_ON))
    th = {w: therm_sb(city, w, 0.0) for w in F.WINDOWS}
    log = lambda m: print(m, flush=True)
    summ, perw = [], []
    for hh in horizons:
        t0 = time.time()
        lam, _, _, status = M.fit_lambda(city, hh, th, 2401, log, with_status=True)
        if lam is None:
            log(f"{city} MPC-SB {hh}h: no admissible lam (fit_status none)"); continue
        res = M.mpc_batch(city, list(F.EVAL_W), [lam], hh, 2401)
        runs = {w: res[i][0] for i, w in enumerate(F.EVAL_W)}
        s, pw = evaluate_sb(city, runs)
        alt = _alt_rows("MPC_PW", city, horizon_h=float(hh), forecast="perfect")
        s["s_pooled_eq_vac_occupied"] = vacation_repool(pw, alt) if alt else ""
        summ.append(dict(city=city, arm="MPC-SB", horizon_h=hh, lam=lam, fit_status=status, **s))
        perw += [dict(city=city, arm="MPC-SB", horizon_h=hh, lam=lam, fit_status=status,
                      vacation=int(r["window"]) in VAC_W, **r) for r in pw]
        log(f"{city} MPC-SB H={hh}h lam={lam:.4f} s_eq={s['s_pooled_eq']:+.2f}% s_raw={s['s_raw']:+.2f}% "
            f"E={s['energy_sav_eq']:+.1f}% starts={s['start_sav_eq']:+.1f}% under={s['deg_h_under']:.3f} "
            f"({time.time()-t0:.0f}s)")
        T1V2.write(V.name("SB_MPC", city), summ); T1V2.write(V.name("SB_MPC_PW", city), perw)


if __name__ == "__main__":
    H.check_scenario_tag()
    H.require_headline_dt("setback_arms (lead grid in 15-min steps)")
    if sys.argv[1] == "rule":
        main_rule()
    elif sys.argv[1] == "mpc":
        main_mpc(sys.argv[2], [float(x) for x in sys.argv[3].split(",")])
