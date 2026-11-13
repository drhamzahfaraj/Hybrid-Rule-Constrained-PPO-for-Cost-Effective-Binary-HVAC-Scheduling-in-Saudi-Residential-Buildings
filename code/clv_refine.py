#!/usr/bin/env python3
"""CLV alone (J8 re-run without the pooled bound; F10). Per held-out window: bound_v2.clv_row --
r3_dp.clv_fit (two-sided lam refinement to 0.002 K, admissibility through F.admissible inside it,
no fallback step), Rule C scoring (F.equalise at the CLV's own mean), fit_status "oracle", T_end.
The per-window certificate (and s_CLV <= B_CLV, B*) is checked against the relaxed bound of the
same city when its T17v3 files exist (bound_v2.py main writes CLV and bound together; this script
only refits the CLV). No selection happens here: the selection rule lives in r3_dp.clv_fit.
Usage: python3 clv_refine.py <city> [setback]  ->  results/T13v3_clv_<city>[_sb].csv"""
import sys, os
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
import config as CFG
import final_tables as F, r3_dp as D, bound_v2 as B
import rbrl_io as IO
import v3_names as V

K = F.MEAN_KEY


def main(city, sb=False):
    stem = V.name("CLV_SB" if sb else "CLV", city)
    pwb, curves = {}, None
    if os.path.exists(f"{IO.R}/{stem}_perwindow.csv"):
        pwb = {int(float(r["window"])): r for r in IO.read_csv(f"{stem}_perwindow", apply_tag=False)}
        key = f"{city}|{CFG.PRICE}|{CFG.C_SW}|{sb}"
        curves = IO.read_json(f"{stem}{IO.tag()}_dualcurves", apply_tag=False).get(key)
    rows = []
    for w in F.EVAL_W:
        th = B.therm_eval(city, w, CFG.PRICE, sb)
        row = dict(city=city, setback=sb, window=w, therm_J=th["J"], therm_T=th[K],
                   **B.clv_row(city, w, CFG.PRICE, sb, F.C_SW, 6401 if sb else 3201, th))
        if w in pwb:
            row["clv_cert_margin"] = D.certificate_margin(row["clv_J"], row["clv_T"], pwb[w]["bound_J_w"],
                                                          pwb[w]["lam_w"], th[K])
        rows.append(row)
        print(city, sb, w, round(row["clv_s_w"], 2), row["clv_tol_met"], row.get("clv_cert_margin"), flush=True)
    s = F.pooled_saving([r["clv_J"] for r in rows], [r["clv_J_eq"] for r in rows])
    summ = dict(city=city, setback=sb, fit_status="oracle", clv_s_pooled=s,
                clv_n_tol_met=int(sum(bool(r["clv_tol_met"]) for r in rows)))
    if curves:
        Tc = float(np.mean([r["clv_T"] for r in rows]))
        summ["clv_B_a"] = 100.0 * (1 - B.lower_cost_curves(curves, Tc) / float(np.mean([r["clv_J_eq"] for r in rows])))
        summ["clv_le_B_a"] = s <= summ["clv_B_a"] + 1e-9
        summ["clv_cert_min_margin"] = float(min(r["clv_cert_margin"] for r in rows))
    print(f"{city} setback={sb}: CLV (Rule C) {s:.2f}%  " +
          " ".join(f"{k}={v}" for k, v in summ.items() if k.startswith("clv_") and k != "clv_s_pooled"), flush=True)
    name = f"T13v3_clv_{city}{'_sb' if sb else ''}"
    IO.write_csv(name, [dict(r, fit_status="oracle") for r in rows], ndigits=None)    # F2: via rbrl_io
    IO.write_csv(name + "_summary", [summ], ndigits=None)


if __name__ == "__main__":
    main(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == "setback")
