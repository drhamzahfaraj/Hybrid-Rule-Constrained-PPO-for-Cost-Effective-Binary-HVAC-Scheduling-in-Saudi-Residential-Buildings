#!/usr/bin/env python3
"""Inter-annual spread of the reported saving, on actual years.

The headline tables run on one TMYx year per city. This study re-runs the
paper's own protocol---tune the two-parameter rule on the tuning windows,
admit it only if comfort-matched in every one, evaluate on the disjoint
held-out windows against that year's own baseline---inside ACTUAL years
(ERA5 reanalysis, see amy_fetch.py), chosen per city as the hottest, the
median and the mildest of 2009--2023 by cooling degree-days.

Two questions, two designs, one table:
  RETUNED  -- the protocol applied within the year: what the method reports
              when commissioned on the year it serves.
  TRANSFER -- the TMYx-tuned thresholds applied unchanged to the real year,
              re-matched on nothing: what a rule commissioned once does when
              the weather is not the typical year.

What this is NOT: a replacement for the headline. ERA5 is a reanalysis on a
0.25-degree cell, not a station record, so these runs measure the SPREAD of
the saving across real years at fixed method and plant, and the TMYx figures
remain the reported ones. The weather source changes; the optics do not---the
same plane-of-array transposition is applied to the ERA5 direct and diffuse
components.
"""
from __future__ import annotations
import sys, os, csv, json, contextlib
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np

import headroom as H
import final_tables as F
from hvac import vertical_irradiance

AMY = "/home/claude/rbrl/amy"
PRICE = 0.18
K = F.MEAN_KEY


def amy_series_fn(city, year, azimuth=180.0):
    """A drop-in replacement for headroom.series reading one ERA5 year (hour-ending, F15)."""
    p = f"{AMY}/{city}_{year}.csv"
    tdb, dni, dhi = [], [], []
    for r in csv.DictReader(open(p)):
        tdb.append(float(r["tdb_C"])); dni.append(float(r["dni_Wm2"]))
        dhi.append(float(r["dhi_Wm2"]))
    return _series_from(np.array(tdb), np.array(dni), np.array(dhi), city, azimuth)


def _series_from(tdb, dni, dhi, city, azimuth):
    irr = vertical_irradiance(dni, dhi, H.CITIES[city], azimuth_deg=azimuth)
    tdb = np.asarray(tdb, float)
    spd = int(round(1.0 / H.DT))

    def series(city_, hours, start_day):
        N = int(round(hours / H.DT)); h0 = int(start_day) * 24
        t = np.repeat(tdb[h0:h0 + hours], spd)[:N]; g = np.repeat(irr[h0:h0 + hours], spd)[:N]
        t.setflags(write=False); g.setflags(write=False)     # same contract as the F3 cache
        return t, g, N
    return series


@contextlib.contextmanager
def weather(series_fn):
    """Point every simulator path (S.sim, F.sim_hyst_batch, F._ctx, shield) at another weather
    record for the duration, and drop the per-weather caches on entry and exit."""
    import shield as D1
    old = H.series
    F._THERM_CURVE.clear()  # shield now reads F directly (Rule C, 2a78a7d)
    H.series = series_fn
    try:
        yield
    finally:
        H.series = old
        F._THERM_CURVE.clear()  # shield now reads F directly (Rule C, 2a78a7d)


# ----------------------------------------------------------------- §2 protocol helpers
# RULING §2.1-2.2 is implemented ONCE in final_tables (F.admissible, F.tune_rule with fit_status);
# tune_A4 defers to it (F6/F7) with the signature (on, off, fit_status, info).
def _cands(on_v, off_v):
    return [(round(float(a), 2), round(float(b), 2)) for a in on_v for b in off_v
            if a - b >= 0.1 - 1e-9 and a <= F.OCC_HI + 1e-9 and b >= F.OCC_LO - 1e-9]


def _tune_rows(city, pairs, price_v=PRICE):
    on = np.array([p[0] for p in pairs]); off = np.array([p[1] for p in pairs])
    import shield as D1
    res = {w: F.sim_hyst_batch(city, w, price_v, on, off) for w in F.TUNE_W}
    return {p: {w: D1.rows_of(res[w], i) for w in F.TUNE_W} for i, p in enumerate(pairs)}


def tune_A4(city, price_v=PRICE, step=0.05):
    """TUNED (on, off) by Rule A4 (§2.2): final_tables.tune_rule (F7). Returns
    (on, off, fit_status, info) or (None, None, 'none', info)."""
    f = F.tune_rule(city, price_v, F.TUNE_W, step=step)
    if f is None:
        return None, None, "none", dict(F.LAST_FIT)
    return f[1], f[2], f.fit_status, dict(f.info)


def evaluate_rule(city, on_, off_, price_v=PRICE):
    """Rule C on EVAL_W (pooled equalised saving + the §2.1 metrics), via t1_v2.evaluate."""
    import t1_v2 as T1V2
    import shield as D1
    th = {w: F.therm_run(city, w, price_v) for w in F.EVAL_W}
    runs = {w: D1.rows_of(F.sim_hyst_batch(city, w, price_v, [on_], [off_]), 0) for w in F.EVAL_W}
    s, pw = T1V2.evaluate(city, price_v, runs, th)
    return s, pw


def protocol(city, price_v=PRICE):
    """The paper's protocol (§2) on whatever H.series currently points to: TUNED by A4 on
    TUNE_W, scored by Rule C on EVAL_W against this weather's own THERM(delta_w)."""
    on_, off_, status, info = tune_A4(city, price_v)
    if on_ is None:
        return dict(ok=False, fit_status="none")
    s, _ = evaluate_rule(city, on_, off_, price_v)
    return dict(ok=True, on=on_, off=off_, fit_status=status, **info, **s)


def transfer(city, on_, off_, fit_status, price_v=PRICE):
    """TMYx-tuned thresholds applied unchanged; Rule C against this weather's THERM(delta_w)."""
    s, _ = evaluate_rule(city, on_, off_, price_v)
    return dict(ok=True, on=on_, off=off_, fit_status=fit_status, **s)


def _fmt(r):
    if not r.get("ok"):
        return "no admissible parameter (fit_status none)"
    return (f"s_eq {r['s_pooled_eq']:+.2f}%  rule {r['on']:.2f}/{r['off']:.2f}  "
            f"dT {r['dT_pooled']:+.4f}  over {r['deg_h_over']:.3f}  cmd_under "
            f"{r['deg_h_cmd_under']:.3f}  [{r['fit_status']}]")


if __name__ == "__main__":
    import rbrl_io as IO
    sel = json.load(open(f"{AMY}/amy_selected.json"))
    cdd = {(r["city"], str(r["year"])): float(r["cdd24"])
           for r in csv.DictReader(open(f"{AMY}/amy_summary.csv"))}
    rows, inputs = [], [f"{AMY}/amy_summary.csv", f"{AMY}/amy_selected.json"]
    for city in ("riyadh", "jeddah", "taif"):
        base = protocol(city)                                   # TMYx (the cached EPW path)
        print(f"\n=== {city.upper()}  TMYx: {_fmt(base)} ===", flush=True)
        rows.append(dict(city=city, year="TMYx", kind="RETUNED", cdd=None, **base))
        inputs.append(f"{IO.ROOT}/{city}.epw")
        for kind in ("mild", "median", "hot"):
            year = sel[city][kind]
            path = f"{AMY}/{city}_{year}.csv"
            if not os.path.exists(path):
                raise FileNotFoundError(path)                   # no silent skip (F18 spirit)
            inputs.append(path)
            with weather(amy_series_fn(city, year)):
                r1 = protocol(city)
                r2 = transfer(city, base["on"], base["off"], base["fit_status"]) if base["ok"] \
                    else dict(ok=False, fit_status="none")
            c = cdd.get((city, str(year)))
            print(f"  {year} ({kind}, CDD {c:.0f})  RETUNED  {_fmt(r1)}", flush=True)
            print(f"  {'':24s}TRANSFER {_fmt(r2)}", flush=True)
            rows.append(dict(city=city, year=year, kind="RETUNED", cdd=c, **r1))
            rows.append(dict(city=city, year=year, kind="TRANSFER", cdd=c, **r2))
    ok = [r for r in rows if r.get("fit_status") != "none"]
    import v3_names as V
    IO.write_csv(V.name("AMY"), ok, inputs=inputs, impl="amy_spread.py")
    for r in rows:
        if r.get("fit_status") == "none":
            print(f"  not tabulated (no admissible parameter): {r['city']} {r['year']} {r['kind']}")
    print("\n-> results/T23v3_amy_spread.csv")
