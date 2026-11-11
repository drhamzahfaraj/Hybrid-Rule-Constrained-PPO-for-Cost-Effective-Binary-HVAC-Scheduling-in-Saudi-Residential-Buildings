#!/usr/bin/env python3
"""Inter-annual spread of the reported saving, on actual years.

The headline tables run on one TMYx year per city. This study re-runs the
paper's own protocol---tune the two-parameter rule on the tuning windows,
admit it only if comfort-matched in every one, evaluate on the disjoint
held-out windows against that year's own baseline---inside ACTUAL years
(ERA5 reanalysis, see amy_fetch.py), chosen per city as the hottest, the
median and the mildest of 2009--2023 by cooling degree-days.

Two questions, two designs, one table:
  RETUNED  -- the protocol applied within the year: what the method reports
              when commissioned on the year it serves.
  TRANSFER -- the TMYx-tuned thresholds applied unchanged to the real year,
              re-matched on nothing: what a rule commissioned once does when
              the weather is not the typical year.

What this is NOT: a replacement for the headline. ERA5 is a reanalysis on a
0.25-degree cell, not a station record, so these runs measure the SPREAD of
the saving across real years at fixed method and plant, and the TMYx figures
remain the reported ones. The weather source changes; the optics do not---the
same plane-of-array transposition is applied to the ERA5 direct and diffuse
components.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, os, csv, json
sys.path.insert(0, _ROOT + "")
import numpy as np

import headroom as H
import final_tables as F
from hvac import vertical_irradiance

AMY = _ROOT + "/amy"
_epw_series = H.series            # keep the TMY path


def amy_series_fn(city, year):
    """A drop-in replacement for headroom.series reading one ERA5 year."""
    p = f"{AMY}/{city}_{year}.csv"
    tdb, dni, dhi = [], [], []
    for r in csv.DictReader(open(p)):
        tdb.append(float(r["tdb_C"])); dni.append(float(r["dni_Wm2"]))
        dhi.append(float(r["dhi_Wm2"]))
    tdb = np.array(tdb)
    irr = vertical_irradiance(np.array(dni), np.array(dhi), H.CITIES[city],
                              azimuth_deg=180.0)

    def series(city_, hours, start_day):
        spd = int(round(1.0 / H.DT)); N = int(round(hours / H.DT))
        h0 = start_day * 24
        return (np.repeat(tdb[h0:h0 + hours], spd)[:N],
                np.repeat(irr[h0:h0 + hours], spd)[:N], N)
    return series


def protocol(city):
    """The paper's protocol on whatever H.series currently points to."""
    th = {w: F.therm_run(city, w, 0.18) for w in F.EVAL_W}
    Jb = np.array([th[w]["J"] for w in F.EVAL_W])
    got = F.tune_rule(city, 0.18, F.TUNE_W,
                      lambda w: F.therm_run(city, w, 0.18)["T_mean_occ"])
    if got is None:
        return dict(ok=False, therm_J=float(Jb.mean()))
    _, on_, off_ = got
    rs = [F.rule_run(city, w, 0.18, on_, off_) for w in F.EVAL_W]
    J = np.array([r["J"] for r in rs])
    sav = 100.0 * (Jb - J) / Jb
    return dict(ok=True, on=on_, off=off_, therm_J=float(Jb.mean()),
                J=float(J.mean()), sav=float(sav.mean()),
                sav_sd=float(sav.std(ddof=1)),
                dT=float(np.mean([r["T_mean_occ"] for r in rs])
                         - np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W])),
                deg_h=float(max(r["deg_h_occ"] for r in rs)))


def transfer(city, on_, off_):
    th = {w: F.therm_run(city, w, 0.18) for w in F.EVAL_W}
    Jb = np.array([th[w]["J"] for w in F.EVAL_W])
    rs = [F.rule_run(city, w, 0.18, on_, off_) for w in F.EVAL_W]
    J = np.array([r["J"] for r in rs])
    sav = 100.0 * (Jb - J) / Jb
    return dict(sav=float(sav.mean()), sav_sd=float(sav.std(ddof=1)),
                dT=float(np.mean([r["T_mean_occ"] for r in rs])
                         - np.mean([th[w]["T_mean_occ"] for w in F.EVAL_W])),
                deg_h=float(max(r["deg_h_occ"] for r in rs)))


if __name__ == "__main__":
    sel = json.load(open(f"{AMY}/amy_selected.json"))
    rows = []
    for city in ("riyadh", "jeddah", "taif"):
        # the TMYx reference, and the thresholds TRANSFER carries
        H.series = _epw_series
        base = protocol(city)
        print(f"\n=== {city.upper()}  TMYx: sav {base['sav']:+.2f}% "
              f"rule {base['on']:.2f}/{base['off']:.2f} ===", flush=True)
        rows.append(dict(city=city, year="TMYx", kind="RETUNED",
                         cdd=None, **{k: round(v, 4) if isinstance(v, float)
                                      else v for k, v in base.items()}))
        summ = {r["city"]: {} for r in rows}
        cdd = {(r["city"], str(r["year"])): float(r["cdd24"])
               for r in csv.DictReader(open(f"{AMY}/amy_summary.csv"))}
        for kind in ("mild", "median", "hot"):
            year = sel[city][kind]
            if not os.path.exists(f"{AMY}/{city}_{year}.csv"):
                print(f"  {kind} {year}: file missing, skipped"); continue
            H.series = amy_series_fn(city, year)
            r1 = protocol(city)
            tag = f"{year} ({kind}, CDD {cdd.get((city, str(year)), 0):.0f})"
            if r1["ok"]:
                print(f"  {tag:28s} RETUNED  sav {r1['sav']:+.2f}+/-"
                      f"{r1['sav_sd']:.2f}%  rule {r1['on']:.2f}/{r1['off']:.2f}"
                      f"  dT {r1['dT']:+.4f}  deg-h {r1['deg_h']:.3f}",
                      flush=True)
            else:
                print(f"  {tag:28s} RETUNED  no admissible rule", flush=True)
            r2 = transfer(city, base["on"], base["off"])
            print(f"  {'':28s} TRANSFER sav {r2['sav']:+.2f}+/-"
                  f"{r2['sav_sd']:.2f}%  dT {r2['dT']:+.4f}  "
                  f"deg-h {r2['deg_h']:.3f}", flush=True)
            rows.append(dict(city=city, year=year, kind="RETUNED",
                             cdd=cdd.get((city, str(year))),
                             **{k: round(v, 4) if isinstance(v, float) else v
                                for k, v in r1.items()}))
            rows.append(dict(city=city, year=year, kind="TRANSFER",
                             cdd=cdd.get((city, str(year))), ok=True,
                             **{k: round(v, 4) for k, v in r2.items()}))
        H.series = _epw_series
    os.makedirs(_ROOT + "/results", exist_ok=True)
    keys = sorted({k for r in rows for k in r})
    with open(_ROOT + "/results/T23_amy_spread.csv", "w",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)
    print("\n-> results/T23_amy_spread.csv")
