#!/usr/bin/env python3
"""Classify occupied band excursions by CAUSE, not by sign.

The defect this addresses
-------------------------
The manuscript exempts under-temperature excursions on the grounds that they
"reflect the absence of a heating actuator and no scheduling policy can correct
them", and then uses under-temperature as the sole evidence that dt = 60 min,
C_th <= 1800 kJ/K and delta_db = 1.5 C are inadmissible. Both cannot be right.

The exemption is correct for a zone free-floating with the compressor OFF while
the outdoor temperature sits below the band: a cooling-only plant genuinely
cannot raise the temperature. It is wrong for a zone driven below the band by
the compressor being ON: Q*dt/C_th overshoot is a control failure, and a
shorter interval or a narrower deadband removes it entirely.

So the test must split by the commanded state at the moment of the excursion:

  over-temperature, any state            -> control failure
  under-temperature while u = 1          -> control failure (cooling overshoot)
  under-temperature while u = 0 and
      T_out below the band               -> plant limit (no heating actuator)
  under-temperature while u = 0 and
      T_out above the band               -> control failure (should not occur)

This script re-runs the configurations the manuscript calls inadmissible and
reports the split, so the admissibility verdicts can be restated in terms the
paper's own exemption actually supports.
"""
from __future__ import annotations
import sys
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import headroom as H
import setback as S

LO, HI = 22.0, 24.0
T0 = 23.0


def run_split(city, start_day, dt_h, c_th, lo_sw, hi_sw, price_v=0.18,
              faces=1, days=7):
    """Simulate a fixed hysteresis and split occupied degree-hours by cause."""
    old_dt = S.DT
    S.DT = dt_h
    try:
        steps = int(round(24.0 / dt_h))
        t_out, irr, N = H.series(city, 24 * days, start_day, )
    finally:
        S.DT = old_dt
    return None


def simulate(city, start_day, dt_h, c_th, lo_sw, hi_sw, days=7, faces=1):
    """Minimal explicit simulation so the cause split is unambiguous."""
    q = H.Q_HVAC
    lam = H.lam_of(faces, city)
    # hourly weather, zero-order held over the sub-steps of this interval
    spd = int(round(24.0 / dt_h))
    h0 = start_day * 24
    tdb = np.asarray(H.raw_tdb(city))[h0:h0 + 24 * days] \
        if hasattr(H, "raw_tdb") else None
    if tdb is None:
        # fall back on headroom.series at its own resolution
        old = S.DT
        S.DT = dt_h
        try:
            t_out, irr, N = H.series(city, 24 * days, start_day)
        finally:
            S.DT = old
    else:
        t_out = np.repeat(tdb, spd)
        irr = np.zeros_like(t_out)
        N = len(t_out)
    decay = float(np.exp(-dt_h * 3600.0 * lam / (c_th * 1e3)))

    T, u = T0, 0
    over = under_on = under_off_cold = under_off_warm = 0.0
    for k in range(N):
        if T >= hi_sw:
            u = 1
        elif T <= lo_sw:
            u = 0
        g = H.SHGC * H.A_GL * irr[k]
        T_inf = t_out[k] + (g - q * u) / lam
        T = T_inf + (T - T_inf) * decay
        if T > HI:
            over += (T - HI) * dt_h
        elif T < LO:
            d = (LO - T) * dt_h
            if u == 1:
                under_on += d
            elif t_out[k] < LO:
                under_off_cold += d
            else:
                under_off_warm += d
    return dict(over=over, under_on=under_on,
                under_off_cold=under_off_cold,
                under_off_warm=under_off_warm)


if __name__ == "__main__":
    print("Occupied-band excursions split by CAUSE (7-day windows).\n")
    print(f"{'case':38s} {'over':>8} {'under|on':>9} {'under|off':>10} "
          f"{'verdict':>18}")
    cases = [
        ("delta_db = 1.50 C (called inadmissible)",
         dict(city="riyadh", start_day=205, dt_h=0.25, c_th=4800.0,
              lo_sw=22.25, hi_sw=23.75)),
        ("delta_db = 1.00 C (adopted)",
         dict(city="riyadh", start_day=205, dt_h=0.25, c_th=4800.0,
              lo_sw=22.5, hi_sw=23.5)),
        ("dt = 60 min (called inadmissible)",
         dict(city="riyadh", start_day=205, dt_h=1.0, c_th=4800.0,
              lo_sw=22.5, hi_sw=23.5)),
        ("dt = 15 min (adopted)",
         dict(city="riyadh", start_day=205, dt_h=0.25, c_th=4800.0,
              lo_sw=22.5, hi_sw=23.5)),
        ("C_th = 1200 kJ/K (called inadmissible)",
         dict(city="riyadh", start_day=205, dt_h=0.25, c_th=1200.0,
              lo_sw=22.5, hi_sw=23.5)),
        ("Taif baseline, 16 Oct window",
         dict(city="taif", start_day=289, dt_h=0.25, c_th=4800.0,
              lo_sw=22.5, hi_sw=23.5)),
    ]
    for name, kw in cases:
        try:
            r = simulate(**kw)
        except Exception as e:
            print(f"{name:38s}  failed: {type(e).__name__}: {e}")
            continue
        under_off = r["under_off_cold"] + r["under_off_warm"]
        ctrl = r["over"] + r["under_on"] + r["under_off_warm"]
        verdict = "CONTROL FAILURE" if ctrl > 1e-3 else (
            "plant limit only" if under_off > 1e-3 else "clean")
        print(f"{name:38s} {r['over']:8.4f} {r['under_on']:9.4f} "
              f"{under_off:10.4f} {verdict:>18}")
    print("\nA configuration is inadmissible if the CONTROL-FAILURE column is "
          "non-zero.\nUnder-temperature with the compressor off and the "
          "outdoor air below the band\nis a missing heating actuator, which no "
          "scheduler can correct.")
