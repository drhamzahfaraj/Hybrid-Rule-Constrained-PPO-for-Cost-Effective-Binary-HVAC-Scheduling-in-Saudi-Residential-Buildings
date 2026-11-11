#!/usr/bin/env python3
"""Per-window comfort match: a bound and an attainable schedule, window by window.

Why per-window
--------------
`attainable.py` applies ONE multiplier across the whole evaluation set. The
aggregate mean then matches the baseline's, but individual windows do not: in
Riyadh the per-window saving at lambda = 2.0 is 18.61 +/- 15.63%, i.e. some
windows run warm and cheap while others run cold and dear. A reviewer is
entitled to say that such a schedule buys part of its saving with temperature
in the windows where it runs warm, even though the average is matched.

Every other arm in this manuscript is matched window by window, so the
clairvoyant arm must be too. For each window w independently:

  * ATTAINABLE. Scan lambda and keep only schedules whose window mean occupied
    temperature is at or below that window's baseline mean. Such a schedule is
    at least as cool as its comparator in that window, so it can claim no
    comfort credit there. Take the cheapest.

  * BOUND. Maximise the window's own dual L*_w(lambda). Because the match is now
    required within each window, J_w >= max_lambda L*_w(lambda) for every
    window-matched schedule, and averaging these per-window bounds gives a
    valid -- and tighter -- bound on the mean cost than maximising a single
    shared multiplier does.

Both quantities are then averaged over windows, and the dispersion reported is
genuine window-to-window variation of a comfort-matched arm, directly
comparable with the dispersion quoted for every other arm.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, csv
sys.path.insert(0, _ROOT + "")
import numpy as np
import final_tables as F
import dp_meanconstrained as M

# coarse grid first, then a local refinement on each side
GRID = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0]
REFINE = 6


def window(city, w, setback, price_v=M.PRICE):
    """Attainable (no-warmer) and dual bound for ONE evaluation window."""
    th = F.therm_run(city, w, price_v)
    Jb, tgt = th["J"], th["T_mean_occ"]

    cache = {}

    def ev(lam):
        lam = round(float(lam), 4)
        if lam not in cache:
            cache[lam] = M.dp_lagrangian(city, w, price_v, lam, setback)
        return cache[lam]

    pts = [(l, ev(l)) for l in GRID]
    pts = [(l, r) for l, r in pts if r is not None]
    if not pts:
        return None

    days = pts[0][1]["days"]

    def dualval(r, lam):
        return r["L"] - (lam / days) * tgt

    # --- bound: maximise the window's own dual ---
    lam_b, best_b = max(((l, dualval(r, l)) for l, r in pts),
                        key=lambda t: t[1])
    lo = max(0.0, lam_b - 0.5)
    hi = lam_b + 0.5
    for _ in range(REFINE):
        a, b = lo + (hi - lo) / 3.0, hi - (hi - lo) / 3.0
        ra, rb = ev(a), ev(b)
        if ra is None or rb is None:
            break
        va, vb = dualval(ra, a), dualval(rb, b)
        if va > best_b:
            best_b, lam_b = va, a
        if vb > best_b:
            best_b, lam_b = vb, b
        if va < vb:
            lo = a
        else:
            hi = b

    # --- attainable: cheapest schedule no warmer than this window's baseline ---
    # refine around the sign change of (T_mean - tgt) to get as close as
    # possible from the cool side
    cool = [(l, r) for l, r in pts if r["T_mean_occ"] <= tgt + 1e-9]
    warm = [(l, r) for l, r in pts if r["T_mean_occ"] > tgt + 1e-9]
    if cool and warm:
        lo_l = max(l for l, _ in warm if l < min(c for c, _ in cool)) \
            if any(l < min(c for c, _ in cool) for l, _ in warm) else 0.0
        hi_l = min(c for c, _ in cool)
        for _ in range(10):
            mid = 0.5 * (lo_l + hi_l)
            rm = ev(mid)
            if rm is None:
                break
            if rm["T_mean_occ"] <= tgt + 1e-9:
                hi_l = mid
                cool.append((mid, rm))
            else:
                lo_l = mid
    if not cool:
        return None
    lam_a, ra = min(cool, key=lambda t: t[1]["J"])

    return dict(w=w, therm_J=Jb, tgt=tgt,
                lam_att=lam_a, att_J=ra["J"], att_dT=ra["T_mean_occ"] - tgt,
                att_fs=ra["f_s"], att_degh=ra["deg_h_occ"],
                lam_bnd=lam_b, bnd_J=best_b)


if __name__ == "__main__":
    rows, summary = [], []
    for city in ("riyadh", "jeddah", "taif"):
        for setback, name in ((False, "OPT"), (True, "OPT+sb")):
            print(f"\n=== {city} {name} ===", flush=True)
            ws = []
            for w in F.EVAL_W:
                r = window(city, w, setback)
                if r is None:
                    print(f"  window {w}: infeasible"); continue
                r.update(city=city, arm=name)
                sav = 100.0 * (r["therm_J"] - r["att_J"]) / r["therm_J"]
                bsv = 100.0 * (r["therm_J"] - r["bnd_J"]) / r["therm_J"]
                r.update(att_sav=sav, bnd_sav=bsv)
                ws.append(r)
                rows.append({k: (round(v, 5) if isinstance(v, float) else v)
                             for k, v in r.items()})
                print(f"  w{w:>4}  attainable {sav:6.2f}% (dT {r['att_dT']:+.4f}, "
                      f"lam {r['lam_att']:.3f})   bound {bsv:6.2f}%", flush=True)
            if not ws:
                continue
            a = np.array([x["att_sav"] for x in ws])
            b = np.array([x["bnd_sav"] for x in ws])
            dT = np.array([x["att_dT"] for x in ws])
            Jb = float(np.mean([x["therm_J"] for x in ws]))
            Ja = float(np.mean([x["att_J"] for x in ws]))
            Jd = float(np.mean([x["bnd_J"] for x in ws]))
            summary.append(dict(city=city, arm=name,
                                therm_J=round(Jb, 4),
                                att_J=round(Ja, 4), bnd_J=round(Jd, 4),
                                att_sav=round(float(a.mean()), 2),
                                att_sd=round(float(a.std(ddof=1)), 2),
                                bnd_sav=round(float(b.mean()), 2),
                                bnd_sd=round(float(b.std(ddof=1)), 2),
                                max_dT=round(float(dT.max()), 4),
                                mean_dT=round(float(dT.mean()), 4),
                                max_degh=round(float(max(x["att_degh"]
                                                         for x in ws)), 5),
                                att_fs=round(float(np.mean(
                                    [x["att_fs"] for x in ws])), 3)))
            s = summary[-1]
            print(f"  --> attainable {s['att_sav']:.2f}+/-{s['att_sd']:.2f}%  "
                  f"(every window no warmer; worst dT {s['max_dT']:+.4f})")
            print(f"  --> bound      {s['bnd_sav']:.2f}+/-{s['bnd_sd']:.2f}%")
    with open(_ROOT + "/results/T14_perwindow.csv", "w", newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=list(rows[0]))
        w_.writeheader(); w_.writerows(rows)
    with open(_ROOT + "/results/T14_perwindow_summary.csv", "w",
              newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=list(summary[0]))
        w_.writeheader(); w_.writerows(summary)
    print("\n--- summary ---")
    for s in summary:
        print(f"  {s['city']:8s} {s['arm']:7s} attainable "
              f"{s['att_sav']:6.2f}+/-{s['att_sd']:5.2f}%   bound "
              f"{s['bnd_sav']:6.2f}+/-{s['bnd_sd']:5.2f}%   worst dT "
              f"{s['max_dT']:+.4f} K")
    print("\n-> results/T14_perwindow.csv, T14_perwindow_summary.csv")
    print("every attainable row is at or below its own window's baseline mean, "
          "so it claims no comfort credit in any window.")
