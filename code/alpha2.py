#!/usr/bin/env python3
"""Comfort-weight sweep, repeated now that the optimiser is healthy.

The first alpha sweep (alpha.py) was run while the forward-hook defect was
active: clip_fraction was 0.998 and approx_kl ~7, so ~0.2% of each gradient
survived and the run measured nothing. Its conclusion ("alpha is not the cause")
is therefore void and this re-runs it on a sound optimiser.

Why alpha should matter: measured per-step magnitudes in this harness are
  comfort penalty  alpha * sum(dev^2)  ~ 77.7   at alpha = 50
  switching cost   c_sw * new_on       ~  0.117
a ~670:1 imbalance. With a healthy optimiser PPO will optimise the dominant
term, which is comfort -- consistent with the observed v_c improving to 2.27
(random 3.03) while J stayed at random level. Balancing the terms needs
alpha of order 0.1-0.5.

Benchmarks: random J=2.2612 f_s=14.16 v_c=3.03; rule J=0.3932 f_s=1.84 v_c=0.82.
"""
import sys, os, time
sys.path.insert(0, "/home/claude/rbrl")
from env import Rules
from train import train, eval_policy, agg
from run_all import cooling_test_starts, write, P15

STEPS = int(os.environ.get("PPO_STEPS", "200000"))
ALPHAS = [50.0, 5.0, 0.5, 0.1]

if __name__ == "__main__":
    t0 = time.time(); rows = []
    P = P15(); rules = Rules(P, use_hard=True, use_cc=False, use_r3=True)
    H = 7 * int(round(24 / P.dt))
    st, _ = cooling_test_starts("riyadh", P.dt, H, 7)
    for a in ALPHAS:
        model, venv, m, to, ir, te, spd = train(
            "riyadh", "4x4", "S", P, 42, STEPS, rules=rules, alpha=a)
        o = agg(eval_policy(model, venv, m, to, ir, st, "S", H, P, rules, n=30))
        rows.append(dict(alpha=a, steps=STEPS, **{k: round(v, 4) for k, v in o.items()}))
        print(f"  alpha={a:>5}: J={o['J_per_zone_day']:.4f} f_s={o['f_s']:.2f} "
              f"v_c={o['v_c']:.2f}  [{time.time()-t0:.0f}s]", flush=True)
        write("alpha2.csv", rows)
    print(f"\nalpha2 done in {time.time()-t0:.0f}s", flush=True)
