#!/usr/bin/env python3
"""Receding-horizon lam-MPC (round-3 ruling (b); round-4 fixes F5, F9).

  * Comfort device: the mean-temperature multiplier lam, stage cost
    (lam/n_occ) max(T', T_min) on occupied steps -- the same device as the
    clairvoyant arm and the bound. The upper limit is enforced pointwise (HI
    while occupied, AWAY_MAX while away); the corrected cold rule (ruling round
    4, Sec. 2.1) holds at every step: a COOLING step may never end below T_min,
    switching off / free float is always allowed (r3_dp.step_ok, shared with
    the DP, the CLV replay and the bound). No ceiling.
  * Forecast (F9). forecast="perfect": the planner sees the true in-horizon
    weather. forecast="persistence" ("tomorrow = yesterday", no seeds): issued
    at step k, the planner uses the measured current T_out t(k), the in-horizon
    T_out t^(j) = t(j - 96) (for horizons beyond 24 h the last measured day is
    repeated, t(j - 96 m) with m = ceil((j - k)/96), so only measured weather
    is ever used), and persisted irradiance I^(j) = I(j - 96 m'),
    m' = ceil((j - k + 1)/96), for every j >= k including the current step.
    (96 = ROLL = steps per day at the headline 15 min; F23 derives it from
    config.DT_MIN, as N_WIN = 168 h of steps.)
    The plant always evolves on the true weather. A callable
    forecast(k) -> (t_hat, irr_hat) (arrays over the window's index range) is
    also accepted; forecast=lambda k: (t_true, irr_true) reproduces the
    perfect run bit-for-bit (tests/test_core_mpc.py).
  * Terminal value: a ROLLOUT of the frozen TUNED rule for 24 h on persistence
    weather (the planner's weather over the last 24 h of the horizon,
    repeated), including energy, c_sw per start and the lam term, plus
    thermal-state pricing at the end. The occupancy schedule of the tail is the
    known schedule of the tail steps themselves (j + 96, R5-7). This is a causal
    heuristic: no closed-loop improvement over TUNED is guaranteed.
  * Grid: r3_dp.grid_for (band +- 0.10 K, lower edge extended below the
    window's lowest free-float equilibrium); its spacing h is reported per
    window (grid_h). The first action is evaluated at the EXACT state.
  * Fallback: if no action has a finite planned cost, the TUNED rule's action
    (the rollout base policy) is applied and counted in fallback_steps.
  * Rule A: lam fitted per city, horizon and forecast mode on the tuning
    windows: scan of {0} U logspace(-2, log10 24, 24), then two rounds of an
    8-point linear refinement in the bracket around the cheapest admissible
    value; Rule C on the held-out windows. lam is also reported as lam/lam*,
    lam* = Lambda * 168 h * p / COP (R5-1).

Usage: python3 mpc_lambda.py --city riyadh --horizons 0.25,1,2,6,24,48 [--ngrid 1601] [--out T21v3]
       python3 mpc_lambda.py --city riyadh --horizons 6,24 --forecast persistence --out T21v3_pers
       python3 mpc_lambda.py --city riyadh --horizons 24 --ngrid 3201 --lam-from T21v3 --out T21v3_conv
  F22 scenario options (non-headline values add a suffix to --out, e.g. _csw0.3, _ls1.01,
  _r23.66-22.4, so headline tables are never overwritten):
       --csw X          switching cost per start; the rollout/fallback TUNED rule is the
                        T5v2_switchcost_tuned row fitted at the same c_sw (error if absent)
       --lam-scale X    no fit: lam = X * lam*  (fit_status = fixed)
       --rule-on/--rule-off R   R1/R2 of the in-rules MPC (implies --ruled)
       --cth X          C_th in kJ/K (== RBRL_CTH; needs RBRL_TAG; the TUNED file under that tag
                        must have been fitted at the same C_th, checked from its provenance)
"""
from __future__ import annotations
import sys, os, json, time, argparse
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
if __name__ == "__main__" and "--cth" in sys.argv:        # F21/F22: --cth X == RBRL_CTH=X; must be set
    _i = sys.argv.index("--cth")                             # before headroom binds C_TH at import
    os.environ["RBRL_CTH"] = str(float(sys.argv[_i + 1])); del sys.argv[_i:_i + 2]
import config as CFG
import headroom as H
import setback as S
import final_tables as F
import r3_dp as D
import t1_v2 as T1V2
import rbrl_io as IO
import v3_names as V

LO, HI = H.BAND_LO, H.BAND_HI
C_TH, T0 = H.C_TH, CFG.T0                  # kJ/K: RBRL_CTH / --cth (F21), same hook as final_tables
PRICE = CFG.PRICE
K = F.MEAN_KEY
ROLL = CFG.STEPS_PER_DAY                    # 24 h rollout / persistence period (steps; 96 at 15 min)
N_WIN = CFG.STEPS_PER_WINDOW                # 168 h window (steps; 672 at 15 min)
HOURS = 168 + 48                            # weather loaded past the window (max horizon 48 h)
TUNED_FILE = V.AUX["TUNED_PARAMS"]         # headline c_sw: {city}|{tariff}|TUNED
TUNED_CSW_FILE = V.name("T5")               # c_sw sweep: rows (c_sw, city, on, off)
TUNED_SHA = {}                              # city -> (file, sha) of the TUNED parameters actually read


def _check_cth(name):
    """the TUNED file must have been fitted at this process's C_th (F22): the provenance env of
    its writer (.meta.json) carries RBRL_CTH; a file without provenance is accepted only at the
    headline C_th."""
    meta = f"{IO.R}/{name}.meta.json"
    if not os.path.exists(meta):              # V-code-22 (4): no provenance -> refused, not assumed
        raise SystemExit(f"{name}: no provenance sidecar {os.path.basename(meta)}; regenerate it "
                         f"under the current code (C_th / c_sw cannot be checked)")
    env = json.load(open(meta)).get("env", {})
    c = float(env.get("RBRL_CTH", H.C_TH_DEFAULT))
    if abs(c - C_TH) > 1e-9:
        raise SystemExit(f"{name}: TUNED fitted at C_th={c}, this run has C_th={C_TH} (set RBRL_TAG)")
    d = float(env.get("RBRL_DT_MIN", CFG.DT_MIN_DEFAULT))       # F23: same control interval
    if abs(d - CFG.DT_MIN) > 1e-9:
        raise SystemExit(f"{name}: TUNED fitted at dt={d:g} min, this run has dt={CFG.DT_MIN:g} min "
                         f"(set RBRL_TAG)")


def tuned_rule(city, tariff="inforce", c_sw=None):
    """TUNED (on, off) for this c_sw and C_th: the rollout base policy and the
    fallback. Read through rbrl_io (RBRL_TAG-aware; the tag selects the C_th
    scenario). Headline c_sw (H.C_SW): tuned_params_v2; any other c_sw: the
    matching row of the c_sw sweep T5v2_switchcost_tuned (no row = error, never
    a silent fallback to the headline rule). The file and its sha go into
    TUNED_SHA[city] and the provenance inputs of every table this process writes."""
    c_sw = F.C_SW if c_sw is None else float(c_sw)
    if abs(c_sw - H.C_SW) <= 1e-12:
        name = f"{TUNED_FILE}{IO.tag()}.json"
        _check_cth(name)
        p = IO.read_json(TUNED_FILE)[f"{city}|{tariff}|TUNED"]
        on, off = p["on"], p["off"]
    else:
        if tariff != "inforce":
            raise ValueError("the c_sw sweep is fitted at the in-force tariff only")
        name = f"{TUNED_CSW_FILE}{IO.tag()}.csv"
        _check_cth(name)
        rows = [r for r in IO.read_csv(TUNED_CSW_FILE)
                if r["city"] == city and abs(float(r["c_sw"]) - c_sw) <= 1e-12]
        if len(rows) != 1 or rows[0]["on"] in ("", None):
            raise SystemExit(f"{name}: no TUNED rule for {city} at c_sw={c_sw} (run t1_v2 csw first)")
        on, off = float(rows[0]["on"]), float(rows[0]["off"])
    TUNED_SHA[city] = (name, IO._sha(f"{IO.R}/{name}"))
    return on, off


def lam_star(city, price_v=PRICE, hours=168):
    """Marginal envelope price of 1 K of window-mean temperature (R5-1):
    lam* = Lambda * hours * p / COP_rated  [SAR per window per K]."""
    return H.lam_of(F.FACES, city) * hours * price_v / (1000.0 * H.COP_RATED)


# Headline MPC grid (V-res-1, ruling §15): 1601 nodes is converged to ~0.1 pt at fixed lambda
# (1601 vs 3201); 801 is not (0.25-0.60 pt). J5 checks 3201 at the fitted lambda (--lam-from).
HEADLINE_NGRID = 1601


def grid_h(city, w, n_grid, setback=False):
    Tg = D.grid_for(city, w, setback, n_grid, hours=HOURS)
    return float(Tg[1] - Tg[0])


def _persistence_src(k, NN):
    """Source indices (into the true series; negative = the day before the
    window) of the persistence forecast issued at step k, for j = 0..NN-1:
    T_out measured for j <= k, t(j - 96 m) beyond; irradiance measured for
    j < k, I(j - 96 m') from the current step on."""
    j = np.arange(NN)
    m_t = np.maximum(0, -((k - j) // ROLL))            # ceil((j-k)/96), 0 for j <= k
    m_i = np.maximum(0, -((k - j - 1) // ROLL))        # ceil((j-k+1)/96), 0 for j < k
    return j - ROLL * m_t, j - ROLL * m_i


def _lerp(a, b, t):
    """linear interpolation that treats an infeasible (inf) neighbour as
    infeasible instead of producing NaN."""
    with np.errstate(invalid="ignore"):
        v = a + t * (b - a)
    return np.where(np.isfinite(a) & np.isfinite(b), v, np.inf)


RULE_ON, RULE_OFF = CFG.RULE_ON, CFG.RULE_OFF      # R1, R2 at the training ceiling (config, F8)


def mpc_lams(city, w, lams, horizon_h, n_grid=801, rule=None, price_v=PRICE, ruled=False,
             setback=False, sb_rule=None, return_actions=False, forecast="perfect", N=N_WIN, backoff=0.0):
    """One window, vectorised over lam. The horizon DP's value function depends
    only on the step, the forecast and lam (not on the realised state), so every
    lam's trajectory advances together; V has shape (n, L), and a batch run
    equals the single runs (test 9). forecast: "perfect", "persistence" or a
    callable k -> (t_hat, irr_hat). N < 672 truncates the window (tests only)."""
    q, cp = H.Q_HVAC, H.COP_RATED
    lam_env = H.lam_of(F.FACES, city)
    Hh = int(round(horizon_h / S.DT))
    if Hh < 1 or horizon_h > 48.0 + 1e-9 or abs(Hh * S.DT - horizon_h) > 1e-9 or N + Hh > int(round(HOURS / S.DT)):
        raise ValueError(f"horizon {horizon_h} h: must be a positive multiple of {S.DT} h, <= 48 h")
    lams = np.asarray(lams, float); L = len(lams)
    t_out, irr, NN = H.series(city, HOURS, w)
    decay = float(np.exp(-S.DT * 3600.0 * lam_env / (C_TH * 1e3)))
    p_el = q / H.cop_series(t_out) / 1000.0                     # per step
    c_sw = F.C_SW
    swc = c_sw + price_v * H.E_START                            # per start (planning and realised)
    occ_x = S.occupancy(NN + ROLL) if setback else np.ones(NN + ROLL, bool)   # known schedule, tail incl.
    occ = occ_x[:NN]
    lo_b, hi_b = S.bands(occ, LO, HI, CFG.AWAY_FLOOR, H.AWAY_MAX)
    if backoff:        # second comfort knob (ruling §16): the PLANNER's occupied ceiling is HI - b;
        hi_b = np.where(occ, hi_b - float(backoff), hi_b)   # comfort is still scored against HI
    n_occ = int(occ[:N].sum())
    wl = lams / n_occ                                               # (L,)
    if setback:
        import setback_arms as SA
        on_at, off_at, LEAD = sb_rule[:3]
        A_ON = sb_rule[3] if len(sb_rule) > 3 else CFG.AWAY_ON
        dnext = SA.steps_to_occ(occ_x)
    else:
        on_at, off_at = rule if rule else tuned_rule(city)
        LEAD, dnext, A_ON = 0, np.zeros(NN + ROLL, int), CFG.AWAY_ON
    Tg = D.grid_for(city, w, setback, n_grid, hours=HOURS); n = len(Tg)
    therm_c = price_v * C_TH * 1e3 / 3.6e6 / cp
    # true weather -> plant; planner weather per issue time k (forecast)
    ginf = H.SHGC * H.A_GL * irr
    Tinf = (t_out + ginf / lam_env, t_out + (ginf - q) / lam_env)
    run_c = price_v * p_el * S.DT                               # per step
    perfect = isinstance(forecast, str) and forecast == "perfect"
    if not perfect:
        if callable(forecast):
            fc = forecast
        elif forecast == "persistence":
            tx, ix, _ = H.series(city, HOURS + 24, w - 1)       # one day of history first
            assert np.array_equal(tx[ROLL:], t_out) and np.array_equal(ix[ROLL:], irr)
            def fc(k):
                st, si = _persistence_src(k, NN)
                return tx[st + ROLL], ix[si + ROLL]
        else:
            raise ValueError(f"forecast={forecast!r}")

    def planner(k):
        """(Tinf0, Tinf1, run_c) the planner uses when issuing at step k."""
        if perfect:
            return Tinf[0], Tinf[1], run_c
        th, ih = fc(k)
        gh = H.SHGC * H.A_GL * ih
        return th + gh / lam_env, th + (gh - q) / lam_env, price_v * (q / H.cop_series(th) / 1000.0) * S.DT

    # interpolation weights, feasibility and stage cost of the grid map at step
    # j. Perfect forecast: identical for every issue time, keyed (j, u). Other
    # forecasts: keyed (j, u, planner T_inf, planner run cost), i.e. exactly
    # on what the entry depends on, so entries are shared between issue times
    # only when the forecast for step j agrees. Entries j <= k are dropped.
    IW = {}
    def iw(j, u, Ti, rc):
        key = (u,) if perfect else (u, Ti, rc)
        d = IW.setdefault(j, {})
        if key not in d:
            Tp = Ti + (Tg - Ti) * decay
            ok = D.step_ok(Tp, u, hi_b[j])     # corrected cold rule (ruling Sec. 2.1)
            x = np.clip(Tp, Tg[0], Tg[-1])
            i = np.clip(np.searchsorted(Tg, x) - 1, 0, n - 2)
            t = ((x - Tg[i]) / (Tg[i + 1] - Tg[i]))[:, None]
            stage = rc * u + (wl[None, :] * np.maximum(Tp, LO)[:, None] if occ[j] else 0.0)
            d[key] = (i, t, np.where(ok[:, None], stage, np.inf))
        return d[key]

    def rollout(end, P0, P1, RC):
        """V_T(T, prev) on the grid: TUNED for ROLL steps from the horizon end,
        weather = the planner's weather over [end-96, end) (persistence), schedule
        = the tail steps' own (end .. end+95)."""
        idx = np.arange(max(0, end - ROLL), end)
        if len(idx) < ROLL:
            idx = np.concatenate([np.full(ROLL - len(idx), idx[0]), idx])
        sched = np.arange(end, end + ROLL)
        out = []
        for p0 in (0, 1):
            T = Tg.copy(); prev = np.full(n, p0); c = np.zeros(n); csum = np.zeros(n)
            for j, js in zip(idx, sched):
                a_on, a_off = (on_at, off_at) if dnext[js] <= LEAD else (A_ON, A_ON - 0.8)
                u = np.where(T >= a_on, 1, np.where(T <= a_off, 0, prev))
                c += np.where((u == 1) & (prev == 0), swc, 0.0) + RC[j] * u
                Ti = np.where(u == 1, P1[j], P0[j])
                T = Ti + (T - Ti) * decay
                if occ_x[js]:
                    csum += np.maximum(T, LO)
                prev = u
            out.append(c[:, None] + wl[None, :] * csum[:, None] + (therm_c * (T - T0))[:, None])
        return out

    T = np.full(L, T0); prev = np.zeros(L, int); ar = np.arange(L); ACT = []
    J = np.zeros(L); E = np.zeros(L); starts = np.zeros(L); fb = np.zeros(L)
    Tsum = np.zeros(L); Tcl = np.zeros(L); over = np.zeros(L); under = np.zeros(L)
    cmd_u = np.zeros(L); ff_u = np.zeros(L); Tmax_away = np.full(L, -np.inf)
    for k in range(N):
        end = k + Hh
        for j in [j for j in IW if j <= k]:
            del IW[j]
        P0, P1, RC = planner(k)
        V0, V1 = rollout(end, P0, P1, RC)
        for j in range(end - 1, k, -1):
            i0, t0, s0 = iw(j, 0, P0[j], RC[j]); i1, t1, s1 = iw(j, 1, P1[j], RC[j])
            n0 = s0 + _lerp(V0[i0], V0[i0 + 1], t0)
            n1 = s1 + _lerp(V1[i1], V1[i1 + 1], t1)
            if ruled:                                   # R1-R2 fix the action outside F
                n0 = np.where((Tg >= RULE_ON)[:, None], np.inf, n0)
                n1 = np.where((Tg <= RULE_OFF)[:, None], np.inf, n1)
            V0 = np.minimum(n0, swc + n1); V1 = np.minimum(n0, n1)
        best = np.full(L, np.inf); bu = np.full(L, -1)
        for u, V, Pu in ((0, V0, P0), (1, V1, P1)):
            Ti = Pu[k]
            Tp = Ti + (T - Ti) * decay
            ok = D.step_ok(Tp, u, hi_b[k])
            x = np.clip(Tp, Tg[0], Tg[-1])
            i = np.clip(np.searchsorted(Tg, x) - 1, 0, n - 2)
            t = (x - Tg[i]) / (Tg[i + 1] - Tg[i])
            Vn = _lerp(V[i, ar], V[i + 1, ar], t)
            c = RC[k] * u + ((u == 1) & (prev == 0)) * swc + (wl * np.maximum(Tp, LO) if occ[k] else 0.0) + Vn
            c = np.where(ok, c, np.inf)
            if ruled:
                c = np.where((T >= RULE_ON) if u == 0 else (T <= RULE_OFF), np.inf, c)
            better = c < best
            best = np.where(better, c, best); bu = np.where(better, u, bu)
        nofeas = bu < 0
        fb += nofeas
        a_on, a_off = (on_at, off_at) if dnext[k] <= LEAD else (A_ON, A_ON - 0.8)
        u_base = np.where(T >= a_on, 1, np.where(T <= a_off, 0, prev))   # TUNED fallback
        if ruled:                                   # the fallback obeys R1/R2 too (V-code-22 (3))
            u_base = np.where(T >= RULE_ON, 1, np.where(T <= RULE_OFF, 0, u_base))
        u = np.where(nofeas, u_base, bu)
        if return_actions:
            ACT.append(int(u[0]))
        st = (u == 1) & (prev == 0)
        J += st * swc + u * run_c[k]; starts += st; E += u * p_el[k] * S.DT + st * H.E_START
        Ti = np.where(u == 1, Tinf[1][k], Tinf[0][k])
        T = Ti + (T - Ti) * decay
        cmd_u += (u == 1) * np.maximum(0.0, LO - T - 1e-9) * S.DT
        if occ[k]:
            Tsum += T; Tcl += np.maximum(T, LO)
            over += np.maximum(0.0, T - HI - 1e-9) * S.DT; under += np.maximum(0.0, LO - T - 1e-9) * S.DT
            ff_u += (u == 0) * np.maximum(0.0, LO - T - 1e-9) * S.DT
        else:
            Tmax_away = np.maximum(Tmax_away, T)
        prev = u
    J += therm_c * (T - T0)
    days = N * S.DT / 24.0
    gh = float(Tg[1] - Tg[0])
    return [dict(J=J[l] / days, E=E[l] / days, f_s=starts[l] / days,
                 T_mean_occ=Tsum[l] / n_occ, T_mean_occ_clip=Tcl[l] / n_occ,
                 deg_h_over=over[l], deg_h_under=under[l],
                 deg_h_occ=over[l] + under[l], fallback_steps=int(fb[l]),
                 deg_h_cmd_under=cmd_u[l], deg_h_ff_under=ff_u[l], T_end=float(T[l]),
                 T_max_away=float(Tmax_away[l]) if np.isfinite(Tmax_away[l]) else float("nan"),
                 grid_h=gh,
                 **({"actions": ACT} if return_actions else {}))
            for l in range(L)]


def mpc_actions(city, w, lam, horizon_h, n_grid=801, forecast="perfect"):
    """action sequence of one MPC run (for imitation demonstrations)."""
    sb = SETBACK[0]
    r = mpc_lams(city, w, [lam], horizon_h, n_grid, setback=sb is not None, sb_rule=sb,
                 return_actions=True, forecast=forecast)
    return r[0]["actions"]


def mpc_batch(city, windows, lams, horizon_h, n_grid=801, rule=None, price_v=PRICE, ruled=False,
              forecast="perfect", backoff=None):
    """backoff None -> BACKOFF[0], the occupied-ceiling back-off of the last fit_lambda (0 when the
    lam knob was admissible), so every caller evaluates the fitted pair (lam, b)."""
    sb = SETBACK[0]
    b = BACKOFF[0] if backoff is None else backoff
    return [mpc_lams(city, w, lams, horizon_h, n_grid, rule, price_v, ruled,
                     setback=sb is not None, sb_rule=sb, forecast=forecast, backoff=b) for w in windows]


RULED = [False]
BACKOFF = [0.0]        # occupied-ceiling back-off b (K) of the fitted cell; 0 = lam knob (ruling §16)
KNOB = {"knob": "lambda", "backoff": 0.0}    # set by fit_lambda: which knob met A4, and b
BACKOFF_GRID = np.round(np.arange(0.0, 0.6 + 1e-9, 0.05), 3)       # coarse b grid (K)
BACKOFF_RES = 0.005                                                 # final b resolution (K)
SETBACK = [None]       # (on, off, lead) of the fitted setback rule -> occupancy-aware MPC
LAMS = [0.0] + list(np.logspace(-2, np.log10(24.0), 24))


def fit_lambda(city, hh, th, n_grid, log, forecast="perfect", with_status=False, batch=None, select=None,
               target=None):
    """Rule A4 over lam (final_tables.select_rows: admissible() per tuning window, pooled 0.03 K,
    one fallback 0.10 K, the A4 objective; ties -> lowest candidate index = evaluation order).
    Candidates: the scan LAMS (25 values, batched), then -- only if nothing is admissible -- up
    to 4 rounds of 4-point bisection of the pooled mean between the bracketing scan values, then
    two rounds of an 8-point linear refinement between the neighbours of the selected value.
    The comparator family follows the run: setback (SETBACK[0] set) -> THERM scored on the
    timetable's occupied steps. th is not used for selection (the target is THERM's pooled
    clipped mean from the comparator family); kept for the call signature.
    Second knob (ruling §16), ONLY when no lam is admissible even at 0.10 K (the lam device is
    near bang-bang: the pooled mean jumps across THERM's target between two scan values): lam is
    fixed at the largest admissible lam on the WARM side of the jump (pooled mean >= target; the
    cost-optimal schedule just short of the jump -- a back-off can only cool, so the cool side
    cannot be moved onto the target), and the planner's occupied ceiling is lowered to HI - b,
    b >= 0 selected by the same A4 rule on BACKOFF_GRID, then bisection of the pooled mean between
    the bracketing grid values and a +-BACKOFF_RES refinement around the selection, to
    BACKOFF_RES. fit_status keeps the §2.2 set; KNOB records knob = "lambda" | "backoff" and b,
    BACKOFF[0] carries b to mpc_batch. Cells with an admissible lam never reach this code (their
    candidates, selection and outputs are those of the lam-only fit).
    THE lambda selection of every MPC (V-res-5): the multi-zone MPC (mz_mpc) passes its own
      batch(lams, backoff) -> [per tuning window: [per lam: metric dict]] (backoff 0 = lam knob),
      select(cands, rows) -> (index or None, fit_status, info) (A4 on the dwelling mean, Rule C),
      target = the pooled THERM clipped mean of its comparator family;
    the defaults are the single-zone ones (mpc_batch, F._select_rows, F._target).
    Returns (lam, relaxed_pooled, all_rows) or, with_status=True, also fit_status."""
    tw = list(F.TUNE_W)
    BACKOFF[0] = 0.0
    KNOB.clear(); KNOB.update(knob="lambda", backoff=0.0)
    sb = SETBACK[0] is not None
    cands, rows, allr = [], [], []
    def evalset(lams):
        lams = [float(x) for x in lams if float(x) not in cands]
        if not lams:
            return
        res = (mpc_batch(city, tw, lams, hh, n_grid, ruled=RULED[0], forecast=forecast) if batch is None
               else batch(lams, 0.0))                                   # BACKOFF[0] = 0
        for l, lam in enumerate(lams):
            rs = [res[i][l] for i in range(len(tw))]
            cands.append(lam); rows.append(rs)
            m = np.array([r[K] for r in rs])
            allr.append(dict(lam=lam, J=float(np.mean([r["J"] for r in rs])), means=m, pmean=float(m.mean()),
                             adm=all(F.admissible(r, w) for r, w in zip(rs, tw))))
            log(f"    lam={lam:.5f} J={allr[-1]['J']:.4f} pooled_mean={m.mean():.4f} "
                f"adm={allr[-1]['adm']} fb={sum(r['fallback_steps'] for r in rs)}")
    def select_():
        i, status, info = (F._select_rows(cands, rows, city, PRICE, tw, setback=sb) if select is None
                           else select(cands, rows))
        log(f"    -> {status} lam={cands[i] if i is not None else None} {info}")
        return i, status
    def ret(lam, status):
        out = (lam, None if lam is None else status == "pooled_0.10", allr)
        return out + (status,) if with_status else out
    evalset(LAMS)
    i, status = select_()
    if i is None:
        tgt = F._target(city, PRICE, tw, None, setback=sb) if target is None else float(target)
        cond1 = [r for r in allr if r["adm"]]
        lo = max([r for r in cond1 if r["pmean"] >= tgt], key=lambda r: r["lam"], default=None)
        hi = min([r for r in cond1 if r["pmean"] < tgt], key=lambda r: r["lam"], default=None)
        for _ in range(4):
            if lo is None or hi is None:
                break
            new = list(np.linspace(lo["lam"], hi["lam"], 6)[1:-1])
            evalset(new)
            i, status = select_()
            if i is not None:
                break
            rr = [r for r in allr if r["adm"] and r["lam"] in new]
            lo = max([r for r in rr + [lo] if r["pmean"] >= tgt], key=lambda r: r["lam"])
            hi = min([r for r in rr + [hi] if r["pmean"] < tgt], key=lambda r: r["lam"])
        if i is None:
            warm = [r for r in allr if r["adm"] and r["pmean"] >= tgt]
            if not warm:
                log("    back-off knob: no admissible lam on the warm side of the target; fit_status none")
                return ret(None, "none")
            lam_w = max(warm, key=lambda r: r["lam"])["lam"]
            b, status = fit_backoff(city, hh, lam_w, tgt, n_grid, log, forecast, batch=batch, select=select)
            if b is None:
                return ret(None, "none")
            BACKOFF[0] = b
            KNOB.update(knob="backoff", backoff=b)
            return ret(lam_w, status)
    for _ in range(2):
        ls = sorted(cands)
        j = ls.index(cands[i])
        a_, b_ = ls[max(0, j - 1)], ls[min(len(ls) - 1, j + 1)]
        evalset(np.linspace(a_, b_, 10)[1:-1])
        i, status = select_()
    return ret(cands[i], status)


def fit_backoff(city, hh, lam, tgt, n_grid, log, forecast="perfect", batch=None, select=None):
    """A4 over the occupied-ceiling back-off b at fixed lam (ruling §16). Candidates in order: the
    coarse BACKOFF_GRID; if nothing is admissible, up to 6 rounds of 4-point bisection of the
    pooled mean between the bracketing b values (warm side mean >= target, cool side < target);
    then +-BACKOFF_RES neighbours of the selection until it no longer moves (b on the
    BACKOFF_RES lattice). Returns (b, fit_status) or (None, "none")."""
    tw = list(F.TUNE_W)
    sb = SETBACK[0] is not None
    cands, rows, info = [], [], {}
    def q(b):
        return float(np.round(round(float(b) / BACKOFF_RES) * BACKOFF_RES, 3))
    def evalset(bs):
        for b in bs:
            b = q(b)
            if b in cands or b < 0:
                continue
            rs = [r[0] for r in (mpc_batch(city, tw, [lam], hh, n_grid, ruled=RULED[0], forecast=forecast,
                                           backoff=b) if batch is None else batch([lam], b))]
            cands.append(b); rows.append(rs)
            m = np.array([r[K] for r in rs])
            info[b] = dict(pmean=float(m.mean()), adm=all(F.admissible(r, w) for r, w in zip(rs, tw)))
            log(f"    backoff b={b:.3f} (lam={lam:.5f}) J={np.mean([r['J'] for r in rs]):.4f} "
                f"pooled_mean={m.mean():.4f} adm={info[b]['adm']} fb={sum(r['fallback_steps'] for r in rs)}")
    def select_():
        i, status, inf = (F._select_rows(cands, rows, city, PRICE, tw, setback=sb) if select is None
                          else select(cands, rows))
        log(f"    -> backoff {status} b={cands[i] if i is not None else None} {inf}")
        return i, status
    evalset(BACKOFF_GRID)
    i, status = select_()
    for _ in range(6):
        if i is not None:
            break
        adm = [b for b in cands if info[b]["adm"]]
        lo = max([b for b in adm if info[b]["pmean"] >= tgt], default=None)
        hi = min([b for b in adm if info[b]["pmean"] < tgt and (lo is None or b > lo)], default=None)
        if lo is None or hi is None or hi - lo <= BACKOFF_RES + 1e-12:
            break
        evalset(np.linspace(lo, hi, 6)[1:-1])
        i, status = select_()
    if i is None:
        log("    back-off knob: no admissible b; fit_status none")
        return None, "none"
    for _ in range(40):
        b0 = cands[i]
        evalset([b0 - BACKOFF_RES, b0 + BACKOFF_RES])
        i, status = select_()
        if cands[i] == b0:
            break
    return cands[i], status


def scenario_suffix(c_sw, lam_scale, rule_on, rule_off):
    """non-headline MPC options never write into the headline table names (S17)."""
    sfx = ""
    if abs(c_sw - H.C_SW) > 1e-12:
        sfx += f"_csw{c_sw:g}"
    if lam_scale is not None:
        sfx += f"_ls{lam_scale:g}"
    if rule_on is not None or rule_off is not None:
        sfx += f"_r{RULE_ON:g}-{RULE_OFF:g}"
    return sfx


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True)
    ap.add_argument("--horizons", default="6,24,48", help="hours, multiples of the control step (0.25 h headline; e.g. 0.25,1,2,6,24,48)")
    ap.add_argument("--ngrid", type=int, default=HEADLINE_NGRID)
    ap.add_argument("--out", default=None,
                    help="file stem without _<city>; default from v3_names.mpc_stem (T21v3, T21v3_pers, "
                         "T21v3_conv for --ngrid != HEADLINE_NGRID (1601), T16v3 in rules) + scenario suffix")
    ap.add_argument("--forecast", default="perfect", choices=("perfect", "persistence"))
    ap.add_argument("--lam-from", default=None, help="reuse fitted lam from this table (RBRL_TAG-aware)")
    ap.add_argument("--lam-scale", type=float, default=None,
                    help="no fit: lam = X * lam*, lam* = Lambda*168h*p/COP (R5-1); fit_status=fixed")
    ap.add_argument("--csw", type=float, default=None, help="switching cost per start (default F.C_SW)")
    ap.add_argument("--rule-on", type=float, default=None, help="R1 of the in-rules MPC (implies --ruled)")
    ap.add_argument("--rule-off", type=float, default=None, help="R2 of the in-rules MPC (implies --ruled)")
    ap.add_argument("--ruled", action="store_true", help="MPC inside R1-R2 (C4c)")
    # --cth X is consumed before import (RBRL_CTH); listed here for --help only
    a = ap.parse_args(argv)
    H.check_scenario_tag()
    global RULE_ON, RULE_OFF
    if a.rule_on is not None:
        RULE_ON = a.rule_on
    if a.rule_off is not None:
        RULE_OFF = a.rule_off
    RULED[0] = a.ruled or a.rule_on is not None or a.rule_off is not None
    if a.csw is not None:
        F.C_SW = a.csw                       # read at call time by mpc_lams, THERM and equalise
    city = a.city
    sfx = scenario_suffix(F.C_SW, a.lam_scale, a.rule_on, a.rule_off)
    out = (a.out + sfx) if a.out else V.mpc_stem(a.forecast, RULED[0], a.ngrid != HEADLINE_NGRID, sfx)
    hours_list = [float(x) for x in a.horizons.split(",")]
    for hh in hours_list:
        if abs(round(hh / S.DT) * S.DT - hh) > 1e-9 or not 0 < hh <= 48:
            ap.error(f"horizon {hh}: must be a positive multiple of {S.DT} h, <= 48 h")
    LOG = []
    logname = f"{IO.ROOT}/logs_{out}{IO.tag()}_{city}.txt"
    def log(s):
        print(s, flush=True); LOG.append(s)
    def flush_log():
        IO.write_text(logname, "\n".join(LOG) + "\n", comment="#")
    th = {w: F.therm_run(city, w, PRICE) for w in F.WINDOWS}
    base = tuned_rule(city)
    lstar = lam_star(city, PRICE)
    gh = [grid_h(city, w, a.ngrid) for w in F.WINDOWS]
    log(f"{city}: forecast={a.forecast} c_sw={F.C_SW:g} C_th={C_TH:g} ruled={RULED[0]} "
        f"R1/R2={RULE_ON:g}/{RULE_OFF:g} grid n={a.ngrid} spacing h = {min(gh)*1e3:.2f}-{max(gh)*1e3:.2f} mK "
        f"(per window), lam* = {lstar:.4f}, TUNED base {base} from {TUNED_SHA.get(city)}")
    summ, perw = [], []
    prior = {}
    if a.lam_from:
        for r in IO.read_csv(f"{a.lam_from}_{city}"):
            if r.get("forecast", "perfect") == a.forecast:
                st = r.get("fit_status") or ""
                if st not in F.FIT_STATUSES or st == "none":     # V-code-22 (2): never relabel
                    raise SystemExit(f"--lam-from {a.lam_from}_{city}: row H={r['horizon_h']} has "
                                     f"fit_status {st!r} (not a Sec. 2.2 status); refit instead")
                prior[float(r["horizon_h"])] = (float(r["lam"]), st == "pooled_0.10", st,
                                                float(r.get("backoff") or 0.0))
    for hh in hours_list:
        t0 = time.time()
        BACKOFF[0] = 0.0
        if a.lam_scale is not None:
            lam, pooled, status = a.lam_scale * lstar, None, "fixed"
        elif hh in prior:
            lam, pooled, status, BACKOFF[0] = prior[hh]
        else:
            lam, pooled, _, status = fit_lambda(city, hh, th, a.ngrid, log, forecast=a.forecast,
                                                with_status=True)
        if lam is None:
            log(f"{city} H={hh:g}h forecast={a.forecast}: no admissible lam (fit_status=none)")
            flush_log(); continue
        res = mpc_batch(city, list(F.EVAL_W), [lam], hh, a.ngrid, ruled=RULED[0], forecast=a.forecast)
        runs = {w: res[i][0] for i, w in enumerate(F.EVAL_W)}
        s, pw = T1V2.evaluate(city, PRICE, runs, th)   # carries the Sec. 2.1 metrics, T_end, fallback_steps
        ghs = [runs[w]["grid_h"] for w in F.EVAL_W]
        row = dict(city=city, horizon_h=hh, forecast=a.forecast, n_grid=a.ngrid,
                   grid_h_min=min(ghs), grid_h_max=max(ghs), c_sw=F.C_SW, c_th=C_TH,
                   ruled=RULED[0], rule_on=RULE_ON if RULED[0] else "", rule_off=RULE_OFF if RULED[0] else "",
                   lam=lam, lam_star=lstar, lam_over_lam_star=lam / lstar, lam_scale=a.lam_scale or "",
                   relaxed_pooled=pooled, fit_status=status,
                   tuned_on=base[0], tuned_off=base[1], tuned_src=TUNED_SHA[city][0],
                   tuned_sha=TUNED_SHA[city][1], **s,
                   knob="backoff" if BACKOFF[0] else "lambda", backoff=BACKOFF[0])
        summ.append(row)
        for r in pw:
            perw.append(dict(city=city, horizon_h=hh, forecast=a.forecast, n_grid=a.ngrid,
                             grid_h=runs[r["window"]]["grid_h"], c_sw=F.C_SW, c_th=C_TH, lam=lam,
                             lam_over_lam_star=lam / lstar, fit_status=status, **r,
                             knob="backoff" if BACKOFF[0] else "lambda", backoff=BACKOFF[0]))
        log(f"{city} H={hh:g}h {a.forecast} n={a.ngrid} lam={lam:.4f} ({lam / lstar:.3f} lam*) {status} "
            f"knob={'backoff b=%.3f' % BACKOFF[0] if BACKOFF[0] else 'lambda'} "
            f"s_eq={s['s_pooled_eq']:+.2f}% s_raw={s['s_raw']:+.2f}% dT={s['dT_pooled']:+.4f} "
            f"starts={s['start_sav_eq']:+.1f}% over={s['deg_h_over']:.3f} under={s['deg_h_under']:.3f} "
            f"cmd_under={s['deg_h_cmd_under']:.3f} T_end={s['T_end_mean']:.3f} "
            f"fallback={s['fallback_steps']} ({time.time()-t0:.0f}s)")
        T1V2.write(f"{out}_{city}", summ)
        T1V2.write(f"{out}_{city}_perwindow", perw)
        flush_log()


if __name__ == "__main__":
    main()
