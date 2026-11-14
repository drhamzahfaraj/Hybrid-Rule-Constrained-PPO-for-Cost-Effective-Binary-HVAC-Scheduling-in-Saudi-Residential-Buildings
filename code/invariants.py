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
  H  deadband actuation     - the condition predicts the baseline's feasibility
  P  round-4 protocol (v3)  - fit_status, Rule C bracket, §2.1 metrics, optimiser constraints and
                              fallback, every arm s_a <= B_a, CLV certificate, grid convergence,
                              statistics re-derived (reads the v3 files named in v3_names)

A missing source file is a FAIL, never a skip. The run is saved to results/invariants_run.json
(n_checks, n_failed): the invariant count printed anywhere is read from that file.

Each test prints PASS or FAIL with the measured quantity. A FAIL is a stop, not
a warning: the number does not get reported.
"""
from __future__ import annotations
import sys, math, os
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
from hvac import Params, read_epw, vertical_irradiance
import results_table as RT
import config as CFG

FAILS = []
NCHECK = [0]


def check(name, ok, detail):
    NCHECK[0] += 1
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}: {detail}")
    if not ok:
        FAILS.append(name)
    return ok


# ---------------------------------------------------------------- A. physical
def a_physical():
    print("\nA. PHYSICAL SANITY")
    tdb, dni, dhi = read_epw("/home/claude/rbrl/riyadh.epw")
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


def h_deadband():
    print("\nH. DEADBAND ACTUATION CONDITION (necessary AND sufficient form)")
    import headroom as H, setback as S
    DB = (24.0 - 22.0) - 1.0        # THERM's deadband on the [22,24] band
    try:
        for dt, cth, want in ((0.25, 4800.0, True), (1.0, 4800.0, False)):
            H.DT = dt; S.DT = dt
            ov = H.Q_HVAC * dt * 3600 / (cth * 1e3)
            _, _, N = H.series("riyadh", 168, 121)
            occ = np.ones(N, bool)
            lo, hi = S.bands(occ, 22.0, 24.0, 18.0, 30.0)
            r = S.sim(S.therm(lo, hi), "riyadh", 1, cth, H.price_flat(N, CFG.PRICE),
                      lo, hi, occ, 168, 121, CFG.T0, c_sw=CFG.C_SW)
            holds = ov <= DB
            feasible = r["deg_h_occ"] <= 1e-9
            check(f"dt={dt*60:.0f}min: condition ({ov:.3f}<={DB:.2f}) predicts "
                  f"feasibility and the baseline agrees",
                  holds == feasible and holds == want,
                  f"condition {'holds' if holds else 'fails'}, "
                  f"baseline deg-h {r['deg_h_occ']:.3f}")
    finally:
        H.DT = 0.25; S.DT = 0.25


def f_tuned_vs_dp():
    price = RT.tariff("inforce")
    d = RT.dp_optimum("riyadh", 1, 4800.0, price)
    t = RT.tuned("riyadh", 1, 4800.0, price)
    gap = t[0]["J"] - d["J"]
    lam = RT.lam_of(1, "riyadh")
    dEdT = lam * 24 * 3600 / 1e6 / 3.6 / RT.COP_RATED
    f_closure({"switching": RT.C_SW * (t[0]["f_s"] - d["f_s"]),
               "mean temperature": price * dEdT * (d["T_mean"] - t[0]["T_mean"]),
               "residual": gap - RT.C_SW * (t[0]["f_s"] - d["f_s"])
                           - price * dEdT * (d["T_mean"] - t[0]["T_mean"])},
              gap, "tuned rule vs DP, Riyadh")


# ---------------------------------------------------------------- P. round-4 protocol on the v3 files
# (RULING_round4 F18.) The v1 classes I-O (rbrl_ppo.csv / T21_g1601 / T14 / T17 / T20 / T22 / T23 with
# figures typed into this file) are deleted: their sources are superseded and none of those figures
# is printed any more. Every check below reads a v3 file through v3_names; a MISSING file is a FAIL,
# never a skip. The only optional source is E2 (X3), which is reported as "not run".
import final_tables as _FT
OK_STATUS = set(_FT.FIT_STATUSES) - {"none"}        # config/final_tables: the §2.2 set + oracle, fixed


def _guard(name, fn):
    """run one check group; a missing/unreadable source is a FAIL with the file named."""
    try:
        fn()
    except (FileNotFoundError, LookupError, KeyError, ValueError) as e:
        check(name, False, f"{type(e).__name__}: {e}")


def _arms(city):
    """every causal arm with v3 per-window rows in this city: [(label, {w: row})]."""
    import v3_names as V
    out = [("TUNED", V.perwindow("TUNED", city)), ("guard", V.perwindow("guard", city))]
    for key, pre in (("MPC", "MPC"), ("MPC_PERS", "MPCp"), ("MPC_RULED", "MPCr")):
        for h in sorted({float(r["horizon_h"]) for r in V.read(key, city)}):
            lab = f"{pre}{h:g}"
            out.append((lab, V.perwindow(lab, city)))
    for seed, pw in sorted(V.perwindow_seeds("RBRL", city).items()):
        out.append((f"RBRL s{seed}", pw))
    out.append(("D1", V.perwindow("D1", city)))
    if city == "riyadh":
        try:
            for seed, pw in sorted(V.perwindow_seeds("E2", city).items()):
                out.append((f"E2 s{seed}", pw))
        except FileNotFoundError:
            print("  [note] E2 (X3) not run: no E2 rows checked")
    return out


def p_v3():
    import v3_names as V
    print("\nP. ROUND-4 PROTOCOL ON THE v3 FILES (fit_status, Rule C, §2.1, B_a, CLV, convergence)")
    STATS["max_bracket_gap"] = {}

    def p1():
        tabs = [("T1", None), ("T7", None), ("T5", None)] + \
               [(k, c) for c in V.CITIES for k in ("MPC", "MPC_PERS", "MPC_RULED", "MPC_GUARD", "RBRL", "D1", "CLV")]
        for k, c in tabs:
            rows = V.read(k, c)
            dflt = "oracle" if k == "CLV" else "<missing>"   # the CLV/bound summary is the oracle by definition
            bad = sorted({r.get("fit_status") or dflt for r in rows} - OK_STATUS)
            check(f"P1 {V.name(k, c)}: every row carries an admissible fit_status",
                  not bad, f"{len(rows)} rows; bad {bad}" if bad else f"{len(rows)} rows")
    _guard("P1 fit_status present", p1)

    for c in V.CITIES:
        def p2(c=c):
            arms = _arms(c)
            # §13: the THERM(delta) curve is not monotone, so gap = m[b] - m[a] is signed; test |gap|
            gaps = [abs(float(r["bracket_gap"])) for _, pw in arms for r in pw.values()]
            clipped = [(a, w) for a, pw in arms for w, r in pw.items() if str(r.get("eq_clipped")) == "True"]
            STATS["max_bracket_gap"][c] = max(gaps)
            check(f"P2 {c}: Rule C comparator bracketed in every window of every arm (no eq_clipped)",
                  not clipped and all(np.isfinite(g) and g >= 0 for g in gaps),
                  f"{len(arms)} arms; max bracket_gap {max(gaps):.4f} K; clipped {clipped}")
            for a, pw in arms:
                need = ("deg_h_over", "deg_h_cmd_under", "deg_h_ff_under", "T_end", "fallback_steps")
                miss = sorted({k for r in pw.values() for k in need if r.get(k) in (None, "")})
                check(f"P3 {c} {a}: §2.1 metrics present in every window", not miss, f"missing {miss}")
            # optimisers: hard constraints and no fallback (V-code-7: fallback_steps == 0 in every cell)
            for a, pw in arms:
                if a.startswith("MPC"):
                    over = sum(float(r["deg_h_over"]) for r in pw.values())
                    cmd = sum(float(r["deg_h_cmd_under"]) for r in pw.values())
                    fb = sum(int(float(r["fallback_steps"])) for r in pw.values())
                    # ruling §28: a persistence-forecast plan is checked against the forecast, so the
                    # realised cold-rule shortfall may be > 0; it is printed and bounded by 1e-3 K h
                    tol = 1e-3 if a.startswith("MPCp") else 1e-9
                    check(f"P4 {c} {a}: optimiser keeps both constraints and never falls back",
                          over <= 1e-9 and cmd <= tol and fb == 0,
                          f"deg_h_over {over:.4f}, deg_h_cmd_under {cmd:.4f}, fallback_steps {fb}")
            # B_a: every arm below the bound at its own mean (s_a <= B_a holds exactly)
            viol, n = [], 0
            for a, pw in arms:
                s_a = V.pooled(pw.values()); b_a, Ta = V.B_a(c, pw.values()); n += 1
                if s_a > b_a + 1e-9:
                    viol.append(f"{a}: s {s_a:.3f} > B_a {b_a:.3f} (T_a {Ta:.3f})")
            check(f"P10 {c}: every causal arm s_a <= B_a (bound at its own clipped mean)", not viol,
                  f"{n} arms; violations {viol}")
        _guard(f"P2-P10 {c}: v3 arm files", p2)

        def p7(c=c):
            (b,) = [r for r in V.read("CLV", c) if str(r.get("setback", "False")) == "False"]
            Bs = float(b["bound_reported"])
            rel = {k[len("bound_rel"):]: float(v) for k, v in b.items() if k.startswith("bound_rel") and v}
            unr = {k[len("bound_unrel"):]: float(v) for k, v in b.items() if k.startswith("bound_unrel") and v}
            common = sorted(set(rel) & set(unr))
            check(f"P7 {c}: relaxed bound >= unrelaxed (saving) at every common grid",
                  bool(common) and all(rel[g] >= unr[g] - 1e-6 for g in common),
                  ", ".join(f"{g}: {rel[g]:.3f} vs {unr[g]:.3f}" for g in common) or "no common grid")
            check(f"P8 {c}: CLV below the relaxed bound in every window (per-window certificate)",
                  str(b.get("clv_le_bound_all_windows")) == "True", str(b.get("clv_le_bound_all_windows")))
            check(f"P9 {c}: CLV <= B* pooled", float(b["clv_s_pooled"]) <= Bs + 1e-9,
                  f"CLV {float(b['clv_s_pooled']):.3f} vs B* {Bs:.1f}")
            # ruling §14: CLV is the best attained schedule no warmer than THERM (the 0.002 K match is
            # met in few windows); the bracket pairs raw CLV with B*, and Rule C CLV with B_CLV
            check(f"P9b {c}: CLV no warmer than THERM (pooled dT <= 0)",
                  float(b["clv_dT_pooled"]) <= 1e-9, f"{float(b['clv_dT_pooled']):+.4f} K")
            check(f"P9c {c}: raw CLV saving <= B*", float(b["clv_s_raw"]) <= Bs + 1e-9,
                  f"raw {float(b['clv_s_raw']):.3f} vs B* {Bs:.1f}")
            check(f"P9d {c}: Rule C CLV saving <= B_CLV", float(b["clv_s_pooled"]) <= float(b["clv_B_a"]) + 1e-9,
                  f"{float(b['clv_s_pooled']):.3f} vs B_CLV {float(b['clv_B_a']):.3f}")
        _guard(f"P7-P9 {c}: v3 CLV/bound file", p7)

        def p11(c=c):
            m8 = {float(r["horizon_h"]): float(r["s_pooled_eq"]) for r in V.read("MPC", c)
                  if r.get("forecast", "perfect") == "perfect"}
            conv = V.read("MPC_CONV", c)
            for r in conv:
                h = float(r["horizon_h"])
                if h not in m8:
                    raise LookupError(f"MPC {c} H={h:g}: no 801-point row to compare")
                # ruling §21.6: grid uncertainty <= 0.5 point, disclosed
                check(f"P11 {c} MPC {h:g} h: headline vs convergence grid |ds| <= 0.5 point",
                      abs(m8[h] - float(r["s_pooled_eq"])) <= 0.5,
                      f"{m8[h]:.3f} vs {float(r['s_pooled_eq']):.3f}")
        _guard(f"P11 {c}: v3 MPC convergence files", p11)

    def p12():
        import stats_v3 as SV
        rows = V.read("STATS")
        fresh = {(r["family"], r["city"]): r for r in SV.run()}
        for r in rows:
            k = (r["family"], r["city"])
            ok = k in fresh and all(abs(float(r[x]) - fresh[k][x]) < 1e-5 for x in ("hl", "hl_lo", "hl_hi", "p_adj"))
            check(f"P12 stats {k}: re-derives from the per-window files; CI contains HL; p >= floor",
                  ok and float(r["hl_lo"]) <= float(r["hl"]) <= float(r["hl_hi"])
                  and float(r["p_adj"]) >= float(r["p_floor"]) - 1e-12,
                  f"HL {float(r['hl']):+.2f} [{float(r['hl_lo']):+.2f},{float(r['hl_hi']):+.2f}] p_adj {float(r['p_adj']):.4f}")
        check("P12 stats: families F1-F4 present for all three cities",
              all((f, c) in fresh for f in ("F1", "F2", "F3", "F4") for c in V.CITIES), f"{len(rows)} rows")
    _guard("P12 stats_v3 table", p12)


STATS = {}
CLASSES = dict(A=a_physical, B=b_bounds, C=c_accounting, D=d_provenance, E=e_monotonic,
               F=f_tuned_vs_dp, G=g_feasibility, H=h_deadband, P=p_v3)


def main(argv=None):
    import argparse, rbrl_io as IO
    ap = argparse.ArgumentParser()
    ap.add_argument("--classes", default="".join(CLASSES), help="subset, e.g. P (a gate run needs all)")
    a = ap.parse_args(argv)
    FAILS.clear(); NCHECK[0] = 0; STATS.clear()
    print("=" * 72)
    print("INVARIANT GATE - run before any number is reported")
    print("=" * 72)
    for k in a.classes:
        CLASSES[k]()
    full = set(a.classes) == set(CLASSES)
    print("\n" + "=" * 72)
    # the saved run: the manuscript's invariant count is read from this file (F18), never typed
    IO.write_json("invariants_run", dict(classes=a.classes, full_gate=full, n_checks=NCHECK[0],
                                         n_failed=len(FAILS), failed=list(FAILS), **STATS))
    if FAILS:
        print(f"GATE FAILED - {len(FAILS)} of {NCHECK[0]} invariant(s) violated:")
        for f in FAILS: print(f"  - {f}")
        print("Do not report these numbers.")
        return 1
    print(f"GATE {'PASSED' if full else 'PASSED (partial: classes ' + a.classes + ')'} - "
          f"all {NCHECK[0]} invariants hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
