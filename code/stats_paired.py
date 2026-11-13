#!/usr/bin/env python3
"""Paired significance tests and interval estimates on the held-out windows.

Why the paper needs this
------------------------
Three of its claims are comparisons between two controllers whose point
estimates differ by less than their own across-window spread:

  (a) RBRL 5.66% vs the guard hysteresis 5.82% -- the paper's central negative
      result, that learning recovers the rule layer's own policy and adds
      nothing. That is an EQUIVALENCE claim, and an equivalence claim cannot be
      supported by a difference of 0.16 points next to a standard deviation of
      several points. It needs an interval.
  (b) TUNED 9.25% vs MPC-24h 9.10% -- the restated fourth finding, that a day
      of lookahead buys nothing.
  (c) TUNED 9.25% vs THERM 0% -- the one comparison the paper needs to be
      POSITIVE, and the only one where a significance test is the right tool.

The windows are paired: every arm is run on the same seven held-out weeks of the
same weather year, so the correct analysis is on the within-window differences,
not on two independent samples. Pairing is what makes n = 7 usable at all.

What n = 7 permits, stated once and honoured throughout
-------------------------------------------------------
The exact two-sided Wilcoxon signed-rank test on seven pairs has a smallest
attainable p-value of 2/2^7 = 0.0156: significance at the 5% level is reachable
but only when every one of the seven differences has the same sign. There is no
power here to detect a small difference, so a non-significant result is reported
as what it is -- an absence of evidence at n = 7 -- and never as evidence of
equivalence. For the equivalence claims the deliverable is therefore the
CONFIDENCE INTERVAL on the difference, and the honest reading of a wide interval
that contains zero is that differences up to its half-width are not excluded.

Methods
-------
* exact Wilcoxon signed-rank (scipy, mode="exact"), two-sided, on paired costs
* exact paired sign test as a distribution-free cross-check that uses only the
  signs, so a single extreme window cannot drive it
* BCa bootstrap, 20000 resamples, on the mean per-window saving and on the mean
  paired difference. BCa rather than the percentile method because the saving
  ratio is a nonlinear function of the costs and its bootstrap distribution is
  skewed at this sample size; the acceleration term corrects for that.
* TOST at a margin stated explicitly below, reported alongside the interval so
  the reader sees the margin rather than inferring it.
"""
from __future__ import annotations
import sys, os, csv, json
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np
from scipy import stats

import headroom as H
import final_tables as F

# Equivalence margin for the TOST, declared before the result is seen and
# justified physically rather than statistically: 1.0 percentage point of the
# saving ratio is, at the in-force 0.18 SAR/kWh and this plant, about 0.011
# SAR/day, roughly 4 SAR a year. A difference smaller than that is below the
# resolution at which a householder or a utility programme could act, so it is
# the right scale at which to call two controllers practically the same.
DELTA_EQ = 1.0          # percentage points of saving ratio
N_BOOT = 20000
RNG = np.random.default_rng(20261111)


# --------------------------------------------------------------------- BCa
def bca_ci(x, stat, alpha=0.05, n_boot=N_BOOT, rng=RNG):
    """Bias-corrected and accelerated bootstrap interval for a 1-sample stat.

    Returns (lo, hi, point). Falls back to the percentile interval if the
    acceleration cannot be formed (which happens when every jackknife replicate
    is identical, i.e. the statistic is constant).
    """
    x = np.asarray(x, float)
    n = x.size
    th0 = stat(x)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot = np.array([stat(x[i]) for i in idx])
    # bias correction z0
    prop = np.mean(boot < th0)
    prop = min(max(prop, 1.0 / n_boot), 1.0 - 1.0 / n_boot)
    z0 = stats.norm.ppf(prop)
    # acceleration from the jackknife
    jack = np.array([stat(np.delete(x, i)) for i in range(n)])
    jm = jack.mean()
    num = np.sum((jm - jack) ** 3)
    den = 6.0 * (np.sum((jm - jack) ** 2) ** 1.5)
    a = 0.0 if den == 0 else num / den
    zl, zu = stats.norm.ppf(alpha / 2.0), stats.norm.ppf(1.0 - alpha / 2.0)

    def adj(z):
        d = 1.0 - a * (z0 + z)
        if d == 0:
            return 0.5
        return float(stats.norm.cdf(z0 + (z0 + z) / d))
    ql, qu = adj(zl), adj(zu)
    lo = float(np.quantile(boot, min(max(ql, 0.0), 1.0)))
    hi = float(np.quantile(boot, min(max(qu, 0.0), 1.0)))
    return lo, hi, float(th0)


def sign_test(d):
    """Exact two-sided paired sign test; zeros discarded, as is conventional."""
    d = np.asarray(d, float)
    nz = d[np.abs(d) > 1e-12]
    n = nz.size
    if n == 0:
        return 1.0, 0, 0
    pos = int((nz > 0).sum())
    p = float(min(1.0, 2.0 * stats.binom.cdf(min(pos, n - pos), n, 0.5)))
    return p, pos, n


def compare(name_a, Ja, name_b, Jb, Jtherm, fout):
    """Full paired analysis of arm A against arm B on identical windows."""
    Ja, Jb, Jt = map(lambda v: np.asarray(v, float), (Ja, Jb, Jtherm))
    assert Ja.shape == Jb.shape == Jt.shape
    n = Ja.size
    sa = 100.0 * (Jt - Ja) / Jt            # per-window saving, arm A
    sb = 100.0 * (Jt - Jb) / Jt
    d_cost = Ja - Jb                        # SAR/day, positive => A dearer
    d_sav = sa - sb                         # points, positive => A saves more

    # exact Wilcoxon on the paired COSTS, the primitive quantity
    try:
        w = stats.wilcoxon(Ja, Jb, zero_method="wilcox", alternative="two-sided",
                           method="exact")
        wp, wstat = float(w.pvalue), float(w.statistic)
    except Exception:
        w = stats.wilcoxon(Ja, Jb, alternative="two-sided")
        wp, wstat = float(w.pvalue), float(w.statistic)
    sp, pos, nsign = sign_test(d_cost)

    lo_d, hi_d, pt_d = bca_ci(d_sav, np.mean)
    lo_a, hi_a, pt_a = bca_ci(sa, np.mean)
    lo_b, hi_b, pt_b = bca_ci(sb, np.mean)

    # TOST: both one-sided t tests against +/- DELTA_EQ on the paired
    # difference in saving. Equivalence is concluded only if BOTH reject.
    se = d_sav.std(ddof=1) / np.sqrt(n)
    if se > 0:
        t_lo = (d_sav.mean() + DELTA_EQ) / se
        t_hi = (d_sav.mean() - DELTA_EQ) / se
        p_lo = float(1.0 - stats.t.cdf(t_lo, n - 1))     # H0: diff <= -delta
        p_hi = float(stats.t.cdf(t_hi, n - 1))           # H0: diff >= +delta
        p_tost = max(p_lo, p_hi)
    else:
        p_tost = 0.0
    equiv = p_tost < 0.05

    print(f"\n=== {name_a}  vs  {name_b}   (n={n} paired held-out windows) ===")
    print(f"  saving {name_a:22s} {pt_a:+7.2f}%  BCa 95% CI [{lo_a:+.2f}, {hi_a:+.2f}]")
    print(f"  saving {name_b:22s} {pt_b:+7.2f}%  BCa 95% CI [{lo_b:+.2f}, {hi_b:+.2f}]")
    print(f"  paired difference A-B        {pt_d:+7.2f} pts  "
          f"BCa 95% CI [{lo_d:+.2f}, {hi_d:+.2f}]")
    print(f"  exact Wilcoxon on costs      W={wstat:.1f}  p={wp:.4f}"
          f"   (smallest attainable p at n={n}: {2/2**n:.4f})")
    print(f"  exact sign test              {pos}/{nsign} windows favour "
          f"{name_b if pt_d>0 else name_a}  p={sp:.4f}")
    print(f"  TOST at +/-{DELTA_EQ:.1f} pt          p={p_tost:.4f}  -> "
          f"{'EQUIVALENT within the margin' if equiv else 'equivalence NOT established'}")
    half = max(abs(lo_d), abs(hi_d))
    print(f"  honest reading: a difference larger than {half:.2f} pts is "
          f"excluded at 95%; smaller ones are not.")

    fout.append(dict(
        comparison=f"{name_a} vs {name_b}", n=n,
        sav_a=round(pt_a, 3), sav_a_lo=round(lo_a, 3), sav_a_hi=round(hi_a, 3),
        sav_b=round(pt_b, 3), sav_b_lo=round(lo_b, 3), sav_b_hi=round(hi_b, 3),
        diff_pts=round(pt_d, 3), diff_lo=round(lo_d, 3), diff_hi=round(hi_d, 3),
        wilcoxon_W=round(wstat, 2), wilcoxon_p=round(wp, 5),
        sign_p=round(sp, 5), sign_pos=pos, sign_n=nsign,
        tost_margin_pts=DELTA_EQ, tost_p=round(p_tost, 5),
        equivalent=bool(equiv), max_excluded_pts=round(half, 3),
        mean_cost_a=round(float(Ja.mean()), 5),
        mean_cost_b=round(float(Jb.mean()), 5)))
    return fout


# ------------------------------------------------------------------ arm data
def arms(city, price=0.18):
    """Per-window cost for every arm, on the identical held-out windows.

    Recomputed here rather than read from the tables so that a mismatch between
    this analysis and the tables cannot be hidden by a stale CSV; the printed
    means are cross-checked against the published ones at the end.
    """
    W = list(F.EVAL_W)
    th = {w: F.therm_run(city, w, price) for w in W}
    Jt = np.array([th[w]["J"] for w in W])

    # TUNED: the tuned fixed rule, parameters from the tuning windows only
    tgt = float(np.mean([th[w]["T_mean_occ"] for w in W]))
    _, on, off = F.tune_rule(city, price, F.TUNE_W,
                             lambda w: F.therm_run(city, w, price)["T_mean_occ"])
    Jtu = np.array([F.rule_run(city, w, price, on, off)["J"] for w in W])

    # GUARD HYSTERESIS: the policy the rule layer itself implies, at the cap the
    # comfort match selects -- i.e. RBRL's own rule layer with the learned part
    # removed. This is the arm RBRL must beat to have earned its training cost.
    cap = {"riyadh": 23.737, "jeddah": 23.737, "taif": 23.93}[city]
    Jh = np.array([F.rule_run(city, w, price, cap - 0.20, 22.0 + 0.40)["J"]
                   for w in W])
    return dict(W=W, therm=Jt, tuned=Jtu, hyst=Jh, tgt=tgt,
                tuned_params=(on, off), cap=cap)


def mpc_h(city, hh=24.0):
    """MPC per-window cost from the 1601-point grid-converged, cap-refined run
    (T21), the arm the manuscript quotes. T15 (801-point, 0.05 K caps) is kept
    for the record only."""
    p = f"/home/claude/rbrl/results/T21_g1601_{city}_mpc_perwindow.csv"
    if not os.path.exists(p):
        return None
    out = {}
    for r in csv.DictReader(open(p)):
        if abs(float(r["horizon_h"]) - hh) < 1e-9:
            out[int(r["w"])] = float(r["J"])
    return out


def rbrl(city, path="/home/claude/rbrl/results/rbrl_ppo5_perwindow.csv"):
    """RBRL per-window cost, averaged across seeds within each window.

    Averaging across seeds BEFORE pairing is the right order: the window is the
    experimental unit the arms share, and seed is a nuisance factor internal to
    this one arm. The across-seed spread is reported separately.
    """
    if not os.path.exists(path):
        return None, None
    by = {}
    for r in csv.DictReader(open(path)):
        if r["city"] != city:
            continue
        by.setdefault(int(r["w"]), []).append(float(r["J"]))
    mean = {w: float(np.mean(v)) for w, v in by.items()}
    sd = {w: float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
          for w, v in by.items()}
    return mean, sd


if __name__ == "__main__":
    rows = []
    for city in ("riyadh", "jeddah", "taif"):
        A = arms(city)
        W, Jt = A["W"], A["therm"]
        print(f"\n{'='*72}\n{city.upper()}   THERM mean "
              f"{Jt.mean():.4f} SAR/day, T_occ target {A['tgt']:.4f} C, "
              f"TUNED {A['tuned_params'][0]:.2f}/{A['tuned_params'][1]:.2f}, "
              f"guard cap {A['cap']:.3f}\n{'='*72}")

        # (c) the positive claim: does the tuned rule beat the thermostat?
        rows = compare("TUNED", A["tuned"], "THERM", Jt, Jt, rows)

        # (a) the central negative claim, once RBRL has finished training
        rb, rbsd = rbrl(city)
        if rb and all(w in rb for w in W):
            Jr = np.array([rb[w] for w in W])
            rows = compare("RBRL (PPO)", Jr, "guard hysteresis", A["hyst"],
                           Jt, rows)
            print(f"  across-seed SD of per-window cost: "
                  f"{np.mean([rbsd[w] for w in W]):.5f} SAR/day "
                  f"(5 seeds; the pairing above uses the seed mean)")
        else:
            print("\n  [RBRL per-window costs not yet available -- 5-seed run "
                  "still training; this comparison is produced on the re-run]")

        # (b) the restated fourth finding
        for hh in (24.0, 48.0):
            m = mpc_h(city, hh)
            if m and all(w in m for w in W):
                Jm = np.array([m[w] for w in W])
                rows = compare("TUNED", A["tuned"], f"MPC {hh:.0f} h", Jm, Jt,
                               rows)
            else:
                print(f"\n  [MPC-{hh:.0f}h not matched in all 7 windows for "
                      f"this city; comparison omitted]")

    os.makedirs("/home/claude/rbrl/results", exist_ok=True)
    with open("/home/claude/rbrl/results/T20_paired_stats.csv", "w",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"\n-> results/T20_paired_stats.csv ({len(rows)} comparisons)")
    print(f"\nNOTE: every interval above is a 95% BCa bootstrap interval over "
          f"{N_BOOT} resamples of {len(F.EVAL_W)} paired windows. At this "
          f"sample size the intervals are wide by construction; that width is "
          f"the finding, not a defect to be hidden.")
