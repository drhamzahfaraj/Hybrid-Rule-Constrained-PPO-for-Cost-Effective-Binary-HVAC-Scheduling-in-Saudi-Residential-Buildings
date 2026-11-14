#!/usr/bin/env python3
"""Search audit (RULING_round4 F7, job J25): no fitted parameter may sit on the edge of its
search range, and no admissible neighbour of a FINAL parameter may be cheaper under the A4
objective (equalised tuning cost ratio, final_tables.score_candidates).

For TUNED (in force tariff) the chosen (on, off) is re-scored together with its +/- 0.05 K
neighbourhood at 0.01 K; for guard the cap with its +/- 0.05 K neighbourhood. A neighbour that A4
would select over the final parameter (better fit_status, or the same status and a strictly
lower ratio) is a failure. Edge hits of the other fitted quantities are listed. Reads the final
parameters through rbrl_io (provenance), writes results/T29_search_audit.csv, exits non-zero on
any failure or unexplained edge hit.

Usage: python3 search_audit.py [city,...]
"""
import sys, os
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import final_tables as F
import t1_v2 as T1V2
import rbrl_io as IO

PRICE = T1V2.PRICE


def neighbours_rule(on, off, r=0.05):
    nb = np.round(np.arange(-r, r + 1e-9, 0.01), 2)
    return [(round(on + a, 2), round(off + b, 2)) for a in nb for b in nb
            if (a, b) != (0.0, 0.0) and (on + a) - (off + b) >= 0.1 - 1e-9
            and on + a <= F.OCC_HI + 1e-9 and off + b >= F.OCC_LO - 1e-9]


def audit_rule(city, on, off, price_v=PRICE, windows=None, db=1.0):
    """(base standing, [(neighbour, standing) A4 would prefer]) for a hysteresis rule."""
    windows = list(F.TUNE_W if windows is None else windows)
    cands = [(round(on, 2), round(off, 2))] + neighbours_rule(on, off)
    rows = F._rows_rule_batch(city, price_v, windows, cands)
    st = F.score_candidates(cands, rows, city, price_v, windows, db)
    return st[0], [(c, s) for c, s in zip(cands[1:], st[1:]) if F.better_than(s, st[0])]


def audit_guard(city, cap, price_v=PRICE, windows=None, db=1.0):
    windows = list(F.TUNE_W if windows is None else windows)
    caps = [round(cap + d, 2) for d in np.round(np.arange(-0.05, 0.0501, 0.01), 2)]
    caps = [cap] + [c for c in caps if c != cap and F.OCC_HI - 0.5 - 1e-9 <= c <= F.OCC_HI + 1e-9]
    rows = F._rows_rule_batch(city, price_v, windows, [(c - T1V2.GUARD_HOT, T1V2.GUARD_OFF) for c in caps])
    st = F.score_candidates(caps, rows, city, price_v, windows, db)
    return st[0], [(c, s) for c, s in zip(caps[1:], st[1:]) if F.better_than(s, st[0])]


def main(cities=F.CITIES):
    rows, bad = [], []
    def rec(item, city, val, lo, hi, note=""):
        edge = abs(val - lo) < 1e-9 or abs(val - hi) < 1e-9
        rows.append(dict(item=item, city=city, value=val, range_lo=lo, range_hi=hi, at_edge=edge, note=note))
        if edge and "natural" not in note:
            bad.append(f"{item} {city} = {val} at edge [{lo},{hi}]")
    params = IO.read_json("tuned_params_v2")
    for c in cities:
        for arm in ("TUNED", "guard"):
            p = params.get(f"{c}|inforce|{arm}")
            if p is None:
                continue
            if arm == "TUNED":
                rec("TUNED on", c, p["on"], F.OCC_LO + 0.3, F.OCC_HI)
                rec("TUNED off", c, p["off"], F.OCC_LO, p["on"] - 0.1)
                base, better = audit_rule(c, p["on"], p["off"])
            else:
                rec("guard cap", c, p["cap"], F.OCC_HI - 0.5, F.OCC_HI)
                base, better = audit_guard(c, p["cap"])
            if base["status"] != p.get("fit_status"):
                bad.append(f"{arm} {c}: recorded fit_status {p.get('fit_status')!r} != re-scored {base['status']!r}")
            for q, s in better:
                bad.append(f"{arm} {c}: neighbour {q} {s['status']} ratio {s['obj']:.6f} beats final "
                           f"{base['status']} {base['obj']:.6f}")
            rows.append(dict(item=f"{arm} A4 neighbourhood", city=c, value=str(p), at_edge="",
                             fit_status=base["status"], tune_obj=base["obj"], n_better=len(better),
                             note="0.01 K, +/-0.05 K"))
            print(f"{c}: {arm} {p} {base['status']} ratio={base['obj']:.6f}; {len(better)} better neighbour(s)",
                  flush=True)
    # edge hits of the other fitted quantities, from whichever result tables exist
    for c in cities:
        for name, col, lo, hi, label in ((f"rbrl_ppo5_v2_{c}", "cap", F.OCC_HI - 0.5, F.OCC_HI, "RBRL cap"),
                                         (f"T21v3_{c}", "lam", 0.0, 24.0, "MPC lam"),
                                         (f"T21v2_{c}", "lam", 0.0, 24.0, "MPC lam")):
            if not os.path.exists(f"{IO.R}/{name}{IO.tag()}.csv"):
                continue
            for r in IO.read_csv(name):
                if r.get(col) not in ("", None):
                    v = float(r[col])
                    rec(f"{label} {name} {r.get('seed', r.get('horizon_h', ''))}", c, v, lo, hi,
                        "natural boundary: lam = 0 (mean constraint slack)" if label == "MPC lam" and v == 0 else "")
    IO.write_csv("T29_search_audit", rows, ndigits=None)
    print(f"{len(rows)} items audited; {len(bad)} failure(s)")
    for b in bad:
        print("  ", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1].split(",") if len(sys.argv) > 1 else F.CITIES))
