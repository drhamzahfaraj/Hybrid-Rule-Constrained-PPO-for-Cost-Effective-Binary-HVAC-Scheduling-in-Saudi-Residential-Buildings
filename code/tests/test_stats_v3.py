"""F17: stats_v3 (RULING_round4 §2.4, §12.7). Exact procedures, floors, families, resolution rule,
and agreement with R1_methods.md's recomputation on the rows that did not change (T20v2)."""
import csv, io, os, subprocess, sys
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import stats_v3 as S
from scipy import stats as st

BASELINE = "d9494c4"          # F0 commit: the v2 files R1 recomputed from


def _git_csv(path):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{BASELINE}:{path}"], capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"{path} not in {BASELINE}")
    return list(csv.DictReader(io.StringIO(r.stdout)))


def test_floors_and_hl_ci_index():
    assert S.p_floor(7, 1) == pytest.approx(2 / 128) and S.p_floor(7, 3) == pytest.approx(0.046875)
    k, cov = S.wilcoxon_crit(7)
    assert k == 2 and cov == pytest.approx(1 - 6 / 128)          # 3rd smallest/largest of 28, 95.3 %
    d = np.arange(1.0, 8.0)
    walsh = np.sort([(d[i] + d[j]) / 2 for i in range(7) for j in range(i, 7)])
    hl, lo, hi, _ = S.hl_ci(d)
    assert (hl, lo, hi) == (4.0, walsh[2], walsh[25])


def test_exact_wilcoxon_matches_scipy_without_ties_and_handles_ties():
    rng = np.random.default_rng(1)
    for _ in range(30):
        d = rng.normal(0.5, 1, 7)
        assert S.wilcoxon_exact(d) == pytest.approx(st.wilcoxon(d, method="exact").pvalue, abs=1e-12)
    assert S.wilcoxon_exact(np.ones(7)) == pytest.approx(2 / 128)    # unanimous -> floor
    assert S.wilcoxon_exact(np.zeros(7)) == 1.0
    p = S.wilcoxon_exact([1, 1, -1, 2, 2, 3, -3])                       # ties: mid-ranks, exact
    assert 0 < p <= 1
    assert S.sign_exact(np.ones(7)) == pytest.approx(2 / 128)
    assert S.sign_exact([1, 1, 1, 1, 1, 1, -1]) == pytest.approx(16 / 128)


def test_holm():
    assert list(S.holm([0.015625] * 3)) == pytest.approx([0.046875] * 3)
    assert list(S.holm([0.01, 0.04, 0.03])) == pytest.approx([0.03, 0.06, 0.06])


def test_matches_R1_recomputation_on_unchanged_rows():
    """R1_methods.md: exact Wilcoxon, sign, Holm, exact HL CI recomputed from T1v2_perwindow /
    T21v2_*_perwindow; matches T20v2 on the rows that did not change (Taif TUNED-THERM: HL 4.18
    [2.99, 5.44]). Every T20v2 row whose per-window inputs are unchanged (same mean difference)
    must be reproduced on HL, CI, p_W, p_sign; Holm on complete unchanged families."""
    t1 = [r for r in _git_csv("results/T1v2_perwindow.csv") if r["tariff"] == "inforce"]
    sw = lambda rows: {int(r["window"]): float(r["s_w"]) for r in rows}
    arm = lambda a, c: sw([r for r in t1 if r["arm"] == a and r["city"] == c])
    mpc = lambda c, h: sw([r for r in _git_csv(f"results/T21v2_{c}_perwindow.csv") if float(r["horizon_h"]) == h])
    t20 = {(r["family"], r["city"]): r for r in _git_csv("results/T20v2_paired_stats.csv")}
    matched = []
    for fam, a, b in (("TUNED-THERM", lambda c: arm("TUNED", c), None),
                      ("TUNED-guard", lambda c: arm("TUNED", c), lambda c: arm("guard", c)),
                      ("TUNED-MPC24", lambda c: arm("TUNED", c), lambda c: mpc(c, 24.0))):
        for c in ("riyadh", "jeddah", "taif"):
            ref = t20.get((fam, c))
            if ref is None:
                continue
            r = S.contrast(a(c), None if b is None else b(c), 0.0, 0.0)
            if abs(r["mean_diff"] - float(ref["mean_diff"])) > 1e-4:
                continue                                   # row changed since T20v2 (refined TUNED)
            for k in ("hl", "hl_lo", "hl_hi", "hl_coverage", "p_wilcoxon", "p_sign"):
                assert r[k] == pytest.approx(float(ref[k]), abs=2e-4), (fam, c, k)
            matched.append((fam, c))
    assert ("TUNED-THERM", "taif") in matched
    r = S.contrast(arm("TUNED", "taif"), None, 0, 0)
    assert (round(r["hl"], 2), round(r["hl_lo"], 2), round(r["hl_hi"], 2)) == (4.18, 2.99, 5.44)


def test_families_on_synthetic_v3(tmp_path, monkeypatch):
    import rbrl_io as IO, test_gates_v3 as G
    monkeypatch.setattr(IO, "R", str(tmp_path)); monkeypatch.setattr(IO, "_READ", {})
    G.make_v3(str(tmp_path))
    rows = S.run()
    fams = {}
    for r in rows:
        fams.setdefault(r["family"], []).append(r)
    assert sorted(fams) == ["F1", "F2", "F3", "F4", "F5"]
    for f in ("F1", "F2", "F3", "F4"):
        assert [r["city"] for r in fams[f]] == ["riyadh", "jeddah", "taif"]
        assert all(r["holm"] and r["family_size"] == 3 and r["p_floor"] == pytest.approx(0.046875) for r in fams[f])
    (f5,) = fams["F5"]
    assert f5["city"] == "riyadh" and not f5["holm"] and f5["p_adj"] == f5["p_wilcoxon"]
    assert f5["p_floor"] == pytest.approx(2 / 128)
    for r in rows:
        assert r["resolution"] == ("resolved" if abs(r["d_pooled"]) >= 3 else "not resolved")
        assert r["unanimous"] == (r["n_pos"] == 7 or r["n_neg"] == 7)
        assert r["hl_lo"] <= r["hl"] <= r["hl_hi"]
    # F1 is TUNED against THERM: d_w = s_w(TUNED), d_pooled = s_pooled(TUNED)
    import v3_names as V
    assert fams["F1"][0]["d_pooled"] == pytest.approx(V.pooled(V.perwindow("TUNED", "riyadh").values()))
    p = S.main()
    assert os.path.basename(p) == "T20v3_paired_stats.csv"
    # F5 optional: E2 missing -> family absent, the others still written; a REQUIRED family missing -> error
    os.remove(V.path("E2_PW"))
    assert "F5" not in {r["family"] for r in S.run()}
    os.remove(V.path("MPC_PERS_PW", "taif"))
    with pytest.raises(FileNotFoundError):
        S.run()
