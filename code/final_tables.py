#!/usr/bin/env python3
"""Every table the revised manuscript needs, at the corrected configuration.

Configuration (all changes from the published version are deliberate):
  occupied band   22-24 C   (was 22-26; 24 C is the occupied ceiling)
  control step    15 min    (was 1 h; the hourly step cannot hold a 1 K deadband); config.DT_MIN (F23)
  C_th            4800 kJ/K (ISO 13786, 96 m2 participating surface at 50 kJ/m2K)
  integration     exact matrix exponential on the sensible node
  Lambda(n)       11.90n + Lambda_inf(city), affine in exposed faces
  tariff          0.18 SAR/kWh in force; 0.21 from Jan 2027; 0.05 historical
  c_sw            0.15 SAR/start

THERM is a 1 K deadband thermostat at a 23 C setpoint (on at 23.5, off at 22.5).
This is simultaneously the manuscript's definition (on at T_max-0.5, off at
T_min+0.5) evaluated on the corrected band, AND a representative hardware
deadband for the remote-controller split units in the Saudi residential stock.
The optimiser's advantage is that it may use the whole 2 K comfort band where
THERM uses only 1 K of it.

Protocol (addresses the in-sample criticism):
  cooling season 1 May - 31 Oct, 168-h windows every 14 days.
  ODD-indexed windows tune the rule; EVEN-indexed windows evaluate it.
  Selection: Rule A4 (admissible(), fit_param(), tune_rule(); RULING_round4 Sec. 2.2).
  Saving: s = 1 - sum J_arm / sum J_THERM(delta_w) over the held-out windows (Sec. 2.3);
  no mean +/- sd of per-window savings.

Outputs results/T1..T6.csv and prints each table.
"""
from __future__ import annotations
import sys, os, csv, argparse
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import config as CFG
import headroom as H
import setback as S

CITIES = ("riyadh", "jeddah", "taif")
OCC_LO, OCC_HI = H.BAND_LO, H.BAND_HI
C_TH = H.C_TH              # kJ/K; RBRL_CTH scenario control (F21), read at call time below
FACES = 1
T0 = CFG.T0
TARIFFS = dict(CFG.TARIFFS)
# Must be a module attribute read at CALL time. setback.sim's signature binds
# its c_sw default when the module is imported, so mutating headroom.C_SW after
# import silently has no effect -- that defect produced an earlier version of
# this table in which every c_sw row was identical.
C_SW = CFG.C_SW

# cooling season windows: 1 May = day 120, 31 Oct = day 303
WINDOWS = list(range(121, 297, 14))          # 13 windows of 168 h
TUNE_W = WINDOWS[1::2]                        # odd index -> tuning
EVAL_W = WINDOWS[0::2]                        # even index -> held out


def _ctx(city, start_day, setback=False):
    _, _, N = H.series(city, 168, start_day)
    occ = S.occupancy(N) if setback else np.ones(N, bool)
    lo, hi = S.bands(occ, OCC_LO, OCC_HI, CFG.AWAY_FLOOR, H.AWAY_MAX)
    return N, occ, lo, hi


def therm_run(city, start_day, price_v, setback=False):
    N, occ, lo, hi = _ctx(city, start_day, setback)
    price = H.price_flat(N, price_v)
    # THERM always sees the occupied band: it has no occupancy input; it is a
    # 1 K-deadband thermostat at THERM_SET (23 C headline; 24 C in the policy scenario)
    _, occ_all, lo_n, hi_n = _ctx(city, start_day, False)
    return S.sim(S.hyst_abs(H.THERM_SET + 0.5, H.THERM_SET - 0.5), city, FACES, C_TH, price,
                 lo_n, hi_n, occ_all, 168, start_day, T0, c_sw=C_SW)


def rule_run(city, start_day, price_v, on_at, off_at):
    N, occ, lo, hi = _ctx(city, start_day, False)
    price = H.price_flat(N, price_v)
    return S.sim(S.hyst_abs(on_at, off_at), city, FACES, C_TH, price,
                 lo, hi, occ, 168, start_day, T0, c_sw=C_SW)


MEAN_KEY = "T_mean_occ_clip"   # Rule B: matching uses the clipped occupied mean

# ------------------------------------------------- vectorised hysteresis (RULING_round4 F4)
# Same 1e-9 comparison convention as setback.sim (max(0, x - 1e-9)), so every key below equals
# the scalar simulator to rounding (test 12: <= 1e-12; most keys are bit-identical).
COMFORT_TOL = 1e-9


def lead_mask(occ_ext, L, N):
    """(P, N) bool: True where a setback rule uses its OCCUPIED thresholds, i.e. occupied or
    within L steps before occupancy resumes (setback_arms.sb_policy: steps_to_occ(occ_ext) <= L).
    occ_ext is the extended timetable (setback_arms uses S.occupancy(N + 200)); L scalar or (P,)."""
    occ_ext = np.asarray(occ_ext, bool)
    d = np.zeros(len(occ_ext), int); nxt = 10 ** 6
    for k in range(len(occ_ext) - 1, -1, -1):
        nxt = 0 if occ_ext[k] else nxt + 1
        d[k] = nxt
    L = np.atleast_1d(np.asarray(L))
    return d[None, :N] <= L[:, None]


def sim_hyst_batch(city, w, price_v, on, off, c_sw=None, T0=T0, c_th=None, faces=FACES,
                   hours=168, occ=None, lo=None, hi=None, active=None, on_away=None,
                   off_away=None, t_min=None):
    """Vectorised setback.sim for P two-threshold hysteresis candidates in lock-step.

    Candidate i: u = 1 if T >= on[i], 0 if T <= off[i], else previous u (setback.hyst_abs).
    Setback variant: pass occ/lo/hi (N,) vectors, `active` ((N,) or (P, N) bool, e.g. lead_mask)
    and on_away/off_away (scalar or (P,)); where active is False the away thresholds apply
    (setback_arms.sb_policy). Default occ/lo/hi = all-occupied band (_ctx(..., False)), as rule_run.
    price_v: scalar (flat tariff) or (N,) array. COP: H.cop_series(t_out), as S.sim with cop=None.

    Returns dict of (P,) arrays: J, E, f_s, starts, T_end, T_mean_occ, T_mean_occ_clip (Rule B),
    v_occ, deg_h_occ (legacy), and the Sec. 2.1 metrics on the post-step state T_{k+1}:
      deg_h_over       sum_occ max(0, T' - hi)*dt
      deg_h_under      sum_occ max(0, lo - T')*dt                (plain)
      deg_h_cmd_under  sum over u = 1 steps (occupied or away) of max(0, t_min - T')*dt
      deg_h_ff_under   sum over u = 0 occupied steps of max(0, t_min - T')*dt
      T_max_away       max T' over away steps (nan if none);  fallback_steps = 0 (rules never fall back)
    t_min defaults to the occupied lower limit (max lo over occupied steps), as setback.sim.
    Equivalence with S.sim holds for E_START, terminal pricing at price[-1] and cop=None (the
    rule_run / setback_arms.run_rule paths); tests/test_fast.py test 12 gates it.
    """
    c_sw = C_SW if c_sw is None else c_sw
    c_th = C_TH if c_th is None else c_th
    on = np.atleast_1d(np.asarray(on, float)); off = np.atleast_1d(np.asarray(off, float))
    on, off = np.broadcast_arrays(on, off); P = len(on)
    t_out, irr, N = H.series(city, hours, w)
    if occ is None:
        _, occ, lo_d, hi_d = _ctx(city, w, False)
        lo = lo_d if lo is None else lo; hi = hi_d if hi is None else hi
    occ = np.asarray(occ, bool)[:N]; lo = np.asarray(lo, float)[:N]; hi = np.asarray(hi, float)[:N]
    if active is not None:
        if on_away is None or off_away is None:
            raise ValueError("setback variant needs on_away and off_away")
        active = np.asarray(active, bool)
        active = np.broadcast_to(active if active.ndim == 2 else active[None, :], (P, active.shape[-1]))
        on_a = np.broadcast_to(np.asarray(on_away, float), (P,))
        off_a = np.broadcast_to(np.asarray(off_away, float), (P,))
    price = H.price_flat(N, price_v) if np.ndim(price_v) == 0 else np.asarray(price_v, float)
    if t_min is None:
        t_min = float(np.max(lo[occ])) if occ.any() else H.BAND_LO
    q, cp = H.Q_HVAC, H.COP_RATED
    lam = H.lam_of(faces, city)
    decay = float(np.exp(-H.DT * 3600.0 * lam / (c_th * 1e3)))
    p_el_k = q / H.cop_series(t_out) / 1000.0
    DT, tol = H.DT, COMFORT_TOL
    T = np.full(P, float(T0)); prev = np.zeros(P, bool)
    cost = np.zeros(P); e = np.zeros(P); sw = np.zeros(P, int)
    dh = np.zeros(P); over = np.zeros(P); under = np.zeros(P); cmd = np.zeros(P); ff = np.zeros(P)
    s_occ = np.zeros(P); s_clip = np.zeros(P); n_viol = np.zeros(P, int)
    t_max_away = np.full(P, -np.inf); n_occ = int(occ.sum()); n_away = N - n_occ
    for k in range(N):
        if active is None:
            on_k, off_k = on, off
        else:
            a = active[:, k]
            on_k = np.where(a, on, on_a); off_k = np.where(a, off, off_a)
        u = np.where(T >= on_k, True, np.where(T <= off_k, False, prev))
        st = u & ~prev
        cost += np.where(st, c_sw + price[k] * H.E_START, 0.0); sw += st; e += np.where(st, H.E_START, 0.0)
        cost += np.where(u, price[k] * p_el_k[k] * DT, 0.0); e += np.where(u, p_el_k[k] * DT, 0.0)
        T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - q * u.astype(float)) / lam
        T = T_inf + (T - T_inf) * decay
        cmd += np.where(u, np.maximum(0.0, t_min - T - tol) * DT, 0.0)
        if occ[k]:
            s_occ += T; s_clip += np.maximum(T, lo[k])
            over += np.maximum(0.0, T - hi[k] - tol) * DT
            under += np.maximum(0.0, lo[k] - T - tol) * DT
            ff += np.where(u, 0.0, np.maximum(0.0, t_min - T - tol) * DT)
            v = (T > hi[k] + tol) | (T < lo[k] - tol)
            n_viol += v
            dh += np.where(v, np.maximum(0.0, T - hi[k]) * DT + np.maximum(0.0, lo[k] - T) * DT, 0.0)
        else:
            t_max_away = np.maximum(t_max_away, T)
        prev = u
    d = hours / 24.0
    cost += price[-1] * (T - T0) * c_th * 1e3 / 3.6e6 / cp
    nan = np.full(P, np.nan)
    return dict(J=cost / d, E=e / d, f_s=sw / d, starts=sw, T_end=T,
                T_mean_occ=s_occ / n_occ if n_occ else nan,
                T_mean_occ_clip=s_clip / n_occ if n_occ else nan,
                v_occ=100.0 * n_viol / max(1, n_occ), deg_h_occ=dh,
                deg_h_over=over, deg_h_under=under, deg_h_cmd_under=cmd, deg_h_ff_under=ff,
                T_max_away=t_max_away if n_away else nan, fallback_steps=np.zeros(P, int))


def therm_shift_run(city, start_day, price_v, delta, db=1.0):
    """THERM(delta): the comparator of deadband db centred on 23 C, shifted by
    delta (on at 23+db/2+delta, off at 23-db/2+delta). db=1, delta=0
    reproduces therm_run exactly."""
    c0 = H.THERM_SET
    return rule_run(city, start_day, price_v, c0 + 0.5 * db + delta,
                    c0 - 0.5 * db + delta)


DELTAS = np.round(np.arange(-0.4, 0.4 + 1e-12, 0.002), 6)     # the Sec. 2.3 comparator grid


HIT_TOL = 1e-12   # K: a target within this of a grid mean IS that grid run (batch vs scalar
                  # simulations differ by ~1e-14, e.g. THERM(0) scored against its own curve)


def rule_c(m, J, T_target, deltas=None):
    """THE Rule C crossing search (RULING_round4 Sec. 13), shared by selection (A4, j_eq), evaluation
    (equalise), the shield, the multi-zone dwelling (mz_r3) and AMY/orientation. m, J: the
    comparator's clipped mean and cost on the delta grid `deltas` (raw curve; it is NOT monotone:
    15-min switching gives drops of up to ~0.1 K between neighbouring deltas).

    Crossings of T_target on the piecewise-linear curve: every grid point with |m[i] - T_target| <=
    HIT_TOL (t = 0) and every other segment [a, a+1] with min(m) < T_target < max(m) strictly, J
    interpolated linearly at the SAME (a, b, t) as every other lerped metric. The chosen crossing
    is the one with MINIMUM J (conservative: the baseline is credited with its cheapest setting at
    the same comfort; ties -> lowest delta index). Clipping is tested against the curve's true
    min / max over the scan (not its end points): outside -> the nearest extreme (cheapest of the
    grid points attaining it), clipped = True, n_crossings = 0.

    Returns dict(a, b, t, delta, J, clipped, n_crossings, J_max, delta_maxJ, gap); `gap` = m[b] -
    m[a] of the chosen segment (0 at an exact grid hit or when clipped). lerp(x, rc) applies the
    crossing to another per-delta array."""
    m = np.asarray(m, float); J = np.asarray(J, float); n = len(m)
    deltas = DELTAS if deltas is None else np.asarray(deltas, float)
    T = float(T_target)
    lo_m, hi_m = float(m.min()), float(m.max())
    if T < lo_m - HIT_TOL or T > hi_m + HIT_TOL:
        ext = np.flatnonzero(m == (lo_m if T < lo_m else hi_m))
        i = int(ext[np.argmin(J[ext])])
        jmax = int(ext[np.argmax(J[ext])])
        return dict(a=i, b=i, t=0.0, delta=float(deltas[i]), J=float(J[i]), clipped=True,
                    n_crossings=0, J_max=float(J[jmax]), delta_maxJ=float(deltas[jmax]), gap=0.0)
    cand = []                                      # (J, sort key, a, b, t)
    hit = np.abs(m - T) <= HIT_TOL
    for i in np.flatnonzero(hit):
        i = int(i); cand.append((float(J[i]), float(i), i, i, 0.0))
    ma, mb = m[:-1], m[1:]
    for a in np.flatnonzero((np.minimum(ma, mb) < T) & (T < np.maximum(ma, mb))
                            & ~hit[:-1] & ~hit[1:]):
        a = int(a); b = a + 1
        span = m[b] - m[a]
        t = 0.0 if abs(span) <= 1e-12 else (T - m[a]) / span
        cand.append((float(J[a] + t * (J[b] - J[a])), a + 0.5, a, b, float(t)))
    cand.sort(key=lambda c: c[1])                  # delta order: ties -> lowest delta
    k = min(range(len(cand)), key=lambda q: cand[q][0])
    kx = max(range(len(cand)), key=lambda q: cand[q][0])
    Jc, _, a, b, t = cand[k]
    _, _, ax, bx, tx = cand[kx]
    return dict(a=a, b=b, t=t, delta=float(deltas[a] + t * (deltas[b] - deltas[a])), J=Jc,
                clipped=False, n_crossings=len(cand), J_max=cand[kx][0],
                delta_maxJ=float(deltas[ax] + tx * (deltas[bx] - deltas[ax])),
                gap=float(m[b] - m[a]))


def lerp(x, rc):
    """another per-delta metric at the crossing rc chosen by rule_c (same a, b, t)."""
    x = np.asarray(x, float); a, b, t = rc["a"], rc["b"], rc["t"]
    return float(x[a]) if a == b else float(x[a] + t * (x[b] - x[a]))


_THERM_CURVE = {}
CURVE_KEYS = ("J", "E", "f_s", "starts", "deg_h_occ", "T_end")


def therm_curve_full(city, w, price_v, db=1.0, setback=False, deltas=None):
    """dict of read-only (D,) arrays (MEAN_KEY and CURVE_KEYS) of THERM(delta) on the delta grid
    (default the Sec. 2.3 grid DELTAS), one sim_hyst_batch call; cached per process on everything
    it depends on (city, w, price, db, setback, c_sw, C_th, THERM_SET, AWAY_MAX, the weather
    source H.series -- AMY swaps, amy_spread). setback: THERM scored on the timetable's occupied
    steps (setback_arms.therm_sb)."""
    ds = DELTAS if deltas is None else np.round(np.asarray(deltas, float), 6)
    key = (city, int(w), float(price_v), float(db), bool(setback), float(C_SW), float(C_TH),
           float(H.THERM_SET), float(H.AWAY_MAX), H.series, ds.tobytes())
    if key not in _THERM_CURVE:
        kw = {}
        if setback:
            N, occ, lo, hi = _ctx(city, w, True)
            kw = dict(occ=occ, lo=lo, hi=np.where(occ, hi, H.AWAY_MAX))
        r = sim_hyst_batch(city, w, price_v, H.THERM_SET + 0.5 * db + ds,
                           H.THERM_SET - 0.5 * db + ds, **kw)
        c = {k: np.array(r[k], float) for k in (MEAN_KEY,) + CURVE_KEYS}
        c["delta"] = ds
        for v in c.values():
            v.setflags(write=False)
        _THERM_CURVE[key] = c
    return _THERM_CURVE[key]


def therm_curve(city, w, price_v, db=1.0, setback=False):
    """(clipped mean, J) of THERM(delta) on DELTAS for one window (raw, NOT monotone-ised)."""
    c = therm_curve_full(city, w, price_v, db, setback)
    return c[MEAN_KEY], c["J"]


def equalise_curve(c, T_target, mean_key=None):
    """Rule C on a precomputed comparator curve c (dict of per-delta arrays incl. the mean, J and
    'delta'; single-zone therm_curve_full or the mz_r3 dwelling curve). Returns the equalise dict:
    delta, J, E, f_s (and starts where present), mean, resid, bracket_gap, clipped, n_crossings,
    J_eq_max, delta_maxJ, deg_h_occ (max of the two bracketing runs)."""
    mk = MEAN_KEY if mean_key is None else mean_key
    m = c[mk]
    rc = rule_c(m, c["J"], T_target, c["delta"])
    out = dict(delta=rc["delta"], J=rc["J"], mean=lerp(m, rc), bracket_gap=rc["gap"],
               clipped=rc["clipped"], n_crossings=rc["n_crossings"], J_eq_max=rc["J_max"],
               delta_maxJ=rc["delta_maxJ"])
    out["resid"] = abs(out["mean"] - float(T_target))
    for k in ("E", "f_s", "starts"):
        if k in c:
            out[k] = lerp(c[k], rc)
    if "deg_h_occ" in c:
        out["deg_h_occ"] = float(max(c["deg_h_occ"][rc["a"]], c["deg_h_occ"][rc["b"]]))
    return out


def j_eq(city, w, price_v, T_target, db=1.0, setback=False, full=False):
    """J_THERM(delta_w),w at the clipped mean T_target on one window (Rule C on the precomputed
    curve; the same rule_c as equalise). Returns (J, clipped), or the rule_c dict if full."""
    m, J = therm_curve(city, w, price_v, db, setback)
    rc = rule_c(m, J, T_target)
    return rc if full else (rc["J"], rc["clipped"])


def equalise(city, start_day, price_v, T_target, lo=-0.4, hi=0.4, step=0.002,
             db=1.0, setback=False):
    """Rule C on one window: THERM(delta_w) at the arm's clipped occupied mean, the minimum-J
    crossing of the delta-grid curve (rule_c), J/E/f_s/starts interpolated at that crossing.
    bracket_gap: mean difference of the two real runs it interpolates; n_crossings and J_eq_max
    (the max-J crossing) for the supplement's crossing-choice range."""
    ds = np.round(np.arange(lo, hi + 1e-12, step), 6)
    c = therm_curve_full(city, start_day, price_v, db, setback,
                         None if (len(ds) == len(DELTAS) and np.array_equal(ds, DELTAS)) else ds)
    return equalise_curve(c, T_target)


# ======================================================================================
# THE selection protocol (RULING_round4 Sec. 2.1 / 2.2, Rule A4). Every causal arm's comfort
# parameter is chosen here and nowhere else: TUNED (on, off), guard / RBRL ceiling, MPC lam,
# TUNED-SB (on, off, lead, away). No module may compare a comfort metric or a mean tolerance
# itself (tests/test_fast.py::test_no_admissibility_outside_helper).
#
#   condition 1, per tuning window w:   admissible(r, w)  (deg_h_over = 0, deg_h_cmd_under = 0,
#                                        and T_max_away <= AWAY_MAX where there are away steps;
#                                        free-float under-temperature is allowed and reported)
#   condition 2, pooled over TUNE_W:    |mean_w T~(p) - mean_w T~_THERM| <= POOL_TOL (0.03 K)
#   one fallback, identical for all arms: POOL_TOL_FALLBACK (0.10 K) if no candidate meets 0.03
#   fit_status in FIT_STATUSES; "none" rows are refused by rbrl_io; "oracle" = CLV (per-window
#   bisection, F10), "fixed" = a parameter set by the caller, not selected (lam = X lam*, or the
#   no-rules ablation with its cap fixed at BAND_HI).
#   ties: the lowest candidate index (candidate order is part of each caller's definition).
# ======================================================================================
POOL_TOL, POOL_TOL_FALLBACK = 0.03, 0.10
FIT_STATUSES = ("pooled_0.03", "pooled_0.10", "none", "oracle", "fixed")
ADM_EPS = 1e-12            # the metrics already subtract COMFORT_TOL (1e-9) before accumulating


def admissible(r, w=None):
    """Condition 1 of Sec. 2.2 on ONE window (the single admissibility helper). r: a simulator
    dict (scalars, or (P,) arrays from a batch simulator -> (P,) bool). Missing metrics raise
    KeyError (no silent default). w is accepted for call-site symmetry and error messages."""
    over = np.asarray(r["deg_h_over"], float)
    cmd = np.asarray(r["deg_h_cmd_under"], float)
    ok = (over <= ADM_EPS) & (cmd <= ADM_EPS)
    tma = r.get("T_max_away")
    if tma is not None:                                   # nan (no away steps) passes
        ok = ok & ~(np.asarray(tma, float) > H.AWAY_MAX + COMFORT_TOL)
    return bool(ok) if np.ndim(ok) == 0 else ok


def pooled_status(dT_pooled):
    """Condition 2 with its one fallback: the fit_status a candidate with pooled clipped-mean
    difference dT_pooled can carry ("pooled_0.03" / "pooled_0.10"), or None."""
    d = abs(float(dT_pooled))
    if d <= POOL_TOL + 1e-12:
        return "pooled_0.03"
    if d <= POOL_TOL_FALLBACK + 1e-12:
        return "pooled_0.10"
    return None


def check_fit_status(s):
    if s not in FIT_STATUSES:
        raise ValueError(f"fit_status {s!r} not in {FIT_STATUSES}")
    return s


class Fit(tuple):
    """Result of a selection: a tuple (objective, *params) -- old callers unpack it as before --
    with .fit_status, .params and .info (tune_ratio / tune_J, pooled dT, counts)."""
    def __new__(cls, objective, params, fit_status, info):
        t = super().__new__(cls, (objective,) + tuple(params))
        t.fit_status = check_fit_status(fit_status)
        t.params = tuple(params); t.info = info
        return t


def _select_core(Jsum, Jref, Tm, adm, target):
    """The one selection rule on precomputed candidate matrices.
    Jsum (P,) sum_w J_w(p); Jref (P,) the objective's denominator; Tm (P, W) clipped means;
    adm (P,) condition 1 on every window; target = pooled THERM clipped mean.
    Returns (index or None, fit_status, info)."""
    Jsum = np.asarray(Jsum, float); Jref = np.asarray(Jref, float); adm = np.asarray(adm, bool)
    P = len(Jsum)
    Tm = np.asarray(Tm, float).reshape(P, -1)
    dT = np.full(P, np.nan)
    if adm.any():
        dT[adm] = Tm[adm].mean(axis=1) - target
    with np.errstate(invalid="ignore", divide="ignore"):
        obj = Jsum / Jref
    st = np.array([pooled_status(d) if (a and np.isfinite(d)) else None for a, d in zip(adm, dT)],
                  dtype=object)
    info = dict(n_cand=int(P), n_adm_cond1=int(adm.sum()),
                n_adm_0p03=int(sum(s == "pooled_0.03" for s in st)),
                n_adm_0p10=int(sum(s in ("pooled_0.03", "pooled_0.10") for s in st)))
    for status, ok_set in (("pooled_0.03", ("pooled_0.03",)),
                           ("pooled_0.10", ("pooled_0.03", "pooled_0.10"))):
        idx = np.flatnonzero([s in ok_set for s in st])
        if len(idx):
            i = int(idx[np.argmin(obj[idx])])           # argmin: first minimum = lowest index
            info.update(tune_obj=float(obj[i]), tune_dT=float(dT[i]),
                        tune_max_abs_dT_w=float(np.max(np.abs(np.asarray(Tm[i], float) - target))))
            return i, status, info
    return None, "none", info


def _objective_parts(J_rows, Tm_rows, eq):
    """(numerator, denominator) of the A4 objective for one candidate: sum_w J_w(p) and
    sum_w J_THERM(delta_w(p)),w, the comparator equalised to the candidate's clipped mean on each
    tuning window (Rule C applied on TUNE_W). Ratio = 1 - tuning saving."""
    num, den = 0.0, 0.0
    for w, J, T in zip(eq.windows, J_rows, Tm_rows):
        Jq, clipped = eq.jeq(w, T)
        num += float(J); den += Jq; eq.n_clipped += bool(clipped)
    return num, den


def select_rows(cands, rows, city=None, price_v=None, windows=None, db=1.0, setback=False,
                target_fn=None, jeq=None, target=None):
    """public form of _select_rows: Fit (objective, cands[i]) or None."""
    i, status, info = _select_rows(cands, rows, city, price_v, windows, db, setback, target_fn,
                                   jeq, target)
    return None if i is None else Fit(info["tune_obj"], (cands[i],), status, info)


def _select_rows(cands, rows, city=None, price_v=None, windows=None, db=1.0, setback=False,
                 target_fn=None, jeq=None, target=None):
    """Rule A4 on candidates whose tuning-window runs are already known. rows[i]: list of sim
    dicts (one per window, in `windows` order) or None (failed condition 1 somewhere). Condition 1
    is (re)checked here with admissible(). Returns (index or None, fit_status, info); the status
    and counts are also left in LAST_FIT."""
    windows = list(TUNE_W if windows is None else windows)
    target = float(target) if target is not None else _target(city, price_v, windows, target_fn,
                                                              db, setback)
    ctx = _EqCtx(city, price_v, windows, db, setback, jeq)
    P, W = len(cands), len(windows)
    Js, Jr, Tm, adm = np.full(P, np.nan), np.full(P, np.nan), np.full((P, W), np.nan), np.zeros(P, bool)
    clip = np.zeros(P, int)
    for i, rr in enumerate(rows):
        if rr is None or len(rr) != W or not all(admissible(r, w) for r, w in zip(rr, windows)):
            continue
        c0 = ctx.n_clipped
        Js[i], Jr[i] = _objective_parts([r["J"] for r in rr], [r[MEAN_KEY] for r in rr], ctx)
        clip[i] = ctx.n_clipped - c0
        Tm[i] = [r[MEAN_KEY] for r in rr]; adm[i] = True
    i, status, info = _select_core(Js, Jr, Tm, adm, target)
    info.update(tune_target=target)
    if i is not None:     # tune_eq_clipped: tuning windows where the chosen p is outside THERM(+-0.4 K)
        info.update(tune_saving=100.0 * (1.0 - info["tune_obj"]), tune_eq_clipped=int(clip[i]))
    LAST_FIT.clear(); LAST_FIT.update(fit_status=status, **info)
    return i, status, info


def fit_param(candidates, run_fn, windows=None, target_fn=None, tol=None, *, city=None,
              price_v=None, db=1.0, setback=False):
    """Rule A4 over an explicit candidate list. run_fn(p, w) -> sim dict on tuning window w.
    A window that fails condition 1 ends that candidate's evaluation (it is inadmissible
    whatever the other windows give). Target = pooled THERM clipped mean (target_fn(w) averaged,
    else THERM at delta = 0 of the comparator family (db, setback)). Returns a Fit
    (objective, p) or None (fit_status "none" in LAST_FIT; the caller records it). `tol` is
    accepted for backward compatibility and ignored: the tolerances are POOL_TOL /
    POOL_TOL_FALLBACK."""
    windows = list(TUNE_W if windows is None else windows)
    cands = list(candidates)
    rows = []
    for p in cands:
        rr = []
        for w in windows:
            r = run_fn(p, w)
            if r is None or not admissible(r, w):
                rr = None; break
            rr.append(r)
        rows.append(rr)
    return select_rows(cands, rows, city, price_v, windows, db, setback, target_fn)


LAST_FIT = {}              # fit_status and info of the most recent fit_param / tune_rule call


class _EqCtx:
    """what the objective needs to equalise a candidate on the tuning windows (F7). jeq(w, T) ->
    (J_THERM(delta_w),w, clipped); default: j_eq on this arm's comparator family (db, setback);
    the multi-zone dwelling passes its own."""
    def __init__(self, city, price_v, windows, db, setback, jeq=None):
        self.city, self.price_v, self.windows, self.db, self.setback = city, price_v, windows, db, setback
        self._jeq = jeq; self.n_clipped = 0

    def jeq(self, w, T):
        if self._jeq is not None:
            r = self._jeq(w, T)
            return (r, False) if np.ndim(r) == 0 else r
        return j_eq(self.city, w, self.price_v, T, self.db, self.setback)


def _target(city, price_v, windows, target_fn, db=1.0, setback=False):
    if target_fn is not None:
        return float(np.mean([target_fn(w) for w in windows]))
    if city is None or price_v is None:
        raise TypeError("fit_param / tune_rule need target_fn or city and price_v")
    i0 = int(np.flatnonzero(DELTAS == 0.0)[0])
    return float(np.mean([therm_curve(city, w, price_v, db, setback)[0][i0] for w in windows]))


def pooled_saving(J_arm, J_ref):
    """The one saving convention: s = 1 - sum J_arm / sum J_ref, in percent."""
    return 100.0 * (1.0 - float(np.sum(J_arm)) / float(np.sum(J_ref)))


def tune_rule(city, price_v, windows=None, target_fn=None, tol=None, step=0.05, refine=True, db=1.0):
    """TUNED: one (on, off) pair by Rule A4 on the tuning windows (objective: equalised tuning
    cost ratio sum_w J_w / sum_w J_THERM(delta_w),w; candidates simulated with sim_hyst_batch).
    Candidate order: the coarse
    grid (on ascending from BAND_LO + 0.3 to BAND_HI, off ascending from BAND_LO to on - 0.1, step
    `step`), then the comparator THERM(db) itself (nesting: TUNED's family contains THERM), then
    each 0.01 K refinement neighbourhood (+/- 0.05 K) of the incumbent, appended in order until
    the selection no longer moves. Returns Fit (objective, on, off) or None (fit_status none,
    in LAST_FIT)."""
    windows = list(TUNE_W if windows is None else windows)
    target = _target(city, price_v, windows, target_fn, db)
    cands, index = [], {}
    def add(on_, off_):
        key = (round(float(on_), 2), round(float(off_), 2))
        if key not in index:
            index[key] = len(cands); cands.append(key)
    for on_ in np.arange(OCC_LO + 0.3, OCC_HI + 0.001, step):
        for off_ in np.arange(OCC_LO, on_ - 0.09, step):
            add(on_, off_)
    add(H.THERM_SET + 0.5 * db, H.THERM_SET - 0.5 * db)
    rows = {}
    def score():
        new = [p for p in cands if p not in rows]
        if new:
            rows.update(zip(new, _rows_rule_batch(city, price_v, windows, new)))
        return _select_rows(cands, [rows[p] for p in cands], city, price_v, windows, db, False,
                            target_fn)
    i, status, info = score()
    if i is not None and refine:
        for _ in range(50):
            c_on, c_off = cands[i]
            for on_ in np.round(np.arange(c_on - 0.05, c_on + 0.0501, 0.01), 2):
                for off_ in np.round(np.arange(c_off - 0.05, c_off + 0.0501, 0.01), 2):
                    if on_ - off_ < 0.1 - 1e-9 or on_ > OCC_HI + 1e-9 or off_ < OCC_LO - 1e-9:
                        continue
                    add(on_, off_)
            i2, status, info = score()
            if i2 == i:
                break
            i = i2
        else:
            raise RuntimeError("tune_rule refinement did not converge in 50 rounds")
    LAST_FIT.clear(); LAST_FIT.update(fit_status=status, **info)
    if i is None:
        return None
    on_, off_ = cands[i]
    return Fit(info["tune_obj"], (float(on_), float(off_)), status, info)


_RANK = {"pooled_0.03": 0, "pooled_0.10": 1}


def score_candidates(cands, rows, city=None, price_v=None, windows=None, db=1.0, setback=False,
                     jeq=None, target=None):
    """per-candidate A4 standing (for the search audit): list of dict(status, obj) with status
    the best fit_status the candidate could carry on its own ("pooled_0.03"/"pooled_0.10"/None)
    and obj its equalised tuning-cost ratio (nan if not admissible)."""
    windows = list(TUNE_W if windows is None else windows)
    target = float(target) if target is not None else _target(city, price_v, windows, None, db, setback)
    ctx = _EqCtx(city, price_v, windows, db, setback, jeq)
    out = []
    for rr in rows:
        if rr is None or not all(admissible(r, w) for r, w in zip(rr, windows)):
            out.append(dict(status=None, obj=float("nan"))); continue
        num, den = _objective_parts([r["J"] for r in rr], [r[MEAN_KEY] for r in rr], ctx)
        dT = float(np.mean([r[MEAN_KEY] for r in rr])) - target
        out.append(dict(status=pooled_status(dT), obj=num / den, dT=dT))
    return out


def better_than(a, b, eps=1e-12):
    """True if standing a would be selected over standing b by A4 (better status, or the same
    status and a strictly lower objective)."""
    if a["status"] is None:
        return False
    if b["status"] is None:
        return True
    ra, rb = _RANK[a["status"]], _RANK[b["status"]]
    return ra < rb or (ra == rb and a["obj"] < b["obj"] - eps)


def _rows_rule_batch(city, price_v, windows, pairs):
    """per-candidate lists of per-window sim dicts of the hysteresis rules `pairs` (vectorised:
    sim_hyst_batch, equal to rule_run to <= 1e-12, test 12), None where condition 1 fails on
    some window."""
    on = np.array([p[0] for p in pairs], float); off = np.array([p[1] for p in pairs], float)
    out = [[] for _ in pairs]
    for w in windows:
        r = sim_hyst_batch(city, w, price_v, on, off)
        ok = admissible(r, w)
        for i in range(len(pairs)):
            if out[i] is not None:
                out[i] = out[i] + [{k: (v[i] if np.ndim(v) else v) for k, v in r.items()}] if ok[i] else None
    return out


def dp_run(city, start_day, price_v, setback=False, cap=None, n_grid=1601):
    N, occ, lo, hi = _ctx(city, start_day, setback)
    price = H.price_flat(N, price_v)
    if cap is not None:
        hi = np.minimum(hi, np.where(occ, cap, hi))
    return S.dp(city, FACES, C_TH, price, lo, hi, occ, 168, start_day,
                T0, c_sw=C_SW, n_grid=n_grid)


def dp_isocomfort(city, start_day, price_v, target, setback=False,
                  tol=0.015, iters=22, n_grid=1601):
    a, b = OCC_LO + 0.15, OCC_HI
    best = None
    for _ in range(iters):
        m = 0.5 * (a + b)
        r = dp_run(city, start_day, price_v, setback, cap=m, n_grid=n_grid)
        # legacy ceiling-bisection oracle (not a Sec. 2.2 arm; superseded by r3_dp): DP feasibility
        if r is None or r["deg_h_occ"] > 1e-9:  # adm-ok: legacy DP oracle, not a selection rule
            a = m; continue
        best = (r, m)
        if abs(r["T_mean_occ"] - target) <= tol:
            return best
        if r["T_mean_occ"] > target:
            b = m
        else:
            a = m
    return best


def pct(base, x):
    return 100.0 * (base - x) / base if base else float("nan")


def dump(name, rows):
    """Through rbrl_io (atomic, locked, tag-aware, provenance). Keeps this function's historical
    format: sorted header, unrounded floats."""
    import rbrl_io as IO
    return IO.write_csv(name, rows, ndigits=None, sort_keys=True)
