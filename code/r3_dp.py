#!/usr/bin/env python3
"""Round-3 Lagrangian dynamic programme: the clairvoyant arm (CLV) and the
provable bound (ruling c).

    L*(lam) = min_u  J(u) + (lam/n_occ) * sum_{occupied k} max(T_{k+1}, T_min)

with the upper band enforced pointwise (occupied: HI; away: AWAY_MAX) and the
corrected cold rule of ruling round 4 (Sec. 2.1): a COOLING step may never end
below T_min (the occupied lower limit) at ANY step, occupied or away; switching
off (free float) is always allowed and has no lower limit. The rule is
state-independent (Markov), so sub-band states arise only by free drift with
T_inf0 < T_min, which the clipped mean max(T', T_min) gives no warm credit.
(The round-3 predicate "u=0 may end below T_min only if T_inf0 < T_min" is
deleted: it trapped legitimate recoveries from a natural cold drift.)

relaxed=True is the optimistic-neighbour relaxation. The plant map
f(x) = T_inf + (x - T_inf) a, a = exp(-dt Lambda / C) < 1, is a contraction, so
for any true trajectory x_k there is a grid trajectory y_k with |y_k - x_k| <= h
(h = grid spacing) under the same actions. Charging every stage at the most
favourable temperature within h (continuation min(V[i], V[i+1]), feasibility
tested as T' <= hi+h and, for u=1, T' >= T_min-h (step_ok with hh=h), mean
term at max(T'-h, T_min), terminal at T-h) makes
every relaxed stage cost <= the true one and every true-feasible step
relaxed-feasible. Hence L*_relaxed(lam) <= L*(lam) <= J(u) + lam (mean(u) - T*)
for every lam >= 0 and every u, and for every u with mean(u) <= T*:

    J(u) >= L*_relaxed(lam) - lam T*      for all lam >= 0.

The right-hand side, maximised over lam, is the reported bound.
"""
from __future__ import annotations
import sys
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import config as CFG
import headroom as H
import setback as S
import final_tables as F

LO, HI = H.BAND_LO, H.BAND_HI
C_TH, T0 = H.C_TH, CFG.T0      # kJ/K: RBRL_CTH (F21 config hook, same as final_tables.C_TH)


def _setup(city, w, price_v, setback, hours=168, cap=None):
    lam_env = H.lam_of(F.FACES, city)
    t_out, irr, N = H.series(city, hours, w)
    decay = float(np.exp(-S.DT * 3600.0 * lam_env / (C_TH * 1e3)))
    occ = S.occupancy(N) if setback else np.ones(N, bool)
    lo_b, hi_b = S.bands(occ, LO, HI, CFG.AWAY_FLOOR, H.AWAY_MAX)
    if cap is not None:                 # clv_fit: occupied upper limit lowered (restriction only)
        hi_b = np.where(occ, np.minimum(hi_b, cap), hi_b)
    price = H.price_flat(N, price_v)
    T_inf0 = t_out + H.SHGC * H.A_GL * irr / lam_env
    return lam_env, t_out, irr, N, decay, occ, lo_b, hi_b, price, T_inf0


def grid_for(city, w, setback, n_grid, hours=168, h_max=None):
    """Restricted grid. Upper edge just above the highest upper limit of the window (HI occupied,
    AWAY_MAX away: F-6, no hard-coded setback edges); lower edge just below the lowest band edge,
    or below the window's lowest free-float equilibrium when the plant can drift under it (no
    trajectory goes below min T_inf with u=0, and a cooling step never ends below T_min).
    h_max: cap on the spacing (F11/F-4: Taif h <= Riyadh h); the node count is then
    max(n_grid, ceil(span/h_max) + 1)."""
    *_, occ, lo_b, hi_b, _, T_inf0 = _setup(city, w, 0.18, setback, hours)
    lo_g, hi_g = float(np.min(lo_b)) - 0.10, float(np.max(hi_b)) + 0.10
    # F-6: the coverage argument (edge clamp never reached by admissible trajectories)
    if setback and not occ.all():
        assert H.AWAY_MAX <= hi_g - 0.10 + 1e-12, "AWAY_MAX above the setback grid edge"
    assert hi_g >= float(np.max(hi_b)) + 0.10 - 1e-12
    lo_g = min(lo_g, float(np.floor((T_inf0.min() - 0.05) * 10) / 10))
    n = int(n_grid)
    if h_max is not None:
        n = max(n, int(np.ceil((hi_g - lo_g) / h_max - 1e-9)) + 1)
    return np.linspace(lo_g, hi_g, n)


def h_ref(n_grid, setback=False, windows=None):
    """F11 (F-4): the largest Riyadh grid spacing at n_grid nodes over `windows` (default the
    held-out windows). Passing it as h_max makes every city's grid at least as fine as Riyadh's,
    and leaves Riyadh's own grids unchanged."""
    import final_tables as _F
    ws = _F.EVAL_W if windows is None else windows
    return max(float(np.diff(grid_for("riyadh", w, setback, n_grid)[:2])[0]) for w in ws)


# R1/R2 of the ruled bound / ruled CLV: defaults from config (BAND_HI - EPS_HOT, BAND_LO + EPS_COLD);
# lagrangian / replay take rule_on / rule_off arguments (F8/F11: the ruled relaxed bound needs
# RULE_ON >= and RULE_OFF <= every in-rules arm's R1/R2).
RULE_ON, RULE_OFF = CFG.RULE_ON, CFG.RULE_OFF

# O4 (ruling §21.3, E-opt1-1 / C19): ONE uniform terminal value for the bound, the CLV and every arm
# they are compared with: the energy value of the stored heat at rated COP PLUS a pro-rata start
# charge c_sw / DELTA_CYCLE per K, V_N(T) = [price C / (3.6e6 COP) + c_sw / DELTA_CYCLE] (T - T0).
# Ending warm can no longer save a start for free. V_N is increasing in T (both coefficients >= 0),
# so the relaxation proof is unchanged (terminal charged at T - h in the relaxed DP). Arms are
# rescored from their stored J and T_end (uniform_J; comparator: comparator_uniform).
DELTA_CYCLE = 1.0          # K per start (one THERM cycle)


def start_charge(c_sw):
    """pro-rata terminal start charge, SAR per K."""
    return float(c_sw) / DELTA_CYCLE


def uniform_J(J, T_end, c_sw, days=7.0):
    """J (SAR/day, simulator terminal = energy value only) -> J under the uniform O4 terminal."""
    return float(J) + start_charge(c_sw) * (float(T_end) - T0) / days


def comparator_uniform(city, w, price_v, T_target, setback=False, c_sw=None, days=7.0):
    """Rule C (F.rule_c, min-J crossing) on THERM(delta)'s curve with J under the uniform O4
    terminal. Returns dict(J, f_s, E, T_end, delta, clipped, n_crossings)."""
    c_sw = F.C_SW if c_sw is None else c_sw
    c = F.therm_curve_full(city, w, price_v, 1.0, setback)
    Ju = c["J"] + start_charge(c_sw) * (c["T_end"] - T0) / days
    rc = F.rule_c(c[F.MEAN_KEY], Ju, T_target, c["delta"])
    return dict(J=float(rc["J"]), f_s=F.lerp(c["f_s"], rc), E=F.lerp(c["E"], rc), T_end=F.lerp(c["T_end"], rc),
                delta=rc["delta"], clipped=rc["clipped"], n_crossings=rc["n_crossings"])
T_MIN = LO          # occupied lower limit; the cold rule applies at every step
TOL = 1e-9


def step_ok(Tp, u, hi, hh=0.0, t_min=None):
    """THE feasibility predicate of one transition (ruling Sec. 2.1), shared by
    the DP (relaxed and unrelaxed), the replay and mpc_lambda.
      * upper: T' <= hi (+hh when relaxed), hi = HI occupied / AWAY_MAX away;
      * cold rule: u = 1  =>  T' >= T_min (-hh when relaxed), at every step;
      * u = 0 has no lower limit.
    Works on scalars and arrays."""
    t_min = T_MIN if t_min is None else t_min
    ok = Tp <= hi + hh + TOL
    if u:
        ok = ok & (Tp >= t_min - hh - TOL)
    return ok


def _interp_inf(x, Tg, V):
    """np.interp that treats an infeasible (inf) neighbour as infeasible: a NaN
    from inf arithmetic becomes +inf instead of silently dropping the action."""
    with np.errstate(invalid="ignore"):
        v = np.interp(x, Tg, V)
    return np.where(np.isnan(v), np.inf, v) if np.ndim(v) else (np.inf if np.isnan(v) else float(v))


def lagrangian(city, w, price_v, lam, setback=False, n_grid=1601, relaxed=False,
               c_sw=None, Tg=None, keep_V=False, ruled=False, rule_on=None, rule_off=None, cap=None,
               terminal="uniform"):
    """Returns dict(L=per-day min Lagrangian incl. the lam term, h, Tg, [V]).
    terminal: "uniform" (O4, default: energy value + c_sw/DELTA_CYCLE per K) or "energy" (the
    simulator's terminal; E1 uses it, because PPO's training objective is the simulator's).
    ruled: R1/R2 fix the action outside (rule_off, rule_on) (defaults RULE_ON / RULE_OFF)."""
    c_sw = F.C_SW if c_sw is None else c_sw
    rule_on = RULE_ON if rule_on is None else rule_on
    rule_off = RULE_OFF if rule_off is None else rule_off
    lam_env, t_out, irr, N, decay, occ, lo_b, hi_b, price, _ = _setup(city, w, price_v, setback, cap=cap)
    if Tg is None:
        Tg = grid_for(city, w, setback, n_grid)
    n = len(Tg); h = float(Tg[1] - Tg[0])
    q, cp = H.Q_HVAC, H.COP_RATED
    p_el = q / H.cop_series(H.series(city, 168, w)[0]) / 1000.0     # per step
    n_occ = int(occ.sum())
    hh = h if relaxed else 0.0
    INF = np.inf
    Tterm = Tg - hh
    if terminal not in ("uniform", "energy"):
        raise ValueError(f"terminal={terminal!r}")
    kap = start_charge(c_sw) if terminal == "uniform" else 0.0
    V = np.repeat((price[-1] * (Tterm - T0) * C_TH * 1e3 / 3.6e6 / cp + kap * (Tterm - T0))[:, None], 2, axis=1)
    Vs = [None] * N if keep_V else None
    if keep_V:
        Vs.append(V.copy())
    for k in range(N - 1, -1, -1):
        g = H.SHGC * H.A_GL * irr[k]
        run = price[k] * p_el[k] * S.DT
        swc = c_sw + price[k] * H.E_START
        nxt = np.empty((n, 2))
        for u in (0, 1):
            T_inf = t_out[k] + (g - q * u) / lam_env
            Tp = T_inf + (Tg - T_inf) * decay
            if relaxed:
                i = np.clip(np.searchsorted(Tg, Tp) - 1, 0, n - 2)
                Vn = np.minimum(V[i, u], V[i + 1, u])
                Vn = np.where(Tp < Tg[0], V[0, u], np.where(Tp > Tg[-1], V[-1, u], Vn))
            else:
                Vn = _interp_inf(Tp, Tg, V[:, u])
            ok = step_ok(Tp, u, hi_b[k], hh)
            extra = (lam / n_occ) * np.maximum(Tp - hh, LO) if occ[k] else 0.0
            nxt[:, u] = np.where(ok, run * u + extra + Vn, INF)
            if ruled:   # R1-R2 fix the action outside F (relaxed: optimistic by h)
                nxt[:, u] = np.where((Tg >= rule_on + hh) if u == 0 else (Tg <= rule_off - hh), INF, nxt[:, u])
        Vn2 = np.empty((n, 2))
        Vn2[:, 0] = np.minimum(nxt[:, 0], swc + nxt[:, 1])   # prev off
        Vn2[:, 1] = np.minimum(nxt[:, 0], nxt[:, 1])          # prev on
        V = Vn2
        if keep_V:
            Vs[k] = V.copy()
    # value at the true initial state (T0, off); relaxed: optimistic neighbour
    if relaxed:
        i = int(np.clip(np.searchsorted(Tg, T0) - 1, 0, n - 2))
        L0 = float(min(V[i, 0], V[i + 1, 0]))
    else:
        L0 = float(np.interp(T0, Tg, V[:, 0]))
    days = N * S.DT / 24.0
    out = dict(L=L0 / days, h=h, Tg=Tg, n_occ=n_occ, days=days)
    if keep_V:
        out["V"] = Vs
    return out


def replay(city, w, price_v, lam, setback=False, n_grid=1601, c_sw=None, ruled=False,
           record=False, rule_on=None, rule_off=None, cap=None, terminal="uniform"):
    """Achievable schedule: exact-state one-step lookahead on the unrelaxed V,
    under the same predicate (step_ok) as the DP. Steps on which no action has a
    finite cost-to-go are counted in r["fallback_steps"] (must be 0).
    cap: occupied upper limit lowered to min(HI, cap) in the DP AND the replay (a restriction of
    the feasible set, so the schedule stays feasible for the true problem; clv_fit's second knob)."""
    c_sw = F.C_SW if c_sw is None else c_sw
    rule_on = RULE_ON if rule_on is None else rule_on
    rule_off = RULE_OFF if rule_off is None else rule_off
    d = lagrangian(city, w, price_v, lam, setback, n_grid, False, c_sw, keep_V=True, ruled=ruled,
                   rule_on=rule_on, rule_off=rule_off, cap=cap, terminal=terminal)
    Tg, Vs, n_occ = d["Tg"], d["V"], d["n_occ"]
    lam_env, t_out, irr, N, decay, occ, lo_b, hi_b, price, _ = _setup(city, w, price_v, setback, cap=cap)
    q, cp = H.Q_HVAC, H.COP_RATED
    p_el = q / H.cop_series(H.series(city, 168, w)[0]) / 1000.0     # per step

    fb = [0]

    def pol(T, prev, k):
        g = H.SHGC * H.A_GL * irr[k]
        best, bu = np.inf, -1
        for u in (0, 1):
            T_inf = t_out[k] + (g - q * u) / lam_env
            Tp = T_inf + (T - T_inf) * decay
            if not step_ok(Tp, u, hi_b[k]):
                continue
            if ruled and ((u == 0 and T >= rule_on) or (u == 1 and T <= rule_off)):
                continue
            c = price[k] * p_el[k] * S.DT * u + ((c_sw + price[k] * H.E_START) if (u == 1 and prev == 0) else 0.0)
            if occ[k]:
                c += (lam / n_occ) * max(Tp, LO)
            c += _interp_inf(Tp, Tg, Vs[k + 1][:, u])
            if c < best:
                best, bu = c, u
        if bu < 0:
            # no action with finite cost-to-go: counted, never silent. Fallback:
            # cool iff free float would break the upper limit.
            fb[0] += 1
            T_inf = t_out[k] + H.SHGC * H.A_GL * irr[k] / lam_env
            bu = int(T_inf + (T - T_inf) * decay > hi_b[k] + TOL)
        return bu
    r = S.sim(pol, city, F.FACES, C_TH, price, lo_b, hi_b, occ, 168, w, T0, c_sw=c_sw,
              t_min=T_MIN, record=record)
    r["fallback_steps"] = fb[0]
    r["terminal"] = terminal
    if terminal == "uniform":           # O4: J on the same terminal as the DP / bound
        r["J_energy_terminal"] = r["J"]
        r["J"] = uniform_J(r["J"], r["T_end"], c_sw, d["days"])
    return r


def dual_max(Lfun, target, n_lam=18, lam_max=24.0, iters=12):
    """max_lam [Lfun(lam) - lam*target/days] ; Lfun returns (L_per_day, days).
    Concave in lam; grid then ternary refinement. Returns (value, lam, curve)."""
    curve = {}
    def D(l):
        if l not in curve:
            L, days = Lfun(l)
            curve[l] = L
        return curve[l] - l * target / Dd[0]
    L0, d0 = Lfun(0.0)
    curve[0.0] = L0
    Dd = [d0]
    grid = list(np.linspace(0.0, lam_max, n_lam))
    vals = [(D(float(l)), float(l)) for l in grid]
    bv, bl = max(vals)
    step = lam_max / (n_lam - 1)
    a, b = max(0.0, bl - step), bl + step
    for _ in range(iters):
        x, y = a + (b - a) / 3, b - (b - a) / 3
        dx, dy = D(x), D(y)
        for v, l in ((dx, x), (dy, y)):
            if v > bv:
                bv, bl = v, l
        if dx < dy:
            a = x
        else:
            b = y
    return bv, bl, curve


# ------------------------------------------------------------------ CLV (F10, ruling Sec. 2.2)
CLV_TOL = 0.002            # K, two-sided: |T~_w(CLV) - T~_THERM,w| <= CLV_TOL


def clv_fit(city, w, price_v, target, setback=False, n_grid=3201, c_sw=None, ruled=False,
            rule_on=None, rule_off=None, tol=CLV_TOL, lam_hi0=0.01, lam_max=200.0, iters=60):
    """THE clairvoyant oracle of one held-out window (fit_status "oracle"): the Lagrangian replay
    whose clipped occupied mean is within +/- tol of `target` (THERM's on the window), lam_w found
    by bisection (geometric) on a bracket [lo, hi] with mean(lo) > target > mean(hi). The replay
    obeys step_ok, and the result must pass the one admissibility helper F.admissible and have no
    fallback step (else RuntimeError: an oracle that leaves D is a defect, never a row).
    Returns (lam, r, info) with info: resid (signed T - target), tol_met, n_replay, bracket.
    If the mean jumps across the tolerance band (staircase), the end point of the final bracket
    with the smaller |resid| is taken and tol_met = False (reported, not hidden)."""
    K = F.MEAN_KEY
    cache = {}

    def run(l):
        l = float(l)
        if l not in cache:
            r = replay(city, w, price_v, l, setback, n_grid, c_sw, ruled=ruled,
                       rule_on=rule_on, rule_off=rule_off)
            if r["fallback_steps"] or not F.admissible(r, w):
                raise RuntimeError(f"CLV replay {city} w{w} lam={l}: outside D "
                                   f"(fallback {r['fallback_steps']})")
            cache[l] = r
        return cache[l]

    def dev(l):
        return run(l)[K] - target

    def done(l, met):
        r = run(l)
        return l, r, dict(resid=float(r[K] - target), tol_met=bool(met), n_replay=len(cache),
                          bracket=(float(lo), float(hi) if hi is not None else float("nan")),
                          cap=float("nan"))

    lo, hi = 0.0, None
    if abs(dev(0.0)) <= tol:
        return done(0.0, True)
    if dev(0.0) < 0:          # even the pure cost minimiser is cooler than THERM: lam=0 is closest
        hi = 0.0
        return done(0.0, False)
    l = lam_hi0
    while l <= lam_max:
        d = dev(l)
        if abs(d) <= tol:
            hi = l
            return done(l, True)
        if d < 0:
            hi = l
            break
        lo, l = l, 2.0 * l
    if hi is None:
        raise RuntimeError(f"CLV {city} w{w}: mean above target at lam={lam_max}")
    for _ in range(iters):
        m = 0.5 * hi if lo == 0.0 else float(np.sqrt(lo * hi))
        d = dev(m)
        if abs(d) <= tol:
            return done(m, True)
        if d > 0:
            lo = m
        else:
            hi = m
        if hi - lo <= 1e-10 * max(hi, 1.0):
            break
    # The Lagrangian schedule's mean jumps across the band at the critical lam: the problem is
    # nearly linear in T, so the minimiser is near bang-bang in the comfort level and no single
    # lam hits the band. Second knob: at the warm side of the bracket (lam = lo, mean > target)
    # the occupied upper limit is lowered to `cap` (a restriction of D, so the schedule stays
    # feasible for the true problem); bisection on cap in [T_min, HI]. If the band is still not
    # hit, the closest schedule no warmer than target + tol is returned with tol_met = False
    # (Rule C scores it at its own mean; it is then not a lower-end candidate, Sec. 2.3).
    cands = [(lo, None, run(lo)), (hi, None, run(hi))]

    def run_cap(c):
        r = replay(city, w, price_v, lo, setback, n_grid, c_sw, ruled=ruled, rule_on=rule_on,
                   rule_off=rule_off, cap=c)
        if r["fallback_steps"]:
            return None                       # cap infeasible for the plant (too tight): skip
        if not F.admissible(r, w):
            raise RuntimeError(f"CLV capped replay {city} w{w} cap={c}: outside D")
        cands.append((lo, c, r))
        return r[K] - target
    a, b = LO + 0.05, HI                      # mean(cap=b) = mean(lo) > target
    for _ in range(40):
        c = 0.5 * (a + b)
        d = run_cap(c)
        if d is not None and (abs(d) <= tol or b - a < 1e-6):
            break
        if d is not None and d > 0:
            b = c
        else:                                 # too cool, or infeasible (too tight)
            a = c
    hit = [x for x in cands if abs(x[2][K] - target) <= tol]
    if hit:
        l, cp_, r = min(hit, key=lambda x: x[2]["J"])
    else:
        cool = [x for x in cands if x[2][K] - target <= tol]
        l, cp_, r = min(cool, key=lambda x: abs(x[2][K] - target))
    return l, r, dict(resid=float(r[K] - target), tol_met=bool(hit), n_replay=len(cache) + len(cands) - 2,
                      bracket=(float(lo), float(hi)), cap=float(cp_) if cp_ is not None else float("nan"))


def certificate_margin(J_a, T_a, bound_J_w, lam_w, T_star, days=7.0):
    """Per-window shifted dual certificate (ruling Sec. 2.3, CTL1-6): for any schedule a on window
    w, J_a,w >= J^bd_w - lam_w (T~_a,w - T~_THERM,w)/days, with J^bd_w = L_w(lam_w) - lam_w T*/days
    the relaxed per-window dual at THERM's mean. Returns the margin (must be >= 0)."""
    return float(J_a) - (float(bound_J_w) - float(lam_w) * (float(T_a) - float(T_star)) / days)


def ruled_cover(arm_rules=()):
    """F11 (F-10): (RULE_ON, RULE_OFF) of a ruled bound that covers every in-rules arm: RULE_ON >=
    every arm's R1 and RULE_OFF <= every arm's R2 (the training rules 23.80/22.40 always
    included). arm_rules: iterable of (R1, R2)."""
    r1 = [RULE_ON] + [float(a) for a, _ in arm_rules]
    r2 = [RULE_OFF] + [float(b) for _, b in arm_rules]
    return max(r1), min(r2)
