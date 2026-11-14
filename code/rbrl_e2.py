#!/usr/bin/env python3
"""E2 (X3, RULING_round4 F12 / J12): PPO given the comfort multiplier, inside the training rules.

The headline RBRL (rbrl_ppo.ZoneEnv, frozen at tag p3-ppo-env) is trained on the lambda-free cost,
whose in-rule optimum is the hold policy (E1 below). E2 asks whether a learner given the same
lambda-priced objective as the MPC / CLV recovers the in-rule MPC gain:

  reward  -(interval cost + (lam/n_occ) max(T', T_min) + PEN deg-h)   (rbrl_sb.SBEnv.step, setback off;
          every step is occupied, n_occ = N; the cost is the simulator's: cop_series, c_sw, the
          terminal store priced at rated COP)
  obs     ZoneEnv's 8 features + the PERFECT outdoor-temperature forecast at +1, +2, +3, +6 h and
          the irradiance forecast at +1, +3 h (14 features; information parity with the MPC)
  rules   R1 force on at RULE_ON = 23.80, R2 force off at RULE_OFF = 22.40, identical in training
          and evaluation (CSRL-7); no post-training ceiling fit -> fit_status "fixed"
  PPO     ZoneEnv's hyper-parameters + ent_coef 0.01 and reward normalisation (VecNormalize,
          norm_obs=False); Monitor episode log and the SB3 progress log (entropy, losses) saved
          beside the model (learning curves)
  check   the deterministic NumPy forward pass equals model.predict on every float32 observation
          visited on one tuning and one held-out window (min logit gap logged)

Evaluation: the held-out windows under Rule C (t1_v2.evaluate), one seed per invocation (each job
< 2 h); rows of other seeds already in the file are merged (rbrl_ppo._merge).

E1 (no training): the exact lambda = 0 objective inside the rules solved by the DP on TUNE_W
(r3_dp.lagrangian(lam=0, ruled=True)); hold = the guard hysteresis (on at R1, off at R2).
J(hold) <= 1.01 J_DP means PPO's lambda-free optimum IS hold.  -> E1v3_hold_dp

Usage: python3 rbrl_ppo.py --e2 --lam <lam> --cities riyadh --seed0 42 [--steps 200000]
       python3 rbrl_ppo.py --e1
"""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import config as CFG
import headroom as H
import setback as S
import final_tables as F
import rbrl_io as IO
import v3_names as V

import gymnasium as gym
from gymnasium import spaces

R1, R2 = CFG.RULE_ON, CFG.RULE_OFF        # 23.80 / 22.40, training == evaluation
LO, HI = CFG.BAND_LO, CFG.BAND_HI
PEN = 50.0
FC_T = (4, 8, 12, 24)                     # +1, +2, +3, +6 h in 15-min steps
FC_I = (4, 12)                            # +1, +3 h
N_OBS = 8 + len(FC_T) + len(FC_I)
EXTRA_H = 6                               # weather loaded past the window for the forecast


def rules(a, T):
    """the training rule layer, fixed at R1/R2 (no cap parameter)."""
    if T >= R1:
        return 1
    if T <= R2:
        return 0
    return int(a)


def obs_vec(T, prev, k, N, t_out, irr):
    """the E2 observation at step k (t_out/irr cover the window plus EXTRA_H hours)."""
    kk = min(k, N - 1); kn = min(k + 4, N - 1)
    h = (kk * H.DT) % 24.0
    base = [(T - 23.0) / 1.0, float(prev), (t_out[kk] - 35.0) / 10.0, (t_out[kn] - 35.0) / 10.0,
            irr[kk] / 500.0, np.sin(2 * np.pi * h / 24.0), np.cos(2 * np.pi * h / 24.0), k / N]
    fc = [(t_out[kk + d] - 35.0) / 10.0 for d in FC_T] + [irr[kk + d] / 500.0 for d in FC_I]
    return np.array(base + fc, dtype=np.float32)


class E2Env(gym.Env):
    """lambda-priced zone environment (does NOT alter rbrl_ppo.ZoneEnv)."""

    def __init__(self, city, windows, price_v, lam, c_th=None, faces=1, seed=0):
        super().__init__()
        self.city, self.windows, self.price_v, self.lam = city, list(windows), float(price_v), float(lam)
        self.c_th = F.C_TH if c_th is None else c_th
        self.c_sw = F.C_SW
        self.lam_env = H.lam_of(faces, city)
        self.decay = float(np.exp(-H.DT * 3600.0 * self.lam_env / (self.c_th * 1e3)))
        self.N = int(round(168 / H.DT))
        self.wx = {}
        for w in self.windows:
            t_out, irr, _ = H.series(city, 168 + EXTRA_H, w)
            p_el = H.Q_HVAC / H.cop_series(t_out) / 1000.0
            self.wx[w] = (t_out, irr, p_el)
        self.n_occ = self.N                    # no setback: every step occupied
        self.rng = np.random.default_rng(seed)
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(-6.0, 6.0, shape=(N_OBS,), dtype=np.float32)

    def _obs(self):
        t_out, irr, _ = self.wx[self.w]
        return obs_vec(self.T, self.prev, self.k, self.N, t_out, irr)

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.w = (options or {}).get("window", self.windows[int(self.rng.integers(len(self.windows)))])
        self.T, self.prev, self.k = 23.0, 0, 0
        return self._obs(), {}

    def step(self, action):
        t_out, irr, p_el = self.wx[self.w]
        k = self.k
        u = rules(action, self.T)
        cost = (self.c_sw + self.price_v * H.E_START if (u and not self.prev) else 0.0) + \
               (self.price_v * p_el[k] * H.DT if u else 0.0)
        T_inf = t_out[k] + (H.SHGC * H.A_GL * irr[k] - H.Q_HVAC * u) / self.lam_env
        self.T = T_inf + (self.T - T_inf) * self.decay
        pen = (self.lam / self.n_occ) * max(self.T, LO) + \
            PEN * (max(0.0, self.T - HI) + max(0.0, LO - self.T)) * H.DT
        self.prev = u; self.k += 1
        done = self.k >= self.N
        if done:
            cost += self.price_v * (self.T - 23.0) * self.c_th * 1e3 / 3.6e6 / H.COP_RATED
        return self._obs(), float(-(cost + pen)), done, False, {"u": u}


def forward32(model):
    """deterministic action and logit gap of an SB3 MlpPolicy (Discrete) in float32, the dtype SB3
    runs in; activations detected over the whole module list (CSRL-8)."""
    import torch
    pol = model.policy
    seq = list(pol.mlp_extractor.policy_net)
    layers = []
    for m in seq:
        if isinstance(m, torch.nn.Linear):
            layers.append(("lin", m.weight.detach().cpu().numpy().astype(np.float32),
                           m.bias.detach().cpu().numpy().astype(np.float32)))
        elif isinstance(m, torch.nn.Tanh):
            layers.append(("tanh",))
        elif isinstance(m, torch.nn.ReLU):
            layers.append(("relu",))
        else:
            raise TypeError(f"unsupported layer {m}")
    Wa = pol.action_net.weight.detach().cpu().numpy().astype(np.float32)
    ba = pol.action_net.bias.detach().cpu().numpy().astype(np.float32)

    def logits(obs):
        h = np.asarray(obs, np.float32)
        for L in layers:
            h = (L[1] @ h + L[2]) if L[0] == "lin" else (np.tanh(h) if L[0] == "tanh" else np.maximum(h, 0))
        return Wa @ h + ba

    def act(obs):
        return int(np.argmax(logits(obs)))
    act.logits = logits
    return act


def visited_states(act, city, windows, price_v, lam):
    """float32 observations visited by the deterministic policy (rules applied) on `windows`."""
    env = E2Env(city, windows, price_v, lam)
    out = []
    for w in windows:
        o, _ = env.reset(options={"window": w}); done = False
        while not done:
            out.append(o)
            o, _, done, _, _ = env.step(act(o))
    return out


def check_numpy_policy(model, act, states):
    """equivalence of the NumPy forward pass and model.predict on visited float32 states; returns
    the minimum |logit gap| (a near-tie is where float64 vs float32 could flip)."""
    gaps = []
    for o in states:
        lg = act.logits(o)
        assert act(o) == int(model.predict(o, deterministic=True)[0]), "numpy policy mismatch on a visited state"
        gaps.append(abs(float(lg[1] - lg[0])))
    return float(min(gaps))


def evaluate(act, city, windows, price_v):
    """the trained policy on the simulator of every other arm (S.sim), rules R1/R2 as in training."""
    out = []
    for w in windows:
        t_out, irr, _ = H.series(city, 168 + EXTRA_H, w)
        N = int(round(168 / H.DT))
        _, occ, lo, hi = F._ctx(city, w, False)
        pol = lambda T, prev, k: rules(act(obs_vec(T, prev, k, N, t_out, irr)), T)
        out.append(S.sim(pol, city, F.FACES, F.C_TH, H.price_flat(N, price_v), lo, hi, occ,
                         168, w, F.T0, c_sw=F.C_SW))
    return out


def train(city, lam, seed, steps, price_v=CFG.PRICE):
    from stable_baselines3 import PPO
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from stable_baselines3.common.logger import configure
    stem = f"{IO.R}/models/{V.name('E2').replace('_riyadh', '')}{IO.tag()}_{city}_lam{lam:g}_{seed}"
    os.makedirs(os.path.dirname(stem), exist_ok=True)
    venv = DummyVecEnv([lambda: Monitor(E2Env(city, F.TUNE_W, price_v, lam, seed=seed), stem + "_monitor")])
    venv = VecNormalize(venv, norm_obs=False, norm_reward=True, gamma=0.999)
    model = PPO("MlpPolicy", venv, seed=seed, verbose=0, n_steps=1344, batch_size=336, gamma=0.999,
                learning_rate=3e-4, ent_coef=0.01, policy_kwargs=dict(net_arch=[256, 128]))
    model.set_logger(configure(stem + "_log", ["csv"]))       # progress.csv: entropy, losses
    model.learn(total_timesteps=steps)
    model.save(stem); venv.save(stem + "_vecnormalize.pkl")
    IO.note_input(stem + ".zip")
    return model, stem


def main(a):
    H.require_headline_dt("rbrl_e2 (PPO observation in 15-min steps)")
    import t1_v2 as T1V2
    import rbrl_ppo as RP
    if a.lam is None:
        raise SystemExit("--e2 needs --lam (the in-rule MPC-6 lam of J6(i), T16v3)")
    rows, pw = [], []
    for city in a.cities.split(","):
        th = {w: F.therm_run(city, w, a.price) for w in F.WINDOWS}
        for seed in range(a.seed0, a.seed0 + a.seeds):
            t0 = time.time()
            model, stem = train(city, a.lam, seed, a.steps, a.price)
            act = forward32(model)
            gap = check_numpy_policy(model, act, visited_states(act, city, [F.TUNE_W[0], F.EVAL_W[0]],
                                                                 a.price, a.lam))
            ev = evaluate(act, city, F.EVAL_W, a.price)
            hold = [F.rule_run(city, w, a.price, R1, R2) for w in F.EVAL_W]
            dev = float(np.mean([r["f_s"] for r in ev])) - float(np.mean([r["f_s"] for r in hold]))
            s, pwr = T1V2.evaluate(city, a.price, {w: ev[i] for i, w in enumerate(F.EVAL_W)}, th)
            common = dict(city=city, seed=seed, steps=a.steps, lam=a.lam, rule_on=R1, rule_off=R2,
                          ent_coef=0.01, reward_norm=True, fit_status="fixed", model=os.path.basename(stem),
                          min_logit_gap=gap)
            rows.append(dict(common, fs_minus_hold=dev,
                             J_hold_mean=float(np.mean([r["J"] for r in hold])), **s))
            pw += [dict(common, **r) for r in pwr]
            print(f"E2 {city} seed {seed} lam={a.lam:g}: s_eq={s['s_pooled_eq']:+.2f}% s_raw={s['s_raw']:+.2f}% "
                  f"dT={s['dT_pooled']:+.4f} starts-hold={dev:+.2f}/day gap={gap:.2e} [{time.time()-t0:.0f}s]",
                  flush=True)
        stem_out = V.name("E2").replace("riyadh", city)
        rc = [r for r in rows if r["city"] == city]; pc = [r for r in pw if r["city"] == city]
        IO.write_csv(stem_out, RP._merge(stem_out, rc, a.seed0, a.seeds), inputs=[f"{IO.ROOT}/{city}.epw"])
        IO.write_csv(stem_out + "_perwindow", RP._merge(stem_out + "_perwindow", pc, a.seed0, a.seeds),
                     inputs=[f"{IO.ROOT}/{city}.epw"])


def e1_rows(cities=F.CITIES, windows=None, n_grid=3201, price_v=CFG.PRICE):
    """E1: J(hold) vs the exact lambda = 0 in-rule optimum (unrelaxed DP value, and the relaxed lower
    bound), summed over the tuning windows."""
    import r3_dp as D
    windows = list(F.TUNE_W if windows is None else windows)
    out = []
    for c in cities:
        Jh = sum(F.rule_run(c, w, price_v, R1, R2)["J"] for w in windows)
        Jd = sum(D.lagrangian(c, w, price_v, 0.0, n_grid=n_grid, ruled=True, rule_on=R1, rule_off=R2,
                              terminal="energy")["L"] for w in windows)     # PPO's objective = simulator J
        Jr = sum(D.lagrangian(c, w, price_v, 0.0, n_grid=n_grid, ruled=True, relaxed=True,
                              rule_on=R1, rule_off=R2, terminal="energy")["L"] for w in windows)
        out.append(dict(city=c, windows="TUNE_W", n_grid=n_grid, rule_on=R1, rule_off=R2, J_hold=Jh / len(windows),
                        J_dp=Jd / len(windows), L_relaxed=Jr / len(windows), ratio_hold_dp=Jh / Jd,
                        ratio_hold_bound=Jh / Jr, hold_is_optimum=bool(Jh <= 1.01 * Jd), fit_status="fixed"))
    return out


def main_e1():
    rows = e1_rows()
    for r in rows:
        print(f"E1 {r['city']:7s} J(hold)/J_DP = {r['ratio_hold_dp']:.4f}  J(hold)/L_relaxed = "
              f"{r['ratio_hold_bound']:.4f}  hold optimal (1 %): {r['hold_is_optimum']}", flush=True)
    IO.write_csv(V.name("E1"), rows, inputs=[f"{IO.ROOT}/{c}.epw" for c in F.CITIES])
