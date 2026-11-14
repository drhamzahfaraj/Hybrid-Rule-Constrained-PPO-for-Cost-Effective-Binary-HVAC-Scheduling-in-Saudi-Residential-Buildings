#!/usr/bin/env python3
"""J1 sensitivity rows (RULING_round4 §2.2 "Sensitivity, supplement only"; §21.4) -> T1v3_sens.

Three variants, in-force tariff, the three cities, scored exactly as T1 (t1_v2.evaluate, Rule C):
  hw_0.1K          TUNED selected by A4 on a 0.1 K hardware grid (tune_rule step 0.1, no 0.01 K
                   refinement; THERM is a candidate, as in the headline family)
  per_window_0.03  TUNED and guard selected with the OLD per-window comfort criterion: on EVERY
                   tuning window the clipped mean within 0.03 K of THERM's (fallback 0.10 K on
                   every window), condition 1 per window, the A4 objective. The per-window status
                   is F.pooled_status applied window by window (no tolerance is restated here).
  self_score       THERM scored as an arm against its own Rule C comparator (min-J crossing,
                   ruling §13): the comparator can only be cheaper, so s <= 0; printed for every
                   city (§21.4).
Usage: python3 t1_sens.py [city,...]
"""
from __future__ import annotations
import sys, json, time
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import config as CFG
import final_tables as F
import t1_v2 as T1V2
import v3_names as V

K = F.MEAN_KEY
PRICE = CFG.PRICE
_RANK = {"pooled_0.03": 0, "pooled_0.10": 1}


def select_per_window(city, pv, cands, rows, windows=None):
    """per-window criterion: candidate status = the WORST of F.pooled_status(T_w - T_THERM,w) over
    the windows (None if any window fails both tolerances); among the best status, the lowest A4
    objective (ties: lowest index). Returns (index, status, objective) or (None, "none", nan)."""
    windows = list(F.TUNE_W if windows is None else windows)
    i0 = int(np.flatnonzero(F.DELTAS == 0.0)[0])
    tgt = [F.therm_curve(city, w, pv)[0][i0] for w in windows]
    ctx = F._EqCtx(city, pv, windows, 1.0, False)
    best = (None, "none", np.nan, (9, np.inf))
    for i, rr in enumerate(rows):
        if rr is None or not all(F.admissible(r, w) for r, w in zip(rr, windows)):
            continue
        st = [F.pooled_status(r[K] - t) for r, t in zip(rr, tgt)]
        if any(s is None for s in st):
            continue
        status = max(st, key=lambda s: _RANK[s])
        num, den = F._objective_parts([r["J"] for r in rr], [r[K] for r in rr], ctx)
        score = (_RANK[status], num / den)
        if score < best[3]:
            best = (i, status, num / den, score)
    return best[:3]


def tuned_per_window(city, pv, windows=None):
    on_g = np.arange(F.OCC_LO + 0.3, F.OCC_HI + 0.001, 0.05)
    cands = [(round(a, 2), round(b, 2)) for a in on_g for b in np.arange(F.OCC_LO, a - 0.09, 0.05)]
    cands.append((CFG.THERM_SET + 0.5, CFG.THERM_SET - 0.5))
    rows = dict(zip(cands, F._rows_rule_batch(city, pv, list(F.TUNE_W if windows is None else windows), cands)))
    i, st, obj = select_per_window(city, pv, cands, [rows[c] for c in cands], windows)
    for _ in range(50):                                   # 0.01 K refinement until stable
        if i is None:
            break
        c0 = cands[i]
        new = [(round(x, 2), round(y, 2)) for x in np.arange(c0[0] - 0.05, c0[0] + 0.0501, 0.01)
               for y in np.arange(c0[1] - 0.05, c0[1] + 0.0501, 0.01)
               if x - y >= 0.1 - 1e-9 and x <= F.OCC_HI + 1e-9 and y >= F.OCC_LO - 1e-9]
        new = [c for c in new if c not in rows]
        if new:
            rows.update(zip(new, F._rows_rule_batch(city, pv, list(F.TUNE_W if windows is None else windows), new)))
            cands += new
        i2, st, obj = select_per_window(city, pv, cands, [rows[c] for c in cands], windows)
        if i2 is not None and cands[i2] == c0:
            break
        i = i2
    return (None, st, obj) if i is None else (cands[i], st, obj)


def guard_per_window(city, pv, windows=None):
    caps = T1V2.guard_caps()
    pairs = [(c - T1V2.GUARD_HOT, T1V2.GUARD_OFF) for c in caps]
    rows = F._rows_rule_batch(city, pv, list(F.TUNE_W if windows is None else windows), pairs)
    i, st, obj = select_per_window(city, pv, pairs, rows, windows)
    return (None, st, obj) if i is None else (caps[i], st, obj)


def main(cities=F.CITIES):
    summ, perw = [], []
    for city in cities:
        t0 = time.time()
        th = {w: F.therm_run(city, w, PRICE) for w in F.WINDOWS}
        arms = []
        hw = F.tune_rule(city, PRICE, step=0.1, refine=False)
        if hw is not None:
            arms.append(("TUNED", "hw_0.1K", dict(on=hw[1], off=hw[2]), hw.fit_status, hw[0]))
        p, st, obj = tuned_per_window(city, PRICE)
        if p is not None:
            arms.append(("TUNED", "per_window_0.03", dict(on=p[0], off=p[1]), st, obj))
        c, st, obj = guard_per_window(city, PRICE)
        if c is not None:
            arms.append(("guard", "per_window_0.03", dict(cap=c, on=round(c - T1V2.GUARD_HOT, 3),
                                                          off=T1V2.GUARD_OFF), st, obj))
        for arm, variant, prm, st, obj in arms:
            runs = {w: F.rule_run(city, w, PRICE, prm["on"], prm["off"]) for w in F.EVAL_W}
            s, pw = T1V2.evaluate(city, PRICE, runs, th)
            summ.append(dict(city=city, tariff="inforce", arm=arm, variant=variant, params=json.dumps(prm),
                             fit_status=st, tune_obj=obj, **s))
            perw += [dict(city=city, tariff="inforce", arm=arm, variant=variant, fit_status=st, **r) for r in pw]
            print(f"{city:7s} {arm:5s} {variant:16s} {prm} {st} s_eq={s['s_pooled_eq']:+.2f}% "
                  f"dT={s['dT_pooled']:+.4f}", flush=True)
        s, pw = T1V2.evaluate(city, PRICE, {w: th[w] for w in F.EVAL_W}, th)
        summ.append(dict(city=city, tariff="inforce", arm="THERM", variant="self_score",
                         params=json.dumps(dict(on=CFG.THERM_SET + 0.5, off=CFG.THERM_SET - 0.5)),
                         fit_status="fixed", **s))
        perw += [dict(city=city, tariff="inforce", arm="THERM", variant="self_score", fit_status="fixed", **r)
                 for r in pw]
        print(f"{city:7s} THERM self-score (min-J Rule C) s_eq={s['s_pooled_eq']:+.3f}% "
              f"({time.time() - t0:.0f}s)", flush=True)
    T1V2.write(V.name("T1_SENS"), summ)
    T1V2.write(V.name("T1_SENS") + "_perwindow", perw)


if __name__ == "__main__":
    main(sys.argv[1].split(",") if len(sys.argv) > 1 else F.CITIES)
