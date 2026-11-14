#!/usr/bin/env python3
"""Per-start transient-loss sensitivity on the v3 files (RULING_round4 F16, job J23; E-hvac2-2, H1-9).

The model charges a compressor start money (c_sw) but no energy, so a start reduction cannot
appear as an energy saving by construction. This script charges each start a fixed loss of
`wh` watt-hours and reports the pooled energy saving of each arm against ITS OWN Rule C
comparator THERM(delta_w), with the end-of-window thermal store priced (terminal pricing).

Energy accounting (§2.3, terminal-priced, flat tariff):
    J = c_sw * f_s + price * E_tp,   E_tp = E_metered + (T_end - T0) C_th / (3.6e3 COP_rated) / days
(the start energy E_START, if any, is inside both E and the per-start charge, so the identity is
exact). The equalised comparator carries only J_eq and fs_eq (linear interpolation commutes with
the identity), so E_tp is recovered from J for both sides:  E_tp = (J - c_sw f_s) / price.
For the arm this is cross-checked against E_arm + the terminal term from T_end (|diff| <= 1e-4
kWh/day, else the script stops).  At equal clipped mean the two E_tp agree to about 1e-5
(duty-cycle identity), so the per-start loss adds an energy saving of about e_s * dN / E.

    saving(e_s) = 1 - sum_w (E_tp,arm,w + e_s fs_arm,w) / sum_w (E_tp,eq,w + e_s fs_eq,w)

Loss grid: absolute 0, 5.5, 10, 14, 25, 50, 100 Wh, and tau_eff * P_el for tau_eff = 0.5, 1, 1.26,
2 min (P_el = Q_HVAC / COP_rated; H2-8: C_D 0.10-0.25 implies tau 0.5-1.26 min).

Usage:  python3 cycling_energy.py [--arms TUNED,guard,MPC24]   -> results/T25v3_cycling_energy.csv
Inputs: T1v3_perwindow (TUNED, guard at the tariff in force), T21v3_<city>_perwindow (MPC-24).
A missing input is an error (no silent skip).
"""
from __future__ import annotations
import argparse, os, sys
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
import numpy as np
import rbrl_io as IO
import v3_names as V
import config as CFG

WH_GRID = (0.0, 5.5, 10.0, 14.0, 25.0, 50.0, 100.0)
TAU_MIN = (0.5, 1.0, 1.26, 2.0)
DAYS = 7.0


def p_el_kw():
    import headroom as H
    return H.Q_HVAC / H.COP_RATED / 1000.0


def _price(r):
    if r.get("price") not in (None, ""):
        return float(r["price"])
    return float(CFG.TARIFFS[r.get("tariff") or "inforce"])


def _csw(r):
    return float(r["c_sw"]) if r.get("c_sw") not in (None, "") else float(CFG.C_SW)


def e_tp(J, fs, price, c_sw):
    """terminal-priced energy (kWh/day) implied by a cost under a flat tariff."""
    return (float(J) - c_sw * float(fs)) / price


def window_energy(r, check=True, c_th=None, t0=None, tol=1e-4):
    """(E_tp_arm, E_tp_eq, fs_arm, fs_eq) of one per-window row; cross-checks the arm's E_tp against
    metered E plus the priced terminal store when E_arm and T_end are present."""
    import headroom as H
    pv, cs = _price(r), _csw(r)
    ea, eq = e_tp(r["J_arm"], r["fs_arm"], pv, cs), e_tp(r["J_eq"], r["fs_eq"], pv, cs)
    if check and r.get("E_arm") not in (None, "") and r.get("T_end") not in (None, ""):
        c_th = float(r["c_th"]) if r.get("c_th") not in (None, "") else (CFG.C_TH if c_th is None else c_th)
        t0 = CFG.T0 if t0 is None else t0
        ea2 = float(r["E_arm"]) + (float(r["T_end"]) - t0) * c_th * 1e3 / 3.6e6 / H.COP_RATED / DAYS
        if abs(ea - ea2) > tol:
            raise ValueError(f"window {r.get('window')}: J-implied energy {ea:.6f} != metered + terminal "
                             f"{ea2:.6f} kWh/day (not terminal-priced, or not a flat tariff)")
    return ea, eq, float(r["fs_arm"]), float(r["fs_eq"])


def pooled_energy_saving(Ea, Eq, fa, fq, wh):
    """% energy saving of the arm against its equalised comparator with a loss of wh per start."""
    e = wh / 1000.0
    return 100.0 * (1.0 - (np.sum(Ea) + e * np.sum(fa)) / (np.sum(Eq) + e * np.sum(fq)))


def from_summary(J_arm_mean, J_eq_mean, start_sav_eq, price, c_sw, wh):
    """the same quantity from a summary row (as E-hvac2-2 derived it from T5v2): with identical
    terminal-priced energy, dJ = c_sw dN, so fs_eq = dN / start_sav and E_tp from J_eq."""
    dN = (float(J_eq_mean) - float(J_arm_mean)) / c_sw
    fq = dN / (float(start_sav_eq) / 100.0)
    Eq = e_tp(J_eq_mean, fq, price, c_sw)
    e = wh / 1000.0
    return 100.0 * e * dN / (Eq + e * fq)


def loss_grid():
    pel = p_el_kw()
    return [(wh, "") for wh in WH_GRID] + [(round(t / 60.0 * pel * 1000.0, 3), t) for t in TAU_MIN]


def arm_rows(arm, city):
    pw = V.perwindow(arm, city)
    ws = sorted(pw)
    vals = np.array([window_energy(pw[w]) for w in ws])
    Ea, Eq, fa, fq = vals.T
    fit = sorted({pw[w].get("fit_status", "") for w in ws})
    out = []
    for wh, tau in loss_grid():
        out.append(dict(city=city, arm=arm, wh_per_start=wh, tau_eff_min=tau, n_windows=len(ws),
                        E_tp_arm=float(Ea.mean()), E_tp_eq=float(Eq.mean()),
                        energy_identity_rel=float(1.0 - Ea.sum() / Eq.sum()),
                        fs_arm=float(fa.mean()), fs_eq=float(fq.mean()),
                        d_starts_per_day=float(fq.mean() - fa.mean()),
                        energy_saving_pct=pooled_energy_saving(Ea, Eq, fa, fq, wh),
                        fit_status="/".join(fit)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="TUNED,guard,MPC24")
    ap.add_argument("--cities", default=",".join(V.CITIES))
    a = ap.parse_args(argv)
    rows = []
    for city in a.cities.split(","):
        for arm in a.arms.split(","):
            rr = arm_rows(arm, city)
            rows += rr
            print(f"{city:7s} {arm:6s} identity {rr[0]['energy_identity_rel']:+.1e}  dN={rr[0]['d_starts_per_day']:.3f}/day  "
                  + " ".join(f"{r['wh_per_start']:g}Wh:{r['energy_saving_pct']:+.2f}%" for r in rr if r["tau_eff_min"] == ""),
                  flush=True)
    return IO.write_csv(V.name("CYCLING"), rows, ndigits=6)


if __name__ == "__main__":
    main()
