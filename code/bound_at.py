#!/usr/bin/env python3
"""B_a: the provable bound at each arm's own pooled clipped mean (RULING_round4 Sec. 2.3, F11).

L_raw(lam) is stored per relaxed grid (T17v3_<city>_dualcurves.json, pooled over the held-out
windows, and per window); for any target T, max_lam [L*(lam) - lam T / days] lower-bounds the mean
cost (SAR/day) of every schedule whose pooled held-out clipped mean is <= T. For arm a:

    B_a = 1 - L*(T~_a) / mean_w J_THERM(delta_w^a),w          (s_a <= B_a exactly)

and on every window the shifted dual certificate
    J_a,w >= J^bd_w - lam_w (T~_a,w - T~_THERM,w) / 7          (margin >= 0).

In-rules arms (MPC in rules, guard-ruled RBRL, E2, D1 on the latch) are also checked against the
RULED relaxed bound (T17v3_ruled_<city>), whose RULE_ON/RULE_OFF cover every in-rules arm's
R1/R2 (bound_v2 ruled): ruled B_a >= s_a. Setback arms use the setback bound (T17v3sb_<city>).

Terminal (O4, ruling §21.3): the bound and the CLV use the uniform terminal value (energy at rated
COP + c_sw / DELTA_CYCLE per K, r3_dp). Every arm is rescored onto the same terminal from its stored
per-window J_arm and T_end (r3_dp.uniform_J) and its comparator recomputed at the arm's mean by
Rule C on THERM(delta) with the same terminal (r3_dp.comparator_uniform), so s_a <= B_a compares
like with like. s_a_file (the arm file's own saving, simulator terminal) is printed beside it.

Writes T17v3_Ba.csv (one row per arm and city) and prints the minimum certificate margin.
Missing arm files are listed, not silently skipped. Usage: python3 bound_at.py [city,...]
"""
import sys, os
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import config as CFG
import final_tables as F
import r3_dp as D
import rbrl_io as IO
import v3_names as V

DAYS = 7.0
GROUP = ("arm", "tariff", "horizon_h", "forecast", "seed", "sigma", "lam_scale", "c_sw", "price")
# (per-window stem key, kind: "free" | "ruled" (also free) | "sb")
ARM_FILES = (("T1_PW", "free"), ("MPC_PW", "free"), ("MPC_PERS_PW", "free"), ("MPC_RULED_PW", "ruled"), ("MPC_GUARD_PW", "ruled"),
             ("RBRL_PW", "ruled"), ("D1_PW", "ruled"), ("E2_PW", "ruled"), ("SB_RULE_PW", "sb"),
             ("SB_MPC_PW", "sb"))


def _curves(stem, sb=False, ruled=False):
    p = f"{IO.R}/{stem}_dualcurves.json"
    if not os.path.exists(p):
        return None
    IO.note_input(p)
    import json
    cv = json.load(open(p))
    city = stem.split("_")[-1]
    key = f"{city}|{CFG.PRICE}|{CFG.C_SW}|{sb}" + ("|ruled" if ruled else "")
    return cv.get(key), cv.get(key + "|perwindow")


def lower_cost_curves(curves, T, days=DAYS):
    """L*(T) per day: max over every relaxed grid and stored lam of L_raw(lam) - lam T / days."""
    return max(L - lam * T / days for tag, pts in curves.items() if tag.startswith("rel") for lam, L in pts)


def lower_cost(city, T, setback=False, price=CFG.PRICE, csw=CFG.C_SW, name=None):
    """backward-compatible entry: L*(T) from the city's v3 dual curves."""
    stem = name or V.name("CLV_SB" if setback else "CLV", city)
    import json
    cv = json.load(open(f"{IO.R}/{stem}_dualcurves.json"))
    return lower_cost_curves(cv[f"{city}|{price}|{csw}|{setback}"], T)


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def bound_for_arm(rows, curves, pw_bound=None):
    """rows: the arm's 7 held-out per-window rows (T_arm, J_arm, J_eq, window). Returns a dict with
    s_a, B_a, T_a, ok, and the certificate minimum when per-window bound rows are given
    ({window: row with bound_J_w, lam_w, therm_T})."""
    Ta = float(np.mean([_f(r["T_arm"]) for r in rows]))
    Ja = [_f(r["J_arm"]) for r in rows]; Jq = [_f(r["J_eq"]) for r in rows]
    s = F.pooled_saving(Ja, Jq)
    B = 100.0 * (1.0 - lower_cost_curves(curves, Ta) / float(np.mean(Jq)))
    out = dict(T_a=Ta, s_a=s, B_a=B, s_le_B=bool(s <= B + 1e-9))
    if pw_bound:
        m = [D.certificate_margin(_f(r["J_arm"]), _f(r["T_arm"]), _f(pw_bound[int(_f(r["window"]))]["bound_J_w"]),
                                  _f(pw_bound[int(_f(r["window"]))]["lam_w"]),
                                  _f(pw_bound[int(_f(r["window"]))]["therm_T"])) for r in rows]
        out.update(cert_min_margin=float(min(m)), cert_ok=bool(min(m) >= -1e-9))
    return out


def uniform_rows(city, rr, setback=False):
    """the arm's per-window rows on the uniform O4 terminal (J_arm, J_eq rescored); None when a
    row has no T_end (cannot be rescored: listed, not guessed)."""
    out = []
    for r in rr:
        if r.get("T_end") in (None, ""):
            return None
        w = int(_f(r["window"]))
        e = D.comparator_uniform(city, w, CFG.PRICE, _f(r["T_arm"]), setback, CFG.C_SW)
        out.append(dict(window=w, T_arm=_f(r["T_arm"]), J_arm=D.uniform_J(_f(r["J_arm"]), _f(r["T_end"]), CFG.C_SW),
                        J_eq=e["J"]))
    return out


def _groups(rows):
    g = {}
    for r in rows:
        if "J_eq" not in r or "T_arm" not in r or r.get("fit_status") in ("none", ""):
            continue
        if r.get("tariff", "inforce") not in ("inforce", ""):
            continue
        if not np.isnan(_f(r.get("price"))) and abs(_f(r["price"]) - CFG.PRICE) > 1e-9:
            continue
        if not np.isnan(_f(r.get("c_sw"))) and abs(_f(r["c_sw"]) - CFG.C_SW) > 1e-9:
            continue
        key = tuple((k, r[k]) for k in GROUP if k in r and r[k] != "")
        g.setdefault(key, []).append(r)
    return {k: v for k, v in g.items() if sorted(int(_f(r["window"])) for r in v) == sorted(F.EVAL_W)}


def main(cities=F.CITIES):
    out, missing = [], []
    for city in cities:
        free = _curves(V.name("CLV", city)); sbc = _curves(V.name("CLV_SB", city), sb=True)
        rul = _curves(V.name("BOUND_RULED", city), ruled=True)
        pwb = lambda stem: ({int(_f(r["window"])): r for r in IO.read_csv(f"{stem}_perwindow", apply_tag=False)}
                            if os.path.exists(f"{IO.R}/{stem}_perwindow.csv") else None)
        pw_free, pw_sb, pw_rul = pwb(V.name("CLV", city)), pwb(V.name("CLV_SB", city)), pwb(V.name("BOUND_RULED", city))
        if free is None:
            missing.append(V.name("DUAL", city)); continue
        Bstar = None
        if os.path.exists(f"{IO.R}/{V.name('CLV', city)}.csv"):
            Bstar = _f(IO.read_csv(V.name("CLV", city), apply_tag=False)[0]["bound_reported"])
        # CLV (oracle) rows, mapped to the arm schema
        if pw_free and all("clv_J" in r for r in pw_free.values()):
            rows = [dict(window=w, J_arm=r["clv_J"], J_eq=r["clv_J_eq"], T_arm=r["clv_T"]) for w, r in pw_free.items()]
            o = bound_for_arm(rows, free[0], pw_free)
            out.append(dict(city=city, arm="CLV", source=V.name("CLV", city), kind="free", fit_status="oracle",
                            B_star=Bstar, print_B_a=Bstar is None or abs(o["B_a"] - Bstar) >= 0.1, **o))  # adm-ok: print rule (pt)
        for key, kind in ARM_FILES:
            stem = V.name(key, city)
            if not os.path.exists(f"{IO.R}/{stem}.csv"):
                missing.append(stem); continue
            rows = [r for r in IO.read_csv(stem, apply_tag=False) if r.get("city", city) == city]
            for gk, rr0 in _groups(rows).items():
                label = " ".join(f"{k}={v}" for k, v in gk) or key
                fs = rr0[0].get("fit_status", "")
                rr = uniform_rows(city, rr0, setback=kind == "sb")
                if rr is None:
                    missing.append(f"{stem} [{label}]: no T_end column (cannot rescore to O4)"); continue
                s_file = F.pooled_saving([_f(r["J_arm"]) for r in rr0], [_f(r["J_eq"]) for r in rr0])
                if kind == "sb":
                    if sbc is None:
                        missing.append(V.name("CLV_SB", city)); continue
                    o = bound_for_arm(rr, sbc[0], pw_sb)
                    out.append(dict(city=city, arm=label, source=stem, kind="sb", fit_status=fs, s_a_file=s_file,
                                    **o)); continue
                o = bound_for_arm(rr, free[0], pw_free)
                row = dict(city=city, arm=label, source=stem, kind="free", fit_status=fs, B_star=Bstar, s_a_file=s_file,
                           print_B_a=Bstar is None or abs(o["B_a"] - Bstar) >= 0.1, **o)  # adm-ok: print rule (pt)
                if kind == "ruled" and rul is not None:
                    orl = bound_for_arm(rr, rul[0], pw_rul)
                    row.update(B_a_ruled=orl["B_a"], s_le_B_ruled=orl["s_le_B"],
                               cert_min_margin_ruled=orl.get("cert_min_margin"))
                out.append(row)
    for m in sorted(set(missing)):
        print(f"missing (not evaluated): {m}", flush=True)
    if not out:
        raise SystemExit("bound_at: no arm could be evaluated")
    bad = [r for r in out if not r["s_le_B"] or r.get("cert_ok") is False or r.get("s_le_B_ruled") is False]
    mins = [r["cert_min_margin"] for r in out if r.get("cert_min_margin") is not None]
    for r in out:
        print(f"{r['city']:7s} {r['arm'][:48]:48s} s={r['s_a']:6.2f} B_a={r['B_a']:6.2f}"
              + (f" B_ruled={r['B_a_ruled']:6.2f}" if r.get("B_a_ruled") is not None else "")
              + (f" cert_min={r['cert_min_margin']:+.2e}" if r.get("cert_min_margin") is not None else ""), flush=True)
    print(f"minimum certificate margin over all arms and windows: {min(mins) if mins else float('nan'):+.3e} SAR/day; "
          f"violations: {len(bad)}", flush=True)
    IO.write_csv(V.name("BA"), out)
    if bad:
        raise SystemExit(f"bound_at: {len(bad)} invariant violation(s)")


if __name__ == "__main__":
    main(sys.argv[1].split(",") if len(sys.argv) > 1 else F.CITIES)
