#!/usr/bin/env python3
"""Training-budget sweep for the manuscript's own rule set (R1+R2 hard, R3 soft).

The 150k-step result (J=2.1569, f_s=13.55) has the signature of an undertrained
policy rather than a converged one. This sweep establishes whether PPO under the
paper's rule layer approaches the rule-based hysteresis reference (J=0.2596) when
given a budget comparable to the manuscript's, or whether the gap persists.

Single seed per budget: we are looking for a trend across two orders of
magnitude, not a variance estimate.
"""
from __future__ import annotations
import sys, os, csv, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hvac import *
from env import HVACEnv, Rules, run_policy, therm
from train import train, eval_policy, agg
from run_all import cooling_test_starts, write, P15

BUDGETS = [150_000, 400_000, 1_000_000, 2_000_000]
SEED = 42


def reference():
    """Rule-based hysteresis, no learning: the comparator."""
    from train import load_city
    P = P15(); m = HVACModel("4x4", P)
    to, ir = load_city("riyadh")
    H = 7 * int(round(24 / P.dt))
    st, _ = cooling_test_starts("riyadh", P.dt, H, 7)
    env = HVACEnv(m, to, ir, st, cost_model="S", horizon=H, P=P, rules=Rules(P, use_cc=False))
    return agg([run_policy(env, therm(3.15), start=int(s)) for s in st[:30]])


if __name__ == "__main__":
    t0 = time.time()
    rows = []
    r = reference()
    rows.append(dict(budget=0, controller="HYST (rule layer, no learning)",
                     **{k: round(v, 4) for k, v in r.items()}))
    print(f"  reference HYST: J={r['J_per_zone_day']:.4f} f_s={r['f_s']:.2f} "
          f"v_c={r['v_c']:.2f}", flush=True)
    write("budget.csv", rows)

    P = P15()
    # the manuscript's rule set exactly: R1+R2 hard, R3 soft bias, no CC hold
    rules = Rules(P, use_hard=True, use_cc=False, use_r3=True)
    H = 7 * int(round(24 / P.dt))

    for B in BUDGETS:
        model, venv, m, to, ir, te, spd = train("riyadh", "4x4", "S", P, SEED, B, rules=rules)
        st, _ = cooling_test_starts("riyadh", P.dt, H, 7)
        a = agg(eval_policy(model, venv, m, to, ir, st, "S", H, P, rules, n=30))
        rows.append(dict(budget=B, controller="RBRL (R1+R2+R3)",
                         **{k: round(v, 4) for k, v in a.items()}))
        print(f"  budget {B:>9,}: J={a['J_per_zone_day']:.4f} f_s={a['f_s']:.2f} "
              f"v_c={a['v_c']:.2f}  [{time.time()-t0:.0f}s]", flush=True)
        write("budget.csv", rows)

    print(f"\nbudget sweep done in {time.time()-t0:.0f}s", flush=True)
