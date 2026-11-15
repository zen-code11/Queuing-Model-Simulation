"""
Extract and Display Core Statistical Accumulators across All 25 Simulation Files.
Calculates 30-replication averages for key queuing metrics with full, descriptive naming:
- Customer Waiting Time in Queue (Wq) [Minutes & Seconds]
- Total Flow Time in System (Cycle Time W) [Minutes & Seconds]
- Active Service Processing Time (VATime / Ws) [Minutes]
- Average Queue Backlog (Lq) [Number of Customers Waiting in Line]
- Work-in-Process (WIP / L) [Total Concurrent Customers in Front-End]
- Peak Server Utilization (%) [Busiest Checkout Counter]
- Average Server Utilization (%) [Across All Active Counters]
- Completed Customer Departures (Throughput per Shift)
"""

import os
import re
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd


def parse_siman_file(file_path):
    """
    Parses a SIMAN .out.txt file and extracts raw replication data
    for all 30 replications.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # Split into individual replication blocks
    rep_blocks = re.split(r"Summary for Replication \d+ of \d+", text)[1:]
    if not rep_blocks:
        return {}

    var_vals = defaultdict(list)
    val_pattern = re.compile(r"^\s*([A-Za-z0-9_ \.]+?)\s{2,}(-?\.?\d+(?:\.\d+)?)")
    ignore = {"Identifier", "Project", "Analyst", "Replication", "Statistics", "Base"}

    for block in rep_blocks:
        for line in block.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("_"):
                continue
            m = val_pattern.match(line)
            if m:
                ident, val_str = m.group(1).strip(), m.group(2)
                if ident not in ignore:
                    try:
                        var_vals[ident].append(float(val_str))
                    except ValueError:
                        pass

    # Core Metrics Extraction
    waiting_time_in_queue_min = np.mean(var_vals.get("Customer.WaitTime", [0.0]))
    waiting_time_in_system_min = np.mean(var_vals.get("Customer.TotalTime", [0.0]))
    service_processing_time_min = np.mean(var_vals.get("Customer.VATime", [0.0]))
    work_in_process_total_customers = np.mean(var_vals.get("Customer.WIP", [0.0]))
    total_customers_completed = np.mean(var_vals.get("Customer.NumberOut", [0.0]))

    # Queue Length Lq (sum of queue backlogs across lanes)
    lq_keys = [k for k in var_vals if "NumberInQueue" in k]
    queue_backlog_customers = sum(np.mean(var_vals[k]) for k in lq_keys) if lq_keys else 0.0

    # Scheduled Server Utilizations
    sched_util_keys = [k for k in var_vals if "ScheduledUtilization" in k]
    if sched_util_keys:
        peak_server_utilization_pct = max(np.mean(var_vals[k]) for k in sched_util_keys) * 100.0
        average_server_utilization_pct = np.mean([np.mean(var_vals[k]) for k in sched_util_keys]) * 100.0
    else:
        peak_server_utilization_pct, average_server_utilization_pct = 0.0, 0.0

    # Return fully detailed variable dictionary
    return {
        "Customer_Waiting_Time_in_Queue_Wq_Minutes": waiting_time_in_queue_min,
        "Customer_Waiting_Time_in_Queue_Wq_Seconds": waiting_time_in_queue_min * 60.0,
        "Total_Customer_Time_in_System_Cycle_W_Minutes": waiting_time_in_system_min,
        "Total_Customer_Time_in_System_Cycle_W_Seconds": waiting_time_in_system_min * 60.0,
        "Active_Service_Processing_Time_VATime_Ws_Minutes": service_processing_time_min,
        "Average_Queue_Backlog_Lq_Waiting_Customers": queue_backlog_customers,
        "Work_In_Process_WIP_Total_Customers": work_in_process_total_customers,
        "Peak_Counter_Scheduled_Utilization_Percent": peak_server_utilization_pct,
        "Average_Counter_Scheduled_Utilization_Percent": average_server_utilization_pct,
        "Total_Completed_Customer_Throughput_Departures": total_customers_completed,
    }


def main():
    base_dir = Path("data")
    if not base_dir.exists():
        base_dir = Path(".")

    all_files = sorted(list(base_dir.glob("*/*.out.txt")))
    if not all_files:
        print("No .out.txt simulation files found!")
        return

    print("=" * 135)
    print(f" SIMULATION REPLICATION ACCUMULATOR SUMMARY ({len(all_files)} OUTPUT FILES, 30 REPLICATIONS EACH)")
    print("=" * 135)

    records = []
    for fp in all_files:
        framework = fp.parent.name
        scenario = fp.stem.replace(".out", "")

        # Clean human-readable scenario name
        scenario_clean = (
            scenario.replace("normal", " Normal")
            .replace("peak", " Peak")
            .replace("daytime", " Daytime")
            .replace("student", " Student Rush")
        )
        scenario_clean = " ".join([w.capitalize() for w in scenario_clean.split()])

        stats = parse_siman_file(fp)
        if not stats:
            continue

        record = {
            "Framework_Architecture": framework,
            "Operating_Scenario": scenario_clean,
        }
        record.update(stats)
        records.append(record)

    df = pd.DataFrame(records)

    # Display grouped by Framework in terminal with clear headers
    for fw, group in df.groupby("Framework_Architecture", sort=False):
        print(f"\n[{fw.upper()}]")
        print("-" * 135)
        print(
            f"{'Operating Scenario':<22} | "
            f"{'Wait Queue (min)':>16} | "
            f"{'Wait Queue (sec)':>16} | "
            f"{'Total Cycle W (m)':>17} | "
            f"{'Backlog Lq (cust)':>17} | "
            f"{'WIP Total (cust)':>16} | "
            f"{'Peak Util (%)':>13} | "
            f"{'Completed':>10}"
        )
        print("-" * 135)
        for _, r in group.iterrows():
            print(
                f"{r['Operating_Scenario']:<22} | "
                f"{r['Customer_Waiting_Time_in_Queue_Wq_Minutes']:>16.4f} | "
                f"{r['Customer_Waiting_Time_in_Queue_Wq_Seconds']:>15.1f}s | "
                f"{r['Total_Customer_Time_in_System_Cycle_W_Minutes']:>17.4f} | "
                f"{r['Average_Queue_Backlog_Lq_Waiting_Customers']:>17.4f} | "
                f"{r['Work_In_Process_WIP_Total_Customers']:>16.2f} | "
                f"{r['Peak_Counter_Scheduled_Utilization_Percent']:>12.1f}% | "
                f"{r['Total_Completed_Customer_Throughput_Departures']:>10.1f}"
            )

    print("\n" + "=" * 135)
    print(" Detailed Variable Dictionary:")
    print("  1. Customer_Waiting_Time_in_Queue_Wq_Minutes        : Average time spent waiting in line (Wq)")
    print("  2. Customer_Waiting_Time_in_Queue_Wq_Seconds        : Average time spent waiting in line (in seconds)")
    print("  3. Total_Customer_Time_in_System_Cycle_W_Minutes    : Total flow time from arrival to departure (W = Wq + Ws)")
    print("  4. Total_Customer_Time_in_System_Cycle_W_Seconds    : Total flow time from arrival to departure (in seconds)")
    print("  5. Active_Service_Processing_Time_VATime_Ws_Minutes : Active checkout barcode scanning and payment time")
    print("  6. Average_Queue_Backlog_Lq_Waiting_Customers       : Mean line backlog (number of customers standing in queue)")
    print("  7. Work_In_Process_WIP_Total_Customers              : Total concurrent customers in checkout area (in queue + being served)")
    print("  8. Peak_Counter_Scheduled_Utilization_Percent       : Scheduled utilization percentage of the most utilized cashier")
    print("  9. Average_Counter_Scheduled_Utilization_Percent    : Average scheduled utilization percentage across all rostered cashiers")
    print(" 10. Total_Completed_Customer_Throughput_Departures   : Average customer departures processed per shift")
    print("=" * 135 + "\n")

    # Export clean summary table to CSV with fully detailed column names
    output_csv = Path("results") / "all_25_files_core_metrics.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Summary table exported with full variable names to: {output_csv.resolve()}\n")


if __name__ == "__main__":
    main()
