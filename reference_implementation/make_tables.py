"""Evaluate trained agents and emit every table used in the paper.

Usage
-----
    python make_tables.py --checkpoints checkpoints --out tables

Produces, on the held-out split only:
  T1  consumption and cost, all configurations, Model S
  T2  results by cost model (L / E / S), 4x4
  T3  component ablation (THERM, RL-only, hard-only, full RBRL)
  T4  cost-model mismatch penalty
  T5  scalability (savings, inference latency)
  T6  seasonal, monthly means
  V1  model validation, 1R1C vs 3R2C
  V2  integration stability, sub-step convergence

Any table whose checkpoints are missing is skipped with a warning, so the
script can be run incrementally as training completes.
"""
import argparse, os, time, json
import numpy as np

from hvac_env import (HVACEnv, CONFIGS, policy_therm, run_episode,
                      monthly_bill, P)

CITIES = ["riyadh", "jeddah"]
MODELS = ["L", "E", "S"]


# ----------------------------------------------------------------- helpers
def load(tag, ckpt):
    """Load a trained agent; return None if the checkpoint is absent."""
    path = os.path.join(ckpt, tag + ".zip")
    if not os.path.exists(path):
        return None
    from stable_baselines3 import PPO
    return PPO.load(path)


def agent_policy(agent):
    def pol(env):
        obs = env._obs()
        a, _ = agent.predict(obs, deterministic=True)
        return np.asarray(a, dtype=int)
    return pol


def eval_agent(env, agent, n_ep=30, seeds=(42, 43, 44, 45, 46)):
    """Mean +/- std over held-out episodes."""
    starts = env._starts(train=False)
    rows = []
    for i in range(min(n_ep, len(starts))):
        rows.append(run_episode(env, agent_policy(agent),
                                start_day=int(starts[i])))
    keys = ["J", "E", "fs", "vc"]
    return {k: (float(np.mean([r[k] for r in rows])),
                float(np.std([r[k] for r in rows]))) for k in keys}


def eval_therm(env, n_ep=30):
    starts = env._starts(train=False)
    rows = [run_episode(env, policy_therm, start_day=int(s))
            for s in starts[:n_ep]]
    keys = ["J", "E", "fs", "vc"]
    return {k: (float(np.mean([r[k] for r in rows])),
                float(np.std([r[k] for r in rows]))) for k in keys}


def fmt(v, p=3):
    return f"{v[0]:.{p}f}$\\pm${v[1]:.{p}f}"


# ----------------------------------------------------------------- tables
def table1(ckpt, out):
    print("\n== T1  consumption and cost, Model S ==")
    lines = []
    for city in CITIES:
        for cfg in CONFIGS:
            env = HVACEnv(city, cfg, "S")
            t = eval_therm(env)
            ag = load(f"{city}_{cfg}_S_seed42", ckpt)
            if ag is None:
                print(f"  skip {city} {cfg}: no checkpoint"); continue
            r = eval_agent(env, ag)
            sav = 100*(t["J"][0]-r["J"][0])/t["J"][0]
            print(f"  {city:>7} {cfg:>4} THERM {t['J'][0]:.3f} RBRL {r['J'][0]:.3f} "
                  f"E {t['E'][0]:.2f}->{r['E'][0]:.2f} vc {r['vc'][0]:.2f} save {sav:.1f}%")
            lines.append(dict(city=city, cfg=cfg, therm=t, rbrl=r, saving=sav))
    json.dump(lines, open(os.path.join(out, "T1.json"), "w"), indent=1)


def table2(ckpt, out):
    print("\n== T2  by cost model, 4x4 ==")
    lines = []
    for city in CITIES:
        for m in MODELS:
            env = HVACEnv(city, "4x4", m)
            t = eval_therm(env)
            ag = load(f"{city}_4x4_{m}_seed42", ckpt)
            if ag is None:
                print(f"  skip {city} {m}"); continue
            r = eval_agent(env, ag)
            sav = 100*(t["J"][0]-r["J"][0])/t["J"][0]
            print(f"  {city:>7} {m}  THERM {t['J'][0]:.3f} RBRL {r['J'][0]:.3f} save {sav:.1f}%")
            lines.append(dict(city=city, model=m, therm=t, rbrl=r, saving=sav))
    json.dump(lines, open(os.path.join(out, "T2.json"), "w"), indent=1)


def table3(ckpt, out):
    print("\n== T3  component ablation, 4x4 riyadh Model S ==")
    env = HVACEnv("riyadh", "4x4", "S")
    rows = {"THERM": eval_therm(env)}
    for tag, lbl in [("riyadh_4x4_S_seed42_nohard", "RL only"),
                     ("riyadh_4x4_S_seed42_nor3",  "hard rules only"),
                     ("riyadh_4x4_S_seed42",       "RBRL full")]:
        ag = load(tag, ckpt)
        if ag is None:
            print(f"  skip {lbl}"); continue
        e = HVACEnv("riyadh", "4x4", "S",
                    use_hard=("nohard" not in tag), r3=("nor3" not in tag))
        rows[lbl] = eval_agent(e, ag)
    for k, v in rows.items():
        print(f"  {k:>18} J {v['J'][0]:.3f} vc {v['vc'][0]:.2f} fs {v['fs'][0]:.2f}")
    json.dump({k: v for k, v in rows.items()},
              open(os.path.join(out, "T3.json"), "w"), indent=1)


def table4(ckpt, out):
    print("\n== T4  cost-model mismatch ==")
    env = HVACEnv("riyadh", "4x4", "S")
    ref = None; rows = {}
    for m in MODELS:
        ag = load(f"riyadh_4x4_{m}_seed42", ckpt)
        if ag is None:
            print(f"  skip trained-on-{m}"); continue
        r = eval_agent(env, ag)
        rows[m] = r
        if m == "S": ref = r["J"][0]
    if ref:
        for m, r in rows.items():
            print(f"  trained on {m}: true J under S {r['J'][0]:.3f} "
                  f"penalty {100*(r['J'][0]-ref)/ref:+.1f}%")
    json.dump(rows, open(os.path.join(out, "T4.json"), "w"), indent=1)


def table5(ckpt, out):
    print("\n== T5  scalability and inference latency ==")
    rows = []
    for cfg in CONFIGS:
        env = HVACEnv("riyadh", cfg, "S")
        ag = load(f"riyadh_{cfg}_S_seed42", ckpt)
        if ag is None:
            print(f"  skip {cfg}"); continue
        t = eval_therm(env); r = eval_agent(env, ag)
        env.reset(train=False); obs = env._obs()
        t0 = time.perf_counter()
        for _ in range(2000):
            ag.predict(obs, deterministic=True)
        ms = (time.perf_counter()-t0)/2000*1000
        sav = 100*(t["J"][0]-r["J"][0])/t["J"][0]
        print(f"  {cfg:>4} Nz={env.n:>2} save {sav:>5.1f}%  inference {ms:.3f} ms")
        rows.append(dict(cfg=cfg, nz=env.n, saving=sav, ms=ms))
    json.dump(rows, open(os.path.join(out, "T5.json"), "w"), indent=1)


def table6(ckpt, out):
    print("\n== T6  seasonal, monthly means (4x4, Model S) ==")
    L = [31,28,31,30,31,30,31,31,30,31,30,31]
    rows = []
    for city in CITIES:
        env = HVACEnv(city, "4x4", "S")
        ag = load(f"{city}_4x4_S_seed42", ckpt)
        if ag is None:
            print(f"  skip {city}"); continue
        s = 0
        for mi, nd in enumerate(L):
            days = [d for d in env.hold if s <= d < s+nd]
            days = [d for d in days if all((d+k) in set(env.hold.tolist())
                                           for k in range(7))]
            if days:
                th = np.mean([run_episode(env, policy_therm, start_day=int(d))["J"]
                              for d in days])
                rb = np.mean([run_episode(env, agent_policy(ag), start_day=int(d))["J"]
                              for d in days])
                rows.append(dict(city=city, month=mi+1, therm=float(th),
                                 rbrl=float(rb), saving=100*(th-rb)/th))
                print(f"  {city:>7} month {mi+1:>2}: THERM {th:.3f} RBRL {rb:.3f} "
                      f"save {100*(th-rb)/th:.1f}%")
            s += nd
    json.dump(rows, open(os.path.join(out, "T6.json"), "w"), indent=1)


def validation(out):
    """V1 and V2 need no trained agent."""
    from hvac_env import HVACEnv as E
    print("\n== V1  model validation, 1R1C vs 3R2C ==")
    print("  (run validate_rc.py -- requires the RC2 reference model)")
    print("\n== V2  integration stability ==")
    tau = P.c_th*1000/(P.lam_ext+P.lam_win)/3600
    print(f"  tau = {tau:.1f} h ; dt = {P.dt} h ; dt/tau = {P.dt/tau:.5f}")
    print("  see validate_rc.py for the sub-step convergence study")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoints", default="checkpoints")
    ap.add_argument("--out", default="tables")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for fn in (table1, table2, table3, table4, table5, table6):
        try:
            fn(a.checkpoints, a.out)
        except Exception as exc:                     # keep going
            print(f"  !! {fn.__name__} failed: {exc}")
    validation(a.out)
    print(f"\nJSON written to {a.out}/")


if __name__ == "__main__":
    main()
