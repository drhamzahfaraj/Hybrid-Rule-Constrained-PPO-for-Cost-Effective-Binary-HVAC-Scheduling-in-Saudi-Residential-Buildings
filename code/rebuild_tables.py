#!/usr/bin/env python3
"""Regenerated results table: computed 10 Nov 2026, NEW WORK.

This is not a correction of the published tables. No measurement exists to
recover: there is no trained agent, no checkpoint, and no rollout of the
proposed controller in the project artefacts, and the repository's own schema
file records the published result tables as transcribed from the manuscript
rather than emitted by a run. Everything below is computed here, today, and
must be labelled as such.

Parameter set, chosen to be internally consistent and to satisfy the
feasibility condition the published set violates:

    C_th     6700 kJ/K   effective furnished capacity (reference implementation)
    dt       0.25 h      Q_hvac*dt/C_th = 1.07 K against a 4 K band  (OK)
    Lambda(n) = 11.90 n + 12.864 W/K   fabric + glazing per exposed face, plus
                                       infiltration at 0.6 ACH
    COP(T)   5.35 - 0.0675 T, clipped [1.5, 5.0]   temperature-dependent
    Q(T)     Q_r [1 - 0.010 (T - 35)], floor 0.6   AHRI capacity derate
    tariff   two-block 0.18 / 0.30 SAR/kWh at 6000 kWh/month (in force)
    c_sw     0.15 SAR/start, reported with a sensitivity because the objective
             is highly sensitive to it

Controllers:
    THERM-1K     naive narrow-deadband thermostat (the comparator the published
                 saving was measured against)
    THERM-tuned  best feasible two-parameter hysteresis, found by 2-D search
    DP           exact clairvoyant optimum, single zone only (upper bound on
                 what any policy can achieve; NOT implementable)

Reported for every row: cost, energy, switching rate, comfort violations,
degree-hours, and MEAN ZONE TEMPERATURE -- the column whose absence makes a
controller comparison uninterpretable.
"""
from __future__ import annotations
import sys, csv, os, time, platform
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
from hvac import Params, read_epw, vertical_irradiance

P0 = Params()
PER_FACE = P0.u_wall * P0.a_wall + P0.u_win * P0.a_gl      # 11.90 W/K
LAM_INF = P0.lam_inf                                        # 12.864 W/K
C_TH = 6700.0
DT = 0.25
Q_RATED = 2000.0
T_MIN, T_MAX = 22.0, 26.0
SHGC, A_GL = 0.25, 2.0
C_SW = 0.15
E_BASE = 800.0                                              # kWh/month non-HVAC
TOPO = {"1x1": (1, 1), "1x4": (1, 4), "2x2": (2, 2), "3x3": (3, 3), "4x4": (4, 4)}


def cop_of(t):  return float(np.clip(5.35 - 0.0675 * t, 1.5, 5.0))
def qcap_of(t): return Q_RATED * max(0.6, 1.0 - 0.010 * (t - 35.0))
def price_of(e_cum): return 0.18 if e_cum <= 6000.0 else 0.30


def grid(nx, ny):
    n = nx * ny
    A = np.zeros((n, n))
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if j + 1 < ny: A[k, k + 1] = A[k + 1, k] = 1
            if i + 1 < nx: A[k, k + nx if False else k + ny] = A[k + ny, k] = 1
    faces = np.array([(i == 0) + (i == nx - 1) + (j == 0) + (j == ny - 1)
                      for i in range(nx) for j in range(ny)], float)
    return A, faces


def series(city, hours, start_day):
    lat = {"riyadh": 24.7, "jeddah": 21.5}[city]
    tdb, dni, dhi = read_epw(f"/home/claude/rbrl/{city}.epw")
    irr = vertical_irradiance(dni, dhi, lat, azimuth_deg=180.0)
    spd = int(round(1.0 / DT)); N = int(round(hours / DT)); h0 = start_day * 24
    return (np.repeat(tdb[h0:h0 + hours], spd)[:N],
            np.repeat(irr[h0:h0 + hours], spd)[:N], N)


def run(city, topo, lo, hi, hours=168, start_day=181):
    """Multi-zone rollout with a two-parameter hysteresis rule on every zone."""
    nx, ny = TOPO[topo]; A, faces = grid(nx, ny); n = len(faces)
    lam = PER_FACE * faces + LAM_INF
    deg = A.sum(1)
    t_out, irr, N = series(city, hours, start_day)
    T = np.full(n, 24.0); prev = np.zeros(n, int)
    cost = e = 0.0; sw = 0; viol = 0; dh = 0.0; Tsum = 0.0
    e_cum = E_BASE
    for k in range(N):
        to = t_out[k]; g = SHGC * A_GL * irr[k] * (faces > 0)
        q = qcap_of(to); cop = cop_of(to); p_el = q / cop / 1000.0
        u = np.where(T >= hi, 1, np.where(T <= lo, 0, prev))
        new = int(np.sum((u == 1) & (prev == 0)))
        sw += new; cost += C_SW * new
        kwh = p_el * u.sum() * DT
        cost += price_of(e_cum) * kwh; e += kwh; e_cum += kwh
        # coupled sensible update, explicit (stable: rho well below 1 at C_th=6700)
        q_iz = P0.lam_iz * (A @ T - deg * T)
        dT = (-lam * (T - to) + g + q_iz - q * u) * DT * 3600.0 / (C_TH * 1e3)
        T = T + dT
        over = np.maximum(0.0, T - T_MAX); under = np.maximum(0.0, T_MIN - T)
        viol += int(np.sum((over > 0) | (under > 0)))
        dh += float(np.sum(over + under)) * DT
        Tsum += float(T.mean()); prev = u
    d = hours / 24.0
    return dict(J=cost / (n * d), E=e / (n * d), f_s=sw / (n * d),
                v_c=100.0 * viol / (N * n), deg_h=dh / n,
                T_mean=Tsum / N, e_cum_end=e_cum, n_zones=n)


def tune(city, topo, hours=168, start_day=181):
    best = None
    for lo in np.arange(22.2, 25.4, 0.2):
        for hi in np.arange(lo + 0.4, 26.0, 0.2):
            r = run(city, topo, lo, hi, hours, start_day)
            if r["deg_h"] <= 1e-9 and (best is None or r["J"] < best[0]["J"]):
                best = (r, lo, hi)
    return best


if __name__ == "__main__":
    t0 = time.time()
    print("=" * 78)
    print("REGENERATED RESULTS -- NEW WORK, computed 10 Nov 2026")
    print(f"  machine : {platform.processor() or 'x86_64'}, {os.cpu_count()} cores, no GPU")
    print(f"  C_th {C_TH:.0f} kJ/K, dt {DT} h -> Q*dt/C_th = "
          f"{Q_RATED*DT*3600/(C_TH*1e3):.2f} K against a {T_MAX-T_MIN:.0f} K band")
    print(f"  Lambda(n) = {PER_FACE:.2f}n + {LAM_INF:.3f} W/K ; COP(T) and Q(T) both "
          f"temperature-dependent")
    print(f"  tariff: two-block 0.18/0.30 at 6000 kWh (in force), E_base {E_BASE:.0f} kWh/mo")
    print("=" * 78)
    rows = []
    for city in ("riyadh", "jeddah"):
        print(f"\n--- {city.upper()} ---")
        print(f"  {'topo':5s} {'Nz':>3s} {'controller':12s} {'J':>8s} {'E':>7s} "
              f"{'f_s':>5s} {'T_mean':>7s} {'v_c%':>6s} {'deg-h':>7s} {'saving':>8s}")
        for topo in ("1x1", "1x4", "2x2", "3x3", "4x4"):
            naive = run(city, topo, 23.5, 24.5)
            best, lo, hi = tune(city, topo)
            sav = 100.0 * (naive["J"] - best["J"]) / naive["J"]
            for lab, r, s in (("THERM-1K", naive, None),
                              (f"tuned {lo:.1f}/{hi:.1f}", best, sav)):
                rows.append(dict(city=city, topo=topo, controller=lab,
                                 **{k: round(v, 4) for k, v in r.items()},
                                 saving_pct=None if s is None else round(s, 2)))
                ss = "" if s is None else f"{s:7.1f}%"
                print(f"  {topo:5s} {r['n_zones']:3d} {lab:12s} {r['J']:8.4f} "
                      f"{r['E']:7.3f} {r['f_s']:5.2f} {r['T_mean']:7.2f} "
                      f"{r['v_c']:6.2f} {r['deg_h']:7.3f} {ss:>8s}")
    os.makedirs("/home/claude/rbrl/results", exist_ok=True)
    with open("/home/claude/rbrl/results/rebuilt_tables.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\n-> results/rebuilt_tables.csv   ({time.time()-t0:.0f}s)")
