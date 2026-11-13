#!/usr/bin/env python3
"""Exact finite-horizon optimum for the single-zone instance, by backward DP.

Reverse engineering: establish J* first, then ask what any controller can
possibly achieve, and only then ask whether PPO can reach it.

The earlier attempt (dp.py) carried cumulative energy as a third state
dimension and never worked. It does not need to: inside a tariff block the
marginal price is constant (verified: the bill is a maximum of affine functions
and the modelled dwelling never crosses a boundary), so energy cost is
p * P_hvac * dt * u per step independently of history. The state is therefore
just (T, u_prev) and the DP is exact and cheap.

State    : T on a fine grid, u_prev in {0,1}
Action   : u in {0,1}
Cost     : c_sw * [u=1 and u_prev=0] + p * P_hvac * dt * u
Dynamics : exact first-order exponential update
Comfort  : hard. Leaving [t_min, t_max] is infeasible (cost +inf), so the DP
           optimum satisfies O1 by construction and is directly comparable to
           the rule-based controllers.
"""
from __future__ import annotations
import sys, time
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
from hvac import read_epw, vertical_irradiance

INF = 1e15


def dp_single_zone(city="riyadh", start_day=181, days=7, dt=0.25,
                   c_th=2400.0, lam=33.0, q_hvac=2000.0, cop=2.985,
                   c_sw=0.15, price=0.18, shgc=0.25, a_gl=2.0,
                   t_min=22.0, t_max=26.0, nT=801, verbose=True):
    lat = {"riyadh": 24.7, "jeddah": 21.5}[city]
    tdb, dni, dhi = read_epw(f"/home/claude/rbrl/{city}.epw")
    irr = vertical_irradiance(dni, dhi, lat, azimuth_deg=180.0)

    spd = int(round(24.0 / dt))
    H = days * spd
    p_hvac = q_hvac / cop / 1000.0            # kW electrical
    C = c_th * 1e3
    tau = C / lam / 3600.0                    # hours
    decay = np.exp(-dt / tau)

    Tg = np.linspace(t_min, t_max, nT)        # feasible set only
    step_T = Tg[1] - Tg[0]

    # terminal: no cost beyond the horizon
    V = np.zeros((nT, 2))
    policy = np.zeros((H, nT, 2), dtype=np.int8)

    for k in range(H - 1, -1, -1):
        h = (start_day * 24 + int(k * dt)) % 8760
        t_out = tdb[h]
        q_sol = shgc * a_gl * irr[h]
        Vn = np.full((nT, 2), INF)
        best_u = np.zeros((nT, 2), dtype=np.int8)
        for u in (0, 1):
            Tinf = t_out + (q_sol - q_hvac * u) / lam
            Tn = Tinf + (Tg - Tinf) * decay
            feas = (Tn >= t_min - 1e-9) & (Tn <= t_max + 1e-9)
            idx = np.clip(np.round((Tn - t_min) / step_T).astype(int), 0, nT - 1)
            energy = price * p_hvac * dt * u
            for up in (0, 1):
                sw = c_sw if (u == 1 and up == 0) else 0.0
                cand = np.where(feas, sw + energy + V[idx, u], INF)
                better = cand < Vn[:, up]
                Vn[better, up] = cand[better]
                best_u[better, up] = u
        V = Vn
        policy[k] = best_u
        if verbose and k % (spd * 1) == 0:
            pass

    # start at 24 C, compressor off
    j = int(np.argmin(np.abs(Tg - 24.0)))
    Jstar = float(V[j, 0])
    feasible = Jstar < INF / 2
    return dict(J_total=Jstar if feasible else float("nan"),
                J_per_day=(Jstar / days) if feasible else float("nan"),
                feasible=feasible, tau_h=tau, H=H, nT=nT,
                Tg=Tg, policy=policy, start_day=start_day, dt=dt,
                decay=decay, tdb=tdb, irr=irr, p_hvac=p_hvac,
                lam=lam, q_hvac=q_hvac, shgc=shgc, a_gl=a_gl,
                c_sw=c_sw, price=price, t_min=t_min, t_max=t_max)


def rollout_dp(d):
    """Run the DP policy forward and measure cost, switching and comfort."""
    Tg, pol = d["Tg"], d["policy"]
    T = 24.0; up = 0; J = 0.0; sw = 0; nv = 0
    dt, spd = d["dt"], int(round(24.0 / d["dt"]))
    for k in range(d["H"]):
        i = int(np.clip(np.round((T - d["t_min"]) / (Tg[1] - Tg[0])), 0, d["nT"] - 1))
        u = int(pol[k, i, up])
        h = (d["start_day"] * 24 + int(k * dt)) % 8760
        t_out = d["tdb"][h]; q_sol = d["shgc"] * d["a_gl"] * d["irr"][h]
        Tinf = t_out + (q_sol - d["q_hvac"] * u) / d["lam"]
        T = Tinf + (T - Tinf) * d["decay"]
        if u == 1 and up == 0:
            J += d["c_sw"]; sw += 1
        J += d["price"] * d["p_hvac"] * dt * u
        if T > d["t_max"] + 1e-6 or T < d["t_min"] - 1e-6:
            nv += 1
        up = u
    days = d["H"] * dt / 24.0
    return dict(J_per_day=J / days, f_s=sw / days, v_c_pct=100.0 * nv / d["H"])


if __name__ == "__main__":
    t0 = time.time()
    print("Exact single-zone DP optimum (hard comfort, constant marginal price)\n")
    for city in ("riyadh", "jeddah"):
        for day in (181, 200):
            d = dp_single_zone(city=city, start_day=day, verbose=False)
            if not d["feasible"]:
                print(f"  {city:7s} day {day}: INFEASIBLE (band not holdable)")
                continue
            r = rollout_dp(d)
            print(f"  {city:7s} day {day}: J* = {d['J_per_day']:.4f} SAR/zone/day "
                  f"| rollout J={r['J_per_day']:.4f} f_s={r['f_s']:.2f} "
                  f"v_c={r['v_c_pct']:.2f}%  (tau={d['tau_h']:.2f} h)")
    print(f"\ndone in {time.time()-t0:.1f}s")
