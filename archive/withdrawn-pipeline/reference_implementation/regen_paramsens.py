"""Regenerate tab:paramsens (DP optimality bound vs construction) using the
original per-exposure-class DP on the real EPW weather. Riyadh 4x4, Model S.
"""
import numpy as np
import hvac_env as H
from hvac_env import HVACEnv, P, hard_rules, policy_therm, run_episode
from bc_pretrain import solve_zone_dp

EPW = "weather/riyadh.epw"
CITY, CFG, MODEL = "riyadh", "4x4", "S"


def dp_saving(c_th, lam_win, lam_ext, n_weeks=6):
    # override construction parameters
    P.c_th, P.lam_win, P.lam_ext = c_th, lam_win, lam_ext
    env = HVACEnv(CITY, CFG, MODEL, epw=EPW)
    starts = env._starts(train=False)
    # summer held-out weeks
    starts = [d for d in starts if 150 <= d <= 260][:n_weeks]

    def dp_policy_factory(day):
        pols = {}
        for z in range(env.n):
            key = env.ext[z]
            if key not in pols:
                pols[key] = solve_zone_dp(env, z, int(day), 168)

        def pol(e):
            u = np.zeros(e.n, dtype=int)
            for z in range(e.n):
                POL, grid = pols[e.ext[z]]
                i = int(np.clip(round((e.T[z] - grid[0]) / (grid[1] - grid[0])),
                                0, len(grid) - 1))
                u[z] = POL[min(e.k, POL.shape[0] - 1), i, e.prev[z]]
            return hard_rules(u, e.T)
        return pol

    Jt, Jd = [], []
    for day in starts:
        Jt.append(run_episode(env, policy_therm, start_day=int(day))["J"])
        Jd.append(run_episode(env, dp_policy_factory(day), start_day=int(day))["J"])
    Jt, Jd = np.mean(Jt), np.mean(Jd)
    return 100.0 * (Jt - Jd) / Jt


ROWS = [
    ("Light construction",        4000, 6.0, 25.0),
    ("Medium",                    6000, 6.0, 25.0),
    ("Baseline (heavy block)",    6700, 6.0, 25.0),
    ("Very heavy",               12000, 6.0, 25.0),
    ("Single glazing (non-SBC)",  6700, 12.5, 25.0),
    ("High-performance envelope", 6700, 4.2, 14.0),
]

if __name__ == "__main__":
    print(f"{'Case':28} {'Cth':>6} {'lwin':>5} {'lext':>5} {'Bound':>7}")
    for name, cth, lw, le in ROWS:
        b = dp_saving(cth, lw, le)
        print(f"{name:28} {cth:>6} {lw:>5} {le:>5} {b:>6.1f}%")
