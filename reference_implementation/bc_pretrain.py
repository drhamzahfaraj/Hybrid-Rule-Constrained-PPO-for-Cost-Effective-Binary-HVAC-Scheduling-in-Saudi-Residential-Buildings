"""Pre-train the RBRL policy by behaviour cloning from a dynamic-programming
solution, then hand the result to PPO for fine-tuning.

Why this is needed
------------------
Trained from scratch, PPO settles into a local optimum: it hovers at a
slightly lower temperature, gaining a few per cent on energy, while cycling
two to three times more than the thermostat.  The extra wear cost exceeds the
energy saved, so total cost rises.  The optimum found by dynamic programming
does the opposite -- it cools through the morning, coasts through the
afternoon peak, and uses FEWER switches than the thermostat.  Random
exploration over N binary zones essentially never produces that trajectory,
so the policy gradient never points toward it.

Behaviour cloning removes the exploration problem: the DP supplies exact
demonstrations, the policy network is fitted to them by supervised learning,
and PPO then fine-tunes from a starting point that already has the right
structure.

Usage
-----
    python bc_pretrain.py --city riyadh --cfg 4x4 --model S
    python train_ppo.py  --city riyadh --cfg 4x4 --model S \
                         --init checkpoints/bc_riyadh_4x4_S.zip --episodes 20000

Requires: torch, stable-baselines3
"""
import argparse
import os

import numpy as np
import torch
import torch.nn.functional as F
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from hvac_env import (CONFIGS, HVACEnv, P, cop, hard_rules, price,
                      q_capacity, run_episode, policy_therm)


# ------------------------------------------------------------------ DP
def solve_zone_dp(env, zone, start_day, hours, t_grid_step=0.1):
    """Optimal state-feedback policy for one zone over `horizon` hours.

    Inter-zone coupling is ignored here: neighbours are a second-order effect
    for a demonstration, and PPO recovers them during fine-tuning.  The zone's
    own exterior exposure IS respected, so interior zones (no envelope load)
    get their own, different policy.
    """
    lam = (P.lam_ext + P.lam_win) * env.ext[zone]
    solar_scale = P.shgc * P.a_gl * env.ext[zone]
    C = P.c_th * 1000.0
    t_out, ghi = env.t_out, env.ghi

    grid = np.arange(P.t_min + P.eps_g, P.t_max - P.eps_g + 1e-9, t_grid_step)
    nT = len(grid)
    INF = 1e18
    horizon = int(hours / P.dt)          # number of control steps

    def nxt(T, u, h):
        qc = q_capacity(P.q_cool, t_out[h])
        q = -qc * 1000.0 * u - lam * (T - t_out[h]) + solar_scale * ghi[h]
        return T + P.dt * 3600.0 / C * q

    V = np.zeros((nT, 2))
    POL = np.zeros((horizon, nT, 2), dtype=np.int8)
    e_ref = P.e_base                      # marginal price is flat below 6 MWh

    for k in range(horizon - 1, -1, -1):
        h = int(start_day * 24 + k * P.dt) % 8760
        qc = q_capacity(P.q_cool, t_out[h])
        el = qc / cop(t_out[h]) + P.fan_w / 1000.0
        p = price(env.model, e_ref)
        Vn = np.full((nT, 2), INF)
        for i, T in enumerate(grid):
            for pu in (0, 1):
                best, best_a = INF, 0
                for u in (0, 1):
                    Tn = nxt(T, u, h)
                    if Tn < grid[0] - 1e-9 or Tn > grid[-1] + 1e-9:
                        continue
                    j = int(np.clip(round((Tn - grid[0]) / t_grid_step), 0, nT - 1))
                    c = p * el * u * P.dt
                    if u == 1 and pu == 0:
                        c += P.c_sw + p * el * P.cd * (4.0 / 60.0)
                    v = c + V[j, u]
                    if v < best:
                        best, best_a = v, u
                Vn[i, pu] = best
                POL[k, i, pu] = best_a
        V = Vn
    return POL, grid


# ------------------------------------------------------------------ demos
def _zone_policies(env, day, hours=168):
    """One DP per exposure class (exterior / interior) for a given start day."""
    pols = {}
    for z in range(env.n):
        key = env.ext[z]
        if key not in pols:
            pols[key] = solve_zone_dp(env, z, int(day), hours)
    return pols


def _dp_action(env, pols):
    """Expert action for the environment's current state."""
    u = np.zeros(env.n, dtype=int)
    for z in range(env.n):
        POL, grid = pols[env.ext[z]]
        i = int(np.clip(round((env.T[z] - grid[0]) / (grid[1] - grid[0])),
                        0, len(grid) - 1))
        u[z] = POL[min(env.k, POL.shape[0] - 1), i, env.prev[z]]
    return u


def dagger(city, cfg, model, agent, rounds=3, weeks_per_round=6,
           horizon=168, verbose=True):
    """Iterative relabelling (DAgger).

    Behaviour cloning trains on states the expert visits, but the learner
    visits a slightly different distribution; errors there compound and the
    policy settles short of the demonstrations.  DAgger closes the gap by
    rolling out the CURRENT policy, asking the expert what it would have done
    in the states actually reached, and adding those pairs to the dataset.
    """
    env = HVACEnv(city=city, cfg=cfg, cost_model=model)
    starts = env._starts(train=True)
    rng = np.random.default_rng(1)
    obs_new, act_new = [], []
    for r in range(rounds):
        days = rng.choice(starts, size=min(weeks_per_round, len(starts)),
                          replace=False)
        for day in days:
            pols = _zone_policies(env, day, horizon)
            env.reset(train=True, start_day=int(day))
            for _ in range(int(horizon / P.dt)):
                obs = env._obs()
                expert = hard_rules(_dp_action(env, pols), env.T)
                learner, _ = agent.predict(obs, deterministic=True)
                obs_new.append(obs)
                act_new.append(expert)          # label with the expert
                env.step(np.asarray(learner, dtype=int))   # follow the learner
        if verbose:
            print(f"  DAgger round {r + 1}/{rounds}: "
                  f"{len(obs_new)} relabelled pairs", flush=True)
    return (np.asarray(obs_new, dtype=np.float32),
            np.asarray(act_new, dtype=np.float32))


def collect_demonstrations(city, cfg, model, n_weeks, horizon=168, verbose=True):
    """Roll the DP policy out in the full multi-zone environment.

    Actions come from the per-zone DP; the environment applies the hard rules
    and the true coupled dynamics, so the recorded observations are exactly
    those the agent will see.
    """
    env = HVACEnv(city=city, cfg=cfg, cost_model=model)
    starts = env._starts(train=True)
    rng = np.random.default_rng(0)
    chosen = rng.choice(starts, size=min(n_weeks, len(starts)), replace=False)

    # one DP per distinct exposure class (exterior / interior)
    obs_all, act_all = [], []
    for w, day in enumerate(chosen):
        pols = {}
        for z in range(env.n):
            key = env.ext[z]
            if key not in pols:
                pols[key] = solve_zone_dp(env, z, int(day), horizon)
        env.reset(train=True, start_day=int(day))
        for k in range(int(horizon / P.dt)):
            obs = env._obs()
            u = np.zeros(env.n, dtype=int)
            for z in range(env.n):
                POL, grid = pols[env.ext[z]]
                i = int(np.clip(round((env.T[z] - grid[0]) / (grid[1] - grid[0])),
                                0, len(grid) - 1))
                u[z] = POL[k, i, env.prev[z]]
            obs_all.append(obs)
            act_all.append(hard_rules(u, env.T))
            env.step(u)
        if verbose:
            print(f"  week {w + 1}/{len(chosen)} (day {int(day)}) collected",
                  flush=True)
    return np.asarray(obs_all, dtype=np.float32), \
           np.asarray(act_all, dtype=np.float32)


# ------------------------------------------------------------------ BC
def behaviour_clone(city, cfg, model, obs, act, epochs=60, batch=256, lr=1e-3):
    """Fit the PPO policy network to the demonstrations."""
    def _factory():
        return HVACEnv(city=city, cfg=cfg, cost_model=model)

    venv = DummyVecEnv([_factory])
    # observations are already scaled inside the environment, so obs
    # normalisation is disabled to keep BC and fine-tuning consistent
    venv = VecNormalize(venv, norm_obs=False, norm_reward=False)

    agent = PPO("MlpPolicy", venv, verbose=0, device="auto",
                policy_kwargs=dict(net_arch=dict(pi=[256, 128], vf=[256, 128]),
                                   activation_fn=torch.nn.ReLU))

    dev = agent.device
    X = torch.as_tensor(obs, device=dev)
    Y = torch.as_tensor(act, device=dev)
    params = list(agent.policy.mlp_extractor.policy_net.parameters()) + \
             list(agent.policy.action_net.parameters()) + \
             list(agent.policy.features_extractor.parameters())
    opt = torch.optim.Adam(params, lr=lr)

    n = len(X)
    for ep in range(epochs):
        perm = torch.randperm(n, device=dev)
        tot = 0.0
        for s in range(0, n, batch):
            idx = perm[s:s + batch]
            feats = agent.policy.extract_features(X[idx])
            if isinstance(feats, tuple):
                feats = feats[0]
            latent = agent.policy.mlp_extractor.forward_actor(feats)
            logits = agent.policy.action_net(latent)
            loss = F.binary_cross_entropy_with_logits(logits, Y[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        if (ep + 1) % 10 == 0 or ep == 0:
            with torch.no_grad():
                feats = agent.policy.extract_features(X)
                if isinstance(feats, tuple):
                    feats = feats[0]
                logits = agent.policy.action_net(
                    agent.policy.mlp_extractor.forward_actor(feats))
                acc = ((logits > 0).float() == Y).float().mean().item()
            print(f"  epoch {ep + 1:>3}: loss {tot / n:.4f}  match {acc:.3f}",
                  flush=True)
    return agent, venv


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="riyadh", choices=["riyadh", "jeddah"])
    ap.add_argument("--cfg", default="4x4", choices=list(CONFIGS))
    ap.add_argument("--model", default="S", choices=["L", "E", "S"])
    ap.add_argument("--weeks", type=int, default=12,
                    help="demonstration weeks to collect")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--dagger", type=int, default=0,
                    help="DAgger rounds after the initial clone (0 = off)")
    ap.add_argument("--out", default="checkpoints")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print(f"[1/3] collecting DP demonstrations "
          f"({args.city}, {args.cfg}, model {args.model})")
    obs, act = collect_demonstrations(args.city, args.cfg, args.model,
                                      args.weeks)
    print(f"      {len(obs)} state-action pairs, "
          f"duty cycle {act.mean():.3f}")

    print("[2/3] behaviour cloning")
    agent, venv = behaviour_clone(args.city, args.cfg, args.model,
                                  obs, act, epochs=args.epochs)

    if args.dagger:
        print(f"[2b] DAgger: {args.dagger} rounds of expert relabelling")
        o2, a2 = dagger(args.city, args.cfg, args.model, agent,
                        rounds=args.dagger)
        obs = np.concatenate([obs, o2]); act = np.concatenate([act, a2])
        print(f"      dataset now {len(obs)} pairs; refitting")
        agent, venv = behaviour_clone(args.city, args.cfg, args.model,
                                      obs, act, epochs=args.epochs)

    print("[3/3] evaluating the cloned policy on held-out days")
    env = HVACEnv(city=args.city, cfg=args.cfg, cost_model=args.model)
    starts = env._starts(train=False)

    def agent_policy(e):
        a, _ = agent.predict(e._obs(), deterministic=True)
        return np.asarray(a, dtype=int)

    # THERM is a baseline: score it on its own logic, without the RBRL rule
    # layer (otherwise it inherits R3 pre-cooling and its switching cost).
    base = [run_episode(env, policy_therm, start_day=int(d), baseline=True)
            for d in starts]
    clone = [run_episode(env, agent_policy, start_day=int(d)) for d in starts]
    bJ = float(np.mean([r["J"] for r in base]))
    cJ = float(np.mean([r["J"] for r in clone]))
    print(f"      THERM {bJ:.3f} SAR/z/d, sw {np.mean([r['fs'] for r in base]):.2f}")
    print(f"      BC    {cJ:.3f} SAR/z/d, sw {np.mean([r['fs'] for r in clone]):.2f}, "
          f"vc {np.mean([r['vc'] for r in clone]):.2f}%")
    print(f"      saving {100 * (bJ - cJ) / bJ:+.2f}%")

    tag = os.path.join(args.out, f"bc_{args.city}_{args.cfg}_{args.model}")
    agent.save(tag)
    venv.save(tag + "_vecnorm.pkl")
    print(f"saved {tag}.zip  -- pass to train_ppo.py with --init")


if __name__ == "__main__":
    main()
