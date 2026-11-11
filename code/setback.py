#!/usr/bin/env python3
"""Occupancy setback with an occupied band capped at 24 C, iso-comfort matched.

Why this configuration
----------------------
Author constraint (2026-11-10): "it is too hot to have more than 24 in Saudi
Arabia once occupied". So the occupied band is 22-24 C, not 22-26 C. This is a
2 K window, half the manuscript's, and it changes three things at once:

  * less usable storage while occupied (0.89 kWh_e against 1.79)
  * a deeper gap between the occupied band and the free-float away band, so the
    setback opportunity is LARGER
  * a harder recovery: the unit must pull the zone back into a 2 K window before
    occupancy resumes, which the manuscript's undersized 2 kW unit may not be
    able to do. Capacity therefore becomes decisive here, although it was
    irrelevant at a fixed 22-26 band.

Comfort accounting
------------------
Degree-hours are counted ONLY while occupied. An unoccupied zone has nobody to
be uncomfortable, which is the entire basis of setback and must be stated.

Iso-comfort matching
--------------------
A cost comparison between two controllers is meaningless if they deliver
different mean temperatures: the cheaper one may simply be running warmer. So
every arm here is tuned to deliver the SAME mean OCCUPIED zone temperature as
the THERM baseline, within 0.05 K. For the rule this is a search over switch
points; for the optimum it is a bisection on the band ceiling it is allowed to
use. The residual cost difference is then attributable to scheduling alone.

Invariant: with occupancy set to all-occupied and the band to 22-26, sim() must
reproduce headroom.simulate() exactly.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys
sys.path.insert(0, _ROOT + "")
import numpy as np
import headroom as H

DT = H.DT
G_LO, G_HI, N_GRID = 16.0, 38.0, 2201        # 10 mK, covers deep free-float


# ------------------------------------------------------------------- schedule
def occupancy(N, away=(8.0, 14.0), workdays=(0, 1, 2, 3, 4), start_dow=0):
    """True while occupied. Saudi working week is Sunday-Thursday; the 168-h
    window is declared to start on a Sunday (start_dow=0). Friday and Saturday
    are occupied all day."""
    k = np.arange(N)
    hour = (k * DT) % 24.0
    dow = ((k * DT) // 24.0 + start_dow).astype(int) % 7
    is_work = np.isin(dow, workdays)
    return ~(is_work & (hour >= away[0]) & (hour < away[1]))


def bands(occ, occ_lo=22.0, occ_hi=24.0, away_lo=18.0, away_hi=30.0):
    lo = np.where(occ, occ_lo, away_lo)
    hi = np.where(occ, occ_hi, away_hi)
    return lo, hi


# ----------------------------------------------------------------- simulation
def sim(policy, city, faces, c_th, price, lo, hi, occ,
        hours=168, start_day=181, T0=23.0, c_sw=H.C_SW, q_hvac=None, cop=None):
    q = H.Q_HVAC if q_hvac is None else q_hvac
    cp = H.COP_RATED if cop is None else cop
    lam = H.lam_of(faces, city)
    t_out, irr, N = H.series(city, hours, start_day)
    decay = float(np.exp(-DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = q / cp / 1000.0
    T, prev = T0, 0
    cost = e = 0.0; sw = 0; viol = 0; dh = 0.0
    Tocc = []
    for k in range(N):
        u = int(policy(T, prev, k))
        if u == 1 and prev == 0:
            cost += c_sw + price[k] * H.E_START; sw += 1; e += H.E_START
        if u == 1:
            cost += price[k] * p_el * DT; e += p_el * DT
        T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - q * u) / lam
        T = T_inf + (T - T_inf) * decay
        if occ[k]:
            Tocc.append(T)
            if T > hi[k] + 1e-9 or T < lo[k] - 1e-9:
                viol += 1
                dh += max(0.0, T - hi[k]) * DT + max(0.0, lo[k] - T) * DT
        prev = u
    d = hours / 24.0
    cost += price[-1] * (T - T0) * c_th * 1e3 / 3.6e6 / cp
    return dict(J=cost / d, E=e / d, f_s=sw / d, deg_h_occ=dh,
                v_occ=100.0 * viol / max(1, len(Tocc)),
                T_mean_occ=float(np.mean(Tocc)) if Tocc else float("nan"),
                T_end=T)


def dp(city, faces, c_th, price, lo, hi, occ, hours=168, start_day=181,
       T0=23.0, c_sw=H.C_SW, q_hvac=None, cop=None, n_grid=N_GRID):
    """Clairvoyant optimum. Comfort enforced only on occupied steps."""
    q = H.Q_HVAC if q_hvac is None else q_hvac
    cp = H.COP_RATED if cop is None else cop
    lam = H.lam_of(faces, city)
    t_out, irr, N = H.series(city, hours, start_day)
    decay = float(np.exp(-DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = q / cp / 1000.0
    Tg = np.linspace(G_LO, G_HI, n_grid); INF = np.inf
    V = np.repeat((price[-1] * (Tg - T0) * c_th * 1e3 / 3.6e6 / cp)[:, None], 2, axis=1)
    pol = np.zeros((N, n_grid, 2), np.int8)
    for k in range(N - 1, -1, -1):
        g = H.SHGC * H.A_GL * irr[k]
        run = price[k] * p_el * DT
        swc = c_sw + price[k] * H.E_START
        cand = np.full((n_grid, 2, 2), INF)
        for u in (0, 1):
            T_inf = t_out[k] + (g - q * u) / lam
            Tp = T_inf + (Tg - T_inf) * decay
            ok = ((Tp >= lo[k] - 1e-9) & (Tp <= hi[k] + 1e-9)) if occ[k] \
                 else ((Tp >= G_LO) & (Tp <= G_HI))
            Vn = np.interp(np.clip(Tp, G_LO, G_HI), Tg, V[:, u])
            nxt = np.where(ok, run * u + Vn, INF)
            for up in (0, 1):
                s = swc if (u == 1 and up == 0) else 0.0
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
    r = sim(pol_fn, city, faces, c_th, price, lo, hi, occ, hours, start_day,
            T0, c_sw, q, cp)
    r["V_bwd"] = float(V[i0, 0]) / (hours / 24.0)
    return r


# ------------------------------------------------------------- rule families
def therm(lo, hi):
    """The manuscript's THERM: on at hi-0.5, off at lo+0.5, band-referred."""
    def pol(T, prev, k):
        if T >= hi[k] - 0.5: return 1
        if T <= lo[k] + 0.5: return 0
        return prev
    return pol


def hyst_abs(on_at, off_at):
    """Absolute switch points, ignoring the away band entirely: the honest
    'thermostat with no occupancy awareness' comparator."""
    def pol(T, prev, k):
        if T >= on_at: return 1
        if T <= off_at: return 0
        return prev
    return pol


def sched_rule(on_at, off_at, occ, lead_steps, on_away, off_away):
    """Occupancy-aware rule: setback points while away, with a fixed-lead
    recovery before occupancy resumes. This is the fair rule-based comparator
    for a setback schedule -- a thermostat that knows the schedule but does not
    optimise against weather or price."""
    occ_arr = np.asarray(occ)
    N = len(occ_arr)
    # recovery starts lead_steps before each occupied run begins
    recover = np.zeros(N, bool)
    for k in range(1, N):
        if occ_arr[k] and not occ_arr[k - 1]:
            recover[max(0, k - lead_steps):k] = True
    def pol(T, prev, k):
        if occ_arr[k] or recover[k]:
            if T >= on_at: return 1
            if T <= off_at: return 0
        else:
            if T >= on_away: return 1
            if T <= off_away: return 0
        return prev
    return pol
