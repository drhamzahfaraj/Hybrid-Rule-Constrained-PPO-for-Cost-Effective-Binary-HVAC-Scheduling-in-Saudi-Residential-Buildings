#!/usr/bin/env python3
"""RBRL-SB: the learning agent given the freedom and the view the occupancy
schedule makes worth learning (round 3, author-directed extension).

Differences from rbrl_ppo.py
  Observation (+5 features): occupied flag, time until the occupants return,
    and a 6-h forecast summary (mean and peak outdoor temperature, mean
    south-vertical irradiance) -- the information the 6-h MPC uses.
  Rule layer, occupied steps: R1 (force on at cap - 0.20) and R2 (force off at
    T_min + 0.40) as before.
  Rule layer, empty house: no setback target is imposed; the agent chooses the
    level. Two safety rules only:
      ENV   force on at the envelope AWAY_MAX - 0.20 (RBRL_AWAY_MAX, default 30)
      ARR   arrival guarantee: force on whenever, given the steps left before
            the occupants return, the zone could no longer be brought down to
            cap - 0.30 by then at the plant's net pull-down rate (from the same
            exact plant map; computed on the forecast weather, which is known
            perfectly to the agent as it is to the MPC).
  Reward: -(interval cost + (lam/n_occ) max(T, T_min) on occupied steps
    + PEN deg-h while occupied); lam is the 6-h MPC's fitted multiplier for the
    city, so the agent optimises cost at the comfort level the comparison uses.
  Fitting and evaluation: R1 ceiling fitted on the tuning windows (Rule A),
    held-out windows scored against THERM equalised on the OCCUPIED mean
    (setback_arms.evaluate_sb, Rule C).
"""
from __future__ import annotations
import sys, os, csv, json, time, argparse
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import headroom as H
import setback as S
import final_tables as F
import setback_arms as SA
import t1_v2 as T1V2
import gymnasium as gym
from gymnasium import spaces

EPS_HOT, EPS_COLD = 0.20, 0.40
LO, HI = H.BAND_LO, H.BAND_HI
PEN = 50.0
R = "/home/claude/rbrl/results"
FH = 24                                  # 6-h forecast summary, in steps


class Plant:
    def __init__(self, city, w, c_th=4800.0, faces=1, year=None):
        self.lam_env = H.lam_of(faces, city)
        self.decay = float(np.exp(-H.DT * 3600.0 * self.lam_env / (c_th * 1e3)))
        self.t_out, self.irr, _ = (H.series(city, 168 + 48, w) if year is None
                                   else H.series_amy(city, year, 168 + 48, w))
        self.N = 672
        self.occ = S.occupancy(len(self.t_out))
        self.dnext = SA.steps_to_occ(self.occ)
        g = H.SHGC * H.A_GL * self.irr
        self.Tinf0 = self.t_out + g / self.lam_env
        self.Tinf1 = self.t_out + (g - H.Q_HVAC) / self.lam_env
        self.p_el = H.Q_HVAC / H.cop_series(self.t_out) / 1000.0
        self.c_th = c_th

    def step(self, T, u, k):
        Ti = self.Tinf1[k] if u else self.Tinf0[k]
        return Ti + (T - Ti) * self.decay

    def _thr(self, cap):
        """thr[k]: largest temperature at step k from which 'off at k, then
        full cooling until the return' still ends at or below cap - 0.30.
        Built backward with the exact inverse of the (monotone) plant map."""
        key = round(cap, 4)
        if not hasattr(self, "_thrc"):
            self._thrc = {}
        if key not in self._thrc:
            n = len(self.t_out); thr = np.full(n, np.inf); ycool = np.full(n + 1, np.inf)
            for k in range(n - 1, -1, -1):
                if self.occ[k]:
                    ycool[k] = cap - 0.30            # value needed at the return
                    continue
                # cooling during step k must land at or below ycool[k+1]
                ycool[k] = self.Tinf1[k] + (ycool[k + 1] - self.Tinf1[k]) / self.decay
                thr[k] = self.Tinf0[k] + (ycool[k + 1] - self.Tinf0[k]) / self.decay
            self._thrc[key] = thr
        return self._thrc[key]

    def must_cool(self, T, k, cap):
        """ARR: waiting one more step would make the return comfort unreachable."""
        return (not self.occ[k]) and T > self._thr(cap)[k]

    def obs(self, T, prev, k):
        kk = min(k, self.N - 1); kn = min(k + 4, len(self.t_out) - 1)
        h = (k * H.DT) % 24.0
        fw = slice(k, min(k + FH, len(self.t_out)))
        return np.array([(T - 23.0), float(prev), (self.t_out[kk] - 35.0) / 10.0,
                         (self.t_out[kn] - 35.0) / 10.0, self.irr[kk] / 500.0,
                         np.sin(2 * np.pi * h / 24.0), np.cos(2 * np.pi * h / 24.0), k / self.N,
                         float(self.occ[kk]), min(self.dnext[kk], 96) / 96.0,
                         (self.t_out[fw].mean() - 35.0) / 10.0, (self.t_out[fw].max() - 35.0) / 10.0,
                         self.irr[fw].mean() / 500.0], dtype=np.float32)


EPSC = [EPS_COLD]          # cold guard margin; fitted on tuning windows in v2


def rules(a, T, k, P, cap):
    if P.occ[k]:
        if T >= cap - EPS_HOT: return 1
        if T <= LO + EPSC[0]: return 0
        return int(a)
    if T >= H.AWAY_MAX - 0.20: return 1                   # ENV
    if P.must_cool(T, k, cap): return 1                   # ARR
    return int(a)


class SBEnv(gym.Env):
    def __init__(self, city, windows, lam_w, price_v=0.18, seed=0, years=None):
        super().__init__()
        # windows may be (window, year) pairs for actual-year training
        self.P = {w: (Plant(city, w[0], year=w[1]) if isinstance(w, tuple) else Plant(city, w))
                  for w in windows}
        self.windows = list(windows); self.price_v = price_v
        self.wl = lam_w / int(S.occupancy(672).sum())
        self.rng = np.random.default_rng(seed)
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(-6.0, 6.0, shape=(13,), dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        if seed is not None: self.rng = np.random.default_rng(seed)
        self.w = self.windows[int(self.rng.integers(len(self.windows)))]
        self.T, self.prev, self.k = 23.0, 0, 0
        return self.P[self.w].obs(self.T, self.prev, 0), {}

    def step(self, action):
        P, k = self.P[self.w], self.k
        u = rules(action, self.T, k, P, HI)
        cost = (H.C_SW if (u and not self.prev) else 0.0) + (self.price_v * P.p_el[k] * H.DT if u else 0.0)
        self.T = P.step(self.T, u, k)
        pen = 0.0
        if P.occ[k]:
            pen = self.wl * max(self.T, LO) + PEN * (max(0.0, self.T - HI) + max(0.0, LO - self.T)) * H.DT
        self.prev = u; self.k += 1
        done = self.k >= P.N
        if done:
            cost += self.price_v * (self.T - 23.0) * P.c_th * 1e3 / 3.6e6 / H.COP_RATED
        return P.obs(self.T, self.prev, self.k), float(-(cost + pen)), done, False, {}


def mpc_demos(city, lam, sb_rule, windows, n_grid=2401):
    """(obs, action) pairs from the 6-h setback MPC on the training weather, kept
    only where the rule layer leaves the action free (imitation warm start)."""
    import mpc_lambda as M
    X, Y = [], []
    for (w, y) in windows:
        P = Plant(city, w, year=y)
        # run the MPC on this actual-year window by temporarily routing series()
        orig = H.series
        H.series = lambda c, hrs, sd, _y=y: H.series_amy(c, _y, hrs, sd)
        try:
            M.SETBACK[0] = sb_rule
            acts = M.mpc_actions(city, w, lam, 6.0, n_grid)
        finally:
            H.series = orig
        T, prev = 23.0, 0
        for k, u in enumerate(acts):
            o = P.obs(T, prev, k)
            if rules(1 - u, T, k, P, HI) == 1 - u:          # free step (not overridden)
                X.append(o); Y.append(u)
            T = P.step(T, u, k); prev = u
    return np.array(X, np.float32), np.array(Y, np.int64)


def behaviour_clone(model, X, Y, epochs=30, lr=1e-3):
    import torch
    pol = model.policy
    opt = torch.optim.Adam(pol.parameters(), lr=lr)
    Xt, Yt = torch.as_tensor(X), torch.as_tensor(Y)
    for _ in range(epochs):
        idx = torch.randperm(len(Xt))
        for b in range(0, len(Xt), 512):
            j = idx[b:b + 512]
            dist = pol.get_distribution(Xt[j])
            loss = -dist.log_prob(Yt[j]).mean()
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        acc = float((pol.get_distribution(Xt).distribution.probs.argmax(1) == Yt).float().mean())
    return acc


def evaluate(act_fn, city, w, cap, price_v=0.18):
    P = Plant(city, w)
    N, occ, lo, hi, price = SA.ctx(city, w)
    def pol(T, prev, k):
        return rules(act_fn(P.obs(T, prev, k)), T, k, P, cap)
    return S.sim(pol, city, F.FACES, 4800.0, price, lo, hi, occ, 168, w, 23.0, c_sw=F.C_SW)


DROPPED = ("rbrl_sb (RBRL-SB) is a dropped arm (RULING_round4 §5, F14): its rule layer, BC filter and "
           "setback baseline predate the v3 protocol. The setback arms are setback_arms.py (TUNED-SB, "
           "MANUAL, THERM-SB, MPC-SB). SBEnv.step stays as the template of the E2 reward (rbrl_e2.py).")


def main():
    raise SystemExit(DROPPED)
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", default="riyadh,jeddah,taif")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--steps", type=int, default=200_000)
    ap.add_argument("--out", default="T30_rbrl_sb")
    ap.add_argument("--amy", action="store_true", help="train on the clean ERA5 years")
    ap.add_argument("--bc", action="store_true", help="warm-start by imitating the 6-h setback MPC")
    ap.add_argument("--fit-margins", action="store_true", help="fit the cold guard margin (Rule A)")
    a = ap.parse_args()
    from stable_baselines3 import PPO
    import rbrl_ppo as RP
    rows, perw = [], []
    for city in a.cities.split(","):
        lam = float(next(r for r in csv.DictReader(open(f"{R}/T21v2_{city}{H.TAG}.csv"))
                         if float(r["horizon_h"]) == 6.0)["lam"])
        tgt = {w: SA.therm_sb(city, w, 0.0)[F.MEAN_KEY] for w in F.TUNE_W}
        for seed in range(42, 42 + a.seeds):
            t0 = time.time()
            trainw = ([(w, y) for y in H.AMY_TRAIN_YEARS[city] for w in F.WINDOWS] if a.amy
                      else list(F.TUNE_W))
            env = SBEnv(city, trainw, lam, seed=seed)
            model = PPO("MlpPolicy", env, seed=seed, verbose=0, n_steps=1344, batch_size=336,
                        gamma=0.999, learning_rate=3e-4, policy_kwargs=dict(net_arch=[256, 128]))
            bc_acc = ""
            if a.bc:
                if "demos" not in locals() or demos[0] != city:
                    prm = json.load(open(f"{R}/setback_rule_params{H.TAG}.json"))[city]
                    sbr = (prm["on"], prm["off"], prm["lead_steps"], prm.get("away_on", 29.8))
                    dw = [(w, y) for y in H.AMY_TRAIN_YEARS[city] for w in F.WINDOWS[::2]] if a.amy \
                        else [(w, None) for w in F.TUNE_W]
                    demos = (city,) + mpc_demos(city, lam, sbr, dw)
                bc_acc = behaviour_clone(model, demos[1], demos[2])
            model.learn(total_timesteps=a.steps)
            os.makedirs(f"{R}/models", exist_ok=True)
            model.save(f"{R}/models/{a.out}{H.TAG}_{city}_{seed}")
            fast = RP.numpy_policy(model) if hasattr(RP, "numpy_policy") else None
            if fast is None:
                fast = lambda o: int(model.predict(o, deterministic=True)[0])
            caps = [round(c, 2) for c in np.arange(HI - 0.5, HI + 1e-4, 0.01)]
            margins = (0.30, 0.35, 0.40) if a.fit_margins else (EPS_COLD,)
            # Rule A4 (final_tables.fit_param) jointly over (R2 margin, R1 cap), margin-major order;
            # setback comparator; no silent cap = HI (fit_status none -> not evaluated)
            def _run(p, w):
                EPSC[0] = p[0]
                return evaluate(fast, city, w, p[1])
            fit = F.fit_param([(m_, c) for m_ in margins for c in caps], _run, F.TUNE_W,
                              city=city, price_v=0.18, setback=True)
            if fit is None:
                print(f"{city:7s} seed {seed}: no admissible (margin, cap) (fit_status none)", flush=True)
                rows.append(dict(city=city, seed=seed, cap="", fit_status="none")); continue
            EPSC[0], cap = fit[1]
            fit_status = fit.fit_status
            runs = {w: evaluate(fast, city, w, cap) for w in F.EVAL_W}
            s, pw = SA.evaluate_sb(city, runs)
            rows.append(dict(city=city, seed=seed, cap=cap, eps_cold=EPSC[0], lam=lam,
                             amy=a.amy, bc=a.bc, bc_acc=bc_acc, fit_status=fit_status, **s))
            perw += [dict(city=city, seed=seed, cap=cap, fit_status=fit_status, **r) for r in pw]
            print(f"{city:7s} seed {seed}: cap={cap} s_eq={s['s_pooled_eq']:+.2f}% s_raw={s['s_raw']:+.2f}% "
                  f"E={s['energy_sav_eq']:+.1f}% starts={s['start_sav_eq']:+.1f}% over={s['deg_h_over']:.3f} "
                  f"[{time.time()-t0:.0f}s]", flush=True)
            T1V2.write(a.out, rows); T1V2.write(f"{a.out}_perwindow", perw)


if __name__ == "__main__":
    main()
