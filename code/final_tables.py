#!/usr/bin/env python3
"""Every table the revised manuscript needs, at the corrected configuration.

Configuration (all changes from the published version are deliberate):
  occupied band   22-24 C   (was 22-26; 24 C is the occupied ceiling)
  control step    15 min    (was 1 h; the hourly step cannot hold a 1 K deadband)
  C_th            4800 kJ/K (ISO 13786, 96 m2 participating surface at 50 kJ/m2K)
  integration     exact matrix exponential on the sensible node
  Lambda(n)       11.90n + Lambda_inf(city), affine in exposed faces
  tariff          0.18 SAR/kWh in force; 0.21 from Jan 2027; 0.05 historical
  c_sw            0.15 SAR/start

THERM is a 1 K deadband thermostat at a 23 C setpoint (on at 23.5, off at 22.5).
This is simultaneously the manuscript's definition (on at T_max-0.5, off at
T_min+0.5) evaluated on the corrected band, AND a representative hardware
deadband for the remote-controller split units in the Saudi residential stock.
The optimiser's advantage is that it may use the whole 2 K comfort band where
THERM uses only 1 K of it.

Protocol (addresses the in-sample criticism):
  cooling season 1 May - 31 Oct, 168-h windows every 14 days.
  ODD-indexed windows tune the rule; EVEN-indexed windows evaluate it.
  Dispersion is reported as mean +/- sd over the held-out windows.

Outputs results/T1..T6.csv and prints each table.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, os, csv, argparse
sys.path.insert(0, _ROOT + "")
import numpy as np
import headroom as H
import setback as S

CITIES = ("riyadh", "jeddah", "taif")
OCC_LO, OCC_HI = 22.0, 24.0
C_TH = 4800.0
FACES = 1
T0 = 23.0
TARIFFS = {"historical": 0.05, "inforce": 0.18, "y2027": 0.21}
# Must be a module attribute read at CALL time. setback.sim's signature binds
# its c_sw default when the module is imported, so mutating headroom.C_SW after
# import silently has no effect -- that defect produced an earlier version of
# this table in which every c_sw row was identical.
C_SW = 0.15

# cooling season windows: 1 May = day 120, 31 Oct = day 303
WINDOWS = list(range(121, 297, 14))          # 13 windows of 168 h
TUNE_W = WINDOWS[1::2]                        # odd index -> tuning
EVAL_W = WINDOWS[0::2]                        # even index -> held out


def _ctx(city, start_day, setback=False):
    _, _, N = H.series(city, 168, start_day)
    occ = S.occupancy(N) if setback else np.ones(N, bool)
    lo, hi = S.bands(occ, OCC_LO, OCC_HI, 18.0, 30.0)
    return N, occ, lo, hi


def therm_run(city, start_day, price_v, setback=False):
    N, occ, lo, hi = _ctx(city, start_day, setback)
    price = H.price_flat(N, price_v)
    # THERM always sees the occupied band: it has no occupancy input
    _, occ_all, lo_n, hi_n = _ctx(city, start_day, False)
    return S.sim(S.therm(lo_n, hi_n), city, FACES, C_TH, price,
                 lo_n, hi_n, occ_all, 168, start_day, T0, c_sw=C_SW)


def rule_run(city, start_day, price_v, on_at, off_at):
    N, occ, lo, hi = _ctx(city, start_day, False)
    price = H.price_flat(N, price_v)
    return S.sim(S.hyst_abs(on_at, off_at), city, FACES, C_TH, price,
                 lo, hi, occ, 168, start_day, T0, c_sw=C_SW)


def tune_rule(city, price_v, windows, target_fn, tol=0.03, step=0.05):
    """Pick one (on, off) pair that is cheapest ON AVERAGE over the tuning
    windows, admissible only if feasible and comfort-matched in every one."""
    best = None
    for on_ in np.arange(OCC_LO + 0.3, OCC_HI + 0.001, step):
        for off_ in np.arange(OCC_LO, on_ - 0.09, step):
            Js = []
            ok = True
            for w in windows:
                r = rule_run(city, w, price_v, on_, off_)
                if r["deg_h_occ"] > 1e-9 or abs(r["T_mean_occ"] - target_fn(w)) > tol:
                    ok = False; break
                Js.append(r["J"])
            if not ok:
                continue
            m = float(np.mean(Js))
            if best is None or m < best[0]:
                best = (m, on_, off_)
    return best


def dp_run(city, start_day, price_v, setback=False, cap=None, n_grid=1601):
    N, occ, lo, hi = _ctx(city, start_day, setback)
    price = H.price_flat(N, price_v)
    if cap is not None:
        hi = np.minimum(hi, np.where(occ, cap, hi))
    return S.dp(city, FACES, C_TH, price, lo, hi, occ, 168, start_day,
                T0, c_sw=C_SW, n_grid=n_grid)


def dp_isocomfort(city, start_day, price_v, target, setback=False,
                  tol=0.015, iters=22, n_grid=1601):
    a, b = OCC_LO + 0.15, OCC_HI
    best = None
    for _ in range(iters):
        m = 0.5 * (a + b)
        r = dp_run(city, start_day, price_v, setback, cap=m, n_grid=n_grid)
        if r is None or r["deg_h_occ"] > 1e-9:
            a = m; continue
        best = (r, m)
        if abs(r["T_mean_occ"] - target) <= tol:
            return best
        if r["T_mean_occ"] > target:
            b = m
        else:
            a = m
    return best


def pct(base, x):
    return 100.0 * (base - x) / base if base else float("nan")


def dump(name, rows):
    os.makedirs(_ROOT + "/results", exist_ok=True)
    p = f"{_ROOT}/results/{name}.csv"
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    print(f"-> results/{name}.csv")
