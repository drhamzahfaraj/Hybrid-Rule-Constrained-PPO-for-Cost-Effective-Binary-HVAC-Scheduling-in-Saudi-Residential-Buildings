#!/usr/bin/env python3
"""D1: the exact one-step model-based shield (RULING_round4 §3 F13; TEAM_cs_3 D1).

Replaces the fixed guard margins (eps_hot = 0.20 K, eps_cold = 0.40 K of rbrl_ppo.apply_rules and
t1_v2.fit_guard) by the two exact one-step predicates of the plant model every arm is scored on
(setback.sim / final_tables.sim_hyst_batch):

    a        = exp(-dt * Lambda / C_th)                         (one-step decay)
    Tinf_u[k] = t_out[k] + (SHGC * A_gl * irr[k] - Q * u) / Lambda
    T'(u)    = Tinf_u[k] + (T - Tinf_u[k]) * a                   (post-step state of action u)

    force ON   iff  T'(0) > upper[k] - sigma      one more free-float step would breach the ceiling
    force OFF  iff  T'(1) < T_min    + sigma      a cooling step would end below T_min (cold rule)

upper[k] = cap on occupied steps (cap = HI = 24 C unless a ceiling is fitted) and AWAY_MAX on away
steps; T_min = BAND_LO at EVERY step (§2.1 corrected cold rule: a cooling step may never end below
T_min; free float is unrestricted, so the shield never forces cooling to protect the floor).
If both predicates hold (never seen on the windows: the cooling drop is ~0.4 K on a 2 K band) the
ceiling wins and the step is counted in `conflict_steps`.

By construction, with sigma >= 0 and the exact model: deg_h_over = 0 (by induction from T0 <= cap:
an unforced step ends <= cap - sigma whatever the base action, because cooling only lowers T';
a forced-on step is a convex combination of T <= cap and Tinf_1 << cap) and deg_h_cmd_under = 0
(cooling is never executed where it would end below T_min), unless conflict_steps > 0.
tests/test_shield.py checks both on TUNE_W for the latch and for random base policies.

Arms
  latch          base action = previous action (hold); the shield alone decides every switch.
                 Its comfort parameter is the ceiling `cap` (as the guard's), fitted per sigma.
  ppo:<model>    a saved RBRL PPO model (results/models/*.zip, v2 8-feature observation) whose
                 deterministic action is overridden by the shield instead of the eps rule layer
                 (post-posed shielding, Alshiekh et al. 2018). No retraining.
  any callable   shielded(base_policy, ...) wraps any setback.sim policy(T, prev, k).

Selection (Rule A4, §2.2): per sigma in SIGMAS = (0, 0.05, 0.10) K, the ceiling is chosen on
TUNE_W: admissible iff deg_h_over_w = 0 and deg_h_cmd_under_w = 0 in EVERY tuning window and the
pooled clipped mean is within 0.03 K of THERM's (fallback 0.10 K, identical for all arms); the
objective is the equalised tuning cost ratio sum_w J_w / sum_w J_THERM(delta_w),w. fit_status in
{pooled_0.03, pooled_0.10, none}. The sigma row reported in the headline is the cheapest admissible
one; all three rows are written (descriptive sensitivity, §2.4).

TODO(F6/F7): when final_tables gains F.admissible(r, w) and the A4 precompute of J_THERM(delta)
per tuning window, `_admissible_w` and `therm_curve` defer to them automatically (hasattr checks
below); until then they implement the documented §2.1/§2.2 interface locally.

Usage (nice, OMP_NUM_THREADS=1):
  python3 shield.py latch <city> [--price 0.18]
  python3 shield.py ppo   <city> [--models 'results/models/rbrl_ppo5_v2_<city>_<city>_*.zip']
  -> results/T_D1_<arm>_<city>[ _perwindow].csv via rbrl_io (fit_status, provenance)
"""
from __future__ import annotations
import sys, os, glob, argparse, time
sys.path.insert(0, os.environ.get("RBRL_ROOT", "/home/claude/rbrl"))
import numpy as np

import headroom as H
import setback as S
import final_tables as F

SIGMAS = (0.0, 0.05, 0.10)
TOL = 1e-9                         # same comparison convention as setback.sim / sim_hyst_batch
POOL_TOL, POOL_TOL_FALLBACK = 0.03, 0.10
K = F.MEAN_KEY


# ----------------------------------------------------------------- the shield itself
class Shield:
    """Exact one-step shield for one city-window. Vectorised: T, cap and sigma may be (P,)."""

    def __init__(self, city, w, hours=168, c_th=None, faces=None, occ=None, t_min=None,
                 away_max=None):
        c_th = F.C_TH if c_th is None else c_th
        faces = F.FACES if faces is None else faces
        self.t_out, self.irr, self.N = H.series(city, hours, w)
        self.lam = H.lam_of(faces, city)
        self.a = float(np.exp(-H.DT * 3600.0 * self.lam / (c_th * 1e3)))
        g = H.SHGC * H.A_GL * np.asarray(self.irr, float)
        self.tinf0 = self.t_out + g / self.lam                       # same expression as S.sim
        self.tinf1 = self.t_out + (g - H.Q_HVAC) / self.lam
        self.occ = np.ones(self.N, bool) if occ is None else np.asarray(occ, bool)[:self.N]
        self.t_min = H.BAND_LO if t_min is None else t_min
        self.away_max = H.AWAY_MAX if away_max is None else away_max

    def next_T(self, T, k, u):
        ti = self.tinf1[k] if u else self.tinf0[k]
        return ti + (T - ti) * self.a

    def force(self, T, k, cap=None, sigma=0.0):
        """(force_on, force_off) booleans (arrays if T/cap/sigma are arrays)."""
        cap = H.BAND_HI if cap is None else cap
        upper = cap if self.occ[k] else self.away_max
        f_on = self.next_T(T, k, 0) > upper - sigma + TOL
        f_off = self.next_T(T, k, 1) < self.t_min + sigma - TOL
        return f_on, f_off

    def apply(self, u, T, k, cap=None, sigma=0.0):
        """shielded action: base u overridden. Returns (u_exec, forced_on, forced_off, conflict)."""
        f_on, f_off = self.force(T, k, cap, sigma)
        u = np.asarray(u).astype(bool)
        u_exec = np.where(f_on, True, np.where(f_off, False, u))
        return u_exec, f_on & ~u, f_off & u & ~f_on, f_on & f_off


def shielded(base, shield, cap=None, sigma=0.0, counters=None):
    """Wrap a setback.sim policy(T, prev, k) -> u with the shield (scalar path)."""
    def pol(T, prev, k):
        u, fo, ff, cf = shield.apply(int(base(T, prev, k)), T, k, cap, sigma)
        if counters is not None:
            counters["forced_on"] += int(fo); counters["forced_off"] += int(ff)
            counters["conflict_steps"] += int(cf)
        return int(u)
    return pol


def latch_base(T, prev, k):
    return prev


# ----------------------------------------------------------------- batched simulator
def sim_shield_batch(city, w, price_v, caps, sigmas, base=None, c_sw=None, hours=168,
                     T0=None, occ=None, lo=None, hi=None, allow_away=False):
    """P shielded candidates (cap_i, sigma_i) in lock-step on the exact single-zone plant.

    base(T (P,), prev (P,) bool, k) -> (P,) bool base action; None = the latch (hold prev).
    Returns the setback.sim / sim_hyst_batch keys as (P,) arrays plus forced_on, forced_off,
    conflict_steps. Equal to setback.sim(shielded(...)) per candidate (tests/test_shield.py)."""
    c_sw = F.C_SW if c_sw is None else c_sw
    T0 = F.T0 if T0 is None else T0
    caps = np.atleast_1d(np.asarray(caps, float)); sigmas = np.atleast_1d(np.asarray(sigmas, float))
    caps, sigmas = np.broadcast_arrays(caps, sigmas); P = len(caps)
    if occ is None:
        _, occ, lo, hi = F._ctx(city, w, False)
    sh = Shield(city, w, hours, occ=occ)
    if not sh.occ.all():
        # V-code-23: a ONE-step shield cannot pre-cool before a return from an away period (the
        # ceiling drops from AWAY_MAX to cap in one step), so zero over is guaranteed only on an
        # all-occupied timetable (riyadh w121 + setback timetable: 0.55 K.h over).
        msg = (f"{city} w{w}: timetable has away steps; the one-step shield's zero-over guarantee "
               f"holds only when every step is occupied")
        if not allow_away:
            raise ValueError(msg + " (pass allow_away=True to run it unguaranteed)")
        import warnings
        warnings.warn(msg)
    N = sh.N; occ = sh.occ; lo = np.asarray(lo, float)[:N]; hi = np.asarray(hi, float)[:N]
    t_min = sh.t_min
    price = H.price_flat(N, price_v) if np.ndim(price_v) == 0 else np.asarray(price_v, float)
    p_el = H.Q_HVAC / H.cop_series(sh.t_out) / 1000.0
    DT = H.DT
    T = np.full(P, float(T0)); prev = np.zeros(P, bool)
    cost = np.zeros(P); e = np.zeros(P); sw = np.zeros(P, int)
    over = np.zeros(P); under = np.zeros(P); cmd = np.zeros(P); ff = np.zeros(P); dh = np.zeros(P)
    s_occ = np.zeros(P); s_clip = np.zeros(P); n_viol = np.zeros(P, int)
    fon = np.zeros(P, int); foff = np.zeros(P, int); conf = np.zeros(P, int)
    tmax_away = np.full(P, -np.inf); n_occ = int(occ.sum())
    for k in range(N):
        ub = prev.copy() if base is None else np.asarray(base(T, prev, k), bool)
        u, a, b, c = sh.apply(ub, T, k, caps, sigmas)
        fon += a; foff += b; conf += c
        st = u & ~prev
        cost += np.where(st, c_sw + price[k] * H.E_START, 0.0); sw += st; e += np.where(st, H.E_START, 0.0)
        cost += np.where(u, price[k] * p_el[k] * DT, 0.0); e += np.where(u, p_el[k] * DT, 0.0)
        T_inf = sh.t_out[k] + (H.SHGC * H.A_GL * sh.irr[k] - H.Q_HVAC * u.astype(float)) / sh.lam
        T = T_inf + (T - T_inf) * sh.a
        cmd += np.where(u, np.maximum(0.0, t_min - T - TOL) * DT, 0.0)
        if occ[k]:
            s_occ += T; s_clip += np.maximum(T, lo[k])
            over += np.maximum(0.0, T - hi[k] - TOL) * DT
            under += np.maximum(0.0, lo[k] - T - TOL) * DT
            ff += np.where(u, 0.0, np.maximum(0.0, t_min - T - TOL) * DT)
            v = (T > hi[k] + TOL) | (T < lo[k] - TOL); n_viol += v
            dh += np.where(v, np.maximum(0.0, T - hi[k]) * DT + np.maximum(0.0, lo[k] - T) * DT, 0.0)
        else:
            tmax_away = np.maximum(tmax_away, T)
        prev = u
    if hasattr(base, "verify"):
        base.verify()                      # forward pass == model.predict on visited states
    d = hours / 24.0
    cost += price[-1] * (T - T0) * F.C_TH * 1e3 / 3.6e6 / H.COP_RATED
    nan = np.full(P, np.nan)
    return dict(J=cost / d, E=e / d, f_s=sw / d, starts=sw, T_end=T,
                T_mean_occ=s_occ / n_occ if n_occ else nan,
                T_mean_occ_clip=s_clip / n_occ if n_occ else nan,
                v_occ=100.0 * n_viol / max(1, n_occ), deg_h_occ=dh,
                deg_h_over=over, deg_h_under=under, deg_h_cmd_under=cmd, deg_h_ff_under=ff,
                T_max_away=tmax_away if n_occ < N else nan, fallback_steps=np.zeros(P, int),
                forced_on=fon, forced_off=foff, conflict_steps=conf)


def rows_of(res, i):
    return {k: (v[i].item() if hasattr(v[i], "item") else v[i]) for k, v in res.items()}


# ----------------------------------------------------------------- saved PPO models (v2 obs)
_PPO = {}


def ppo_forward(model_path):
    """Batched NumPy forward pass (O (P, 8) -> (P,) bool) of a saved PPO model's deterministic
    action, checked against model.predict on 200 random observations. Cached per path."""
    if model_path in _PPO:
        return _PPO[model_path]
    from stable_baselines3 import PPO
    import torch
    model = PPO.load(model_path, device="cpu")
    if model.observation_space.shape != (8,):
        raise ValueError(f"{model_path}: expected the v2 8-feature observation, got "
                         f"{model.observation_space.shape} (setback/E2 models need their own obs)")
    pol = model.policy
    mods = [m for m in pol.mlp_extractor.policy_net if isinstance(m, torch.nn.Linear)]
    Ws = [(m.weight.detach().cpu().numpy().astype(np.float64),
           m.bias.detach().cpu().numpy().astype(np.float64)) for m in mods]
    actn = pol.mlp_extractor.policy_net[1].__class__.__name__.lower()
    f = np.tanh if "tanh" in actn else (lambda x: np.maximum(x, 0.0))
    Wa = pol.action_net.weight.detach().cpu().numpy().astype(np.float64)
    ba = pol.action_net.bias.detach().cpu().numpy().astype(np.float64)

    def fwd(O):                                    # O (P, 8) -> (P,) bool
        h = O.astype(np.float32).astype(np.float64)
        for W, b in Ws:
            h = f(h @ W.T + b)
        lg = h @ Wa.T + ba
        return lg[:, 1] > lg[:, 0]                 # argmax (ties -> 0, as np.argmax)
    rng = np.random.default_rng(0)
    O = rng.uniform(-3, 3, (200, 8)).astype(np.float32)
    ref = np.array([int(model.predict(o, deterministic=True)[0]) for o in O])
    assert np.array_equal(fwd(O).astype(int), ref), f"{model_path}: numpy forward != predict"
    def predict(O):
        return np.array([int(model.predict(o, deterministic=True)[0]) for o in O], int)
    fwd.predict = predict
    _PPO[model_path] = fwd
    return fwd


def ppo_base(model_path, city, w, hours=168):
    """Batched base action of a saved v2 RBRL PPO model with the 8-feature observation of
    rbrl_ppo.evaluate (non-setback), for window w."""
    fwd = ppo_forward(model_path)
    t_out, irr, N = H.series(city, hours, w)
    seen = []

    def base(T, prev, k):
        kn = min(k + 4, N - 1); h = (k * H.DT) % 24.0
        P = len(T)
        O = np.empty((P, 8))
        O[:, 0] = (T - 23.0); O[:, 1] = prev.astype(float)
        O[:, 2] = (t_out[k] - 35.0) / 10.0; O[:, 3] = (t_out[kn] - 35.0) / 10.0
        O[:, 4] = irr[k] / 500.0; O[:, 5] = np.sin(2 * np.pi * h / 24.0)
        O[:, 6] = np.cos(2 * np.pi * h / 24.0); O[:, 7] = k / N
        a = fwd(O)
        if k % 16 == 0:                             # sample of visited states (V-code-23)
            seen.append((O[:: max(1, P // 8)].astype(np.float32), a[:: max(1, P // 8)]))
        return a

    def verify():
        """The batched forward pass must equal model.predict on the visited (float32) states."""
        if not seen:
            return
        O = np.concatenate([o for o, _ in seen]); A = np.concatenate([a for _, a in seen])
        ref = fwd.predict(O)
        bad = int((ref != A.astype(int)).sum())
        seen.clear()
        if bad:
            raise AssertionError(f"{model_path} w{w}: numpy forward != predict on {bad}/{len(O)} "
                                 f"visited states")
    base.verify = verify
    return base


# ----------------------------------------------------------------- A4 selection (§2.2)
def _admissible_w(r, w):
    """Condition 1 of §2.2 on one tuning window: the single helper F.admissible (F6)."""
    return bool(F.admissible(r, w))


def therm_curve(city, w, price_v, step=0.002, lo=-0.4, hi=0.4):
    """(mean_clip(delta), J(delta)) of THERM(delta) on the §2.3 delta grid: final_tables.therm_curve
    (one cache, keyed on everything the curve depends on). step/lo/hi: legacy, ignored."""
    return F.therm_curve(city, w, price_v)


def J_eq(city, w, price_v, T_target):
    """J of THERM(delta_w) at the arm's clipped mean (Rule C on one window): final_tables.j_eq,
    the shared minimum-J crossing helper F.rule_c (RULING §13)."""
    return F.j_eq(city, w, price_v, T_target)[0]


def select_A4(cand_rows, city, price_v, windows=None, jeq=None, target=None):
    """cand_rows: {param: {w: sim dict}} on the tuning windows. Returns (param, fit_status, info).
    jeq(w, T) -> J_THERM(delta_w),w at clipped mean T and `target` (pooled THERM mean) default to
    the single-zone plant; the multi-zone dwelling (mz_r3) passes its own.
    F6/F7: the single A4 selector final_tables.select_rows (candidate order = dict order; ties ->
    lowest index)."""
    windows = list(F.TUNE_W if windows is None else windows)
    cands = list(cand_rows)
    rows = [[cand_rows[p][w] for w in windows] for p in cands]
    fit = F.select_rows(cands, rows, city, price_v, windows, jeq=jeq, target=target)
    info = dict(F.LAST_FIT)
    if fit is None:
        return None, "none", info
    info["tune_ratio"] = info["tune_obj"]
    return fit[1], fit.fit_status, info


# ----------------------------------------------------------------- arms
def caps_grid():
    return np.round(np.arange(H.BAND_HI - 0.50, H.BAND_HI + 1e-9, 0.01), 2)


def fit_and_eval(city, price_v, base_for=None, sigmas=SIGMAS, caps=None, label="latch"):
    """For every sigma: fit the ceiling by A4 on TUNE_W, evaluate on EVAL_W under Rule C."""
    import t1_v2 as T1V2                      # evaluate(): Rule C, pooled saving (no edits there)
    caps = caps_grid() if caps is None else np.asarray(caps, float)
    th = {w: F.therm_run(city, w, price_v) for w in F.EVAL_W}
    rows, pw = [], []
    for sg in sigmas:
        cand = {}
        tune = {w: sim_shield_batch(city, w, price_v, caps, sg,
                                    base=None if base_for is None else base_for(w))
                for w in F.TUNE_W}
        for i, c in enumerate(caps):
            cand[float(c)] = {w: rows_of(tune[w], i) for w in F.TUNE_W}
        cap, status, info = select_A4(cand, city, price_v)
        tune_max_over = max(r["deg_h_over"] for rr in cand.values() for r in rr.values())
        tune_max_cmd = max(r["deg_h_cmd_under"] for rr in cand.values() for r in rr.values())
        row = dict(city=city, arm=f"D1-{label}", sigma=sg, cap=cap, fit_status=status,
                   tune_max_deg_h_over=tune_max_over, tune_max_deg_h_cmd_under=tune_max_cmd,
                   **{k: v for k, v in info.items() if k != "fit_status"})    # (duplicate key crash)
        if cap is not None:
            runs = {w: rows_of(sim_shield_batch(city, w, price_v, [cap], sg,
                                                base=None if base_for is None else base_for(w)), 0)
                    for w in F.EVAL_W}
            s, p = T1V2.evaluate(city, price_v, runs, th)
            row.update(s, deg_h_cmd_under=sum(runs[w]["deg_h_cmd_under"] for w in F.EVAL_W),
                       deg_h_ff_under=sum(runs[w]["deg_h_ff_under"] for w in F.EVAL_W),
                       T_end=float(np.mean([runs[w]["T_end"] for w in F.EVAL_W])),
                       forced_on=sum(runs[w]["forced_on"] for w in F.EVAL_W),
                       forced_off=sum(runs[w]["forced_off"] for w in F.EVAL_W),
                       conflict_steps=sum(runs[w]["conflict_steps"] for w in F.EVAL_W))
            pw += [dict(city=city, arm=row["arm"], sigma=sg, cap=cap, **r) for r in p]
        rows.append(row)
        print(f"  {city} {row['arm']} sigma={sg:.2f} cap={cap} {status} "
              f"s_eq={row.get('s_pooled_eq', float('nan')):+.2f}%", flush=True)
    return rows, pw


def main():
    import rbrl_io as IO
    ap = argparse.ArgumentParser()
    ap.add_argument("arm", choices=("latch", "ppo"))
    ap.add_argument("city")
    ap.add_argument("--price", type=float, default=0.18)
    ap.add_argument("--models", default=None)
    a = ap.parse_args()
    t0 = time.time()
    inputs = [f"{IO.ROOT}/{a.city}.epw"]
    if a.arm == "latch":
        rows, pw = fit_and_eval(a.city, a.price)
        import v3_names as V
        name = V.name("D1", a.city)
    else:
        pat = a.models or f"{IO.R}/models/rbrl_ppo5_v2_{a.city}_{a.city}_*.zip"
        rows, pw = [], []
        for mp in sorted(glob.glob(pat)):
            seed = os.path.splitext(os.path.basename(mp))[0].rsplit("_", 1)[-1]
            r, p = fit_and_eval(a.city, a.price, base_for=lambda w, mp=mp: ppo_base(mp, a.city, w),
                                label=f"ppo{seed}")
            for x in r + p:
                x["model"] = os.path.basename(mp)
            rows += r; pw += p; inputs.append(mp)
        import v3_names as V
        name = V.name("D1_PPO", a.city)
    IO.write_csv(name, rows, inputs=inputs, impl="shield.py")
    if pw:
        IO.write_csv(f"{name}_perwindow", pw, inputs=inputs, impl="shield.py")
    print(f"done [{time.time() - t0:.0f}s]", flush=True)


if __name__ == "__main__":
    H.require_headline_dt("shield (PPO observation look-ahead in 15-min steps)")
    main()
