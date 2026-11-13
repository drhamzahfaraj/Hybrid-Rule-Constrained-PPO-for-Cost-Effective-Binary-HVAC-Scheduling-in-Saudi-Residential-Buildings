#!/usr/bin/env python3
"""C15: clairvoyant schedule over exactly the rule-admissible action set (R1 at 23.80, R2 at
22.40): bound_v2.clv_row with ruled=True (r3_dp.clv_fit, two-sided 0.002 K, F.admissible, no
fallback), Rule C scoring, fit_status "oracle". No selection here (V-code-27). The ruled bound and
this CLV are also produced together by `bound_v2.py ruled` (T17v3_ruled_<city>)."""
import sys
sys.path.insert(0, "/home/claude/rbrl")
import config as CFG
import final_tables as F, bound_v2 as B
import rbrl_io as IO

rows = []
for city in F.CITIES:
    for w in F.EVAL_W:
        th = F.therm_run(city, w, CFG.PRICE)
        rows.append(dict(city=city, window=w, therm_J=th["J"], therm_T=th[F.MEAN_KEY], fit_status="oracle",
                         **B.clv_row(city, w, CFG.PRICE, False, F.C_SW, 3201, th, ruled=True,
                                     rule_on=CFG.RULE_ON, rule_off=CFG.RULE_OFF)))
        print(city, w, rows[-1]["clv_J"], rows[-1]["clv_tol_met"], flush=True)
    rr = [r for r in rows if r["city"] == city]
    print(f"{city}: CLV-in-rules pooled saving (Rule C) "
          f"{F.pooled_saving([r['clv_J'] for r in rr], [r['clv_J_eq'] for r in rr]):.2f}%", flush=True)
IO.write_csv("T27v3_clv_ruled", rows, ndigits=None)                 # F2: via rbrl_io
