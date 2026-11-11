#!/usr/bin/env python3
"""Per-start transient-loss sensitivity (manuscript §Limitations, "No per-start
energy penalty").

The model charges a compressor start money (c_sw) but no energy, so a start
reduction cannot appear as an energy saving by construction. AHRI 210/240's
C_D cannot repair this: it enters through PLF = 1 - C_D(1 - X), and the
duty-cycle identity equalises the part-load ratio X across mean-matched arms,
so C_D degrades every arm identically. What would differentiate the arms is a
fixed energy loss per start. This script charges each start a loss of
`wh` watt-hours on the Riyadh held-out means and reports the THERM-TUNED
energy difference.
"""
from __future__ import annotations
import csv, os
_ROOT = os.path.dirname(os.path.abspath(__file__))


def means(city="riyadh"):
    rows = list(csv.DictReader(open(f"{_ROOT}/results/T1_heldout_three_cities.csv")))
    pick = lambda pre: next(r for r in rows if r["city"] == city and r["tariff"] == "inforce"
                            and r["controller"].startswith(pre))
    t, u = pick("THERM"), pick("tuned")
    return (float(t["E_mean"]), float(t["fs_mean"])), (float(u["E_mean"]), float(u["fs_mean"]))


if __name__ == "__main__":
    (Et, ft), (Eu, fu) = means()
    print(f"Riyadh held-out means: THERM E={Et:.4f} kWh/day f_s={ft:.3f}; "
          f"TUNED E={Eu:.4f} kWh/day f_s={fu:.3f}")
    out = []
    for wh in (0, 10, 20, 30, 50, 100):
        e = wh / 1000.0
        a, b = Et + e * ft, Eu + e * fu
        d = 100.0 * (a - b) / a
        out.append(dict(wh_per_start=wh, therm_E=round(a, 4), tuned_E=round(b, 4),
                        energy_saving_pct=round(d, 2)))
        print(f"  {wh:3d} Wh/start: energy saving TUNED vs THERM {d:+.2f}%")
    with open(f"{_ROOT}/results/T25_cycling_energy.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print("-> results/T25_cycling_energy.csv")
