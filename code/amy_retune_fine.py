#!/usr/bin/env python3
"""Re-tune on a 0.02 K grid for AMY city-years where the 0.05 K tune collapsed.

In several actual years the paper's per-window +/-0.03 K admission rule, searched
on the headline 0.05 K grid, admits no candidate or only near-baseline ones
(results/T23_amy_spread.csv, kind RETUNED). This repeats the search on a 0.02 K
grid for those city-years, to establish whether the collapse is grid
quantisation or a property of the admission protocol. Finding: in the mildest
Riyadh year (2013) no rule is admissible even at 0.02 K, so what fails to
transfer across weather years is the admission protocol, not the rule family
(manuscript §Robustness, "Weather year").
"""
from __future__ import annotations
import sys, csv, os
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
import numpy as np
import headroom as H
import final_tables as F
from amy_spread import amy_series_fn, _epw_series

TODO = [("riyadh", 2013), ("riyadh", 2018), ("jeddah", 2011), ("jeddah", 2023),
        ("taif", 2013), ("taif", 2012), ("taif", 2021)]

if __name__ == "__main__":
    out = []
    for city, year in TODO:
        H.series = amy_series_fn(city, year)
        th = {w: F.therm_run(city, w, 0.18) for w in F.EVAL_W}
        Jb = np.array([th[w]["J"] for w in F.EVAL_W])
        got = F.tune_rule(city, 0.18, F.TUNE_W,
                          lambda w: F.therm_run(city, w, 0.18)["T_mean_occ"], step=0.02)
        if got is None:
            print(f"{city} {year}: no admissible rule at 0.02 K", flush=True)
            out.append(dict(city=city, year=year, kind="RETUNED_fine", ok=False))
            continue
        _, on_, off_ = got
        rs = [F.rule_run(city, w, 0.18, on_, off_) for w in F.EVAL_W]
        J = np.array([r["J"] for r in rs]); sav = 100 * (Jb - J) / Jb
        dT = float(np.mean([r["T_mean_occ"] for r in rs])
                   - np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W]))
        dh = float(max(r["deg_h_occ"] for r in rs))
        print(f"{city} {year}: rule {on_:.2f}/{off_:.2f} sav {sav.mean():+.2f}"
              f"+/-{sav.std(ddof=1):.2f}% dT {dT:+.4f} deg-h {dh:.3f}", flush=True)
        out.append(dict(city=city, year=year, kind="RETUNED_fine", ok=True,
                        on=round(on_, 2), off=round(off_, 2), sav=round(float(sav.mean()), 2),
                        sav_sd=round(float(sav.std(ddof=1)), 2), dT=round(dT, 4),
                        deg_h=round(dh, 4)))
    H.series = _epw_series
    keys = sorted({k for r in out for k in r})
    with open(f"{_ROOT}/results/T23_amy_retune_fine.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
    print("-> results/T23_amy_retune_fine.csv")
