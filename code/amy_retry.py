#!/usr/bin/env python3
"""Retry pass for the AMY fetch: only missing city-years, slow pacing."""
import sys, os, time, json, csv
sys.path.insert(0, "/home/claude/rbrl")
import amy_fetch as A

rows = []
sp = f"{A.OUT}/amy_summary.csv"
if os.path.exists(sp):
    rows = list(csv.DictReader(open(sp)))
    for r in rows:
        r["year"] = int(r["year"])
have = {(r["city"], r["year"]) for r in rows}
for city in A.SITES:
    for year in A.YEARS:
        p = f"{A.OUT}/{city}_{year}.csv"
        if os.path.exists(p) and (city, year) in have:
            continue
        try:
            rec = A.tidy(A.fetch(city, year, retries=6), city, year)
            A.write_csv(city, year, rec)
            s = A.summarise(city, year, rec)
            rows.append(s)
            print(f"  {city} {year}: CDD24={s['cdd24']}", flush=True)
        except Exception as e:
            print(f"  {city} {year} FAILED: {e}", flush=True)
        time.sleep(18.0)

rows.sort(key=lambda r: (r["city"], int(r["year"])))
with open(sp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
sel = {}
for city in A.SITES:
    rs = [r for r in rows if r["city"] == city]
    if not rs: continue
    key = lambda r: float(r["cdd24"])
    hot, mild = max(rs, key=key), min(rs, key=key)
    med = sorted(rs, key=key)[len(rs)//2]
    sel[city] = dict(hot=int(hot["year"]), mild=int(mild["year"]),
                     median=int(med["year"]), n=len(rs))
    print(f"{city}: n={len(rs)} hot {hot['year']} ({key(hot):.0f}) mild "
          f"{mild['year']} ({key(mild):.0f}) median {med['year']}")
with open(f"{A.OUT}/amy_selected.json", "w") as f:
    json.dump(sel, f, indent=2)
