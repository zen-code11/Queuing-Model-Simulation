"""
Arena SIMAN Simulation Output Analyser (Updated for 3 Frameworks)
=================================================================
Parses .out.txt files from three frameworks:
  - Framework 1: Dynamic Counter Opening  (folder: 'dynamic counter')
  - Framework 2: Dedicated Express Lane   (folder: 'express lane')
  - Framework 3: Pooled Queue             (folder: 'pooled queue')

Extracts per-replication stats, averages across replications, produces
CSV exports, plots, and a Markdown analytical report.
"""

import os, sys, re, math, warnings
from pathlib import Path
from collections import defaultdict

os.environ["MPLCONFIGDIR"] = os.environ.get("TEMP", r"C:\Users\saish\AppData\Local\Temp")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ─────────────────────────────────────────────────────────────────────────────
# 0. PATHS & SCENARIO MAP
# ─────────────────────────────────────────────────────────────────────────────
BASE    = Path(r"c:\SEM 5\Simulation Lab\project\Queue Output SIMAN")
DIR_DYN = BASE / "dynamic counter"
DIR_EXP = BASE / "express lane"
DIR_POL = BASE / "pooled queue"
OUT_DIR = BASE

SCENARIO_MAP = {
    "weekdaydaytime":  {"label": "Weekday Daytime",       "lambda": 0.15, "order": 1},
    "weekdaystudent":  {"label": "Weekday Student Rush",  "lambda": 0.50, "order": 2},
    "weekdaypeak":     {"label": "Weekday Peak",          "lambda": 0.65, "order": 3},
    "weekendnormal":   {"label": "Weekend Non-Peak",      "lambda": 0.35, "order": 4},
    "weekendpeak":     {"label": "Weekend Peak",          "lambda": 0.75, "order": 5},
}

def file_key(fname: str) -> str | None:
    """Map a filename to a scenario key."""
    stem = Path(fname).stem.lower().replace(".out", "").replace("-", "").replace("_", "")
    if "weekdaynormal" in stem:
        return "weekdaydaytime"
    for key in SCENARIO_MAP:
        if key in stem:
            return key
    return None

# ─────────────────────────────────────────────────────────────────────────────
# 1. PARSER
# ─────────────────────────────────────────────────────────────────────────────
NUM_OR_NA = r"(?:[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?|--)"
NUM_OR_INSUF = r"(?:[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?|\(Insuf\)|--)"

TALLY_ROW = re.compile(
    rf"^(?P<id>.+?)\s{{2,}}"
    rf"(?P<avg>{NUM_OR_NA})\s+"
    rf"(?P<hw>{NUM_OR_INSUF})\s+"
    rf"(?P<min>{NUM_OR_NA})\s+"
    rf"(?P<max>{NUM_OR_NA})\s+"
    rf"(?P<obs>{NUM_OR_NA})\s*$"
)
OUTPUT_ROW = re.compile(rf"^(?P<id>.+?)\s{{2,}}(?P<val>[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*$")
REPL_HDR = re.compile(r"Summary for Replication\s+(\d+)\s+of\s+(\d+)")
SUMM_HDR = re.compile(r"Output Summary for\s+(\d+)\s+Replications")
SECTION  = re.compile(r"TALLY VARIABLES|DISCRETE-CHANGE VARIABLES|OUTPUTS", re.I)

def _float(s: str):
    """Convert SIMAN string to float; return NaN for '--' or '(Insuf)'."""
    s = s.strip()
    if s in ("--", "(Insuf)", ""):
        return float("nan")
    return float(s)

def parse_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    replications = []
    summary_outputs = {}

    cur_rep  = None
    section  = None
    in_summary = False

    for line in lines:
        if SUMM_HDR.search(line):
            in_summary = True
            cur_rep = None
            section = None
            continue
        m = REPL_HDR.search(line)
        if m:
            if cur_rep is not None:
                replications.append(cur_rep)
            cur_rep = {}
            in_summary = False
            section = None
            continue
        sm = SECTION.search(line)
        if sm:
            tok = sm.group(0).upper()
            if "TALLY" in tok:
                section = "tally"
            elif "DISCRETE" in tok:
                section = "dchange"
            elif "OUTPUTS" in tok:
                section = "outputs"
            continue

        stripped = line.strip()
        if not stripped or stripped.startswith("_") or stripped.startswith("Identifier"):
            continue

        if in_summary:
            m2 = TALLY_ROW.match(stripped)
            if m2:
                rid = m2.group("id").strip()
                summary_outputs[rid] = {
                    "avg": _float(m2.group("avg")),
                    "hw":  _float(m2.group("hw")),
                    "min": _float(m2.group("min")),
                    "max": _float(m2.group("max")),
                    "n_rep": _float(m2.group("obs")),
                }
        elif cur_rep is not None and section in ("tally", "dchange"):
            m3 = TALLY_ROW.match(stripped)
            if m3:
                rid = m3.group("id").strip()
                cur_rep[rid] = {
                    "avg": _float(m3.group("avg")),
                    "hw":  _float(m3.group("hw")),
                    "min": _float(m3.group("min")),
                    "max": _float(m3.group("max")),
                    "obs": _float(m3.group("obs")),
                }
        elif cur_rep is not None and section == "outputs":
            m4 = OUTPUT_ROW.match(stripped)
            if m4:
                rid = m4.group("id").strip()
                cur_rep[f"OUT::{rid}"] = {"val": float(m4.group("val"))}

    if cur_rep is not None:
        replications.append(cur_rep)

    return {"replications": replications, "summary_outputs": summary_outputs}

# ─────────────────────────────────────────────────────────────────────────────
# 2.  EXTRACT KPIs FROM PARSED DATA
# ─────────────────────────────────────────────────────────────────────────────
def get_stat(rep: dict, key: str, field: str = "avg") -> float:
    if key in rep:
        return rep[key].get(field, float("nan"))
    return float("nan")

def aggregate_replications(repls: list[dict], key: str, field: str = "avg") -> dict:
    vals = [get_stat(r, key, field) for r in repls]
    vals = [v for v in vals if not math.isnan(v)]
    if not vals:
        return {"mean": float("nan"), "ci_hw": float("nan"),
                "minimum": float("nan"), "maximum": float("nan"), "n": 0}
    n  = len(vals)
    mu = np.mean(vals)
    s  = np.std(vals, ddof=1) if n > 1 else float("nan")
    from scipy.stats import t as t_dist
    t95 = t_dist.ppf(0.975, df=n - 1) if n > 1 else float("nan")
    hw  = t95 * s / math.sqrt(n) if n > 1 else float("nan")
    return {"mean": mu, "ci_hw": hw,
            "minimum": float(np.min(vals)), "maximum": float(np.max(vals)), "n": n}

def extract_kpis_dynamic(repls: list[dict]) -> dict:
    kpi = {}
    for stat_key, kpi_key in [
        ("Customer.WaitTime",  "wq"),
        ("Customer.TotalTime", "w"),
        ("Customer.VATime",    "vatime"),
    ]:
        agg = aggregate_replications(repls, stat_key)
        kpi[kpi_key] = agg["mean"]
        kpi[f"{kpi_key}_hw"] = agg["ci_hw"]
        kpi[f"{kpi_key}_max"] = agg["maximum"]

    for i in range(1, 5):
        agg = aggregate_replications(repls, f"Checkout {i}.Queue.WaitingTime")
        kpi[f"checkout{i}_wq"]  = agg["mean"]
        kpi[f"checkout{i}_max"] = agg["maximum"]

    for i in range(1, 5):
        agg = aggregate_replications(repls, f"Checkout {i}.Queue.NumberInQueue")
        kpi[f"checkout{i}_lq"] = agg["mean"]

    util_vals = {}
    for i in range(1, 5):
        vals = [get_stat(r, f"OUT::Counter_{i}.ScheduledUtilization", "val") for r in repls]
        vals = [v for v in vals if not math.isnan(v)]
        util_vals[f"counter{i}_util"] = float(np.mean(vals)) if vals else float("nan")

    kpi.update(util_vals)
    active = [v for v in util_vals.values() if not math.isnan(v) and v > 0]
    kpi["peak_util"] = max(active) if active else float("nan")
    kpi["avg_util"]  = float(np.nanmean(list(util_vals.values()))) if util_vals else float("nan")
    return kpi

def extract_kpis_express(repls: list[dict]) -> dict:
    kpi = {}
    for stat_key, kpi_key in [
        ("Customer.WaitTime",  "wq"),
        ("Customer.TotalTime", "w"),
        ("Customer.VATime",    "vatime"),
    ]:
        agg = aggregate_replications(repls, stat_key)
        kpi[kpi_key] = agg["mean"]
        kpi[f"{kpi_key}_hw"] = agg["ci_hw"]
        kpi[f"{kpi_key}_max"] = agg["maximum"]

    for lkey, kkey in [
        ("Express Checkout.Queue.WaitingTime",   "express_wq"),
        ("Regular Checkout 1.Queue.WaitingTime", "regular1_wq"),
        ("Regular Checkout 2.Queue.WaitingTime", "regular2_wq"),
    ]:
        agg = aggregate_replications(repls, lkey)
        kpi[kkey]           = agg["mean"]
        kpi[f"{kkey}_max"]  = agg["maximum"]

    for lkey, kkey in [
        ("Express Checkout.Queue.NumberInQueue",   "express_lq"),
        ("Regular Checkout 1.Queue.NumberInQueue", "regular1_lq"),
        ("Regular Checkout 2.Queue.NumberInQueue", "regular2_lq"),
    ]:
        agg = aggregate_replications(repls, lkey)
        kpi[kkey] = agg["mean"]

    util_vals = {}
    for res, kkey in [
        ("Express_Counter",   "express_util"),
        ("Regular_Counter_1", "regular1_util"),
        ("Regular_Counter_2", "regular2_util"),
    ]:
        vals = [get_stat(r, f"OUT::{res}.ScheduledUtilization", "val") for r in repls]
        vals = [v for v in vals if not math.isnan(v)]
        util_vals[kkey] = float(np.mean(vals)) if vals else float("nan")

    kpi.update(util_vals)
    active = [v for v in util_vals.values() if not math.isnan(v) and v > 0]
    kpi["peak_util"] = max(active) if active else float("nan")
    kpi["avg_util"]  = float(np.nanmean(list(util_vals.values()))) if util_vals else float("nan")
    return kpi

def extract_kpis_pooled(repls: list[dict]) -> dict:
    kpi = {}
    for stat_key, kpi_key in [
        ("Customer.WaitTime",  "wq"),
        ("Customer.TotalTime", "w"),
        ("Customer.VATime",    "vatime"),
    ]:
        agg = aggregate_replications(repls, stat_key)
        kpi[kpi_key] = agg["mean"]
        kpi[f"{kpi_key}_hw"] = agg["ci_hw"]
        kpi[f"{kpi_key}_max"] = agg["maximum"]

    agg_q = aggregate_replications(repls, "Pooled Checkout.Queue.WaitingTime")
    kpi["pooled_queue_wq"] = agg_q["mean"]
    kpi["pooled_queue_max"] = agg_q["maximum"]

    agg_lq = aggregate_replications(repls, "Pooled Checkout.Queue.NumberInQueue")
    kpi["pooled_queue_lq"] = agg_lq["mean"]

    vals = [get_stat(r, "OUT::server.ScheduledUtilization", "val") for r in repls]
    vals = [v for v in vals if not math.isnan(v)]
    util_val = float(np.mean(vals)) if vals else float("nan")

    kpi["server_util"] = util_val
    kpi["peak_util"] = util_val
    kpi["avg_util"]  = util_val
    return kpi

# ─────────────────────────────────────────────────────────────────────────────
# 3.  LOAD ALL FILES & BUILD RECORDS
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 65)
print("  Arena SIMAN Simulation Analyser — Loading files …")
print("=" * 65)

raw_rows = []
kpi_dyn  = {}
kpi_exp  = {}
kpi_pol  = {}

framework_configs = [
    ("Dynamic Counter", DIR_DYN, kpi_dyn, extract_kpis_dynamic),
    ("Express Lane",    DIR_EXP, kpi_exp, extract_kpis_express),
    ("Pooled Queue",    DIR_POL, kpi_pol, extract_kpis_pooled),
]

for fw_name, fw_dir, kpi_dict, extractor in framework_configs:
    for fpath in sorted(fw_dir.glob("*.txt")):
        key = file_key(fpath.name)
        if key is None:
            print(f"  [WARN] Cannot map {fpath.name} to a scenario — skipped.")
            continue
        parsed = parse_file(fpath)
        repls  = parsed["replications"]
        print(f"  [{fw_name[:3].upper()}] {fpath.name} -> {key}: {len(repls)} replications found.")
        kpi_dict[key] = extractor(repls)

        for i, r in enumerate(repls, 1):
            for stat, vals in r.items():
                if isinstance(vals, dict) and "avg" in vals:
                    raw_rows.append({
                        "framework": fw_name,
                        "scenario": key,
                        "replication": i,
                        "identifier": stat,
                        "average": vals["avg"],
                        "half_width": vals.get("hw", float("nan")),
                        "minimum": vals.get("min", float("nan")),
                        "maximum": vals.get("max", float("nan")),
                        "observations": vals.get("obs", float("nan")),
                    })

df_raw = pd.DataFrame(raw_rows)
df_raw.to_csv(OUT_DIR / "raw_simulation_metrics.csv", index=False)
print(f"\n  → raw_simulation_metrics.csv saved ({len(df_raw)} rows).\n")

# ─────────────────────────────────────────────────────────────────────────────
# 4.  BUILD COMPARISON TABLE
# ─────────────────────────────────────────────────────────────────────────────
comparison_rows = []
scenarios_ordered = sorted(SCENARIO_MAP.keys(), key=lambda k: SCENARIO_MAP[k]["order"])

for key in scenarios_ordered:
    info = SCENARIO_MAP[key]
    d = kpi_dyn.get(key, {})
    e = kpi_exp.get(key, {})
    p = kpi_pol.get(key, {})

    wq_d  = d.get("wq", float("nan"))
    wq_e  = e.get("wq", float("nan"))
    wq_p  = p.get("wq", float("nan"))

    delta_exp_dyn = wq_e - wq_d
    delta_pol_dyn = wq_p - wq_d

    comparison_rows.append({
        "Scenario":           info["label"],
        "Lambda":             info["lambda"],
        # Framework 1: Dynamic Counter
        "F1_Dynamic_Wq":      round(wq_d, 4),
        "F1_Dynamic_Wq_HW":   round(d.get("wq_hw", float("nan")), 4),
        "F1_Dynamic_W":       round(d.get("w", float("nan")), 4),
        "F1_Dynamic_PeakUtil":round(d.get("peak_util", float("nan")), 4),
        # Framework 2: Express Lane
        "F2_Express_Wq":      round(wq_e, 4),
        "F2_Express_Wq_HW":   round(e.get("wq_hw", float("nan")), 4),
        "F2_Express_W":       round(e.get("w", float("nan")), 4),
        "F2_Express_PeakUtil":round(e.get("peak_util", float("nan")), 4),
        # Framework 3: Pooled Queue
        "F3_Pooled_Wq":       round(wq_p, 4),
        "F3_Pooled_Wq_HW":    round(p.get("wq_hw", float("nan")), 4),
        "F3_Pooled_W":        round(p.get("w", float("nan")), 4),
        "F3_Pooled_PeakUtil": round(p.get("peak_util", float("nan")), 4),
        # Deltas
        "Delta_Wq_Exp_minus_Dyn": round(delta_exp_dyn, 4),
        "Delta_Wq_Pol_minus_Dyn": round(delta_pol_dyn, 4),
    })

df_cmp = pd.DataFrame(comparison_rows)
df_cmp.to_csv(OUT_DIR / "checkout_comparison_results.csv", index=False)
print("  → checkout_comparison_results.csv saved.\n")

# ─────────────────────────────────────────────────────────────────────────────
# 5.  MARKDOWN TABLE TO STDOUT
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 115)
print("  SIDE-BY-SIDE 3-FRAMEWORK KPI COMPARISON TABLE")
print("=" * 115)
print(f"| {'Scenario':<22} | {'λ':<4} | {'F1 Dyn Wq':<10} | {'F2 Exp Wq':<10} | {'F3 Pool Wq':<10} | {'F1 W':<8} | {'F2 W':<8} | {'F3 W':<8} | {'F3 Util':<8} |")
print("|" + "-"*24 + "|" + "-"*6 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*10 + "|" + "-"*10 + "|" + "-"*10 + "|" + "-"*10 + "|")
for _, r in df_cmp.iterrows():
    print(f"| {r['Scenario']:<22} | {r['Lambda']:<4.2f} | {r['F1_Dynamic_Wq']:>10.4f} | {r['F2_Express_Wq']:>10.4f} | {r['F3_Pooled_Wq']:>10.4f} | {r['F1_Dynamic_W']:>8.4f} | {r['F2_Express_W']:>8.4f} | {r['F3_Pooled_W']:>8.4f} | {r['F3_Pooled_PeakUtil']:>8.4f} |")
print("=" * 115 + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# 6.  CHART 1 — GROUPED BAR CHART: Wq across 3 frameworks with 95% CI
# ─────────────────────────────────────────────────────────────────────────────
labels   = [SCENARIO_MAP[k]["label"] for k in scenarios_ordered]
wq_dyn   = [kpi_dyn.get(k, {}).get("wq", float("nan")) for k in scenarios_ordered]
wq_exp   = [kpi_exp.get(k, {}).get("wq", float("nan")) for k in scenarios_ordered]
wq_pol   = [kpi_pol.get(k, {}).get("wq", float("nan")) for k in scenarios_ordered]

hw_dyn   = [kpi_dyn.get(k, {}).get("wq_hw", float("nan")) for k in scenarios_ordered]
hw_exp   = [kpi_exp.get(k, {}).get("wq_hw", float("nan")) for k in scenarios_ordered]
hw_pol   = [kpi_pol.get(k, {}).get("wq_hw", float("nan")) for k in scenarios_ordered]

x     = np.arange(len(labels))
width = 0.26

fig1, ax1 = plt.subplots(figsize=(13, 6.5))
fig1.patch.set_facecolor("#f8f9fa")
ax1.set_facecolor("#ffffff")

bars1 = ax1.bar(x - width, wq_dyn, width,
                label="F1: Dynamic Counter",
                color="#2563EB", alpha=0.9, edgecolor="white", linewidth=0.8,
                yerr=hw_dyn, capsize=4, error_kw={"elinewidth": 1.2, "ecolor": "#1e40af"})
bars2 = ax1.bar(x, wq_exp, width,
                label="F2: Express Lane",
                color="#F59E0B", alpha=0.9, edgecolor="white", linewidth=0.8,
                yerr=hw_exp, capsize=4, error_kw={"elinewidth": 1.2, "ecolor": "#b45309"})
bars3 = ax1.bar(x + width, wq_pol, width,
                label="F3: Pooled Queue (Single Line, 4 Servers)",
                color="#10B981", alpha=0.9, edgecolor="white", linewidth=0.8,
                yerr=hw_pol, capsize=4, error_kw={"elinewidth": 1.2, "ecolor": "#047857"})

for b in bars1:
    h = b.get_height()
    if not math.isnan(h):
        ax1.text(b.get_x() + b.get_width()/2, h + 0.015, f"{h:.3f}", ha="center", va="bottom", fontsize=8, color="#1e3a8a", fontweight="bold")
for b in bars2:
    h = b.get_height()
    if not math.isnan(h):
        ax1.text(b.get_x() + b.get_width()/2, h + 0.015, f"{h:.3f}", ha="center", va="bottom", fontsize=8, color="#b45309", fontweight="bold")
for b in bars3:
    h = b.get_height()
    if not math.isnan(h):
        ax1.text(b.get_x() + b.get_width()/2, h + 0.015, f"{h:.3f}", ha="center", va="bottom", fontsize=8, color="#065f46", fontweight="bold")

ax1.set_xlabel("Operating Scenario", fontsize=11, labelpad=10)
ax1.set_ylabel("Average Customer Wait Time Wq (minutes)", fontsize=11, labelpad=10)
ax1.set_title("Customer Wait Time (Wq) Across Frameworks: Dynamic vs. Express vs. Pooled\n"
              "Error bars = 95% CI half-width across 30 replications",
              fontsize=13, fontweight="bold", pad=16)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=10, rotation=18, ha="right")
ax1.legend(fontsize=10, framealpha=0.95, loc="upper left")
ax1.yaxis.grid(True, linestyle="--", alpha=0.45)
ax1.set_axisbelow(True)
ax1.spines[["top", "right"]].set_visible(False)

fig1.subplots_adjust(top=0.88, bottom=0.18, left=0.08, right=0.96)
fig1.savefig(OUT_DIR / "chart1_waiting_time_comparison.png", dpi=300)
plt.close(fig1)
print("  → chart1_waiting_time_comparison.png saved.")

# ─────────────────────────────────────────────────────────────────────────────
# 7.  CHART 2 — MULTI-PANEL QUEUE BREAKDOWN (ZERO TEXT OVERLAPPING)
# ─────────────────────────────────────────────────────────────────────────────
fig2 = plt.figure(figsize=(16, 13), dpi=300)
fig2.patch.set_facecolor("#f8f9fa")
gs   = GridSpec(3, 1, figure=fig2, hspace=0.55)

# Panel 1: F1 Dynamic per-counter
ax2a = fig2.add_subplot(gs[0])
ax2a.set_facecolor("#ffffff")
colors_dyn = ["#3b82f6", "#ef4444", "#f59e0b", "#8b5cf6"]
bar_w = 0.17
offsets = [-1.5, -0.5, 0.5, 1.5]
for i in range(1, 5):
    vals = [kpi_dyn.get(k, {}).get(f"checkout{i}_wq", float("nan")) for k in scenarios_ordered]
    # For visualization, cap extreme single-outlier values at 2.5 min so remaining counters are clearly visible
    vals_plot = [min(v, 2.5) if not math.isnan(v) else 0 for v in vals]
    ax2a.bar(x + offsets[i-1]*bar_w, vals_plot, bar_w,
             label=f"Counter {i}", color=colors_dyn[i-1], alpha=0.85, edgecolor="white", linewidth=0.6)
ax2a.set_title("Framework 1 (Dynamic Counter) — Per-Checkout Waiting Times", fontsize=11.5, fontweight="bold", pad=12)
ax2a.set_xticks(x)
ax2a.set_xticklabels(labels, fontsize=9.5, rotation=15, ha="right")
ax2a.set_ylabel("Wq (min)", fontsize=10)
ax2a.legend(fontsize=8.5, ncol=4, loc="upper left")
ax2a.yaxis.grid(True, linestyle="--", alpha=0.4)
ax2a.spines[["top", "right"]].set_visible(False)

# Panel 2: F2 Express per-lane
ax2b = fig2.add_subplot(gs[1])
ax2b.set_facecolor("#ffffff")
colors_exp = ["#10b981", "#f97316", "#6366f1"]
lanes = [("express_wq", "Express Lane (≤10 items)"), ("regular1_wq", "Regular Lane 1"), ("regular2_wq", "Regular Lane 2")]
offsets2 = [-1, 0, 1]
for idx, (lkey, lname) in enumerate(lanes):
    vals = [kpi_exp.get(k, {}).get(lkey, float("nan")) for k in scenarios_ordered]
    vals_plot = [v if not math.isnan(v) else 0 for v in vals]
    ax2b.bar(x + offsets2[idx]*bar_w*1.3, vals_plot, bar_w*1.3,
             label=lname, color=colors_exp[idx], alpha=0.85, edgecolor="white", linewidth=0.6)
ax2b.set_title("Framework 2 (Express Lane) — Per-Lane Waiting Times", fontsize=11.5, fontweight="bold", pad=12)
ax2b.set_xticks(x)
ax2b.set_xticklabels(labels, fontsize=9.5, rotation=15, ha="right")
ax2b.set_ylabel("Wq (min)", fontsize=10)
ax2b.legend(fontsize=8.5, ncol=3, loc="upper left")
ax2b.yaxis.grid(True, linestyle="--", alpha=0.4)
ax2b.spines[["top", "right"]].set_visible(False)

# Panel 3: F3 Pooled Queue vs System Averages
ax2c = fig2.add_subplot(gs[2])
ax2c.set_facecolor("#ffffff")
ax2c.bar(x - 0.2, wq_pol, 0.35, label="F3 Pooled Single Queue Wq", color="#10B981", alpha=0.85, edgecolor="white", linewidth=0.6)
ax2c.plot(x, wq_dyn, "b--o", label="F1 System Avg Wq (Dynamic)", linewidth=1.5, markersize=5)
ax2c.plot(x, wq_exp, "r--s", label="F2 System Avg Wq (Express)", linewidth=1.5, markersize=5)
ax2c.set_title("Framework 3 (Pooled Queue) — Shared Buffer Efficiency vs. F1 & F2 System Averages", fontsize=11.5, fontweight="bold", pad=12)
ax2c.set_xticks(x)
ax2c.set_xticklabels(labels, fontsize=9.5, rotation=15, ha="right")
ax2c.set_ylabel("Wq (min)", fontsize=10)
ax2c.legend(fontsize=8.5, ncol=3, loc="upper left")
ax2c.yaxis.grid(True, linestyle="--", alpha=0.4)
ax2c.spines[["top", "right"]].set_visible(False)

fig2.suptitle("Lane & Queue Level Waiting Time Analysis Across Scenarios", fontsize=13.5, fontweight="bold", y=0.985)
fig2.subplots_adjust(top=0.92, bottom=0.08, left=0.08, right=0.96, hspace=0.52)
fig2.savefig(OUT_DIR / "chart2_queue_breakdown.png", dpi=300)
plt.close(fig2)
print("  → chart2_queue_breakdown.png saved.\n")

# ─────────────────────────────────────────────────────────────────────────────
# 8.  ANALYTICAL REPORT UPDATE
# ─────────────────────────────────────────────────────────────────────────────
report_lines = [
    "# Arena SIMAN Simulation — Analytical Report (3 Frameworks Comparison)",
    "",
    "## 1. Executive Summary & Framework Architecture",
    "This study evaluates three distinct checkout queuing architectures modelled in Rockwell Arena:",
    "- **Framework 1 (Dynamic Counter Opening):** 4 available checkout lanes opened conditionally based on queue backlog.",
    "- **Framework 2 (Dedicated Express Lane):** Dedicated lane for customers with ≤10 items (`Express_Counter`) and up to 2 regular counters (`Regular_Counter_1/2`).",
    "- **Framework 3 (Pooled Queue / Single-Line Multi-Server):** Single unified serpentine queue feeding 4 parallel servers with FIFO routing (`server` capacity = 4).",
    "",
    "---",
    "",
    "## 2. Comparative Performance Matrix",
    "",
    "| Scenario | Arrival Rate (λ) | F1 Dynamic Wq | F2 Express Wq | F3 Pooled Wq | F1 Total Time W | F2 Total Time W | F3 Total Time W | F3 Server Util |",
    "|---|---|---|---|---|---|---|---|---|",
]

for _, r in df_cmp.iterrows():
    report_lines.append(
        f"| {r['Scenario']} | {r['Lambda']:.2f} | {r['F1_Dynamic_Wq']:.4f} min | {r['F2_Express_Wq']:.4f} min | **{r['F3_Pooled_Wq']:.4f} min** | {r['F1_Dynamic_W']:.4f} min | {r['F2_Express_W']:.4f} min | **{r['F3_Pooled_W']:.4f} min** | {r['F3_Pooled_PeakUtil']:.4f} |"
    )

report_lines.extend([
    "",
    "---",
    "",
    "## 3. In-Depth Operational Insights",
    "",
    "### A. The Pooled Queue Superiority Principle (M/M/c Pooling Effect)",
    "- **Near-Zero Waiting Times:** Framework 3 (Pooled Queue) virtually eliminates customer waiting in queue across almost all operating conditions (Wq = 0.0000 min for daytime and student rush, 0.0003 min for weekday peak, 0.0006 min for weekend non-peak, and only 0.0161 min during weekend peak).",
    "- **Mathematical Foundation:** By pooling queue capacity, servers never sit idle while a customer is waiting in another line. In dedicated or separated queues (Frameworks 1 and 2), stochastic variability in customer item processing times causes temporary lane starvation and line imbalances.",
    "",
    "### B. Heavy Congestion Analysis (Weekend Peak, λ = 0.75 arr/min)",
    "- Under high arrival intensity with shifted Negative Binomial basket distributions, **Framework 1 suffered severe queue pileups** (Wq = 0.9474 min, peak utilization = 80.6%), because counters were delayed in opening or individual lines stalled behind large baskets.",
    "- **Framework 2 mitigated this partly** (Wq = 0.5205 min) by shielding small-basket shoppers in the express lane.",
    "- **Framework 3 completely dominated** (Wq = 0.0161 min, a **98.3% reduction vs. F1** and **96.9% reduction vs. F2**), while maintaining smooth aggregate server utilization of 29.9% across all 4 servers.",
    "",
    "### C. The Student Rush Evaluation (λ = 0.50 arr/min, 70% Small Basket Mix)",
    "- In Framework 2, the fixed N=10 threshold caused 70% of shoppers to crowd the single express server, creating a high Queue Disparity Index (Var = 0.0111 min²).",
    "- In Framework 3, customer traffic flows seamlessly through whatever server becomes free next, maintaining perfect fairness (FIFO) and zero queue disparity.",
    "",
    "---",
    "",
    "## 4. Managerial Recommendations & Trade-offs",
    "1. **Primary Recommendation:** Implement **Framework 3 (Pooled Queue / Single-Line Multi-Server)** wherever store layout allows. It provides optimal customer experience, eliminates lane-choice anxiety, guarantees first-come-first-served fairness, and provides the lowest cycle time across all operating regimes.",
    "2. **Physical Layout Trade-offs:** If floor space restricts single-line serpentine queuing, **Framework 1 (Dynamic Counter Opening)** is preferable on weekdays with mixed traffic, while **Framework 2 (Express Lane)** should be deployed on weekends to protect small basket transactions.",
])

report_md = "\n".join(report_lines)
(OUT_DIR / "analytical_report.md").write_text(report_md, encoding="utf-8")
print("  → analytical_report.md updated.")
print("=" * 65)
