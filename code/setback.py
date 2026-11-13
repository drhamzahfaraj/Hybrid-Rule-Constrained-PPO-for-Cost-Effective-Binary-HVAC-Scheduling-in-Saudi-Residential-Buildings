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
import sys
sys.path.insert(0, "/home/claude/rbrl")
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
        hours=168, start_day=181, T0=23.0, c_sw=H.C_SW, q_hvac=None, cop=None,
        t_min=None, record=False):
    """Simulate one arm. Comfort is scored on the post-step state T_{k+1} with
    the step-k occupancy and band (ruling round 4, Sec. 2.1). Metrics:
      deg_h_over       occupied sum max(0, T' - hi)*dt                (upper)
      deg_h_cmd_under  sum over COOLING steps (u=1), occupied or away, of
                       max(0, t_min - T')*dt: cooling-caused under-temperature
                       (the corrected cold rule says this must be 0)
      deg_h_ff_under   the same over u=0 (free-float) steps, occupied only
      deg_h_under      plain occupied under-temperature (= cmd + ff, occupied)
      deg_h_occ        deg_h_over + deg_h_under (legacy)
      T_end, T_max_away (nan when there are no away steps)
    t_min defaults to the occupied lower limit of the caller's band (lo on
    occupied steps). record=True adds r["u"], r["T_next"] (per-step arrays)
    for in_domain()."""
    q = H.Q_HVAC if q_hvac is None else q_hvac
    cp = H.COP_RATED if cop is None else cop
    lam = H.lam_of(faces, city)
    t_out, irr, N = H.series(city, hours, start_day)
    decay = float(np.exp(-DT * 3600.0 * lam / (c_th * 1e3)))
    p_el_k = q / (H.cop_series(t_out) if cop is None else np.full(N, cp)) / 1000.0
    occ_a = np.asarray(occ, bool)
    if t_min is None:
        t_min = float(np.max(np.asarray(lo)[occ_a[:len(lo)]])) if occ_a.any() else H.BAND_LO
    T, prev = T0, 0
    cost = e = 0.0; sw = 0; viol = 0; dh = 0.0
    Tocc = []; Tclip = []; dh_over = dh_under = 0.0
    dh_cmd = dh_ff = 0.0; T_max_away = -np.inf; n_away = 0
    U = []; TN = []
    for k in range(N):
        u = int(policy(T, prev, k))
        if u == 1 and prev == 0:
            cost += c_sw + price[k] * H.E_START; sw += 1; e += H.E_START
        if u == 1:
            cost += price[k] * p_el_k[k] * DT; e += p_el_k[k] * DT
        T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - q * u) / lam
        T = T_inf + (T - T_inf) * decay
        if record:
            U.append(u); TN.append(T)
        if u == 1:
            dh_cmd += max(0.0, t_min - T - 1e-9) * DT
        if occ[k]:
            Tocc.append(T)
            Tclip.append(max(T, lo[k]))      # Rule B: cold excursions buy no warm credit
            dh_over += max(0.0, T - hi[k] - 1e-9) * DT
            dh_under += max(0.0, lo[k] - T - 1e-9) * DT
            if u == 0:
                dh_ff += max(0.0, t_min - T - 1e-9) * DT
            if T > hi[k] + 1e-9 or T < lo[k] - 1e-9:
                viol += 1
                dh += max(0.0, T - hi[k]) * DT + max(0.0, lo[k] - T) * DT
        else:
            n_away += 1
            T_max_away = max(T_max_away, T)
        prev = u
    d = hours / 24.0
    cost += price[-1] * (T - T0) * c_th * 1e3 / 3.6e6 / cp
    out = dict(J=cost / d, E=e / d, f_s=sw / d, deg_h_occ=dh,
               v_occ=100.0 * viol / max(1, len(Tocc)),
               T_mean_occ=float(np.mean(Tocc)) if Tocc else float("nan"),
               T_mean_occ_clip=float(np.mean(Tclip)) if Tclip else float("nan"),
               deg_h_over=dh_over, deg_h_under=dh_under,
               deg_h_cmd_under=dh_cmd, deg_h_ff_under=dh_ff,
               T_max_away=float(T_max_away) if n_away else float("nan"),
               T_end=T)
    if record:
        out["u"] = np.array(U, np.int8); out["T_next"] = np.array(TN)
    return out


def in_domain(u, T_next, occ, hi, t_min=None, away_max=None, tol=1e-9):
    """Is an arm's realised trajectory inside the feasible set D of the DP /
    MPC / bound (ruling round 4, Sec. 2.1)?  D is defined pointwise on the
    post-step state T_{k+1} = T_next[k] of the action u[k]:
      * occupied steps: T_{k+1} <= hi[k] (= HI);
      * away steps:     T_{k+1} <= AWAY_MAX (hi[k] on away steps by default);
      * every step:     u[k] = 1  =>  T_{k+1} >= t_min (cooling never ends
                        below the occupied lower limit); u[k] = 0 is free.
    Returns (ok, info) with the counts of each kind of exclusion and the first
    offending step. Use r = sim(..., record=True); in_domain(r["u"], r["T_next"], occ, hi)."""
    u = np.asarray(u).astype(int); Tn = np.asarray(T_next, float)
    occ = np.asarray(occ, bool)[:len(u)]; hi = np.asarray(hi, float)[:len(u)]
    t_min = H.BAND_LO if t_min is None else t_min
    cap = hi if away_max is None else np.where(occ, hi, away_max)
    over = Tn > cap + tol
    cold = (u == 1) & (Tn < t_min - tol)
    bad = over | cold
    info = dict(n_over_occ=int((over & occ).sum()), n_over_away=int((over & ~occ).sum()),
                n_cmd_under=int(cold.sum()),
                first=int(np.argmax(bad)) if bad.any() else -1)
    return (not bad.any()), info


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
