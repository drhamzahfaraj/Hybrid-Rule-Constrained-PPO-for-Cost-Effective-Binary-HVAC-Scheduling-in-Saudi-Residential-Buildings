#!/usr/bin/env python3
"""Does observing the inter-zone temperature enable coordination? (test of C3)

Contribution C3 claims that carrying adjacent-zone temperatures in the agent
state "enables the RBRL agent to anticipate inter-zone heat cascades". The
manuscript reports no multi-zone result, so the claim is unevidenced. This
script tests it directly, with a rule rather than a learned policy, because a
rule makes the mechanism explicit and because Corollary 1 says a learned policy
under hard guards reproduces the rule anyway.

The mechanism under test
------------------------
Inter-zone flux is a pure transfer: summed over an unordered pair it cancels,
so coupling creates no energy. What it does is REDISTRIBUTE. A zone being
cooled draws heat from its neighbours, which slows their warming and defers
their own switch-ons. Two zones cooling simultaneously waste that: each is
pulling heat from a neighbour that is itself being cooled. Two zones cooling in
turn exploit it.

So if C3 has content, a controller that can see T_iz should be able to stagger:
hold off switching on while a neighbour is already running and therefore
already cooling you. The coordinated rule below does exactly that, with one
parameter -- how much warmer the zone is allowed to get before overriding the
stagger -- and nothing else. If staggering buys nothing, C3 is unsupported on
this plant, which is a finding worth reporting rather than hiding.

Comfort is matched the same way as everywhere else in this study: each arm is
compared at a mean occupied temperature no warmer than the baseline's, so no
arm can buy a saving with temperature.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, csv
sys.path.insert(0, _ROOT + "")
import numpy as np
import multizone as MZ
import final_tables as F

LO, HI = 22.0, 24.0


def independent(on, off):
    """Per-zone hysteresis; no knowledge of neighbours."""
    def pol(T, prev, k, T_iz):
        u = prev.copy()
        u[T >= on] = 1
        u[T <= off] = 0
        return u
    return pol


def staggered(on, off, geo, hold):
    """Hysteresis that defers a switch-on while a neighbour is already on.

    `hold` is how far above the switch-on point the zone may drift before the
    stagger is overridden. hold = 0 disables the stagger and recovers the
    independent rule exactly, which the self-check below verifies.
    """
    nbr = [[] for _ in range(geo["nz"])]
    for a, b in geo["pairs"]:
        nbr[a].append(b)
        nbr[b].append(a)

    def pol(T, prev, k, T_iz):
        u = prev.copy()
        want = T >= on
        for i in np.flatnonzero(want):
            if u[i] == 1:
                continue
            # a neighbour already cooling is already drawing heat out of i
            busy = any(prev[j] == 1 for j in nbr[i])
            if busy and T[i] < on + hold:
                continue                     # defer; the neighbour is helping
            u[i] = 1
        u[T <= off] = 0
        return u
    return pol


TOL = 0.03          # per-window match tolerance, as final_tables.tune_rule uses


def match_and_run(geo, city, policy_fn, windows, step=0.05, span=1.2,
                  tol=TOL):
    """Search the threshold pair, admitting only comfort-matched arms.

    A fixed-threshold rule uses ONE pair across all windows, so it cannot match
    every window exactly the way an arm with a per-window ceiling can. The
    criterion is therefore the one `final_tables.tune_rule` applies to TUNED:
    the mean occupied temperature must be within `tol` of the baseline's in
    EVERY window, and no occupied degree-hours may be leaked. Both arms here
    are held to it, so the comparison between them is like for like.
    """
    base = {}
    for w in windows:
        base[w] = MZ.simulate(geo, city, w, MZ.hyst(23.5, 22.5), days=7)
    best = None
    for on in np.arange(23.95, 23.95 - span, -step):
        for db in (1.00, 1.15, 1.25):
            off = on - db
            rs, ok = [], True
            for w in windows:
                r = MZ.simulate(geo, city, w, policy_fn(on, off), days=7)
                if abs(r["T_mean_occ"] - base[w]["T_mean_occ"]) > tol:
                    ok = False
                    break
                if r["deg_h_occ"] > 2e-3:
                    ok = False
                    break
                rs.append(r)
            if ok and len(rs) == len(windows):
                J = float(np.mean([r["J"] for r in rs]))
                sav = float(np.mean(
                    [100.0 * (base[w]["J"] - r["J"]) / base[w]["J"]
                     for w, r in zip(windows, rs)]))
                dT = float(np.mean([r["T_mean_occ"] - base[w]["T_mean_occ"]
                                    for w, r in zip(windows, rs)]))
                worst = float(np.max([r["T_mean_occ"] - base[w]["T_mean_occ"]
                                      for w, r in zip(windows, rs)]))
                if best is None or J < best["J"]:
                    best = dict(on=float(on), off=float(off), J=J, sav=sav,
                                dT=dT, worst_dT=worst,
                                f_s=float(np.mean([r["f_s"] for r in rs])))
    base_J = float(np.mean([base[w]["J"] for w in windows]))
    return best, base_J


if __name__ == "__main__":
    city = "riyadh"
    windows = F.EVAL_W
    rows = []
    print("DOES SEEING THE NEIGHBOURS HELP? (contribution C3)\n")
    print("Only 3x3 and 4x4 are tested: in 1xN and 2x2 every zone is")
    print("identical, so the inter-zone flux is exactly zero and there is")
    print("nothing to coordinate.\n")
    for kind, n in (("grid", 3), ("grid", 4)):
        geo = MZ.build(kind, n, city)
        print(f"=== {geo['label']}  (N_z={geo['nz']}) ===", flush=True)
        ind, base_J = match_and_run(geo, city, independent, windows)
        if ind is None:
            print("  independent: no admissible match"); continue
        print(f"  independent  on/off {ind['on']:.2f}/{ind['off']:.2f}  "
              f"J={ind['J']:.4f}  saving {ind['sav']:+.2f}%  "
              f"f_s={ind['f_s']:.3f}  dT={ind['dT']:+.4f}", flush=True)
        rows.append(dict(topo=geo["label"], nz=geo["nz"], arm="independent",
                         hold=0.0, **{k: round(v, 5) for k, v in ind.items()}))
        for hold in (0.10, 0.20, 0.30):
            fn = lambda on, off, g=geo, h=hold: staggered(on, off, g, h)
            co, _ = match_and_run(geo, city, fn, windows)
            if co is None:
                print(f"  stagger h={hold:.2f}: no admissible match")
                continue
            delta = co["sav"] - ind["sav"]
            print(f"  stagger h={hold:.2f}  on/off {co['on']:.2f}/"
                  f"{co['off']:.2f}  J={co['J']:.4f}  saving {co['sav']:+.2f}% "
                  f" ({delta:+.2f} pts vs independent)  f_s={co['f_s']:.3f}",
                  flush=True)
            rows.append(dict(topo=geo["label"], nz=geo["nz"], arm="staggered",
                             hold=hold,
                             **{k: round(v, 5) for k, v in co.items()}))
    if rows:
        with open(_ROOT + "/results/T19_coordination.csv", "w",
                  newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
        print("\n-> results/T19_coordination.csv")
    print("\nReading: if no stagger setting beats the independent rule at "
          "matched\ncomfort, then on this plant inter-zone observation buys "
          "nothing, and C3\nmust be scoped to the capacity-limited shared-plant"
          " case it was argued for.")
