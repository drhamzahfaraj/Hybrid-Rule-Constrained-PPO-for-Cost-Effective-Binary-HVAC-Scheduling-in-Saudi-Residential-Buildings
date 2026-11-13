#!/usr/bin/env python3
"""Fetch Actual Meteorological Year records for the three cities from ERA5.

Why this exists
---------------
Every result in the manuscript rests on one TMYx year per city. A typical year
is by construction not any year that occurred: its months are spliced from
different years to be representative, so it understates both the hot tail and
the mild tail. A saving ratio measured on it carries no statement about the
year-to-year spread a householder would actually see. The reviewers asked for
actual years; this fetches them.

Source: ERA5 reanalysis, served hourly by the Open-Meteo archive API. ERA5 is
the ECMWF global reanalysis; its 2 m temperature and surface radiation are the
same fields the TMYx files for this region are themselves assembled from where
no long station record exists. Crucially the API serves DIRECT NORMAL and
DIFFUSE components separately, not only global horizontal, so the same
plane-of-array transposition the EPW path uses can be applied unchanged -- the
weather source changes, the optics do not.

What is NOT claimed
-------------------
ERA5 is a reanalysis, not a station observation. Its 0.25 deg grid cell is
coarser than a city, it is known to under-represent urban heat island warming,
and its direct/diffuse split is modelled rather than measured. So these years
are used ONLY to measure the SPREAD of the saving ratio across real years at
fixed method and fixed plant. They are not used to restate any headline number,
and the TMYx result remains the reported one. That distinction is stated in the
manuscript wherever these results appear.

Output: one CSV per city-year with the three fields `series()` consumes, in the
EPW field convention (dry-bulb degC, DNI W/m2, DHI W/m2) plus relative humidity
for the latent study, 8760 rows, local standard time, hour 1..24 per day.
"""
from __future__ import annotations
import sys, os, json, time, csv, urllib.request, urllib.error
sys.path.insert(0, "/home/claude/rbrl")
import numpy as np

# Station coordinates, matched to the TMYx files the manuscript already uses so
# that the AMY and TMY runs describe the same place. Elevation is reported back
# by the API and logged, as a check that the right cell was served.
SITES = {
    "riyadh": dict(lat=24.7000, lon=46.7333, tz="Asia/Riyadh"),
    "jeddah": dict(lat=21.5000, lon=39.1833, tz="Asia/Riyadh"),
    "taif":   dict(lat=21.4833, lon=40.5500, tz="Asia/Riyadh"),
}
YEARS = list(range(2009, 2024))          # 15 complete years
OUT = "/home/claude/rbrl/amy"
VARS = ("temperature_2m", "relative_humidity_2m",
        "direct_normal_irradiance", "diffuse_radiation",
        "shortwave_radiation")


MODELS = "era5"                          # pinned (R4 S9): no unpinned Open-Meteo blend


def fetch(city, year, retries=4):
    """One city-year, requested with ONE EXTRA DAY (to 1 Jan of year+1) because the record is
    re-indexed to the EPW hour-ending convention in tidy() (R4 S5): Open-Meteo stamps hourly
    radiation with the END of its averaging hour, and the first row is 00:00 on 1 Jan, which
    belongs to the PREVIOUS year's last interval. The old code wrote that row as EPW hour 1
    (00:00-01:00), so every ERA5 series was 1 h late (GHI centroid ~ solar noon + 1 h)."""
    s = SITES[city]
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={s['lat']}&longitude={s['lon']}"
           f"&start_date={year}-01-01&end_date={year + 1}-01-01"
           f"&hourly={','.join(VARS)}"
           f"&models={MODELS}"
           # Local STANDARD time, no daylight shift: Saudi Arabia observes none,
           # so UTC+3 fixed is the EPW clock convention.
           "&timezone=Asia%2FRiyadh&windspeed_unit=ms")
    last = None
    for a in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as e:                     # rate limit or transient
            last = e
            time.sleep(3.0 * (a + 1))
    raise RuntimeError(f"{city} {year}: {last}")


def tidy(d, city, year):
    """Validate and convert to the three EPW fields plus RH.

    Checks that would otherwise become silent corruption downstream:
      * exactly 8760 or 8784 hours (leap), and we trim leap years to 8760 by
        dropping 29 February, because the simulator indexes days 0..364 and a
        366-day record would silently shift every window after the leap day
      * no gaps: a None in any field is interpolated only if isolated, and the
        year is REJECTED if any field has a run of more than three missing hours
      * irradiance non-negative, temperature inside a physically possible range
    """
    h = d["hourly"]
    t_all = np.array(h["time"])
    n_all = len(t_all)
    # ERA5 1 h shift (R4 S5, RULING F15). Row j of the API is stamped at the END of its hour
    # (radiation: mean over [t-1h, t]; temperature/RH: instantaneous at t). EPW hour i (1-based)
    # is the interval [i-1, i) stamped at its end, so EPW hour i <- API row i (00:00 of 1 Jan is
    # dropped; 00:00 of 1 Jan year+1 closes the last interval). The interval START of EPW hour i
    # is API timestamp i-1, which decides the date (and hence the 29 Feb trim) below.
    if n_all not in (8760 + 24, 8784 + 24):
        raise ValueError(f"{city} {year}: {n_all} hours, expected 8784/8808 (year + 1 Jan)")
    n = n_all - 24
    if not (t_all[0].startswith(f"{year}-01-01T00") and t_all[n].startswith(f"{year + 1}-01-01T00")):
        raise ValueError(f"{city} {year}: unexpected time axis {t_all[0]} .. {t_all[n]}")
    t = t_all[:n]                         # interval start of EPW hour 1..n
    sl = slice(1, n + 1)                  # the hour-ending rows that close those intervals

    def arr(k):
        v = np.array([np.nan if x is None else float(x) for x in h[k][sl]])
        bad = ~np.isfinite(v)
        if bad.any():
            # reject on any long gap; interpolate isolated ones
            runs, run = [], 0
            for b in bad:
                run = run + 1 if b else 0
                runs.append(run)
            if max(runs) > 3:
                raise ValueError(f"{city} {year}: {k} has a gap of "
                                 f"{max(runs)} h")
            idx = np.arange(n)
            v[bad] = np.interp(idx[bad], idx[~bad], v[~bad])
        return v

    tdb = arr("temperature_2m")
    rh = np.clip(arr("relative_humidity_2m"), 0.0, 100.0)
    dni = np.maximum(0.0, arr("direct_normal_irradiance"))
    dhi = np.maximum(0.0, arr("diffuse_radiation"))
    ghi = np.maximum(0.0, arr("shortwave_radiation"))

    if n == 8784:                       # drop 29 February
        keep = np.array([not s[5:10] == "02-29" for s in t])
        tdb, rh, dni, dhi, ghi = (x[keep] for x in (tdb, rh, dni, dhi, ghi))
        if tdb.size != 8760:
            raise ValueError(f"{city} {year}: leap trim gave {tdb.size}")

    if not (-20.0 < tdb.min() and tdb.max() < 60.0):
        raise ValueError(f"{city} {year}: T range {tdb.min():.1f}..{tdb.max():.1f}")
    # DNI is normal to the beam, so it legitimately exceeds GHI at low sun; the
    # closure that must hold is on the HORIZONTAL projection, and only loosely,
    # because the API's components are modelled. Flag, do not reject.
    note = ""
    if (dhi > ghi + 25.0).sum() > 50:
        note = "diffuse exceeds global in >50 h"
    return dict(tdb=tdb, rh=rh, dni=dni, dhi=dhi, ghi=ghi, note=note,
                elevation=d.get("elevation"), grid_lat=d.get("latitude"),
                grid_lon=d.get("longitude"), models=MODELS, hour_convention="hour-ending (EPW)")


def write_csv(city, year, rec):
    os.makedirs(OUT, exist_ok=True)
    p = f"{OUT}/{city}_{year}.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hour", "tdb_C", "rh_pct", "dni_Wm2", "dhi_Wm2", "ghi_Wm2"])
        for i in range(8760):
            w.writerow([i + 1, f"{rec['tdb'][i]:.2f}", f"{rec['rh'][i]:.1f}",
                        f"{rec['dni'][i]:.1f}", f"{rec['dhi'][i]:.1f}",
                        f"{rec['ghi'][i]:.1f}"])
    return p


def summarise(city, year, rec):
    """The two statistics that decide which years get used.

    Cooling degree-days base 24 degC drives the cooling load and therefore the
    headroom; the summer mean dry-bulb is reported alongside because CDD alone
    cannot distinguish a long mild summer from a short severe one.
    """
    tdb = rec["tdb"]
    daily = tdb.reshape(365, 24).mean(axis=1)
    cdd24 = float(np.maximum(0.0, daily - 24.0).sum())
    jja = tdb.reshape(365, 24)[151:243].mean()     # 1 Jun - 31 Aug
    return dict(city=city, year=year, cdd24=round(cdd24, 1),
                t_mean=round(float(tdb.mean()), 2),
                t_jja=round(float(jja), 2), t_max=round(float(tdb.max()), 1),
                rh_jja=round(float(rec["rh"].reshape(365, 24)[151:243].mean()), 1),
                ghi_sum_kWh=round(float(rec["ghi"].sum()) / 1000.0, 1),
                elevation=rec["elevation"], grid_lat=rec.get("grid_lat"),
                grid_lon=rec.get("grid_lon"), models=rec.get("models"),
                ghi_centroid_dev_h=round(ghi_centroid_dev(rec["ghi"], city), 3),
                note=rec["note"])


def solar_noon_lst(city, n_days=365):
    """Local standard time (UTC+3, meridian 45 E) of solar noon per day of year (Spencer-type
    equation of time, minutes; accuracy ~1 min, ample for a 0.5 h acceptance band)."""
    d = np.arange(1, n_days + 1)
    B = 2 * np.pi * (d - 81) / 364.0
    eot = 9.87 * np.sin(2 * B) - 7.53 * np.cos(B) - 1.5 * np.sin(B)
    return 12.0 - (SITES[city]["lon"] - 45.0) / 15.0 - eot / 60.0


def ghi_centroid_dev(ghi, city):
    """Mean over days of (GHI-weighted centroid of the day's hours - solar noon), in hours.
    Row k (0-based within the day) is the interval [k, k+1) -> centre k + 0.5, which is the
    hour vertical_irradiance assigns to it. ~0 for a correctly aligned record (F15 test)."""
    g = np.asarray(ghi, float)[:8760].reshape(365, 24)
    c = (g * (np.arange(24) + 0.5)).sum(1) / np.maximum(g.sum(1), 1e-9)
    ok = g.sum(1) > 0
    return float(np.mean((c - solar_noon_lst(city))[ok]))


if __name__ == "__main__":
    rows, failed = [], []
    for city in SITES:
        for year in YEARS:
            tag = f"{city} {year}"
            try:
                rec = tidy(fetch(city, year), city, year)
                write_csv(city, year, rec)
                s = summarise(city, year, rec)
                rows.append(s)
                print(f"  {tag:14s} CDD24={s['cdd24']:7.1f}  "
                      f"T_JJA={s['t_jja']:5.2f}  RH_JJA={s['rh_jja']:4.1f}%  "
                      f"elev={s['elevation']}  {s['note']}", flush=True)
            except Exception as e:
                failed.append((tag, str(e)))
                print(f"  {tag:14s} FAILED: {e}", flush=True)
            time.sleep(0.6)             # courtesy to a free public endpoint

    with open(f"{OUT}/amy_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    print(f"\n{len(rows)} years written, {len(failed)} failed")
    # Pick the extremes per city by CDD24: the question the reviewers asked is
    # how much the saving ratio moves between a hot year and a mild year, so the
    # two years used are the argmax and argmin, not a random pair.
    print("\nYEARS SELECTED FOR THE SPREAD STUDY (by CDD base 24 degC)")
    sel = {}
    for city in SITES:
        rs = [r for r in rows if r["city"] == city]
        if not rs:
            continue
        hot = max(rs, key=lambda r: r["cdd24"])
        mild = min(rs, key=lambda r: r["cdd24"])
        med = sorted(rs, key=lambda r: r["cdd24"])[len(rs) // 2]
        sel[city] = dict(hot=hot["year"], mild=mild["year"], median=med["year"])
        print(f"  {city:8s} hot {hot['year']} (CDD {hot['cdd24']:.0f})  "
              f"median {med['year']} (CDD {med['cdd24']:.0f})  "
              f"mild {mild['year']} (CDD {mild['cdd24']:.0f})  "
              f"-> spread {hot['cdd24'] - mild['cdd24']:.0f} degC.d "
              f"({100*(hot['cdd24']-mild['cdd24'])/med['cdd24']:.1f}% of median)")
    with open(f"{OUT}/amy_selected.json", "w") as f:
        json.dump(sel, f, indent=2)
    print(f"\n-> {OUT}/amy_summary.csv, {OUT}/amy_selected.json")
