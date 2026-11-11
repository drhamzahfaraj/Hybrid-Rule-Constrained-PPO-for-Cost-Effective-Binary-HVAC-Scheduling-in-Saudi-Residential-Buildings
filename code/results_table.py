#!/usr/bin/env python3
"""Replacement results table: three cities, documented parameters, DP-bounded.

This generates NEW results. It does not repair the withdrawn tables and must not
be presented as doing so. Every figure here is produced by this script from the
stated parameters and the bundled TMYx EPW files.

Design decisions, each stated because each is a place a referee will look:

* Integration is exact (matrix exponential on the sensible node), so no
  discretisation claim is needed.
* Envelope conductance is affine in exposed faces: Lambda(n) = 11.90n + 12.864
  W/K, the second term being infiltration at 0.6 ACH. The previous version's
  multiplicative form was wrong.
* The feasibility condition Q_hvac*dt/C_th <= band width must hold or no policy
  can keep the zone in band. At dt = 15 min this requires C_th >= 450 kJ/K.
  The headline capacity is 4800 kJ/K (ISO 13786 areal heat capacity, 96 m2 of
  participating surface at 50 kJ/m2K for a furnished heavy-construction room),
  which satisfies it with a factor of 10.7 margin. A sweep is reported.
* The tariff is the schedule IN FORCE: two-block, 0.18 SAR/kWh to 6,000
  kWh/month then 0.30. For this dwelling the boundary is never crossed, so the
  marginal price is CONSTANT and no tier-timing incentive exists. The pre-2018
  four-tier schedule is reported as a labelled counterfactual, not as current.
* Mean zone temperature is a first-class column. Without it a cost comparison
  between two controllers cannot be distinguished from a setpoint difference.
* The DP optimum is CLAIRVOYANT: it sees the whole weather trajectory. Any
  implementable causal controller achieves strictly less, so the gap to it is a
  lower bound on what is left for control, not an achievable target.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, os, csv, argparse, itertools
sys.path.insert(0, _ROOT + "")
import numpy as np
from hvac import Params, read_epw, vertical_irradiance

P0 = Params()
PER_FACE = P0.u_wall * P0.a_wall + P0.u_win * P0.a_gl      # 11.90 W/K
LAM_INF = P0.lam_inf                                        # 12.864 W/K
CITIES = {"riyadh": 24.7, "jeddah": 21.5, "taif": 21.483}
LAT_ELEV = {"riyadh": 635, "jeddah": 15, "taif": 1478}

TMIN, TMAX = 22.0, 26.0
Q_HVAC, COP_RATED = 2000.0, 2.985
SHGC, A_GL = 0.25, 2.0
C_SW = 0.15
DT = 0.25
BAND = TMAX - TMIN


# Infiltration conductance depends on air density and therefore on station
# pressure, so it is per-city. Taif sits at 1478 m / 85.7 kPa, where air is 15%
# less dense than at Jeddah's sea level: using one value for all three cities
# overstates Taif's load by 19%.
R_AIR, VOL_Z, ACH_Z, CP_AIR = 287.055, 64.0, 0.6, 1005.0
P_STATION = {"riyadh": 94300.0, "jeddah": 101200.0, "taif": 85700.0}

def lam_inf_of(city, T_ref=24.0):
    rho = P_STATION[city] / (R_AIR * (T_ref + 273.15))
    return ACH_Z * VOL_Z * rho * CP_AIR / 3600.0

def lam_of(faces, city="riyadh"):
    return PER_FACE * faces + lam_inf_of(city)


def tariff(kind):
    """Marginal price in SAR/kWh. Constant for this dwelling under both
    in-force blocks, so returned as a scalar with the regime named."""
    return {"inforce": 0.18, "historical": 0.05, "flat012": 0.12}[kind]


def series(city, hours, start_day):
    lat = CITIES[city]
    tdb, dni, dhi = read_epw(f"{_ROOT}/{city}.epw")
    irr = vertical_irradiance(dni, dhi, lat, azimuth_deg=180.0)
    spd = int(round(1.0 / DT)); N = int(round(hours / DT)); h0 = start_day * 24
    return (np.repeat(tdb[h0:h0 + hours], spd)[:N],
            np.repeat(irr[h0:h0 + hours], spd)[:N], N)


def simulate(policy, city, faces, c_th, price, hours=168, start_day=181, T0=24.0):
    lam = lam_of(faces, city)
    t_out, irr, N = series(city, hours, start_day)
    decay = float(np.exp(-DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = Q_HVAC / COP_RATED / 1000.0
    T, prev = T0, 0
    cost = e = 0.0; sw = 0; viol = 0; dh = 0.0; Ts = []
    for k in range(N):
        u = int(policy(T, prev, k))
        if u == 1 and prev == 0: cost += C_SW; sw += 1
        if u == 1: cost += price * p_el * DT; e += p_el * DT
        T_inf = t_out[k] + (SHGC * A_GL * irr[k] - Q_HVAC * u) / lam
        T = T_inf + (T - T_inf) * decay
        if T > TMAX or T < TMIN:
            viol += 1
            dh += max(0.0, T - TMAX) * DT + max(0.0, TMIN - T) * DT
        Ts.append(T); prev = u
    d = hours / 24.0
    # Terminal correction. A controller that finishes warmer than it started has
    # borrowed thermal storage it never paid to remove; one that finishes cooler
    # has paid for storage it does not use. Both are end-of-horizon artefacts and
    # neither is a control result. Charge or credit the difference at the same
    # price, so every controller is compared on a common energy basis. Without
    # this a hysteresis rule appears to beat a terminal-constrained optimum: the
    # tuned rules below finish 1.2-1.7 K warm, worth 0.013-0.020 SAR/day, which
    # is the same order as the gaps being measured.
    borrowed_kwh_e = (T - T0) * c_th * 1e3 / 3.6e6 / COP_RATED
    cost_corr = cost + price * borrowed_kwh_e
    return dict(J=cost_corr / d, J_uncorrected=cost / d, E=e / d, f_s=sw / d,
                v_T=100.0 * viol / N, deg_h=dh, T_mean=float(np.mean(Ts)),
                T_end=T, terminal_corr=price * borrowed_kwh_e / d)


def hyst(lo, hi):
    def pol(T, prev, k):
        return 1 if T >= hi else (0 if T <= lo else prev)
    return pol


def tuned(city, faces, c_th, price, hours=168, start_day=181, feasible_only=True):
    """2-D search over asymmetric switch points; zero degree-hours required."""
    best = None
    for lo in np.arange(TMIN + 0.1, TMAX - 0.4, 0.1):
        for hi in np.arange(lo + 0.2, TMAX - 0.05, 0.1):
            r = simulate(hyst(lo, hi), city, faces, c_th, price, hours, start_day)
            if feasible_only and r["deg_h"] > 1e-9:
                continue
            if best is None or r["J"] < best[0]["J"]:
                best = (r, lo, hi)
    return best


def dp_optimum(city, faces, c_th, price, hours=168, start_day=181,
               n_grid=401, T0=24.0):
    """Clairvoyant lower bound. Grid on the band; one-sided terminal condition."""
    lam = lam_of(faces, city)
    t_out, irr, N = series(city, hours, start_day)
    decay = float(np.exp(-DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = Q_HVAC / COP_RATED / 1000.0
    run = price * p_el * DT
    Tg = np.linspace(TMIN, TMAX, n_grid); INF = np.inf
    # Terminal value = the economic value of the final thermal state, so the DP
    # optimises exactly the terminally-corrected objective that simulate()
    # reports. A hard end constraint was tried first and is wrong: it forces the
    # DP to buy end-of-horizon cooling that the comparator rules never pay for,
    # which made a tuned rule appear to beat the optimum in the humid case.
    term = price * (Tg - T0) * c_th * 1e3 / 3.6e6 / COP_RATED
    V = np.repeat(term[:, None], 2, axis=1)
    pol = np.zeros((N, n_grid, 2), np.int8)
    for k in range(N - 1, -1, -1):
        g = SHGC * A_GL * irr[k]
        cand = np.full((n_grid, 2, 2), INF)
        for u in (0, 1):
            T_inf = t_out[k] + (g - Q_HVAC * u) / lam
            Tp = T_inf + (Tg - T_inf) * decay
            inside = (Tp >= TMIN - 1e-9) & (Tp <= TMAX + 1e-9)
            Vn = np.interp(np.clip(Tp, TMIN, TMAX), Tg, V[:, u])
            nxt = np.where(inside, run * u + Vn, INF)
            for up in (0, 1):
                sw = C_SW if (u == 1 and up == 0) else 0.0
                cand[:, up, u] = np.where(np.isfinite(nxt), sw + nxt, INF)
        Vn2 = np.full((n_grid, 2), INF)
        for up in (0, 1):
            bu = np.argmin(np.nan_to_num(cand[:, up, :], nan=INF, posinf=1e300), axis=1)
            pol[k, :, up] = bu.astype(np.int8)
            Vn2[:, up] = cand[np.arange(n_grid), up, bu]
        V = Vn2
    V0 = float(V[int(np.argmin(np.abs(Tg - T0))), 0])
    if not np.isfinite(V0):
        return None
    def pol_fn(T, prev, k):
        return int(pol[k, int(np.argmin(np.abs(Tg - T))), prev])
    r = simulate(pol_fn, city, faces, c_th, price, hours, start_day, T0)
    r["V_bwd"] = V0 / (hours / 24.0)
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--c_th", type=float, default=4800.0)
    ap.add_argument("--faces", type=int, default=1)
    ap.add_argument("--tariff", default="inforce")
    ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args()
    price = tariff(a.tariff)
    print(f"Replacement results. C_th = {a.c_th:.0f} kJ/K, dt = {DT*60:.0f} min, "
          f"exact integration, {a.faces} exposed face(s), tariff = {a.tariff} "
          f"({price} SAR/kWh constant)")
    print(f"Feasibility: Q*dt/C_th = {Q_HVAC*DT*3600/(a.c_th*1e3):.3f} K against a "
          f"{BAND:.1f} K band -> {'OK' if Q_HVAC*DT*3600/(a.c_th*1e3)<=BAND else 'VIOLATED'}\n")

    if a.sweep:
        print("Thermal-capacity sensitivity (answer to comment 2), Riyadh, tuned rule:")
        print(f"  {'C_th':>7s} {'Q*dt/C':>8s} {'feasible':>9s} {'J':>8s} {'E':>7s} "
              f"{'f_s':>5s} {'T_mean':>7s} {'DP J*':>8s} {'gap':>7s}")
        for C in (450, 600, 1200, 2400, 4800, 6700, 9600):
            fc = Q_HVAC * DT * 3600 / (C * 1e3)
            t = tuned("riyadh", a.faces, C, price)
            d = dp_optimum("riyadh", a.faces, C, price)
            if t is None or d is None:
                print(f"  {C:7.0f} {fc:8.3f} {'-':>9s}   no feasible rule"); continue
            print(f"  {C:7.0f} {fc:8.3f} {'yes' if fc<=BAND else 'NO':>9s} "
                  f"{t[0]['J']:8.4f} {t[0]['E']:7.3f} {t[0]['f_s']:5.2f} "
                  f"{t[0]['T_mean']:7.2f} {d['J']:8.4f} "
                  f"{100*(t[0]['J']-d['J'])/d['J']:+6.2f}%")
        raise SystemExit

    rows = []
    print(f"{'city':8s} {'controller':22s} {'J':>8s} {'E':>7s} {'f_s':>5s} "
          f"{'T_mean':>7s} {'v_T%':>6s} {'deg-h':>7s} {'gap to DP':>10s}")
    for city in ("riyadh", "jeddah", "taif"):
        d = dp_optimum(city, a.faces, a.c_th, price)
        for lab, pol in (("THERM 1 K deadband", hyst(23.5, 24.5)),
                         ("THERM 2 K deadband", hyst(23.0, 25.0)),
                         ("THERM 3 K deadband", hyst(22.5, 25.5))):
            r = simulate(pol, city, a.faces, a.c_th, price)
            rows.append(dict(city=city, controller=lab, **{k: round(v, 4) for k, v in r.items()}))
            print(f"{city:8s} {lab:22s} {r['J']:8.4f} {r['E']:7.3f} {r['f_s']:5.2f} "
                  f"{r['T_mean']:7.2f} {r['v_T']:6.2f} {r['deg_h']:7.3f} "
                  f"{100*(r['J']-d['J'])/d['J']:+9.2f}%")
        t = tuned(city, a.faces, a.c_th, price)
        rows.append(dict(city=city, controller=f"tuned rule ({t[1]:.1f},{t[2]:.1f})",
                         **{k: round(v, 4) for k, v in t[0].items()}))
        print(f"{city:8s} {'tuned rule (%.1f,%.1f)'%(t[1],t[2]):22s} {t[0]['J']:8.4f} "
              f"{t[0]['E']:7.3f} {t[0]['f_s']:5.2f} {t[0]['T_mean']:7.2f} "
              f"{t[0]['v_T']:6.2f} {t[0]['deg_h']:7.3f} "
              f"{100*(t[0]['J']-d['J'])/d['J']:+9.2f}%")
        rows.append(dict(city=city, controller="DP optimum (clairvoyant)",
                         **{k: round(v, 4) for k, v in d.items() if k != 'V_bwd'}))
        print(f"{city:8s} {'DP optimum (clairvoyant)':22s} {d['J']:8.4f} {d['E']:7.3f} "
              f"{d['f_s']:5.2f} {d['T_mean']:7.2f} {d['v_T']:6.2f} {d['deg_h']:7.3f} "
              f"{'--':>10s}   [V_bwd {d['V_bwd']:.4f}]")
        print()
    os.makedirs(_ROOT + "/results", exist_ok=True)
    with open(_ROOT + "/results/replacement_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    print("-> results/replacement_table.csv")
