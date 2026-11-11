#!/usr/bin/env python3
"""Monotone cap scan for Taif, to settle the unreproducible 2.9% figure.

Two reviewers independently swept the cap and found that 2.9% does not occur in
the family at any cap. This script scans the cap on a fine grid under the
protocol's own feasibility rule and reports every comfort-feasible outcome, so
the manuscript can quote a figure that exists.

It also separates over- from under-temperature degree-hours, because the
bisection in final_tables.dp_isocomfort is NON-MONOTONE in the cap: its
feasibility predicate raises the cap on any violation, including an
under-temperature excursion that no cooling-only plant can correct, so it can
converge on a phase accident rather than on the comfort target.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, csv
sys.path.insert(0, _ROOT + "")
import numpy as np
import headroom as H
import setback as S
import final_tables as F

CITY = "taif"
PRICE = 0.18
LO, HI = 22.0, 24.0
EPS_HOT, EPS_COLD = 0.20, 0.40


def split_deg_h(city, w, on_at, off_at):
    """Re-run one window and split the excursion by direction."""
    N, occ, lo, hi = F._ctx(city, w, False)
    price = H.price_flat(N, PRICE)
    lam = H.lam_of(F.FACES, city)
    t_out, irr, _ = H.series(city, 168, w)
    decay = float(np.exp(-S.DT * 3600.0 * lam / (F.C_TH * 1e3)))
    T, prev = F.T0, 0
    over = under = 0.0
    for k in range(N):
        u = 1 if (T >= on_at or (prev == 1 and T > off_at)) else 0
        T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - H.Q_HVAC * u) / lam
        T = T_inf + (T - T_inf) * decay
        over += max(0.0, T - HI) * S.DT
        under += max(0.0, LO - T) * S.DT
        prev = u
    return over, under


if __name__ == "__main__":
    th = {w: F.therm_run(CITY, w, PRICE) for w in F.EVAL_W}
    Jb = np.array([th[w]["J"] for w in F.EVAL_W])
    tgt = float(np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W]))
    th_over = th_under = 0.0
    for w in F.EVAL_W:
        o, u = split_deg_h(CITY, w, 23.5, 22.5)
        th_over += o; th_under += u
    print(f"Taif THERM: J={Jb.mean():.4f}  T_occ={tgt:.4f}  "
          f"deg-h over={th_over:.4f} under={th_under:.4f}\n")
    print(f"{'cap':>6} {'on_at':>6} {'J':>8} {'f_s':>6} {'T_occ':>8} "
          f"{'dT':>8} {'over':>7} {'under':>7} {'sav%':>8}")
    rows = []
    for cap in np.arange(HI, LO + 0.55, -0.01):
        on_at = float(cap) - EPS_HOT
        rs = [F.rule_run(CITY, w, PRICE, on_at, LO + EPS_COLD)
              for w in F.EVAL_W]
        J = np.array([r["J"] for r in rs])
        Tm = float(np.mean([r["T_mean_occ"] for r in rs]))
        over = under = 0.0
        for w in F.EVAL_W:
            o, u = split_deg_h(CITY, w, on_at, LO + EPS_COLD)
            over += o; under += u
        sav = float(np.mean(100.0 * (Jb - J) / Jb))
        feas_over = over <= 1e-9
        rows.append(dict(cap=round(float(cap), 2), on_at=round(on_at, 2),
                         J=round(float(J.mean()), 4),
                         f_s=round(float(np.mean([r["f_s"] for r in rs])), 3),
                         T_occ=round(Tm, 4), dT=round(Tm - tgt, 4),
                         deg_h_over=round(over, 5), deg_h_under=round(under, 5),
                         sav=round(sav, 2)))
        r = rows[-1]
        flag = ""
        if feas_over and abs(r["dT"]) <= 0.03: flag = "  <== MATCHED"
        elif feas_over: flag = "  feasible"
        print(f"{r['cap']:6.2f} {r['on_at']:6.2f} {r['J']:8.4f} {r['f_s']:6.2f} "
              f"{r['T_occ']:8.4f} {r['dT']:+8.4f} {r['deg_h_over']:7.4f} "
              f"{r['deg_h_under']:7.4f} {r['sav']:+8.2f}{flag}")
    with open(_ROOT + "/results/taif_cap_scan.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    ok = [r for r in rows if r["deg_h_over"] <= 1e-9 and abs(r["dT"]) <= 0.03]
    print("\n--- comfort-feasible AND matched within 0.03 K ---")
    if ok:
        for r in ok:
            print(f"  cap {r['cap']:.2f}: saving {r['sav']:+.2f}%  dT {r['dT']:+.4f}")
    else:
        print("  NONE. No cap delivers a matched Taif figure.")
        near = min((r for r in rows if r["deg_h_over"] <= 1e-9),
                   key=lambda r: abs(r["dT"]))
        print(f"  closest feasible: cap {near['cap']:.2f}, "
              f"dT {near['dT']:+.4f} K, saving {near['sav']:+.2f}%")
    print("-> results/taif_cap_scan.csv")
