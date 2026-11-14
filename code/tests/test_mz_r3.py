"""F19: multi-zone dwelling geometry, single-zone reduction, §2 metrics, batched = scalar.

Run: cd /home/claude/rbrl && OMP_NUM_THREADS=1 nice python3 -m pytest -q tests/test_mz_r3.py
"""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.environ.get("RBRL_ROOT", "/home/claude/rbrl"))
import final_tables as F
import mz_r3 as Z


def test_azimuths_match_the_floor_plan():
    """R4 S4: 2x2 zones (r0c0, r0c1, r1c0, r1c1) coupled 0-1, 0-2, 1-3, 2-3 -> coupled rooms share
    a facade orientation; 1x4 is a realisable row (S, S, N, N)."""
    assert Z.AZ["2x2"] == [(180, 90), (180, 270), (0, 90), (0, 270)]
    g = Z.geometry("2x2", "riyadh")
    for i, j in g["pairs"]:
        assert set(Z.AZ["2x2"][i]) & set(Z.AZ["2x2"][j]), (i, j)
    assert Z.AZ["1x4"] == [(180,), (180,), (0,), (0,)]


@pytest.mark.parametrize("on,off", ((23.5, 22.5), (23.7, 22.3)))
def test_1x1_reproduces_single_zone(on, off):
    w = F.TUNE_W[0]
    a = Z.Dwelling("riyadh", "1x1", w).run(Z.hyst_all(on, off))
    b = F.rule_run("riyadh", w, 0.18, on, off)
    for k in ("J", "E", "f_s", "T_mean_occ_clip", "deg_h_over", "deg_h_cmd_under", "T_end"):
        assert abs(a[k] - b[k]) <= 1e-9, (k, a[k], b[k])


def test_batch_equals_scalar_and_rule_C_at_therm():
    w = F.EVAL_W[0]
    D = Z.Dwelling("riyadh", "2x2", w)
    on = np.array([23.5, 23.7, 23.6]); off = np.array([22.5, 22.3, 22.4])
    r = D.run_batch(Z.hyst_batch(on, off, D.nz), 3)
    for i in range(3):
        s = D.run(Z.hyst_all(on[i], off[i]))
        assert abs(s["J"] - r["J"][i]) <= 1e-12 and abs(s[Z.K] - r[Z.K][i]) <= 1e-12
    th = Z.therm(D)
    e = Z.equalise(D, th[Z.K])
    # THERM scores ~0 against itself, up to the staircase interpolation (bracket_gap, §2.3)
    assert e["resid"] <= 1e-9 and not e["clipped"] and abs(e["delta"]) <= 0.01
    assert abs(e["J"] - th["J"]) <= 0.005 * th["J"]


def test_lambda_ij_sweep_changes_coupling_only():
    a = Z.Dwelling("riyadh", "1x2", 181, lam_ij=12.5).g; b = Z.Dwelling("riyadh", "1x2", 181, lam_ij=35.0).g
    assert np.allclose(a["lam_env"], b["lam_env"]) and b["lam_iz"][0] == 35.0
