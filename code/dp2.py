#!/usr/bin/env python3
"""Exact finite-horizon optimum for the single-zone binary scheduling problem.

Why the earlier attempt (dp.py) failed: it carried a cumulative-energy
dimension and indexed it incorrectly. Under the tariff actually in force the
marginal price is CONSTANT for this dwelling (the 6,000 kWh block boundary is
never crossed), so the per-step cost has no dependence on accumulated
consumption and the state collapses to (T, u_prev). That is a 2-D DP.

Method
------
Backward value iteration over N steps. State: T on a uniform grid, u_prev in
{0,1}. Transition: the EXACT first-order solution
    T' = T_inf + (T - T_inf) * exp(-h * Lambda / C_th)
with T_inf the forcing-dependent asymptote for the chosen action. The value
function is evaluated at T' by LINEAR INTERPOLATION rather than by projecting
the state onto the nearest grid point, so discretisation error does not
accumulate as a random walk in state space.

Comfort is handled two ways, reported side by side, because a cooling-only
plant cannot raise temperature and some under-temperature excursions may be
unavoidable:
  * 'penalty'  - quadratic charge on excursion, finite, always solvable
  * 'hard'     - excursions forbidden (+inf), returns inf if infeasible
Reporting both distinguishes unavoidable infeasibility from policy error.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, os, argparse
sys.path.insert(0, _ROOT + "")
import numpy as np
from hvac import read_epw, vertical_irradiance

BIG = 1e12


def solve(city="riyadh", walls=1, hours=168, start_day=181,
          c_th=2400.0, dt=0.25, q_hvac=2000.0, cop=2.985,
          t_min=22.0, t_max=26.0, c_sw=0.15, price=0.18,
          shgc=0.25, a_gl=2.0, lam_per_wall=33.0,
          grid_lo=14.0, grid_hi=34.0, n_grid=1001,
          mode="penalty", pen=500.0, verbose=True):
    lam = lam_per_wall * walls                      # W/K
    p_hvac = q_hvac / cop / 1000.0                  # kW
    lat = {"riyadh": 24.7, "jeddah": 21.5}[city]
    tdb, dni, dhi = read_epw(f"{_ROOT}/{city}.epw")
    irr = vertical_irradiance(dni, dhi, lat, azimuth_deg=180.0)

    spd = int(round(1.0 / dt))                      # steps per hour
    N = int(round(hours / dt))
    Tg = np.linspace(grid_lo, grid_hi, n_grid)
    decay = float(np.exp(-dt * 3600.0 * lam / (c_th * 1e3)))

    # per-step exogenous series
    h0 = start_day * 24
    t_out = np.repeat(tdb[h0:h0 + hours], spd)[:N]
    irrad = np.repeat(irr[h0:h0 + hours], spd)[:N]

    # cost of a step: switch-on charge + energy
    e_step = p_hvac * dt                            # kWh per on-step
    run_cost = price * e_step

    # excursion charge on the POST-step temperature
    def excursion(T):
        return np.maximum(0.0, t_min - T) ** 2 + np.maximum(0.0, T - t_max) ** 2

    V = np.zeros((n_grid, 2))                       # terminal value
    policy = np.zeros((N, n_grid, 2), dtype=np.int8)

    for k in range(N - 1, -1, -1):
        q_sol = shgc * a_gl * irrad[k]              # W
        Vn = np.full((n_grid, 2), BIG)
        cand = np.empty((n_grid, 2, 2))             # [T, u_prev, u]
        for u in (0, 1):
            T_inf = t_out[k] + (q_sol - q_hvac * u) / lam
            Tp = T_inf + (Tg - T_inf) * decay
            exc = excursion(Tp)
            if mode == "hard":
                bad = exc > 1e-12
                step_pen = np.where(bad, BIG, 0.0)
            else:
                step_pen = pen * exc
            # value of landing at Tp with u_prev = u, by linear interpolation
            Vnext = np.interp(Tp, Tg, V[:, u])
            base = run_cost * u + step_pen + Vnext
            for up in (0, 1):
                sw = c_sw if (u == 1 and up == 0) else 0.0
                cand[:, up, u] = sw + base
        for up in (0, 1):
            best_u = np.argmin(cand[:, up, :], axis=1)
            policy[k, :, up] = best_u.astype(np.int8)
            Vn[:, up] = cand[np.arange(n_grid), up, best_u]
        V = Vn
        if verbose and k % 200 == 0:
            print(f"    step {k:4d}/{N}  V(24C,off) = {np.interp(24.0,Tg,V[:,0]):.4f}",
                  flush=True)

    # forward simulate the optimal policy from T = 24, compressor off
    T = 24.0; up = 0
    cost = sw_n = 0.0; e_tot = 0.0; viol = 0; dh = 0.0
    traj = []
    for k in range(N):
        u = int(policy[k, int(np.argmin(np.abs(Tg - T))), up])
        if u == 1 and up == 0:
            cost += c_sw; sw_n += 1
        if u == 1:
            cost += run_cost; e_tot += e_step
        q_sol = shgc * a_gl * irrad[k]
        T_inf = t_out[k] + (q_sol - q_hvac * u) / lam
        T = T_inf + (T - T_inf) * decay
        if T > t_max or T < t_min:
            viol += 1
            dh += max(0.0, T - t_max) * dt + max(0.0, t_min - T) * dt
        traj.append((t_out[k], T, u))
        up = u
    days = hours / 24.0
    return dict(city=city, walls=walls, mode=mode, c_th=c_th, dt=dt,
                J_star=cost / days, E=e_tot / days, f_s=sw_n / days,
                v_c=100.0 * viol / N, degree_hours=dh,
                V_backward=float(np.interp(24.0, Tg, V[:, 0])) / days,
                n_grid=n_grid, traj=traj)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", type=int, default=1001)
    a = ap.parse_args()
    print("Exact single-zone optimum, state (T, u_prev), linear-interpolated value\n")
    for city in ("riyadh", "jeddah"):
        for walls in (1, 4):
            for mode in ("penalty", "hard"):
                r = solve(city=city, walls=walls, mode=mode,
                          n_grid=a.grid, verbose=False)
                jb = r["V_backward"]
                print(f"  {city:7s} walls={walls} {mode:8s}: "
                      f"J*={r['J_star']:8.4f}  f_s={r['f_s']:5.2f}  "
                      f"E={r['E']:6.3f}  v_c={r['v_c']:5.2f}%  "
                      f"deg-h={r['degree_hours']:6.2f}  "
                      f"V_bwd={jb:8.4f}", flush=True)
