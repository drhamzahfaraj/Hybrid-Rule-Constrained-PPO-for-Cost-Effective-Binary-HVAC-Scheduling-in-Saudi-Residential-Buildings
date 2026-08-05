"""Regenerate summary figures from the published CSV tables.

    python results/plot_results.py [--outdir figures]

Produces: savings by configuration, cost-model comparison, the switching-cost
trade-off, and the thermal-capacity sensitivity. Reads only results/tables/*.csv,
so it runs without a trained agent.
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = os.path.join(HERE, "tables")


def load(name):
    with open(os.path.join(TABLES, name), newline="") as f:
        return list(csv.DictReader(f))


def fig_savings_by_config(outdir):
    rows = load("consumption_monthly.csv")
    cfgs = [r["config"] for r in rows if r["city"] == "riyadh"]
    riy = [float(r["saving_pct"]) for r in rows if r["city"] == "riyadh"]
    jed = [float(r["saving_pct"]) for r in rows if r["city"] == "jeddah"]
    x = range(len(cfgs))
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar([i - 0.2 for i in x], riy, 0.4, label="Riyadh (BWh)")
    ax.bar([i + 0.2 for i in x], jed, 0.4, label="Jeddah (BSh)")
    ax.set_xticks(list(x)); ax.set_xticklabels(cfgs)
    ax.set_xlabel("Zone configuration"); ax.set_ylabel("Cost saving vs THERM (%)")
    ax.set_title("Monthly saving by configuration (720 h horizon)")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "savings_by_config.png"), dpi=200)
    plt.close(fig)


def fig_cost_models(outdir):
    rows = [r for r in load("cost_model_comparison.csv") if r["config"] == "4x4"]
    models = ["L", "E", "S"]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    for k, city in enumerate(("riyadh", "jeddah")):
        vals = []
        for m in models:
            v = [r for r in rows if r["city"] == city and r["cost_model"] == m
                 and r["method"] == "RBRL"]
            vals.append(float(v[0]["saving_vs_therm_pct"]) if v else 0.0)
        ax.bar([i + (k - 0.5) * 0.4 for i in range(3)], vals, 0.4, label=city.title())
    ax.set_xticks(range(3))
    ax.set_xticklabels(["Linear", "Exponential", "Step-wise"])
    ax.set_xlabel("Cost model used in training")
    ax.set_ylabel("Saving vs THERM (%)")
    ax.set_title("Cost-model fidelity (4x4, 168 h horizon)")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "cost_models.png"), dpi=200)
    plt.close(fig)


def fig_switching(outdir):
    rows = load("sensitivity_switching_cost.csv")
    c = [float(r["c_sw_sar"]) for r in rows]
    j = [float(r["j_bar_sar_zone_day"]) for r in rows]
    f = [float(r["switches_zone_day"]) for r in rows]
    fig, ax1 = plt.subplots(figsize=(6, 3.4))
    ax1.plot(c, j, "o-", label="cost")
    ax1.set_xlabel("Switching cost $c_{sw}$ (SAR)")
    ax1.set_ylabel("Cost (SAR/zone/day)")
    ax2 = ax1.twinx()
    ax2.plot(c, f, "s--", color="tab:red", label="switching")
    ax2.set_ylabel("Switches/zone/day")
    ax1.set_title("Switching-cost trade-off")
    ax1.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "switching_tradeoff.png"), dpi=200)
    plt.close(fig)


def fig_capacity(outdir):
    rows = load("sensitivity_thermal_capacity.csv")
    c = [float(r["c_th_kj_per_k"]) for r in rows]
    s = [float(r["saving_pct"]) for r in rows]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.semilogx(c, s, "o-")
    for x, y, r in zip(c, s, rows):
        ax.annotate(r["description"], (x, y), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8)
    ax.set_xlabel("Thermal capacity $C_{th}$ (kJ/K, log scale)")
    ax.set_ylabel("Saving vs THERM (%)")
    ax.set_ylim(16, 19)
    ax.set_title("Saving is insensitive to thermal capacity (<1 pp)")
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "capacity_sensitivity.png"), dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(HERE, "..", "figures"))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    fig_savings_by_config(a.outdir)
    fig_cost_models(a.outdir)
    fig_switching(a.outdir)
    fig_capacity(a.outdir)
    print("figures written to", os.path.abspath(a.outdir))
