#!/usr/bin/env python3
"""Grid convergence of the Lagrangian bound, and a conservative rounded value.

The defect
----------
`dp_meanconstrained.py` evaluates the inner minimisation on a 1601-point
temperature grid with interpolated continuation values. A discretised DP returns
a minimum that is too EXPENSIVE, so L*(lambda) comes out too high and the
resulting saving bound comes out too TIGHT -- the unsafe direction. At 1601
points the bound is reported as <= 18.83% in Jeddah while a primal schedule from
the same script attains 19.11%, i.e. the stated bound is violated by its own
solution.

Why this is cheap to fix
------------------------
Equation (dual_bound) holds for EVERY lambda, not only the maximiser. So the
lambda* found on the coarse grid can be re-evaluated at a finer resolution and
the result is still a valid bound -- no re-maximisation is needed. Only the
inner minimisation has to be refined, which is 7 window solves per city.

What is reported
----------------
L*(lambda*) at 1601, 3201 and 6401 points, the implied saving bound at each,
and a value rounded OUTWARD (upward, in saving terms) to the nearest 0.1 point
at the finest resolution, so that the number printed in the manuscript is
conservative with respect to the residual discretisation error.
"""
from __future__ import annotations
import sys, csv, time
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import final_tables as F
import dp_meanconstrained as M

GRIDS = (1601, 3201, 6401)
# lambda* from the coarse maximisation (results/T11_meanbound.csv)
LAMSTAR = {("riyadh", False): 2.0219, ("riyadh", True): 1.2799,
           ("jeddah", False): 2.1772, ("jeddah", True): 0.9129,
           ("taif", False): 1.4597, ("taif", True): 1.2936}


def bound_at(city, setback, lam, n_grid, price_v=M.PRICE):
    th = {w: F.therm_run(city, w, price_v) for w in F.EVAL_W}
    Jb = float(np.mean([th[w]["J"] for w in F.EVAL_W]))
    tgt = float(np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W]))
    rs = [M.dp_lagrangian(city, w, price_v, lam, setback, n_grid=n_grid)
          for w in F.EVAL_W]
    if any(r is None for r in rs):
        return None
    days = rs[0]["days"]
    L = float(np.mean([r["L"] for r in rs])) - (lam / days) * tgt
    return dict(L=L, Jb=Jb, sav=100.0 * (Jb - L) / Jb)


if __name__ == "__main__":
    t0 = time.time()
    rows = []
    for city in ("riyadh", "jeddah", "taif"):
        for setback, name in ((False, "OPT"),):
            lam = LAMSTAR[(city, setback)]
            print(f"\n=== {city} {name}  lambda*={lam:.4f} ===", flush=True)
            prev = None
            for g in GRIDS:
                r = bound_at(city, setback, lam, g)
                if r is None:
                    print(f"  n_grid={g:5d}  infeasible"); continue
                d = "" if prev is None else f"  (delta {r['sav']-prev:+.3f} pp)"
                print(f"  n_grid={g:5d}  cost >= {r['L']:.5f}  "
                      f"saving <= {r['sav']:.3f}%{d}", flush=True)
                prev = r["sav"]
                rows.append(dict(city=city, arm=name, lam=lam, n_grid=g,
                                 bound_J=round(r["L"], 5),
                                 bound_sav=round(r["sav"], 3)))
            # conservative published value: round the saving bound UP to 0.1 pp
            fin = [x for x in rows if x["city"] == city and x["arm"] == name]
            if fin:
                best = fin[-1]["bound_sav"]
                # add one more delta as a margin for the residual drift
                drift = (fin[-1]["bound_sav"] - fin[-2]["bound_sav"]) \
                    if len(fin) > 1 else 0.0
                safe = np.ceil((best + abs(drift)) * 10.0) / 10.0
                print(f"  --> publish  <= {safe:.1f}%   "
                      f"(finest {best:.3f} + drift margin {abs(drift):.3f})",
                      flush=True)
                rows[-1]["published"] = safe
    with open("/home/claude/rbrl/results/T17_bound_convergence.csv", "w",
              newline="") as f:
        fn = ["city", "arm", "lam", "n_grid", "bound_J", "bound_sav",
              "published"]
        w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(f"\n-> results/T17_bound_convergence.csv ({time.time()-t0:.0f} s)")
    print("Any lambda gives a valid bound, so re-evaluating lambda* on a finer "
          "grid is itself valid; the published value is rounded outward.")
