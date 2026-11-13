#!/usr/bin/env python3
"""Measured rerun of the experimental programme on this machine.

Part A reproduces the manuscript's own discretisation exactly as written in
src/environment.py (C_th = 77.2 kJ/K, dt = 1 h, forward Euler) and reports what
it produces.

Part B runs the same programme under a defensible configuration (exact
matrix-exponential integration, furnished effective capacity) with the
thermostat family, on held-out weeks, and measures wall-clock timing on this
CPU.

Every number this script prints is measured here. Hardware: see the header it
emits. There is no GPU in this environment.
"""
from __future__ import annotations
import sys, os, csv, time, platform
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
from hvac import HVACModel, Params, read_epw, vertical_irradiance
from env import HVACEnv, Rules, run_policy, therm
from train import load_city, agg
from run_all import cooling_test_starts, write

OUT = "/home/claude/rbrl/results"
os.makedirs(OUT, exist_ok=True)
TOPOS = ["1x1", "1x4", "2x2", "3x3", "4x4"]


def header():
    import torch
    print("=" * 72)
    print("MEASURED RERUN -- all figures produced on this machine")
    print(f"  platform : {platform.platform()}")
    print(f"  cpu      : {platform.processor() or 'x86_64'}, {os.cpu_count()} cores")
    print(f"  cuda     : torch.cuda.is_available() = {torch.cuda.is_available()}")
    print("=" * 72, flush=True)


# ---------------------------------------------------------------- Part A
def paper_scheme(city, topo, hours=168, c_th=77.2, dt=1.0):
    """The manuscript's own update, transcribed from src/environment.py.

        heat_flow = -q_hvac*u - (lam_tot/1000)*(T - t_out)
                    - (lam_iz_tot/1000)*(T - t_iz) + q_sol      [kW]
        T += (dt*3600/(c_th*1000)) * heat_flow * 1000
    """
    lam_ext, lam_win, lam_iz = 20.5, 12.5, 12.5      # configs/*.yaml
    q_hvac, shgc, a_gl = 2.0, 0.25, 2.0
    t_min, t_max, eps_g = 22.0, 26.0, 0.5
    lat = {"riyadh": 24.7, "jeddah": 21.5}[city]
    tdb, dni, dhi = read_epw(f"/home/claude/rbrl/{city}.epw")
    ghi = dni * 0.0 + dhi                             # GHI proxy as in the original
    r, c = {"1x1": (1, 1), "1x2": (1, 2), "1x4": (1, 4), "1x6": (1, 6),
            "2x2": (2, 2), "3x3": (3, 3), "4x4": (4, 4)}[topo]
    n = r * c
    A = np.zeros((n, n))
    for i in range(r):
        for j in range(c):
            k = i * c + j
            if j + 1 < c: A[k, k + 1] = A[k + 1, k] = 1
            if i + 1 < r: A[k, k + c] = A[k + c, k] = 1
    T = np.full(n, 24.0); prev = np.zeros(n, int)
    h0 = 181 * 24
    nviol = 0; sw = 0; diverged = False
    for k in range(hours):
        h = (h0 + k) % 8760
        t_out = tdb[h]; q_sol = shgc * a_gl * ghi[h] / 1000.0
        u = prev.copy()
        u[T >= t_max - eps_g] = 1
        u[T <= t_min + eps_g] = 0
        for i in range(n):
            nb = np.where(A[i] > 0)[0]
            t_iz = T[nb].mean() if len(nb) else T[i]
            lam_iz_tot = lam_iz * len(nb)
            hf = (-q_hvac * u[i] - ((lam_ext + lam_win) / 1000.0) * (T[i] - t_out)
                  - (lam_iz_tot / 1000.0) * (T[i] - t_iz) + q_sol)
            T[i] += dt * 3600.0 / (c_th * 1000.0) * hf * 1000.0
        if not np.all(np.isfinite(T)) or np.any(np.abs(T) > 1e6):
            diverged = True; break
        nviol += int(np.sum((T > t_max) | (T < t_min)))
        sw += int(np.sum((u == 1) & (prev == 0)))
        prev = u
    days = (k + 1) * dt / 24.0
    return dict(topo=topo, city=city, c_th=c_th, dt_h=dt,
                diverged=diverged, steps_completed=k + 1,
                T_min=float(np.nanmin(T)) if np.all(np.isfinite(T)) else float("nan"),
                T_max=float(np.nanmax(T)) if np.all(np.isfinite(T)) else float("nan"),
                v_c_pct=round(100.0 * nviol / max(1, (k + 1) * n), 2),
                f_s=round(sw / (n * days), 2) if days > 0 else float("nan"))


# ---------------------------------------------------------------- Part B
def defensible(city, topo, c_th=2400.0, dt=0.25, n_windows=24):
    P = Params(dt=dt, c_th=c_th, eps_lo=0.5, eps_hi=0.35)
    m = HVACModel(topo, P)
    to, ir = load_city(city)
    H = 7 * int(round(24 / dt))
    st, _ = cooling_test_starts(city, dt, H, 7)
    rows = []
    for lab, db in (("THERM-1K", 1.0), ("THERM-2K", 2.0), ("THERM-3K", 3.0)):
        env = HVACEnv(m, to, ir, st, cost_model="S", horizon=H, P=P,
                      rules=Rules(P, use_cc=False))
        t0 = time.perf_counter()
        a = agg([run_policy(env, therm(db), start=int(s)) for s in st[:n_windows]])
        wall = time.perf_counter() - t0
        rows.append(dict(city=city, topo=topo, n_zones=m.n, controller=lab,
                         c_th=c_th, dt_h=dt, n_windows=min(n_windows, len(st)),
                         wall_s=round(wall, 2),
                         ms_per_decision=round(1e3 * wall /
                                               max(1, min(n_windows, len(st)) * H * m.n), 4),
                         **{k: round(v, 4) for k, v in a.items()}))
    return rows


if __name__ == "__main__":
    header()
    t0 = time.time()

    print("\n--- PART A: the manuscript's own scheme (C_th=77.2, dt=1h, forward Euler) ---",
          flush=True)
    A = []
    for city in ("riyadh", "jeddah"):
        for topo in TOPOS:
            r = paper_scheme(city, topo)
            A.append(r)
            print(f"  {city:7s} {topo:4s}: diverged={str(r['diverged']):5s} "
                  f"steps={r['steps_completed']:3d} T range [{r['T_min']:.1f},{r['T_max']:.1f}] "
                  f"v_c={r['v_c_pct']:6.2f}% f_s={r['f_s']}", flush=True)
    write("rerun_partA_paper_scheme.csv", A)

    print("\n--- PART B: defensible configuration, measured ---", flush=True)
    B = []
    for city in ("riyadh", "jeddah"):
        for topo in TOPOS:
            rows = defensible(city, topo)
            B += rows
            r = rows[-1]
            print(f"  {city:7s} {topo:4s} Nz={r['n_zones']:2d} THERM-3K: "
                  f"J={r['J_per_zone_day']:.4f} f_s={r['f_s']:5.2f} v_c={r['v_c']:5.2f} "
                  f"({r['ms_per_decision']:.4f} ms/decision)", flush=True)
            write("rerun_partB_defensible.csv", B)

    print(f"\ndone in {time.time()-t0:.0f}s", flush=True)
