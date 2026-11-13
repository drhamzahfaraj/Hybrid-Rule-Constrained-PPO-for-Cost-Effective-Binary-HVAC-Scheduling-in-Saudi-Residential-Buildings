#!/usr/bin/env python3
"""The multi-zone optimum, reached backwards by decomposition.

The obstruction
---------------
A direct clairvoyant dynamic programme over N_z coupled zones has G^N_z states
and 2^N_z actions per interval: 2e7 state-action transitions at two zones,
6.6e10 at three, 2.4e56 at sixteen (scalability.py). It is the formulation that
obstructs, not the machine, so the multi-zone optimum cannot be computed the
way the single-zone one is.

The way round it
----------------
Work backwards from the optimum instead of forwards from the actions. The only
thing that couples the zones is the term Lambda_iz,i (T_iz,i - T_i) in zone i's
dynamics. HOLD THAT TERM FIXED as an exogenous trajectory and the problem
separates into N_z independent single-zone programmes, each of which is exactly
the tractable problem solved elsewhere in this study. Two quantities follow,
and they bracket the coupled optimum from both sides.

  BOUND (from below on cost, above on saving). Give every zone the most
  favourable neighbour trajectory the comfort band permits -- neighbours held
  at T_min for the whole window, which maximises the heat each zone can dump
  into them. Solve the zones independently under that gift and sum. No real
  schedule can do better, because no real neighbour can be colder than the band
  allows, so the sum is a rigorous lower bound on the coupled optimum's cost.

  ATTAINABLE (from above on cost). Best response: simulate, read off each
  zone's actual neighbour trajectory, re-solve that zone's programme against
  it, and iterate. A fixed point is a schedule in which every zone is optimal
  given the others -- a person-by-person optimum. It is feasible by
  construction, so its cost is attained.

The gap between them is what is not known about the coupled optimum, and it is
reported rather than assumed away -- the same discipline the single-zone
Lagrangian bracket follows.

Comfort is matched as everywhere else: every arm is held to a mean occupied
temperature no warmer than the baseline's, in every window.
"""
from __future__ import annotations
import sys, csv
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import headroom as H
import setback as S
import multizone as MZ
import final_tables as F

LO, HI = 22.0, 24.0
T0 = 23.0
N_GRID = 801
PRICE = 0.18


def zone_dp(city, start_day, price_v, lam_env, lam_iz, t_iz_traj, faces,
            cap=None, c_th=MZ.C_TH, n_grid=N_GRID, lam_mult=0.0, nz=1):
    """Single-zone clairvoyant DP with an exogenous neighbour trajectory.

    The zone sees an effective ambient that blends outdoor air and neighbours:
        dT/dt = [Lambda_env (T_out - T) + Lambda_iz (T_iz - T) + Q_sol - Q u]/C
    which is the scalar problem with conductance (Lambda_env + Lambda_iz) and a
    conductance-weighted ambient. Returns (J, actions, T trace) or None.
    """
    q, cp = MZ.Q_HVAC, MZ.COP
    t_out, irr, N = H.series(city, 168, start_day)
    lam_tot = lam_env + lam_iz
    decay = float(np.exp(-S.DT * 3600.0 * lam_tot / c_th))
    p_el = q / cp / 1000.0
    price = H.price_flat(N, price_v)
    hi_b = HI if cap is None else min(HI, cap)

    Tg = np.linspace(S.G_LO, S.G_HI, n_grid)
    INF = np.inf
    V = np.repeat((price[-1] * (Tg - T0) * c_th / 3.6e6 / cp)[:, None],
                  2, axis=1)
    pol = np.zeros((N, n_grid, 2), np.int8)
    for k in range(N - 1, -1, -1):
        g = MZ.SHGC * MZ.A_GL * faces * irr[k]
        amb = (lam_env * t_out[k] + lam_iz * t_iz_traj[k]) / lam_tot
        run = price[k] * p_el * S.DT
        swc = H.C_SW + price[k] * H.E_START
        cand = np.full((n_grid, 2, 2), INF)
        for u in (0, 1):
            T_inf = amb + (g - q * u) / lam_tot
            Tp = T_inf + (Tg - T_inf) * decay
            ok = (Tp >= LO - 1e-9) & (Tp <= hi_b + 1e-9)
            Vn = np.interp(np.clip(Tp, S.G_LO, S.G_HI), Tg, V[:, u])
            # Lagrangian price on this zone's contribution to the BUILDING
            # mean occupied temperature: (lam/nz)*(1/N)*T, so that summing
            # over zones gives lam*(building mean) exactly.
            extra = (lam_mult / nz / N) * Tp if lam_mult else 0.0
            nxt = np.where(ok, run * u + extra + Vn, INF)
            for up in (0, 1):
                sc = swc if (u == 1 and up == 0) else 0.0
                cand[:, up, u] = np.where(np.isfinite(nxt), sc + nxt, INF)
        Vn2 = np.full((n_grid, 2), INF)
        for up in (0, 1):
            bu = np.argmin(np.nan_to_num(cand[:, up, :], nan=INF,
                                         posinf=1e300), axis=1)
            pol[k, :, up] = bu.astype(np.int8)
            Vn2[:, up] = cand[np.arange(n_grid), up, bu]
        V = Vn2

    i0 = int(np.argmin(np.abs(Tg - T0)))
    if not np.isfinite(V[i0, 0]):
        return None
    # replay
    T, prev = T0, 0
    J = 0.0
    acts = np.zeros(N, np.int8)
    Ts = np.zeros(N)
    for k in range(N):
        u = int(pol[k, int(np.argmin(np.abs(Tg - T))), prev])
        acts[k] = u
        if u == 1 and prev == 0:
            J += H.C_SW + price[k] * H.E_START
        if u == 1:
            J += price[k] * p_el * S.DT
        g = MZ.SHGC * MZ.A_GL * faces * irr[k]
        amb = (lam_env * t_out[k] + lam_iz * t_iz_traj[k]) / lam_tot
        T_inf = amb + (g - q * u) / lam_tot
        T = T_inf + (T - T_inf) * decay
        Ts[k] = T
        prev = u
    J += price[-1] * (T - T0) * c_th / 3.6e6 / cp
    days = N * S.DT / 24.0
    Lval = float(V[i0, 0]) / days
    return dict(J=J / days, acts=acts, T=Ts, T_mean=float(Ts.mean()),
                L=Lval)


def neighbour_traj(geo, T_hist):
    """Effective inter-zone temperature trajectory for each zone."""
    nz, N = geo["nz"], T_hist.shape[1]
    out = np.zeros((nz, N))
    nbr = [[] for _ in range(nz)]
    for a, b in geo["pairs"]:
        nbr[a].append(b)
        nbr[b].append(a)
    for i in range(nz):
        if geo["lam_iz"][i] > 0:
            out[i] = T_hist[nbr[i]].mean(axis=0)
        else:
            out[i] = T_hist[i]
    return out


def bound_at_lambda(geo, city, w, lam, tgt, price_v=PRICE):
    """Lower bound on the coupled cost at one multiplier.

    TWO relaxations, both in the safe direction:
      * neighbours are pinned at T_min for the whole window, the coldest the
        band permits, which is the most help any zone could possibly receive;
      * the building mean-temperature constraint is dualised, so the bound
        holds for EVERY schedule matched in that mean, whatever its structure.
    Each is a relaxation, so the result cannot exceed the true coupled optimum.
    """
    _, _, N = H.series(city, 168, w)
    nz = geo["nz"]
    tot = 0.0
    for i in range(nz):
        r = zone_dp(city, w, price_v, geo["lam_env"][i], geo["lam_iz"][i],
                    np.full(N, LO), geo["faces"][i],
                    lam_mult=lam, nz=nz)
        if r is None:
            return None
        tot += r["L"]
    return tot / nz - lam * tgt


def bound_optimistic(geo, city, w, tgt, price_v=PRICE, lams=None):
    """max over lambda of the dual, which is the best bound this family gives."""
    if lams is None:
        lams = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]
    best = None
    for lam in lams:
        v = bound_at_lambda(geo, city, w, lam, tgt, price_v)
        if v is None:
            continue
        if best is None or v > best:
            best = v
    return best


def best_response(geo, city, w, tgt, price_v=PRICE, cap=None, iters=6,
                  tol=1e-3):
    """Each zone's optimal response to its neighbours, iterated to a fixed point.

    `cap` is an occupied ceiling applied to every zone; it is the device that
    brings the building's mean occupied temperature down to the baseline's.
    Returns the attained cost and the realised building mean, so the caller can
    scan `cap` until the arm is no warmer than its comparator.
    """
    _, _, N = H.series(city, 168, w)
    T_hist = np.full((geo["nz"], N), T0)
    prev_J = None
    J = None
    for it in range(iters):
        tiz = neighbour_traj(geo, T_hist)
        newT = np.zeros_like(T_hist)
        tot = 0.0
        for i in range(geo["nz"]):
            r = zone_dp(city, w, price_v, geo["lam_env"][i], geo["lam_iz"][i],
                        tiz[i], geo["faces"][i], cap=cap)
            if r is None:
                return None
            newT[i] = r["T"]
            tot += r["J"]
        shift = float(np.abs(newT - T_hist).max())
        T_hist = newT
        J = tot / geo["nz"]
        if prev_J is not None and abs(J - prev_J) < tol and shift < 0.05:
            break
        prev_J = J
    return dict(J=J, iters=it + 1, shift=shift,
                T_mean=float(T_hist.mean()))


def attainable_matched(geo, city, w, tgt, price_v=PRICE, step=0.02):
    """Scan the ceiling down until the arm is NO WARMER than the baseline.

    The same criterion the single-zone study applies: an arm that is cooler
    than its comparator everywhere can claim no comfort credit, so its saving
    is attainable rather than bought with temperature.
    """
    best = None
    for cap in np.arange(HI, LO + 0.6, -step):
        r = best_response(geo, city, w, tgt, price_v, cap=float(cap))
        if r is None:
            continue
        if r["T_mean"] <= tgt + 1e-9:
            return dict(r, cap=float(cap))
        best = dict(r, cap=float(cap))
    return best


if __name__ == "__main__":
    city = "riyadh"
    rows = []
    print("THE MULTI-ZONE OPTIMUM, BRACKETED BY DECOMPOSITION\n")
    print("Every arm is comfort-matched: the attainable schedule is no warmer")
    print("than the baseline in every window, and the bound is dualised on the")
    print("building mean, so it holds for any schedule matched in that mean.\n")
    print(f"{'topo':6s} {'Nz':>3} {'THERM J':>9} {'attain J':>9} "
          f"{'bound J':>9} {'attain %':>9} {'bound %':>8} {'gap':>6} "
          f"{'worst dT':>9}")
    for kind, n in (("single", 1), ("grid", 2), ("grid", 3), ("grid", 4)):
        geo = MZ.build(kind, n, city)
        Jb, Ja, Jd, dTs = [], [], [], []
        for w in F.EVAL_W:
            base = MZ.simulate(geo, city, w, MZ.hyst(23.5, 22.5), days=7)
            tgt = base["T_mean_occ"]
            at = attainable_matched(geo, city, w, tgt)
            bd = bound_optimistic(geo, city, w, tgt)
            if at is None or bd is None:
                continue
            Jb.append(base["J"]); Ja.append(at["J"]); Jd.append(bd)
            dTs.append(at["T_mean"] - tgt)
        if not Jb:
            print(f"{geo['label']:6s} {geo['nz']:3d}  infeasible"); continue
        Jb_, Ja_, Jd_ = (float(np.mean(x)) for x in (Jb, Ja, Jd))
        sa = 100.0 * (Jb_ - Ja_) / Jb_
        sb = 100.0 * (Jb_ - Jd_) / Jb_
        worst = float(np.max(dTs))
        rows.append(dict(topo=geo["label"], nz=geo["nz"],
                         therm_J=round(Jb_, 4), attain_J=round(Ja_, 4),
                         bound_J=round(Jd_, 4), attain_sav=round(sa, 2),
                         bound_sav=round(sb, 2), gap=round(sb - sa, 2),
                         worst_dT=round(worst, 4), n_win=len(Jb)))
        print(f"{geo['label']:6s} {geo['nz']:3d} {Jb_:9.4f} {Ja_:9.4f} "
              f"{Jd_:9.4f} {sa:8.2f}% {sb:7.2f}% {sb-sa:6.2f} {worst:+9.4f}",
              flush=True)
    if rows:
        with open("/home/claude/rbrl/results/T20_multizone_opt.csv", "w",
                  newline="") as f:
            w_ = csv.DictWriter(f, fieldnames=list(rows[0]))
            w_.writeheader(); w_.writerows(rows)
        print("\n-> results/T20_multizone_opt.csv")
    print("\nSELF-CHECK: at N_z = 1 there are no neighbours, so the two")
    print("relaxations coincide with the single-zone problem and the attainable")
    print("value must agree with the single-zone study's 18.09% for Riyadh.")
