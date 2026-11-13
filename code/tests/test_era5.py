"""F15 (RULING_round4 §3): ERA5 1 h shift (R4 S5), pinned models= (R4 S9), solar-noon test.

Acceptance: the per-day GHI centroid of every ERA5 CSV lies within +/-0.5 h of solar noon
(mean over days), with row k of a day taken as the interval [k, k+1) -- the convention of the
EPW files and of hvac.vertical_irradiance. The legacy (unshifted) files fail this by ~+1 h.

Run: cd /home/claude/rbrl && OMP_NUM_THREADS=1 nice python3 -m pytest -q tests/test_era5.py
"""
import os, sys, glob, json
import numpy as np
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import amy_fetch as A


def _synthetic_response(city, year):
    """An Open-Meteo-shaped response for year + 1 Jan of year+1, hour-ENDING stamps: radiation at
    stamp t is the mean of a clear-sky bell over [t-1h, t], peaked at the true solar noon."""
    leap = (year % 4 == 0)
    n_days = 366 if leap else 365
    n = 24 * n_days + 24
    import datetime as dt
    t0 = dt.datetime(year, 1, 1)
    times = [(t0 + dt.timedelta(hours=j)).strftime("%Y-%m-%dT%H:%M") for j in range(n)]
    sn_365 = A.solar_noon_lst(city, 365)
    ghi = np.zeros(n)
    for j in range(1, n):
        day = min((j - 1) // 24, n_days - 1)
        day365 = min(day, 364)
        sn = sn_365[day365]
        s = np.linspace(j - 1, j, 61) - 24 * day          # clock hours within the day
        ghi[j] = np.mean(np.maximum(0.0, np.cos(np.pi * (s - sn) / 13.0)) ** 1.5) * 1000.0
    temp = 30.0 + 8.0 * np.sin(2 * np.pi * (np.arange(n) - 9) / 24.0)
    z = list(np.zeros(n))
    return dict(hourly=dict(time=times, temperature_2m=list(temp), relative_humidity_2m=[20.0] * n,
                            direct_normal_irradiance=list(ghi), diffuse_radiation=z,
                            shortwave_radiation=list(ghi)),
                elevation=600.0, latitude=24.75, longitude=46.75)


@pytest.mark.parametrize("year", (2018, 2020))
def test_tidy_realigns_hour_ending_stamps(year):
    city = "riyadh"
    rec = A.tidy(_synthetic_response(city, year), city, year)
    assert rec["ghi"].size == 8760
    dev = A.ghi_centroid_dev(rec["ghi"], city)
    assert abs(dev) < 0.05, dev                     # exact alignment on a synthetic bell
    # the legacy indexing (API row j -> EPW hour j+1) is 1 h late on the same input
    d = _synthetic_response(city, year)
    g = np.asarray(d["hourly"]["shortwave_radiation"])[:8760]
    assert abs(A.ghi_centroid_dev(g, city) - 1.0) < 0.05


def test_tidy_rejects_unextended_record():
    d = _synthetic_response("riyadh", 2018)
    for k, v in d["hourly"].items():
        d["hourly"][k] = v[:8760]
    with pytest.raises(ValueError):
        A.tidy(d, "riyadh", 2018)


def test_fetch_pins_models_and_extends_one_day(monkeypatch):
    seen = {}

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    def fake(url, timeout=None):
        seen["url"] = url
        return R()
    monkeypatch.setattr(A.urllib.request, "urlopen", fake)
    A.fetch("taif", 2019)
    assert "models=era5" in seen["url"]
    assert "start_date=2019-01-01" in seen["url"] and "end_date=2020-01-01" in seen["url"]


FILES = sorted(glob.glob(f"{ROOT}/amy/*_[12][0-9][0-9][0-9].csv"))


@pytest.mark.skipif(not FILES, reason="no ERA5 CSVs on disk")
@pytest.mark.parametrize("path", FILES, ids=lambda p: os.path.basename(p))
def test_solar_noon_centroid(path):
    """GHI centroid within +/-0.5 h of solar noon in every ERA5 CSV on disk."""
    import csv
    city = os.path.basename(path).split("_")[0]
    g = np.array([float(r["ghi_Wm2"]) for r in csv.DictReader(open(path))])
    assert g.size == 8760
    dev = A.ghi_centroid_dev(g, city)
    assert abs(dev) <= 0.5, f"{path}: GHI centroid {dev:+.2f} h from solar noon"


@pytest.mark.skipif(not os.path.exists(f"{ROOT}/amy/amy_summary.csv"), reason="no summary")
def test_summary_records_pinned_model_and_elevation():
    import csv
    rows = list(csv.DictReader(open(f"{ROOT}/amy/amy_summary.csv")))
    assert rows and all(r.get("models") == "era5" for r in rows)
    assert all(r.get("elevation") not in (None, "") for r in rows)
