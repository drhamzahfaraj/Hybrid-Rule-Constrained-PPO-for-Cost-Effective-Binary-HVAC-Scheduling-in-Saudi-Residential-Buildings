#!/usr/bin/env python3
"""Latent-load effect at the ADOPTED configuration.

The manuscript cites SHR 0.65 (Jeddah) and 0.85 (Riyadh) from the literature and
concludes that "because both THERM and RBRL share this penalty, percentage
savings remain valid". Two things are wrong with that.

1. The cited sensible heat ratios disagree with the EPW records actually used.
   Computed from the humidity fields over the cooling season, the infiltration
   SHR is 0.994 in Riyadh and 0.446 in Jeddah -- the cited pair is wrong in
   both directions.
2. A multiplicative error on the ENERGY term does not cancel in a ratio whose
   numerator is dominated by an additive SWITCHING term. Inflating the energy
   term shrinks the switching share and therefore shrinks the percentage.

The previous latent run (results/latent.csv) cannot settle either point: it was
made at C_th = 2400, band [22,26], SHR 0.75 for both cities, a single 7-day
window from day 181, and the superseded 22.7/25.8 rule. This script re-runs the
author's own two-state model at the configuration the paper actually adopts,
over the held-out window set, with each city's measured SHR.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, csv
sys.path.insert(0, _ROOT + "")
import numpy as np
import latent as L
import final_tables as F

C_TH, LO, HI = 4800.0, 22.0, 24.0
PRICE, C_SW = 0.18, 0.15
THERM = (22.5, 23.5)          # 1 K deadband, as the manuscript defines it
TUNED = {"riyadh": (22.35, 23.60), "jeddah": (22.35, 23.60),
         "taif": (22.40, 23.59)}


def measured_shr(city):
    """Infiltration sensible fraction over the cooling season, from the EPW."""
    z = L.LatentZone(city, c_th=C_TH, t_min=LO, t_max=HI,
                     price=PRICE, c_sw=C_SW)
    sl = slice(120 * 24, 296 * 24)
    t_out = np.asarray(z.t_out)[sl]
    w_out = np.asarray(z.w_out)[sl]
    sens = z.m_inf * L.CP * np.maximum(t_out - 23.0, 0.0)
    lat = z.m_inf * L.H_FG * np.maximum(w_out - float(z.w_set), 0.0)
    tot = sens.mean() + lat.mean()
    return (sens.mean() / tot if tot else 1.0), float(sens.mean()), float(lat.mean())


if __name__ == "__main__":
    rows = []
    for city in ("riyadh", "jeddah", "taif"):
        shr, s_w, l_w = measured_shr(city)
        print(f"\n=== {city.upper()}  measured SHR {shr:.3f}  "
              f"(sensible {s_w:.0f} W, latent {l_w:.0f} W) ===", flush=True)
        z = L.LatentZone(city, c_th=C_TH, t_min=LO, t_max=HI, price=PRICE,
                         c_sw=C_SW, shr_rated=round(shr, 3))
        for latflag in (False, True):
            tag = "with latent" if latflag else "sensible only"
            acc = {}
            for name, (lo_, hi_) in (("THERM", THERM), ("TUNED", TUNED[city])):
                Js, Es, fs, rhm, rhx, cap = [], [], [], [], [], []
                for w in F.EVAL_W:
                    r = z.run(L.hyst(lo_, hi_), start_day=w, days=7,
                              T0=23.0, latent=latflag)
                    Js.append(r["J"]); Es.append(r["E"]); fs.append(r["f_s"])
                    rhm.append(r["rh_mean"]); rhx.append(r["rh_max"])
                    cap.append(r["lat_capped"])
                acc[name] = (float(np.mean(Js)), float(np.mean(Es)),
                             float(np.mean(fs)), float(np.mean(rhm)),
                             float(np.max(rhx)), float(np.mean(cap)))
            Jb, Eb, fb, rb, rxb, cb = acc["THERM"]
            Jt, Et, ft, rt, rxt, ct = acc["TUNED"]
            sav = 100.0 * (Jb - Jt) / Jb
            starts = 100.0 * (fb - ft) / fb if fb else float("nan")
            rows.append(dict(city=city, shr=round(shr, 3), latent=latflag,
                             therm_J=round(Jb, 4), tuned_J=round(Jt, 4),
                             therm_E=round(Eb, 4), therm_fs=round(fb, 3),
                             tuned_fs=round(ft, 3),
                             rh_mean=round(rb, 1), rh_max=round(rxb, 1),
                             lat_capped_pct=round(cb, 1),
                             sav=round(sav, 2), start_sav=round(starts, 2)))
            print(f"  {tag:14s} THERM J={Jb:.4f} E={Eb:.3f} f_s={fb:.2f}  "
                  f"TUNED J={Jt:.4f} f_s={ft:.2f}  saving={sav:+.2f}%  "
                  f"starts={starts:+.1f}%  RH mean={rb:.1f}% max={rxb:.1f}%",
                  flush=True)
    with open(_ROOT + "/results/T10_latent.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print("\n--- effect of latent load on the reported percentage ---")
    for city in ("riyadh", "jeddah", "taif"):
        a = [r for r in rows if r["city"] == city and not r["latent"]][0]
        b = [r for r in rows if r["city"] == city and r["latent"]][0]
        print(f"  {city:7s} {a['sav']:+.2f}% -> {b['sav']:+.2f}%  "
              f"({b['sav']-a['sav']:+.2f} pp); THERM energy "
              f"{a['therm_E']:.3f} -> {b['therm_E']:.3f} kWh/day "
              f"({100*(b['therm_E']/a['therm_E']-1):+.1f}%); "
              f"THERM starts {a['therm_fs']:.2f} -> {b['therm_fs']:.2f}")
    print("-> results/T10_latent.csv")
