#!/usr/bin/env python3
"""RBRL: PPO under the corrected asymmetric rule layer, on the verified physics.

Built directly on setback.py / headroom.py rather than on the older env.py, so
the agent is trained and evaluated on exactly the dynamics, conductances,
capacity and tariff used for THERM, TUNED and OPT in the same tables.

Rule layer (hard, applied to the commanded action)
  R1  force ON  when T >= T_max - eps_hot    eps_hot  = 0.20 K
  R2  force OFF when T <= T_min + eps_cold   eps_cold = 0.40 K
Both thresholds are derived rather than assumed: a guard band must cover the
temperature excursion of one actuation interval in its own direction. Cooling
moves the zone by Q*dt/C_th = 0.375 K per step; the worst warming, set by the
peak load rather than by the plant, is 0.129 K. The bands are therefore
asymmetric, and the symmetric eps_g = 0.5 of the earlier version of this study
would confine the agent to (22.5, 23.5) and so forbid the best rule in its own
family on a 2 K band.

Training windows are the tuning set; evaluation is on the disjoint held-out set,
the same split used for TUNED.
"""
from __future__ import annotations
import sys, os, csv, time, argparse
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import config as CFG
import headroom as H
import setback as S
import final_tables as F
import t1_v2 as T1V2
import rbrl_io as IO
import v3_names as V

import gymnasium as gym
from gymnasium import spaces

# F8: rule margins, band and away limit from config.py. At the headline config these equal the
# literals the PPO models were trained with (0.20/0.40, 22/24, 30), so ZoneEnv's dynamics and
# observations are unchanged (tag p3-ppo-env; tests/test_fast.py::test_ppo_env_unchanged).
EPS_HOT, EPS_COLD = CFG.EPS_HOT, CFG.EPS_COLD
LO, HI = CFG.BAND_LO, CFG.BAND_HI
PEN = 50.0                      # SAR per degree-hour, comfort penalty in reward


USE_RULES = True
# Occupancy-setback variant (RBRL-SB): the agent sees whether the zone is
# occupied and how long until the occupants return; while the zone is empty R1
# acts at the away ceiling (30 C) instead of the occupied one, so the agent has
# a genuine decision to learn (when to start cooling before the return), which
# the corollary does not cover (it assumes no exogenous schedule). R2 stays at
# the occupied floor, so the empty zone is never pre-cooled below the band.
SETBACK = False
AWAY_HI = CFG.AWAY_MAX
N_OBS = 8


def apply_rules(u, T, cap=HI, occupied=True):
    """Hard rule layer. With USE_RULES False the agent is unconstrained, which
    is the ablation that tests whether comfort is enforced by construction or
    merely learned."""
    if not USE_RULES: return int(u)
    if T >= (cap if occupied else AWAY_HI) - EPS_HOT: return 1
    if T <= LO + EPS_COLD: return 0
    return int(u)


def occ_features(N):
    occ = S.occupancy(N + 200) if SETBACK else np.ones(N + 200, bool)
    d = np.zeros(len(occ), int); nxt = 10 ** 6
    for k in range(len(occ) - 1, -1, -1):
        nxt = 0 if occ[k] else nxt + 1
        d[k] = nxt
    return occ, np.minimum(d, 48) / 48.0


class ZoneEnv(gym.Env):
    def __init__(self, city, windows, price_v, c_th=4800.0, faces=1, seed=0):
        super().__init__()
        self.city, self.windows, self.price_v = city, list(windows), price_v
        self.c_th, self.faces = c_th, faces
        self.lam = H.lam_of(faces, city)
        self.decay = float(np.exp(-H.DT * 3600.0 * self.lam / (c_th * 1e3)))
        self.p_el = H.Q_HVAC / H.COP_RATED / 1000.0
        self.series = {w: H.series(city, 168, w) for w in self.windows}
        self.N = self.series[self.windows[0]][2]
        self.rng = np.random.default_rng(seed)
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(-5.0, 5.0, shape=(N_OBS,), dtype=np.float32)
        self.occ, self.dnext = occ_features(self.N)

    def _obs(self):
        t_out, irr, _ = self.series[self.w]
        k = min(self.k, self.N - 1)
        kn = min(self.k + 4, self.N - 1)          # one hour ahead
        h = (k * H.DT) % 24.0
        return np.array([
            (self.T - 23.0) / 1.0,
            float(self.prev),
            (t_out[k] - 35.0) / 10.0,
            (t_out[kn] - 35.0) / 10.0,
            irr[k] / 500.0,
            np.sin(2 * np.pi * h / 24.0),
            np.cos(2 * np.pi * h / 24.0),
            self.k / self.N,
        ] + ([float(self.occ[k]), self.dnext[k]] if SETBACK else []), dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        if seed is not None: self.rng = np.random.default_rng(seed)
        self.w = self.windows[int(self.rng.integers(len(self.windows)))]
        self.T, self.prev, self.k = 23.0, 0, 0
        return self._obs(), {}

    def step(self, action):
        t_out, irr, _ = self.series[self.w]
        k = self.k
        u = apply_rules(action, self.T, occupied=bool(self.occ[k]))
        cost = 0.0
        if u == 1 and self.prev == 0: cost += H.C_SW
        if u == 1: cost += self.price_v * self.p_el * H.DT
        T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - H.Q_HVAC * u) / self.lam
        self.T = T_inf + (self.T - T_inf) * self.decay
        dh = (max(0.0, self.T - HI) * H.DT + max(0.0, LO - self.T) * H.DT) if self.occ[k] else 0.0
        self.prev = u; self.k += 1
        done = self.k >= self.N
        if done:   # price the terminal thermal state, as the DP and sim do
            cost += self.price_v * (self.T - 23.0) * self.c_th * 1e3 / 3.6e6 / H.COP_RATED
        return self._obs(), float(-(cost + PEN * dh)), done, False, {}


def _merge(name, rows, seed0, nseeds):
    """one seed per job (each < 2 h): rows of OTHER (city, seed) pairs already in results/<name>
    are kept when they were written by the same code sha (else refused: rerun them), so the
    per-city v3 file accumulates the seeds of separate jobs."""
    import os
    path = f"{IO.R}/{name}{IO.tag()}.csv"
    if not os.path.exists(path):
        return rows
    mine = {(r["city"], str(r["seed"])) for r in rows}
    old = [r for r in IO.read_csv(name) if (r.get("city"), str(r.get("seed"))) not in mine]
    if not old:
        return rows
    shas = {r.get("prov_code_sha") for r in old}
    if shas != {IO.code_sha()}:
        raise SystemExit(f"{name}: existing rows from code {sorted(map(str, shas))} != {IO.code_sha()}; "
                         f"rerun those seeds or move the file")
    old = [{k: v for k, v in r.items() if not k.startswith("prov_")} for r in old]
    return sorted(old + list(rows), key=lambda r: (r["city"], int(r["seed"]), int(float(r.get("window", 0) or 0))))


def numpy_policy(model):
    """Deterministic action of an SB3 MlpPolicy (Discrete) as a NumPy forward
    pass: argmax of the action logits. Identical to model.predict(...,
    deterministic=True) (checked on construction) and ~20x faster, which makes
    the Rule-A ceiling scan affordable."""
    import torch
    pol = model.policy
    mods = [m for m in pol.mlp_extractor.policy_net if isinstance(m, torch.nn.Linear)]
    Ws = [(m.weight.detach().cpu().numpy().astype(np.float64),
           m.bias.detach().cpu().numpy().astype(np.float64)) for m in mods]
    act = pol.mlp_extractor.policy_net[1].__class__.__name__.lower()
    f = np.tanh if "tanh" in act else (lambda x: np.maximum(x, 0.0))
    Wa = pol.action_net.weight.detach().cpu().numpy().astype(np.float64)
    ba = pol.action_net.bias.detach().cpu().numpy().astype(np.float64)
    def act_fn(obs):
        h = obs.astype(np.float64)
        for W, b in Ws:
            h = f(W @ h + b)
        return int(np.argmax(Wa @ h + ba))
    rng = np.random.default_rng(0)
    for _ in range(200):
        o = rng.uniform(-3, 3, model.observation_space.shape[0]).astype(np.float32)
        assert act_fn(o) == int(model.predict(o, deterministic=True)[0]), "numpy policy mismatch"
    return act_fn


def evaluate(model, city, windows, price_v, c_th=None, faces=1, cap=HI):
    """Run the learned policy on the SAME simulator used for every other arm: C_th, c_sw and the
    band read at call time from final_tables / config (F8, V-code-17)."""
    c_th = F.C_TH if c_th is None else c_th
    out = []
    act_fn = model if callable(model) else numpy_policy(model)
    lam = H.lam_of(faces, city)
    decay = float(np.exp(-H.DT * 3600.0 * lam / (c_th * 1e3)))
    for w in windows:
        t_out, irr, N = H.series(city, 168, w)
        occ_x, dnext = occ_features(N)
        occ = occ_x[:N]
        lo, hi = S.bands(occ, LO, HI, CFG.AWAY_FLOOR, CFG.AWAY_MAX)
        price = H.price_flat(N, price_v)
        state = {"T": 23.0, "prev": 0}
        def pol(T, prev, k):
            kn = min(k + 4, N - 1)
            h = (k * H.DT) % 24.0
            obs = np.array([(T - 23.0) / 1.0, float(prev),
                            (t_out[k] - 35.0) / 10.0, (t_out[kn] - 35.0) / 10.0,
                            irr[k] / 500.0, np.sin(2*np.pi*h/24.0),
                            np.cos(2*np.pi*h/24.0), k / N]
                           + ([float(occ_x[k]), dnext[k]] if SETBACK else []), dtype=np.float32)
            return apply_rules(act_fn(obs), T, cap, occupied=bool(occ_x[k]))
        out.append(S.sim(pol, city, faces, c_th, price, lo, hi, occ,
                         168, w, F.T0, c_sw=F.C_SW))
    return out


if __name__ == "__main__":
    H.require_headline_dt("rbrl_ppo (observation look-ahead in 15-min steps)")
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=200_000)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--cities", default="riyadh,jeddah,taif")
    ap.add_argument("--price", type=float, default=CFG.PRICE)
    ap.add_argument("--norules", action="store_true",
                    help="ablate the hard rule layer (R1/R2 off)")
    ap.add_argument("--out", default=None,
                    help="output stem; default v3_names: rbrl_ppo5_v3_<city> (one file per city) or, with "
                         "--norules, rbrl_norules5_v3 (+ _perwindow)")
    ap.add_argument("--models", default=None,
                    help="model stem template ({c} = city) under results/models/; default "
                         "rbrl_ppo5_v2_{c} (the saved headline models) or rbrl_norules5_v3")
    ap.add_argument("--setback", action="store_true",
                    help="RBRL-SB: occupancy timetable in the state and rules")
    ap.add_argument("--nomatch", action="store_true",
                    help="skip comfort matching (for the no-rules ablation, "
                         "where the band is violated and matching is undefined)")
    ap.add_argument("--seed0", type=int, default=42, help="first seed (seeds seed0 .. seed0+seeds-1)")
    ap.add_argument("--refit", action="store_true",
                    help="no training: load the saved model results/models/<out><TAG>_<city>_<seed> "
                         "and redo only the A4 cap fit and the evaluation (J11a')")
    ap.add_argument("--e2", action="store_true",
                    help="E2 (F12/J12): lambda-priced PPO with forecasts inside R1/R2 (rbrl_e2.py); one seed "
                         "per invocation recommended (--seeds 1 --seed0 S)")
    ap.add_argument("--lam", type=float, default=None, help="E2: the comfort multiplier (in-rule MPC-6 lam)")
    ap.add_argument("--e1", action="store_true", help="E1: J(hold) vs the DP at lambda = 0 in the rules")
    a = ap.parse_args()
    if a.e1 or a.e2:                 # separate env class; ZoneEnv (tag p3-ppo-env) is not touched
        import rbrl_e2 as E2
        E2.main_e1() if a.e1 else E2.main(a)
        raise SystemExit(0)
    if a.setback:      # RBRL-SB is a dropped arm (RULING_round4 §5, F14): no baseline under the v3 protocol
        raise SystemExit("rbrl_ppo --setback: RBRL-SB is a dropped arm (ruling round 4 §5/F14); the setback "
                         "arms are setback_arms.py (TUNED-SB, MANUAL, THERM-SB, MPC-SB)")
    mstem = a.models or ("rbrl_norules5_v3" if a.norules else "rbrl_ppo5_v2_{c}")
    from stable_baselines3 import PPO
    globals()["USE_RULES"] = not a.norules
    import rbrl_ppo as _self
    _self.USE_RULES = not a.norules
    _self.SETBACK = globals()["SETBACK"] = a.setback
    _self.N_OBS = globals()["N_OBS"] = 10 if a.setback else 8
    if a.setback:
        import setback_arms as SA
    print(f"rule layer: {'ON' if _self.USE_RULES else 'OFF (ablation)'}", flush=True)
    t0 = time.time(); rows = []
    # Per-window costs, not only their mean. A paired test and a bootstrap
    # interval both need the window-level pairs; reporting only the mean and its
    # standard deviation discards exactly the pairing that makes the comparison
    # between two controllers on the SAME seven weeks informative.
    pw = []
    for city in a.cities.split(","):
        th = ({w: SA.therm_sb(city, w, 0.0) for w in F.WINDOWS} if a.setback
              else {w: F.therm_run(city, w, a.price) for w in F.WINDOWS})
        Jb = np.array([th[w]["J"] for w in F.EVAL_W])
        for seed in range(a.seed0, a.seed0 + a.seeds):
            # RBRL_TAG in the model name too, so a scenario run cannot overwrite headline models
            mpath = f"/home/claude/rbrl/results/models/{mstem.format(c=city)}{IO.tag()}_{city}_{seed}"
            if a.refit:
                model = PPO.load(mpath + ".zip", device="cpu")
                IO.note_input(mpath + ".zip")
            else:
                env = ZoneEnv(city, F.TUNE_W, a.price, seed=seed)
                model = PPO("MlpPolicy", env, seed=seed, verbose=0,
                            n_steps=1344, batch_size=336, gamma=0.999,
                            learning_rate=3e-4, policy_kwargs=dict(net_arch=[256, 128]))
                model.learn(total_timesteps=a.steps)
                os.makedirs(f"/home/claude/rbrl/results/models", exist_ok=True)
                model.save(mpath)
            # The R1 ceiling is fitted below by Rule A4, frozen, and evaluated on the held-out
            # windows against the per-window equalised comparator THERM(delta_w) (Rule C).
            if a.nomatch:
                # no-rules ablation: the cap is not selected (matching is undefined when the band
                # is violated); it is fixed at BAND_HI -> fit_status "fixed" (Sec. 2.2 set)
                capf, fit_status, fit = HI, "fixed", None
            else:
                # Rule A4 (final_tables.fit_param): the post-training R1 ceiling is the arm's one
                # comfort parameter, scanned BAND_HI - 0.5 .. BAND_HI in 0.01 K steps (ascending)
                # on the TUNING windows only; the policy itself is fixed. No silent fallback to
                # cap = HI: a seed with no admissible cap is recorded with fit_status "none"
                # (refused by rbrl_io, listed in the .meta.json) and not evaluated.
                caps = [round(c, 2) for c in np.arange(HI - 0.50, HI + 0.0001, 0.01)]
                fast = numpy_policy(model)
                run = lambda cap, w: evaluate(fast, city, [w], a.price, cap=cap)[0]
                fit = F.fit_param(caps, run, F.TUNE_W, city=city, price_v=a.price, setback=a.setback)
                fit_status = fit.fit_status if fit else "none"
                if fit is None:
                    print(f"  {city:7s} seed {seed}: no admissible cap (fit_status none); not evaluated",
                          flush=True)
                    rows.append(dict(city=city, seed=seed, steps=a.steps, cap="",
                                     fit_status="none", fit_windows="TUNE_W"))
                    continue
                capf = fit[1]
            ev = evaluate(model, city, F.EVAL_W, a.price, cap=capf)
            runs = {w: ev[i] for i, w in enumerate(F.EVAL_W)}
            if a.nomatch:
                for w in F.EVAL_W:
                    r = runs[w]
                    pw.append(dict(city=city, seed=seed, window=w, cap=capf, fit_status=fit_status,
                                   J_arm=r["J"], J_therm0=th[w]["J"], T_arm=r[F.MEAN_KEY],
                                   T_therm0=th[w][F.MEAN_KEY], fs_arm=r["f_s"], E_arm=r["E"],
                                   deg_h_occ=r["deg_h_occ"], deg_h_over=r["deg_h_over"],
                                   deg_h_under=r["deg_h_under"],
                                   s_raw_w=100.0 * (1 - r["J"] / th[w]["J"])))
                Jr = [runs[w]["J"] for w in F.EVAL_W]
                summ = dict(s_raw=F.pooled_saving(Jr, Jb),
                            deg_h_occ=float(sum(runs[w]["deg_h_occ"] for w in F.EVAL_W)),
                            T_arm=float(np.mean([runs[w][F.MEAN_KEY] for w in F.EVAL_W])))
            else:
                summ, pwr = (SA.evaluate_sb(city, runs) if a.setback
                             else T1V2.evaluate(city, a.price, runs, th))
                for r in pwr:
                    pw.append(dict(city=city, seed=seed, cap=capf, fit_status=fit_status, **r))
            rows.append(dict(city=city, seed=seed, steps=a.steps, cap=capf, fit_status=fit_status,
                             **(T1V2.tune_cols(fit) if fit else {}),
                             **{"fit_windows": "TUNE_W", **summ}))
            print(f"  {city:7s} seed {seed}: cap={capf} " +
                  " ".join(f"{k}={v:+.3f}" for k, v in summ.items()
                           if k in ("s_pooled_eq", "s_raw", "dT_pooled", "deg_h_occ", "deg_h_over")) +
                  f"  [{time.time()-t0:.0f}s]", flush=True)
    # rbrl_io: RBRL_TAG-aware names (S6), atomic, key union, provenance, refuses fit_status none
    _w = lambda name, rr: IO.write_csv(name, _merge(name, rr, a.seed0, a.seeds),
                                       inputs=[f"{IO.ROOT}/{c}.epw" for c in a.cities.split(",")])
    if a.out:
        _w(a.out, rows); _w(f"{a.out}_perwindow", pw)
    elif a.norules:
        _w(V.name("NORULES"), rows); _w(V.name("NORULES_PW"), pw)
    else:
        for c in a.cities.split(","):
            rc, pc = [r for r in rows if r["city"] == c], [r for r in pw if r["city"] == c]
            if rc:
                _w(V.name("RBRL", c), rc)
            if pc:
                _w(V.name("RBRL_PW", c), pc)
