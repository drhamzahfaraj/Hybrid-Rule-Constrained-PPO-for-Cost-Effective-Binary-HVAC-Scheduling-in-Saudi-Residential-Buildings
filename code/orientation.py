#!/usr/bin/env python3
"""Orientation sensitivity of the reported saving.

The headline zone faces south, which at these latitudes is the MILDEST of the
four cardinal choices in summer: the midday sun stands high, so a south
vertical window receives less irradiance than an east or west one that faces
the low morning or afternoon sun. The reported saving is therefore a best case
in this one respect, and the direction was until now asserted rather than
measured.

This study re-runs the paper's own protocol -- THERM baseline, rule tuned on
the tuning windows under the per-window comfort-match admission rule,
evaluated on the disjoint held-out windows -- with the glazed face turned to
each cardinal orientation. Only the solar transposition changes; envelope,
infiltration, plant, tariff and windows are identical. The expected mechanism:
a higher solar load lengthens on-phases, cuts the start count, and so shrinks
the switching share that the saving is made of.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, csv, os
sys.path.insert(0, _ROOT + "")
import numpy as np

import headroom as H
import final_tables as F
from hvac import read_epw, vertical_irradiance

_epw_series = H.series
AZ = {"north": 0.0, "east": 90.0, "south": 180.0, "west": 270.0}


def series_at(city, azimuth):
    tdb, dni, dhi = read_epw(f"{_ROOT}/{city}.epw")
    irr = vertical_irradiance(dni, dhi, H.CITIES[city], azimuth_deg=azimuth)
    tdb = np.asarray(tdb, float)

    def series(city_, hours, start_day):
        spd = int(round(1.0 / H.DT)); N = int(round(hours / H.DT))
        h0 = start_day * 24
        return (np.repeat(tdb[h0:h0 + hours], spd)[:N],
                np.repeat(irr[h0:h0 + hours], spd)[:N], N)
    return series


if __name__ == "__main__":
    city = "riyadh"
    rows = []
    for name, az in AZ.items():
        H.series = series_at(city, az)
        th = {w: F.therm_run(city, w, 0.18) for w in F.EVAL_W}
        Jb = np.array([th[w]["J"] for w in F.EVAL_W])
        got = F.tune_rule(city, 0.18, F.TUNE_W,
                          lambda w: F.therm_run(city, w, 0.18)["T_mean_occ"])
        if got is None:
            print(f"{name:6s}: no admissible rule"); continue
        _, on_, off_ = got
        rs = [F.rule_run(city, w, 0.18, on_, off_) for w in F.EVAL_W]
        J = np.array([r["J"] for r in rs])
        fs_t = float(np.mean([th[w]["f_s"] for w in F.EVAL_W]))
        fs_r = float(np.mean([r["f_s"] for r in rs]))
        sav = 100.0 * (Jb - J) / Jb
        E_t = float(np.mean([th[w]["E"] for w in F.EVAL_W]))
        row = dict(orientation=name, azimuth=az,
                   therm_J=round(float(Jb.mean()), 4),
                   therm_E=round(E_t, 3),
                   therm_fs=round(fs_t, 3), rule_fs=round(fs_r, 3),
                   on=round(on_, 2), off=round(off_, 2),
                   sav=round(float(sav.mean()), 2),
                   sav_sd=round(float(sav.std(ddof=1)), 2),
                   dT=round(float(np.mean([r["T_mean_occ"] for r in rs])
                            - np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W])), 4),
                   max_deg_h=round(max(r["deg_h_occ"] for r in rs), 5))
        rows.append(row)
        print(f"{name:6s} az={az:5.0f}  THERM J={row['therm_J']:.4f} "
              f"E={row['therm_E']:.3f} f_s={fs_t:.2f}  rule {on_:.2f}/{off_:.2f}"
              f"  sav {row['sav']:+.2f}+/-{row['sav_sd']:.2f}%  f_s {fs_r:.2f}"
              f"  dT {row['dT']:+.4f}", flush=True)
    H.series = _epw_series
    os.makedirs(_ROOT + "/results", exist_ok=True)
    with open(_ROOT + "/results/T24_orientation.csv", "w",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print("-> results/T24_orientation.csv")
