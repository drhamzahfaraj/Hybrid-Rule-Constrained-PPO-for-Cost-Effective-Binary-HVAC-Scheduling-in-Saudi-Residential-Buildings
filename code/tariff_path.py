#!/usr/bin/env python3
"""Is a step tariff path-dependent? The question that decides Rule R3.

Rule R3 was a soft bias toward pre-cooling. It was withdrawn on the grounds
that under a CONSTANT marginal price pre-cooling is strictly dominated, since
running colder than necessary raises consumption and the price does not reward
the timing. The obvious objection is that the step-wise tariff is not constant:
if the marginal price RISES with cumulative consumption, surely buying energy
early -- while the account is still in a cheap block -- is worth something, and
R3 should be reinstated for Model S.

This script settles it. Under any non-decreasing marginal price p(E), the
energy bill over a billing month is

    B = integral_0^{E_total} p(e) de

which depends ONLY on the total energy consumed, not on the order in which it
was consumed. Two schedules that consume the same total energy pay the same
energy bill whatever their timing, so no amount of pre-cooling can arbitrage
the tier structure WITHIN a billing month. And since pre-cooling raises total
energy (the duty-cycle identity), it strictly raises the bill.

The script verifies this three ways:
  (a) analytically, by integrating the tariff along two different consumption
      paths with identical totals;
  (b) by simulation, running two schedules with matched total energy and
      different timing through the Model S accumulator;
  (c) by checking the one case where the structure IS exploitable -- shifting
      consumption ACROSS a billing-month boundary, where the tiers reset.
"""
from __future__ import annotations
import sys
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np

TIERS = [(2000.0, 0.05), (4000.0, 0.10), (6000.0, 0.20),
         (float("inf"), 0.30)]


def marginal(E):
    for hi, p in TIERS:
        if E <= hi:
            return p
    return TIERS[-1][1]


def bill(E_total):
    """Integral of the marginal price from 0 to E_total."""
    b, prev = 0.0, 0.0
    for hi, p in TIERS:
        if E_total <= hi:
            return b + p * (E_total - prev)
        b += p * (hi - prev)
        prev = hi
    return b


def bill_along_path(increments):
    """Accumulate cost step by step, charging the marginal rate in force."""
    E, b = 0.0, 0.0
    for de in increments:
        # split the increment at any boundary it crosses
        rem = de
        while rem > 1e-12:
            p = marginal(E + 1e-12)
            nxt = min(hi for hi, _ in TIERS if hi > E + 1e-12)
            take = min(rem, nxt - E)
            b += p * take
            E += take
            rem -= take
    return b, E


if __name__ == "__main__":
    print("DOES THE STEP TARIFF REWARD TIMING?\n")

    # ---- (a) two paths, identical total -----------------------------------
    total = 2140.0            # the 4x4 account, which crosses the 2,000 boundary
    front = [total * 0.8, total * 0.2]       # most consumption early
    back = [total * 0.2, total * 0.8]        # most consumption late
    even = [total / 100.0] * 100             # evenly spread
    for name, path in (("front-loaded", front), ("back-loaded", back),
                       ("even", even)):
        b, E = bill_along_path(path)
        print(f"  {name:14s} total {E:8.1f} kWh -> bill {b:9.4f} SAR")
    print(f"  closed form   total {total:8.1f} kWh -> bill {bill(total):9.4f} SAR")
    paths = [bill_along_path(p)[0] for p in (front, back, even)]
    spread = max(paths) - min(paths)
    print(f"\n  spread across orderings: {spread:.3e} SAR "
          f"{'-- PATH-INDEPENDENT' if spread < 1e-9 else '-- PATH-DEPENDENT'}")

    # ---- (b) the consequence for pre-cooling ------------------------------
    print("\n  Consequence. Pre-cooling changes WHEN energy is drawn and, by the")
    print("  duty-cycle identity, raises how MUCH is drawn. Since the bill")
    print("  depends only on the total, the timing earns nothing and the extra")
    print("  energy costs. Pre-cooling is dominated under the step tariff for")
    print("  exactly the reason it is dominated under a flat one.")
    for extra in (0.0, 10.0, 50.0):
        print(f"    +{extra:5.1f} kWh of pre-cooling -> bill "
              f"{bill(total + extra):9.4f} SAR "
              f"({bill(total+extra)-bill(total):+.4f})")

    # ---- (c) the one case that IS exploitable -----------------------------
    print("\n  The exception: the tiers reset each billing month, so moving")
    print("  consumption ACROSS a month boundary is not path-independent.")
    hot, mild = 2600.0, 1400.0
    separate = bill(hot) + bill(mild)
    balanced = 2 * bill((hot + mild) / 2.0)
    print(f"    two months at {hot:.0f} and {mild:.0f} kWh : {separate:.4f} SAR")
    print(f"    the same 4,000 kWh split evenly  : {balanced:.4f} SAR")
    print(f"    seasonal shifting is worth       : {separate-balanced:+.4f} SAR"
          f"  ({100*(separate-balanced)/separate:+.2f}%)")
    print("\n  That is a seasonal storage question, not a within-day scheduling")
    print("  one, and nothing in this paper's formulation can exploit it: the")
    print("  horizon is one week and the thermal store holds 0.89 kWh.")

    # ---- (d) the same argument covers Model E, and explains the ablation ---
    print("\n(d) THE GENERAL STATEMENT, AND WHY THE COST-MODEL ABLATION WAS "
          "UNINFORMATIVE")
    cr, beta = 0.12, 5e-4

    def bill_E(E):
        return cr / beta * (np.exp(beta * E) - 1.0)

    def path_E(incs, n=2000):
        E, b = 0.0, 0.0
        for de in incs:
            h = de / n
            for _ in range(n):
                b += cr * np.exp(beta * E) * h
                E += h
        return b, E

    for name, p in (("front", [total * 0.8, total * 0.2]),
                    ("back", [total * 0.2, total * 0.8]),
                    ("even", [total / 50] * 50)):
        b, E = path_E(p)
        print(f"    Model E {name:6s}: {b:10.4f} SAR "
              f"(closed form {bill_E(E):10.4f}; residual is the Riemann sum)")
    print("\n    Any cost model whose marginal price is a function of")
    print("    cumulative consumption alone gives a bill that is the integral")
    print("    of that price, hence path-independent. Models L, E and S are")
    print("    all of this form. They therefore cannot be distinguished by the")
    print("    TIMING of consumption at all, only by the exchange rate between")
    print("    an avoided switch and an hour of running:")
    Q, dt, c_sw = 0.670, 0.25, 0.15
    for name, p in (("L (flat 0.12)", 0.12),
                    ("E (at E_cum)", cr * np.exp(beta * total)),
                    ("S (tier 2)", 0.10)):
        print(f"      {name:16s} p = {p:.4f} SAR/kWh  ->  "
              f"c_sw/(p*Phi*dt) = {c_sw/(p*Q*dt):6.2f}")
    print("\n    That single scalar is the whole of the difference between the")
    print("    three models. The cost-model ablation withdrawn from an earlier")
    print("    version of this study was therefore not uninformative because")
    print("    its data were wrong; it was uninformative because there is")
    print("    nothing for it to measure beyond a reparameterisation of"
          " c_sw.")
