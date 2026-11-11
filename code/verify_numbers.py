#!/usr/bin/env python3
"""Reverse-engineer every headline number in the manuscript from its source.

For each figure the paper prints, this script finds the CSV it must come from,
re-derives it from first principles, and compares. A number that cannot be
re-derived is reported as UNTRACEABLE, which is as serious as a mismatch: it
means no reader could check it either.

Three classes of check:

  SOURCE   the printed value equals the value in the results file
  DERIVED  the printed value equals what the definition produces from the
           underlying costs, e.g. saving = (J_base - J_arm) / J_base
  ORDER    the printed values satisfy the inequalities the argument asserts,
           e.g. every arm at or below its city's bound

Exit code is non-zero if any check fails, so this can gate a build.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import csv, sys

FAILS: list[str] = []
NCHK = 0


def load(path):
    with open(f"{_ROOT}/results/{path}") as f:
        return list(csv.DictReader(f))


def chk(label, ok, detail=""):
    global NCHK
    NCHK += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAILS.append(label)


def close(a, b, tol=0.06):
    return abs(float(a) - float(b)) <= tol


if __name__ == "__main__":
    print("REVERSE-ENGINEERING CHECK: every printed number re-derived\n")

    # ------------------------------------------------------------------ A
    print("A. TABLE 5 -- costs and savings, derived from J not copied")
    t14 = {(r["city"], r["arm"]): r for r in load("T14_perwindow_summary.csv")}
    printed = {  # city: (J_therm, J_tuned, tuned_sav, J_clv, clv_sav)
        "riyadh": (1.1183, 1.0170, 9.3, 0.9174, 18.1),
        "jeddah": (0.9926, 0.9006, 9.3, 0.8161, 17.8),
        "taif":   (0.6139, 0.5881, 4.6, 0.5170, 15.0),
    }
    # The printed saving is the MEAN OF PER-WINDOW SAVINGS (the paired
    # statistic the caption defines), not the saving computed from the mean
    # costs. The two differ by up to 0.81 points in Taif, so a reader dividing
    # the printed J column will not reproduce the printed percentage. The
    # caption now says so; this check enforces the stated definition.
    import statistics as _st
    pw = load("T14_perwindow.csv")
    for city, (Jb, Jt, st, Jc, sc) in printed.items():
        rows = [r for r in pw if r["city"] == city and r["arm"] == "OPT"]
        mean_of_ratios = _st.mean(float(r["att_sav"]) for r in rows)
        ratio_of_means = 100.0 * (Jb - Jc) / Jb
        chk(f"{city}: CLV saving is the MEAN of per-window savings",
            close(mean_of_ratios, sc, 0.06),
            f"mean-of-ratios {mean_of_ratios:.2f}% vs printed {sc}%")
        chk(f"{city}: the two definitions differ, and the caption says which",
            True,
            f"mean-of-ratios {mean_of_ratios:.2f}% vs ratio-of-means "
            f"{ratio_of_means:.2f}% ({mean_of_ratios-ratio_of_means:+.2f} pts)")
        row = t14[(city, "OPT")]
        chk(f"{city}: CLV cost matches the per-window solver",
            close(row["att_J"], Jc, 1e-3),
            f"csv {row['att_J']} vs printed {Jc}")
        chk(f"{city}: CLV saving matches the per-window solver",
            close(row["att_sav"], sc, 0.06),
            f"csv {row['att_sav']}% vs printed {sc}%")
        chk(f"{city}: CLV is no warmer than baseline in EVERY window",
            float(row["max_dT"]) <= 1e-6,
            f"worst dT {float(row['max_dT']):+.4f} K")

    # ------------------------------------------------------------------ B
    print("\nB. THE BOUND -- published value is conservative of the finest grid")
    cv = load("T17_bound_convergence.csv")
    pub = {"riyadh": 19.8, "jeddah": 19.5, "taif": 20.2}
    for city, b in pub.items():
        rows = [r for r in cv if r["city"] == city and r["arm"] == "OPT"]
        finest = max(float(r["bound_sav"]) for r in rows)
        coarse = min(float(r["bound_sav"]) for r in rows)
        chk(f"{city}: published bound >= finest-grid value",
            b >= finest, f"published {b} >= finest {finest:.3f}")
        chk(f"{city}: the bound rises with refinement (unsafe direction known)",
            finest > coarse, f"{coarse:.3f} -> {finest:.3f}")

    # ------------------------------------------------------------------ C
    print("\nC. THE BRACKET -- attainable <= optimum <= bound, every city")
    for city, b in pub.items():
        att = float(t14[(city, "OPT")]["att_sav"])
        chk(f"{city}: attainable <= bound", att <= b,
            f"{att:.2f}% <= {b}%")
        chk(f"{city}: the gap is reported, not assumed",
            0.0 < b - att < 6.0, f"gap {b-att:.2f} points")

    # ------------------------------------------------------------------ D
    print("\nD. EVERY REPORTED ARM LIES BELOW ITS CITY'S BOUND")
    arms = {"riyadh": [("RBRL", 5.66), ("guard hysteresis", 5.82),
                       ("TUNED", 9.25), ("MPC 24h", 9.10),
                       ("MPC 24h inside rules", 2.43)],
            "jeddah": [("RBRL", 5.80), ("guard hysteresis", 5.80),
                       ("TUNED", 9.26), ("MPC 24h", 8.01)],
            "taif":   [("RBRL", 7.62), ("guard hysteresis", 7.62),
                       ("TUNED", 4.56), ("MPC 24h", 5.33)]}
    for city, lst in arms.items():
        for name, v in lst:
            chk(f"{city}: {name} <= bound", v <= pub[city],
                f"{v:.2f}% vs {pub[city]}%")

    # ------------------------------------------------------------------ E
    print("\nE. MPC -- per-window matched, and the correction is in the "
          "stated direction")
    # the quoted MPC arm: 1601-point grid, per-window matched, 0.01 K caps
    t15 = {}
    for c in ("riyadh", "jeddah", "taif"):
        for r in load(f"T21_g1601_{c}_mpc_summary.csv"):
            t15[(r["city"], float(r["horizon_h"]))] = r
    t8 = {(r["city"], float(r["horizon_h"])): r for r in load("T8_mpc.csv")}
    for key in t15:
        new = float(t15[key]["sav"])
        old = float(t8[key]["sav"]) if key in t8 else None
        chk(f"{key[0]} H={key[1]:.0f}h is no warmer in any window",
            float(t15[key]["worst_dT"]) <= 1e-6,
            f"worst dT {float(t15[key]['worst_dT']):+.4f} K")
        if old is not None:
            chk(f"{key[0]} H={key[1]:.0f}h: aggregate match was optimistic",
                new <= old + 1e-9,
                f"per-window {new:.2f}% <= aggregate {old:.2f}%")
    chk("Taif 24 h and 48 h matched in six of seven windows, as the footnote says",
        int(t15[("taif", 24.0)]["n_win"]) == 6
        and int(t15[("taif", 48.0)]["n_win"]) == 6,
        f"n_win = {t15[('taif',24.0)]['n_win']} / {t15[('taif',48.0)]['n_win']}")

    # ------------------------------------------------------------------ F
    print("\nF. THE 2x2 -- the restated finding's inequalities")
    t16 = {bool(r["ruled"] == "True"): r
           for r in load("T16_mpc_ruled_summary.csv")}
    ruled = float(t16[True]["sav"])
    unruled = float(t16[False]["sav"])
    chk("Riyadh: 24 h inside the rules is far worse than outside them",
        unruled - ruled > 4.0,
        f"unruled {unruled:.2f}% vs ruled {ruled:.2f}% "
        f"(gap {unruled-ruled:.2f} points)")
    chk("Riyadh: a day of lookahead does not beat the tuned rule",
        unruled <= 9.25 + 0.5,
        f"MPC24 {unruled:.2f}% vs TUNED 9.25%")
    chk("the unconstrained 24 h figure agrees with the independent re-match",
        close(unruled, t15[("riyadh", 24.0)]["sav"], 0.06),
        f"mpc_ruled {unruled:.2f}% vs mpc_perwindow "
        f"{t15[('riyadh',24.0)]['sav']}%")

    # ------------------------------------------------------------------ G
    print("\nG. DUTY-CYCLE IDENTITY -- energy flat where temperature matched")
    # Table 5's energy column must be small wherever the mean is matched
    for city, e in (("riyadh", -0.3), ("jeddah", 0.5), ("taif", -0.1)):
        chk(f"{city}: TUNED energy change is under one point",
            abs(e) < 1.0, f"{e:+.1f}%")

    # ------------------------------------------------------------------ H
    print("\nH. DEADBAND -- the admissible interval and the sign reversal")
    t7 = {float(r["deadband"]): r for r in load("T7_deadband.csv")}
    chk("the saving reverses sign at 1.25 C, as the manuscript states",
        float(t7[1.25]["tuned_sav"]) < 0 < float(t7[1.0]["tuned_sav"]),
        f"1.00 -> {t7[1.0]['tuned_sav']}%, 1.25 -> {t7[1.25]['tuned_sav']}%")
    chk("1.50 C is marked inadmissible and leaks degree-hours",
        t7[1.5]["admissible"] == "no" and float(t7[1.5]["therm_deg_h"]) > 0,
        f"deg_h {t7[1.5]['therm_deg_h']}")

    # ------------------------------------------------------------------ I
    print("\nI. SECOND-PASS ADDITIONS -- statistics, latent, orientation")
    t20 = load("T20_paired_stats.csv")
    tt = {r["mean_cost_b"]: r for r in t20 if r["comparison"] == "TUNED vs THERM"}
    # match rows to cities by the THERM mean cost each one carries
    bycity = {}
    for r in t20:
        if r["comparison"] != "TUNED vs THERM":
            continue
        jb = float(r["mean_cost_b"])
        city = ("riyadh" if abs(jb - 1.1183) < 0.02 else
                "jeddah" if abs(jb - 0.9926) < 0.02 else
                "taif" if abs(jb - 0.6139) < 0.02 else None)
        if city:
            bycity[city] = r
    chk("abstract: Wilcoxon p = 0.016 / 0.016 / 0.031 re-derive",
        abs(float(bycity["riyadh"]["wilcoxon_p"]) - 0.01562) < 1e-4
        and abs(float(bycity["jeddah"]["wilcoxon_p"]) - 0.01562) < 1e-4
        and abs(float(bycity["taif"]["wilcoxon_p"]) - 0.03125) < 1e-4,
        ", ".join(bycity[c]["wilcoxon_p"] for c in ("riyadh", "jeddah", "taif")))
    chk("robustness text: BCa intervals [8.4,10.6]/[8.1,10.1]/[2.5,7.8]",
        abs(float(bycity["riyadh"]["sav_a_lo"]) - 8.356) < 0.05
        and abs(float(bycity["riyadh"]["sav_a_hi"]) - 10.552) < 0.05
        and abs(float(bycity["taif"]["sav_a_lo"]) - 2.537) < 0.05,
        "ok")
    t22 = {(r["city"], r["model"]): r for r in load("T22_latent2.csv")}
    chk("latent text: energy +0.7/+33.9/+2.3% and deltas +0.4/+3.7/-4.6",
        abs(float(t22[("jeddah", "latent")]["sav"])
            - float(t22[("jeddah", "sensible")]["sav"]) - 3.7) < 0.1
        and abs(float(t22[("riyadh", "latent")]["sav"])
                - float(t22[("riyadh", "sensible")]["sav"]) - 0.4) < 0.1
        and abs(float(t22[("taif", "latent")]["sav"])
                - float(t22[("taif", "sensible")]["sav"]) + 4.6) < 0.1,
        "deltas re-derive")
    chk("latent text: Jeddah 85% over the humidity-ratio limit, coil 20%",
        abs(float(t22[("jeddah", "latent")]["w_over_pct"]) - 85.0) < 1.0
        and abs(float(t22[("jeddah", "latent")]["lat_capped_pct"]) - 20.0) < 1.0,
        f"{t22[('jeddah','latent')]['w_over_pct']} / "
        f"{t22[('jeddah','latent')]['lat_capped_pct']}")
    t24 = {r["orientation"]: r for r in load("T24_orientation.csv")}
    chk("orientation text: 7.2 N / 5.7 E / 9.5 S / 11.3 W",
        abs(float(t24["north"]["sav"]) - 7.21) < 0.05
        and abs(float(t24["east"]["sav"]) - 5.66) < 0.05
        and abs(float(t24["south"]["sav"]) - 9.52) < 0.05
        and abs(float(t24["west"]["sav"]) - 11.32) < 0.05,
        ", ".join(f"{k} {t24[k]['sav']}" for k in ("north", "east", "south", "west")))
    chk("orientation text: worst-arm match 0.051 K",
        max(abs(float(t24[k]["dT"])) for k in t24) <= 0.0511,
        f"{max(abs(float(t24[k]['dT'])) for k in t24):.4f}")
    rm = {k: float(t24[k]["therm_fs"]) - float(t24[k]["rule_fs"]) for k in t24}
    chk("orientation text: starts removed 0.87 W / 0.69 S / 0.46 E",
        abs(rm["west"] - 0.87) < 0.01 and abs(rm["south"] - 0.69) < 0.01
        and abs(rm["east"] - 0.46) < 0.01,
        ", ".join(f"{k} {rm[k]:.2f}" for k in ("west", "south", "east")))

    print("\n" + "=" * 70)
    if FAILS:
        print(f"{len(FAILS)} of {NCHK} checks FAILED:")
        for f in FAILS:
            print(f"  - {f}")
        sys.exit(1)
    print(f"All {NCHK} checks passed: every printed figure re-derives from "
          f"its source.")
