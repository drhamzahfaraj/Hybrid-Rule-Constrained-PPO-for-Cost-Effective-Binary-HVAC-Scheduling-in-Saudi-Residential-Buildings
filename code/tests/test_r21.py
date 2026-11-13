"""Ruling §21.4 producers and the r21 job file (short)."""
import os, sys, json
import numpy as np

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import config as CFG
import final_tables as F


def test_per_window_criterion_selects_admissible_candidate():
    import t1_sens as T
    W = F.TUNE_W[:2]
    cands = [(23.5, 22.5), (23.9, 22.1), (23.7, 22.35)]
    rows = F._rows_rule_batch("riyadh", CFG.PRICE, W, cands)
    i, st, obj = T.select_per_window("riyadh", CFG.PRICE, cands, rows, W)
    assert i is not None and st in ("pooled_0.03", "pooled_0.10")
    i0 = int(np.flatnonzero(F.DELTAS == 0.0)[0])
    for r, w in zip(rows[i], W):
        assert F.admissible(r, w) and F.pooled_status(r[F.MEAN_KEY] - F.therm_curve("riyadh", w, CFG.PRICE)[0][i0])


def test_therm_self_score_is_not_positive():
    import t1_v2 as T1V2
    th = {w: F.therm_run("taif", w, CFG.PRICE) for w in F.WINDOWS}
    s, pw = T1V2.evaluate("taif", CFG.PRICE, {w: th[w] for w in F.EVAL_W}, th)
    assert s["s_pooled_eq"] <= 1e-9 and abs(s["dT_pooled"]) < 1e-12


def test_shield_latch_rows_build():
    import shield as SH
    rows, pw = SH.fit_and_eval("riyadh", CFG.PRICE, sigmas=(0.05,), caps=[23.8, 23.9, 24.0])
    assert rows and rows[0]["fit_status"] in F.FIT_STATUSES and rows[0]["sigma"] == 0.05


def test_r21_jobfile():
    p = os.path.join(ROOT, "jobs", "r21.jsonl")
    jobs = [json.loads(l) for l in open(p) if l.strip() and not l.lstrip().startswith("#")]
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids)) and all(j["outputs"] for j in jobs)
    for j in jobs:
        assert set(j) <= {"id", "cmd", "env", "outputs", "after", "code_sensitive"}
        assert set(j.get("after", [])) <= set(ids)
        script = j["cmd"].split()[1]
        assert os.path.exists(os.path.join(ROOT, script)), script
