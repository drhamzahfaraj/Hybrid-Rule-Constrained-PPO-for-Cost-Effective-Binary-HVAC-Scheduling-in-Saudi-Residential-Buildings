"""F23: the control / actuation interval Delta t as one config setting (config.DT_MIN, env
RBRL_DT_MIN, default 15 min) for the J24 time-step table (supplement tab:s-timestep).

  * headline Delta t = 15 is bit-identical to tag p9 (rule_run, therm_run, sim_hyst_batch,
    mpc_lams perfect + persistence on one window at a small grid, lagrangian relaxed/unrelaxed;
    golden values written on the p9 tree by tests/f23_golden.py);
  * every step count is derived from Delta t (series, N, ROLL, persistence offset);
  * the plant integration is exact at every Delta t: an hourly on/off schedule resampled to
    5/15/30/60 min gives the same hourly temperatures, energy and cost, and the zone energy
    balance closes;
  * THERM admissibility and THERM deg-h reproduce tab:s-timestep's columns;
  * non-headline Delta t needs RBRL_TAG; modules not written for a general Delta t refuse it;
  * timestep_table.py checks each input's provenance env.
Every Delta t != 15 computation runs in a subprocess (module constants are bound at import).
"""
import csv, json, os, subprocess, sys
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("RBRL_")}
HERE = os.path.dirname(os.path.abspath(__file__))


def _run(args, env=None, ok=True):
    e = dict(CLEAN, OMP_NUM_THREADS="1", **(env or {}))
    r = subprocess.run([sys.executable, "-I", "-B", *args], capture_output=True, text=True, env=e,
                       cwd=ROOT, timeout=300)
    if ok:
        assert r.returncode == 0, r.stderr[-3000:]
    return r


def _py(code, env=None):
    r = _run(["-c", f"import sys; sys.path.insert(0, {ROOT!r}); " + code], env)
    return json.loads(r.stdout.strip().splitlines()[-1])


# ------------------------------------------------------------------ headline bit-identity vs p9
def test_headline_dt_bit_identical_to_p9():
    gold = json.load(open(os.path.join(HERE, "f23_golden_p9.json")))
    now = json.loads(_run([os.path.join(HERE, "f23_golden.py")]).stdout.strip().splitlines()[-1])
    assert set(now) == set(gold)
    for k in gold:
        assert now[k] == gold[k], f"{k}: differs from tag p9 at the headline dt"


def test_default_dt_is_headline_and_exact():
    d = _py("import config as C, headroom as H, setback as S, mpc_lambda as M, json; "
            "print(json.dumps([C.DT_MIN, C.DT_H, H.DT, S.DT, C.STEPS_PER_HOUR, M.ROLL, M.N_WIN, "
            "H.series('riyadh', 168, 121)[2]]))")
    assert d == [15.0, 0.25, 0.25, 0.25, 4, 96, 672, 672]


# ------------------------------------------------------------------ derived step counts
@pytest.mark.parametrize("dt", [5, 30])
def test_step_counts_derive_from_dt(dt):
    code = ("import config as C, headroom as H, setback as S, final_tables as F, mpc_lambda as M, json, numpy as np; "
            "t, g, N = H.series('riyadh', 168, 121); t15 = np.repeat(H._epw('riyadh')[0][121*24:121*24+168], C.STEPS_PER_HOUR); "
            "src = M._persistence_src(5, 3 * M.ROLL)[0]; "
            "print(json.dumps([H.DT, S.DT, N, M.ROLL, M.N_WIN, F.WINDOWS, F.TUNE_W, F.EVAL_W, "
            "bool(np.array_equal(t, t15)), int(src[6] - 6 + 24 * C.STEPS_PER_HOUR), "
            "int(np.sum(S.occupancy(N)) - N + 6 * 5 * 60 // C.DT_MIN)]))")
    d = _py(code, dict(RBRL_DT_MIN=str(dt), RBRL_TAG=f"_dt{dt}"))
    spd = 60 // dt
    assert d[0] == d[1] == dt / 60.0
    assert d[2] == 168 * spd and d[3] == 24 * spd and d[4] == 168 * spd
    assert d[5] == list(range(121, 297, 14)) and len(d[6]) == 6 and len(d[7]) == 7   # windows in days
    assert d[8]                                   # hourly EPW held over 60/dt steps
    assert d[9] == 0                              # persistence: j beyond k uses t(j - 1 day of steps)
    assert d[10] == 0                             # setback timetable: 6 h away on 5 workdays


def test_invalid_and_untagged_dt_refused():
    r = _run(["-c", f"import sys; sys.path.insert(0, {ROOT!r}); import config"], dict(RBRL_DT_MIN="7"), ok=False)
    assert r.returncode != 0 and "whole number of steps per hour" in r.stderr
    r = _run([os.path.join(ROOT, "t1_v2.py"), "nojob"], dict(RBRL_DT_MIN="30"), ok=False)
    assert r.returncode != 0 and "set RBRL_TAG" in r.stderr
    r = _run([os.path.join(ROOT, "bound_v2.py"), "nojob"], dict(RBRL_DT_MIN="30"), ok=False)
    assert r.returncode != 0 and "set RBRL_TAG" in r.stderr
    r = _run([os.path.join(ROOT, "setback_arms.py"), "nojob"], dict(RBRL_DT_MIN="30", RBRL_TAG="_dt30"), ok=False)
    assert r.returncode != 0 and "not Delta-t generic" in r.stderr


# ------------------------------------------------------------------ exact plant at every dt
_BAL = """
import config as C, headroom as H, setback as S, numpy as np, json
spd = C.STEPS_PER_HOUR; city, w, faces, cth = 'riyadh', 135, 1, 4800.0
hourly = np.array([(h % 24) in (1, 2, 5, 9, 10, 11, 13, 14, 15, 16, 19, 20, 22) for h in range(168)], int)
u = np.repeat(hourly, spd)                        # fixed hourly schedule resampled to the step
t_out, irr, N = H.series(city, 168, w)
occ = np.ones(N, bool); lo, hi = S.bands(occ, 22.0, 24.0)
r = S.sim(lambda T, prev, k: int(u[k]), city, faces, cth, H.price_flat(N, 0.18), lo, hi, occ, 168, w,
          23.0, record=True)
# zone balance on the exact solution: C dT = lam * integral (T_inf - T) dt, per step analytically
lam = H.lam_of(faces, city); a = lam / (cth * 1e3); dts = H.DT * 3600.0
Tin = np.concatenate([[23.0], r['T_next'][:-1]])
Tinf = t_out + (H.SHGC * H.A_GL * irr - H.Q_HVAC * u) / lam
intT = Tinf * dts + (Tin - Tinf) * (1.0 - np.exp(-a * dts)) / a
flow = float(np.sum(lam * (Tinf * dts - intT)))   # J into the zone
store = (r['T_next'][-1] - 23.0) * cth * 1e3
print(json.dumps(dict(Th=r['T_next'][spd - 1::spd].tolist(), E=r['E'], J=r['J'], f_s=r['f_s'],
                      bal=(store - flow) / abs(flow), q=float(H.Q_HVAC * u.sum() * dts))))
"""


def test_plant_energy_balance_consistent_across_dt():
    res = {dt: _py(_BAL, dict(RBRL_DT_MIN=str(dt), RBRL_TAG=f"_dt{dt}") if dt != 15 else None)
           for dt in (5, 15, 30, 60)}
    ref = res[15]
    for dt, r in res.items():
        assert abs(r["bal"]) < 1e-9, f"dt={dt}: zone energy balance residual {r['bal']}"
        assert max(abs(a - b) for a, b in zip(r["Th"], ref["Th"])) < 1e-9, f"dt={dt}: hourly T differs"
        assert abs(r["E"] - ref["E"]) < 1e-12 and abs(r["q"] - ref["q"]) < 1e-6
        assert abs(r["J"] - ref["J"]) < 1e-12 and r["f_s"] == ref["f_s"]   # c_sw per start, price per kWh


# ------------------------------------------------------------------ tab:s-timestep columns
def test_therm_admissibility_matches_table():
    import headroom as H
    assert [H.step_admissible(d, 4800.0) for d in (5, 15, 30, 60)] == ["yes", "yes", "yes", "no"]
    assert [round(H.step_overshoot(d, 4800.0), 3) for d in (5, 15, 30, 60)] == [0.125, 0.375, 0.75, 1.5]
    assert [H.step_admissible(15, c) for c in (1200, 1800, 2400, 4800, 7200, 9600)] == \
        ["no", "marg.", "yes", "yes", "yes", "yes"]
    code = ("import final_tables as F, json; th = F.therm_run('riyadh', F.WINDOWS[0], 0.18); "
            "print(json.dumps([round(th['deg_h_occ'], 3), round(th['J'], 4)]))")
    got = {dt: _py(code, dict(RBRL_DT_MIN=str(dt), RBRL_TAG=f"_dt{dt}") if dt != 15 else None)
           for dt in (5, 15, 30, 60)}
    # THERM deg-h column of tab:s-timestep (and the THERM J of the round-2 T2_timestep table)
    assert {d: g[0] for d, g in got.items()} == {5: 0.0, 15: 0.0, 30: 0.025, 60: 4.470}
    assert {d: g[1] for d, g in got.items()} == {5: 1.0085, 15: 0.9246, 30: 0.8824, 60: 0.8212}


@pytest.mark.parametrize("dt", [5, 30])
def test_mpc_and_bound_paths_at_dt(dt):
    """mpc_lams (perfect and persistence, horizon 24 h) and the Lagrangian run at dt; the
    relaxation is below the unrelaxed value; a perfect-forecast callable equals 'perfect'."""
    spd = 60 // dt
    code = (f"import mpc_lambda as M, r3_dp as D, headroom as H, json; "
            f"r = M.mpc_lams('riyadh', 121, [0.0, 0.24], 24.0, n_grid=121, rule=(23.71, 22.36), N={6 * spd}); "
            f"p = M.mpc_lams('riyadh', 121, [0.24], 24.0, n_grid=121, rule=(23.71, 22.36), N={3 * spd}, forecast='persistence'); "
            f"t, g, _ = H.series('riyadh', M.HOURS, 121); "
            f"c = M.mpc_lams('riyadh', 121, [0.24], 24.0, n_grid=121, rule=(23.71, 22.36), N={3 * spd}, forecast=lambda k: (t, g)); "
            f"q = M.mpc_lams('riyadh', 121, [0.24], 24.0, n_grid=121, rule=(23.71, 22.36), N={3 * spd}); "
            f"L0 = D.lagrangian('riyadh', 121, 0.18, 0.24, n_grid=201)['L']; "
            f"L1 = D.lagrangian('riyadh', 121, 0.18, 0.24, n_grid=201, relaxed=True)['L']; "
            f"print(json.dumps([r[0]['J'], r[1]['J'], r[0]['deg_h_over'], r[0]['fallback_steps'], p[0]['J'], "
            f"bool(c[0]['J'] == q[0]['J']), float(L0), float(L1)]))")
    d = _py(code, dict(RBRL_DT_MIN=str(dt), RBRL_TAG=f"_dt{dt}"))
    assert all(x == x for x in d[:2] + d[4:5]) and d[2] == 0.0 and d[3] == 0
    assert d[5] is True
    assert d[7] <= d[6] + 1e-12


# ------------------------------------------------------------------ the J24 summary producer
def _fake(d, name, rows, env):
    with open(os.path.join(d, name + ".csv"), "w", newline="") as f:
        keys = list(rows[0]) + ["prov_env"]
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows:
            w.writerow(dict(r, prov_env=json.dumps(env)))


def test_timestep_table_reads_tagged_outputs(tmp_path):
    res, head = tmp_path / "res", tmp_path / "head"
    res.mkdir(); head.mkdir()
    sets = {"_dt5": dict(RBRL_DT_MIN="5", RBRL_TAG="_dt5"), "": {},
            "_dt30": dict(RBRL_DT_MIN="30", RBRL_TAG="_dt30"), "_cth7200": dict(RBRL_CTH="7200", RBRL_TAG="_cth7200")}
    for i, (tg, env) in enumerate(sets.items()):
        d = str(head if tg == "" else res)
        _fake(d, f"T1v3_heldout{tg}", [dict(tariff="inforce", city=c, arm="TUNED", s_pooled_eq=10 + i,
                                            dT_pooled=0.01, fit_status="pooled_0.03", params="{}")
                                       for c in ("riyadh", "jeddah", "taif")], env)
        _fake(d, f"T21v3_riyadh{tg}", [dict(horizon_h=24.0, forecast="perfect", s_pooled_eq=18 + i, dT_pooled=0.0,
                                            fit_status="pooled_0.03", knob="lambda", backoff=0.0,
                                            lam_over_lam_star=1.0, n_grid=1601)], env)
        _fake(d, f"T17v3_riyadh{tg}", [dict(bound_reported=20 + i)], env)
    env = dict(RBRL_RESULTS=str(res))
    _run([os.path.join(ROOT, "timestep_table.py"), "--headline", str(head)], env)
    rows = list(csv.DictReader(open(res / "T2v3_timestep.csv")))
    cell = {(r["row"], r["city"], r["arm"]): r for r in rows}
    assert float(cell[("dt5", "riyadh", "MPC-24")]["s"]) == 18.0
    assert float(cell[("dt15", "riyadh", "B*")]["s"]) == 21.0
    assert float(cell[("cth7200", "taif", "TUNED")]["s"]) == 13.0
    assert cell[("dt30", "riyadh", "TUNED")]["adm"] == "yes" and float(cell[("dt30", "riyadh", "TUNED")]["overshoot_K"]) == 0.75
    assert ("dt5", "jeddah", "MPC-24") not in cell                     # MPC / B*: Riyadh required only
    # a tagged input written under another dt is refused
    _fake(str(res), "T17v3_riyadh_dt30", [dict(bound_reported=1)], dict(RBRL_DT_MIN="5", RBRL_TAG="_dt30"))
    r = _run([os.path.join(ROOT, "timestep_table.py"), "--headline", str(head)], env, ok=False)
    assert r.returncode != 0 and "expected dt=30" in r.stderr
