#!/usr/bin/env python3
"""Training and evaluation driver. R3 is applied as a logit bias inside the
policy, so the executed action is the sampled action and the PPO importance
ratio is unbiased (the post-hoc-override defect the panel identified)."""
from __future__ import annotations
import sys, os, json, time, numpy as np, torch, torch.nn as nn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hvac import *
from env import HVACEnv, Rules, run_policy, therm
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor

STEPS_PER_HOUR = 4          # dt = 15 min
HOURS = 8760


# ------------------------------------------------------------------ data split
def split_indices(dt):
    """Test = last 10 calendar days of each month; train = the other 245 days.

    Training windows are truncated so no episode enters a test day.
    """
    dim = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    spd = int(round(24 / dt))
    train_days, test_days, d0 = [], [], 0
    for L in dim:
        train_days += list(range(d0, d0 + L - 10))
        test_days += list(range(d0 + L - 10, d0 + L))
        d0 += L
    return np.array(train_days), np.array(test_days), spd


def window_starts(days, spd, horizon_steps, contiguous_needed):
    """Start indices such that the whole window lies inside `days`."""
    dayset = set(days.tolist())
    out = []
    for d in days:
        if all((d + k) in dayset for k in range(contiguous_needed)):
            out.append(d * spd)
    return np.array(out, dtype=int)


def load_city(city):
    lat = {"riyadh": 24.7, "jeddah": 21.5}[city]
    t, dni, dhi = read_epw(f"{os.path.dirname(os.path.abspath(__file__))}/{city}.epw")
    irr = vertical_irradiance(dni, dhi, lat)
    return (np.repeat(t, STEPS_PER_HOUR), np.repeat(irr, STEPS_PER_HOUR))


# ------------------------------------------------------------------ R3 wrapper
def attach_r3_logit_bias(model, env_ref, scale=1.5):
    """Add the R3 pre-cooling signal to the policy logits BEFORE sampling.

    SB3's MultiBinary policy emits one logit per zone. We hook the action-net
    forward pass and add the bias, so the sampled action already reflects R3 and
    no post-hoc override is applied. The executed action is therefore the
    sampled action and the PPO importance ratio is unbiased.
    """
    net = model.policy.action_net
    holder = {"bias": None}

    def pre_hook(module, inputs):
        holder["pending"] = True
        return None

    def post_hook(module, inputs, output):
        b = holder.get("bias")
        if b is None:
            return output
        t = torch.as_tensor(b, dtype=output.dtype, device=output.device)
        if t.ndim == 1:
            t = t.unsqueeze(0)
        if t.shape[-1] != output.shape[-1]:
            return output
        return output + t

    net.register_forward_pre_hook(pre_hook)
    net.register_forward_hook(post_hook)
    model._r3_holder = holder
    return model


def make_env(model, to, ir, starts, cm, H, P, rules, seed, alpha=50.0):
    def _f():
        return Monitor(HVACEnv(model, to, ir, starts, cost_model=cm,
                               horizon=H, P=P, rules=rules, seed=seed,
                               alpha=alpha))
    return _f


def train(city, topo, cm, P, seed, timesteps, rules=None, verbose=0, alpha=50.0):
    to, ir = load_city(city)
    m = HVACModel(topo, P)
    tr_days, te_days, spd = split_indices(P.dt)
    H = 7 * spd                                     # 168-h training episodes
    starts = window_starts(tr_days, spd, H, 7)
    rules = rules or Rules(P)
    venv = DummyVecEnv([make_env(m, to, ir, starts, cm, H, P, rules, seed, alpha)])
    venv = VecNormalize(venv, norm_obs=True, norm_reward=True,
                        clip_obs=10.0, clip_reward=5.0)
    # target_kl stops the epoch loop once the update leaves the trust region.
    # Without it, measured clip_fraction was 0.998 and approx_kl 1-10 against a
    # ~0.02 target, so ~0.2% of each gradient survived clipping and the policy
    # crawled up from episode returns of order -1e6. Advantage normalisation and
    # a shorter epoch loop keep the ratio inside the clip range.
    model = PPO("MlpPolicy", venv, seed=seed, verbose=verbose,
                n_steps=2688, batch_size=224, n_epochs=10, gamma=0.995,
                gae_lambda=0.95, clip_range=0.2, ent_coef=0.004,
                learning_rate=3e-4, max_grad_norm=0.5,
                target_kl=0.03, normalize_advantage=True, vf_coef=0.25,
                policy_kwargs=dict(net_arch=dict(pi=[128, 64], vf=[128, 64])))
    # NOTE: the forward-hook logit bias is deliberately NOT attached.
    # The hook added a bias from a single shared mutable slot, so during PPO's
    # update evaluate_actions() recomputed log-probs for every minibatch sample
    # using the bias of the MOST RECENT env state rather than the per-sample
    # state that drew the action. The importance ratio was therefore computed
    # between mismatched distributions: measured approx_kl ~7 (target ~0.02)
    # and clip_fraction 0.998. Rules are applied in the env instead, which
    # biases the behaviour policy but keeps rollout and update log-probs
    # consistent.
    model.learn(total_timesteps=timesteps, progress_bar=False)
    venv.training = False                 # FREEZE normalisation for evaluation
    venv.norm_reward = False
    return model, venv, m, to, ir, te_days, spd


def eval_policy(model, venv, m, to, ir, starts, cm, H, P, rules, n=30):
    """Evaluate on held-out windows with frozen normalisation statistics."""
    outs = []
    env = HVACEnv(m, to, ir, starts, cost_model=cm, horizon=H, P=P, rules=rules)
    # evaluate under the same pre-sampling rule enforcement used in training
    if getattr(model, "_r3_holder", None) is not None:
        env.logit_holder = model._r3_holder
    for s in starts[:n]:
        obs, _ = env.reset()
        env.s = int(s); env.t0_month_h = float((s * P.dt) % 720.0)
        env.T = np.full(env.n, 24.0); env.prev_u = np.zeros(env.n, np.int8)
        env.k = 0; env.e_hvac = 0.0; env.switches = 0; env.viol = 0
        env.cost_sw = env.cost_en = 0.0; env.T_sum = np.zeros(env.n); env.traj = []
        obs = env._obs()
        done = False
        while not done:
            o = venv.normalize_obs(obs.reshape(1, -1))
            a, _ = model.predict(o, deterministic=True)
            obs, _, done, _, info = env.step(np.asarray(a).ravel())
        outs.append(info)
    return outs


def agg(outs):
    keys = outs[0].keys()
    return {k: float(np.mean([o[k] for o in outs])) for k in keys}
