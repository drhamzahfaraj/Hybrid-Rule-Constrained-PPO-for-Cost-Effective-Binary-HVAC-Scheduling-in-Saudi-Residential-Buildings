#!/usr/bin/env python3
"""Generate the round-4 LaTeX tables from the v3 result files (RULING_round4 F18, job J17).
No number in these tables is typed: every cell is read from a v3 CSV through v3_names, or computed
from one (pooled savings, HL estimates, B_a). A missing source file is an error.

Outputs (/home/claude/v4/tables/, provenance header line with the input shas):
  tab_main.tex         body (tabularx) of Table tab:main      -> main.tex, replaces its tabularx
  tab_sensitivity.tex  body of the merged Table tab:sensitivity (tariff, c_sw, deadband, C_th)
  tab_stats.tex        complete table* tab:stats (families F1-F5 of §2.4)
  tab_s_mz.tex         body of Table S-MZ (tab:s-mz)          -> supplement.tex

Usage: python3 gen_tables_v3.py [--out DIR] [--only main,sensitivity,stats,smz]
"""
from __future__ import annotations
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import rbrl_io as IO
import v3_names as V
import stats_v3 as SV
import config as CFG

OUT = os.environ.get("RBRL_TEX_TABLES", "/home/claude/v4/tables")
CITIES, CN = V.CITIES, V.CN
FIT = {"pooled_0.03": "a", "pooled_0.10": "b", "oracle": "o", "fixed": "f"}
FIT_NOTE = (r"Fit status: $^{a}$pooled $0.03\,$K; $^{b}$pooled fallback $0.10\,$K; $^{o}$oracle "
            r"(per-window $\lambda_w$); $^{f}$fixed $\lambda$.")
NA = "---"


# ------------------------------------------------------------------ formatting
def f(x, d=1, sign=False):
    x = float(x)
    if not np.isfinite(x):
        return NA
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"          # callers put cells in math mode


def fit_mark(st):
    marks = [FIT[s] for s in str(st).split("/") if s in FIT]
    bad = [s for s in str(st).split("/") if s and s not in FIT]
    if bad:
        raise ValueError(f"fit_status {bad} cannot be tabulated (§2.2: 'none' rows are never tabulated)")
    return f"$^{{{','.join(sorted(set(marks)))}}}$" if marks else ""


def mean(rows, k):
    return float(np.mean([float(r[k]) for r in rows]))


def hl_vs(sw_a, sw_tuned):
    r = SV.contrast(sw_a, sw_tuned, 0.0, 0.0)
    return f"${f(r['hl'], 1, True)}$ [${f(r['hl_lo'], 1, True)}$, ${f(r['hl_hi'], 1, True)}$]"


def write(name, text, out):
    os.makedirs(out, exist_ok=True)
    return IO.write_text(os.path.join(out, name), text)


# ------------------------------------------------------------------ tab:main
def _arm_cells(label, pw, sw_tuned, extra="", fit=None):
    """one city's cells for an arm from its per-window rows {w: row} (seeded arms: list of such)."""
    seeds = pw if isinstance(pw, list) else [pw]
    rows = [r for s in seeds for r in s.values()]
    s = float(np.mean([V.pooled(x.values()) for x in seeds]))
    sw = {w: float(np.mean([V.s_w(x[w]) for x in seeds])) for w in seeds[0]}
    fit = fit or "/".join(sorted({r.get("fit_status", "") for r in rows}))
    if not fit:
        raise ValueError(f"{label}: no fit_status (every fitted cell prints it, §2.2)")
    J = float(np.mean([mean(x.values(), "J_arm") for x in seeds]))
    on = mean(rows, "fs_arm"); don = on - mean(rows, "fs_eq")
    ndays = len(seeds)
    return [f"${J:.4f}$", f"${f(s)}${fit_mark(fit)}", NA if sw_tuned is None else hl_vs(sw, sw_tuned),
            f"${on:.2f}$ (${f(don, 2, True)}$)", f"${f(mean(rows, 'dT_w'), 3, True)}$",
            f"${mean(rows, 'T_end'):.2f}$",
            f"${sum(float(r['deg_h_cmd_under']) for r in rows) / ndays:.2f}$/"
            f"${sum(float(r['deg_h_ff_under']) for r in rows) / ndays:.2f}$", extra]


def tab_main():
    L = [r"\begin{tabularx}{\textwidth}{@{}llrrXrrrrl@{}}", r"\toprule",
         r" & & $J$ & $s$ & HL vs TUNED & On/day & $\Delta\tilde T$ & $T_{\mathrm{end}}$ & "
         r"Under cmd/ff & \\",
         r"Arm & City & (SAR/day) & (\%) & [95.3\% CI] (pts) & ($\Delta$) & (K) & ($^\circ$C) & (K\,h) & Note \\",
         r"\midrule"]
    t7 = {r["city"]: r for r in V.read("T7") if abs(float(r["deadband"]) - 1.0) < 1e-9}
    sw_t = {c: {w: V.s_w(r) for w, r in V.perwindow("TUNED", c).items()} for c in CITIES}
    best_att, Bstar, Ba_notes = {}, {}, []

    def block(label, cells_by_city):
        first = True
        for c in CITIES:
            if c not in cells_by_city:
                continue
            L.append(f"{label if first else ''} & {CN[c]} & " + " & ".join(cells_by_city[c]) + r" \\")
            first = False
        L.append(r"\addlinespace")

    def note_Ba(label, c, pw_rows):
        b, _ = V.B_a(c, pw_rows)
        if abs(b - Bstar[c]) >= 0.1:
            Ba_notes.append(f"{label} {CN[c]} ${b:.1f}$")

    for c in CITIES:
        (b,) = [r for r in V.read("CLV", c) if str(r.get("setback", "False")) == "False"]
        Bstar[c] = float(b["bound_reported"])
    # THERM
    cells = {}
    for c in CITIES:
        tu = V.summary("TUNED", c)
        fs = mean(V.perwindow("TUNED", c).values(), "fs_therm0") if "fs_therm0" in tu or \
            "fs_therm0" in next(iter(V.perwindow("TUNED", c).values())) else float(t7[c]["therm_fs"])
        cells[c] = [f"${float(tu['J_therm0_mean']):.4f}$", "0 (ref.)", NA, f"${fs:.2f}$", NA, NA, NA,
                    r"1\,K deadband"]
    block("THERM", cells)
    # rule arms
    for arm, lab in (("TUNED", "TUNED"), ("guard", "Guard hysteresis")):
        cells = {}
        for c in CITIES:
            pw = V.perwindow(arm, c); sm = V.summary(arm, c); p = json.loads(sm["params"])
            ex = (f"${p['on']:.2f}/{p['off']:.2f}$" if arm == "TUNED" else f"R1 ${p['on']:.2f}$")
            cells[c] = _arm_cells(lab, pw, None if arm == "TUNED" else sw_t[c], ex)
            note_Ba(lab, c, pw.values())
            if abs(mean(pw.values(), "dT_w")) <= 0.002:
                best_att[c] = max(best_att.get(c, -1e9), V.pooled(pw.values()))
        block(lab, cells)
    cells = {}
    for c in CITIES:
        seeds = list(V.perwindow_seeds("RBRL", c).values())
        cells[c] = _arm_cells("RBRL", seeds, sw_t[c], f"{len(seeds)} seeds")
    block("RBRL", cells)
    cells = {}
    for c in CITIES:
        best, pw = V.d1_selected(c)
        cells[c] = _arm_cells("D1", pw, sw_t[c], f"$\\sigma={float(best['sigma']):.2f}$",
                              fit=best["fit_status"])
        note_Ba("D1", c, pw.values())
    block("D1 shield (latch)", cells)
    for key, pre, lab in (("MPC", "MPC", "MPC, perfect"), ("MPC_PERS", "MPCp", "MPC, persistence"),
                          ("MPC_RULED", "MPCr", "MPC in rules")):
        hs = sorted({float(r["horizon_h"]) for c in CITIES for r in V.read(key, c)})
        for h in hs:
            cells = {}
            for c in CITIES:
                pw = V.perwindow(f"{pre}{h:g}", c)
                r0 = next(iter(pw.values()))
                gh = [float(r["grid_h"]) for r in pw.values() if r.get("grid_h") not in (None, "")]
                ex = f"$\\lambda/\\lambda^*={float(r0['lam_over_lam_star']):.2f}$" + \
                     (f", $h={1e3 * max(gh):.1f}\\,$mK" if gh else "")
                cells[c] = _arm_cells(lab, pw, sw_t[c], ex)
                note_Ba(f"{lab} {h:g}\\,h", c, pw.values())
            block(f"{lab}, ${h:g}\\,$h", cells)
    try:
        seeds = list(V.perwindow_seeds("E2", "riyadh").values())
        block("E2-PPO", {"riyadh": _arm_cells("E2", seeds, sw_t["riyadh"], f"{len(seeds)} seeds")})
    except FileNotFoundError:
        L.append(r"E2-PPO & Riyadh & \multicolumn{8}{l}{not run} \\ \addlinespace")
    cells = {}
    for c in CITIES:
        (b,) = [r for r in V.read("CLV", c) if str(r.get("setback", "False")) == "False"]
        s = float(b["clv_s_pooled"]); best_att[c] = max(best_att.get(c, -1e9), s)
        cells[c] = [f"${float(b['therm_J']) * (1 - s / 100):.4f}$", f"${f(s)}${fit_mark(b.get('fit_status', 'oracle'))}",
                    NA, f"(${f(-float(b['clv_start_sav']), 1, True)}\\,\\%$)", f"${f(b['clv_dT_pooled'], 3, True)}$",
                    NA, NA, "best attained"]
    block("CLV", cells)
    cells = {c: [f"$\\ge{float(V.read('CLV', c)[0]['therm_J']) * (1 - Bstar[c] / 100):.4f}$",
                 f"$\\le{Bstar[c]:.1f}$", NA, NA, NA, NA, NA,
                 f"gap ${Bstar[c] - best_att[c]:.1f}$"] for c in CITIES}
    block(r"\emph{Bound} $B^{\ast}$", cells)
    L[-1:] = [r"\bottomrule"]
    notes = FIT_NOTE + " Bracket per city: lower end = best attained schedule at THERM's mean (CLV or any arm " \
        r"with $|\Delta\tilde T|\le0.002\,$K), upper end = provable bound $B^\ast$; " + \
        "; ".join(f"{CN[c]} $[{best_att[c]:.1f}, {Bstar[c]:.1f}]$" for c in CITIES) + "."
    if Ba_notes:
        notes += r" Arm-specific bounds $B_a$ differing from $B^\ast$ by $\ge0.1$ point: " + "; ".join(Ba_notes) + "."
    L.append(r"\multicolumn{10}{@{}p{\textwidth}@{}}{\footnotesize " + notes + r"} \\")
    L.append(r"\end{tabularx}")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ tab:sensitivity (Riyadh)
def _share(c_sw, fs, J):
    return f"${100 * c_sw * fs / J:.1f}$"


def tab_sensitivity(city="riyadh"):
    L = [r"\begin{tabularx}{\textwidth}{@{}Xrrrrr@{}}", r"\toprule",
         r"Setting & THERM on-command share (\%) & TUNED & Guard & MPC-$24\,$h & $B^\ast$ \\", r"\midrule"]
    t7 = {float(r["deadband"]): r for r in V.read("T7") if r["city"] == city}
    fs_therm = float(t7[1.0]["therm_fs"])          # THERM's actions do not depend on price or c_sw
    clv = [r for r in V.read("CLV", city) if str(r.get("setback", "False")) == "False"][0]
    mpc = {float(r["horizon_h"]): r for r in V.read("MPC", city)}
    cell = lambda r, k="s_pooled_eq": f"${f(r[k])}${fit_mark(r['fit_status'])}"
    # (a) tariff
    L.append(r"\multicolumn{6}{@{}l}{\emph{(a) Tariff, $c_{\mathrm{sw}}=" + f"{CFG.C_SW:g}" + r"\,$SAR}} \\")
    t1 = V.read("T1"); tb = {float(r["price"]): r for r in V.read("T4_BOUND") if r.get("city", city) == city}
    for tname in ("historical", "inforce", "y2027"):
        tu = [r for r in t1 if r["city"] == city and r["arm"] == "TUNED" and r["tariff"] == tname][0]
        pv = float(tu["price"])
        g = [r for r in t1 if r["city"] == city and r["arm"] == "guard" and r["tariff"] == tname]
        B = f"${Bstar_of(clv):.1f}$" if tname == "inforce" else f"${float(tb[pv]['bound_reported']):.1f}$"
        L.append(f"${pv:g}\\,$SAR/kWh & {_share(CFG.C_SW, fs_therm, float(tu['J_therm0_mean']))} & {cell(tu)} & "
                 f"{cell(g[0]) if g else NA} & {cell(mpc[24.0]) if tname == 'inforce' else NA} & {B} \\\\")
    # (b) c_sw
    L.append(r"\multicolumn{6}{@{}l}{\emph{(b) Charge per on-command, tariff in force}} \\")
    t5 = [r for r in V.read("T5") if r["city"] == city]
    b5 = {float(r["c_sw"]): r for r in V.read("T5_BOUND") if r.get("city", city) == city}
    for cs in sorted({float(r["c_sw"]) for r in t5}):
        tu = [r for r in t5 if abs(float(r["c_sw"]) - cs) < 1e-12 and r.get("arm", "TUNED") == "TUNED"][0]
        g = [r for r in t5 if abs(float(r["c_sw"]) - cs) < 1e-12 and r.get("arm") == "guard"]
        if abs(cs - CFG.C_SW) < 1e-12:
            m, B = mpc[24.0], f"${Bstar_of(clv):.1f}$"
        else:
            m = {float(r["horizon_h"]): r for r in V.read_stem(f"T21v3_csw{cs:g}_{city}")}[24.0]
            B = f"${float(b5[cs]['bound_reported']):.1f}$" if cs in b5 else NA
        L.append(f"${cs:g}\\,$SAR & {_share(cs, fs_therm, float(tu['J_therm0_mean']))} & {cell(tu)} & "
                 f"{cell(g[0]) if g else NA} & {cell(m)} & {B} \\\\")
    # (c) deadband
    L.append(r"\multicolumn{6}{@{}l}{\emph{(c) THERM deadband, band $[22,24]\,^\circ$C}} \\")
    for db, r in sorted(t7.items()):
        gd = (f"${f(r['guard_s_eq'])}${fit_mark(r['guard_fit_status'])}" if r.get("guard_s_eq") not in (None, "")
              else NA)
        L.append(f"${db:.2f}\\,^\\circ$C & {_share(CFG.C_SW, float(r['therm_fs']), float(r['J_therm0_mean']))} & "
                 f"{cell(r)} & {gd} & {NA} & {NA} \\\\")
    # (d) C_th
    L.append(r"\multicolumn{6}{@{}l}{\emph{(d) Thermal capacity, every arm refitted by Rule A4; MPC cell: $24\,$h ($1\,$h)}} \\")
    for cth, tg in sorted(V.CTH_TAGS.items()):
        t1c = V.read("T1", tag=tg)
        tu = [r for r in t1c if r["city"] == city and r["arm"] == "TUNED" and r["tariff"] == "inforce"][0]
        g = [r for r in t1c if r["city"] == city and r["arm"] == "guard" and r["tariff"] == "inforce"]
        mc = {float(r["horizon_h"]): r for r in V.read("MPC", city, tag=tg)}
        pw = V.perwindow("TUNED", city, tag=tg)
        sh = (_share(CFG.C_SW, mean(pw.values(), "fs_therm0"), float(tu["J_therm0_mean"]))
              if "fs_therm0" in next(iter(pw.values())) else
              (_share(CFG.C_SW, fs_therm, float(tu["J_therm0_mean"])) if tg == "" else NA))
        m1 = f" ({cell(mc[1.0])})" if 1.0 in mc else ""
        L.append(f"${int(cth):,}".replace(",", "{,}") + r"\,$kJ/K & " + f"{sh} & {cell(tu)} & {cell(g[0]) if g else NA} & "
                 f"{cell(mc[24.0])}{m1} & {f'${Bstar_of(clv):.1f}$' if tg == '' else NA} \\\\")
    L.append(r"\bottomrule")
    L.append(r"\multicolumn{6}{@{}p{\textwidth}@{}}{\footnotesize Pooled equalised saving $s$ (\%). " + FIT_NOTE
             + r" ---: not run for this setting.} \\")
    L.append(r"\end{tabularx}")
    return "\n".join(L) + "\n"


def Bstar_of(clv_row):
    return float(clv_row["bound_reported"])


# ------------------------------------------------------------------ tab:stats
def tab_stats():
    rows = V.read("STATS")
    fl1, fl3 = SV.p_floor(7, 1), SV.p_floor(7, 3)
    L = [r"\begin{table*}[t]", r"\centering",
         r"\caption{Pre-declared paired comparisons (Section~\ref{subsec:protocol}): per-window difference "
         r"of the equalised savings, $n=7$ held-out windows per city. Hodges--Lehmann estimate with its exact "
         r"$95.3\%$ interval, exact two-sided Wilcoxon signed-rank and sign tests; Holm within each "
         r"three-city family (F1--F4); F5 is a single-city family without Holm. At $n=7$ the smallest "
         f"exact two-sided $p$ is ${fl1:.3f}$ and the smallest Holm-adjusted $p$ in a three-member family is "
         f"${fl3:.3f}$. Pooled differences below ${SV.RESOLUTION_PTS:g}$ points are not resolved, whatever the test. "
         r"Generated from the v3 results files.}",
         r"\label{tab:stats}", r"\small",
         r"\begin{tabularx}{\textwidth}{@{}llXrrrrrl@{}}", r"\toprule",
         r"Family & Contrast & City & HL [95.3\% CI] (pts) & $+/-$ & $p_W$ & $p_{\mathrm{sign}}$ & $p_{\mathrm{adj}}$ & Pooled $\Delta s$ \\",
         r"\midrule"]
    last = None
    for r in rows:
        fam = r["family"] if r["family"] != last else ""
        con = r["contrast"] if r["family"] != last else ""
        last = r["family"]
        adj = f"${float(r['p_adj']):.3f}$" + ("" if r["holm"] == "True" else r"$^{\dagger}$")
        L.append(f"{fam} & {con} & {CN[r['city']]} & ${f(r['hl'], 1, True)}$ [${f(r['hl_lo'], 1, True)}$, "
                 f"${f(r['hl_hi'], 1, True)}$] & {r['n_pos']}/{r['n_neg']} & ${float(r['p_wilcoxon']):.3f}$ & "
                 f"${float(r['p_sign']):.3f}$ & {adj} & ${f(r['d_pooled'], 1, True)}$ ({r['resolution']}) \\\\")
    L += [r"\bottomrule",
          r"\multicolumn{9}{@{}l}{\footnotesize $^{\dagger}$single-city family, unadjusted.} \\",
          r"\end{tabularx}", r"\end{table*}"]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ table S-MZ
def _faces(topo):
    import mz_r3
    nm = {0: "N", 90: "E", 180: "S", 270: "W"}
    return ",".join("+".join(nm[a] for a in z) for z in mz_r3.AZ[topo])


def tab_s_mz():
    L = [r"\begin{tabularx}{\textwidth}{@{}llrrrXXrr@{}}", r"\toprule",
         r"Layout & Glazed faces & $\lambda_{ij}$ & THERM $J$ & TUNED $s$ & Guard $s$, HL vs TUNED & "
         r"MPC-MZ $s$, HL vs TUNED & Spread (K) & On/room-day \\", r"\midrule"]
    for topo, lijs in V.MZ_LAYOUTS:
        for lij in lijs:
            stem = V.MZ_RULES.format(topo=topo, lij=lij)
            sm = {r["arm"]: r for r in V.read_stem(stem)}
            pw = {}
            for r in V.read_stem(stem + "_perwindow"):
                pw.setdefault(r["arm"], {})[int(float(r["window"]))] = r
            mstem = V.MZ_MPC.format(topo=topo, lij=lij, h=V.MZ_MPC_H)
            msm = V.read_stem(mstem)[0]
            mpw = {int(float(r["window"])): r for r in V.read_stem(mstem + "_perwindow")}
            swt = {w: V.s_w(r) for w, r in pw["TUNED"].items()}
            cellhl = lambda s, p: (f"${f(s['s_pooled_eq'])}${fit_mark(s['fit_status'])} "
                                   + hl_vs({w: V.s_w(r) for w, r in p.items()}, swt))
            L.append(f"${topo.replace('x', r'{\times}')}$ & {_faces(topo)} & ${lij:g}$ & "
                     f"${float(sm['TUNED']['J_therm0_mean']):.4f}$ & "
                     f"${f(sm['TUNED']['s_pooled_eq'])}${fit_mark(sm['TUNED']['fit_status'])} & "
                     f"{cellhl(sm['guard'], pw['guard']) if 'guard' in sm else NA} & {cellhl(msm, mpw)} & "
                     f"${float(sm['TUNED']['T_zone_spread_mean']):.2f}$ & ${mean(pw['TUNED'].values(), 'fs_arm'):.2f}$ \\\\")
    L += [r"\bottomrule",
          r"\multicolumn{9}{@{}p{\textwidth}@{}}{\footnotesize Pooled equalised saving on the dwelling mean (\%); "
          r"spread = mean range of the room clipped means (TUNED); on-commands per room-day (TUNED). "
          + FIT_NOTE + r"} \\", r"\end{tabularx}"]
    return "\n".join(L) + "\n"


TABLES = dict(main=("tab_main.tex", tab_main), sensitivity=("tab_sensitivity.tex", tab_sensitivity),
              stats=("tab_stats.tex", tab_stats), smz=("tab_s_mz.tex", tab_s_mz))
INPUT_LINES = {
    "main": r"main.tex, Table tab:main: replace its tabularx with \input{tables/tab_main}",
    "sensitivity": r"main.tex, Table tab:sensitivity: replace its tabularx with \input{tables/tab_sensitivity}",
    "stats": r"main.tex, after the statistics paragraph (Sec. Results): \input{tables/tab_stats}",
    "smz": r"supplement.tex, Table S-MZ (tab:s-mz): replace its tabularx with \input{tables/tab_s_mz}",
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--only", default=",".join(TABLES))
    a = ap.parse_args(argv)
    paths = []
    for k in a.only.split(","):
        fn, gen = TABLES[k]
        paths.append(write(fn, gen(), a.out))
    print("\n".join(INPUT_LINES[k] for k in a.only.split(",")))
    return paths


if __name__ == "__main__":
    main()
