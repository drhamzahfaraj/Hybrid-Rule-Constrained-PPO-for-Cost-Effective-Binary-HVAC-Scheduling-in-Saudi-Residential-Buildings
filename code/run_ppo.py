#!/usr/bin/env python3
"""PPO training programme: RBRL vs the thermostat family, 5 seeds."""
from __future__ import annotations
import sys, os, csv, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hvac import *
from env import HVACEnv, Rules, run_policy, therm
from train import load_city, split_indices, window_starts, train, eval_policy, agg
from run_all import cooling_test_starts, write, P15

STEPS = int(os.environ.get("PPO_STEPS", "150000"))
SEEDS = [int(x) for x in os.environ.get("SEEDS", "42,43,44,45,46").split(",")]


def one(city, topo, cm, seed, steps, variant="full"):
    P = P15()
    rules = Rules(P, use_hard=(variant != "norules"),
                  use_cc=(variant not in ("norules", "nocc")),
                  use_r3=(variant not in ("norules", "nor3")))
    model, venv, m, to, ir, te, spd = train(city, topo, cm, P, seed, steps, rules=rules)
    H = 7 * spd
    st, _ = cooling_test_starts(city, P.dt, H, 7)
    outs = eval_policy(model, venv, m, to, ir, st, cm, H, P, rules, n=30)
    return agg(outs), len(st)


if __name__ == "__main__":
    job = sys.argv[1] if len(sys.argv) > 1 else "main"
    rows = []
    t0 = time.time()

    if job == "main":
        for city in ("riyadh", "jeddah"):
            for cm in ("S", "L"):
                for seed in SEEDS:
                    a, nst = one(city, "4x4", cm, seed, STEPS)
                    rows.append(dict(city=city, topo="4x4", cost_model=cm,
                                     controller="RBRL", seed=seed, n_test=nst,
                                     **{k: round(v, 4) for k, v in a.items()}))
                    print(f"  {city} 4x4 {cm} seed{seed}: J={a['J_per_zone_day']:.4f} "
                          f"f_s={a['f_s']:.2f} v_c={a['v_c']:.2f} "
                          f"peak={a['peak_kW']:.2f}  [{time.time()-t0:.0f}s]", flush=True)
                    write("ppo_main.csv", rows)

    elif job == "scale":
        for city in ("riyadh", "jeddah"):
            for topo in ("1x1", "1x4", "2x2", "3x3"):
                for seed in SEEDS[:3]:
                    a, nst = one(city, topo, "S", seed, STEPS)
                    rows.append(dict(city=city, topo=topo, cost_model="S",
                                     controller="RBRL", seed=seed, n_test=nst,
                                     **{k: round(v, 4) for k, v in a.items()}))
                    print(f"  {city} {topo} seed{seed}: J={a['J_per_zone_day']:.4f} "
                          f"f_s={a['f_s']:.2f}  [{time.time()-t0:.0f}s]", flush=True)
                    write("ppo_scale.csv", rows)

    elif job == "ablate":
        for variant in ("full", "nocc", "nor3", "norules"):
            for seed in SEEDS[:3]:
                a, nst = one("riyadh", "4x4", "S", seed, STEPS, variant)
                rows.append(dict(city="riyadh", topo="4x4", cost_model="S",
                                 variant=variant, seed=seed,
                                 **{k: round(v, 4) for k, v in a.items()}))
                print(f"  {variant} seed{seed}: J={a['J_per_zone_day']:.4f} "
                      f"f_s={a['f_s']:.2f} v_c={a['v_c']:.2f}  "
                      f"[{time.time()-t0:.0f}s]", flush=True)
                write("ppo_ablate.csv", rows)

    print(f"\n{job} done in {time.time()-t0:.0f}s", flush=True)
