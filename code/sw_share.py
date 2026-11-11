#!/usr/bin/env python3
"""One definition of the switching share, used by BOTH panels of
tab:sensitivity and by fig:tariff.

    share = c_sw * <f_s> / <J>   for THERM, over the held-out windows,

i.e. the ratio of the reported means, which is what the table's own f_s and J
columns support. Panels (a) and (b) previously quoted 55.0% and 55.1% for the
same configuration because each recomputed the share its own way. Only THERM
runs are needed, so this is cheap and can be regenerated at will.
"""
from __future__ import annotations
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))  # repository-relative paths
import sys, csv
sys.path.insert(0, _ROOT + "")
import numpy as np
import headroom as H
import final_tables as F

rows = []


def share(price, c_sw):
    old = H.C_SW
    H.C_SW = F.C_SW = c_sw
    try:
        th = [F.therm_run("riyadh", w, price) for w in F.EVAL_W]
        J = float(np.mean([r["J"] for r in th]))
        fs = float(np.mean([r["f_s"] for r in th]))
        return J, fs, (100.0 * c_sw * fs / J if J else 0.0)
    finally:
        H.C_SW = F.C_SW = old


print("(a) tariff sweep, c_sw = 0.15")
for tag, p in (("historical", 0.05), ("inforce", 0.18), ("y2027", 0.21)):
    J, fs, s = share(p, 0.15)
    rows.append(dict(panel="a", key=tag, price=p, c_sw=0.15,
                     therm_J=round(J, 4), therm_fs=round(fs, 3),
                     sw_share_pct=round(s, 1)))
    print(f"  {tag:11s} J={J:.4f} f_s={fs:.3f} share={s:.1f}%")

print("(b) switching-cost sweep, tariff in force")
for cs in (0.0, 0.05, 0.15, 0.30, 0.60):
    J, fs, s = share(0.18, cs)
    rows.append(dict(panel="b", key=f"c_sw={cs:.2f}", price=0.18, c_sw=cs,
                     therm_J=round(J, 4), therm_fs=round(fs, 3),
                     sw_share_pct=round(s, 1)))
    print(f"  c_sw={cs:4.2f}    J={J:.4f} f_s={fs:.3f} share={s:.1f}%")

# consistency check: the in-force row appears in both panels and must agree
a = next(r for r in rows if r["panel"] == "a" and r["key"] == "inforce")
b = next(r for r in rows if r["panel"] == "b" and r["c_sw"] == 0.15)
assert a["sw_share_pct"] == b["sw_share_pct"] and a["therm_J"] == b["therm_J"], \
    f"panels disagree: {a} vs {b}"
print(f"\nOK: both panels give {a['sw_share_pct']}% at the shared configuration "
      f"(THERM J = {a['therm_J']})")

with open(_ROOT + "/results/sw_share.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("-> results/sw_share.csv")
