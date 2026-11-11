#!/usr/bin/env python3
"""Clairvoyant optimum under a MEAN occupied-temperature constraint.

Why this exists
---------------
The clairvoyant arm previously enforced the comfort match with a POINTWISE
occupied ceiling: the zone was forbidden to exceed a constant cap at any
occupied step. That is strictly stronger than requiring a matched MEAN, so the
capped dynamic programme optimises over a smaller feasible set than the
controllers it was supposed to bound -- and four arms duly exceeded it.

The constraint that belongs here is

    minimise  J(u)   subject to   T_k in [T_min, T_max] for all occupied k
                                  (1/N) sum_k T_k = T*,

i.e. the band is enforced pointwise (it is the real comfort constraint) while
the match is enforced only in the mean (it is a device for fair comparison).

Method
------
Lagrangian relaxation of the mean constraint alone:

    L(u, lam) = J(u) + lam * ( (1/N) sum_k T_k  -  T* ).

For fixed lam this is the ordinary DP with an extra additive stage cost
(lam/N) * T_{k+1}; nothing else changes. Two properties make it the right tool:

1.  For ANY lam and any u feasible for the constrained problem,
        J(u) = L(u, lam) >= min_u' L(u', lam) =: L*(lam).
    So L*(lam) is a valid LOWER BOUND on the constrained optimal cost for every
    lam, and max_lam L*(lam) is the best such bound. This holds whether or not
    the dual gap closes, so the reported bound is rigorous even though the
    action space is binary and the problem non-convex.

2.  The mean attained by the unconstrained minimiser is non-increasing in lam
    (a larger lam prices temperature more heavily), so lam can be bisected to
    drive the attained mean onto T*. Where that succeeds the schedule is
    feasible and its true cost is an ACHIEVABLE value, bracketing the optimum
    from above.

The script reports both: the best lower bound on cost (hence an upper bound on
the saving, which is what the manuscript needs) and the best feasible schedule
found (an achievable saving). Their gap is the duality gap, reported rather
than assumed away.
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

LO, HI = 22.0, 24.0
C_TH, T0 = 4800.0, 23.0
N_GRID = 1601
PRICE = 0.18


def dp_lagrangian(city, start_day, price_v, lam, setback=False,
                  faces=1, c_th=C_TH, n_grid=N_GRID):
    """DP with the mean-temperature multiplier folded into the stage cost.

    Returns (J_true, T_mean_occ, L_value, f_s, deg_h) where J_true excludes the
    multiplier term and L_value is min_u [ J(u) + lam * mean(T) ].
    """
    q, cp = H.Q_HVAC, H.COP_RATED
    lam_env = H.lam_of(faces, city)
    t_out, irr, N = H.series(city, 168, start_day)
    decay = float(np.exp(-S.DT * 3600.0 * lam_env / (c_th * 1e3)))
    p_el = q / cp / 1000.0
    price = H.price_flat(N, price_v)
    occ = S.occupancy(N) if setback else np.ones(N, bool)
    lo_b, hi_b = S.bands(occ, LO, HI, 18.0, 30.0)
    n_occ = int(occ.sum())

    Tg = np.linspace(S.G_LO, S.G_HI, n_grid)
    INF = np.inf
    # terminal: price the thermal state exactly as setback.dp does
    V = np.repeat((price[-1] * (Tg - T0) * c_th * 1e3 / 3.6e6 / cp)[:, None],
                  2, axis=1)
    pol = np.zeros((N, n_grid, 2), np.int8)
    for k in range(N - 1, -1, -1):
        g = H.SHGC * H.A_GL * irr[k]
        run = price[k] * p_el * S.DT
        swc = H.C_SW + price[k] * H.E_START
        cand = np.full((n_grid, 2, 2), INF)
        for u in (0, 1):
            T_inf = t_out[k] + (g - q * u) / lam_env
            Tp = T_inf + (Tg - T_inf) * decay
            ok = (Tp >= lo_b[k] - 1e-9) & (Tp <= hi_b[k] + 1e-9)
            Vn = np.interp(np.clip(Tp, S.G_LO, S.G_HI), Tg, V[:, u])
            # the multiplier term: lam * (1/n_occ) * T, charged on occupied steps
            extra = (lam / n_occ) * Tp if occ[k] else 0.0
            nxt = np.where(ok, run * u + extra + Vn, INF)
            for up in (0, 1):
                sc = swc if (u == 1 and up == 0) else 0.0
                cand[:, up, u] = np.where(np.isfinite(nxt), sc + nxt, INF)
        Vn2 = np.full((n_grid, 2), INF)
        for up in (0, 1):
            bu = np.argmin(np.nan_to_num(cand[:, up, :], nan=INF, posinf=1e300),
                           axis=1)
            pol[k, :, up] = bu.astype(np.int8)
            Vn2[:, up] = cand[np.arange(n_grid), up, bu]
        V = Vn2

    i0 = int(np.argmin(np.abs(Tg - T0)))
    if not np.isfinite(V[i0, 0]):
        return None
    L_value = float(V[i0, 0])

    # replay the policy on the true plant to recover J and the attained mean
    def pol_fn(T, prev, k):
        return int(pol[k, int(np.argmin(np.abs(Tg - T))), prev])

    r = S.sim(pol_fn, city, faces, c_th, price, lo_b, hi_b, occ,
              168, start_day, T0, c_sw=F.C_SW)
    # V is the window TOTAL while sim reports per-day; work in per-day units so
    # the Lagrangian value is directly comparable with J.
    days = N * S.DT / 24.0
    return dict(J=r["J"], T_mean_occ=r["T_mean_occ"], f_s=r["f_s"],
                deg_h_occ=r["deg_h_occ"], L=L_value / days, E=r["E"],
                days=days)


def solve_city(city, setback=False, price_v=PRICE, n_lam=18, lam_max=24.0):
    """Maximise the Lagrangian dual to get a rigorous bound.

    The attained mean is a STEP function of lam: the binary action set makes the
    inner minimiser jump, so lam-bisection generally cannot land on the target
    and no exactly mean-matched schedule need exist in this family. That does
    not weaken the bound. For every lam and every schedule u that IS mean
    matched, J(u) = L(u,lam) >= L*(lam), so

        max_lam L*(lam)   lower-bounds the cost of any mean-matched schedule,

    and therefore upper-bounds the saving any such schedule can achieve. The
    dual is concave in lam, so a coarse grid plus a local refinement finds the
    maximum reliably.
    """
    th = {w: F.therm_run(city, w, price_v) for w in F.EVAL_W}
    Jb = np.array([th[w]["J"] for w in F.EVAL_W])
    tgt = float(np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W]))

    def dual(lam):
        rs = [dp_lagrangian(city, w, price_v, lam, setback) for w in F.EVAL_W]
        if any(r is None for r in rs):
            return None
        days = rs[0]["days"]
        Lb = float(np.mean([r["L"] for r in rs])) - (lam / days) * tgt
        return dict(L=Lb, Tm=float(np.mean([r["T_mean_occ"] for r in rs])),
                    J=float(np.mean([r["J"] for r in rs])),
                    f_s=float(np.mean([r["f_s"] for r in rs])))

    grid = list(np.linspace(0.0, lam_max, n_lam))
    best = None
    for lam in grid:
        d = dual(float(lam))
        if d is None:
            continue
        if best is None or d["L"] > best["L"]:
            best = dict(d, lam=float(lam))
    # local refinement around the maximiser (the dual is concave)
    step = lam_max / (n_lam - 1)
    lo_l, hi_l = max(0.0, best["lam"] - step), best["lam"] + step
    for _ in range(10):
        a, b = lo_l + (hi_l - lo_l) / 3.0, hi_l - (hi_l - lo_l) / 3.0
        da, db = dual(a), dual(b)
        if da is None or db is None:
            break
        for d, lam in ((da, a), (db, b)):
            if d["L"] > best["L"]:
                best = dict(d, lam=lam)
        if da["L"] < db["L"]:
            lo_l = a
        else:
            hi_l = b
    return best, float(Jb.mean()), tgt


if __name__ == "__main__":
    rows = []
    print("Rigorous upper bound on the saving achievable at a matched mean "
          "occupied temperature.\n")
    for city in ("riyadh", "jeddah", "taif"):
        for setback, name in ((False, "OPT"), (True, "OPT+sb")):
            best, Jb, tgt = solve_city(city, setback)
            if best is None:
                print(f"{city:8s} {name:7s}  dual unbounded"); continue
            bound_sav = 100.0 * (Jb - best["L"]) / Jb
            rows.append(dict(city=city, arm=name, lam=round(best["lam"], 4),
                             therm_J=round(Jb, 4), bound_J=round(best["L"], 4),
                             bound_sav=round(bound_sav, 2),
                             lagrangian_mean=round(best["Tm"], 4),
                             target_mean=round(tgt, 4)))
            r = rows[-1]
            print(f"{city:8s} {name:7s} lam*={r['lam']:7.3f}  "
                  f"THERM J={Jb:.4f}  cost >= {r['bound_J']:.4f}  "
                  f"=> saving <= {r['bound_sav']:.2f}%", flush=True)
    with open(_ROOT + "/results/T11_meanbound.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print("\n--- every reported arm must lie below its own bound ---")
    arms = {"riyadh": [("TUNED", 9.25), ("guard hyst", 5.82), ("RBRL", 5.66),
                       ("MPC 24h", 11.95), ("capped DP", 10.93)],
            "jeddah": [("TUNED", 9.26), ("guard hyst", 5.80), ("RBRL", 5.80),
                       ("MPC 24h", 11.28), ("capped DP", 10.52)],
            "taif": [("TUNED", 4.56), ("guard hyst", 7.62), ("RBRL", 7.62),
                     ("MPC 24h", 15.70), ("capped DP", 4.67)]}
    bad = 0
    for r in rows:
        if r["arm"] != "OPT":
            continue
        for n, v in arms[r["city"]]:
            if v > r["bound_sav"]:
                print(f"  *** {r['city']} {n} {v:.2f}% EXCEEDS bound "
                      f"{r['bound_sav']:.2f}% ***"); bad += 1
    print(f"  {bad} violation(s)" if bad else
          "  none: the bound holds for every arm in every city.")
    print("-> results/T11_meanbound.csv")
