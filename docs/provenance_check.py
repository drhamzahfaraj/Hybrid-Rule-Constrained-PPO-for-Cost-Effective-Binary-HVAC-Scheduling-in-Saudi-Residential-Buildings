#!/usr/bin/env python3
"""Value-by-value provenance map for the round-4 manuscript, checked against the result files.

Every entry below names a printed value (table cell or sentence of the abstract / conclusions),
the result file, column and row filter it is read from, and how it is computed. The script reads
the CSVs (never writes to results/), formats each value at the printed precision and compares it
with the printed string. It then looks up, for every source file, its provenance stamp
(<file>.meta.json: code sha -> code tag, argv, RBRL_* environment, UTC) and the job that ran it
(code/jobs/*.jsonl and docs/jobs/*.jsonl, matched on command and environment).

    python3 docs/provenance_check.py            # print the check, exit 1 on any mismatch
    python3 docs/provenance_check.py --write    # also (re)write docs/PROVENANCE.md

Paths are repository-relative (results/, code/jobs/, docs/jobs/). Needs Python 3 only.
"""
from __future__ import annotations
import csv, glob, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RES = os.environ.get("RBRL_RESULTS", os.path.join(REPO, "results"))
CITIES = ("riyadh", "jeddah", "taif")
CN = {"riyadh": "Riyadh", "jeddah": "Jeddah", "taif": "Taif"}

# code sha (rbrl_io.code_sha_now over code/*.py) of each tag of the private working repository;
# results are stamped with the sha of the code that produced them. code/ in this release = p13.
TAG_OF_SHA = {"e2edc1977534": "p18 (1807829)", "e4d7eb184ea5": "p16 (3021d83)", "efbca8c69379": "p15 (d9d14a1)", "4456d5d606cb": "p13 (ad73590)", "0dfeff39fa25": "p12 (280f533)",
              "f8fb2cd89384": "p11 (d9b327f)", "5ca2e0ff7e9d": "p10 (818f270)",
              "746846849b97": "p9 (9ce9142)", "b64c08d6b645": "p8 (d837b4a)",
              "ba2229db8d46": "p7 (989b324)", "5020e03ec6ca": "p6 (c5c2fdb)",
              "b0af014ede8f": "p5 (bac4ec7)", "53dd44e2371b": "p4 (19cdbcf)",
              "9a0eb5b7471b": "42c01ee (p12 + setpoint_sens.py; the commit before p13, at which the 188-invariant gate ran)"}

# ------------------------------------------------------------------ reading
_CACHE = {}


def rows(stem):
    if stem not in _CACHE:
        p = os.path.join(RES, stem + ".csv")
        _CACHE[stem] = list(csv.DictReader(open(p))) if os.path.exists(p) else None
    if _CACHE[stem] is None:
        raise FileNotFoundError(stem + ".csv")
    return _CACHE[stem]


def _eq(a, v):
    if isinstance(v, float):
        try:
            return abs(float(a) - v) < 1e-9
        except (TypeError, ValueError):
            return False
    return str(a) == str(v)


def sel(stem, **f):
    out = [r for r in rows(stem) if all(_eq(r.get(k), v) for k, v in f.items())]
    if not out:
        raise LookupError(f"{stem}: no row with {f}")
    return out


def one(stem, col, **f):
    r = sel(stem, **f)
    if len(r) != 1:
        raise LookupError(f"{stem}: {len(r)} rows with {f}")
    return float(r[0][col])


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def sar(pw, c_sw, price=0.18, days=184):
    """three-layer money: 184 [c_sw (f_eq - f_arm) + p (E_eq - E_arm)], means over the windows."""
    m = lambda k: mean(float(r[k]) for r in pw)
    return days * (c_sw * (m("fs_eq") - m("fs_arm")) + price * (m("E_eq") - m("E_arm")))


# ------------------------------------------------------------------ formatting / matching
def fmt_like(v, printed):
    """format v at the precision (and sign style) of the printed string."""
    p = printed.strip().replace("−", "-")
    up = p.startswith("<=")
    core = p[2:] if up else p
    d = len(core.split(".")[1]) if "." in core else 0
    if up:                                       # bounds are rounded outward (up) to 0.1 point
        v = math.ceil(round(v * 10 ** d, 9)) / 10 ** d
        return "<=" + f"{v:.{d}f}"
    s = f"{v:+.{d}f}" if core.startswith("+") else f"{v:.{d}f}"
    if s in ("-0.0", "-0.00", "-0.000", "-0") and not core.startswith("-"):  # negative zero prints as 0 unless printed with its sign
        s = s[1:]
    if core.startswith("+") and s.startswith("+-"):
        s = s[1:]
    return s


ENTRIES = []   # dict(loc, item, printed, src, how, fn)


def E(loc, item, printed, src, how, fn):
    ENTRIES.append(dict(loc=loc, item=item, printed=printed, src=src, how=how, fn=fn))


S_HOW = "s = 100 (1 - sum_w J_arm / sum_w J_THERM(delta_w)) over the 7 held-out windows (Rule C)"
DT_HOW = "pooled clipped occupied mean of the arm minus THERM (unshifted), K"
ON_HOW = "change in on-commands vs the equalised baseline = -start_sav_eq"
SUMMARY_COLS = "s_pooled_eq | dT_pooled | -start_sav_eq"


def triple(loc, label, stem, f, fit=True):
    """s, dT, on of one summary row (tab:main convention)."""
    E(loc, label + ": s", None, f"{stem} [{fmtf(f)}] s_pooled_eq", S_HOW, lambda: one(stem, "s_pooled_eq", **f))
    E(loc, label + ": dT~", None, f"{stem} [{fmtf(f)}] dT_pooled", DT_HOW, lambda: one(stem, "dT_pooled", **f))
    E(loc, label + ": on", None, f"{stem} [{fmtf(f)}] start_sav_eq", ON_HOW, lambda: -one(stem, "start_sav_eq", **f))


def fmtf(f):
    return ", ".join(f"{k}={v}" for k, v in f.items())


def fill(values):
    """attach printed strings, in order, to the entries just added with printed=None."""
    pend = [e for e in ENTRIES if e["printed"] is None]
    assert len(pend) == len(values), (len(pend), len(values), pend[0]["item"] if pend else None)
    for e, v in zip(pend, values):
        e["printed"] = v


# ================================================================== tab:main
L = "tab:main"
for c in CITIES:
    E(L, f"THERM J (SAR/day), {CN[c]}", None, "T1v3_heldout [tariff=inforce, arm=TUNED] J_therm0_mean",
      "mean over held-out windows of THERM's (unshifted) daily cost", lambda c=c: one("T1v3_heldout", "J_therm0_mean", city=c, tariff="inforce", arm="TUNED"))
    E(L, f"THERM on-commands/day, {CN[c]}", None, "T1v3_heldout [tariff=inforce, arm=TUNED] fs_therm0_mean",
      "mean over held-out windows of THERM's on-commands per day", lambda c=c: one("T1v3_heldout", "fs_therm0_mean", city=c, tariff="inforce", arm="TUNED"))
fill(["1.118", "4.10", "0.993", "3.73", "0.614", "2.33"])
for arm, lab in (("TUNED", "TUNED"), ("guard", "Guard hysteresis")):
    for c in CITIES:
        triple(L, f"{lab}, {CN[c]}", "T1v3_heldout", dict(city=c, tariff="inforce", arm=arm))
fill(["12.5", "+0.011", "-22.8", "13.6", "+0.029", "-24.2", "12.4", "+0.005", "-21.7",
      "5.7", "+0.036", "-10.5", "7.6", "+0.035", "-13.6", "11.0", "+0.056", "-19.3"])
for c in CITIES[:2]:   # RBRL Riyadh/Jeddah: every seed rounds to the printed value; checked on seed 43
    for col, how, sgn in (("s_pooled_eq", S_HOW, 1), ("dT_pooled", DT_HOW, 1), ("start_sav_eq", ON_HOW, -1)):
        E(L, f"RBRL 5 seeds, {CN[c]}: {col} (all seeds, min..max)", None, f"rbrl_ppo5_v3_{c} [all 5 seeds] {col}",
          how + "; every seed rounds to the printed value",
          lambda c=c, col=col, sgn=sgn: (min(sgn * float(r[col]) for r in rows(f"rbrl_ppo5_v3_{c}")),
                                         max(sgn * float(r[col]) for r in rows(f"rbrl_ppo5_v3_{c}"))))
fill([("5.7", "5.7"), ("+0.036", "+0.036"), ("-10.5", "-10.5"), ("7.6", "7.6"), ("+0.035", "+0.035"), ("-13.6", "-13.6")])
E(L, "RBRL 5 seeds, Taif: s min--max", ("8.6", "11.0"), "rbrl_ppo5_v3_taif [5 seeds] s_pooled_eq", S_HOW + "; range over seeds",
  lambda: (min(float(r["s_pooled_eq"]) for r in rows("rbrl_ppo5_v3_taif")), max(float(r["s_pooled_eq"]) for r in rows("rbrl_ppo5_v3_taif"))))
for c in CITIES:
    triple(L, f"D1 shield on latch (sigma=0), {CN[c]}", f"T_D1_latch_{c}", dict(sigma=0.0))
fill(["14.0", "-0.009", "-25.4", "13.5", "+0.021", "-24.0", "12.4", "+0.005", "-21.7"])
for c, pr in zip(CITIES, (("12.8", "14.1"), ("11.2", "13.5"), ("8.0", "12.0"))):
    E(L, f"D1 on PPO, 5 seeds, {CN[c]}: s min--max", pr, f"T_D1_ppo_{c} [sigma=0, 5 models] s_pooled_eq", S_HOW + "; range over the 5 saved PPO models",
      lambda c=c: (min(float(r["s_pooled_eq"]) for r in sel(f"T_D1_ppo_{c}", sigma=0.0)), max(float(r["s_pooled_eq"]) for r in sel(f"T_D1_ppo_{c}", sigma=0.0))))
MAINP = {0.25: ["-3.9", "+0.058", "+7.1", "1.6", "+0.023", "-2.9", "1.0", "+0.034", "-1.8"],
         1.0: ["10.1", "+0.024", "-18.4", "10.1", "+0.001", "-17.9", "6.8", "+0.009", "-11.9"],
         2.0: ["7.0", "-0.099", "-12.7", "10.2", "-0.062", "-18.2", "9.2", "-0.003", "-16.2"],
         6.0: ["15.1", "-0.021", "-27.4", "16.3", "+0.022", "-28.9", "15.9", "-0.005", "-28.0"],
         24.0: ["18.3", "+0.014", "-33.3", "18.1", "-0.011", "-32.0", "16.9", "-0.011", "-29.8"],
         48.0: ["17.6", "-0.018", "-32.0", "17.5", "-0.012", "-31.1", "18.9", "+0.089", "-33.4"]}
for h, vals in MAINP.items():
    for c in CITIES:
        triple(L, f"MPC {h:g} h perfect, {CN[c]}", f"T21v3_{c}", dict(horizon_h=h, forecast="perfect"))
    fill(vals)
for h, cs, vals in ((6.0, ("riyadh", "taif"), ["14.4", "-0.004", "-26.3", "14.0", "+0.003", "-24.6"]),
                    (24.0, CITIES, ["12.7", "-0.076", "-23.2", "14.6", "-0.037", "-25.9", "10.8", "-0.086", "-18.8"])):
    for c in cs:
        triple(L, f"MPC {h:g} h persistence, {CN[c]}", f"T21v3_pers_{c}", dict(horizon_h=h, forecast="persistence"))
    fill(vals)
GUARD = {"riyadh": "23.6-22.4", "jeddah": "23.62-22.4", "taif": "23.66-22.4"}
TRAIN = {1.0: ["9.7", "+0.115", "-17.7", "-3.6", "-0.053", "+6.5", "-1.8", "-0.023", "+3.1"],
         6.0: ["10.7", "-0.028", "-19.4", "10.9", "-0.006", "-19.3", "11.1", "-0.016", "-19.4"],
         24.0: ["11.6", "-0.061", "-21.1", "14.1", "-0.003", "-24.9", "10.0", "-0.064", "-17.6"]}
GRULE = {1.0: ["2.5", "+0.038", "-4.5", "1.5", "+0.051", "-2.8", "8.0", "+0.064", "-14.2"],
         6.0: ["6.4", "+0.025", "-11.7", "7.6", "+0.024", "-13.5", "9.5", "+0.076", "-16.7"],
         24.0: ["6.7", "+0.028", "-12.3", "4.4", "+0.068", "-7.7", "10.5", "+0.043", "-18.6"]}
for h, vals in TRAIN.items():
    for c in CITIES:
        triple(L, f"MPC {h:g} h, training rules 23.80/22.40, {CN[c]}", f"T16v3_r23.8-22.4_{c}", dict(horizon_h=h))
    fill(vals)
for h, vals in GRULE.items():
    for c in CITIES:
        triple(L, f"MPC {h:g} h, guard rules {GUARD[c]}, {CN[c]}", f"T16v3_r{GUARD[c]}_{c}", dict(horizon_h=h))
    fill(vals)
for c, vals in zip(CITIES, (["18.0", "-0.036", "-31.1"], ["18.4", "-0.018", "-31.2"], ["16.7", "-0.025", "-26.1"])):
    E(L, f"CLV raw, {CN[c]}: s", vals[0], f"T17v3_{c} clv_s_raw", "clairvoyant schedule vs UNSHIFTED THERM, O4 terminal V_N", lambda c=c: one(f"T17v3_{c}", "clv_s_raw"))
    E(L, f"CLV raw, {CN[c]}: dT~", vals[1], f"T17v3_{c} clv_dT_pooled", DT_HOW, lambda c=c: one(f"T17v3_{c}", "clv_dT_pooled"))
    E(L, f"CLV raw, {CN[c]}: on", vals[2], f"T17v3_{c} clv_start_sav", "-clv_start_sav (on-commands vs equalised THERM)", lambda c=c: -one(f"T17v3_{c}", "clv_start_sav"))
for c, pe, pv in (("riyadh", "<=20.0", "<=20.0"), ("jeddah", "<=20.1", "<=19.9")):
    E(L, f"B* energy-only terminal, {CN[c]}", pe, f"T17v2_{c} [setback=False] bound_reported (unstamped file)",
      "relaxed Lagrangian dual bound, simulator (energy-only) terminal, rounded up to 0.1", lambda c=c: one(f"T17v2_{c}", "bound_reported", setback="False"))
    E(L, f"B* V_N terminal, {CN[c]}", pv, f"T17v3_{c} bound_reported", "relaxed dual bound under the O4 terminal V_N, min over relaxed grids, rounded up to 0.1",
      lambda c=c: one(f"T17v3_{c}", "bound_reported"))
E(L, "B* V_N terminal, Taif", "<=21.0", "T17v3_taif bound_reported", "as above", lambda: one("T17v3_taif", "bound_reported"))
for c, cl, rb in (("riyadh", "12.9", "<=14.9"), ("jeddah", "13.8", "<=15.6"), ("taif", "12.3", "<=16.2")):
    E(L, f"CLV in rules (raw), {CN[c]}", cl, f"T17v3_ruled_{c} clv_s_raw", "clairvoyant schedule inside the training rules, vs unshifted THERM",
      lambda c=c: one(f"T17v3_ruled_{c}", "clv_s_raw"))
    E(L, f"ruled bound, {CN[c]}", rb, f"T17v3_ruled_{c} bound_reported", "relaxed dual bound inside the rules (12801 nodes), rounded up",
      lambda c=c: one(f"T17v3_ruled_{c}", "bound_reported"))

# ================================================================== tab:layers
L = "tab:layers"


def pw_of(arm, c):
    if arm == "TUNED" or arm == "guard":
        return sel("T1v3_perwindow", city=c, arm=arm, tariff="inforce")
    if arm == "D1":
        return sel(f"T_D1_latch_{c}_perwindow", sigma=0.0)
    if arm == "MPC24":
        return sel(f"T21v3_{c}_perwindow", horizon_h=24.0, forecast="perfect")
    if arm == "MPCp24":
        return sel(f"T21v3_pers_{c}_perwindow", horizon_h=24.0)
    if arm == "TUNED-SB":
        return sel("T28v3_setback_rule_perwindow", city=c, arm="TUNED-SB")
    if arm == "MPC-SB":
        return rows(f"T28v3_setback_mpc_{c}_perwindow")
    raise KeyError(arm)


SUMSTEM = {"TUNED": lambda c: ("T1v3_heldout", dict(city=c, arm="TUNED", tariff="inforce")),
           "guard": lambda c: ("T1v3_heldout", dict(city=c, arm="guard", tariff="inforce")),
           "D1": lambda c: (f"T_D1_latch_{c}", dict(sigma=0.0)),
           "MPC24": lambda c: (f"T21v3_{c}", dict(horizon_h=24.0, forecast="perfect")),
           "MPCp24": lambda c: (f"T21v3_pers_{c}", dict(horizon_h=24.0)),
           "TUNED-SB": lambda c: ("T28v3_setback_rule", dict(city=c, arm="TUNED-SB")),
           "MPC-SB": lambda c: (f"T28v3_setback_mpc_{c}", {})}
PWSTEM = {"TUNED": "T1v3_perwindow", "guard": "T1v3_perwindow", "D1": "T_D1_latch_{c}_perwindow",
          "MPC24": "T21v3_{c}_perwindow", "MPCp24": "T21v3_pers_{c}_perwindow",
          "TUNED-SB": "T28v3_setback_rule_perwindow", "MPC-SB": "T28v3_setback_mpc_{c}_perwindow"}
LAYERS = {"TUNED": [("22.8", "-0.3", "4", "19", "25"), ("24.2", "+0.5", "5", "19", "25"), ("21.7", "-0.5", "2", "10", "14")],
          "guard": [("10.5", "-0.4", "2", "8", "11"), ("13.6", "0.0", "2", "10", "14"), ("19.3", "0.0", "2", "9", "12")],
          "D1": [("25.4", "+0.7", "5", "22", "29"), ("24.0", "-0.7", "3", "18", "24"), ("21.7", "0.0", "2", "11", "14")],
          "MPC24": [("33.3", "-0.4", "6", "28", "37"), ("32.0", "+1.2", "6", "26", "34"), ("29.8", "+0.8", "4", "15", "20")],
          "MPCp24": [("23.2", "-0.2", "4", "20", "26"), ("25.9", "+0.7", "5", "21", "27"), ("18.8", "-1.2", "1", "9", "12")],
          "TUNED-SB": [("33.6", "-0.2", "6", "28", "37"), ("35.0", "+0.6", "6", "28", "36"), ("29.2", "-0.8", "3", "14", "18")],
          "MPC-SB": [("42.3", "+0.6", "9", "37", "49"), ("39.7", "+2.1", "8", "33", "42"), ("39.3", "+3.3", "6", "21", "28")]}
for arm, cells in LAYERS.items():
    for c, (on, en, lo, hi, ref) in zip(CITIES, cells):
        st, f = SUMSTEM[arm](c)
        pws = PWSTEM[arm].format(c=c)
        E(L, f"{arm}, {CN[c]}: On (%)", on, f"{st} [{fmtf(f)}] start_sav_eq", "on-commands avoided vs the comfort-equalised THERM, pooled: 100 (1 - sum f_arm / sum f_eq)",
          lambda st=st, f=f: one(st, "start_sav_eq", **f))
        E(L, f"{arm}, {CN[c]}: Energy (%)", en, f"{st} [{fmtf(f)}] energy_sav_eq", "electricity saved vs equalised THERM: 100 (1 - sum E_arm / sum E_eq)",
          lambda st=st, f=f: one(st, "energy_sav_eq", **f))
        for cs, pr in ((0.025, lo), (0.114, hi), (0.15, ref)):
            E(L, f"{arm}, {CN[c]}: SAR/season at c_sw={cs}", pr, f"{pws} fs_arm, fs_eq, E_arm, E_eq",
              "184 [c_sw (mean f_eq - mean f_arm) + 0.18 (mean E_eq - mean E_arm)], means over the 7 held-out windows",
              lambda arm=arm, c=c, cs=cs: sar(pw_of(arm, c), cs))

# ================================================================== tab:stats
L = "tab:stats"
STATS = {("F1", "riyadh"): ("+12.6", "+11.4", "+13.8", "7/0", "0.016", "0.016", "0.047", "+12.5", "res.", "+0.011"),
         ("F1", "jeddah"): ("+13.7", "+12.3", "+15.3", "7/0", "0.016", "0.016", "0.047", "+13.6", "res.", "+0.029"),
         ("F1", "taif"): ("+11.8", "+10.6", "+14.4", "7/0", "0.016", "0.016", "0.047", "+12.4", "res.", "+0.005"),
         ("F2", "riyadh"): ("+6.0", "+3.8", "+7.5", "7/0", "0.016", "0.016", "0.047", "+5.7", "res.", "+0.004"),
         ("F2", "jeddah"): ("+4.2", "+3.8", "+5.3", "7/0", "0.016", "0.016", "0.047", "+4.4", "res.", "-0.040"),
         ("F2", "taif"): ("+4.6", "+2.0", "+8.0", "7/0", "0.016", "0.016", "0.047", "+4.5", "res.", "-0.017"),
         ("F3", "riyadh"): ("-0.1", "-2.9", "+2.7", "3/4", "0.812", "1.000", "0.812", "+0.2", "n.r.", "-0.087"),
         ("F3", "jeddah"): ("+0.9", "-0.0", "+1.9", "4/3", "0.219", "1.000", "0.438", "+1.0", "n.r.", "-0.066"),
         ("F3", "taif"): ("-1.9", "-5.8", "+1.3", "1/6", "0.109", "0.125", "0.328", "-1.6", "n.r.", "-0.092"),
         ("F4", "riyadh"): ("-6.6", "-7.7", "-5.6", "0/7", "0.016", "0.016", "0.047", "-6.8", "res.", "+0.025"),
         ("F4", "jeddah"): ("-6.0", "-6.8", "-5.2", "0/7", "0.016", "0.016", "0.047", "-6.0", "res.", "+0.006"),
         ("F4", "taif"): ("+0.0", "-3.0", "+0.1", "5/2", "0.938", "0.453", "0.938", "-1.4", "n.r.", "+0.051")}
DTARM = {"TUNED": lambda c: one("T1v3_heldout", "dT_pooled", city=c, arm="TUNED", tariff="inforce"),
         "guard": lambda c: one("T1v3_heldout", "dT_pooled", city=c, arm="guard", tariff="inforce"),
         "THERM": lambda c: 0.0,
         "MPC24": lambda c: one(f"T21v3_{c}", "dT_pooled", horizon_h=24.0, forecast="perfect"),
         "MPCp24": lambda c: one(f"T21v3_pers_{c}", "dT_pooled", horizon_h=24.0)}
for (fam, c), v in STATS.items():
    lab = f"{fam} {CN[c]}"
    g = lambda col, fam=fam, c=c: sel("T20v3_paired_stats", family=fam, city=c)[0][col]
    E(L, lab + ": HL", v[0], "T20v3_paired_stats [family, city] hl", "Hodges-Lehmann estimate of the per-window difference s_w(a) - s_w(b), points", lambda g=g: float(g("hl")))
    E(L, lab + ": CI low", v[1], "... hl_lo", "exact 95.3 % CI (Walsh averages, n = 7)", lambda g=g: float(g("hl_lo")))
    E(L, lab + ": CI high", v[2], "... hl_hi", "as above", lambda g=g: float(g("hl_hi")))
    E(L, lab + ": +/-", v[3], "... n_pos / n_neg", "windows with positive / negative difference", lambda g=g: f"{g('n_pos')}/{g('n_neg')}")
    E(L, lab + ": p_W", v[4], "... p_wilcoxon", "exact two-sided Wilcoxon signed-rank p", lambda g=g: float(g("p_wilcoxon")))
    E(L, lab + ": p_sign", v[5], "... p_sign", "exact two-sided sign-test p", lambda g=g: float(g("p_sign")))
    E(L, lab + ": p_adj", v[6], "... p_adj", "Holm adjustment within the three-city family", lambda g=g: float(g("p_adj")))
    E(L, lab + ": pooled delta s", v[7], "... d_pooled", "s_pooled(a) - s_pooled(b), from unrounded values", lambda g=g: float(g("d_pooled")))
    E(L, lab + ": resolution", v[8], "... resolution", "'resolved' iff |d_pooled| >= 3 points and the test family is significant",
      lambda g=g: {"resolved": "res.", "not resolved": "n.r.", "not_resolved": "n.r."}.get(g("resolution"), g("resolution")))
    E(L, lab + ": dT~a - dT~b", v[9], "dT_pooled of arm_a and arm_b (T1v3_heldout / T21v3_<c> / T21v3_pers_<c>)", "difference of the two arms' pooled clipped-mean offsets, K",
      lambda g=g, c=c: DTARM[g("arm_a")](c) - DTARM[g("arm_b")](c))

# ================================================================== tab:sota (this work)
L = "tab:sota"
E(L, "This work: TUNED Riyadh", "12.5", "T1v3_heldout [riyadh, TUNED, inforce] s_pooled_eq", S_HOW, lambda: one("T1v3_heldout", "s_pooled_eq", city="riyadh", arm="TUNED", tariff="inforce"))
E(L, "This work: MPC-24 h Riyadh", "18.3", "T21v3_riyadh [24 h, perfect] s_pooled_eq", S_HOW, lambda: one("T21v3_riyadh", "s_pooled_eq", horizon_h=24.0, forecast="perfect"))
E(L, "This work: bracket low (CLV raw)", "18.0", "T17v3_riyadh clv_s_raw", "clairvoyant schedule vs unshifted THERM", lambda: one("T17v3_riyadh", "clv_s_raw"))
E(L, "This work: bracket high (B*)", "<=20.0", "T17v3_riyadh bound_reported", "relaxed dual bound, V_N, rounded up", lambda: one("T17v3_riyadh", "bound_reported"))

# ================================================================== tab:sensitivity (Riyadh)
L = "tab:sensitivity"
share = lambda stem, csw, **f: 100 * csw * one(stem, "fs_therm0_mean", **f) / one(stem, "J_therm0_mean", **f)
SHARE_HOW = "THERM on-command share of cost = 100 c_sw f_s / J (THERM, unshifted, held-out mean)"
for tar, pr, sh, s in (("historical", 0.05, "81.5", "18.6"), ("inforce", 0.18, "55.0", "12.5"), ("y2027", 0.21, "51.2", "11.6")):
    E(L, f"(a) tariff {pr}: THERM share", sh, f"T1v3_heldout [riyadh, TUNED, tariff={tar}] fs_therm0_mean, J_therm0_mean", SHARE_HOW,
      lambda tar=tar: share("T1v3_heldout", 0.15, city="riyadh", arm="TUNED", tariff=tar))
    E(L, f"(a) tariff {pr}: TUNED", s, f"T1v3_heldout [riyadh, TUNED, tariff={tar}] s_pooled_eq", S_HOW,
      lambda tar=tar: one("T1v3_heldout", "s_pooled_eq", city="riyadh", arm="TUNED", tariff=tar))
for pr, b in ((0.05, "<=29.6"), (0.21, "<=18.6")):
    E(L, f"(a) tariff {pr}: B*", b, f"T4v3_bound [riyadh, price={pr}] bound_reported", "relaxed dual bound, V_N, rounded up", lambda pr=pr: one("T4v3_bound", "bound_reported", city="riyadh", price=pr))
for csw, sh, s in ((0.0, "0.0", "0.0"), (0.025, "16.9", "3.8"), (0.05, "29.0", "6.6"), (0.1, "44.9", "10.2"), (0.114, "48.2", "11.0"),
                   (0.15, "55.0", "12.5"), (0.2, "62.0", "14.1"), (0.3, "71.0", "16.2"), (0.6, "83.0", "18.9")):
    E(L, f"(b) c_sw {csw}: THERM share", sh, f"T5v3_switchcost_tuned [riyadh, c_sw={csw}] fs_therm0_mean, J_therm0_mean", SHARE_HOW,
      lambda csw=csw: share("T5v3_switchcost_tuned", csw, city="riyadh", c_sw=csw))
    E(L, f"(b) c_sw {csw}: TUNED", s, f"T5v3_switchcost_tuned [riyadh, c_sw={csw}] s_pooled_eq", S_HOW + "; TUNED refitted at each c_sw",
      lambda csw=csw: one("T5v3_switchcost_tuned", "s_pooled_eq", city="riyadh", c_sw=csw))
for csw, m, b in ((0.025, "5.7", "<=6.3"), (0.114, "16.1", "<=17.5")):
    E(L, f"(b) c_sw {csw}: MPC-24 h", m, f"T21v3_csw{csw:g}_riyadh [24 h] s_pooled_eq", S_HOW, lambda csw=csw: one(f"T21v3_csw{csw:g}_riyadh", "s_pooled_eq", horizon_h=24.0))
    E(L, f"(b) c_sw {csw}: B*", b, f"T5v3_bound [riyadh, c_sw={csw}] bound_reported", "relaxed dual bound, V_N, rounded up", lambda csw=csw: one("T5v3_bound", "bound_reported", city="riyadh", c_sw=csw))
for db, fs, s in ((0.5, "7.37", "40.2"), (0.75, "5.22", "23.4"), (1.0, "4.10", "12.5"), (1.25, "3.45", "5.7")):
    E(L, f"(c) deadband {db}: THERM on/day", fs, f"T7v3_deadband [riyadh, deadband={db}] therm_fs", "THERM on-commands/day at that deadband", lambda db=db: one("T7v3_deadband", "therm_fs", city="riyadh", deadband=db))
    E(L, f"(c) deadband {db}: TUNED", s, f"T7v3_deadband [riyadh, deadband={db}] s_pooled_eq", S_HOW + " against THERM with that deadband", lambda db=db: one("T7v3_deadband", "s_pooled_eq", city="riyadh", deadband=db))
E(L, "(c) deadband 1.00: MPC-24 h", "18.3", "T21v3_riyadh [24 h, perfect] s_pooled_eq", S_HOW, lambda: one("T21v3_riyadh", "s_pooled_eq", horizon_h=24.0, forecast="perfect"))
for tag, fs, t, m in (("_cth2400", "7.43", "-2.8", "12.2"), ("", "4.10", "12.5", "18.3"), ("_cth7200", "2.94", "16.0", "19.8"), ("_cth9600", "2.24", "15.8", "16.2")):
    st = f"T1v3_heldout{tag}"
    E(L, f"(d) C_th{tag or ' 4800'}: THERM on/day", fs, f"{st} [riyadh, TUNED, inforce] fs_therm0_mean", "THERM on-commands/day", lambda st=st: one(st, "fs_therm0_mean", city="riyadh", arm="TUNED", tariff="inforce"))
    E(L, f"(d) C_th{tag or ' 4800'}: TUNED", t, f"{st} [riyadh, TUNED, inforce] s_pooled_eq", S_HOW, lambda st=st: one(st, "s_pooled_eq", city="riyadh", arm="TUNED", tariff="inforce"))
    E(L, f"(d) C_th{tag or ' 4800'}: MPC-24 h", m, f"T21v3_riyadh{tag} [24 h] s_pooled_eq", S_HOW, lambda tag=tag: one(f"T21v3_riyadh{tag}", "s_pooled_eq", horizon_h=24.0, forecast="perfect"))
E(L, "(d) C_th 7200: B*", "<=20.0", "T17v3_riyadh_cth7200 bound_reported", "relaxed dual bound, V_N, rounded up", lambda: one("T17v3_riyadh_cth7200", "bound_reported"))
E(L, "caption: TUNED switch points for c_sw > 0 (on/off)", "23.71/22.36", "T5v3_switchcost_tuned [riyadh, c_sw=0.025..0.6] on, off", "fitted R1/R2 (identical at every c_sw > 0)",
  lambda: "/".join(sorted({f"{float(r['on']):.2f}/{float(r['off']):.2f}" for r in sel("T5v3_switchcost_tuned", city="riyadh") if float(r["c_sw"]) > 0})))
E(L, "caption: TUNED switch points at c_sw = 0", "23.54/22.39", "T5v3_switchcost_tuned [riyadh, c_sw=0] on, off", "fitted R1/R2",
  lambda: "{:.2f}/{:.2f}".format(*[one("T5v3_switchcost_tuned", k, city="riyadh", c_sw=0.0) for k in ("on", "off")]))

# ================================================================== tab:timestep (and S1)
L = "tab:timestep"
TS = {("dt5", "riyadh"): ("25.0", "23.8", "<=27.3"), ("dt5", "jeddah"): ("24.8", None, None), ("dt5", "taif"): ("25.7", None, None),
      ("dt15", "riyadh"): ("12.5", "18.3", "<=20.0"), ("dt15", "jeddah"): ("13.6", "18.1", "<=19.9"), ("dt15", "taif"): ("12.4", "16.9", "<=21.0"),
      ("dt30", "riyadh"): ("-1.2", "6.6", "<=10.9"), ("dt30", "jeddah"): ("-1.5", "11.4", "<=13.9"), ("dt30", "taif"): ("-1.2", "11.3", "<=14.7"),
      ("cth7200", "riyadh"): ("16.0", "19.8", "<=20.0"), ("cth7200", "jeddah"): ("16.7", None, None), ("cth7200", "taif"): ("17.7", None, None)}
for (rw, c), vals in TS.items():
    for arm, v in zip(("TUNED", "MPC-24", "B*"), vals):
        if v is None:
            continue
        E(L, f"{rw} {arm} {CN[c]}", v, f"T2v3_timestep [row={rw}, city={c}, arm={arm}] s (copied from the 'source' file named in the row)",
          "timestep_table.py collects s_pooled_eq of TUNED / MPC-24 and bound_reported of B* from the tagged runs", lambda rw=rw, c=c, arm=arm: one("T2v3_timestep", "s", row=rw, city=c, arm=arm))
E(L, "note b: MPC-24 5 min dT~", "-0.078", "T2v3_timestep [dt5, riyadh, MPC-24] dT", DT_HOW, lambda: one("T2v3_timestep", "dT", row="dt5", city="riyadh", arm="MPC-24"))
E(L, "note c: lam/lam* at 30 min", "6.27", "T2v3_timestep [dt30, riyadh, MPC-24] lam_over_lam_star", "fitted lam divided by lam* = Lambda 168 h p / COP", lambda: one("T2v3_timestep", "lam_over_lam_star", row="dt30", city="riyadh", arm="MPC-24"))
for c, v in zip(CITIES, ("+0.033", "+0.040", "+0.121")):
    E(L, f"caption: TUNED at 7200 kJ/K dT~ {CN[c]}", v, f"T1v3_heldout_cth7200 [{c}, TUNED] dT_pooled", DT_HOW, lambda c=c: one("T1v3_heldout_cth7200", "dT_pooled", city=c, arm="TUNED", tariff="inforce"))

# ================================================================== supplement
L = "S1 tab:s-timestep"
for rw, v in (("dt5", "0.125"), ("dt15", "0.375"), ("dt30", "0.750"), ("cth7200", "0.250")):
    E(L, f"Q dt / C_th ({rw})", v, f"T2v3_timestep [row={rw}] overshoot_K", "per-step excursion Q_hvac dt / C_th, degC", lambda rw=rw: one("T2v3_timestep", "overshoot_K", row=rw, city="riyadh", arm="TUNED"))
R3 = "occupied degree-hours of THERM on the first held-out Riyadh week (round-3 file, unstamped; THERM has no fitted parameter, so the round-4 protocol does not enter)"
for dt, v in ((5.0, "0.000"), (15.0, "0.000"), (30.0, "0.025"), (60.0, "4.470")):
    E(L, f"THERM deg-h at {dt:g} min", v, f"T2_timestep [dt_min={dt:g}] therm_deg_h", R3, lambda dt=dt: one("T2_timestep", "therm_deg_h", dt_min=dt))
for cth, v in ((1200.0, "2.737"), (1800.0, "2.500"), (2400.0, "0.000"), (4800.0, "0.000"), (7200.0, "0.000"), (9600.0, "0.000")):
    E(L, f"THERM deg-h at C_th {cth:g}", v, f"T3_capacity [C_th={cth:g}] therm_deg_h", R3, lambda cth=cth: one("T3_capacity", "therm_deg_h", C_th=cth))
for cth, v in ((1200.0, "1.500"), (1800.0, "1.000"), (2400.0, "0.750"), (9600.0, "0.188")):
    E(L, f"Q dt / C_th at C_th {cth:g}", v, f"T3_capacity [C_th={cth:g}] overshoot_K", "per-step excursion Q_hvac dt / C_th, degC", lambda cth=cth: one("T3_capacity", "overshoot_K", C_th=cth))
for cth, t, m in (("2400", "-2.8", "12.2"), ("9600", "15.8", "16.2")):
    E(L, f"(b) C_th {cth}: TUNED / MPC", f"{t} / {m}", f"T1v3_heldout_cth{cth} / T21v3_riyadh_cth{cth} s_pooled_eq", S_HOW,
      lambda cth=cth: f"{fmt_like(one(f'T1v3_heldout_cth{cth}', 's_pooled_eq', city='riyadh', arm='TUNED', tariff='inforce'), t)} / {fmt_like(one(f'T21v3_riyadh_cth{cth}', 's_pooled_eq', horizon_h=24.0, forecast='perfect'), m)}")

L = "S2 tab:s-protocol"
for c, v in zip(CITIES, ("9.7", "12.2", "4.0")):
    E(L, f"TUNED per-window 0.03 K, {CN[c]}", v, f"T1v3_sens [{c}, TUNED, per_window_0.03] s_pooled_eq", S_HOW + "; selection requires |dT_w| <= 0.03 K on every tuning window",
      lambda c=c: one("T1v3_sens", "s_pooled_eq", city=c, arm="TUNED", variant="per_window_0.03"))
for c, v in zip(CITIES, ("5.8", "5.9", "7.8")):
    E(L, f"guard per-window 0.03 K, {CN[c]}", v, f"T1v3_sens [{c}, guard, per_window_0.03] s_pooled_eq", S_HOW,
      lambda c=c: one("T1v3_sens", "s_pooled_eq", city=c, arm="guard", variant="per_window_0.03"))
for c, v in zip(CITIES, ("-4.0", "-6.3", "+3.8")):
    E(L, f"F4 under per-window criterion, {CN[c]}", v, "T1v3_sens guard - TUNED (per_window_0.03)", "difference of the two pooled savings",
      lambda c=c: one("T1v3_sens", "s_pooled_eq", city=c, arm="guard", variant="per_window_0.03") - one("T1v3_sens", "s_pooled_eq", city=c, arm="TUNED", variant="per_window_0.03"))
for c, v in zip(CITIES, ("5.7", "7.4", "8.4")):
    E(L, f"TUNED on 0.1 K grid, {CN[c]}", v, f"T1v3_sens [{c}, TUNED, hw_0.1K] s_pooled_eq", S_HOW, lambda c=c: one("T1v3_sens", "s_pooled_eq", city=c, arm="TUNED", variant="hw_0.1K"))
for c, lo, hi in (("riyadh", "12.5", "13.7"), ("jeddah", "13.6", "14.4"), ("taif", "12.4", "12.4")):
    E(L, f"Rule C cheapest/dearest crossing, TUNED, {CN[c]}", (lo, hi), "T1v3_heldout [TUNED, inforce] s_eq_minJ, s_eq_maxJ", "saving with the cheapest / dearest THERM crossing at the arm's mean",
      lambda c=c: (one("T1v3_heldout", "s_eq_minJ", city=c, arm="TUNED", tariff="inforce"), one("T1v3_heldout", "s_eq_maxJ", city=c, arm="TUNED", tariff="inforce")))
for c, lo, hi in (("riyadh", "18.3", "19.0"), ("jeddah", "18.1", "18.4"), ("taif", "16.9", "17.4")):
    E(L, f"Rule C cheapest/dearest crossing, MPC-24 h, {CN[c]}", (lo, hi), f"T21v3_{c} [24 h] s_eq_minJ, s_eq_maxJ", "as above",
      lambda c=c: (one(f"T21v3_{c}", "s_eq_minJ", horizon_h=24.0, forecast="perfect"), one(f"T21v3_{c}", "s_eq_maxJ", horizon_h=24.0, forecast="perfect")))
for c, v in zip(CITIES, ("-0.8", "-0.1", "0.0")):
    E(L, f"THERM scored against its own curve, {CN[c]}", v, f"T1v3_sens [{c}, THERM, self_score] s_pooled_eq", "THERM (unshifted) through Rule C against THERM(delta)",
      lambda c=c: one("T1v3_sens", "s_pooled_eq", city=c, arm="THERM", variant="self_score"))
LS = {6.0: {"riyadh": (("16.2", "+0.198"), ("14.0", "-0.026"), ("10.7", "-0.126")), "jeddah": (("17.4", "+0.185"), ("16.5", "+0.018"), ("10.5", "-0.109")),
            "taif": (("15.0", "+0.293"), ("14.0", "-0.059"), ("7.7", "-0.184"))},
      24.0: {"riyadh": (("18.4", "+0.185"), ("18.0", "+0.015"), ("16.9", "-0.043")), "jeddah": (("18.2", "+0.168"), ("17.9", "+0.033"), ("16.0", "-0.056")),
             "taif": (("14.4", "+0.379"), ("17.5", "+0.018"), ("16.8", "-0.042"))}}
for h, d in LS.items():
    for c, trip in d.items():
        for x, (s, dt) in zip(("0.99", "1.01", "1.05"), trip):
            st = f"T21v3_ls{x}_{c}"
            E(L, f"MPC {h:g} h at {x} lam*, {CN[c]}: s", s, f"{st} [{h:g} h] s_pooled_eq", S_HOW + "; lam fixed (fit_status fixed)", lambda st=st, h=h: one(st, "s_pooled_eq", horizon_h=h))
            E(L, f"MPC {h:g} h at {x} lam*, {CN[c]}: dT~", dt, f"{st} [{h:g} h] dT_pooled", DT_HOW, lambda st=st, h=h: one(st, "dT_pooled", horizon_h=h))
for c, a, b in (("riyadh", "18.3", "18.2"), ("jeddah", "18.1", "18.5"), ("taif", "16.9", "16.6")):
    E(L, f"MPC-24 h 1601 nodes, {CN[c]}", a, f"T21v3_{c} [24 h] s_pooled_eq", S_HOW, lambda c=c: one(f"T21v3_{c}", "s_pooled_eq", horizon_h=24.0, forecast="perfect"))
    E(L, f"MPC-24 h 3201 nodes, {CN[c]}", b, f"T21v3_conv_{c} s_pooled_eq", S_HOW + " at the 1601-node lam", lambda c=c: one(f"T21v3_conv_{c}", "s_pooled_eq"))
for c, h, v in (("riyadh", 1.0, "0.21"), ("jeddah", 0.25, "0.205"), ("jeddah", 1.0, "0.25"), ("taif", 1.0, "0.345"), ("taif", 2.0, "0.345")):
    E(L, f"back-off b, MPC {h:g} h, {CN[c]}", v, f"T21v3_{c} [{h:g} h] backoff (knob=backoff)", "occupied-ceiling back-off b (K) used when lam alone cannot match comfort",
      lambda c=c, h=h: one(f"T21v3_{c}", "backoff", horizon_h=h, forecast="perfect"))
for c, vals in zip(CITIES, (("14.0", "12.4", "6.2"), ("13.5", "8.3", "7.7"), ("12.4", "10.5", "7.0"))):
    for sg, v in zip((0.0, 0.05, 0.1), vals):
        E(L, f"D1 latch sigma={sg}, {CN[c]}", v, f"T_D1_latch_{c} [sigma={sg}] s_pooled_eq", S_HOW, lambda c=c, sg=sg: one(f"T_D1_latch_{c}", "s_pooled_eq", sigma=sg))

L = "S3 tab:s-clv"
CLVP = {"riyadh": "F/-0.013 F/-0.029 T/-0.001 T/+0.000 F/-0.026 F/-0.034 F/-0.148",
        "jeddah": "F/-0.010 F/-0.076 F/-0.025 T/-0.001 F/-0.003 F/-0.011 F/-0.003",
        "taif": "F/-0.018 F/-0.019 F/-0.002 F/-0.007 F/-0.075 F/-0.028 F/-0.025"}


def clv_pw(c):
    out = []
    for r in sorted(rows(f"T17v3_{c}_perwindow"), key=lambda r: int(float(r["window"]))):
        res = float(r["clv_resid"])
        s = f"{res:+.3f}"
        s = "+0.000" if s == "-0.000" else s
        out.append(("T" if r["clv_tol_met"] == "True" else "F") + "/" + s)
    return " ".join(out)


for c in CITIES:
    E(L, f"{CN[c]} windows 1-7", CLVP[c], f"T17v3_{c}_perwindow clv_tol_met, clv_resid", "|T~_CLV,w - T~_THERM,w| <= 0.002 K met? / residual (K)", lambda c=c: clv_pw(c))

L = "S-MZ tab:s-mz"
MZ = {("1x1", 12.5): ("-0.8", "12.5", "5.7"), ("1x2", 12.5): ("-0.1", "12.4", "7.2"), ("1x2", 35): ("-0.3", "12.2", "6.5"),
      ("2x2", 12.5): ("-0.1", "11.7", "8.3"), ("2x2", 35): ("-0.2", "12.9", "7.6"), ("1x4", 12.5): ("-0.5", "13.6", "7.7"), ("1x4", 35): ("-0.3", "13.3", "6.9")}
for (topo, lij), vals in MZ.items():
    st = f"T31_mz_rules_riyadh_{topo}_lij{lij:g}"
    for arm, v in zip(("THERM", "TUNED", "guard"), vals):
        E(L, f"{topo} lij={lij:g} {arm}", v, f"{st} [arm={arm}] s_pooled_eq", S_HOW + " on the dwelling-mean clipped temperature", lambda st=st, arm=arm: one(st, "s_pooled_eq", arm=arm))
MZMPC = {("1x1", 12.5): ("18.3", "a"), ("1x2", 12.5): ("16.0", "b"), ("1x2", 35): ("15.8", "b"), ("2x2", 12.5): ("15.9", "a"),
         ("2x2", 35): ("16.1", "a"), ("1x4", 12.5): ("15.7", "a"), ("1x4", 35): ("16.1", "a")}
for (topo, lij), (v, mark) in MZMPC.items():
    st = f"T31_mz_mpc_riyadh_{topo}_lij{lij:g}_h24"
    E(L, f"{topo} lij={lij:g} MPC-MZ", v, f"{st} s_pooled_eq", S_HOW + " on the dwelling mean; non-cooperative distributed MPC, 24 h, 1601 nodes",
      lambda st=st: float(rows(st)[0]["s_pooled_eq"]))
    E(L, f"{topo} lij={lij:g} MPC-MZ fit mark", mark, f"{st} fit_status", "a = pooled_0.03, b = pooled_0.10",
      lambda st=st: {"pooled_0.03": "a", "pooled_0.10": "b"}.get(rows(st)[0]["fit_status"], rows(st)[0]["fit_status"]))

L = "S4 tab:s-cmd"
CMD = [("Headline TUNED", ("0", "0.0007", "0.0066"), lambda c: one("T1v3_heldout", "deg_h_cmd_under", city=c, arm="TUNED", tariff="inforce"), "T1v3_heldout [TUNED, inforce] deg_h_cmd_under"),
       ("Headline TUNED-SB", ("0.0102", "0", "0"), lambda c: one("T28v3_setback_rule", "deg_h_cmd_under", city=c, arm="TUNED-SB"), "T28v3_setback_rule [TUNED-SB] deg_h_cmd_under"),
       ("TUNED dt=5", ("0", "0", "0.0011"), lambda c: one("T1v3_heldout_dt5", "deg_h_cmd_under", city=c, arm="TUNED", tariff="inforce"), "T1v3_heldout_dt5 deg_h_cmd_under"),
       ("TUNED dt=30", ("0.0097", "0.0025", "0"), lambda c: one("T1v3_heldout_dt30", "deg_h_cmd_under", city=c, arm="TUNED", tariff="inforce"), "T1v3_heldout_dt30 deg_h_cmd_under"),
       ("TUNED C_th 2400", ("0", "0", "0.0042"), lambda c: one("T1v3_heldout_cth2400", "deg_h_cmd_under", city=c, arm="TUNED", tariff="inforce"), "T1v3_heldout_cth2400 deg_h_cmd_under"),
       ("TUNED C_th 7200", ("0.0047", "0", "0.0017"), lambda c: one("T1v3_heldout_cth7200", "deg_h_cmd_under", city=c, arm="TUNED", tariff="inforce"), "T1v3_heldout_cth7200 deg_h_cmd_under"),
       ("TUNED vs 0.5 C comparator", ("0.0054", "0.0063", "0.0066"), lambda c: one("T7v3_deadband", "deg_h_cmd_under", city=c, deadband=0.5), "T7v3_deadband [deadband=0.5] deg_h_cmd_under"),
       ("TUNED vs 0.75 C comparator", ("0", "0.0016", "0.0066"), lambda c: one("T7v3_deadband", "deg_h_cmd_under", city=c, deadband=0.75), "T7v3_deadband [deadband=0.75] deg_h_cmd_under"),
       ("TUNED vs 1.25 C comparator", ("0.0092", "0.0063", "0"), lambda c: one("T7v3_deadband", "deg_h_cmd_under", city=c, deadband=1.25), "T7v3_deadband [deadband=1.25] deg_h_cmd_under"),
       ("TUNED per-window refit", ("0", "0.0016", "0"), lambda c: one("T1v3_sens", "deg_h_cmd_under", city=c, arm="TUNED", variant="per_window_0.03"), "T1v3_sens [TUNED, per_window_0.03] deg_h_cmd_under")]
for lab, vals, fn, src in CMD:
    for c, v in zip(CITIES, vals):
        E(L, f"{lab}, {CN[c]}", v, src, "degree-hours below T_min at the end of COOLING steps, summed over the 7 held-out windows", lambda fn=fn, c=c: fn(c))
E(L, "MPC 6 h persistence, Riyadh", "0.0006", "T21v3_pers_riyadh [6 h] deg_h_cmd_under", "as above", lambda: one("T21v3_pers_riyadh", "deg_h_cmd_under", horizon_h=6.0))
E(L, "TUNED north facade, Riyadh", "0.0026", "T24v3_orientation [riyadh, north] deg_h_cmd_under", "as above", lambda: one("T24v3_orientation", "deg_h_cmd_under", city="riyadh", orientation="north"))
for kind, vals in (("TRANSFER", (("0", "0", "0"), ("0.0007", "0", "0.0001"), ("0.0110", "0.0034", "0.0015"))),
                   ("RETUNED", (("0", "0.0007", "0.0034"), ("0.0023", "0", "0.0238"), ("0", "0", "0")))):
    for c, trip in zip(CITIES, vals):
        E(L, f"actual years {kind.lower()} (mildest, median, hottest by CDD), {CN[c]}", " ".join(trip), f"T23v3_amy_spread [{c}, kind={kind}, 3 actual years ordered by cdd] deg_h_cmd_under", "as above",
          lambda c=c, kind=kind, trip=trip: " ".join(fmt_like(float(r["deg_h_cmd_under"]), p) for r, p in zip(sorted((r for r in sel("T23v3_amy_spread", city=c, kind=kind) if r["year"] != "TMYx"), key=lambda r: float(r["cdd"])), trip)))
for lij, v in ((12.5, "0.0002"), (35, "0.0004")):
    E(L, f"TUNED 2x2 dwelling lij={lij:g}", v, f"T31_mz_rules_riyadh_2x2_lij{lij:g} [TUNED] deg_h_cmd_under", "as above", lambda lij=lij: one(f"T31_mz_rules_riyadh_2x2_lij{lij:g}", "deg_h_cmd_under", arm="TUNED"))
for lij, v in ((12.5, "0.000003"), (35, "0.000025")):
    E(L, f"MPC-MZ 2x2 dwelling lij={lij:g}", v, f"T31_mz_mpc_riyadh_2x2_lij{lij:g}_h24 deg_h_cmd_under", "as above",
      lambda lij=lij: float(rows(f"T31_mz_mpc_riyadh_2x2_lij{lij:g}_h24")[0]["deg_h_cmd_under"]))
E(L, "PPO without rules, admissible seed", "0.0065", "rbrl_norules5_v3 [riyadh, seed 42] deg_h_cmd_under", "as above", lambda: one("rbrl_norules5_v3", "deg_h_cmd_under", city="riyadh"))

L = "S4 text (setback, vacation weeks counted as occupied)"
for c, a, b in zip(CITIES, ("16.1", "17.4", "14.3"), ("20.8", "20.5", "19.5")):
    E(L, f"TUNED-SB, {CN[c]}", a, "T28v3_setback_rule [TUNED-SB] s_pooled_eq_vac_occupied", S_HOW + " with vacation weeks scored as occupied", lambda c=c: one("T28v3_setback_rule", "s_pooled_eq_vac_occupied", city=c, arm="TUNED-SB"))
    E(L, f"MPC-SB, {CN[c]}", b, f"T28v3_setback_mpc_{c} s_pooled_eq_vac_occupied", "as above", lambda c=c: one(f"T28v3_setback_mpc_{c}", "s_pooled_eq_vac_occupied"))

L = "S5 tab:s-ba"
BA = {"arm=TUNED tariff=inforce": ("TUNED", (("12.7", "19.7"), ("13.2", "20.2"), ("12.9", "20.8"))),
      "arm=guard tariff=inforce": ("Guard", (("6.0", "19.6"), ("7.6", "20.2"), ("11.0", "21.4"))),
      "arm=D1-latch sigma=0.0": ("D1 latch", (("13.4", "19.7"), ("14.0", "20.1"), ("12.5", "20.6"))),
      "horizon_h=24.0 forecast=perfect c_sw=0.15": ("MPC 24 h perfect", (("18.6", "19.9"), ("17.2", "19.3"), ("16.3", "20.4"))),
      "horizon_h=24.0 forecast=persistence c_sw=0.15": ("MPC 24 h persistence", (("13.0", "18.1"), ("14.1", "18.9"), ("11.8", "19.9"))),
      "CLV": ("CLV (Rule C)", (("18.3", "19.6"), ("18.5", "19.4"), ("16.5", "20.2")))}
for key, (lab, vals) in BA.items():
    for c, (sa, ba) in zip(CITIES, vals):
        def ba_row(c=c, key=key):
            rs = [r for r in sel("T17v3_Ba", city=c, arm=key) if r["kind"] in ("free",) and not r["source"].startswith("T16v3")]
            if len(rs) != 1:
                raise LookupError(f"T17v3_Ba {c} {key}: {len(rs)} rows")
            return rs[0]
        E(L, f"{lab}, {CN[c]}: s_a", sa, f"T17v3_Ba [city={c}, arm='{key}'] s_a", "saving rescored onto the V_N terminal, comparator at the arm's mean (Rule C)", lambda f=ba_row: float(f()["s_a"]))
        E(L, f"{lab}, {CN[c]}: B_a", ba, f"T17v3_Ba [city={c}, arm='{key}'] B_a", "B_a = 1 - L*(T~_a) / mean_w J_THERM(delta_w^a): bound at the arm's own pooled mean", lambda f=ba_row: float(f()["B_a"]))
E(L, "rows with s_a <= B_a", "89", "T17v3_Ba s_le_B", "count of rows (all must be True)", lambda: float(sum(r['s_le_B'] == 'True' for r in rows('T17v3_Ba'))) if all(r['s_le_B'] == 'True' for r in rows('T17v3_Ba')) else -1.0)
for arm, lab, vals in (("CLV", "CLV", ("22.33", "22.40", "22.35")), ("TUNED", "TUNED", ("22.83", "23.05", "22.69"))):
    for c, v in zip(CITIES, vals):
        if arm == "CLV":
            E(L, f"caption: T_end {lab}, {CN[c]}", v, f"T17v3_{c} clv_T_end_mean", "pooled end-of-window temperature", lambda c=c: one(f"T17v3_{c}", "clv_T_end_mean"))
        else:
            E(L, f"caption: T_end {lab}, {CN[c]}", v, "T1v3_heldout [TUNED, inforce] T_end_mean", "pooled end-of-window temperature", lambda c=c: one("T1v3_heldout", "T_end_mean", city=c, arm="TUNED", tariff="inforce"))
for c, v in zip(CITIES, ("22.92", "22.77", "23.03")):
    E(L, f"caption: T_end THERM, {CN[c]}", v, f"T17v3_ruled_{c} therm_T_end_mean", "THERM's pooled end-of-window temperature", lambda c=c: one(f"T17v3_ruled_{c}", "therm_T_end_mean"))
for c, v in zip(CITIES, ("22.87", "23.18", "23.12")):
    E(L, f"caption: T_end MPC 24 h, {CN[c]}", v, f"T21v3_{c} [24 h] T_end_mean", "pooled end-of-window temperature", lambda c=c: one(f"T21v3_{c}", "T_end_mean", horizon_h=24.0, forecast="perfect"))

L = "S6 tab:s-bias"
E(L, "actual years transfer range", ("10.5", "13.4"), "T23v3_amy_spread [kind=TRANSFER, 9 actual years] s_pooled_eq", "min..max", lambda: (min(float(r["s_pooled_eq"]) for r in sel("T23v3_amy_spread", kind="TRANSFER")), max(float(r["s_pooled_eq"]) for r in sel("T23v3_amy_spread", kind="TRANSFER"))))
E(L, "actual years re-tuned range", ("11.5", "14.8"), "T23v3_amy_spread [kind=RETUNED, years != TMYx] s_pooled_eq", "min..max", lambda: (min(float(r["s_pooled_eq"]) for r in sel("T23v3_amy_spread", kind="RETUNED") if r["year"] != "TMYx"), max(float(r["s_pooled_eq"]) for r in sel("T23v3_amy_spread", kind="RETUNED") if r["year"] != "TMYx")))
E(L, "start-up energy effect", ("0.33", "0.90"), "T25v3_cycling_energy [TUNED, wh_per_start 10..25] energy_saving_pct", "energy saving when each avoided start also saves 10-25 Wh",
  lambda: (min(float(r["energy_saving_pct"]) for r in rows("T25v3_cycling_energy") if r["arm"] == "TUNED" and float(r["wh_per_start"]) in (10.0, 25.0)),
           max(float(r["energy_saving_pct"]) for r in rows("T25v3_cycling_energy") if r["arm"] == "TUNED" and float(r["wh_per_start"]) in (10.0, 25.0))))
E(L, "other cells", "(cross-references)", "values of tab:sensitivity, tab:timestep, S2, tab:stats F3", "see those rows", None)

L = "S7 tab:s-ablation"
E(L, "PPO without rules, Riyadh (1 of 5 admissible)", "-3.5", "rbrl_norules5_v3 [riyadh] s_pooled_eq (only admissible seed is written)", S_HOW + "; cap fixed (fit_status fixed)", lambda: one("rbrl_norules5_v3", "s_pooled_eq", city="riyadh"))
E(L, "other rows", "(repeat tab:main)", "see tab:main rows RBRL, guard, D1, MPC in rules, TUNED", "", None)

# ================================================================== abstract / conclusions
L = "abstract + conclusions"
E(L, "fitted deadband R1 - R2 (min..max over cities)", ("1.32", "1.36"), "T1v3_heldout [TUNED, inforce] params.on - params.off", "TUNED switch points R1 - R2 (degC)",
  lambda: (min(json.loads(r["params"])["on"] - json.loads(r["params"])["off"] for r in sel("T1v3_heldout", arm="TUNED", tariff="inforce")),
           max(json.loads(r["params"])["on"] - json.loads(r["params"])["off"] for r in sel("T1v3_heldout", arm="TUNED", tariff="inforce"))))
E(L, "on-commands avoided by TUNED (22--24)", ("22", "24"), "T1v3_heldout [TUNED, inforce] start_sav_eq", "min..max over cities (21.7 rounds to 22)",
  lambda: (min(float(r["start_sav_eq"]) for r in sel("T1v3_heldout", arm="TUNED", tariff="inforce")), max(float(r["start_sav_eq"]) for r in sel("T1v3_heldout", arm="TUNED", tariff="inforce"))))
E(L, "TUNED electricity within +/-0.5 % (max |energy_sav_eq|)", "0.5", "T1v3_heldout [TUNED, inforce] energy_sav_eq", "max over cities of |energy saving|",
  lambda: max(abs(float(r["energy_sav_eq"])) for r in sel("T1v3_heldout", arm="TUNED", tariff="inforce")))
E(L, "TUNED SAR/season at 0.025--0.114 (2--19)", ("2", "19"), "T1v3_perwindow [TUNED, inforce] fs/E", "tab:layers formula, min over cities at 0.025, max at 0.114",
  lambda: (min(sar(pw_of("TUNED", c), 0.025) for c in CITIES), max(sar(pw_of("TUNED", c), 0.114) for c in CITIES)))
E(L, "TUNED cost saving 12.4--13.6", ("12.4", "13.6"), "T1v3_heldout [TUNED, inforce] s_pooled_eq", "min..max over cities",
  lambda: (min(float(r["s_pooled_eq"]) for r in sel("T1v3_heldout", arm="TUNED", tariff="inforce")), max(float(r["s_pooled_eq"]) for r in sel("T1v3_heldout", arm="TUNED", tariff="inforce"))))
E(L, "TUNED against a 1.25 C comparator (Riyadh)", "5.7", "T7v3_deadband [riyadh, 1.25] s_pooled_eq", S_HOW, lambda: one("T7v3_deadband", "s_pooled_eq", city="riyadh", deadband=1.25))
E(L, "MPC-24 perfect avoids 30--33 % of on-commands", ("30", "33"), "T21v3_<c> [24 h, perfect] start_sav_eq", "min..max over cities",
  lambda: (min(one(f"T21v3_{c}", "start_sav_eq", horizon_h=24.0, forecast="perfect") for c in CITIES), max(one(f"T21v3_{c}", "start_sav_eq", horizon_h=24.0, forecast="perfect") for c in CITIES)))
E(L, "TUNED at half / twice capacity (Riyadh)", ("-2.8", "15.8"), "T1v3_heldout_cth2400 / _cth9600 [riyadh, TUNED] s_pooled_eq", S_HOW,
  lambda: (one("T1v3_heldout_cth2400", "s_pooled_eq", city="riyadh", arm="TUNED", tariff="inforce"), one("T1v3_heldout_cth9600", "s_pooled_eq", city="riyadh", arm="TUNED", tariff="inforce")))
E(L, "MPC margin over TUNED at half / twice capacity (Riyadh)", ("15.0", "0.4"), "T21v3_riyadh_cth2400/9600 minus T1v3_heldout_cth2400/9600 s_pooled_eq", "difference of unrounded savings",
  lambda: tuple(one(f"T21v3_riyadh_cth{x}", "s_pooled_eq", horizon_h=24.0, forecast="perfect") - one(f"T1v3_heldout_cth{x}", "s_pooled_eq", city="riyadh", arm="TUNED", tariff="inforce") for x in ("2400", "9600")))
E(L, "TUNED at 30 min (-1.2 to -1.5)", ("-1.2", "-1.5"), "T2v3_timestep [dt30, TUNED] s", "max..min over cities",
  lambda: (max(one("T2v3_timestep", "s", row="dt30", city=c, arm="TUNED") for c in CITIES), min(one("T2v3_timestep", "s", row="dt30", city=c, arm="TUNED") for c in CITIES)))
E(L, "MPC at 30 min (6.6--11.4)", ("6.6", "11.4"), "T2v3_timestep [dt30, MPC-24] s", "min..max over cities",
  lambda: (min(one("T2v3_timestep", "s", row="dt30", city=c, arm="MPC-24") for c in CITIES), max(one("T2v3_timestep", "s", row="dt30", city=c, arm="MPC-24") for c in CITIES)))
for c, lo, hi in (("riyadh", "18.0", "20.0"), ("jeddah", "18.4", "19.9"), ("taif", "16.7", "21.0")):
    E(L, f"bracket {CN[c]} (CLV raw -- B*)", (lo, hi), f"T17v3_{c} clv_s_raw, bound_reported", "clairvoyant schedule (raw) and relaxed dual bound (V_N)",
      lambda c=c: (one(f"T17v3_{c}", "clv_s_raw"), one(f"T17v3_{c}", "bound_reported")))
E(L, "multi-zone TUNED 11.7--13.6 (2 and 4 rooms)", ("11.7", "13.6"), "T31_mz_rules_riyadh_{1x2,2x2,1x4}_lij{12.5,35} [TUNED] s_pooled_eq", "min..max over the six multi-room layouts",
  lambda: (min(one(f"T31_mz_rules_riyadh_{t}_lij{l}", "s_pooled_eq", arm="TUNED") for t in ("1x2", "2x2", "1x4") for l in ("12.5", "35")),
           max(one(f"T31_mz_rules_riyadh_{t}_lij{l}", "s_pooled_eq", arm="TUNED") for t in ("1x2", "2x2", "1x4") for l in ("12.5", "35"))))
E(L, "electricity per 0.1 K warmer mean (0.9--2.3 %)", ("0.9", "2.3"), "T32_setpoint_sens [point=+0.1] -energy_pct", "THERM shifted +0.1 K: % change in electricity (sign flipped)",
  lambda: (min(-float(r["energy_pct"]) for r in sel("T32_setpoint_sens", point="+0.1")), max(-float(r["energy_pct"]) for r in sel("T32_setpoint_sens", point="+0.1"))))
E(L, "conclusions: on 0.1 C grid avoids 11--15 %", ("11", "15"), "T1v3_sens [TUNED, hw_0.1K] start_sav_eq", "min..max over cities",
  lambda: (min(float(r["start_sav_eq"]) for r in sel("T1v3_sens", arm="TUNED", variant="hw_0.1K")), max(float(r["start_sav_eq"]) for r in sel("T1v3_sens", arm="TUNED", variant="hw_0.1K"))))
E(L, "conclusions: TUNED attains 62--65 % of the bound at its own mean", ("62", "65"), "T17v3_Ba [arm=TUNED inforce] 100 s_a / B_a", "ratio of rescored saving to B_a",
  lambda: (min(100 * float(r["s_a"]) / float(r["B_a"]) for r in sel("T17v3_Ba", arm="arm=TUNED tariff=inforce")), max(100 * float(r["s_a"]) / float(r["B_a"]) for r in sel("T17v3_Ba", arm="arm=TUNED tariff=inforce"))))
E(L, "conclusions: MPC-24 adds 4--6 points (F2 pooled delta)", ("4", "6"), "T20v3_paired_stats [F2] d_pooled", "min..max over cities",
  lambda: (min(float(r["d_pooled"]) for r in sel("T20v3_paired_stats", family="F2")), max(float(r["d_pooled"]) for r in sel("T20v3_paired_stats", family="F2"))))
E(L, "conclusions: guard costs 6.8 and 6.0 points (Riyadh, Jeddah)", ("6.8", "6.0"), "T20v3_paired_stats [F4] -d_pooled", "TUNED - guard, pooled",
  lambda: tuple(-float(sel("T20v3_paired_stats", family="F4", city=c)[0]["d_pooled"]) for c in ("riyadh", "jeddah")))
E(L, "conclusions: MPC-24 in training rules over guard (about 6)", ("5.9", "6.4"), "T16v3_r23.8-22.4_<c> [24 h] - T1v3_heldout [guard]", "difference of pooled savings, Riyadh and Jeddah",
  lambda: tuple(one(f"T16v3_r23.8-22.4_{c}", "s_pooled_eq", horizon_h=24.0) - one("T1v3_heldout", "s_pooled_eq", city=c, arm="guard", tariff="inforce") for c in ("riyadh", "jeddah")))
E(L, "conclusions: setback raises on-commands avoided to 29--35 %", ("29", "35"), "T28v3_setback_rule [TUNED-SB] start_sav_eq", "min..max over cities",
  lambda: (min(float(r["start_sav_eq"]) for r in sel("T28v3_setback_rule", arm="TUNED-SB")), max(float(r["start_sav_eq"]) for r in sel("T28v3_setback_rule", arm="TUNED-SB"))))
E(L, "conclusions: setback cost saving 17--20 %", ("17", "20"), "T28v3_setback_rule [TUNED-SB] s_pooled_eq", "min..max over cities",
  lambda: (min(float(r["s_pooled_eq"]) for r in sel("T28v3_setback_rule", arm="TUNED-SB")), max(float(r["s_pooled_eq"]) for r in sel("T28v3_setback_rule", arm="TUNED-SB"))))
MZM = [f"T31_mz_mpc_riyadh_{t}_lij{l}_h24" for t, l in (("1x2", "12.5"), ("2x2", "12.5"), ("1x4", "12.5"), ("1x2", "35"), ("2x2", "35"), ("1x4", "35"))]
E(L, "conclusions: MPC-MZ in 2- and 4-room dwellings 15.7--16.1 %", ("15.7", "16.1"), "T31_mz_mpc_riyadh_{1x2,2x2,1x4}_lij{12.5,35}_h24 s_pooled_eq", "min..max over the six multi-room layouts",
  lambda: (min(float(rows(m)[0]["s_pooled_eq"]) for m in MZM), max(float(rows(m)[0]["s_pooled_eq"]) for m in MZM)))
E(L, "conclusions: against 18.3 % in the single zone", "18.3", "T31_mz_mpc_riyadh_1x1_lij12.5_h24 s_pooled_eq", "1x1 instance = single-zone MPC-24", lambda: float(rows("T31_mz_mpc_riyadh_1x1_lij12.5_h24")[0]["s_pooled_eq"]))
L = "main §5 reward subsection, §9.2, Limitations (PPO vs hold, training cost)"
T33 = "T33_ppo_hold_gap"
T33_HOW = "gap = 100 (J_PPO / J_hold - 1) with the TRAINING cost (no lambda term) at the training rules; tune = six tuning weeks, eval = held-out weeks"
taif_below = lambda: [r for r in sel(T33, city="taif") if float(r["gap_eval_pct"]) > 0.01]   # the four Taif seeds below the guard on held-out weeks
E(L, "Taif: seeds below hold on held-out weeks", "4", f"{T33} [taif] gap_eval_pct > 0", "count of seeds (seed 43 reproduces hold)", lambda: float(len(taif_below())))
E(L, "Taif: of those, seeds within 0.05 % of hold on tuning weeks", "3", f"{T33} [taif, seeds below hold] |gap_tune_pct| <= 0.05", T33_HOW, lambda: float(sum(abs(float(r["gap_tune_pct"])) <= 0.05 for r in taif_below())))
E(L, "Taif: the fourth seed's tuning gap (also the 'one Taif seed (1.4 %)' of §9.2 and Limitations)", "1.4", f"{T33} [taif, seed 46] gap_tune_pct", T33_HOW, lambda: max(float(r["gap_tune_pct"]) for r in taif_below()))
E(L, "Taif: held-out gap of those four seeds", ("0.5", "2.5"), f"{T33} [taif, seeds below hold] gap_eval_pct", T33_HOW + "; min..max",
  lambda: (min(float(r["gap_eval_pct"]) for r in taif_below()), max(float(r["gap_eval_pct"]) for r in taif_below())))
E(L, "Limitations and §9.2: every trained policy within 0.9 % of hold's training cost except one Taif seed", "0.9", f"{T33} [all 15 seeds except taif 46] max |gap_tune_pct|", T33_HOW,
  lambda: max(abs(float(r["gap_tune_pct"])) for r in rows(T33) if not (r["city"] == "taif" and r["seed"] == "46")))
L = "main §8.4 (multi-zone)"
E(L, "MPC-MZ avoids 28--32 % of on-commands", ("28", "32"), "T31_mz_mpc_riyadh_<6 multi-room layouts>_h24 start_sav_eq", "min..max", lambda: (min(float(rows(m)[0]["start_sav_eq"]) for m in MZM), max(float(rows(m)[0]["start_sav_eq"]) for m in MZM)))
E(L, "MPC-MZ electricity within +/-0.7 % (max |energy_sav_eq|)", "0.7", "T31_mz_mpc_riyadh_<6 multi-room layouts>_h24 energy_sav_eq", "max |.|", lambda: max(abs(float(rows(m)[0]["energy_sav_eq"])) for m in MZM))
E(L, "MPC-MZ occupied over-temperature, 1x4 lij=35 (degC h)", "0.0001", "T31_mz_mpc_riyadh_1x4_lij35_h24 deg_h_over", "occupied degree-hours above the ceiling, 7 windows", lambda: float(rows("T31_mz_mpc_riyadh_1x4_lij35_h24")[0]["deg_h_over"]))
E(L, "MPC-MZ commanded under-temperature, 2x2 (at most 0.00003)", "0.00003", "T31_mz_mpc_riyadh_2x2_lij{12.5,35}_h24 deg_h_cmd_under", "max over the two 2x2 runs",
  lambda: max(float(rows(f"T31_mz_mpc_riyadh_2x2_lij{l}_h24")[0]["deg_h_cmd_under"]) for l in ("12.5", "35")))


# ================================================================== evaluation
def check(e):
    if e["fn"] is None:
        return "NOT IN A RESULT FILE" if "not in a v3 file" in e["src"] else "n/a", ""
    try:
        v = e["fn"]()
    except Exception as ex:          # noqa: BLE001 -- report, never hide
        return "ERROR", f"{type(ex).__name__}: {ex}"
    p = e["printed"]
    if isinstance(v, str):
        if p == "(pending)":
            return "PENDING", v
        return ("OK" if v == p else "MISMATCH"), v
    if isinstance(p, tuple):
        got = tuple(fmt_like(x, q) for x, q in zip(v, p))
        return ("OK" if got == p else "MISMATCH"), " / ".join(got)
    got = fmt_like(v, p)
    return ("OK" if got == p else "MISMATCH"), got


def meta_of(stem):
    p = os.path.join(RES, stem + ".csv.meta.json")
    if not os.path.exists(p):
        p = os.path.join(RES, stem + ".json.meta.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def jobs():
    out = []
    for f in sorted(glob.glob(os.path.join(REPO, "code", "jobs", "*.jsonl")) + glob.glob(os.path.join(HERE, "jobs", "*.jsonl"))):
        for line in open(f):
            line = line.strip()
            if line and not line.startswith("#"):
                j = json.loads(line)
                out.append((os.path.relpath(f, REPO), j))
    return out


def job_for(stem, meta):
    hits = []
    for f, j in JOBS:
        if any(o.endswith("/" + stem + ".csv") for o in j.get("outputs", [])):
            hits.append(f"{f}:{j['id']}")
    if not hits and meta:
        for f, j in JOBS:
            cmd, env = j["cmd"].strip(), {k: v for k, v in j.get("env", {}).items() if k.startswith("RBRL_")}
            mc = re.search(r"\s--cth\s+(\S+)", cmd)          # --cth X is moved into RBRL_CTH by the producer
            if mc:
                cmd = cmd.replace(mc.group(0), ""); env["RBRL_CTH"] = str(float(mc.group(1)))
            if cmd == ("python3 " + meta.get("argv", "")).strip() and env == meta.get("env", {}):
                hits.append(f"{f}:{j['id']}")
    return hits


STEM_RE = re.compile(r"\b((?:T\d+v?\d*|T_D1|rbrl|E1v3)[A-Za-z0-9_.\-]*?)(?=\s|\[|$|,| s_| /)")


def stems_in(src):
    out = []
    for m in re.finditer(r"\b([A-Za-z0-9_.\-]+)", src):
        s = m.group(1)
        if os.path.exists(os.path.join(RES, s + ".csv")) and s not in out:
            out.append(s)
    return out


JOBS = jobs()

# producer script -> the function that computes the written rows (all summaries go through
# t1_v2.evaluate / final_tables.equalise / final_tables.pooled_saving unless stated)
FUNC = {"t1_v2.py": "run_t1 / run_t7 / run_csw -> evaluate()", "mpc_lambda.py": "main -> fit_lambda() (Rule A) -> t1_v2.evaluate()",
        "bound_v2.py": "main(mode) -> config() (bound, CLV via r3_dp.clv_fit)", "bound_at.py": "main() -> v3_names.B_a / r3_dp.certificate_margin",
        "shield.py": "main() (latch / ppo) -> t1_v2.evaluate()", "rbrl_ppo.py": "evaluate() (policy rollout) -> t1_v2.evaluate()", "ppo_hold_gap.py": "main() (saved PPO models vs hold, training cost)",
        "stats_v3.py": "main() (HL, Wilcoxon, sign, Holm)", "setback_arms.py": "main_rule() / main_mpc() -> evaluate_sb() (setback Rule C)",
        "t1_sens.py": "main() -> t1_v2.evaluate()", "timestep_table.py": "main() (collects tagged runs)",
        "mz_r3.py": "main_rules() (dwelling-mean Rule C)", "mz_mpc.py": "main() -> mpc_lambda.fit_lambda()",
        "amy_spread.py": "__main__ -> protocol() / evaluate_rule() -> t1_v2.evaluate()", "orientation.py": "run() -> amy_spread.protocol()",
        "cycling_energy.py": "main() -> from_summary()", "setpoint_sens.py": "main() (THERM shifted on its own Rule C curve)"}


def main(write=False):
    res = [(e, *check(e)) for e in ENTRIES]
    n = {}
    for _, st, _ in res:
        n[st] = n.get(st, 0) + 1
    for e, st, got in res:
        if st not in ("OK",):
            print(f"[{st}] {e['loc']} | {e['item']} | printed {e['printed']} | file {got} | {e['src']}")
    print("summary:", ", ".join(f"{k} {v}" for k, v in sorted(n.items())), f"(of {len(res)})")
    if write:
        write_md(res, n)
    return 1 if n.get("MISMATCH") or n.get("ERROR") else 0


def pr(p):
    return " -- ".join(p) if isinstance(p, tuple) else str(p)


def write_md(res, n):
    L = [open(os.path.join(HERE, "provenance_header.md")).read().rstrip(), "",
         f"## 3. Check result\n\n`python3 docs/provenance_check.py` on this release: "
         + ", ".join(f"**{k}** {v}" for k, v in sorted(n.items())) + f" of {len(res)} mapped values.\n"]
    bad = [(e, st, got) for e, st, got in res if st not in ("OK",)]
    L.append("Values that are not a plain match (pending, not in a result file, cross-references, or mismatches):\n")
    L.append("| Location | Item | Printed | From the file | Status |\n|---|---|---|---|---|")
    for e, st, got in bad:
        L.append(f"| {e['loc']} | {e['item']} | {pr(e['printed'])} | {got or '—'} | {st} |")
    L.append("\n## 4. Value map\n")
    loc = None
    for e, st, got in res:
        if e["loc"] != loc:
            loc = e["loc"]
            L.append(f"\n### {loc}\n\n| Item | Printed | Source: file [row filter] column | How it is computed | Check |\n|---|---|---|---|---|")
        L.append(f"| {e['item']} | {pr(e['printed'])} | `{e['src']}` | {e['how']} | {st} |")
    L.append("\n## 5. Source files: producer, job, command and code stamp\n")
    L.append("Every file cited above, with the stamp in its `.meta.json` (code sha → tag of the working repository), "
             "the exact command and `RBRL_*` environment it ran with, and the job that ran it (job lists: `code/jobs/`, "
             "and the per-stage lists that ran before p13 in `docs/jobs/`).\n")
    L.append("| File | Producer (impl): function | Command (argv) | RBRL_* env | Code sha → tag | Written (UTC) | Job |\n|---|---|---|---|---|---|---|")
    stems = []
    for e, _, _ in res:
        for s in stems_in(e["src"]):
            if s not in stems:
                stems.append(s)
    for s in stems:
        for x in (s, s + "_perwindow") if not s.endswith("_perwindow") else (s,):
            if not os.path.exists(os.path.join(RES, x + ".csv")):
                continue
            m = meta_of(x)
            if m is None:
                L.append(f"| `{x}.csv` | — | — | — | unstamped (no .meta.json) | — | — |")
                continue
            sha = m.get("code_sha", "")
            L.append(f"| `{x}.csv` | `{m.get('impl', '')}`: {FUNC.get(m.get('impl', ''), '')} | `{m.get('argv', '')}` | `{json.dumps(m.get('env', {}))}` | "
                     f"`{sha}` → {TAG_OF_SHA.get(sha, 'unknown')} | {m.get('utc', '')} | {', '.join(job_for(x, m)) or '—'} |")
    open(os.path.join(HERE, "PROVENANCE.md"), "w").write("\n".join(L) + "\n")
    print("-> docs/PROVENANCE.md")


if __name__ == "__main__":
    sys.exit(main(write="--write" in sys.argv))
