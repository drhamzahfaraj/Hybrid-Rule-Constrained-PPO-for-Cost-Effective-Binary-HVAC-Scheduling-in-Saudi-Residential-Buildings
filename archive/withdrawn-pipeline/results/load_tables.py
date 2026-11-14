"""Load the published result tables and re-verify their internal arithmetic.

    python results/load_tables.py

Reads every CSV in results/tables/, prints a summary, and recomputes each
reported percentage from the costs it derives from. Exits non-zero if any
value fails to reproduce, so it can be used as a CI check.
"""
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = os.path.join(HERE, "tables")
TOL = 0.06  # percentage points


def load(name):
    with open(os.path.join(TABLES, name), newline="") as f:
        return list(csv.DictReader(f))


def check(label, computed, reported, failures):
    if abs(computed - reported) > TOL:
        failures.append(f"{label}: computed {computed:.2f} %, reported {reported:.2f} %")


def main():
    failures = []

    rows = load("consumption_monthly.csv")
    for r in rows:
        t, b = float(r["therm_sar_zone_month"]), float(r["rbrl_sar_zone_month"])
        check(f"consumption {r['city']} {r['config']}",
              (t - b) / t * 100, float(r["saving_pct"]), failures)

    cm = load("cost_model_comparison.csv")
    therm = {(r["city"], r["config"], r["cost_model"]): float(r["j_bar_sar_zone_day"])
             for r in cm if r["method"] == "THERM"}
    for r in cm:
        if r["method"] != "THERM" and r["saving_vs_therm_pct"]:
            t = therm[(r["city"], r["config"], r["cost_model"])]
            check(f"cost-model {r['city']} {r['config']} {r['cost_model']} {r['method']}",
                  (t - float(r["j_bar_sar_zone_day"])) / t * 100,
                  float(r["saving_vs_therm_pct"]), failures)

    base = 1.98  # RBRL full, Riyadh 4x4, Model S
    for r in load("ablation_components.csv"):
        if r["variant"] == "RBRL full":
            continue
        check(f"ablation {r['variant']}",
              (float(r["j_bar_sar_zone_day"]) - base) / base * 100,
              float(r["delta_vs_rbrl_pct"]), failures)

    for r in load("cost_model_mismatch.csv"):
        check(f"mismatch {r['training_cost_model']}",
              (float(r["true_cost_under_S_sar_zone_day"]) - base) / base * 100,
              float(r["penalty_pct"]), failures)

    print(f"{'file':42}{'rows':>6}")
    print("-" * 48)
    for path in sorted(glob.glob(os.path.join(TABLES, "*.csv"))):
        with open(path, newline="") as f:
            n = sum(1 for _ in csv.DictReader(f))
        print(f"{os.path.basename(path):42}{n:>6}")

    print()
    if failures:
        print(f"{len(failures)} value(s) failed to reproduce:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("All reported percentages reproduce from their source costs.")


if __name__ == "__main__":
    main()
