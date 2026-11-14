#!/usr/bin/env python3
"""Headroom study: which change to the PROBLEM raises the achievable saving.

Motivation
----------
The saving ratio reported by any controller is bounded above by the clairvoyant
DP optimum for the same problem instance. In the current instance (flat marginal
price, fixed 22-26 band, single zone, constant COP) that bound is small: the DP
beats a 3 K thermostat by 7-15% on cost and 2-14% on energy. No controller --
PPO, RBRL, MPC or anything else -- can exceed it. So "raise the saving ratio" is
not a question about the controller. It is a question about which feature of the
problem is suppressing the bound.

This module generalises the simulator and the DP to
  * a TIME-VARYING marginal price  price[k]
  * a TIME-VARYING comfort band    tmin[k], tmax[k]
and then measures the DP ceiling and the tuned-rule saving under each candidate
change, so each lever is quantified rather than asserted.

Self-checks (both must pass or the generalisation is wrong)
  I1  peak ratio 1.0 must reproduce the flat-price result to <1e-9
  I2  a constant band must reproduce the fixed-band result to <1e-9
"""
from __future__ import annotations
import sys, os, csv, argparse, functools
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
from hvac import Params, read_epw, vertical_irradiance

P0 = Params()
PER_FACE = P0.u_wall * P0.a_wall + P0.u_win * P0.a_gl
CITIES = {"riyadh": 24.7, "jeddah": 21.5, "taif": 21.483}
Q_HVAC, COP_RATED = 2000.0, 2.985
SHGC, A_GL = 0.25, 2.0
import config as _CFG      # F8: band, c_sw, AWAY_MAX, C_th, THERM_SET have ONE source (config.py)
C_SW = _CFG.C_SW
DT = _CFG.DT_H                 # h per control step (F23: config.DT_MIN / RBRL_DT_MIN; headline 0.25)
SPH = _CFG.STEPS_PER_HOUR      # steps per hour (the hourly EPW is held over SPH steps)
# Cycling energy penalty, kWh per compressor start. The manuscript's model has
# none: a start costs money (c_sw) but no energy, so switching reduction cannot
# show up as an energy saving. Real on/off DX equipment loses capacity during the
# start transient (refrigerant migration, oil return, coil re-wetting), which
# AHRI 210/240 represents with a part-load degradation coefficient. Setting this
# to p_el * t_start charges the transient as energy, which is the physically
# correct accounting and makes the energy saving independent of c_sw.
E_START = 0.0
R_AIR, VOL_Z, ACH_Z, CP_AIR = 287.055, 64.0, 0.6, 1005.0
P_STATION = {"riyadh": 94300.0, "jeddah": 101200.0, "taif": 85700.0}

# global DP grid must cover every band any scenario uses
G_LO, G_HI, N_GRID = 18.0, 34.0, 1601          # 10 mK


def lam_inf_of(city, T_ref=24.0):
    rho = P_STATION[city] / (R_AIR * (T_ref + 273.15))
    return ACH_Z * VOL_Z * rho * CP_AIR / 3600.0


def lam_of(faces, city):
    return PER_FACE * faces + lam_inf_of(city)


# Weather cache (RULING_round4 F3, SPEC_software Fix 2). The EPW used to be re-parsed and the
# irradiance re-transposed on every call (55 ms; rule_run called it twice). The arrays are now
# computed once per process and handed out READ-ONLY, so a caller that mutated them in place
# would raise instead of corrupting every later simulation. Results are bit-identical
# (tests/test_fast.py::test_series_cache_identical_and_readonly). rbrl_sb still monkeypatches
# series() at call time for AMY years; that path bypasses the cache and is unaffected.
@functools.lru_cache(maxsize=None)
def _epw(city):
    tdb, dni, dhi = read_epw(f"/home/claude/rbrl/{city}.epw")
    irr = vertical_irradiance(dni, dhi, CITIES[city], azimuth_deg=180.0)
    tdb.setflags(write=False); irr.setflags(write=False)
    return tdb, irr


@functools.lru_cache(maxsize=4096)
def _series(city, hours, start_day):
    tdb, irr = _epw(city)
    spd = SPH; N = int(round(hours / DT)); h0 = start_day * 24
    t = np.repeat(tdb[h0:h0 + hours], spd)[:N]
    g = np.repeat(irr[h0:h0 + hours], spd)[:N]
    t.setflags(write=False); g.setflags(write=False)
    return t, g, N


def series(city, hours, start_day):
    """(t_out, irr, N) at the control step for a window of `hours` from day `start_day`.
    The two arrays are shared and read-only: copy before modifying."""
    return _series(city, int(hours), int(start_day))


def hour_of(k):
    """Clock hour at step k, starting at midnight of the start day."""
    return (k * DT) % 24.0


# --------------------------------------------------------------- price profiles
def price_flat(N, p=0.18):
    return np.full(N, p)


def price_tou(N, mean_price=0.18, peak_ratio=3.0, peak=(13.0, 17.0)):
    """Revenue-neutral time-of-use: the ENERGY-WEIGHTED mean over a flat
    reference load equals mean_price, so a ToU scenario cannot raise the saving
    merely by being cheaper on average."""
    h = np.array([hour_of(k) for k in range(N)])
    is_peak = (h >= peak[0]) & (h < peak[1])
    f = is_peak.mean()
    # p_off * ((1-f) + f*ratio) = mean  ->  p_off
    p_off = mean_price / ((1.0 - f) + f * peak_ratio)
    return np.where(is_peak, p_off * peak_ratio, p_off)


# ---------------------------------------------------------------- band profiles
def band_fixed(N, lo=22.0, hi=26.0):
    return np.full(N, lo), np.full(N, hi)


def band_setback(N, lo=22.0, hi=26.0, away=(8.0, 15.0), lo_a=18.0, hi_a=32.0):
    h = np.array([hour_of(k) for k in range(N)])
    a = (h >= away[0]) & (h < away[1])
    return np.where(a, lo_a, lo), np.where(a, hi_a, hi)


def band_adaptive(city, N, hours, start_day, width=3.5):
    """ASHRAE 55 adaptive comfort, 80% acceptability:
       T_comf = 0.31*T_rm + 17.8,  band = T_comf +/- width,
    with T_rm the exponentially-weighted running mean outdoor temperature
    (alpha = 0.8) computed from the preceding week of the EPW."""
    tdb, _, _ = read_epw(f"/home/claude/rbrl/{city}.epw")
    daily = tdb.reshape(-1, 24).mean(axis=1)
    alpha = 0.8
    trm = np.zeros_like(daily); trm[0] = daily[0]
    for d in range(1, len(daily)):
        trm[d] = (1 - alpha) * daily[d - 1] + alpha * trm[d - 1]
    spd = SPH
    days = np.arange(N) // (24 * spd) + start_day
    tc = 0.31 * trm[days % len(daily)] + 17.8
    tc = np.clip(tc, 18.0, 30.5)                      # standard's applicability
    return tc - width, tc + width


# ------------------------------------------------------------------- simulation
def simulate(policy, city, faces, c_th, price, tmin, tmax,
             hours=168, start_day=181, T0=24.0, c_sw=C_SW):
    lam = lam_of(faces, city)
    t_out, irr, N = series(city, hours, start_day)
    decay = float(np.exp(-DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = Q_HVAC / COP_RATED / 1000.0
    T, prev = T0, 0
    cost = e = 0.0; sw = 0; viol = 0; dh = 0.0; Ts = []
    peak_kw = 0.0
    for k in range(N):
        u = int(policy(T, prev, k))
        if u == 1 and prev == 0:
            cost += c_sw + price[k] * E_START; sw += 1; e += E_START
        if u == 1:
            cost += price[k] * p_el * DT; e += p_el * DT
            peak_kw = max(peak_kw, p_el)
        T_inf = t_out[k] + (SHGC * A_GL * irr[k] - Q_HVAC * u) / lam
        T = T_inf + (T - T_inf) * decay
        if T > tmax[k] + 1e-9 or T < tmin[k] - 1e-9:
            viol += 1
            dh += max(0.0, T - tmax[k]) * DT + max(0.0, tmin[k] - T) * DT
        Ts.append(T); prev = u
    d = hours / 24.0
    borrowed = (T - T0) * c_th * 1e3 / 3.6e6 / COP_RATED
    cost += price[-1] * borrowed
    return dict(J=cost / d, E=e / d, f_s=sw / d, v_T=100.0 * viol / N,
                deg_h=dh, T_mean=float(np.mean(Ts)), T_end=T, peak_kw=peak_kw)


def hyst_band(a, b):
    """Hysteresis referred to the INSTANTANEOUS band: on at tmax-a, off at
    tmin+b. Reduces to a fixed deadband when the band is fixed."""
    def make(tmin, tmax):
        def pol(T, prev, k):
            if T >= tmax[k] - a: return 1
            if T <= tmin[k] + b: return 0
            return prev
        return pol
    return make


def tuned(city, faces, c_th, price, tmin, tmax, hours=168, start_day=181,
          c_sw=C_SW, step=0.1):
    best = None
    span = float(np.min(tmax - tmin))
    for a in np.arange(0.1, span - 0.15, step):
        for b in np.arange(0.1, span - a - 0.05, step):
            pol = hyst_band(a, b)(tmin, tmax)
            r = simulate(pol, city, faces, c_th, price, tmin, tmax,
                         hours, start_day, c_sw=c_sw)
            if r["deg_h"] > 1e-9: continue
            if best is None or r["J"] < best[0]["J"]:
                best = (r, a, b)
    return best


def dp(city, faces, c_th, price, tmin, tmax, hours=168, start_day=181,
       T0=24.0, c_sw=C_SW, n_grid=N_GRID):
    lam = lam_of(faces, city)
    t_out, irr, N = series(city, hours, start_day)
    decay = float(np.exp(-DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = Q_HVAC / COP_RATED / 1000.0
    Tg = np.linspace(G_LO, G_HI, n_grid); INF = np.inf
    term = price[-1] * (Tg - T0) * c_th * 1e3 / 3.6e6 / COP_RATED
    V = np.repeat(term[:, None], 2, axis=1)
    pol = np.zeros((N, n_grid, 2), np.int8)
    for k in range(N - 1, -1, -1):
        g = SHGC * A_GL * irr[k]
        run = price[k] * p_el * DT
        cand = np.full((n_grid, 2, 2), INF)
        for u in (0, 1):
            T_inf = t_out[k] + (g - Q_HVAC * u) / lam
            Tp = T_inf + (Tg - T_inf) * decay
            inside = (Tp >= tmin[k] - 1e-9) & (Tp <= tmax[k] + 1e-9)
            Vn = np.interp(np.clip(Tp, G_LO, G_HI), Tg, V[:, u])
            nxt = np.where(inside, run * u + Vn, INF)
            for up in (0, 1):
                s = (c_sw + price[k] * E_START) if (u == 1 and up == 0) else 0.0
                cand[:, up, u] = np.where(np.isfinite(nxt), s + nxt, INF)
        Vn2 = np.full((n_grid, 2), INF)
        for up in (0, 1):
            bu = np.argmin(np.nan_to_num(cand[:, up, :], nan=INF, posinf=1e300), axis=1)
            pol[k, :, up] = bu.astype(np.int8)
            Vn2[:, up] = cand[np.arange(n_grid), up, bu]
        V = Vn2
    i0 = int(np.argmin(np.abs(Tg - T0)))
    if not np.isfinite(V[i0, 0]):
        return None
    def pol_fn(T, prev, k):
        return int(pol[k, int(np.argmin(np.abs(Tg - T))), prev])
    r = simulate(pol_fn, city, faces, c_th, price, tmin, tmax,
                 hours, start_day, T0, c_sw)
    r["V_bwd"] = float(V[i0, 0]) / (hours / 24.0)
    # share of runtime inside the peak window, for reporting shift behaviour
    return r


def runtime_profile(policy, city, faces, c_th, price, tmin, tmax,
                    hours=168, start_day=181, T0=24.0):
    """Fraction of ON-steps falling in each price level."""
    lam = lam_of(faces, city)
    t_out, irr, N = series(city, hours, start_day)
    decay = float(np.exp(-DT * 3600.0 * lam / (c_th * 1e3)))
    T, prev = T0, 0
    on_by_level = {}
    for k in range(N):
        u = int(policy(T, prev, k))
        if u == 1:
            key = round(float(price[k]), 6)
            on_by_level[key] = on_by_level.get(key, 0) + 1
        T_inf = t_out[k] + (SHGC * A_GL * irr[k] - Q_HVAC * u) / lam
        T = T_inf + (T - T_inf) * decay
        prev = u
    tot = sum(on_by_level.values()) or 1
    return {k: 100.0 * v / tot for k, v in sorted(on_by_level.items())}


def coast_time_h(city, faces, c_th, band, hours=168, start_day=181):
    """Hours of free-float to traverse the band at the median and peak load."""
    lam = lam_of(faces, city)
    t_out, irr, _ = series(city, hours, start_day)
    load = np.maximum(0.0, (t_out - 24.0) * lam + SHGC * A_GL * irr)
    out = {}
    for lab, q in (("median", np.median(load)), ("95th pct", np.percentile(load, 95))):
        out[lab] = float(c_th * 1e3 * band / q / 3600.0) if q > 0 else float("inf")
    return out


# ------------------------------------------------------------------ COP model
# "const": COP fixed at the rating point (the headline model).
# "badescu": COP falls with the outdoor-indoor difference, using the R410A
# mini-split regression of Shen et al. as tabulated by Badescu (REHVA Journal
# 06/2025): COP = 4.0542 - 0.0852 dT, dT = T_out - T_in, T_in = 23 C here,
# rescaled so that COP equals COP_RATED at the AHRI rating difference
# (35 - 26.7 = 8.3 K). Capacity is held at Q_HVAC (a stated simplification).
import os as _os_cop
COP_MODEL = _os_cop.environ.get("RBRL_COP", "const")
TAG = _os_cop.environ.get("RBRL_TAG", "")
# Policy scenario controls (defaults reproduce the headline model exactly):
#   occupied comfort band [BAND_LO, BAND_HI] (22-24 C) and THERM's setpoint
#   THERM_SET (23 C; THERM cycles THERM_SET +/- 0.5). The national 24 C
#   guidance scenario uses BAND 21.5-24.5 (22-24 C with 0.5 K tolerance on each
#   side) and THERM_SET = 24.
BAND_SHIFT, BAND_LO, BAND_HI, THERM_SET = _CFG.BAND_SHIFT, _CFG.BAND_LO, _CFG.BAND_HI, _CFG.THERM_SET
THERM_C = THERM_SET
# empty-house safety limit (the setback level itself is chosen by each controller);
# 26/28/30 C sensitivity stands in for neighbour-zone considerations
AWAY_MAX = _CFG.AWAY_MAX
# Effective thermal capacitance of the zone, kJ/K (F21; ISO 13786 headline 4800). Scenario control
# for the capacity sweep J13: set RBRL_CTH (or --cth on t1_v2 / setback_arms, which sets it) and
# a non-empty RBRL_TAG (check_scenario_tag). final_tables.C_TH is this value; r3_dp / mpc_lambda
# must read it too (F9 developer).
C_TH_DEFAULT, C_TH = _CFG.C_TH_DEFAULT, _CFG.C_TH


DT_MIN, DT_MIN_DEFAULT = _CFG.DT_MIN, _CFG.DT_MIN_DEFAULT


def check_scenario_tag():
    """a non-default scenario must carry a tag, so it can never overwrite headline files (S17)."""
    if C_TH != C_TH_DEFAULT and not _os_cop.environ.get("RBRL_TAG", ""):
        raise SystemExit(f"RBRL_CTH={C_TH} is not the headline {C_TH_DEFAULT}: set RBRL_TAG")
    if DT_MIN != DT_MIN_DEFAULT and not _os_cop.environ.get("RBRL_TAG", ""):
        raise SystemExit(f"RBRL_DT_MIN={DT_MIN:g} is not the headline {DT_MIN_DEFAULT:g}: set RBRL_TAG")


def require_headline_dt(what):
    """modules whose step counts are still written for 15 min (setback lead grid, PPO observation)
    refuse a non-headline control interval instead of silently mis-scaling (F23)."""
    if DT_MIN != DT_MIN_DEFAULT:
        raise SystemExit(f"{what}: not Delta-t generic; RBRL_DT_MIN={DT_MIN:g} is not supported "
                         f"(headline {DT_MIN_DEFAULT:g} min only)")


def step_overshoot(dt_min=None, c_th=None):
    """Q_hvac * dt / C_th (K): the temperature drop of one full cooling step with no load (the
    deadband-form forcing condition of tab:s-timestep)."""
    dt_min = DT_MIN if dt_min is None else float(dt_min)
    c_th = C_TH if c_th is None else float(c_th)
    return Q_HVAC * dt_min * 60.0 / (c_th * 1e3)


def step_admissible(dt_min=None, c_th=None, deadband=1.0):
    """'yes' / 'marg.' / 'no': can THERM's deadband (1 K) hold one cooling step? A step that cools
    by more than the deadband overshoots it (tab:s-timestep "adm."; equality is marginal)."""
    ov = round(step_overshoot(dt_min, c_th), 9)
    return "yes" if ov < deadband else ("marg." if ov == deadband else "no")

_T_IN, _DT_RATING = 23.0, 8.3


def cop_series(t_out):
    """per-step COP for an outdoor temperature series."""
    t_out = np.asarray(t_out, float)
    if COP_MODEL == "const":
        return np.full(t_out.shape, COP_RATED)
    f = lambda d: 4.0542 - 0.0852 * d
    return COP_RATED * np.maximum(f(t_out - _T_IN), 0.5) / f(_DT_RATING)


# ------------------------------------------------- actual-year (ERA5) series
# Training-only weather: ERA5 reanalysis years (amy/<city>_<year>.csv, from the
# Open-Meteo archive), transposed to the same south-vertical plane. The years
# used for training exclude every year that supplies a cooling-season month to
# the TMYx test record, so no test weather is seen in training.
AMY_TRAIN_YEARS = {"riyadh": (2018, 2019, 2020, 2021, 2022),
                   "jeddah": (2017, 2018, 2020, 2021, 2023),
                   "taif": (2018, 2019, 2021, 2022, 2023)}
_AMY_CACHE = {}


def series_amy(city, year, hours, start_day):
    key = (city, year)
    if key not in _AMY_CACHE:
        import csv as _csv
        rows = list(_csv.DictReader(open(f"/home/claude/rbrl/amy/{city}_{year}.csv")))
        tdb = np.array([float(r["tdb_C"]) for r in rows])
        dni = np.array([float(r["dni_Wm2"]) for r in rows])
        dhi = np.array([float(r["dhi_Wm2"]) for r in rows])
        irr = vertical_irradiance(dni, dhi, CITIES[city], azimuth_deg=180.0)
        _AMY_CACHE[key] = (tdb, irr)
    tdb, irr = _AMY_CACHE[key]
    spd = SPH; N = int(round(hours / DT)); h0 = start_day * 24
    return (np.repeat(tdb[h0:h0 + hours], spd)[:N], np.repeat(irr[h0:h0 + hours], spd)[:N], N)
