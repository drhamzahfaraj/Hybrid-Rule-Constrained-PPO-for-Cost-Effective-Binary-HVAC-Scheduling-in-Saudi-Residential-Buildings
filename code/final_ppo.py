#!/usr/bin/env python3
"""PPO run after the logit-hook defect was removed.

Benchmarks in this harness (24-30 held-out weeks, Riyadh 4x4, Model S):
  random actions          J = 2.2612  f_s = 14.16  v_c = 3.03
  always-on               J = 2.5047  f_s = 15.78
  rule hysteresis (3.15K) J = 0.3932  f_s = 1.84   v_c = 0.82
"""
import sys, os, time
sys.path.insert(0, "/home/claude/rbrl")
from env import Rules
from train import train, eval_policy, agg
from run_all import cooling_test_starts, write, P15

if __name__ == "__main__":
    t0 = time.time(); rows = []
    P = P15(); rules = Rules(P, use_hard=True, use_cc=False, use_r3=True)
    H = 7 * int(round(24 / P.dt))
    st, _ = cooling_test_starts("riyadh", P.dt, H, 7)
    for B in (100_000, 300_000):
        model, venv, m, to, ir, te, spd = train("riyadh", "4x4", "S", P, 42, B, rules=rules)
        a = agg(eval_policy(model, venv, m, to, ir, st, "S", H, P, rules, n=30))
        rows.append(dict(budget=B, **{k: round(v, 4) for k, v in a.items()}))
        print(f"  PPO budget {B:>8,}: J={a['J_per_zone_day']:.4f} f_s={a['f_s']:.2f} "
              f"v_c={a['v_c']:.2f}  [{time.time()-t0:.0f}s]", flush=True)
        write("final_ppo.csv", rows)
    print(f"\ndone in {time.time()-t0:.0f}s", flush=True)
