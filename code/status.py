#!/usr/bin/env python3
"""One-screen tracker: running jobs and the headline number of every result file."""
import csv, glob, os, subprocess
R = "/home/claude/rbrl/results"
ps = subprocess.run(["ps", "-eo", "etime,args"], capture_output=True, text=True).stdout.splitlines()
print("RUNNING:")
for l in ps:
    if "python3" in l and "bin/bash" not in l and "status.py" not in l:
        print("  ", l.strip()[:110])
print("\nRESULTS (pooled comfort-equalised saving, %):")
for f in sorted(glob.glob(f"{R}/*.csv")):
    b = os.path.basename(f)
    if "perwindow" in b or "archive" in f:
        continue
    try:
        rows = list(csv.DictReader(open(f)))
    except Exception:
        continue
    if rows and "s_pooled_eq" in rows[0]:
        vals = []
        for r in rows:
            lab = "/".join(str(r.get(k, "")) for k in ("city", "arm", "horizon_h", "seed", "tariff", "deadband", "c_sw") if r.get(k))
            v = r['s_pooled_eq']
            vals.append(f"{lab}={float(v):.1f}" if v not in ('', None) else f"{lab}=n/a")
        print(f"  {b:42s} " + "  ".join(vals[:9]) + (" ..." if len(vals) > 9 else ""))
