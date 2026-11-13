#!/usr/bin/env python3
"""Round-4 paired statistics, pre-declared (RULING_round4 §2.4, §12.7; F17, job J17).

Unit    per-window difference of the equalised savings of two arms on the same 7 held-out
        windows, d_w = s_w(A) - s_w(B), s_w = 1 - J_arm,w / J_THERM(delta_w),w (each arm against
        its own Rule C comparator). Contrast "A vs B" reports A - B. RBRL/E2 enter as the
        per-window seed mean.
Tests   exact two-sided Wilcoxon signed-rank (full enumeration of the 2^n sign vectors over the
        ranks of the non-zero |d|, mid-ranks for ties), exact two-sided sign test (binomial), and the
        exact Hodges-Lehmann estimate with its distribution-free CI: the k-th smallest and largest of
        the n(n+1)/2 Walsh averages, k from the exact signed-rank null (n = 7: 3rd of 28,
        coverage 1 - 2*3/128 = 95.3 %). No bootstrap, no BCa.
Families (pre-declared; one contrast x cities; Holm within each 3-city family):
        F1 TUNED vs THERM, F2 MPC-24 (perfect) vs TUNED, F3 MPC-24 (persistence) vs TUNED,
        F4 guard vs TUNED (price of the guarantee); F5 E2-PPO vs guard, Riyadh only, a single-city
        family WITHOUT Holm (§12.7). F5 is written only if X3 ran (its files exist).
Floors  n = 7: the smallest exact two-sided p is 2/128 = 0.0156; the smallest Holm-adjusted p in a
        3-member family is 3 x 0.0156 = 0.047 (column p_floor, printed by the table).
Reading the HL estimate and CI lead; p is secondary. `unanimous` is True only at 7/7 (never write
        "significantly" for 6/7). Resolution rule: a pooled difference |s_A - s_B| < 3 points is
        "not resolved", whatever the test says (column resolution).

Matches R1_methods.md's recomputation method (exact Wilcoxon, sign, Holm and exact HL CI from the
per-window CSVs) on unchanged rows: tests/test_stats_v3.py reproduces T20v2 (Taif TUNED-THERM:
HL 4.18 [2.99, 5.44]).

Usage:  python3 stats_v3.py            -> results/T20v3_paired_stats.csv
"""
from __future__ import annotations
import itertools, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats as _st
import rbrl_io as IO
import v3_names as V

ALPHA = 0.05
RESOLUTION_PTS = 3.0
ZERO = 1e-12

# (family, A, B, cities, holm). B None = THERM (d_w = s_w(A), since THERM(delta) vs itself is 0).
FAMILIES = (
    ("F1", "TUNED", None, V.CITIES, True),
    ("F2", "MPC24", "TUNED", V.CITIES, True),
    ("F3", "MPCp24", "TUNED", V.CITIES, True),
    ("F4", "guard", "TUNED", V.CITIES, True),
    ("F5", "E2", "guard", ("riyadh",), False),
)
LABEL = {"TUNED": "TUNED", "MPC24": "MPC-24 (perfect)", "MPCp24": "MPC-24 (persistence)",
         "guard": "guard", "E2": "E2-PPO", None: "THERM"}
OPTIONAL = {"F5"}                    # only if X3 (E2) ran


# ------------------------------------------------------------------ exact procedures
def _signed_rank_null(n):
    """counts of T+ = 0..n(n+1)/2 over the 2^n equally likely sign vectors (no ties)."""
    counts = np.zeros(n * (n + 1) // 2 + 1)
    for signs in itertools.product((0, 1), repeat=n):
        counts[sum(i + 1 for i in range(n) if signs[i])] += 1
    return counts


def wilcoxon_crit(n, alpha=ALPHA):
    """largest k with P(T+ <= k) <= alpha/2 under H0 (exact); returns (k, coverage of the CI)."""
    counts = _signed_rank_null(n)
    cdf = np.cumsum(counts) / counts.sum()
    ok = np.where(cdf <= alpha / 2)[0]
    if not len(ok):
        return -1, 1.0
    k = int(ok.max())
    return k, float(1 - 2 * cdf[k])


def hl_ci(d, alpha=ALPHA):
    """exact Hodges-Lehmann estimate and CI: (hl, lo, hi, coverage). n = 7: walsh[2], walsh[25]."""
    d = np.asarray(d, float); n = len(d)
    walsh = np.sort([(d[i] + d[j]) / 2 for i in range(n) for j in range(i, n)])
    k, cov = wilcoxon_crit(n, alpha)
    hl = float(np.median(walsh))
    if k < 0:
        return hl, float("nan"), float("nan"), cov
    return hl, float(walsh[k]), float(walsh[len(walsh) - 1 - k]), cov


def wilcoxon_exact(d):
    """exact two-sided signed-rank p by enumeration; zeros dropped (Wilcoxon), ties mid-ranked.
    p = P(|T+ - E T+| >= |t_obs - E T+|) under the 2^m equally likely sign vectors."""
    d = np.asarray(d, float); d = d[np.abs(d) > ZERO]
    m = len(d)
    if m == 0:
        return 1.0
    r = _st.rankdata(np.abs(d))
    t_obs = float(r[d > 0].sum()); mu = float(r.sum()) / 2.0
    dev = abs(t_obs - mu) - 1e-9
    hit = 0
    for signs in itertools.product((False, True), repeat=m):
        t = sum(ri for ri, s in zip(r, signs) if s)
        hit += abs(t - mu) >= dev
    return min(1.0, hit / 2.0 ** m)


def sign_exact(d):
    d = np.asarray(d, float); d = d[np.abs(d) > ZERO]
    if len(d) == 0:
        return 1.0
    return float(_st.binomtest(int((d > 0).sum()), len(d), 0.5).pvalue)


def holm(ps):
    ps = np.asarray(ps, float)
    idx = np.argsort(ps, kind="stable"); m = len(ps); adj = np.empty(m); run = 0.0
    for r, i in enumerate(idx):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


def p_floor(n, m):
    """smallest attainable (Holm-adjusted, family size m) exact two-sided Wilcoxon p at n."""
    return min(1.0, m * 2.0 / 2.0 ** n)


# ------------------------------------------------------------------ data
def arm_sw(arm, city, tag=""):
    """({window: s_w}, pooled s, fit_status) of an arm; seeded arms as per-window seed means and
    the mean of the per-seed pooled savings."""
    if arm in ("RBRL", "E2"):
        seeds = V.perwindow_seeds(arm, city, tag)
        fit = sorted({r.get("fit_status", "") for v in seeds.values() for r in v.values()})
        return V.seed_mean_sw(seeds), float(np.mean([V.pooled(v.values()) for v in seeds.values()])), "/".join(fit)
    pw = V.perwindow(arm, city, tag)
    fit = sorted({r.get("fit_status", "") for r in pw.values()})
    return {w: V.s_w(r) for w, r in pw.items()}, V.pooled(pw.values()), "/".join(fit)


def contrast(sa, sb, pa, pb):
    """one city's row from per-window savings {w: s} of A and B (sb None = THERM)."""
    ws = sorted(sa) if sb is None else sorted(set(sa) & set(sb))
    if sb is not None and set(sa) != set(sb):
        raise ValueError(f"windows differ: {sorted(sa)} vs {sorted(sb)}")
    d = np.array([sa[w] - (0.0 if sb is None else sb[w]) for w in ws])
    hl, lo, hi, cov = hl_ci(d)
    npos, nneg = int((d > ZERO).sum()), int((d < -ZERO).sum())
    dpool = pa - (0.0 if sb is None else pb)
    return dict(n=len(d), hl=hl, hl_lo=lo, hl_hi=hi, hl_coverage=cov, s_pooled_a=pa,
                s_pooled_b=0.0 if sb is None else pb, d_pooled=dpool, mean_diff=float(d.mean()),
                n_pos=npos, n_neg=nneg, unanimous=bool(npos == len(d) or nneg == len(d)),
                p_wilcoxon=wilcoxon_exact(d), p_sign=sign_exact(d),
                resolution="resolved" if abs(dpool) >= RESOLUTION_PTS else "not resolved")


def family_rows(fam, a, b, cities, use_holm, tag=""):
    block = []
    for c in cities:
        sa, pa, fa = arm_sw(a, c, tag)
        sb, pb, fb = (None, 0.0, "") if b is None else arm_sw(b, c, tag)
        row = dict(family=fam, contrast=f"{LABEL[a]} vs {LABEL[b]}", arm_a=a, arm_b=b or "THERM",
                   city=c, fit_status_a=fa, fit_status_b=fb or "-", **contrast(sa, sb, pa, pb))
        block.append(row)
    m = len(block)
    adj = holm([r["p_wilcoxon"] for r in block]) if use_holm else [r["p_wilcoxon"] for r in block]
    for r, p in zip(block, adj):
        r.update(holm=bool(use_holm), family_size=m, p_adj=float(p),
                 p_floor=p_floor(r["n"], m if use_holm else 1),
                 at_floor=bool(abs(p - p_floor(r["n"], m if use_holm else 1)) < 1e-12))
    return block


def run(tag=""):
    rows = []
    for fam, a, b, cities, use_holm in FAMILIES:
        try:
            rows += family_rows(fam, a, b, cities, use_holm, tag)
        except FileNotFoundError as e:
            if fam in OPTIONAL:
                print(f"{fam}: not run ({e}); reported as 'not run'", flush=True)
                continue
            raise
    return rows


def main(argv=None):
    rows = run()
    p = IO.write_csv(V.name("STATS"), rows, ndigits=6)
    for r in rows:
        print(f"{r['family']} {r['contrast']:34s} {r['city']:7s} HL={r['hl']:+.2f} "
              f"[{r['hl_lo']:+.2f},{r['hl_hi']:+.2f}] ({r['hl_coverage']:.3f})  +{r['n_pos']}/-{r['n_neg']}  "
              f"pW={r['p_wilcoxon']:.4f} p_adj={r['p_adj']:.4f} (floor {r['p_floor']:.3f})  "
              f"psign={r['p_sign']:.4f}  d_pooled={r['d_pooled']:+.2f} {r['resolution']}")
    print(f"n = 7 floor: exact two-sided p >= {p_floor(7, 1):.4f}; Holm within a 3-city family >= "
          f"{p_floor(7, 3):.3f}")
    return p


if __name__ == "__main__":
    main()
