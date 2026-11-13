"""F19 (RULING_round4 §3, §5; R5-6): MPC-MZ batch invariance (test 10) and corrected cold rule.

Run: cd /home/claude/rbrl && OMP_NUM_THREADS=1 nice python3 -m pytest -q tests/test_mz_mpc.py
"""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.environ.get("RBRL_ROOT", "/home/claude/rbrl"))
import final_tables as F
import mz_r3 as Z
import mz_mpc as MM

RULE = (23.6, 22.35)


def _D(topo, w=181, n=48, sb=False):
    D = Z.Dwelling("riyadh", topo, w, None, sb); D.N = n
    return D


def _same(a, b):
    assert a.keys() == b.keys()
    for k in a:
        x, y = np.asarray(a[k], float), np.asarray(b[k], float)
        assert np.array_equal(x, y, equal_nan=True), (k, a[k], b[k])


@pytest.mark.parametrize("topo", ("1x2", "2x2"))
def test10_batch_invariance(topo):
    """A lambda's run must not depend on the other lambdas in its batch (R5-6 (1), E-sw3-3)."""
    a = MM.mz_mpc_run(_D(topo), [0.5], 6.0, RULE, n_grid=101)[0]
    b = MM.mz_mpc_run(_D(topo), [0.0, 0.5, 24.0], 6.0, RULE, n_grid=101)[1]
    _same(a, b)


def test_corrected_cold_rule_and_metrics():
    """Cooling never ends a step below T_min (hard constraint in the optimiser): zero commanded
    under-temperature; no fallback on an ordinary window; all §2.1 metrics emitted."""
    rs = MM.mz_mpc_run(_D("1x2", F.TUNE_W[0], 96), [0.0, 0.3, 5.0], 6.0, RULE, n_grid=101)
    for r in rs:
        assert r["deg_h_cmd_under"] == 0.0
        assert r["fallback_steps"] == 0
        for k in ("deg_h_over", "deg_h_ff_under", "T_end", "T_max_away", "T_zone_spread"):
            assert k in r


def test_grid_reaches_below_freefloat_min():
    D = _D("2x2", 121)
    Tg = MM._grid(D, 101)
    assert Tg[0] <= min(F.H.BAND_LO - 0.1, D.tinf0_min() - 0.05) + 1e-12


def test_shared_plant_is_inert():
    with pytest.raises(ValueError):
        Z.Dwelling("riyadh", "1x2", 181, 1, False)
    with pytest.raises(SystemExit):
        MM.main(["riyadh", "1x2", "--m", "1"])


# ------------------------------------------------------------ V-res-5: one lambda selection
def _sz_vs_mz(monkeypatch, tune_w, eval_w, hh, n_grid, rule):
    import mpc_lambda as M, mz_mpc as MZ, mz_r3 as Z, final_tables as F, t1_v2 as T1V2
    monkeypatch.setattr(F, "TUNE_W", list(tune_w)); monkeypatch.setattr(F, "EVAL_W", list(eval_w))
    monkeypatch.setattr(M, "tuned_rule", lambda city, *a, **k: rule)
    log = lambda m: None
    lam1, _, _, st1 = M.fit_lambda("riyadh", hh, None, n_grid, log, with_status=True)
    b1 = M.KNOB["backoff"]
    th = {w: F.therm_run("riyadh", w, 0.18) for w in set(F.TUNE_W) | set(F.EVAL_W)}
    runs1 = {w: M.mpc_lams("riyadh", w, [lam1], hh, n_grid, rule=rule, backoff=b1)[0] for w in F.EVAL_W}
    s1, _ = T1V2.evaluate("riyadh", 0.18, runs1, th)
    Ds = {w: Z.Dwelling("riyadh", "1x1", w, None, False) for w in F.TUNE_W}
    De = {w: Z.Dwelling("riyadh", "1x1", w, None, False) for w in F.EVAL_W}
    lam2, b2, st2, info, n = MZ.fit_mz(Ds, hh, rule, 0.18, None, n_grid, log)
    runs2 = {w: MZ.mz_mpc_run(De[w], [lam2], hh, rule, 0.18, None, n_grid, backoff=b2)[0] for w in F.EVAL_W}
    s2, _ = Z.evaluate(De, runs2, 0.18)
    return (lam1, st1, b1, s1["s_pooled_eq"]), (lam2, st2, b2, s2["s_pooled_eq"])


def test_mz_1x1_lambda_selection_equals_single_zone_fast(monkeypatch):
    """V-res-5, reduced: the 1x1 dwelling MPC selects the same lambda (same scan, bisection,
    refinement, A4) and scores the same Rule C saving as the single-zone MPC."""
    import final_tables as F
    a, b = _sz_vs_mz(monkeypatch, [F.TUNE_W[0]], [F.EVAL_W[0]], 0.5, 101, (23.71, 22.36))
    assert a[:3] == b[:3] and abs(a[3] - b[3]) < 1e-6, (a, b)


@pytest.mark.slow
def test_mz_1x1_reproduces_T21v3_mpc24():
    """V-res-5 acceptance: 1x1 MPC-MZ on Riyadh (MZ TUNED rollout, 1601 nodes, H = 24 h) reproduces
    the single-zone T21v3_riyadh MPC-24 saving 18.263835 % to 1e-6 (hours of CPU)."""
    import csv, mz_mpc as MZ, mz_r3 as Z, final_tables as F, rbrl_io as IO
    ref = next(r for r in csv.DictReader(open(f"{IO.R}/T21v3_riyadh.csv")) if float(r["horizon_h"]) == 24.0)
    rule = MZ.mz_tuned("riyadh", "1x1", 12.5, False)
    Ds = {w: Z.Dwelling("riyadh", "1x1", w, None, False) for w in F.TUNE_W}
    De = {w: Z.Dwelling("riyadh", "1x1", w, None, False) for w in F.EVAL_W}
    lam, b, st, info, n = MZ.fit_mz(Ds, 24.0, rule, 0.18, None, MZ.NG, lambda m: None)
    runs = {w: MZ.mz_mpc_run(De[w], [lam], 24.0, rule, 0.18, None, MZ.NG, backoff=b)[0] for w in F.EVAL_W}
    s, _ = Z.evaluate(De, runs, 0.18)
    assert abs(lam - float(ref["lam"])) < 1e-6 and st == ref["fit_status"]
    assert abs(s["s_pooled_eq"] - float(ref["s_pooled_eq"])) < 1e-6


def test_budgeted_chain_resumes_to_the_same_fit(monkeypatch, tmp_path):
    """jobq2 kills at 2 h: a budgeted run stops after one new window batch (Budget), the next run
    replays the cache and continues; the chained result equals the unbudgeted fit."""
    import mz_mpc as MZ, mz_r3 as Z, final_tables as F
    monkeypatch.setattr(F, "TUNE_W", [F.TUNE_W[0]])
    rule = (23.71, 22.36); log = lambda m: None
    Ds = {w: Z.Dwelling("riyadh", "1x1", w, None, False) for w in F.TUNE_W}
    ref = MZ.fit_mz(Ds, 0.5, rule, 0.18, None, 41, log)
    path = str(tmp_path / "c.pkl"); n_jobs = 0
    while True:
        n_jobs += 1
        c = MZ.RunCache(path, dict(t="x"), budget_s=0.0, log=log)
        try:
            got = MZ.fit_mz(Ds, 0.5, rule, 0.18, None, 41, log, c)
            break
        except MZ.Budget:
            assert n_jobs < 200
    assert n_jobs > 1 and got[:3] == ref[:3]


def test_mz_final_jobfile():
    import json
    p = os.path.join(os.environ.get("RBRL_ROOT", "/home/claude/rbrl"), "jobs", "mz_final.jsonl")
    jobs = [json.loads(l) for l in open(p) if l.strip() and not l.lstrip().startswith("#")]
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids)) and all(j["outputs"] for j in jobs)
    assert all(set(j.get("after", [])) <= set(ids) for j in jobs)
    finals = [j for j in jobs if "--final" in j["cmd"]]
    assert len(finals) == 7 and all(o.endswith(".csv") for j in finals for o in j["outputs"])
