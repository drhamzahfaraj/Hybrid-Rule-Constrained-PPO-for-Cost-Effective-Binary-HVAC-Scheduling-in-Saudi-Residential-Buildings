#!/usr/bin/env python3
"""Re-derive every tabulated number from the v3 result files (RULING_round4 F18, job J17).

No result value is typed in this file (the v1/v2 version compared CSVs with figures copied from
the manuscript; those are deleted). Every check derives one v3 quantity from another:

  A  SUMMARY    every summary row re-derives from its per-window rows (pooled Rule C saving,
                starts, dT, J, §2.1 metric sums, T_end, fallback_steps)
  B  IDENTITY   at equal clipped mean the arm and its comparator use the same terminal-priced
                energy, so the cost saving is c_sw x on-commands avoided (the text's claim)
  C  CYCLING    T25v3 re-derives from the per-window files (cycling_energy)
  D  STATS      T20v3 re-derives from the per-window files (stats_v3)
  E  TABLES     every generated LaTeX table exists, carries no nan, and was generated from the
                CURRENT bytes of each input (sha in its provenance header == sha of the file now)
  F  TEXT       every \\input{tables/...} in main.tex / supplement.tex exists; the number of
                remaining \\pend{} placeholders is printed (with --final every one is a FAIL:
                0 printed values without a CURRENT source)

A missing file is a FAIL. Exit code is non-zero on any FAIL.
Usage: python3 verify_numbers.py [--final] [--tex DIR] [--tables DIR]
"""
from __future__ import annotations
import argparse, csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import rbrl_io as IO
import v3_names as V

FAILS: list[str] = []
NCHK = [0]
TEX = os.environ.get("RBRL_TEX_DIR", "/home/claude/v4")


def chk(label, ok, detail=""):
    NCHK[0] += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def guard(label, fn):
    try:
        fn()
    except (FileNotFoundError, LookupError, KeyError, ValueError) as e:
        chk(label, False, f"{type(e).__name__}: {e}")


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


TOL = 2e-4          # 6-digit CSV rounding, propagated through a pooled ratio (points / K / SAR)


def summary_matches(label, s, pw):
    """A: one summary row against its per-window rows."""
    pw = list(pw)
    der = dict(s_pooled_eq=V.pooled(pw),
               start_sav_eq=100 * (1 - sum(float(r["fs_arm"]) for r in pw) / sum(float(r["fs_eq"]) for r in pw)),
               dT_pooled=float(np.mean([float(r["dT_w"]) for r in pw])),
               J_arm_mean=float(np.mean([float(r["J_arm"]) for r in pw])),
               J_eq_mean=float(np.mean([float(r["J_eq"]) for r in pw])),
               deg_h_over=sum(float(r["deg_h_over"]) for r in pw),
               deg_h_cmd_under=sum(float(r["deg_h_cmd_under"]) for r in pw),
               deg_h_ff_under=sum(float(r["deg_h_ff_under"]) for r in pw),
               T_end_mean=float(np.mean([float(r["T_end"]) for r in pw])),
               fallback_steps=sum(int(float(r["fallback_steps"])) for r in pw))
    bad = {k: (s.get(k), round(v, 6)) for k, v in der.items()
           if s.get(k) in (None, "") or not close(s[k], v, TOL * max(1.0, abs(v)))}
    chk(f"A {label}: summary re-derives from its {len(pw)} per-window rows", not bad and len(pw) == 7,
        f"mismatch {bad}" if bad else f"s={der['s_pooled_eq']:.3f}")


def identity(label, pw):
    """B: equal terminal-priced energy, and s = c_sw x dN / J_eq (pooled)."""
    import cycling_energy as C
    pw = list(pw)
    vals = np.array([C.window_energy(r) for r in pw])
    Ea, Eq, fa, fq = vals.T
    rel = 1 - Ea.sum() / Eq.sum()
    cs = np.array([C._csw(r) for r in pw])
    s_sw = 100 * float(np.sum(cs * (fq - fa))) / sum(float(r["J_eq"]) for r in pw)
    s = V.pooled(pw)
    chk(f"B {label}: terminal-priced energy equals the comparator's; s = c_sw x on-commands avoided",
        abs(rel) < 1e-4 and abs(s - s_sw) < 0.05,
        f"energy rel {rel:+.1e}; s {s:.3f} vs c_sw*dN/J_eq {s_sw:.3f}")


def class_A_B():
    print("\nA/B. SUMMARIES RE-DERIVE; DUTY-CYCLE IDENTITY")
    for c in V.CITIES:
        for arm in ("TUNED", "guard"):
            guard(f"A/B {arm} {c}", lambda arm=arm, c=c: (
                summary_matches(f"{arm} {c}", V.summary(arm, c), V.perwindow(arm, c).values()),
                identity(f"{arm} {c}", V.perwindow(arm, c).values())))
        for key, pre in (("MPC", "MPC"), ("MPC_PERS", "MPCp"), ("MPC_RULED", "MPCr")):
            def mpc(key=key, pre=pre, c=c):
                for r in V.read(key, c):
                    lab = f"{pre}{float(r['horizon_h']):g}"
                    pw = V.perwindow(lab, c).values()
                    summary_matches(f"{lab} {c}", r, pw); identity(f"{lab} {c}", pw)
            guard(f"A/B MPC {key} {c}", mpc)

        def rbrl(c=c):
            seeds = V.perwindow_seeds("RBRL", c)
            for r in V.summary("RBRL", c):
                summary_matches(f"RBRL {c} seed {r['seed']}", r, seeds[str(r["seed"])].values())
        guard(f"A RBRL {c}", rbrl)

        def d1(c=c):
            best, pw = V.d1_selected(c)
            summary_matches(f"D1 {c} sigma {best['sigma']}", best, pw.values())
        guard(f"A D1 {c}", d1)


def class_C():
    print("\nC. CYCLING ENERGY (T25v3) RE-DERIVES")
    def run():
        import cycling_energy as C
        rows = V.read("CYCLING")
        for (c, arm) in sorted({(r["city"], r["arm"]) for r in rows}):
            fresh = {float(r["wh_per_start"]): r for r in C.arm_rows(arm, c)}
            got = [r for r in rows if r["city"] == c and r["arm"] == arm]
            bad = [r["wh_per_start"] for r in got
                   if not close(r["energy_saving_pct"], fresh[float(r["wh_per_start"])]["energy_saving_pct"], 1e-5)]
            chk(f"C {c} {arm}: per-start energy saving re-derives at every loss", not bad and len(got) == len(fresh),
                f"{len(got)} losses; mismatch at {bad}")
    guard("C T25v3", run)


def class_D():
    print("\nD. STATISTICS (T20v3) RE-DERIVE")
    def run():
        import stats_v3 as SV
        rows = V.read("STATS")
        fresh = {(r["family"], r["city"]): r for r in SV.run()}
        for r in rows:
            k = (r["family"], r["city"]); f = fresh.get(k)
            keys = ("hl", "hl_lo", "hl_hi", "p_wilcoxon", "p_sign", "p_adj", "d_pooled")
            chk(f"D {k}: HL, CI, p and pooled difference re-derive",
                f is not None and all(close(r[x], f[x], 1e-5) for x in keys) and r["resolution"] == f["resolution"],
                "" if f else "family row not reproducible")
        chk("D families: no re-derived row missing from T20v3", set(fresh) <= {(r["family"], r["city"]) for r in rows},
            f"missing {sorted(set(fresh) - {(r['family'], r['city']) for r in rows})}")
    guard("D T20v3", run)


def class_E(tables_dir):
    print("\nE. GENERATED TABLES ARE CURRENT")
    import gen_tables_v3 as G
    for fn, _ in G.TABLES.values():
        def run(fn=fn):
            p = os.path.join(tables_dir, fn)
            if not os.path.exists(p):
                raise FileNotFoundError(f"generated table missing: {p}")
            head, body = open(p).read().split("\n", 1)
            m = re.search(r"inputs=(\{.*\})\s*$", head)
            if not m:
                raise ValueError(f"{fn}: no provenance header")
            ins = json.loads(m.group(1))
            stale = []
            for rel, sha in ins.items():
                q = rel if os.path.isabs(rel) else os.path.normpath(os.path.join(IO.ROOT, rel))
                if not os.path.exists(q) or IO._sha(q) != sha:
                    stale.append(rel)
            chk(f"E {fn}: generated from the current bytes of all {len(ins)} inputs, no nan",
                ins and not stale and "nan" not in body.lower(), f"stale/missing {stale}" if stale else "")
        guard(f"E {fn}", run)


def class_F(tex, final):
    print("\nF. MANUSCRIPT: generated tables wired in, placeholders left")
    n_pend = 0
    for fn in ("main.tex", "supplement.tex"):
        p = os.path.join(tex, fn)
        if not chk(f"F {fn} present", os.path.exists(p), p):
            continue
        src = re.sub(r"(?<!\\)%.*", "", open(p).read())
        for t in re.findall(r"\\input\{(tables/[^}]+)\}", src):
            q = os.path.join(tex, t if t.endswith(".tex") else t + ".tex")
            chk(f"F {fn}: \\input{{{t}}} exists", os.path.exists(q), q)
        k = len(re.findall(r"\\pend\{", src))
        n_pend += k
        if final:
            chk(f"F {fn}: no \\pend placeholder left (every printed value has a CURRENT source)", k == 0, f"{k} left")
    print(f"  [info] \\pend placeholders remaining: {n_pend}")
    return n_pend


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true", help="G2: any remaining \\pend is a FAIL")
    ap.add_argument("--tex", default=TEX)
    ap.add_argument("--tables", default=os.environ.get("RBRL_TEX_TABLES", f"{TEX}/tables"))
    a = ap.parse_args(argv)
    FAILS.clear(); NCHK[0] = 0
    print("RE-DERIVATION CHECK on the v3 files\n")
    class_A_B(); class_C(); class_D(); class_E(a.tables); n_pend = class_F(a.tex, a.final)
    print("\n" + "=" * 70)
    if FAILS:
        print(f"{len(FAILS)} of {NCHK[0]} checks FAILED:")
        for f in FAILS:
            print(f"  - {f}")
        return 1
    print(f"All {NCHK[0]} checks passed" + ("" if a.final else f" ({n_pend} \\pend placeholders still open)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
