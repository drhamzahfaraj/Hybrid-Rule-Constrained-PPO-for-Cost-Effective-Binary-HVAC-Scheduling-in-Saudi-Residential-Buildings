#!/usr/bin/env python3
"""Exact dynamic-programming optimum for the single-zone instance.

This is the optimality reference the manuscript claims not to have. The state
is (T, E_cum, u_prev); the transition uses the exact exponential update, so the
bound is not contaminated by integration error. Backward sweep over the horizon.
"""
from __future__ import annotations
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hvac import *

def dp_optimum(city, horizon_h, start_h, P: Params, cost_model="S",
               n_T=81, n_E=361, verbose=True):
    lat = {"riyadh": 24.7, "jeddah": 21.5}[city]
    tdb, dni, dhi = read_epw(f"{os.path.dirname(os.path.abspath(__file__))}/{city}.epw")
    irr = vertical_irradiance(dni, dhi, lat)
    m = HVACModel("1x1", P, walls_override=1)
    spd = int(round(1.0 / P.dt))
    H = int(horizon_h / P.dt)

    # grid extends well beyond the band so excursions are tracked honestly
    T_LO, T_HI = P.t_min - 6.0, P.t_max + 10.0
    Tg = np.linspace(T_LO, T_HI, n_T)
    e_step = P.p_hvac * P.dt
    Emax = e_step * H
    Eg = np.linspace(0.0, Emax, n_E)
    dE = Eg[1] - Eg[0]

    # transition for each (T, u): exact scalar update
    lam = float(m.lam[0]); agl = float(m.a_gl[0]); C = P.c_th * 1e3
    tau_h = C / lam / 3600.0

    INF = 1e18
    ALPHA = 50.0
    V = np.zeros((n_T, n_E, 2))
    for k in range(H - 1, -1, -1):
        idx = (start_h * spd + k) % len(tdb)
        t_out = tdb[idx // spd] if spd > 1 else tdb[idx]
        ir = irr[idx // spd] if spd > 1 else irr[idx]
        Vn = np.full((n_T, n_E, 2), INF)
        base = P.e_base * ((start_h + k * P.dt) % 720.0) / 720.0
        for u in (0, 1):
            Tinf = t_out + (P.shgc * agl * ir - P.q_hvac * u) / lam
            Tn = Tinf + (Tg - Tinf) * np.exp(-P.dt / tau_h)
            dev = np.maximum(0.0, np.maximum(P.t_min - Tn, Tn - P.t_max))
            pen = ALPHA * dev ** 2
            Tc = np.clip(Tn, T_LO, T_HI)
            ti = np.clip(np.round((Tc - T_LO) / (Tg[1] - Tg[0])).astype(int), 0, n_T - 1)
            de = e_step * u
            p = marginal_price(cost_model, base + 0.0, P)   # price at interval start
            for up in (0, 1):
                sw = P.c_sw * (1 if (u == 1 and up == 0) else 0)
                ei = int(round(de / dE)) if dE > 0 else 0
                nxt = np.empty((n_T, n_E))
                Vk = V[:, :, u]
                for j in range(n_E):
                    jj = min(j + ei, n_E - 1)
                    pj = marginal_price(cost_model, base + Eg[j], P)
                    nxt[:, j] = sw + pj * de + Vk[ti, jj]
                nxt += pen[:, None]
                Vn[:, :, up] = np.minimum(Vn[:, :, up], nxt)
        V = Vn
    j = int(np.argmin(np.abs(Tg - 24.0)))
    best = float(V[j, 0, 0])
    days = horizon_h / 24.0
    return best / days, tau_h


if __name__ == "__main__":
    P = Params(dt=0.25, eps_lo=0.5, eps_hi=0.35)
    import time
    for city in ("riyadh", "jeddah"):
        t0 = time.time()
        Jstar, tau = dp_optimum(city, 168, 181 * 24, P, "S", n_T=321, n_E=181)
        print(f"{city}: DP optimum J* = {Jstar:.4f} SAR/zone/day  "
              f"(tau={tau:.2f} h, {time.time()-t0:.1f}s)", flush=True)
