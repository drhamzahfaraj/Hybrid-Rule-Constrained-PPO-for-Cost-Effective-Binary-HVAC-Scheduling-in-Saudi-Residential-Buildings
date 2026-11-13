#!/usr/bin/env python3
"""Independent check of Corollary 1 against a constructive counterexample.

The corollary claims: under the hard rules, at a matched mean occupied
temperature, the rule-induced hysteresis attains cost no greater than ANY policy
differing from it on the free interval F.

The test: solve the clairvoyant DP RESTRICTED to the rule-admissible action set
(u forced to 1 at T >= cap - eps_hot, forced to 0 at T <= T_min + eps_cold, free
on F).  Such a DP policy differs from the guard hysteresis only on F, so the
corollary says it cannot be cheaper.  If it IS cheaper at a matched mean, the
corollary as stated is false.
"""
from __future__ import annotations
import sys
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import headroom as H
import setback as S
import final_tables as F

EPS_HOT, EPS_COLD = 0.20, 0.40
LO, HI = 22.0, 24.0


def dp_rule_constrained(city, start_day, price_v, cap, c_th=4800.0, faces=1,
                        n_grid=S.N_GRID):
    """Clairvoyant DP over the rule-admissible action set only."""
    q, cp = H.Q_HVAC, H.COP_RATED
    lam = H.lam_of(faces, city)
    t_out, irr, N = H.series(city, 168, start_day)
    decay = float(np.exp(-S.DT * 3600.0 * lam / (c_th * 1e3)))
    p_el = q / cp / 1000.0
    price = H.price_flat(N, price_v)
    Tg = np.linspace(S.G_LO, S.G_HI, n_grid)
    INF = np.inf
    T0 = 23.0

    # rule mask on the GRID: which actions the rule layer permits at each T
    force_on = Tg >= cap - EPS_HOT
    force_off = Tg <= LO + EPS_COLD
    allowed = np.ones((n_grid, 2), bool)
    allowed[force_on, 0] = False        # cannot be off in the hot guard
    allowed[force_off, 1] = False       # cannot be on in the cold guard

    V = np.repeat((price[-1] * (Tg - T0) * c_th * 1e3 / 3.6e6 / cp)[:, None],
                  2, axis=1)
    pol = np.zeros((N, n_grid, 2), np.int8)
    for k in range(N - 1, -1, -1):
        g = H.SHGC * H.A_GL * irr[k]
        run = price[k] * p_el * S.DT
        swc = H.C_SW + price[k] * H.E_START
        cand = np.full((n_grid, 2, 2), INF)
        for u in (0, 1):
            T_inf = t_out[k] + (g - q * u) / lam
            Tp = T_inf + (Tg - T_inf) * decay
            ok = (Tp >= LO - 1e-9) & (Tp <= HI + 1e-9)
            ok &= allowed[:, u]                      # <-- the rule layer
            Vn = np.interp(np.clip(Tp, S.G_LO, S.G_HI), Tg, V[:, u])
            nxt = np.where(ok, run * u + Vn, INF)
            for up in (0, 1):
                s = swc if (u == 1 and up == 0) else 0.0
                cand[:, up, u] = np.where(np.isfinite(nxt), s + nxt, INF)
        Vn2 = np.full((n_grid, 2), INF)
        for up in (0, 1):
            bu = np.argmin(np.nan_to_num(cand[:, up, :], nan=INF, posinf=1e300),
                           axis=1)
            pol[k, :, up] = bu.astype(np.int8)
            Vn2[:, up] = cand[np.arange(n_grid), up, bu]
        V = Vn2
    i0 = int(np.argmin(np.abs(Tg - T0)))
    if not np.isfinite(V[i0, 0]):
        return None

    def pol_fn(T, prev, k):
        return int(pol[k, int(np.argmin(np.abs(Tg - T))), prev])

    occ = np.ones(N, bool)
    lo_a, hi_a = S.bands(occ, LO, HI, 18.0, 30.0)
    return S.sim(pol_fn, city, faces, c_th, price, lo_a, hi_a, occ,
                 168, start_day, T0, c_sw=H.C_SW)


if __name__ == "__main__":
    for city, cap in (("riyadh", 23.737), ("jeddah", 23.737)):
        th = {w: F.therm_run(city, w, 0.18) for w in F.EVAL_W}
        Jb = np.array([th[w]["J"] for w in F.EVAL_W])
        Tb = float(np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W]))

        # (a) the guard hysteresis itself -- what the corollary says is optimal
        hy = [F.rule_run(city, w, 0.18, cap - EPS_HOT, LO + EPS_COLD)
              for w in F.EVAL_W]
        # (b) the clairvoyant optimum over the SAME admissible action set
        dp = [dp_rule_constrained(city, w, 0.18, cap) for w in F.EVAL_W]
        if any(d is None for d in dp):
            print(f"{city}: DP infeasible on some window"); continue

        def agg(rs):
            J = np.array([r["J"] for r in rs])
            return (float(J.mean()),
                    float(np.mean([r["f_s"] for r in rs])),
                    float(np.mean([r["T_mean_occ"] for r in rs])),
                    float(max(r["deg_h_occ"] for r in rs)),
                    float(np.mean(100.0 * (Jb - J) / Jb)))

        Jh, fh, Th, dh, sh = agg(hy)
        Jd, fd, Td, dd, sd = agg(dp)
        print(f"\n=== {city} (cap {cap}, THERM T_occ {Tb:.4f}) ===")
        print(f"  guard hysteresis : J={Jh:.4f}  f_s={fh:.3f}  "
              f"T_occ={Th:.4f} (dT {Th-Tb:+.4f})  deg-h={dh:.4g}  sav={sh:+.2f}%")
        print(f"  rule-constrained DP: J={Jd:.4f}  f_s={fd:.3f}  "
              f"T_occ={Td:.4f} (dT {Td-Tb:+.4f})  deg-h={dd:.4g}  sav={sd:+.2f}%")
        gap = Jh - Jd
        print(f"  --> DP is {gap:+.4f} SAR/day cheaper ({100*gap/Jh:+.2f}%), "
              f"f_s {fd-fh:+.3f}")
        if gap > 1e-4 and dd <= 1e-9:
            # EXPECTED on this instance, and not a refutation of the corollary
            # as it now stands. The corollary assumes a CONSTANT disturbance;
            # the simulation supplies diurnally varying weather, so its
            # hypothesis is not met here. The manuscript states this (Remark
            # on corollary scope) and reports the gap below as the measured
            # price of that gap, which is the whole point of running this.
            print("  hypothesis NOT satisfied under varying weather, as "
                  "expected: a policy differing only on F is cheaper at "
                  f"comparable comfort by {100*gap/Jh:.2f}%")
        else:
            print("  no gap resolvable on this instance")
