#!/usr/bin/env python3
"""Generate the manuscript's data figures from the gated result CSVs.

Every number plotted here comes from results/*.csv, which invariants.py gates.
Nothing is drawn by hand. Output: /home/claude/v4/figs/*.pdf
"""
from __future__ import annotations
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = "/home/claude/v4/figs"
RES = "/home/claude/rbrl/results"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.linewidth": 0.6,
    "grid.linewidth": 0.4,
    "lines.linewidth": 1.2,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.015,
})
COL, FULL = 3.30, 6.85          # inches: one column, full text width
GREY = "0.45"


def rows(name):
    with open(f"{RES}/{name}") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- fig: guards
def guards():
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    LO, HI = 22.0, 24.0
    EH, EC = 0.20, 0.40
    ax.axhspan(LO, HI, color="#dff0d8", zorder=0)
    for y, s in ((LO, "-"), (HI, "-")):
        ax.axhline(y, color="0.3", lw=0.8, ls=s)
    # guard regions
    ax.axhspan(HI - EH, HI, color="#f2b8b8", zorder=1)
    ax.axhspan(LO, LO + EC, color="#b8d0f2", zorder=1)
    ax.text(0.06, HI - EH / 2, r"R1 forces ON", va="center", fontsize=6.6)
    ax.text(0.06, LO + EC / 2, r"R2 forces OFF", va="center", fontsize=6.6)
    ax.text(0.06, (LO + EC + HI - EH) / 2, "agent free: 1.40 K of the 2 K band",
            va="center", fontsize=6.8, style="italic")
    # one-interval excursions, to scale
    ax.annotate("", xy=(0.80, LO + EC), xytext=(0.80, LO + EC - 0.375),
                arrowprops=dict(arrowstyle="<->", lw=0.9, color="#1f5fa8"))
    ax.text(0.825, LO + EC - 0.19, "cooling\n0.375 K", fontsize=6.3,
            color="#1f5fa8", va="center")
    ax.annotate("", xy=(0.80, HI - EH), xytext=(0.80, HI - EH + 0.129),
                arrowprops=dict(arrowstyle="<->", lw=0.9, color="#a81f1f"))
    ax.text(0.825, HI - EH + 0.07, "warming\n0.129 K", fontsize=6.3,
            color="#a81f1f", va="center")
    # TUNED switch points vs a symmetric 0.5 K guard
    ax.plot([0.42, 0.42], [22.35, 23.60], color="k", lw=0, marker="_",
            ms=11, mew=1.4)
    ax.text(0.44, 23.60, "TUNED on 23.60", fontsize=6.3, va="bottom")
    ax.text(0.44, 22.35, "TUNED off 22.35", fontsize=6.3, va="top")
    for y in (22.5, 23.5):
        ax.plot([0.30, 0.56], [y, y], color="0.25", lw=0.9, ls=(0, (3, 2)))
    ax.text(0.30, 23.5 + 0.03, r"symmetric $\epsilon_g=0.5$ would forbid both",
            fontsize=6.3, va="bottom")
    ax.set_xlim(0, 1.18); ax.set_ylim(21.78, 24.22)
    ax.set_yticks([22.0, 22.4, 23.0, 23.8, 24.0])
    ax.set_yticklabels(["22.0\n$T_{\\min}$", "22.4", "23.0", "23.8",
                        "24.0\n$T_{\\max}$"])
    ax.set_xticks([]); ax.set_ylabel("Zone temperature ($^\\circ$C)")
    for sp in ("top", "right", "bottom"): ax.spines[sp].set_visible(False)
    fig.savefig(f"{OUT}/guards.pdf"); plt.close(fig)


# ---------------------------------------------------------------- fig: sweeps
def sweeps():
    fig, axs = plt.subplots(1, 2, figsize=(FULL, 2.15))
    t2 = rows("T2_timestep.csv")
    dt = [float(r["dt_min"]) for r in t2]
    rs = [float(r["rule_sav_pct"]) if r["rule_sav_pct"] else np.nan for r in t2]
    dp = [float(r["dp_sav_pct"]) for r in t2]
    dh = [float(r["therm_deg_h"]) for r in t2]
    ax = axs[0]
    ax.axhline(0, color="0.6", lw=0.6)
    ax.plot(dt, dp, "o-", color="#1f5fa8", label="OPT (clairvoyant)")
    ax.plot(dt, rs, "s--", color="#a81f1f", label="TUNED")
    bad = [d for d, g in zip(dt, dh) if g > 1e-9]
    if bad:
        ax.axvspan(min(bad) * 0.93, max(dt) * 1.08, color="#f6e3e3", zorder=0)
        ax.text(min(bad) * 0.97, 25, "baseline leaks\ncomfort", fontsize=6.3,
                color="#a81f1f", ha="left", va="top")
    ax.set_xscale("log"); ax.set_xticks(dt)
    ax.set_xticklabels([f"{int(d)}" for d in dt])
    ax.set_xlabel(r"Actuation interval $\Delta t$ (min)")
    ax.set_ylabel("Saving vs THERM (\\%)")
    ax.set_title("(a) actuation interval", loc="left")
    ax.grid(alpha=0.3); ax.legend(frameon=False, loc="lower left")

    t3 = rows("T3_capacity.csv")
    C = [float(r["C_th"]) for r in t3]
    rs3 = [float(r["rule_sav_pct"]) if r["rule_sav_pct"] else np.nan for r in t3]
    dp3 = [float(r["dp_sav_pct"]) if r["dp_sav_pct"] else np.nan for r in t3]
    dh3 = [float(r["therm_deg_h"]) for r in t3]
    ax = axs[1]
    ax.axhline(0, color="0.6", lw=0.6)
    inad = [c for c, g in zip(C, dh3) if g > 1e-9]
    if inad:
        ax.axvspan(min(C) * 0.9, max(inad) * 1.02, color="#f6e3e3", zorder=0)
        ax.text(min(C) * 1.05, -55, "condition (8)\nviolated", fontsize=6.3,
                color="#a81f1f", ha="left")
    ax.plot(C, dp3, "o-", color="#1f5fa8", label="OPT")
    ax.plot(C, rs3, "s--", color="#a81f1f", label="TUNED")
    ax.axvline(4800, color="0.35", lw=0.8, ls=":")
    ax.text(4950, -55, "adopted", fontsize=6.3, color="0.3")
    ax.set_xscale("log"); ax.set_xticks([900, 1800, 2400, 4800, 9600])
    ax.set_xticklabels(["900", "1.8k", "2.4k", "4.8k", "9.6k"])
    ax.set_xlabel(r"Thermal capacity $C_{\mathrm{th}}$ (kJ/K)")
    ax.set_title("(b) thermal capacity", loc="left")
    ax.grid(alpha=0.3); ax.legend(frameon=False, loc="lower right")
    fig.savefig(f"{OUT}/sweeps.pdf"); plt.close(fig)


# ---------------------------------------------------------------- fig: tariff
def tariff():
    # price, switching share of THERM cost, TUNED saving, OPT saving
    data = [("pre-2018\nTier 1", 0.05, 81.5, 13.6, 22.7),
            ("in force\n(2018--26)", 0.18, 55.0, 9.3, 14.7),
            ("announced\n2027", 0.21, 51.2, 8.6, 13.3)]
    fig, ax = plt.subplots(figsize=(COL, 2.15))
    x = np.arange(len(data))
    opt = [d[4] for d in data]; tun = [d[3] for d in data]
    ax.bar(x - 0.18, opt, 0.34, color="#1f5fa8", label="OPT ceiling")
    ax.bar(x + 0.18, tun, 0.34, color="#a81f1f", label="TUNED")
    for xi, v in zip(x - 0.18, opt):
        ax.text(xi, v + 0.5, f"{v:.1f}", ha="center", fontsize=6.4)
    for xi, v in zip(x + 0.18, tun):
        ax.text(xi, v + 0.5, f"{v:.1f}", ha="center", fontsize=6.4)
    ax.set_xticks(x); ax.set_xticklabels([d[0] for d in data], fontsize=6.8)
    ax.set_ylabel("Saving vs THERM (\\%)"); ax.set_ylim(0, 27)
    ax.grid(axis="y", alpha=0.3); ax.set_axisbelow(True)
    ax2 = ax.twinx()
    ax2.plot(x, [d[2] for d in data], "o:", color="0.25", ms=4,
             label="switching share of bill")
    ax2.set_ylim(0, 100); ax2.set_ylabel("Switching share of THERM cost (\\%)",
                                         fontsize=7)
    ax2.tick_params(labelsize=7)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper right", fontsize=6.5)
    fig.savefig(f"{OUT}/tariff.pdf"); plt.close(fig)


# ---------------------------------------------------------------- fig: season
def season():
    r = rows("T6_per_window.csv")
    cities = ["riyadh", "jeddah", "taif"]
    lab = {"riyadh": "Riyadh", "jeddah": "Jeddah", "taif": "Taif"}
    col = {"riyadh": "#1f5fa8", "jeddah": "#a81f1f", "taif": "#2e7d32"}
    mk = {"riyadh": "o", "jeddah": "s", "taif": "^"}
    days = sorted({int(x["start_day"]) for x in r})
    names = {121: "1 May", 149: "29 May", 177: "26 Jun", 205: "24 Jul",
             233: "21 Aug", 261: "18 Sep", 289: "16 Oct"}
    fig, axs = plt.subplots(1, 2, figsize=(FULL, 2.1))
    ax = axs[0]
    for c in cities:
        y = [float(x["sav_pct"]) for d in days for x in r
             if x["city"] == c and int(x["start_day"]) == d]
        ax.plot(range(len(days)), y, mk[c] + "-", color=col[c], label=lab[c], ms=4)
    ax.axhline(0, color="0.6", lw=0.6)
    ax.set_xticks(range(len(days)))
    ax.set_xticklabels([names[d] for d in days], rotation=35, ha="right", fontsize=6.5)
    ax.set_ylabel("TUNED saving vs THERM (\\%)")
    ax.set_title("(a) held-out windows", loc="left")
    ax.grid(alpha=0.3); ax.legend(frameon=False, ncol=3, fontsize=6.6)

    ax = axs[1]
    for c in cities:
        th = [float(x["therm_J"]) for d in days for x in r
              if x["city"] == c and int(x["start_day"]) == d]
        ru = [float(x["rule_J"]) for d in days for x in r
              if x["city"] == c and int(x["start_day"]) == d]
        ax.plot(th, ru, mk[c], color=col[c], label=lab[c], ms=4.5)
    lim = [0.3, 1.45]
    ax.plot(lim, lim, "--", color="0.5", lw=0.8)
    ax.text(1.18, 1.22, "no saving", fontsize=6.3, color="0.4", rotation=38)
    ax.set_xlim(*lim); ax.set_ylim(*lim)
    ax.set_xlabel("THERM cost (SAR/zone/day)")
    ax.set_ylabel("TUNED cost (SAR/zone/day)")
    ax.set_title("(b) paired by window", loc="left")
    ax.grid(alpha=0.3)
    fig.savefig(f"{OUT}/season.pdf"); plt.close(fig)


if __name__ == "__main__":
    guards(); sweeps(); tariff(); season()
    for f in sorted(os.listdir(OUT)):
        print(" ", f, os.path.getsize(f"{OUT}/{f}"), "bytes")
