"""Consistency tests for the published result tables.

    python -m pytest tests/ -v      (or simply: python tests/test_tables.py)

These check that every percentage reported in results/tables/ reproduces from
the costs it derives from, and that the files are well formed. They need no
trained agent and no heavy dependencies.
"""
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = os.path.join(HERE, "..", "results", "tables")
TOL = 0.06  # percentage points


def _load(name):
    with open(os.path.join(TABLES, name), newline="") as f:
        return list(csv.DictReader(f))


def test_all_csv_rectangular():
    for path in glob.glob(os.path.join(TABLES, "*.csv")):
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        width = len(rows[0])
        for i, r in enumerate(rows):
            assert len(r) == width, f"{os.path.basename(path)} row {i} is ragged"


def test_consumption_savings_reproduce():
    for r in _load("consumption_monthly.csv"):
        t = float(r["therm_sar_zone_month"])
        b = float(r["rbrl_sar_zone_month"])
        assert abs((t - b) / t * 100 - float(r["saving_pct"])) < TOL, \
            f"{r['city']} {r['config']}"


def test_cost_model_savings_reproduce():
    rows = _load("cost_model_comparison.csv")
    therm = {(r["city"], r["config"], r["cost_model"]): float(r["j_bar_sar_zone_day"])
             for r in rows if r["method"] == "THERM"}
    for r in rows:
        if r["method"] == "THERM" or not r["saving_vs_therm_pct"]:
            continue
        t = therm[(r["city"], r["config"], r["cost_model"])]
        v = (t - float(r["j_bar_sar_zone_day"])) / t * 100
        assert abs(v - float(r["saving_vs_therm_pct"])) < TOL, \
            f"{r['city']} {r['config']} {r['cost_model']} {r['method']}"


def test_ablation_deltas_reproduce():
    base = 1.98
    for r in _load("ablation_components.csv"):
        if r["variant"] == "RBRL full":
            continue
        v = (float(r["j_bar_sar_zone_day"]) - base) / base * 100
        assert abs(v - float(r["delta_vs_rbrl_pct"])) < TOL, r["variant"]


def test_mismatch_penalties_reproduce():
    base = 1.98
    for r in _load("cost_model_mismatch.csv"):
        v = (float(r["true_cost_under_S_sar_zone_day"]) - base) / base * 100
        assert abs(v - float(r["penalty_pct"])) < TOL, r["training_cost_model"]


def test_comfort_violations_zero_for_rule_constrained():
    """Every rule-constrained variant must report zero comfort violations."""
    for r in _load("ablation_components.csv"):
        if "RL only" in r["variant"]:
            continue  # the unconstrained ablation is expected to violate
        assert float(r["vc_pct"]) == 0.0, r["variant"]


def test_configs_match_paper_parameters():
    import yaml
    cfg_dir = os.path.join(HERE, "..", "configs")
    for path in glob.glob(os.path.join(cfg_dir, "*.yaml")):
        c = yaml.safe_load(open(path))
        assert c["c_th"] == 77.2, path
        assert c["dt"] == 1.0, path
        assert c["c_sw"] == 0.15, path
        assert [c["t_min"], c["t_max"]] == [22.0, 26.0], path


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    raise SystemExit(1 if failed else 0)
