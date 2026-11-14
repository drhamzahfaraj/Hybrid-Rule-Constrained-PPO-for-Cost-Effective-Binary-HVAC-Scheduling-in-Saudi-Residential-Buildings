#!/usr/bin/env python3
"""Final MPC analysis once the 1601-point refined runs are in.

Produces, in one place, every number the manuscript's MPC propagation needs:
  * per-city, per-horizon matched savings (mean +/- sd, worst dT) at 1601
  * the 801-vs-1601 convergence statement under the IDENTICAL cap protocol
  * the paired analysis for TUNED vs MPC-24h: exact Wilcoxon, sign test,
    BCa interval, mean AND median difference, n-better-of-7 -- the
    mean/median split the triage reviewer required finding four to carry
  * the 48 h horizon row
"""
from __future__ import annotations
import sys, csv, os, glob
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np

import final_tables as F
from stats_paired import bca_ci, sign_test, DELTA_EQ
from scipy import stats


def load(prefix):
    rows = []
    for p in glob.glob(f"/home/claude/rbrl/results/{prefix}*_mpc_perwindow.csv"):
        rows += list(csv.DictReader(open(p)))
    return rows


def table(rows, tag):
    print(f"\n=== {tag} ===")
    out = {}
    for city in ("riyadh", "jeddah", "taif"):
        for hh in (6.0, 24.0, 48.0):
            got = [r for r in rows if r["city"] == city
                   and abs(float(r["horizon_h"]) - hh) < 1e-9]
            if not got:
                continue
            sav = np.array([float(r["sav"]) for r in got])
            dT = np.array([float(r["dT"]) for r in got])
            out[(city, hh)] = {int(r["w"]): float(r["J"]) for r in got}
            print(f"  {city:8s} H={hh:4.0f}h  n={len(got)}  "
                  f"sav {sav.mean():+6.2f}+/-{sav.std(ddof=1):4.2f}%  "
                  f"worst dT {dT.min():+.4f}  "
                  f"caps {min(float(r['cap']) for r in got):.2f}"
                  f"-{max(float(r['cap']) for r in got):.2f}")
    return out


if __name__ == "__main__":
    g1601 = load("T21_g1601")
    g801 = load("T21_g801")
    J16 = table(g1601, "1601-point grid, refined caps (the reported arm)")
    J8 = table(g801, "801-point grid, refined caps (convergence control)")

    print("\n=== grid convergence, identical cap protocol ===")
    for city in ("riyadh", "jeddah", "taif"):
        for hh in (6.0, 24.0):
            a, b = J8.get((city, hh)), J16.get((city, hh))
            if not a or not b:
                continue
            common = sorted(set(a) & set(b))
            d = np.array([b[w] - a[w] for w in common])
            print(f"  {city:8s} H={hh:4.0f}h  mean J shift 801->1601: "
                  f"{d.mean():+.4f} SAR/day ({100*d.mean()/np.mean([a[w] for w in common]):+.2f}%)"
                  f"  max |shift| {np.abs(d).max():.4f}")

    print("\n=== TUNED vs MPC-24h, paired on the 7 held-out windows ===")
    for city in ("riyadh", "jeddah"):
        m = J16.get((city, 24.0))
        if not m or len(m) < 7:
            print(f"  {city}: incomplete ({0 if not m else len(m)}/7)")
            continue
        W = list(F.EVAL_W)
        th = {w: F.therm_run(city, w, 0.18) for w in W}
        Jt = np.array([th[w]["J"] for w in W])
        _, on_, off_ = F.tune_rule(city, 0.18, F.TUNE_W,
                                   lambda w: F.therm_run(city, w, 0.18)["T_mean_occ"])
        Ju = np.array([F.rule_run(city, w, 0.18, on_, off_)["J"] for w in W])
        Jm = np.array([m[w] for w in W])
        s_t = 100.0 * (Jt - Ju) / Jt
        s_m = 100.0 * (Jt - Jm) / Jt
        d = s_t - s_m
        wt = stats.wilcoxon(Ju, Jm, alternative="two-sided", method="exact")
        sp, pos, nn = sign_test(Ju - Jm)
        lo, hi, pt = bca_ci(d, np.mean)
        n_mpc = int((s_m > s_t).sum())
        print(f"  {city:8s} TUNED {s_t.mean():+.2f}% (med {np.median(s_t):+.2f})"
              f"   MPC24 {s_m.mean():+.2f}% (med {np.median(s_m):+.2f})")
        print(f"           diff mean {d.mean():+.2f} / median {np.median(d):+.2f} pts"
              f"   BCa95 [{lo:+.2f},{hi:+.2f}]   Wilcoxon p={wt.pvalue:.3f}"
              f"   MPC better in {n_mpc}/7 windows")
        print(f"           per-window sav: TUNED {np.round(s_t,2)}")
        print(f"                           MPC24 {np.round(s_m,2)}")
