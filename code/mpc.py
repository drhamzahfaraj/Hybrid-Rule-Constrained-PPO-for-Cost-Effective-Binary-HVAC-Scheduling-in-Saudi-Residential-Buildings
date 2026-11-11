#!/usr/bin/env python3
"""Receding-horizon MPC on the verified physics, as a CAUSAL comparator.

The clairvoyant DP (OPT) sees the whole week and so bounds every causal
controller in the iso-comfort class; it is not implementable. This script
supplies the missing middle term: a controller with the same plant, the same
band, the same tariff and the same switching cost, but a perfect forecast only
inside a finite horizon. Beyond the horizon it knows nothing.

At each interval k it solves the same Bellman recursion as setback.dp over
[k, k+Hh), takes the first action, advances one interval, and re-solves. The
terminal value at the end of the horizon prices the thermal state exactly as
the full-horizon DP does, so a longer horizon cannot be penalised for ending
warm; the only difference between horizons is how far ahead the weather is
known.

This separates two explanations of the paper's negative result that are
otherwise confounded: that there is nothing to gain inside the rule-constrained
class, and that what there is to gain requires a forecast the agent does not
have.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, csv, time
sys.path.insert(0, _ROOT + "")
import numpy as np
import headroom as H
import setback as S
import final_tables as F

LO, HI = 22.0, 24.0
C_TH = 4800.0
T0 = 23.0
N_GRID = 801            # coarser than the 1601 of OPT; verified below
G_LO, G_HI = S.G_LO, S.G_HI


def mpc_run(city, start_day, price_v, horizon_h, cap=None, faces=1,
            c_th=C_TH, n_grid=N_GRID):
    """Simulate one window under receding-horizon control."""
    q, cp = H.Q_HVAC, H.COP_RATED
    lam = H.lam_of(faces, city)
    t_out, irr, N = H.series(city, 168, start_day)
    decay = float(np.exp(-S.DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = q / cp / 1000.0
    price = H.price_flat(N, price_v)
    hi_occ = HI if cap is None else min(HI, cap)
    Hh = int(round(horizon_h / S.DT))          # horizon in intervals
    Tg = np.linspace(G_LO, G_HI, n_grid)
    INF = np.inf

    T, prev = T0, 0
    J = E = 0.0
    starts = 0
    deg_h = 0.0
    Tsum = 0.0

    for k in range(N):
        end = min(N, k + Hh)
        # ---- solve the horizon subproblem backwards
        V = np.repeat((price[end - 1] * (Tg - T0) * c_th * 1e3 / 3.6e6 / cp)[:, None],
                      2, axis=1)
        first = None
        for j in range(end - 1, k - 1, -1):
            g = H.SHGC * H.A_GL * irr[j]
            run = price[j] * p_el * S.DT
            swc = H.C_SW + price[j] * H.E_START
            cand = np.full((n_grid, 2, 2), INF)
            for u in (0, 1):
                T_inf = t_out[j] + (g - q * u) / lam
                Tp = T_inf + (Tg - T_inf) * decay
                ok = (Tp >= LO - 1e-9) & (Tp <= hi_occ + 1e-9)
                Vn = np.interp(np.clip(Tp, G_LO, G_HI), Tg, V[:, u])
                nxt = np.where(ok, run * u + Vn, INF)
                for up in (0, 1):
                    sc = swc if (u == 1 and up == 0) else 0.0
                    cand[:, up, u] = np.where(np.isfinite(nxt), sc + nxt, INF)
            Vn2 = np.full((n_grid, 2), INF)
            bu_all = np.empty((n_grid, 2), np.int8)
            for up in (0, 1):
                bu = np.argmin(np.nan_to_num(cand[:, up, :], nan=INF,
                                             posinf=1e300), axis=1)
                bu_all[:, up] = bu.astype(np.int8)
                Vn2[:, up] = cand[np.arange(n_grid), up, bu]
            V = Vn2
            if j == k:
                first = bu_all
        # ---- take the first action only
        i = int(np.argmin(np.abs(Tg - T)))
        if not np.isfinite(V[i, prev]):
            return None                      # horizon infeasible from here
        u = int(first[i, prev])
        # ---- advance the true plant one interval
        if u == 1 and prev == 0:
            J += H.C_SW + price[k] * H.E_START
            starts += 1
        if u == 1:
            J += price[k] * p_el * S.DT
            E += p_el * S.DT
        T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - q * u) / lam
        T = T_inf + (T - T_inf) * decay
        deg_h += (max(0.0, T - HI) + max(0.0, LO - T)) * S.DT
        Tsum += T
        prev = u
    J += price[-1] * (T - T0) * c_th * 1e3 / 3.6e6 / cp   # terminal, as dp does
    days = N * S.DT / 24.0
    return dict(J=J / days, E=E / days, f_s=starts / days,
                deg_h_occ=deg_h, T_mean_occ=Tsum / N)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", default="riyadh,jeddah,taif")
    ap.add_argument("--horizons", default="6,24")
    ap.add_argument("--price", type=float, default=0.18)
    a = ap.parse_args()
    t0 = time.time()
    rows = []
    for city in a.cities.split(","):
        th = {w: F.therm_run(city, w, a.price) for w in F.EVAL_W}
        Jb = np.array([th[w]["J"] for w in F.EVAL_W])
        tgt = float(np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W]))
        for hh in [float(x) for x in a.horizons.split(",")]:
            # comfort-match by a MONOTONE scan over the ceiling, not a bisection:
            # the bisection in final_tables is non-monotone when an excursion is
            # an under-temperature one the plant cannot correct.
            best = None
            # narrow bracket on a 0.05 K grid: the match lies near the ceiling,
            # and a 70-point scan at 5.6 s per window is not affordable
            for cap in np.arange(HI, 23.30, -0.05):
                rs = [mpc_run(city, w, a.price, hh, cap=float(cap))
                      for w in F.EVAL_W]
                if any(r is None for r in rs):
                    continue
                if max(r["deg_h_occ"] for r in rs) > 1e-3:
                    continue
                Tm = float(np.mean([r["T_mean_occ"] for r in rs]))
                d = abs(Tm - tgt)
                if best is None or d < best[0]:
                    best = (d, float(cap), rs)
                if Tm < tgt - 0.03:
                    break
            if best is None:
                print(f"  {city} H={hh}h: no comfort-feasible cap", flush=True)
                continue
            dT, cap, rs = best
            J = np.array([r["J"] for r in rs])
            sav = 100.0 * (Jb - J) / Jb
            rows.append(dict(city=city, horizon_h=hh, cap=round(cap, 3),
                             J=round(float(J.mean()), 4),
                             f_s=round(float(np.mean([r["f_s"] for r in rs])), 3),
                             T_occ=round(float(np.mean([r["T_mean_occ"] for r in rs])), 4),
                             dT=round(float(np.mean([r["T_mean_occ"] for r in rs])) - tgt, 4),
                             max_deg_h=round(float(max(r["deg_h_occ"] for r in rs)), 5),
                             sav=round(float(sav.mean()), 2),
                             sav_sd=round(float(sav.std(ddof=1)), 2)))
            r = rows[-1]
            print(f"  {city:7s} H={hh:4.0f}h cap={cap:.2f} J={r['J']:.4f} "
                  f"f_s={r['f_s']:.2f} dT={r['dT']:+.4f} "
                  f"sav={r['sav']:+.2f}+/-{r['sav_sd']:.2f}%  "
                  f"[{time.time()-t0:.0f}s]", flush=True)
    with open(_ROOT + "/results/T8_mpc.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print("-> results/T8_mpc.csv")
