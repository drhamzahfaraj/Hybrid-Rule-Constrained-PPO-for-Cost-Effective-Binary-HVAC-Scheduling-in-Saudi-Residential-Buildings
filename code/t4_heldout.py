#!/usr/bin/env python3
"""Tariff sweep on the HELD-OUT protocol, to put a data file behind every row of
tab:sensitivity(a). The in-force and 2027 rows exist in T1; the pre-2018 row was
computed inline and had no CSV. All three are regenerated here under one
protocol so the table, the figure and the data agree.

Protocol, identical to T1: the rule is tuned on TUNE_W and evaluated on EVAL_W,
every arm comfort-matched to THERM's mean occupied temperature, paired per
window.
"""
from __future__ import annotations
import sys, csv
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import final_tables as F

SCHEDULES = [("historical", 0.05), ("inforce", 0.18), ("y2027", 0.21)]
CITY = "riyadh"
rows = []

for tag, price in SCHEDULES:
    th = {w: F.therm_run(CITY, w, price) for w in F.WINDOWS}
    Jb = np.array([th[w]["J"] for w in F.EVAL_W])

    # Switching share of the baseline's cost: c_sw * f_s / J for THERM, formed
    # as the ratio of the reported means, which is how tab:sensitivity defines
    # it and what its f_s and J columns support.
    fs_m = float(np.mean([th[w]["f_s"] for w in F.EVAL_W]))
    sw_share = F.C_SW * fs_m / float(Jb.mean())

    # tune the rule on the tuning windows against THERM's own comfort there
    best = F.tune_rule(CITY, price, F.TUNE_W, lambda w: th[w]["T_mean_occ"])
    _, on_, off_ = best
    ru = [F.rule_run(CITY, w, price, on_, off_) for w in F.EVAL_W]
    assert max(r["deg_h_occ"] for r in ru) <= 1e-9, "tuned rule leaked comfort"
    Jr = np.array([r["J"] for r in ru])
    sr = 100.0 * (Jb - Jr) / Jb

    # clairvoyant optimum, comfort-matched per window
    Jd, nd = [], 0
    for w in F.EVAL_W:
        got = F.dp_isocomfort(CITY, w, price, th[w]["T_mean_occ"])
        if got is None:
            continue
        Jd.append(got[0]["J"]); nd += 1
    Jd = np.array(Jd)
    sd = 100.0 * (Jb[:nd] - Jd) / Jb[:nd]

    rows.append(dict(
        schedule=tag, price=price,
        sw_share_pct=round(100.0 * sw_share, 1),
        therm_J=round(float(Jb.mean()), 4),
        on_at=round(float(on_), 2), off_at=round(float(off_), 2),
        tuned_sav=round(float(sr.mean()), 1), tuned_sd=round(float(sr.std(ddof=1)), 1),
        opt_sav=round(float(sd.mean()), 1), opt_sd=round(float(sd.std(ddof=1)), 1),
        n_eval=len(F.EVAL_W), n_dp=nd))
    r = rows[-1]
    print(f"{tag:11s} p={price:.2f}  sw={r['sw_share_pct']:.1f}%  "
          f"rule {on_:.2f}/{off_:.2f}  "
          f"TUNED {r['tuned_sav']:+.1f}+/-{r['tuned_sd']:.1f}  "
          f"OPT {r['opt_sav']:+.1f}+/-{r['opt_sd']:.1f}  (n_dp={nd})", flush=True)

with open("/home/claude/rbrl/results/T4_tariff_heldout.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("-> results/T4_tariff_heldout.csv")
