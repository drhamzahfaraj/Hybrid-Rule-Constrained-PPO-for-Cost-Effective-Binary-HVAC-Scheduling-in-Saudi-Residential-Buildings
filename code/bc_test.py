#!/usr/bin/env python3
"""Reverse-engineering test: can the policy class REPRESENT the DP optimum?

The forward direction has been exhausted. Measured so far, single-zone-matched
4x4 Riyadh Model S in this harness:
  - the optimiser is healthy (approx_kl 0.001, clip_fraction ~0, EV 0.9)
  - the reward weighting is not the cause (alpha 50 -> 0.5 moves J only 7.6%)
  - PPO sits at random-action level regardless

So we start from the optimum and work back. This script:
  1. solves the single-zone problem exactly by DP (dp2.solve)
  2. rolls the optimal policy out, recording (observation, optimal action)
     pairs using the SAME observation vector the PPO agent receives
  3. fits that mapping supervised (behaviour cloning)
  4. reports fit accuracy and the cost achieved by the fitted policy

Interpretation:
  * high accuracy AND near-optimal cost -> the policy class and the observation
    are sufficient; the failure is exploration / credit assignment in PPO
  * high accuracy BUT poor cost          -> compounding error; the task is
    sensitive to rare decisions
  * low accuracy                         -> the observation is insufficient to
    determine the optimal action; no amount of RL tuning can fix it, the state
    must be extended
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np, torch, torch.nn as nn
from hvac import HVACModel, Params, read_epw, vertical_irradiance
from dp2 import solve

CITY = "riyadh"
HOURS, START = 168, 181
DT, C_TH = 0.25, 2400.0
LAM, QH, COP = 33.0, 2000.0, 2.985
TMIN, TMAX, CSW, PRICE = 22.0, 26.0, 0.15, 0.18
SHGC, AGL = 0.25, 2.0


def series():
    lat = {"riyadh": 24.7, "jeddah": 21.5}[CITY]
    tdb, dni, dhi = read_epw(f"/home/claude/rbrl/{CITY}.epw")
    irr = vertical_irradiance(dni, dhi, lat, azimuth_deg=180.0)
    spd = int(round(1.0 / DT)); N = int(round(HOURS / DT)); h0 = START * 24
    return (np.repeat(tdb[h0:h0 + HOURS + 4], spd)[:N + 12],
            np.repeat(irr[h0:h0 + HOURS + 4], spd)[:N + 12], N)


def obs_of(T, prev_u, k, t_out, e_cum):
    """The same observation layout the PPO agent sees, for one zone."""
    spd = int(round(24.0 / DT))
    hod = (k % spd) * DT
    return np.array([
        (T - 24.0) / 4.0,                  # zone temperature
        (T - 24.0) / 4.0,                  # inter-zone (single zone: itself)
        float(prev_u),                     # previous action
        (t_out[k + 1] - 35.0) / 10.0,      # 3-step outdoor forecast
        (t_out[k + 2] - 35.0) / 10.0,
        (t_out[k + 3] - 35.0) / 10.0,
        e_cum / 2000.0,
        np.sin(2 * np.pi * hod / 24.0),
        np.cos(2 * np.pi * hod / 24.0),
    ], dtype=np.float32)


def rollout_optimal():
    """Replay the DP optimal policy, recording observations and actions."""
    r = solve(city=CITY, walls=1, mode="hard", n_grid=1001, verbose=False)
    t_out, irrad, N = series()
    decay = float(np.exp(-DT * 3600.0 * LAM / (C_TH * 1e3)))
    p_hvac = QH / COP / 1000.0
    X, Y = [], []
    T, up, e = 24.0, 0, 0.0
    cost = 0.0; sw = 0; viol = 0
    for k, (_, _, u) in enumerate(r["traj"]):
        X.append(obs_of(T, up, k, t_out, e)); Y.append(int(u))
        if u == 1 and up == 0: cost += CSW; sw += 1
        if u == 1: cost += PRICE * p_hvac * DT; e += p_hvac * DT
        T_inf = t_out[k] + (SHGC * AGL * irrad[k] - QH * u) / LAM
        T = T_inf + (T - T_inf) * decay
        if T > TMAX or T < TMIN: viol += 1
        up = u
    d = HOURS / 24.0
    return (np.array(X), np.array(Y, dtype=np.float32),
            dict(J=cost / d, f_s=sw / d, v_c=100.0 * viol / N), r)


def simulate(pick):
    """Run a policy given as pick(obs) -> 0/1, in the DP's exact setting."""
    t_out, irrad, N = series()
    decay = float(np.exp(-DT * 3600.0 * LAM / (C_TH * 1e3)))
    p_hvac = QH / COP / 1000.0
    T, up, e = 24.0, 0, 0.0
    cost = 0.0; sw = 0; viol = 0; dh = 0.0
    for k in range(N):
        u = int(pick(obs_of(T, up, k, t_out, e)))
        if u == 1 and up == 0: cost += CSW; sw += 1
        if u == 1: cost += PRICE * p_hvac * DT; e += p_hvac * DT
        T_inf = t_out[k] + (SHGC * AGL * irrad[k] - QH * u) / LAM
        T = T_inf + (T - T_inf) * decay
        if T > TMAX or T < TMIN:
            viol += 1
            dh += max(0.0, T - TMAX) * DT + max(0.0, TMIN - T) * DT
        up = u
    d = HOURS / 24.0
    return dict(J=cost / d, f_s=sw / d, v_c=100.0 * viol / N, dh=dh)


if __name__ == "__main__":
    torch.manual_seed(0); np.random.seed(0)
    X, Y, opt, dpres = rollout_optimal()
    print(f"DP optimum replayed: J*={opt['J']:.4f} f_s={opt['f_s']:.2f} v_c={opt['v_c']:.2f}%")
    print(f"dataset: {len(X)} steps, optimal action is ON {100*Y.mean():.1f}% of steps\n")

    net = nn.Sequential(nn.Linear(X.shape[1], 128), nn.ReLU(),
                        nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))
    optim = torch.optim.Adam(net.parameters(), lr=1e-3)
    lossf = nn.BCEWithLogitsLoss()
    Xt = torch.as_tensor(X); Yt = torch.as_tensor(Y).unsqueeze(1)
    for ep in range(1, 601):
        optim.zero_grad()
        out = net(Xt); loss = lossf(out, Yt)
        loss.backward(); optim.step()
        if ep % 150 == 0:
            acc = ((out > 0).float() == Yt).float().mean().item()
            print(f"  epoch {ep:4d}  loss {loss.item():.4f}  train accuracy {100*acc:.2f}%",
                  flush=True)
    with torch.no_grad():
        acc = ((net(Xt) > 0).float() == Yt).float().mean().item()
    print(f"\nBEHAVIOUR-CLONING FIT: {100*acc:.2f}% of optimal actions reproduced")

    def pick(o):
        with torch.no_grad():
            return int(net(torch.as_tensor(o).unsqueeze(0)).item() > 0)
    bc = simulate(pick)
    print(f"cloned policy in closed loop: J={bc['J']:.4f} f_s={bc['f_s']:.2f} "
          f"v_c={bc['v_c']:.2f}% deg-h={bc['dh']:.2f}")
    print(f"gap to optimum: {100*(bc['J']-opt['J'])/opt['J']:+.1f}%")
    print("\nReference points in this exact setting:")
    print(f"  DP optimum                 J = {opt['J']:.4f}")
    print(f"  best feasible hysteresis   J = 1.4133  (2.0 K, +27.5%)")
