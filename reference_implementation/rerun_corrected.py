"""rerun_corrected.py -- regenerate the paper's numbers at CORRECTED parameters.

Corrections applied (see the revised manuscript, Table 2 and Remark 1):
    C_th   = 6,700 kJ/K   effective capacity (air + furnishings + inner fabric)
    dt     = 0.25 h       15-minute scheduling interval (672 steps / week)
    eps_g  = 0.19 C       guard band sized to the per-step drift
    c_sw   = 0.15 SAR     unchanged
Baselines are scored WITHOUT the RBRL rule layer (`baseline=True`), so the
thermostat is evaluated on its own logic and does not inherit R3 pre-cooling.

Stage 1 (fast, no training): thermostat baselines + DP optimality ceiling.
Stage 2 (needs training):    load trained agents and score them.

    py rerun_corrected.py --stage 1
    py rerun_corrected.py --stage 2 --checkpoints checkpoints
"""
import argparse
import numpy as np

from hvac_env import (HVACEnv, P, CONFIGS, policy_therm, run_episode,
                      cop, q_capacity, price)

CITIES = ["riyadh", "jeddah"]


def apply_corrections():
    P.c_th = 6700.0
    P.dt = 0.25
    P.eps_g = 0.19
    P.c_sw = 0.15
    print(f"corrected: C_th={P.c_th:.0f} kJ/K, dt={P.dt} h, eps_g={P.eps_g} C, "
          f"tau={P.c_th*1000/(P.lam_ext+P.lam_win)/3600:.0f} h")


def summer_starts(env, n=30):
    return [d for d in env._starts(train=False) if 150 <= d <= 260][:n]


def therm_row(city, cfg, model, n=30):
    env = HVACEnv(city=city, cfg=cfg, cost_model=model)
    rows = [run_episode(env, policy_therm, start_day=int(d), baseline=True)
            for d in summer_starts(env, n)]
    m = lambda k: float(np.mean([r[k] for r in rows]))
    s = lambda k: float(np.std([r[k] for r in rows]))
    return dict(J=m("J"), Jsd=s("J"), E=m("E"), fs=m("fs"), vc=m("vc"))


# ---------------------------------------------------------------- DP ceiling
def dp_zone_cost(env, zone, start_day, hours, e_ref, grid_step=0.05):
    """Exact single-zone DP cost (SAR/day) for the given exposure class."""
    lam = (P.lam_ext + P.lam_win) * env.ext[zone]
    solar = P.shgc * P.a_gl * env.ext[zone]
    C = P.c_th * 1000.0
    t_out, ghi = env.t_out, env.ghi
    grid = np.arange(P.t_min, P.t_max + 1e-9, grid_step)
    nT, n = len(grid), int(hours / P.dt)
    INF = 1e15

    def nxt(T, u, h):
        qc = q_capacity(P.q_cool, t_out[h])
        return T + P.dt*3600.0/C*(-qc*1000.0*u - lam*(T-t_out[h]) + solar*ghi[h])

    V = np.zeros((nT, 2))
    POL = np.zeros((n, nT, 2), dtype=np.int8)
    for k in range(n-1, -1, -1):
        h = int(start_day*24 + k*P.dt) % 8760
        el = q_capacity(P.q_cool, t_out[h])/cop(t_out[h]) + P.fan_w/1000.0
        p = price(env.model, e_ref)
        Vn = np.full((nT, 2), INF)
        for pu in (0, 1):
            best = np.full(nT, INF); besta = np.zeros(nT, dtype=np.int8)
            for u in (0, 1):
                Tn = np.array([nxt(T, u, h) for T in grid])
                bad = (Tn < grid[0]-1e-9) | (Tn > grid[-1]+1e-9)
                j = np.clip(np.round((Tn-grid[0])/grid_step).astype(int), 0, nT-1)
                c = p*el*u*P.dt + (P.c_sw if (u == 1 and pu == 0) else 0.0)
                v = np.where(bad, INF, c + V[j, u])
                take = v < best
                best = np.where(take, v, best); besta = np.where(take, u, besta)
            Vn[:, pu] = best; POL[k, :, pu] = besta
        V = Vn

    T, pu, cost = 24.0, 0, 0.0
    for k in range(n):
        h = int(start_day*24 + k*P.dt) % 8760
        i = int(np.clip(round((T-grid[0])/grid_step), 0, nT-1))
        u = int(POL[k, i, pu])
        el = q_capacity(P.q_cool, t_out[h])/cop(t_out[h]) + P.fan_w/1000.0
        cost += price(env.model, e_ref)*el*u*P.dt + (P.c_sw if (u == 1 and pu == 0) else 0)
        T = nxt(T, u, h); pu = u
    return cost / (n*P.dt/24.0)


def therm_zone_cost(env, zone, start_day, hours, e_ref):
    """Thermostat cost for the SAME isolated zone -- comparable with the DP."""
    lam = (P.lam_ext + P.lam_win) * env.ext[zone]
    solar = P.shgc * P.a_gl * env.ext[zone]
    C = P.c_th * 1000.0
    t_out, ghi = env.t_out, env.ghi
    T, pu, cost = 24.0, 0, 0.0
    n = int(hours / P.dt)
    for k in range(n):
        h = int(start_day*24 + k*P.dt) % 8760
        u = pu
        if T >= P.t_max - 0.5: u = 1
        elif T <= P.t_min + 0.5: u = 0
        el = q_capacity(P.q_cool, t_out[h])/cop(t_out[h]) + P.fan_w/1000.0
        cost += price(env.model, e_ref)*el*u*P.dt + (P.c_sw if (u == 1 and pu == 0) else 0)
        qc = q_capacity(P.q_cool, t_out[h])
        T = T + P.dt*3600.0/C*(-qc*1000.0*u - lam*(T-t_out[h]) + solar*ghi[h])
        pu = u
    return cost / (n*P.dt/24.0)


def dp_ceiling(city, model="S", n_weeks=6):
    env = HVACEnv(city=city, cfg="4x4", cost_model=model)
    starts = summer_starts(env, n_weeks)
    jt = [therm_zone_cost(env, 0, int(d), 168, P.e_base) for d in starts]
    jd = [dp_zone_cost(env, 0, int(d), 168, P.e_base) for d in starts]
    Jt, Jd = float(np.mean(jt)), float(np.mean(jd))
    return Jt, Jd, 100.0*(Jt-Jd)/Jt


def stage1():
    print("\n== THERMOSTAT baselines (corrected, baseline=True) ==")
    print(f"{'city':8}{'cfg':6}{'J':>9}{'E':>8}{'sw/day':>9}{'vc %':>8}")
    for city in CITIES:
        for cfg in CONFIGS:
            r = therm_row(city, cfg, "S")
            print(f"{city:8}{cfg:6}{r['J']:>9.3f}{r['E']:>8.2f}"
                  f"{r['fs']:>9.2f}{r['vc']:>8.2f}")

    print("\n== DP optimality ceiling (single exterior zone, Model S) ==")
    print(f"{'city':8}{'THERM':>9}{'DP':>9}{'ceiling':>10}")
    for city in CITIES:
        Jt, Jd, c = dp_ceiling(city)
        print(f"{city:8}{Jt:>9.3f}{Jd:>9.3f}{c:>9.1f}%")


def stage2(ckpt_dir):
    from stable_baselines3 import PPO
    import os
    print("\n== RBRL vs THERM (corrected) ==")
    print(f"{'city':8}{'cfg':6}{'model':6}{'THERM':>9}{'RBRL':>9}"
          f"{'saving':>9}{'vc %':>8}{'sw/day':>9}")
    for city in CITIES:
        for cfg in CONFIGS:
            for model in ("S",):
                tag = f"{city}_{cfg}_{model}_seed42"
                path = os.path.join(ckpt_dir, tag + ".zip")
                if not os.path.exists(path):
                    print(f"{city:8}{cfg:6}{model:6}  (no checkpoint {tag})")
                    continue
                agent = PPO.load(path)
                env = HVACEnv(city=city, cfg=cfg, cost_model=model)

                def pol(e):
                    a, _ = agent.predict(e._obs(), deterministic=True)
                    return np.asarray(a, dtype=int)

                starts = summer_starts(env, 30)
                b = therm_row(city, cfg, model)
                rows = [run_episode(env, pol, start_day=int(d)) for d in starts]
                m = lambda k: float(np.mean([r[k] for r in rows]))
                sav = 100.0*(b["J"] - m("J"))/b["J"]
                print(f"{city:8}{cfg:6}{model:6}{b['J']:>9.3f}{m('J'):>9.3f}"
                      f"{sav:>8.1f}%{m('vc'):>8.2f}{m('fs'):>9.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=1, choices=[1, 2])
    ap.add_argument("--checkpoints", default="checkpoints")
    a = ap.parse_args()
    apply_corrections()
    if a.stage == 1:
        stage1()
    else:
        stage2(a.checkpoints)
