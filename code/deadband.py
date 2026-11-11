#!/usr/bin/env python3
"""Sensitivity of the reported saving to the BASELINE's deadband, at fixed band.

The manuscript sweeps the comfort band, the capacity, the actuation interval,
the tariff and the switching cost. It does not sweep delta_db, the one
comparator parameter that creates the saving: THERM's deadband is defined
relative to the band (on at T_max-0.5, off at T_min+0.5), so halving the band
halved the deadband and tripled the baseline's cycling. A real thermostat's
hysteresis is a fixed hardware property, independent of the comfort band.

This script holds the band at [22,24] and sweeps a THERM centred at 23 C with
deadband d, re-tuning the rule against that baseline's own mean occupied
temperature at each d, exactly as the protocol does at d = 1.

It also evaluates the corrected admissibility bound. The manuscript's
eq:deadband_condition gives

    Q dt / C_th  <=  delta_db  <=  T_max - T_min,

but the upper bound is wrong: the switch points plus their own per-interval
excursions must fit inside the band. Switching on at 23 + d/2 the zone still
warms by the hot-guard excursion before the plant bites, and switching off at
23 - d/2 it still cools by Q dt / C_th. So

    delta_db  <=  (T_max - T_min) - Q dt/C_th - eps_hot,

and for a deadband centred on the band, d <= 2 * min(half-band - excursion).
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, csv
sys.path.insert(0, _ROOT + "")
import numpy as np
import headroom as H
import setback as S
import final_tables as F

LO, HI = 22.0, 24.0
CENTRE = 0.5 * (LO + HI)
C_TH = 4800.0
EPS_HOT = 0.20
PRICE = 0.18
CITY = "riyadh"
DEADBANDS = (0.50, 0.75, 1.00, 1.25, 1.50)


def therm_d(city, w, price_v, d):
    """A thermostat with a FIXED deadband d, centred on the band."""
    return F.rule_run(city, w, price_v, CENTRE + 0.5 * d, CENTRE - 0.5 * d)


def bounds():
    cool = H.Q_HVAC * H.DT * 3600.0 / (C_TH * 1e3)       # per-interval cooling
    lower = cool
    upper_band = HI - LO                                  # the paper's bound
    upper_corrected = (HI - LO) - cool - EPS_HOT          # must fit inside
    upper_centred = 2.0 * min(0.5 * (HI - LO) - cool,
                              0.5 * (HI - LO) - EPS_HOT)
    return cool, lower, upper_band, upper_corrected, upper_centred


if __name__ == "__main__":
    cool, lo_b, up_paper, up_corr, up_centred = bounds()
    print(f"per-interval cooling excursion  Q dt/C_th = {cool:.3f} K")
    print(f"lower bound on delta_db                   = {lo_b:.3f} K")
    print(f"upper bound, as the manuscript states it  = {up_paper:.3f} K")
    print(f"upper bound, corrected (fit inside band)  = {up_corr:.3f} K")
    print(f"upper bound for a CENTRED deadband        = {up_centred:.3f} K\n")

    rows = []
    for d in DEADBANDS:
        th = {w: therm_d(CITY, w, PRICE, d) for w in F.WINDOWS}
        Jb = np.array([th[w]["J"] for w in F.EVAL_W])
        fs_b = float(np.mean([th[w]["f_s"] for w in F.EVAL_W]))
        dh_b = float(max(th[w]["deg_h_occ"] for w in F.EVAL_W))
        Tb = float(np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W]))

        # re-tune the rule against THIS baseline's own comfort, same protocol
        best = F.tune_rule(CITY, PRICE, F.TUNE_W, lambda w: th[w]["T_mean_occ"])
        if best is None:
            tn, tsd, on_, off_ = float("nan"), float("nan"), float("nan"), float("nan")
        else:
            _, on_, off_ = best
            ru = [F.rule_run(CITY, w, PRICE, on_, off_) for w in F.EVAL_W]
            Jr = np.array([r["J"] for r in ru])
            sv = 100.0 * (Jb - Jr) / Jb
            tn, tsd = float(sv.mean()), float(sv.std(ddof=1))

        # the guard hysteresis, i.e. what RBRL collapses to, at this baseline
        gh = [F.rule_run(CITY, w, PRICE, 23.737 - EPS_HOT, LO + 0.40)
              for w in F.EVAL_W]
        Jg = np.array([r["J"] for r in gh])
        gv = 100.0 * (Jb - Jg) / Jb

        adm = "yes" if (cool <= d <= up_centred + 1e-9) else "no"
        rows.append(dict(deadband=d, admissible=adm,
                         therm_J=round(float(Jb.mean()), 4),
                         therm_fs=round(fs_b, 3),
                         therm_deg_h=round(dh_b, 4),
                         therm_T_occ=round(Tb, 3),
                         tuned_on=round(on_, 2) if on_ == on_ else "",
                         tuned_off=round(off_, 2) if off_ == off_ else "",
                         tuned_sav=round(tn, 2) if tn == tn else "",
                         tuned_sd=round(tsd, 2) if tsd == tsd else "",
                         guard_sav=round(float(gv.mean()), 2)))
        r = rows[-1]
        print(f"d={d:.2f} K  adm={adm:3s}  THERM J={r['therm_J']:.4f} "
              f"f_s={r['therm_fs']:.2f} deg-h={r['therm_deg_h']:.3f}  "
              f"TUNED={r['tuned_sav']}+/-{r['tuned_sd']}%  "
              f"guard-hyst={r['guard_sav']:+.2f}%", flush=True)

    with open(_ROOT + "/results/T7_deadband.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print("\n-> results/T7_deadband.csv")
