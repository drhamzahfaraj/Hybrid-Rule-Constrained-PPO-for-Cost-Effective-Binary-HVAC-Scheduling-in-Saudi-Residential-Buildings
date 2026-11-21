#!/usr/bin/env python3
"""Full experimental programme for Revision 5. Writes CSV tables incrementally."""
from __future__ import annotations
import sys, os, json, time, csv, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hvac import *
from env import HVACEnv, Rules, run_policy, therm, always_on_floor
from train import load_city, split_indices, window_starts, train, eval_policy, agg

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)
DIM = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
COOL = {"riyadh": set(range(2, 10)), "jeddah": set(range(0, 12))}   # month idx


def month_of_day(d):
    c = 0
    for i, L in enumerate(DIM):
        if d < c + L:
            return i
        c += L
    return 11


def cooling_test_starts(city, dt, horizon_steps, days_needed):
    _, te, spd = split_indices(dt)
    te = np.array([d for d in te if month_of_day(d) in COOL[city]])
    return window_starts(te, spd, horizon_steps, days_needed), spd


def write(name, rows):
    if not rows:
        return
    p = os.path.join(OUT, name)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"  -> {name} ({len(rows)} rows)", flush=True)


def P15(**kw):
    return Params(dt=0.25, eps_lo=0.5, eps_hi=0.35, **kw)


# ============================================================ 1. baselines
def tab_baselines():
    print("\n[1] Thermostat family and reference controllers", flush=True)
    rows = []
    for city in ("riyadh", "jeddah"):
        to, ir = load_city(city)
        for topo in ("1x1", "1x4", "2x2", "3x3", "4x4"):
            P = P15(); m = HVACModel(topo, P)
            H = 7 * int(round(24 / P.dt))
            st, spd = cooling_test_starts(city, P.dt, H, 7)
            for lab, fn, cc in (("THERM-1K", therm(1.0), False),
                                ("THERM-2K", therm(2.0), False),
                                ("THERM-3K", therm(3.0), False),
                                ("THERM-full", therm(3.15), True),
                                ("HOLD-Tmax", always_on_floor(), False)):
                env = HVACEnv(m, to, ir, st, cost_model="S", horizon=H,
                              P=P, rules=Rules(P, use_cc=cc))
                a = agg([run_policy(env, fn, start=int(s)) for s in st[:30]])
                rows.append(dict(city=city, topo=topo, controller=lab,
                                 **{k: round(v, 4) for k, v in a.items()}))
            print(f"    {city} {topo} done", flush=True)
    write("baselines.csv", rows)
    return rows


# ============================================================ 2. integrator
def tab_integrator():
    print("\n[2] Integrator and time-step study (reviewer comment 8)", flush=True)
    rows = []
    for topo in ("1x1", "4x4"):
        for cth in (77.2, 500.0, 1200.0, 4800.0):
            for dtm in (60, 30, 15, 5):
                dt = dtm / 60.0
                P = Params(dt=dt, c_th=cth,
                           eps_lo=min(1.9, 2000 * dt * 3600 / (cth * 1e3) + 0.1),
                           eps_hi=min(1.9, 0.85 * dt * (4800 / cth) + 0.15))
                m = HVACModel(topo, P)
                rho = m.euler_spectral_radius(dt)
                tt = m.taus()
                rows.append(dict(topo=topo, c_th=cth, dt_min=dtm,
                                 tau_fast_h=round(float(tt.min()), 3),
                                 tau_slow_h=round(float(tt.max()), 3),
                                 dt_over_tau_fast=round(dt / float(tt.min()), 3),
                                 euler_spectral_radius=round(rho, 4),
                                 euler_stable=bool(rho < 1.0),
                                 guard_lo=round(P.eps_lo, 2), guard_hi=round(P.eps_hi, 2),
                                 free_band_K=round(4.0 - P.eps_lo - P.eps_hi, 2),
                                 band_holdable=bool(4.0 - P.eps_lo - P.eps_hi > 0)))
    write("integrator.csv", rows)
    # consequences at a fixed controller
    rows2 = []
    to, ir = load_city("riyadh")
    for cth in (77.2, 1200.0, 4800.0):
        for dtm, integ in ((60, "euler"), (60, "exact"), (15, "euler"), (15, "exact")):
            dt = dtm / 60.0
            P = Params(dt=dt, c_th=cth,
                       eps_lo=min(1.9, 2000 * dt * 3600 / (cth * 1e3) + 0.1),
                       eps_hi=min(1.9, 0.85 * dt * (4800 / cth) + 0.15))
            m = HVACModel("4x4", P)
            spd = int(round(24 / dt))
            t2 = np.repeat(read_epw("riyadh.epw")[0], spd // 24 if spd >= 24 else 1)
            i2 = np.repeat(vertical_irradiance(*read_epw("riyadh.epw")[1:], 24.7),
                           spd // 24 if spd >= 24 else 1)
            env = HVACEnv(m, t2, i2, [181 * spd], cost_model="S",
                          horizon=30 * spd, P=P, rules=Rules(P), integrator=integ)
            try:
                a = run_policy(env, therm(min(3.15, 4.0 - P.eps_lo - P.eps_hi)))
                rows2.append(dict(c_th=cth, dt_min=dtm, integrator=integ,
                                  **{k: round(v, 4) for k, v in a.items()}))
            except Exception as e:
                rows2.append(dict(c_th=cth, dt_min=dtm, integrator=integ,
                                  J_per_zone_day=float("nan"), note=str(e)[:40]))
    write("integrator_consequences.csv", rows2)
    return rows, rows2


# ============================================================ 3. tariffs
def tab_tariffs():
    print("\n[3] Cost models and tariff vintages (reviewer comment 6)", flush=True)
    rows = []
    for city in ("riyadh", "jeddah"):
        to, ir = load_city(city)
        P = P15(); m = HVACModel("4x4", P)
        H = 30 * int(round(24 / P.dt))             # monthly
        st, spd = cooling_test_starts(city, P.dt, H, 30)
        if len(st) == 0:
            # A 30-day window cannot fit inside a 10-day test block. Use the
            # 168-h held-out windows and scale to a billing month instead, so
            # no evaluation touches a training day.
            H = 7 * int(round(24 / P.dt))
            st, spd = cooling_test_starts(city, P.dt, H, 7)
        for cm, lab in (("L", "Linear 0.12"), ("E", "Exponential"),
                        ("S", "Four-tier 2016-17"), ("C", "Two-block 2018-26"),
                        ("C27", "Two-block 2027")):
            for ctrl, fn, cc in (("THERM-1K", therm(1.0), False),
                                 ("THERM-full", therm(3.15), True)):
                env = HVACEnv(m, to, ir, st, cost_model=cm, horizon=H,
                              P=P, rules=Rules(P, use_cc=cc))
                a = agg([run_policy(env, fn, start=int(s)) for s in st[:6]])
                rows.append(dict(city=city, cost_model=cm, tariff=lab,
                                 controller=ctrl, **{k: round(v, 4) for k, v in a.items()}))
        print(f"    {city} done", flush=True)
    write("tariffs.csv", rows)
    return rows


# ============================================================ 4. capacity
def tab_capacity():
    print("\n[4] Thermal-capacity sensitivity (reviewer comment 2)", flush=True)
    rows = []
    to, ir = load_city("riyadh")
    for cth in (1200, 2000, 3200, 4800, 6400):
        dt = 0.25
        P = Params(dt=dt, c_th=cth,
                   eps_lo=2000 * dt * 3600 / (cth * 1e3) + 0.1,
                   eps_hi=0.85 * dt * (4800 / cth) + 0.15)
        m = HVACModel("4x4", P)
        H = 7 * int(round(24 / dt))
        st, spd = cooling_test_starts("riyadh", dt, H, 7)
        for ctrl, fn, cc in (("THERM-1K", therm(1.0), False),
                             ("THERM-full", therm(3.15), True)):   # FIXED band, not guard-dependent
            env = HVACEnv(m, to, ir, st, cost_model="S", horizon=H, P=P,
                          rules=Rules(P, use_cc=cc))
            a = agg([run_policy(env, fn, start=int(s)) for s in st[:20]])
            rows.append(dict(c_th=cth, controller=ctrl,
                             free_band_K=round(4.0 - P.eps_lo - P.eps_hi, 2),
                             **{k: round(v, 4) for k, v in a.items()}))
    write("capacity.csv", rows)
    return rows


# ============================================================ 5. switching cost
def tab_csw():
    print("\n[5] Switching-cost sweep", flush=True)
    rows = []
    to, ir = load_city("riyadh")
    for csw in (0.0, 0.05, 0.15, 0.30, 0.60):
        P = P15(c_sw=csw); m = HVACModel("4x4", P)
        H = 7 * int(round(24 / P.dt))
        st, spd = cooling_test_starts("riyadh", P.dt, H, 7)
        for ctrl, fn, cc in (("THERM-1K", therm(1.0), False),
                             ("THERM-full", therm(3.15), True)):
            env = HVACEnv(m, to, ir, st, cost_model="S", horizon=H, P=P,
                          rules=Rules(P, use_cc=cc))
            a = agg([run_policy(env, fn, start=int(s)) for s in st[:20]])
            rows.append(dict(c_sw=csw, controller=ctrl,
                             **{k: round(v, 4) for k, v in a.items()}))
    write("csw_sweep.csv", rows)
    return rows


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()
    if which in ("all", "base"): tab_baselines()
    if which in ("all", "integ"): tab_integrator()
    if which in ("all", "tariff"): tab_tariffs()
    if which in ("all", "cap"): tab_capacity()
    if which in ("all", "csw"): tab_csw()
    print(f"\ndone in {time.time()-t0:.0f}s", flush=True)
