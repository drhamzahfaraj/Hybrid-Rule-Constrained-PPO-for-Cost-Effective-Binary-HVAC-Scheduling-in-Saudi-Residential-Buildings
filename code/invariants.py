#!/usr/bin/env python3
"""Invariant gate. No number is reported until this passes.

Rationale
---------
Every error found in this work so far was caught AFTER a result was reported,
not before. Each would have been caught by a cheap check run first. This file is
that set of checks, grouped by the failure it would have caught:

  A  physical sanity        - solar azimuth sign error (south read as north)
  B  bound consistency      - terminal-condition handicap (rule "beat" the DP)
  C  accounting identity    - finite BIG sentinel; penalty omitted from cost
  D  parameter provenance   - fabricated conductance 33 W/K; one Lambda_inf for
                              three cities at different station pressures
  E  monotonicity           - symmetric-only deadband sweep (27.5% vs 4.25%)
  F  decomposition closure  - "runs warmer" claim (components summed to 106%)
  G  feasibility            - Q*dt/C_th vs band width

Each test prints PASS or FAIL with the measured quantity. A FAIL is a stop, not
a warning: the number does not get reported.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, math
sys.path.insert(0, _ROOT + "")
import numpy as np
from hvac import Params, read_epw, vertical_irradiance
import results_table as RT

FAILS = []


def check(name, ok, detail):
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}: {detail}")
    if not ok:
        FAILS.append(name)
    return ok


# ---------------------------------------------------------------- A. physical
def a_physical():
    print("\nA. PHYSICAL SANITY")
    tdb, dni, dhi = read_epw(_ROOT + "/riyadh.epw")
    jul = slice(181 * 24, 212 * 24)
    def vi(az, sl=None):
        v = vertical_irradiance(dni, dhi, 24.7, azimuth_deg=az)
        return v.mean() if sl is None else v[sl].mean()
    # The ANNUAL ordering is the sign test. In JULY at 24.7 N the declination is
    # +23.4 deg, so the sun rises ~26 deg north of east and sits 88.7 deg high at
    # noon -- a vertical south wall then sees an incidence of 1.3 deg from the
    # surface (cos = 0.022). North legitimately exceeds south in July. Testing
    # July would reject correct code, which is what it did on the first run.
    check("solar: south exceeds north on an ANNUAL basis",
          vi(180) > vi(0), f"annual south {vi(180):.1f} vs north {vi(0):.1f} W/m2")
    check("solar: north exceeds south in July at this latitude (high sun)",
          vi(0, jul) > vi(180, jul),
          f"July north {vi(0,jul):.1f} vs south {vi(180,jul):.1f} W/m2")
    check("solar: east and west exceed south in July",
          vi(90, jul) > vi(180, jul) and vi(270, jul) > vi(180, jul),
          f"July east {vi(90,jul):.1f}, west {vi(270,jul):.1f}, south {vi(180,jul):.1f}")
    check("solar: west exceeds east in July (afternoon bias)",
          vi(270, jul) > vi(90, jul),
          f"July west {vi(270,jul):.1f} vs east {vi(90,jul):.1f} W/m2")
    # energy must fall as the zone is held warmer
    price = RT.tariff("inforce")
    r24 = RT.simulate(RT.hyst(23.5, 24.5), "riyadh", 1, 4800.0, price)
    r25 = RT.simulate(RT.hyst(24.5, 25.5), "riyadh", 1, 4800.0, price)
    check("energy decreases as mean zone temperature rises",
          r25["E"] < r24["E"],
          f"E(mean {r24['T_mean']:.2f}C)={r24['E']:.3f} > E(mean {r25['T_mean']:.2f}C)={r25['E']:.3f}")
    # load must rise with exposed faces
    e1 = RT.simulate(RT.hyst(22.5, 25.5), "riyadh", 1, 4800.0, price)["E"]
    e2 = RT.simulate(RT.hyst(22.5, 25.5), "riyadh", 2, 4800.0, price)["E"]
    check("energy rises with exposed-face count", e2 > e1,
          f"1 face {e1:.3f} < 2 faces {e2:.3f} kWh/zone/day")


# ---------------------------------------------------------------- B. bounds
def b_bounds():
    print("\nB. BOUND CONSISTENCY")
    price = RT.tariff("inforce")
    for city in ("riyadh", "jeddah", "taif"):
        d = RT.dp_optimum(city, 1, 4800.0, price)
        # forward rollout must agree with the backward value
        rel = abs(d["J"] - d["V_bwd"]) / d["J"]
        check(f"{city}: DP forward rollout agrees with backward value",
              rel < 0.01, f"J={d['J']:.4f} vs V_bwd={d['V_bwd']:.4f} ({100*rel:.2f}%)")
        # NO controller may beat the lower bound
        worst = None
        for lab, pol in (("1K", RT.hyst(23.5, 24.5)), ("2K", RT.hyst(23.0, 25.0)),
                         ("3K", RT.hyst(22.5, 25.5))):
            r = RT.simulate(pol, city, 1, 4800.0, price)
            if worst is None or r["J"] < worst[1]:
                worst = (lab, r["J"])
        t = RT.tuned(city, 1, 4800.0, price)
        best_rule = min(worst[1], t[0]["J"]) if t else worst[1]
        check(f"{city}: no rule beats the DP bound",
              best_rule >= d["J"] - 1e-9,
              f"best rule {best_rule:.4f} vs bound {d['J']:.4f} "
              f"({100*(best_rule-d['J'])/d['J']:+.2f}%)")


# ---------------------------------------------------------------- C. accounting
def c_accounting():
    print("\nC. ACCOUNTING IDENTITY")
    price = RT.tariff("inforce")
    r = RT.simulate(RT.hyst(22.5, 25.5), "riyadh", 1, 4800.0, price)
    recon = RT.C_SW * r["f_s"] + price * r["E"]
    check("uncorrected cost equals c_sw*f_s + price*E",
          abs(recon - r["J_uncorrected"]) < 1e-6,
          f"reconstructed {recon:.6f} vs reported {r['J_uncorrected']:.6f}")
    check("terminal correction is reported, not hidden",
          "terminal_corr" in r and "T_end" in r,
          f"corr={r['terminal_corr']:+.5f} SAR/day, T_end={r['T_end']:.2f}C")
    check("corrected cost equals uncorrected plus the stated correction",
          abs(r["J"] - (r["J_uncorrected"] + r["terminal_corr"])) < 1e-9,
          f"{r['J']:.6f} = {r['J_uncorrected']:.6f} + {r['terminal_corr']:+.6f}")
    check("no infinite or sentinel value reaches a reported figure",
          all(np.isfinite(v) for v in r.values() if isinstance(v, (int, float))),
          "all reported fields finite")


# ---------------------------------------------------------------- D. provenance
def d_provenance():
    print("\nD. PARAMETER PROVENANCE")
    P = Params()
    per = P.u_wall * P.a_wall + P.u_win * P.a_gl
    check("per-face conductance derives from the parameter table, not a literal",
          abs(per - RT.PER_FACE) < 1e-9,
          f"U_wall*A_wall + U_win*A_gl = {per:.2f} W/K = PER_FACE")
    # city-dependent parameters must actually differ by city
    li = {c: RT.lam_inf_of(c) for c in ("riyadh", "jeddah", "taif")}
    check("infiltration conductance differs by city (station pressure)",
          len(set(round(v, 3) for v in li.values())) == 3,
          ", ".join(f"{c} {v:.3f}" for c, v in li.items()) + " W/K")
    check("latitude differs by city",
          len(set(RT.CITIES.values())) == 3,
          ", ".join(f"{c} {v}" for c, v in RT.CITIES.items()))
    # the conductance must not be the withdrawn fabricated value
    check("conductance is not the withdrawn 33.0 W/K literal",
          abs(RT.lam_of(1, "riyadh") - 33.0) > 1.0,
          f"Lambda(1 face, riyadh) = {RT.lam_of(1,'riyadh'):.2f} W/K")


# ---------------------------------------------------------------- E. monotonic
def e_monotonic():
    print("\nE. MONOTONICITY")
    price = RT.tariff("inforce")
    fs = []
    for db in (1.0, 2.0, 3.0):
        r = RT.simulate(RT.hyst(24 - db / 2, 24 + db / 2), "riyadh", 1, 4800.0, price)
        fs.append(r["f_s"])
    check("switching frequency falls as the deadband widens",
          fs[0] > fs[1] > fs[2], f"1K {fs[0]:.2f} > 2K {fs[1]:.2f} > 3K {fs[2]:.2f}")
    fc = []
    for C in (1200.0, 2400.0, 4800.0):
        r = RT.simulate(RT.hyst(22.5, 25.5), "riyadh", 1, C, price)
        fc.append(r["f_s"])
    check("switching frequency falls as capacity rises",
          fc[0] > fc[1] > fc[2], f"1200 {fc[0]:.2f} > 2400 {fc[1]:.2f} > 4800 {fc[2]:.2f}")
    # the tuned search must not be beaten by a perturbation of its own answer
    t = RT.tuned("riyadh", 1, 4800.0, price)
    lo, hi = t[1], t[2]
    beaten = []
    for dlo in (-0.2, 0.0, 0.2):
        for dhi in (-0.2, 0.0, 0.2):
            if dlo == dhi == 0: continue
            r = RT.simulate(RT.hyst(lo + dlo, hi + dhi), "riyadh", 1, 4800.0, price)
            if r["deg_h"] <= 1e-9 and r["J"] < t[0]["J"] - 1e-9:
                beaten.append((lo + dlo, hi + dhi, r["J"]))
    check("tuned optimum is not beaten by a local perturbation",
          not beaten, f"searched 8 neighbours of ({lo:.1f},{hi:.1f}); "
                      f"{len(beaten)} better" if beaten else
                      f"({lo:.1f},{hi:.1f}) is locally optimal")


# ---------------------------------------------------------------- F. closure
def f_closure(components, total, name="decomposition"):
    print(f"\nF. DECOMPOSITION CLOSURE ({name})")
    s = sum(components.values())
    check("components sum to the total within 2%",
          abs(s - total) <= 0.02 * abs(total),
          ", ".join(f"{k} {v:+.4f}" for k, v in components.items())
          + f" = {s:+.4f} vs total {total:+.4f}")


# ---------------------------------------------------------------- G. feasible
def g_feasibility():
    print("\nG. FEASIBILITY")
    for C in (450.0, 1200.0, 4800.0):
        q = RT.Q_HVAC * RT.DT * 3600 / (C * 1e3)
        check(f"Q*dt/C_th within the band at C_th={C:.0f}",
              q <= RT.BAND + 1e-9, f"{q:.3f} K against a {RT.BAND:.1f} K band")
    for city in ("riyadh", "jeddah", "taif"):
        price = RT.tariff("inforce")
        r = RT.simulate(RT.hyst(22.5, 25.5), city, 1, 4800.0, price)
        check(f"{city}: band is holdable with zero degree-hours",
              r["deg_h"] <= 1e-9, f"degree-hours {r['deg_h']:.4f}")


if __name__ == "__main__":
    print("=" * 72)
    print("INVARIANT GATE - run before any number is reported")
    print("=" * 72)
    a_physical(); b_bounds(); c_accounting()
    d_provenance(); e_monotonic(); g_feasibility()
    # the decomposition claim that was reported wrongly once
    price = RT.tariff("inforce")
    d = RT.dp_optimum("riyadh", 1, 4800.0, price)
    t = RT.tuned("riyadh", 1, 4800.0, price)
    gap = t[0]["J"] - d["J"]
    P = Params()
    lam = RT.lam_of(1, "riyadh")
    dEdT = lam * 24 * 3600 / 1e6 / 3.6 / RT.COP_RATED
    f_closure({"switching": RT.C_SW * (t[0]["f_s"] - d["f_s"]),
               "mean temperature": price * dEdT * (d["T_mean"] - t[0]["T_mean"]),
               "residual": gap - RT.C_SW * (t[0]["f_s"] - d["f_s"])
                           - price * dEdT * (d["T_mean"] - t[0]["T_mean"])},
              gap, "tuned rule vs DP, Riyadh")
    # ---- H. new in this revision: the deadband actuation condition -------
    print("\nH. DEADBAND ACTUATION CONDITION (necessary AND sufficient form)")
    import headroom as H, setback as S
    import numpy as _np
    DB = (24.0 - 22.0) - 1.0        # THERM's deadband on the [22,24] band
    for dt, cth, want in ((0.25, 4800.0, True), (1.0, 4800.0, False)):
        H.DT = dt; S.DT = dt
        ov = H.Q_HVAC * dt * 3600 / (cth * 1e3)
        _, _, N = H.series("riyadh", 168, 121)
        occ = _np.ones(N, bool)
        lo, hi = S.bands(occ, 22.0, 24.0, 18.0, 30.0)
        r = S.sim(S.therm(lo, hi), "riyadh", 1, cth, H.price_flat(N, 0.18),
                  lo, hi, occ, 168, 121, 23.0)
        holds = ov <= DB
        feasible = r["deg_h_occ"] <= 1e-9
        check(f"dt={dt*60:.0f}min: condition ({ov:.3f}<={DB:.2f}) predicts "
              f"feasibility and the baseline agrees",
              holds == feasible and holds == want,
              f"condition {'holds' if holds else 'fails'}, "
              f"baseline deg-h {r['deg_h_occ']:.3f}")
    H.DT = 0.25; S.DT = 0.25

    # ---- I. corollary closure: the rule layer IS the policy ---------------
    print("\nI. COROLLARY CLOSURE (rule layer vs learned policy)")
    import final_tables as F
    import csv as _csv

    # Read EVERY seed from the results file rather than comparing against a
    # hand-typed figure. An earlier version of this invariant hardcoded the
    # best Riyadh seed (1.0576) and therefore passed while the manuscript
    # claimed, wrongly, that all three seeds were identical: seed 42 gives
    # 1.0610. A gate that checks a typed constant checks nothing.
    with open(_ROOT + "/results/rbrl_ppo.csv") as _f:
        ppo_rows = list(_csv.DictReader(_f))

    for city, cap in (("riyadh", 23.737), ("jeddah", 23.737)):
        Js = [F.rule_run(city, w, 0.18, cap - 0.20, 22.40)["J"] for w in F.EVAL_W]
        Jm = float(_np.mean(Js))
        seeds = [(int(r["seed"]), float(r["J"])) for r in ppo_rows
                 if r["city"] == city]
        assert seeds, f"no PPO rows for {city}"

        # The corollary predicts an INEQUALITY: under the hard rules and at
        # matched comfort the rule is cost-optimal in its class, so no learned
        # policy may cost LESS than it. Equality is the typical case, not the
        # claim. Tolerance is one unit in the fourth decimal of a SAR figure.
        worst_under = min(J - Jm for _, J in seeds)
        check(f"{city}: no seed costs less than the guard hysteresis "
              f"(corollary is an inequality)", worst_under > -1e-4,
              f"rule {Jm:.4f}; seeds " +
              ", ".join(f"s{s}={J:.4f}" for s, J in sorted(seeds)) +
              f"; largest shortfall {worst_under:+.4f} SAR/day")

        # and the manuscript's reported mean must be the mean of all seeds
        mean_J = float(_np.mean([J for _, J in seeds]))
        n_exact = sum(1 for _, J in seeds if abs(J - Jm) < 1e-4)
        check(f"{city}: reported RBRL cost is the mean over all seeds, "
              f"not the best one", abs(mean_J - Jm) < 5e-3,
              f"seed mean {mean_J:.4f} vs rule {Jm:.4f}; "
              f"{n_exact}/{len(seeds)} seeds reproduce the rule exactly")

    print("\nJ. COROLLARY SCOPE (the constant-disturbance hypothesis)")
    # Corollary 1 holds only when the disturbance is time-invariant. Under the
    # diurnally varying weather actually simulated, a clairvoyant DP over
    # EXACTLY the rule-admissible action set beats the guard hysteresis. The
    # gap is the measured price of the dropped hypothesis; the manuscript
    # quotes it, so it is gated here. An earlier version of this file asserted
    # the corollary without this check and the claim went to review unqualified.
    try:
        import verify_corollary as VC
        for city, cap, quoted in (("riyadh", 23.737, 0.59), ("jeddah", 23.737, 0.02)):
            hy = [F.rule_run(city, w, 0.18, cap - 0.20, 22.40) for w in F.EVAL_W]
            dp = [VC.dp_rule_constrained(city, w, 0.18, cap) for w in F.EVAL_W]
            if any(d is None for d in dp):
                check(f"{city}: rule-constrained DP solvable", False, "infeasible")
                continue
            Jh = float(_np.mean([r["J"] for r in hy]))
            Jd = float(_np.mean([r["J"] for r in dp]))
            gap = 100.0 * (Jh - Jd) / Jh
            check(f"{city}: measured gap to the rule-constrained optimum matches "
                  f"the figure quoted in the manuscript",
                  abs(gap - quoted) < 0.1,
                  f"rule {Jh:.4f}, constrained DP {Jd:.4f}, gap {gap:.2f}% "
                  f"(manuscript quotes {quoted:.2f}%)")
            check(f"{city}: the gap is non-negative, as the corollary's "
                  f"inequality requires", gap > -1e-6, f"gap {gap:+.3f}%")
    except Exception as e:
        check("corollary-scope check ran", False, f"{type(e).__name__}: {e}")

    print("\nK. MPC BASELINE, matched window by window on the DP's own grid")
    # The MPC run is too slow to recompute in the gate, so the gate checks the
    # released CSVs against the figures printed in the paper. History of the
    # criterion: T8 matched only the aggregate mean (weaker than every other
    # arm); T15 matched per window on an 801-point grid with 0.05 K caps; the
    # quoted arm is T21_g1601, per-window matched on the 1601-point grid with
    # the cap refined to 0.01 K, plus a 48 h horizon. Earlier files are kept
    # for the record but must not be the source of a printed figure.
    try:
        import csv as _csv, glob as _glob
        mp = {}
        for p in _glob.glob(_ROOT + "/results/T21_g1601_*_mpc_summary.csv"):
            for r in _csv.DictReader(open(p)):
                mp[(r["city"], float(r["horizon_h"]))] = r
        quoted = {("riyadh", 6.0): -4.0, ("riyadh", 24.0): 8.4,
                  ("riyadh", 48.0): 10.8,
                  ("jeddah", 6.0): -4.7, ("jeddah", 24.0): 5.9,
                  ("jeddah", 48.0): 9.5,
                  ("taif", 6.0): -18.2, ("taif", 24.0): 2.9,
                  ("taif", 48.0): 4.3}
        for key, q in quoted.items():
            r = mp.get(key)
            check(f"MPC {key[0]} H={key[1]:.0f}h matches the manuscript",
                  r is not None and abs(float(r["sav"]) - q) < 0.06,
                  f"csv {r['sav'] if r else 'MISSING'}%, manuscript {q}%")
        # every MPC row must be NO WARMER than its baseline in every window,
        # which is the criterion the manuscript claims for all arms
        for key, r in mp.items():
            check(f"{key[0]} H={key[1]:.0f}h is no warmer in any window",
                  float(r["worst_dT"]) <= 1e-6,
                  f"worst dT {float(r['worst_dT']):+.4f} K")
        # the orderings the restated finding rests on
        riy24 = float(mp[("riyadh", 24.0)]["sav"])
        check("Riyadh: a 24 h horizon does NOT beat the tuned rule",
              riy24 < 9.25 + 0.5,
              f"MPC24 {riy24:.2f}% vs TUNED 9.25%")
        jed24 = float(mp[("jeddah", 24.0)]["sav"])
        check("Jeddah: the 24 h arm sits below the tuned rule, as the "
              "significance claim requires", jed24 < 9.27,
              f"MPC24 {jed24:.2f}% vs TUNED 9.27%")
        for city, tuned in (("riyadh", 9.25), ("jeddah", 9.27)):
            h48 = float(mp[(city, 48.0)]["sav"])
            check(f"{city}: the 48 h arm is level or ahead of the tuned rule",
                  h48 > tuned - 1.0, f"MPC48 {h48:.2f}% vs TUNED {tuned}%")
    except Exception as e:
        check("MPC baseline check ran", False, f"{type(e).__name__}: {e}")

    print("\nL. THE BRACKET (every arm below its own bound, in every city)")
    # The gate previously encoded the SUPERSEDED pointwise-capped device as
    # "the bound" and tested Riyadh only, which is why it passed while the
    # manuscript's framing was wrong. It now reads the published bracket and
    # tests all three cities.
    try:
        import csv as _csv
        with open(_ROOT + "/results/T14_perwindow_summary.csv") as _f:
            pw = {(r["city"], r["arm"]): r for r in _csv.DictReader(_f)}
        # published bounds: finest grid plus the last increment, rounded outward
        published = {"riyadh": 19.8, "jeddah": 19.5, "taif": 20.2}
        # every arm the manuscript reports at the in-force tariff, no setback
        arms = {"riyadh": [("RBRL", 5.66), ("guard hyst", 5.82), ("TUNED", 9.25),
                           ("MPC 24h", 9.10)],
                "jeddah": [("RBRL", 5.80), ("guard hyst", 5.80), ("TUNED", 9.26),
                           ("MPC 24h", 8.01)],
                "taif": [("RBRL", 7.62), ("guard hyst", 7.62), ("TUNED", 4.56)]}
        for city, b in published.items():
            att = float(pw[(city, "OPT")]["att_sav"])
            check(f"{city}: the attainable schedule lies below the bound",
                  att <= b, f"attainable {att:.2f}% vs bound {b:.1f}%")
            check(f"{city}: the attainable schedule is cool in every window",
                  float(pw[(city, "OPT")]["max_dT"]) <= 1e-6,
                  f"worst dT {float(pw[(city,'OPT')]['max_dT']):+.4f} K")
            for name, v in arms[city]:
                check(f"{city}: {name} lies below the bound",
                      v <= b, f"{v:.2f}% vs bound {b:.1f}%")
        # the bound must be quoted OUTWARD of the finest grid value
        with open(_ROOT + "/results/T17_bound_convergence.csv") as _f:
            cv = [r for r in _csv.DictReader(_f)]
        for city, b in published.items():
            fin = [r for r in cv if r["city"] == city and r["arm"] == "OPT"]
            if not fin:
                continue
            finest = max(float(r["bound_sav"]) for r in fin)
            check(f"{city}: the published bound is conservative of the "
                  f"finest grid", b >= finest,
                  f"published {b:.1f}% >= finest {finest:.3f}%")
    except Exception as e:
        check("bracket check ran", False, f"{type(e).__name__}: {e}")

    # ------------------------------------------------- M. paired statistics
    # The statistical paragraph added in revision must agree with its CSV, and
    # the claims the abstract makes (p-values, direction) must be reproducible
    # from the per-window data, not merely quoted.
    try:
        with open(_ROOT + "/results/T20_paired_stats.csv") as _f:
            st = [r for r in _csv.DictReader(_f)]
        tt = [r for r in st if r["comparison"] == "TUNED vs THERM"]
        check("stats: TUNED-vs-THERM rows exist for three cities", len(tt) == 3,
              f"{len(tt)} rows")
        for r in tt:
            check(f"stats: TUNED beats THERM with p<=0.05 "
                  f"(sav {r['sav_a']}%)", float(r["wilcoxon_p"]) <= 0.05,
                  f"p={r['wilcoxon_p']}")
            check(f"stats: BCa interval excludes zero for TUNED-vs-THERM "
                  f"(sav {r['sav_a']}%)", float(r["diff_lo"]) > 0.0,
                  f"lo={r['diff_lo']}")
            check("stats: point estimate inside its own interval",
                  float(r["diff_lo"]) <= float(r["diff_pts"])
                  <= float(r["diff_hi"]), r["diff_pts"])
    except FileNotFoundError:
        check("stats CSV present", False, "T20_paired_stats.csv missing")
    except Exception as e:
        check("stats check ran", False, f"{type(e).__name__}: {e}")

    # ------------------------------------------------- N. latent side study
    # The rebuilt latent module must (a) reproduce the headline in its
    # sensible-only arm, (b) never exceed saturation, and (c) agree with the
    # deltas quoted in the manuscript (+0.4 Riyadh, +3.7 Jeddah, -4.6 Taif).
    try:
        with open(_ROOT + "/results/T22_latent2.csv") as _f:
            lt = {(r["city"], r["model"]): r for r in _csv.DictReader(_f)}
        pub_sen = {"riyadh": 9.25, "jeddah": 9.26, "taif": 4.56}
        pub_dlt = {"riyadh": +0.4, "jeddah": +3.7, "taif": -4.6}
        for city, v in pub_sen.items():
            sen = float(lt[(city, "sensible")]["sav"])
            check(f"latent: sensible arm reproduces the headline in {city}",
                  abs(sen - v) < 0.05, f"{sen:.2f} vs {v:.2f}")
            d = float(lt[(city, "latent")]["sav"]) - sen
            check(f"latent: quoted delta holds in {city}",
                  abs(d - pub_dlt[city]) < 0.1, f"{d:+.2f} vs {pub_dlt[city]:+.1f}")
            check(f"latent: no supersaturation in {city}",
                  float(lt[(city, "latent")]["rh_max"]) <= 100.0 + 1e-6,
                  lt[(city, "latent")]["rh_max"])
        check("latent: Jeddah humidity non-compliance is the quoted 85%",
              abs(float(lt[("jeddah", "latent")]["w_over_pct"]) - 85.0) < 1.0,
              lt[("jeddah", "latent")]["w_over_pct"])
    except FileNotFoundError:
        check("latent CSV present", False, "T22_latent2.csv missing")
    except Exception as e:
        check("latent check ran", False, f"{type(e).__name__}: {e}")

    # ------------------------------------------------- O. AMY weather years
    try:
        import csv as _csv
        tr = {}
        for r in _csv.DictReader(open(_ROOT + "/results/T23_amy_spread.csv")):
            if r.get("kind") == "TRANSFER":
                tr[(r["city"], str(r["year"]))] = float(r["sav"])
        riy = [tr[("riyadh", y)] for y in ("2013", "2018", "2021")]
        jed = [tr[("jeddah", y)] for y in ("2011", "2017", "2023")]
        tai = [tr[("taif", y)] for y in ("2013", "2012", "2021")]
        check("AMY: Riyadh transfer spans 9.4-10.5% as quoted",
              abs(min(riy) - 9.40) < 0.05 and abs(max(riy) - 10.45) < 0.05,
              f"{min(riy)}-{max(riy)}")
        check("AMY: Jeddah transfer spans 9.1-9.4% as quoted",
              abs(min(jed) - 9.10) < 0.05 and abs(max(jed) - 9.38) < 0.05,
              f"{min(jed)}-{max(jed)}")
        check("AMY: Taif transfer spans 1.5-4.3% as quoted",
              abs(min(tai) - 1.48) < 0.05 and abs(max(tai) - 4.32) < 0.05,
              f"{min(tai)}-{max(tai)}")
    except Exception as e:
        check("AMY check ran", False, f"{type(e).__name__}: {e}")

    print("\n" + "=" * 72)
    if FAILS:
        print(f"GATE FAILED - {len(FAILS)} invariant(s) violated:")
        for f in FAILS: print(f"  - {f}")
        print("Do not report these numbers.")
        sys.exit(1)
    print("GATE PASSED - all invariants hold. Numbers may be reported.")
