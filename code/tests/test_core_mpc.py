"""F9 / F22 (ruling round 4, Sec. 3 and 12.6): mpc_lambda.

  * test 9: a batch over lam equals the single-lam runs (perfect and persistence);
  * persistence with forecast := truth reproduces the perfect run bit-for-bit;
  * the persistence forecast uses measured weather only (t(j-96 m), irradiance from j < k);
  * test 15: mpc_lams equals the scalar reference `mpc_run` (moved here from mpc_lambda);
  * horizons 0.25 / 1 / 2 h accepted; TUNED fallback; lam*; routed writes;
  * F22 / V-code-17: C_th from the RBRL_CTH hook reaches mpc_lambda and r3_dp consistently,
    4800 stays bit-identical; TUNED base read for the matching c_sw / C_th.

Short windows (N = 96 steps) keep the module under a minute on one core.
Run: cd /home/claude/rbrl && OMP_NUM_THREADS=1 nice python3 -I -m pytest -q tests/test_core_mpc.py"""
import json, os, re, subprocess, sys
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import headroom as H
import setback as S
import final_tables as F
import r3_dp as D
import mpc_lambda as M

CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("RBRL_")}
RULE = (23.6, 22.35)
CITY, W, NS, NG = "riyadh", 121, 96, 101


def _py(code, env=None):
    r = subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {ROOT!r}); " + code],
                       capture_output=True, text=True, env=dict(CLEAN, **(env or {})), cwd=ROOT, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def _same(a, b):
    """exact equality of result dicts; NaN equals NaN (T_max_away without away steps)."""
    if isinstance(a, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a.keys() == b.keys() and all(
        (a[k] == b[k]) or (isinstance(a[k], float) and np.isnan(a[k]) and np.isnan(b[k])) for k in a)


def _run(lams, hh=1.0, **kw):
    kw.setdefault("rule", RULE)
    return M.mpc_lams(CITY, W, lams, hh, NG, N=NS, **kw)


# ---------------------------------------------------------------- reference (legacy) implementation
def mpc_run(city, w, price_v, horizon_h, lam, n_grid=801, rule=None, N=672):
    """Scalar receding-horizon lam-MPC, one lam, no setback, perfect forecast: the round-3
    mpc_lambda.mpc_run moved into the tests (F9) with the round-4 semantics (step_ok cold
    rule, TUNED fallback, c_sw + price*E_START per start, per-step COP). Reference for test 15."""
    q = H.Q_HVAC
    lam_env = H.lam_of(F.FACES, city)
    Hh = int(round(horizon_h / S.DT))
    t_out, irr, NN = H.series(city, M.HOURS, w)
    decay = float(np.exp(-S.DT * 3600.0 * lam_env / (M.C_TH * 1e3)))
    p_el = q / H.cop_series(t_out) / 1000.0
    run_c = price_v * p_el * S.DT
    swc = F.C_SW + price_v * H.E_START
    wl = lam / N
    on_at, off_at = rule
    Tg = D.grid_for(city, w, False, n_grid, hours=M.HOURS)
    n = len(Tg)
    ginf = H.SHGC * H.A_GL * irr
    Tinf = (t_out + ginf / lam_env, t_out + (ginf - q) / lam_env)
    therm_c = price_v * M.C_TH * 1e3 / 3.6e6 / H.COP_RATED

    def rollout(end):
        idx = np.arange(max(0, end - M.ROLL), end)
        if len(idx) < M.ROLL:
            idx = np.concatenate([np.full(M.ROLL - len(idx), idx[0]), idx])
        out = np.empty((n, 2))
        for p0 in (0, 1):
            T = Tg.copy(); prev = np.full(n, p0); c = np.zeros(n)
            for j in idx:
                u = np.where(T >= on_at, 1, np.where(T <= off_at, 0, prev))
                c += np.where((u == 1) & (prev == 0), swc, 0.0) + run_c[j] * u
                Ti = np.where(u == 1, Tinf[1][j], Tinf[0][j])
                T = Ti + (T - Ti) * decay
                c += wl * np.maximum(T, M.LO)
                prev = u
            out[:, p0] = c + therm_c * (T - M.T0)
        return out

    T, prev = M.T0, 0
    J = 0.0; starts = 0; fallback = 0; Tclip = []
    for k in range(N):
        end = k + Hh
        V = rollout(end)
        for j in range(end - 1, k, -1):
            nxt = np.empty((n, 2))
            for u in (0, 1):
                Ti = Tinf[u][j]
                Tp = Ti + (Tg - Ti) * decay
                ok = D.step_ok(Tp, u, M.HI)
                Vn = D._interp_inf(Tp, Tg, V[:, u])
                nxt[:, u] = np.where(ok, run_c[j] * u + wl * np.maximum(Tp, M.LO) + Vn, np.inf)
            V = np.stack([np.minimum(nxt[:, 0], swc + nxt[:, 1]), np.minimum(nxt[:, 0], nxt[:, 1])], axis=1)
        best, bu = np.inf, None
        for u in (0, 1):
            Ti = Tinf[u][k]
            Tp = Ti + (T - Ti) * decay
            if not D.step_ok(Tp, u, M.HI):
                continue
            c = run_c[k] * u + (swc if (u and not prev) else 0.0) + wl * max(Tp, M.LO) \
                + D._interp_inf(Tp, Tg, V[:, u])
            if c < best:
                best, bu = c, u
        if bu is None or not np.isfinite(best):
            bu = 1 if T >= on_at else (0 if T <= off_at else prev); fallback += 1
        u = bu
        if u and not prev:
            J += swc; starts += 1
        J += run_c[k] * u
        Ti = Tinf[u][k]
        T = Ti + (T - Ti) * decay
        Tclip.append(max(T, M.LO))
        prev = u
    J += therm_c * (T - M.T0)
    days = N * S.DT / 24.0
    return dict(J=J / days, f_s=starts / days, T_mean_occ_clip=float(np.mean(Tclip)),
                fallback_steps=fallback, T_end=T)


# ---------------------------------------------------------------- tests
@pytest.mark.parametrize("forecast", ["perfect", "persistence"])
def test9_batch_equals_single(forecast):
    lams = [0.0, 0.3, 5.0]
    a = _run(lams, forecast=forecast)
    for l, lam in enumerate(lams):
        b = _run([lam], forecast=forecast)[0]
        assert _same(a[l], b), (forecast, lam)


def test_persistence_with_truth_is_perfect_bit_for_bit():
    t_out, irr, _ = H.series(CITY, M.HOURS, W)
    truth = lambda k: (t_out, irr)
    for hh in (1.0, 6.0):
        p = _run([0.0, 0.25], hh, forecast="perfect", return_actions=True)
        q = _run([0.0, 0.25], hh, forecast=truth, return_actions=True)
        assert _same(p, q), hh
    r = _run([0.25], 6.0, forecast="persistence")[0]
    assert not _same(r, _run([0.25], 6.0, forecast="perfect")[0])      # the forecast matters


def test_persistence_uses_measured_weather_only():
    NN = 864
    for k in (0, 5, 95, 96, 400, 671):
        st, si = M._persistence_src(k, NN)
        j = np.arange(NN)
        assert np.all(st <= k) and np.all(si <= k - 1)                 # causal
        assert np.array_equal(st[:k + 1], j[:k + 1])                    # T_out measured up to now
        assert np.array_equal(si[:k], j[:k])                            # irradiance measured before now
        fut = j > k
        assert np.all((j - st)[fut] % 96 == 0) and np.all((j - si)[j >= k] % 96 == 0)
        h = j[(j > k) & (j <= k + 96)]
        assert np.array_equal(st[h], h - 96)                            # in-horizon t^(j) = t(j - 96)
        assert si[k] == k - 96                                          # current irradiance persisted
    # history before the window is real weather (the day before), not padding
    tx, ix, _ = H.series(CITY, M.HOURS + 24, W - 1)
    t_out, _, _ = H.series(CITY, M.HOURS, W)
    assert np.array_equal(tx[96:], t_out)


def test15_equals_scalar_reference():
    for hh, lam in ((1.0, 0.0), (2.0, 0.3)):
        ref = mpc_run(CITY, W, 0.18, hh, lam, NG, rule=RULE, N=NS)
        got = _run([lam], hh)[0]
        for k in ("J", "f_s", "T_mean_occ_clip", "T_end"):
            assert abs(got[k] - ref[k]) <= 1e-9 * max(1.0, abs(ref[k])), (hh, k, got[k], ref[k])
        assert got["fallback_steps"] == ref["fallback_steps"] == 0


def test_short_horizons_and_columns():
    for hh in (0.25, 1.0, 2.0):
        r = _run([0.2], hh)[0]
        for k in ("J", "T_end", "fallback_steps", "grid_h", "deg_h_cmd_under", "deg_h_ff_under"):
            assert k in r
        assert r["deg_h_cmd_under"] == 0.0 and r["deg_h_over"] == 0.0
        assert abs(r["grid_h"] - M.grid_h(CITY, W, NG)) < 1e-15
    for bad in (0.3, 0.0, 49.0):
        with pytest.raises(ValueError):
            _run([0.2], bad)


def test_fallback_is_tuned_action():
    """an impossible upper limit leaves no feasible action: every step falls back to TUNED,
    so the trajectory is the TUNED rule's (S.sim with the hysteresis policy)."""
    import unittest.mock as um
    with um.patch.object(D, "step_ok", lambda Tp, u, hi, hh=0.0, t_min=None: np.zeros_like(Tp, bool)):
        r = _run([0.2], 1.0, return_actions=True)[0]
    assert r["fallback_steps"] == NS
    N, occ, lo, hi = F._ctx(CITY, W, False)
    s = S.sim(S.hyst_abs(*RULE), CITY, F.FACES, F.C_TH, H.price_flat(N, 0.18), lo, hi, occ, 168, W,
              F.T0, c_sw=F.C_SW, record=True)
    assert r["actions"] == s["u"][:NS].tolist()
    assert _run([0.2], 1.0)[0]["fallback_steps"] == 0


def test_lam_star_matches_r5():
    got = [round(M.lam_star(c), 4) for c in ("riyadh", "jeddah", "taif")]
    assert got == [0.2406, 0.2494, 0.2297]


def test_mpc_lambda_writes_only_through_rbrl_io():
    src = open(os.path.join(ROOT, "mpc_lambda.py")).read()
    assert not re.search(r"json\.dump\(|DictWriter\(|csv\.writer|open\([^)]*[\"'][wa]\+?[\"']", src)
    assert "ROLLC" not in src and "def mpc_run" not in src and "golden" not in src


def stamp_tuned_files(dst):
    """provenance-stamped copies of the TUNED files in `dst` (rbrl_io writes the .meta.json), so
    tuned_rule's provenance check can be exercised before J2/J20 regenerate the real files."""
    code = ("import json, csv, rbrl_io as IO; "
            f"src = {ROOT!r} + '/results/'; "
            "d = json.load(open(src + 'tuned_params_v2.json')); d.pop('_provenance', None); "
            "IO.write_json('tuned_params_v2', d); "
            "rows = list(csv.DictReader(open(src + 'T5v2_switchcost_tuned.csv'))); "
            "rows = [{k: v for k, v in r.items() if not k.startswith('prov_')} for r in rows]; "
            "IO.write_csv('T5v3_switchcost_tuned', rows, ndigits=None); print('[]')")   # v3 name (v3_names T5)
    _py(code, dict(RBRL_RESULTS=str(dst)))


def test_tuned_base_matches_csw_key(tmp_path, monkeypatch):
    import rbrl_io as IO
    stamp_tuned_files(tmp_path)
    monkeypatch.setattr(IO, "R", str(tmp_path))
    on, off = M.tuned_rule(CITY)
    assert M.TUNED_SHA[CITY][0] == "tuned_params_v2.json"
    rows = [r for r in csv_rows("T5v2_switchcost_tuned") if r["city"] == CITY]
    r0 = rows[0]
    assert M.tuned_rule(CITY, c_sw=float(r0["c_sw"])) == (float(r0["on"]), float(r0["off"]))
    assert M.TUNED_SHA[CITY][0] == M.TUNED_CSW_FILE + ".csv" == "T5v3_switchcost_tuned.csv"
    with pytest.raises(SystemExit):
        M.tuned_rule(CITY, c_sw=0.777)                 # no silent fallback to the headline rule
    os.remove(f"{tmp_path}/tuned_params_v2.json.meta.json")
    with pytest.raises(SystemExit, match="no provenance"):
        M.tuned_rule(CITY)                             # V-code-22 (4): unstamped file refused


def csv_rows(name):
    import csv
    return list(csv.DictReader(open(f"{ROOT}/results/{name}.csv")))


def test_cth_reaches_mpc_and_dp_consistently(tmp_path):
    """V-code-17: RBRL_CTH=7200 changes mpc_lams (decay + terminal pricing), the DP and the
    replay together, consistently with setback.sim at F.C_TH; 4800 (explicit) is bit-identical
    to the default; a TUNED file fitted at another C_th is refused."""
    code = ("import mpc_lambda as M, r3_dp as D, final_tables as F, setback as S, headroom as H, json\n"
            "import numpy as np\n"
            f"w = {W}; N = {NS}\n"
            "m = M.mpc_lams('riyadh', w, [0.2], 1.0, 101, rule=(23.6, 22.35), N=N, return_actions=True)[0]\n"
            "a = np.array(m['actions']); N0, occ, lo, hi = F._ctx('riyadh', w, False)\n"
            "full = np.concatenate([a, np.zeros(N0 - N, int)])\n"
            "s = S.sim(lambda T, p, k: full[k], 'riyadh', F.FACES, F.C_TH, H.price_flat(N0, 0.18), lo, hi, occ, 168, w, F.T0, c_sw=F.C_SW, record=True)\n"
            "L = D.lagrangian('riyadh', w, 0.18, 0.2, n_grid=201)['L']\n"
            "try:\n    M.tuned_rule('riyadh'); refused = False\nexcept SystemExit:\n    refused = True\n"
            "print(json.dumps([M.C_TH, D.C_TH, F.C_TH, m['J'], m['T_end'], float(s['T_next'][N - 1]), L, refused]))")
    stamp_tuned_files(tmp_path)
    RR = dict(RBRL_RESULTS=str(tmp_path))
    d0 = _py(code, RR)
    d48 = _py(code, dict(RR, RBRL_CTH="4800"))
    d72 = _py(code, dict(RR, RBRL_CTH="7200", RBRL_TAG=""))
    assert d0 == d48 and d0[:3] == [4800.0] * 3 and d0[7] is False
    assert d72[:3] == [7200.0] * 3
    assert d72[3] != d0[3] and d72[4] != d0[4] and d72[6] != d0[6]
    assert abs(d0[5] - d0[4]) < 1e-12 and abs(d72[5] - d72[4]) < 1e-12   # same plant as setback.sim
    assert d72[7] is True                                                 # headline TUNED refused at 7200


def test_cli_cth_needs_tag():
    r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "mpc_lambda.py"), "--city", "riyadh",
                        "--cth", "7200"], capture_output=True, text=True, env=CLEAN, cwd=ROOT, timeout=120)
    assert r.returncode != 0 and "set RBRL_TAG" in r.stderr


def test_scenario_suffix():
    assert M.scenario_suffix(H.C_SW, None, None, None) == ""
    assert M.scenario_suffix(0.3, 1.01, None, None) == "_csw0.3_ls1.01"


# ------------------------------------------------------------ ruling §16: occupied-ceiling back-off
def test_backoff_zero_is_bit_identical_and_lowers_the_mean():
    """b = 0 (and the default) is the p6 MPC bit for bit; b > 0 lowers the planner's occupied
    ceiling (cooler mean) while comfort is still scored against HI."""
    a = M.mpc_lams(CITY, 121, [0.0], 1.0, 201, rule=(23.6, 22.4), N=192)[0]
    b0 = M.mpc_lams(CITY, 121, [0.0], 1.0, 201, rule=(23.6, 22.4), N=192, backoff=0.0)[0]
    assert all((v == b0[k]) or (v != v and b0[k] != b0[k]) for k, v in a.items())     # nan == nan
    b3 = M.mpc_lams(CITY, 121, [0.0], 1.0, 201, rule=(23.6, 22.4), N=192, backoff=0.3)[0]
    assert b3[M.K] < a[M.K] and b3["deg_h_over"] == 0.0 and b3["fallback_steps"] == 0


def _fake_mpc(monkeypatch, jump):
    """stand-in MPC on one tuning window: lam sets a hysteresis rule with a bang-bang jump in the
    comfort level at lam = 1 when `jump`; the back-off b lowers both thresholds by b."""
    import final_tables as F
    W1 = [F.TUNE_W[0]]
    monkeypatch.setattr(F, "TUNE_W", W1)
    def pair(l, b):
        if jump:
            on, off = (23.8, 22.9) if l < 1.0 else (23.2, 22.45)
        else:
            on, off = 23.5 + 0.4 * np.tanh(l), 22.5 - 0.2 * np.tanh(l)
        return on - b, off - b
    def fake(city, windows, lams, hh, n_grid, rule=None, price_v=0.18, ruled=False, forecast="perfect",
             backoff=None):
        b = M.BACKOFF[0] if backoff is None else backoff
        return [[dict(F.rule_run(city, w, 0.18, *pair(l, b)), fallback_steps=0) for l in lams] for w in windows]
    monkeypatch.setattr(M, "mpc_batch", fake)
    return W1


def test_backoff_knob_only_when_lam_has_no_admissible_point(monkeypatch):
    import final_tables as F
    W1 = _fake_mpc(monkeypatch, jump=True)
    lam, relaxed, allr, status = M.fit_lambda(CITY, 6.0, None, 101, lambda m: None, with_status=True)
    assert M.KNOB["knob"] == "backoff" and M.BACKOFF[0] == M.KNOB["backoff"] > 0
    assert lam < 1.0                                         # warm side of the jump
    assert status in ("pooled_0.03", "pooled_0.10")
    assert abs(round(M.BACKOFF[0] / M.BACKOFF_RES) * M.BACKOFF_RES - M.BACKOFF[0]) < 1e-9
    tgt = F._target(CITY, 0.18, W1, None)
    r = F.rule_run(CITY, W1[0], 0.18, 23.8 - M.BACKOFF[0], 22.9 - M.BACKOFF[0])
    assert F.pooled_status(r[F.MEAN_KEY] - tgt) == status


def test_lam_knob_cells_unchanged(monkeypatch):
    """a cell with an admissible lam never enters the back-off code: knob lambda, b = 0."""
    _fake_mpc(monkeypatch, jump=False)
    lam, relaxed, allr, status = M.fit_lambda(CITY, 6.0, None, 101, lambda m: None, with_status=True)
    assert lam is not None and M.KNOB == {"knob": "lambda", "backoff": 0.0} and M.BACKOFF[0] == 0.0
