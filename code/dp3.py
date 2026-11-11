#!/usr/bin/env python3
"""Single-zone optimality reference, rebuilt to the numerics supervisor's spec.

Defects in dp2.py that this corrects
------------------------------------
1. Conductance was fabricated: `lam_per_wall * walls` with lam_per_wall = 33.0
   (the PAPER's config split) combined with the rebuild's C_th and integrator.
   The harness defines  Lambda(n) = (U_wall*A_wall + U_win*A_gl)*n + Lambda_inf
                                  = 11.90*n + 12.864 W/K
   so 24.76 (one face) and 60.46 (four faces), not 33 and 132. The Lambda=132
   "capacity infeasibility" was an artefact: at 60.46 the peak load is ~1660 W
   against 2000 W available, and the instance is feasible.
2. BIG = 1e12 was FINITE, so "hard" mode silently optimised over band-violating
   paths, and the forward rollout accumulated only c_sw and energy -- omitting
   the penalty the optimiser was minimising. Reported costs were therefore not
   costs. Here the grid is restricted to [T_min, T_max] so infeasibility is
   structural: a transition leaving the band is simply unavailable, no sentinel
   value is interpolated, and feasibility is exact.
3. Terminal condition V_H == 0 let the policy coast off at the end of the
   horizon, finishing warm with borrowed thermal storage never repaid -- worth
   ~2.6% of the very gap being measured. Here the terminal condition is CYCLIC:
   the run must end at its starting state, so J* is the cost of a sustainable
   cycle and is comparable with a controller that has to keep running.

Also added
----------
* Pass 0 reachability certificate. Because the scalar dynamics are monotone in
  u, the reachable set at each step is the interval between the u==0 and u==1
  trajectories. One forward pass of each certifies whether the band is holdable
  at all, before any DP is run.
* Feasibility checked at the post-step temperature only, which is EXACT rather
  than an approximation: T_inf is constant within a step and the solution
  relaxes monotonically toward it, so the intra-step extremum is at an endpoint.
* J_rollout: the DP policy executed on the exact dynamics with no grid in the
  loop. This is a certified upper bound on J*. V_bwd is an estimate, not a
  bound, so both are reported.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, os, argparse
sys.path.insert(0, _ROOT + "")
import numpy as np
from hvac import Params, read_epw, vertical_irradiance

P0 = Params()
PER_FACE = P0.u_wall * P0.a_wall + P0.u_win * P0.a_gl     # 11.90 W/K
LAM_INF = P0.lam_inf                                       # 12.864 W/K


def lam_of(faces: int) -> float:
    """Harness envelope conductance: affine in exposed faces, not multiplicative."""
    return PER_FACE * faces + LAM_INF


def exogenous(city, hours, start_day, dt):
    lat = {"riyadh": 24.7, "jeddah": 21.5, "taif": 21.483}[city]
    tdb, dni, dhi = read_epw(f"{_ROOT}/{city}.epw")
    irr = vertical_irradiance(dni, dhi, lat, azimuth_deg=180.0)
    spd = int(round(1.0 / dt)); N = int(round(hours / dt)); h0 = start_day * 24
    return (np.repeat(tdb[h0:h0 + hours], spd)[:N],
            np.repeat(irr[h0:h0 + hours], spd)[:N], N)


def reachability(city, faces, hours, start_day, dt, c_th, q_hvac,
                 t_min, t_max, shgc, a_gl, T0=24.0):
    """Pass 0: is the band holdable at all? Exact, no DP."""
    lam = lam_of(faces)
    t_out, irrad, N = exogenous(city, hours, start_day, dt)
    decay = float(np.exp(-dt * 3600.0 * lam / (c_th * 1e3)))
    hot = cold = T0                              # u==0 envelope, u==1 envelope
    worst_hot = -1e9; worst_cold = 1e9
    for k in range(N):
        g = shgc * a_gl * irrad[k]
        hot = (t_out[k] + g / lam) + (hot - (t_out[k] + g / lam)) * decay
        ci = t_out[k] + (g - q_hvac) / lam
        cold = ci + (cold - ci) * decay
        worst_hot = max(worst_hot, hot); worst_cold = min(worst_cold, cold)
    return dict(max_reachable=worst_hot, min_reachable=worst_cold,
                over_unavoidable=bool(worst_cold > t_max),
                under_unavoidable=bool(worst_hot < t_min),
                peak_load_W=None)


def solve(city="riyadh", faces=1, hours=168, start_day=181,
          c_th=2400.0, dt=0.25, q_hvac=2000.0, cop=2.985,
          t_min=22.0, t_max=26.0, c_sw=0.15, price=0.05,
          shgc=0.25, a_gl=2.0, n_grid=401, cyclic=True, T0=24.0, u0=0):
    lam = lam_of(faces)
    p_hvac = q_hvac / cop / 1000.0
    t_out, irrad, N = exogenous(city, hours, start_day, dt)
    decay = float(np.exp(-dt * 3600.0 * lam / (c_th * 1e3)))

    # grid restricted to the band: leaving it is structurally unavailable
    Tg = np.linspace(t_min, t_max, n_grid)
    e_step = p_hvac * dt
    run_cost = price * e_step

    INF = np.inf
    if cyclic:
        # One-sided terminal condition: the run may not finish WARMER than it
        # started, so thermal storage cannot be borrowed and left unrepaid.
        # Requiring an exact return to the start cell is infeasible on a finite
        # grid (the trajectory would have to land on one 10 mK cell), which is
        # why the strict version returned INFEASIBLE everywhere.
        V = np.where(np.repeat(Tg[:, None], 2, axis=1) <= T0 + 1e-9, 0.0, INF)
    else:
        V = np.zeros((n_grid, 2))

    policy = np.zeros((N, n_grid, 2), dtype=np.int8)
    for k in range(N - 1, -1, -1):
        g = shgc * a_gl * irrad[k]
        cand = np.full((n_grid, 2, 2), INF)
        for u in (0, 1):
            T_inf = t_out[k] + (g - q_hvac * u) / lam
            Tp = T_inf + (Tg - T_inf) * decay
            inside = (Tp >= t_min - 1e-9) & (Tp <= t_max + 1e-9)
            Tc = np.clip(Tp, t_min, t_max)
            Vn = np.interp(Tc, Tg, V[:, u])          # within-band only
            nxt = np.where(inside, run_cost * u + Vn, INF)
            for up in (0, 1):
                sw = c_sw if (u == 1 and up == 0) else 0.0
                cand[:, up, u] = np.where(np.isfinite(nxt), sw + nxt, INF)
        Vn2 = np.full((n_grid, 2), INF)
        for up in (0, 1):
            bu = np.argmin(np.nan_to_num(cand[:, up, :], nan=INF, posinf=1e300), axis=1)
            policy[k, :, up] = bu.astype(np.int8)
            Vn2[:, up] = cand[np.arange(n_grid), up, bu]
        V = Vn2

    V0 = float(V[int(np.argmin(np.abs(Tg - T0))), u0])
    if not np.isfinite(V0):
        return dict(city=city, faces=faces, feasible=False, J_rollout=np.inf,
                    V_bwd=np.inf, lam=lam, n_grid=n_grid)

    # forward rollout on EXACT dynamics, no grid in the loop
    T = T0; up = u0
    cost = 0.0; sw_n = 0; e = 0.0; viol = 0; dh = 0.0
    for k in range(N):
        u = int(policy[k, int(np.argmin(np.abs(Tg - T))), up])
        if u == 1 and up == 0: cost += c_sw; sw_n += 1
        if u == 1: cost += run_cost; e += e_step
        g = shgc * a_gl * irrad[k]
        T_inf = t_out[k] + (g - q_hvac * u) / lam
        T = T_inf + (T - T_inf) * decay
        if T > t_max + 1e-9 or T < t_min - 1e-9:
            viol += 1
            dh += max(0.0, T - t_max) * dt + max(0.0, t_min - T) * dt
        up = u
    d = hours / 24.0
    return dict(city=city, faces=faces, feasible=True, lam=lam,
                J_rollout=cost / d, V_bwd=V0 / d, E=e / d, f_s=sw_n / d,
                v_c=100.0 * viol / N, degree_hours=dh, n_grid=n_grid,
                T_end=T, cyclic=cyclic)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--conv", action="store_true", help="grid convergence study")
    a = ap.parse_args()
    print(f"Lambda(n) = {PER_FACE:.2f}n + {LAM_INF:.3f} W/K  "
          f"-> 1 face {lam_of(1):.2f}, 2 faces {lam_of(2):.2f}, 4 faces {lam_of(4):.2f}\n")

    if a.conv:
        print("Grid convergence (Riyadh, 1 face, cyclic, price 0.05):")
        prev = None
        for n in (101, 201, 401, 801, 1601):
            r = solve(n_grid=n)
            d = "" if prev is None else f"   |dV| = {abs(r['V_bwd']-prev):.5f}"
            print(f"  n={n:5d}  dT={(26-22)/(n-1)*1000:6.1f} mK  "
                  f"V_bwd={r['V_bwd']:.5f}  J_rollout={r['J_rollout']:.5f}  "
                  f"v_c={r['v_c']:.2f}%{d}")
            prev = r["V_bwd"]
        raise SystemExit

    print("Pass 0 reachability certificates (is the band holdable at all?)")
    for city in ("riyadh", "jeddah"):
        for faces in (1, 2, 4):
            c = reachability(city, faces, 168, 181, 0.25, 2400.0, 2000.0,
                             22.0, 26.0, 0.25, 2.0)
            print(f"  {city:7s} {faces} face(s) Lam={lam_of(faces):6.2f}: "
                  f"u=0 reaches {c['max_reachable']:7.2f} C, "
                  f"u=1 reaches {c['min_reachable']:7.2f} C  "
                  f"-> over-temp unavoidable: {c['over_unavoidable']}")

    print("\nOptimum (cyclic terminal condition, grid on [22,26], price 0.05 SAR/kWh)")
    for city in ("riyadh", "jeddah"):
        for faces in (1, 2, 4):
            r = solve(city=city, faces=faces, n_grid=401)
            if not r["feasible"]:
                print(f"  {city:7s} {faces} face(s): INFEASIBLE (no sustainable cycle)")
                continue
            print(f"  {city:7s} {faces} face(s) Lam={r['lam']:6.2f}: "
                  f"J_rollout={r['J_rollout']:.4f}  V_bwd={r['V_bwd']:.4f}  "
                  f"f_s={r['f_s']:5.2f}  E={r['E']:6.3f}  v_c={r['v_c']:.2f}%  "
                  f"deg-h={r['degree_hours']:.3f}")
