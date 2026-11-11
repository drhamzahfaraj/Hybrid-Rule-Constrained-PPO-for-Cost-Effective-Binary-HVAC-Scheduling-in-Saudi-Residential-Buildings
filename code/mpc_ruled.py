#!/usr/bin/env python3
"""The missing cell: a 24 h-horizon controller INSIDE the rule-admissible set.

Why this experiment decides a principal finding
-----------------------------------------------
The manuscript concludes that what forecloses the remaining headroom is the
agent's one-hour observation window rather than the rule layer. Its evidence is
the diagonal of a 2x2 design, and the diagonal cannot separate the two factors:

                    | no rules          | rules R1-R2
    ----------------+-------------------+------------------
    no lookahead    |  TUNED    9.3%    |  hysteresis 5.8%
    24 h lookahead  |  MPC-24  11.9%    |  ???          <-- never run
    clairvoyant     |  CLV     18.1%    |  rule-DP    6.0%   (verify_corollary)

Reading along the diagonal (hysteresis 5.8 -> MPC-24 11.9) attributes the whole
gain to lookahead. But the column comparison says otherwise: with UNLIMITED
lookahead inside the rules the clairvoyant rule-constrained DP reaches only
6.0% (J = 1.0513 against THERM's 1.1183), i.e. infinite foresight inside the
rule layer is worth +0.2 points over no foresight at all, while removing the
rules with only a day of foresight is worth +6.2.

If that is right, the binding constraint is the rule layer, not the observation
window, and the manuscript's attribution is inverted. The cell that settles it
is the missing one: a receding-horizon controller with a 24 h forecast that is
also forced to obey R1 and R2.

  * If it reaches ~12%, lookahead is the binding factor and the manuscript's
    reading survives (the rule-DP result would then be a horizon artefact).
  * If it reaches ~6%, the rule layer is the binding factor and the finding
    must be restated.

Implementation
--------------
`mpc.mpc_run` with one change: at every grid point the action set is masked by
the same guards `verify_corollary.dp_rule_constrained` applies -- forced on at
T >= cap - 0.20, forced off at T <= 22.0 + 0.40 -- both inside the horizon
subproblem and on the action actually applied. Everything else (plant, band,
tariff, switching cost, terminal pricing, grid) is identical, so the only
difference from the reported MPC arm is the rule layer.

Comfort is matched per window, on the same criterion as every other arm: the
cheapest run that is no warmer than that window's own baseline mean.
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
C_TH, T0 = 4800.0, 23.0
N_GRID = 1601    # matched to the clairvoyant DP; was 801
G_LO, G_HI = S.G_LO, S.G_HI
EPS_HOT, EPS_COLD = 0.20, 0.40          # as verify_corollary.py
CAP_LO, STEP = 22.60, 0.05


def mpc_run_ruled(city, start_day, price_v, horizon_h, cap=None, faces=1,
                  c_th=C_TH, n_grid=N_GRID, ruled=True):
    """Receding-horizon control, optionally restricted to rule-admissible actions."""
    q, cp = H.Q_HVAC, H.COP_RATED
    lam = H.lam_of(faces, city)
    t_out, irr, N = H.series(city, 168, start_day)
    decay = float(np.exp(-S.DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = q / cp / 1000.0
    price = H.price_flat(N, price_v)
    hi_occ = HI if cap is None else min(HI, cap)
    Hh = int(round(horizon_h / S.DT))
    Tg = np.linspace(G_LO, G_HI, n_grid)
    INF = np.inf

    # the rule layer, exactly as the RBRL guards define it
    allowed = np.ones((n_grid, 2), bool)
    if ruled:
        allowed[Tg >= hi_occ - EPS_HOT, 0] = False   # too hot: must be on
        allowed[Tg <= LO + EPS_COLD, 1] = False      # too cold: must be off

    T, prev = T0, 0
    J = E = 0.0
    starts = 0
    deg_h = 0.0
    Tsum = 0.0

    for k in range(N):
        end = min(N, k + Hh)
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
                ok &= allowed[:, u]                  # <-- the rule layer
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
        i = int(np.argmin(np.abs(Tg - T)))
        if not np.isfinite(V[i, prev]):
            return None
        u = int(first[i, prev])
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
    J += price[-1] * (T - T0) * c_th * 1e3 / 3.6e6 / cp
    days = N * S.DT / 24.0
    return dict(J=J / days, E=E / days, f_s=starts / days,
                deg_h_occ=deg_h, T_mean_occ=Tsum / N)


def match_window(city, w, price_v, hh, tgt, ruled):
    """Coarse 0.05 K cap scan, then a 0.01 K refinement of the admissibility
    boundary, as in mpc_perwindow: the coarse grid alone leaves windows
    over-cooled by up to ~0.05 K, which handicaps the arm by several points."""
    best = None
    for cap in np.arange(HI, CAP_LO - 1e-9, -STEP):
        r = mpc_run_ruled(city, w, price_v, hh, cap=float(cap), ruled=ruled)
        if r is None:
            continue
        if r["T_mean_occ"] > tgt + 1e-9:
            continue
        if best is None or r["J"] < best["J"]:
            best = dict(r, cap=float(cap))
        if r["T_mean_occ"] < tgt - 0.06:
            break
    if best is None:
        return None
    for cap in np.arange(best["cap"] + 0.04, best["cap"] + 0.004, -0.01):
        r = mpc_run_ruled(city, w, price_v, hh, cap=float(cap), ruled=ruled)
        if r is None or r["T_mean_occ"] > tgt + 1e-9:
            continue
        if r["J"] < best["J"]:
            best = dict(r, cap=float(cap))
    return best


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", default="riyadh")
    ap.add_argument("--horizons", default="24")
    ap.add_argument("--price", type=float, default=0.18)
    a = ap.parse_args()
    t0 = time.time()
    rows, summary = [], []
    for city in a.cities.split(","):
        th = {w: F.therm_run(city, w, a.price) for w in F.EVAL_W}
        for hh in [float(x) for x in a.horizons.split(",")]:
            for ruled in (True, False):
                tag = "rule-constrained" if ruled else "unconstrained"
                print(f"\n=== {city} H={hh:.0f}h {tag} ===", flush=True)
                got = []
                for w in F.EVAL_W:
                    tgt = th[w]["T_mean_occ"]
                    b = match_window(city, w, a.price, hh, tgt, ruled)
                    if b is None:
                        print(f"  w{w:>4}: no cap reaches the baseline mean",
                              flush=True)
                        continue
                    sav = 100.0 * (th[w]["J"] - b["J"]) / th[w]["J"]
                    got.append(dict(city=city, horizon_h=hh, ruled=ruled, w=w,
                                    cap=round(b["cap"], 3), J=round(b["J"], 4),
                                    therm_J=round(th[w]["J"], 4),
                                    dT=round(b["T_mean_occ"] - tgt, 4),
                                    f_s=round(b["f_s"], 3),
                                    sav=round(sav, 2)))
                    print(f"  w{w:>4} cap={b['cap']:.2f} J={b['J']:.4f} "
                          f"dT={b['T_mean_occ']-tgt:+.4f} sav={sav:+6.2f}%",
                          flush=True)
                if not got:
                    continue
                rows.extend(got)
                s = np.array([g["sav"] for g in got])
                summary.append(dict(city=city, horizon_h=hh, ruled=ruled,
                                    J=round(float(np.mean([g["J"] for g in got])), 4),
                                    f_s=round(float(np.mean([g["f_s"] for g in got])), 3),
                                    sav=round(float(s.mean()), 2),
                                    sav_sd=round(float(s.std(ddof=1)), 2),
                                    worst_dT=round(float(max(g["dT"] for g in got)), 4),
                                    n_win=len(got)))
                q = summary[-1]
                print(f"  --> {tag}: {q['sav']:.2f}+/-{q['sav_sd']:.2f}%  "
                      f"J={q['J']:.4f}  f_s={q['f_s']:.2f}", flush=True)
    with open(_ROOT + "/results/T16_mpc_ruled.csv", "w",
              newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=list(rows[0]))
        w_.writeheader(); w_.writerows(rows)
    with open(_ROOT + "/results/T16_mpc_ruled_summary.csv", "w",
              newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=list(summary[0]))
        w_.writeheader(); w_.writerows(summary)
    print(f"\n--- the 2x2 cell, completed ({time.time()-t0:.0f} s) ---")
    for q in summary:
        tag = "rules R1-R2" if q["ruled"] else "no rules   "
        print(f"  {q['city']:8s} H={q['horizon_h']:4.0f}h  {tag}  "
              f"{q['sav']:6.2f}+/-{q['sav_sd']:5.2f}%")
    print("\nVERDICT: if the rule-constrained figure is near the hysteresis's "
          "5.8%, the binding constraint is the RULE LAYER, not the horizon, "
          "and Section 7.2's attribution must be restated.")
    print("-> results/T16_mpc_ruled.csv, T16_mpc_ruled_summary.csv")
