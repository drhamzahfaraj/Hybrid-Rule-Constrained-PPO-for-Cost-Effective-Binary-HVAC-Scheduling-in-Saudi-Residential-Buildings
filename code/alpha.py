#!/usr/bin/env python3
"""Comfort-penalty weight sweep.

Diagnostic: at alpha=50 the comfort term averages 77.7 per step under random
actions against 0.117 for the switching term -- a 670:1 imbalance. Under
VecNormalize(norm_reward=True) the switching signal is then ~0.15% of the
gradient, so PPO optimises comfort and is indifferent to switching. The
f_s ~ 14 plateau across training budgets is consistent with that reading.

This sweep reduces alpha so the two terms are commensurate and establishes
whether PPO becomes competitive with the rule-based reference once it can
actually see the objective.
"""
from __future__ import annotations
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hvac import *
from env import HVACEnv, Rules, run_policy, therm
from train import train, eval_policy, agg, load_city
from run_all import cooling_test_starts, write, P15

STEPS = 400_000
SEED = 42
ALPHAS = [50.0, 2.0, 0.5]


def main():
    t0 = time.time()
    P = P15()
    rules = Rules(P, use_hard=True, use_cc=False, use_r3=True)
    H = 7 * int(round(24 / P.dt))
    st, _ = cooling_test_starts("riyadh", P.dt, H, 7)
    rows = []

    # reference
    m = HVACModel("4x4", P); to, ir = load_city("riyadh")
    env = HVACEnv(m, to, ir, st, cost_model="S", horizon=H, P=P,
                  rules=Rules(P, use_cc=False))
    r = agg([run_policy(env, therm(3.15), start=int(s)) for s in st[:30]])
    rows.append(dict(alpha="ref", controller="HYST", **{k: round(v, 4) for k, v in r.items()}))
    print(f"  reference HYST: J={r['J_per_zone_day']:.4f} f_s={r['f_s']:.2f} "
          f"v_c={r['v_c']:.2f}", flush=True)
    write("alpha.csv", rows)

    for a in ALPHAS:
        model, venv, m2, to2, ir2, te, spd = train(
            "riyadh", "4x4", "S", P, SEED, STEPS, rules=rules, alpha=a)
        o = agg(eval_policy(model, venv, m2, to2, ir2, st, "S", H, P, rules, n=30))
        rows.append(dict(alpha=a, controller="RBRL", **{k: round(v, 4) for k, v in o.items()}))
        print(f"  alpha={a:>5}: J={o['J_per_zone_day']:.4f} f_s={o['f_s']:.2f} "
              f"v_c={o['v_c']:.2f}  [{time.time()-t0:.0f}s]", flush=True)
        write("alpha.csv", rows)

    print(f"\nalpha sweep done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
