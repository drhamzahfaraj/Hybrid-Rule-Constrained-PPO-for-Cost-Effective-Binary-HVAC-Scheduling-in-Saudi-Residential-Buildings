#!/usr/bin/env python3
"""J24 summary (F23; journal Comment 8): supplement tab:s-timestep -> results/T2v3_timestep.csv.

Reads the per-setting outputs of the full round-4 protocol and writes one row per
(setting, city, arm), arm in {TUNED, MPC-24, B*}:
    dt5      Delta t =  5 min, C_th 4800   RBRL_TAG _dt5    (RBRL_DT_MIN=5)
    dt15     Delta t = 15 min, C_th 4800   headline files   (--headline DIR, default results/)
    dt30     Delta t = 30 min, C_th 4800   RBRL_TAG _dt30   (RBRL_DT_MIN=30)
    cth7200  Delta t = 15 min, C_th 7200   RBRL_TAG _cth7200 (RBRL_CTH=7200)
  TUNED  : T1v3_heldout<tag>  (in-force tariff), s = pooled equalised saving s_pooled_eq (Rule C)
  MPC-24 : T21v3_<city><tag>  H = 24 h, perfect forecast, s_pooled_eq, knob/backoff, lam/lam*
  B*     : T17v3_<city><tag>  bound_reported (relaxed dual at THERM's pooled mean, rounded up)
Every row carries dT (pooled clipped-mean difference to THERM; blank for B*) and fit_status
(B*: "bound"). TUNED is required for all three cities; MPC-24 and B* for Riyadh (the table is
Riyadh), other cities are added when their files exist. A tagged input whose provenance env does
not carry the setting's RBRL_DT_MIN / RBRL_CTH (or a headline input that does) is refused.
fit_status 'none' rows are refused by the writer (reported as "no admissible parameter").
The deadband-form forcing condition Q*dt/C_th and the 'adm.' flag (headroom.step_admissible) are
written beside each row; 60 min is inadmissible and not run (tab:s-timestep keeps '---').

Usage: python3 timestep_table.py [--headline /home/claude/rbrl_p9/results:/home/claude/rbrl_p6/results]
"""
from __future__ import annotations
import sys, os, csv, json, argparse
sys.path.insert(0, "/home/claude/rbrl")
import config as CFG
import headroom as H
import rbrl_io as IO
import v3_names as V

SETTINGS = (("dt5", 5.0, CFG.C_TH_DEFAULT, V.DT_TAGS[5.0]),
            ("dt15", 15.0, CFG.C_TH_DEFAULT, ""),
            ("dt30", 30.0, CFG.C_TH_DEFAULT, V.DT_TAGS[30.0]),
            ("cth7200", 15.0, 7200.0, V.CTH_TAGS[7200.0]))


def _read(stem, tag, headline_dirs):
    """rows of <stem><tag>.csv (tagged: results dir; headline: the first of headline_dirs that has
    the file, e.g. the p9 MPC reruns before the p6 queue); None if absent."""
    ds = headline_dirs if tag == "" else [IO.R]
    ps = [f"{d}/{stem}{tag}.csv" for d in ds if os.path.exists(f"{d}/{stem}{tag}.csv")]
    if not ps:
        return None
    p = ps[0]
    IO.note_input(p)
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows or None


def _check_env(rows, what, dt, cth, tag):
    """the writer's RBRL_* env must be this setting's (F23 / F21 provenance)."""
    for r in rows:
        env = json.loads(r.get("prov_env") or "{}")
        d = float(env.get("RBRL_DT_MIN", CFG.DT_MIN_DEFAULT))
        c = float(env.get("RBRL_CTH", CFG.C_TH_DEFAULT))
        t = env.get("RBRL_TAG", "")
        if abs(d - dt) > 1e-9 or abs(c - cth) > 1e-9 or t != tag:
            raise SystemExit(f"{what}: written at dt={d:g} min, C_th={c:g}, tag={t!r}; "
                             f"expected dt={dt:g}, C_th={cth:g}, tag={tag!r}")


def _f(x):
    return "" if x in (None, "") else float(x)


def build(headline_dir):
    out, missing = [], []
    for key, dt, cth, tag in SETTINGS:
        base = dict(row=key, dt_min=dt, c_th=cth, overshoot_K=round(H.step_overshoot(dt, cth), 6),
                    adm=H.step_admissible(dt, cth), tag=tag)
        t1 = _read(V.name("T1"), tag, headline_dir)
        if t1 is None:
            raise SystemExit(f"{key}: {V.name('T1')}{tag}.csv missing (run t1_v2 t1 with RBRL_TAG={tag!r})")
        _check_env(t1, f"{V.name('T1')}{tag}", dt, cth, tag)
        for city in V.CITIES:
            tu = [r for r in t1 if r["city"] == city and r["arm"] == "TUNED" and r["tariff"] == "inforce"]
            if len(tu) != 1:
                missing.append(f"{key} {city} TUNED: no admissible parameter"); continue
            r = tu[0]
            out.append(dict(base, city=city, arm="TUNED", s=_f(r["s_pooled_eq"]), dT=_f(r["dT_pooled"]),
                            fit_status=r["fit_status"], params=r.get("params", ""),
                            source=f"{V.name('T1')}{tag}"))
            mp = _read(V.name("MPC", city), tag, headline_dir)
            if mp is None:
                if city == "riyadh":
                    raise SystemExit(f"{key}: {V.name('MPC', city)}{tag}.csv missing")
            else:
                _check_env(mp, f"{V.name('MPC', city)}{tag}", dt, cth, tag)
                m = [x for x in mp if abs(float(x["horizon_h"]) - 24.0) < 1e-9 and x["forecast"] == "perfect"]
                if len(m) != 1:
                    missing.append(f"{key} {city} MPC-24: no admissible parameter")
                else:
                    m = m[0]
                    out.append(dict(base, city=city, arm="MPC-24", s=_f(m["s_pooled_eq"]),
                                    dT=_f(m["dT_pooled"]), fit_status=m["fit_status"],
                                    knob=m.get("knob", "lambda") or "lambda", backoff=_f(m.get("backoff")),
                                    lam_over_lam_star=_f(m.get("lam_over_lam_star")),
                                    n_grid=int(float(m["n_grid"])), source=f"{V.name('MPC', city)}{tag}"))
            bd = _read(V.name("CLV", city), tag, headline_dir)
            if bd is None:
                if city == "riyadh":
                    raise SystemExit(f"{key}: {V.name('CLV', city)}{tag}.csv missing (bound_v2 main)")
            else:
                _check_env(bd, f"{V.name('CLV', city)}{tag}", dt, cth, tag)
                out.append(dict(base, city=city, arm="B*", s=_f(bd[0]["bound_reported"]), dT="",
                                fit_status="bound", source=f"{V.name('CLV', city)}{tag}"))
    return out, missing


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--headline", default=IO.R,
                    help="results dir(s) of the headline (dt 15, C_th 4800) files, ':'-separated, first match wins")
    a = ap.parse_args(argv)
    if IO.tag():
        raise SystemExit("timestep_table.py reads the tagged files itself: run it with RBRL_TAG unset")
    rows, missing = build([os.path.abspath(d) for d in a.headline.split(":") if d])
    for m in missing:
        print("!!", m, flush=True)
    for key, dt, cth, _ in SETTINGS:
        cell = {r["arm"]: r for r in rows if r["row"] == key and r["city"] == "riyadh"}
        txt = " / ".join(f"{cell[k]['s']:.2f}" if k in cell else "none" for k in ("TUNED", "MPC-24", "B*"))
        print(f"{key:8s} dt={dt:g} C_th={cth:g} Riyadh TUNED / MPC-24 / B* = {txt}", flush=True)
    IO.write_csv(V.name("TIMESTEP"), rows, apply_tag=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
