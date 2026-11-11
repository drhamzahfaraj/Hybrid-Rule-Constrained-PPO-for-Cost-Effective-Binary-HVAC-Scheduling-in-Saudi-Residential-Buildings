#!/usr/bin/env python3
"""Decisive test of the pre-sampling rule-enforcement fix.

Before the fix, R1/R2 rewrote 38.5% of sampled zone-actions post-hoc, so PPO's
gradient was attached to actions the environment never executed, and the trained
policy scored at random-action level. The mask makes the sampled action comply
before execution (verified: 0/107,520 rewritten).

Benchmarks in this harness: random actions J=2.2612 f_s=14.16;
rule hysteresis (no learning) J=0.3932 f_s=1.84.
"""
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, os, time
sys.path.insert(0, _ROOT + "")
from hvac import *
from env import HVACEnv, Rules
from train import train, eval_policy, agg
from run_all import cooling_test_starts, write, P15

if __name__ == "__main__":
    t0 = time.time()
    P = P15()
    rules = Rules(P, use_hard=True, use_cc=False, use_r3=True)
    H = 7 * int(round(24 / P.dt))
    st, _ = cooling_test_starts("riyadh", P.dt, H, 7)
    rows = []
    for B in (400_000, 1_000_000):
        model, venv, m, to, ir, te, spd = train("riyadh", "4x4", "S", P, 42, B, rules=rules)
        a = agg(eval_policy(model, venv, m, to, ir, st, "S", H, P, rules, n=30))
        rows.append(dict(budget=B, **{k: round(v, 4) for k, v in a.items()}))
        print(f"  FIXED budget {B:>9,}: J={a['J_per_zone_day']:.4f} "
              f"f_s={a['f_s']:.2f} v_c={a['v_c']:.2f}  [{time.time()-t0:.0f}s]", flush=True)
        write("fixtest.csv", rows)
    print(f"\nfixtest done in {time.time()-t0:.0f}s", flush=True)
