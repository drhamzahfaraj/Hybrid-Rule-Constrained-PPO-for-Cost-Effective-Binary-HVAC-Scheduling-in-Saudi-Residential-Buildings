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
import sys, os
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np

import headroom as H
import final_tables as F
from hvac import read_epw
import amy_spread as AS          # weather() swap + the §2 protocol helpers (HOOK(F6/F7) there)

AZ = {"north": 0.0, "east": 90.0, "south": 180.0, "west": 270.0}


def series_at(city, azimuth):
    """headroom.series replacement: the city's TMYx record transposed to one glazed azimuth."""
    tdb, dni, dhi = read_epw(f"/home/claude/rbrl/{city}.epw")
    return AS._series_from(tdb, dni, dhi, city, azimuth)


def run(city="riyadh", price_v=AS.PRICE):
    rows = []
    for name, az in AZ.items():
        with AS.weather(series_at(city, az)):
            th = {w: F.therm_run(city, w, price_v) for w in F.EVAL_W}
            r = AS.protocol(city, price_v)
        row = dict(city=city, orientation=name, azimuth=az,
                   therm_J=float(np.mean([th[w]["J"] for w in F.EVAL_W])),
                   therm_E=float(np.mean([th[w]["E"] for w in F.EVAL_W])),
                   therm_fs=float(np.mean([th[w]["f_s"] for w in F.EVAL_W])), **r)
        print(f"{name:6s} az={az:5.0f}  THERM J={row['therm_J']:.4f}  {AS._fmt(r)}", flush=True)
        rows.append(row)
    return rows


if __name__ == "__main__":
    import rbrl_io as IO
    city = sys.argv[1] if len(sys.argv) > 1 else "riyadh"
    rows = run(city)
    ok = [r for r in rows if r.get("fit_status") != "none"]
    for r in rows:
        if r.get("fit_status") == "none":
            print(f"  not tabulated (no admissible parameter): {r['orientation']}")
    import v3_names as V
    IO.write_csv(V.name("ORIENT") + ("" if city == "riyadh" else f"_{city}"), ok,
                 inputs=[f"{IO.ROOT}/{city}.epw"], impl="orientation.py")
    print(f"-> results/{V.name('ORIENT')}.csv")
