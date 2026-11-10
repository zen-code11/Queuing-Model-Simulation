# Queuing Model Simulation — Arena SIMAN Analysis

> **Course:** Simulation Lab · Semester 5  
> **Tool:** Rockwell Arena (SIMAN Engine) · 30 Replications per Scenario  
> **Author:** saishashankreddypuchala@gmail.com

---

## Project Overview

This project simulates and compares three supermarket checkout queueing architectures modelled in Rockwell Arena across five distinct operating scenarios. The objective is to identify which checkout design minimizes customer wait time ($W_q$) and system cycle time ($W$) under varying arrival intensities and basket-size distributions.

| Framework | Architecture | Description |
|-----------|--------------|-------------|
| **F1 — Dynamic Counter Opening** | Multi-Queue Multi-Server (Dynamic) | Up to 4 counters (`Counter_1` to `Counter_4`) activated conditionally on queue backlog with dynamic queue routing. |
| **F2 — Dedicated Express Lane** | Partitioned Queue Multi-Server | Dedicated express lane for baskets with $\le 10$ items (`Express_Counter`) and up to 2 regular counters (`Regular_Counter_1/2`). |
| **F3 — Pooled Queue** | Single-Queue Multi-Server (M/M/4-type) | Single shared serpentine queue feeding 4 parallel identical servers (`server` capacity = 4) under strict First-Come, First-Served (FIFO) discipline. |

---

## Operating Scenarios

| # | Scenario | Arrival Rate (λ) | Basket Distribution & Notes |
|---|----------|-----------------|-----------------------------|
| 1 | Weekday Daytime | 0.15 arr/min | Low traffic baseline |
| 2 | Weekday Student Rush | 0.50 arr/min | 70% small-basket mix (student traffic) |
| 3 | Weekday Peak | 0.65 arr/min | High arrival intensity, standard basket mix |
| 4 | Weekend Non-Peak | 0.35 arr/min | Shifted Negative Binomial baskets (larger, higher variance) |
| 5 | Weekend Peak | 0.75 arr/min | Highest congestion, shifted Negative Binomial baskets |

---

## Repository Structure

```
Queuing-Model-Simulation/
│
├── arena files/
│   ├── Dynamic Counter.doe        # Rockwell Arena model for Framework 1
│   ├── Express Lane.doe           # Rockwell Arena model for Framework 2
│   └── pooled queue.doe           # Rockwell Arena model for Framework 3
│
├── data/
│   ├── dynamic counter/          # Raw Arena SIMAN .out.txt files (5 scenarios)
│   ├── express lane/             # Raw Arena SIMAN .out.txt files (5 scenarios)
│   └── pooled queue/             # Raw Arena SIMAN .out.txt files (5 scenarios)
│
├── results/
│   ├── raw_simulation_metrics.csv          # 9,826 rows — full per-replication metrics
│   ├── checkout_comparison_results.csv     # 5-scenario side-by-side comparative table
│   ├── chart1_waiting_time_comparison.png  # Grouped bar chart with 95% CI error bars
│   ├── chart2_queue_breakdown.png          # Lane-level & queue breakdown across scenarios
│   └── analytical_report.md               # Complete multi-framework technical report
│
├── scripts/
│   └── analyse_simulation.py              # End-to-end Python parser & analysis pipeline
│
└── README.md
```

---

## KPI Comparison Table (All 3 Frameworks)

All metrics are aggregated across 29 usable replications (each replication: 480 minutes total, 30 minutes warm-up period).

| Scenario | λ (arr/min) | F1 Dynamic $W_q$ | F2 Express $W_q$ | F3 Pooled $W_q$ | F1 Cycle $W$ | F2 Cycle $W$ | F3 Cycle $W$ | F3 Server Util |
|---|---|---|---|---|---|---|---|---|
| Weekday Daytime | 0.15 | 0.0653 min | 0.0530 min | **0.0000 min** | 0.9866 min | 0.9742 min | **0.9214 min** | 3.39% |
| Weekday Student Rush | 0.50 | 0.1631 min | 0.2064 min | **0.0000 min** | 0.9714 min | 0.9608 min | **0.8072 min** | 10.14% |
| Weekday Peak | 0.65 | 0.2475 min | 0.3284 min | **0.0003 min** | 1.1657 min | 1.2462 min | **0.9181 min** | 14.90% |
| Weekend Non-Peak | 0.35 | 0.3885 min | 0.2367 min | **0.0006 min** | 1.9720 min | 1.8197 min | **1.5842 min** | 13.98% |
| Weekend Peak | 0.75 | 0.9474 min | 0.5205 min | **0.0161 min** | 2.5316 min | 2.1056 min | **1.5988 min** | 29.85% |

---

## Visualisations

### Chart 1 — Customer Queue Waiting Time ($W_q$) Across All 3 Frameworks (with 95% CI)
![Chart 1](results/chart1_waiting_time_comparison.png)

### Chart 2 — Detailed Lane & Queue Breakdown Across Scenarios
![Chart 2](results/chart2_queue_breakdown.png)

---

## Key Findings & Comparative Insights

### 1. The Queue Pooling Principle (F3 Pooled Queue Dominance)
- **Near-Zero Waiting Across Scenarios:** Framework 3 (Pooled Queue) virtually eradicates queue wait time across all regimes ($W_q < 0.001$ min in 4 of 5 scenarios, and just $0.0161$ min during Weekend Peak).
- **Elimination of Server Idleness:** In multi-queue setups (F1 and F2), stochastic service time variations cause some servers to sit idle while customers remain trapped in adjacent lines. A pooled line ensures a free server immediately seizes the next customer in line.

### 2. High Congestion Stress Test (Weekend Peak, $\lambda = 0.75$ arr/min)
- **F1 (Dynamic Counter):** Degraded substantially ($W_q = 0.9474$ min, peak utilization $80.6\%$) as Negative Binomial basket distributions caused lines to back up before counters could open.
- **F2 (Express Lane):** Reduced wait to $0.5205$ min by partitioning small baskets from large ones.
- **F3 (Pooled Queue):** Achieved **$0.0161$ min**—a **98.3% wait reduction vs. F1** and **96.9% reduction vs. F2**, while operating smoothly at $29.85\%$ server utilization.

### 3. Student Rush Bottleneck ($\lambda = 0.50$ arr/min, 70% Small Basket Mix)
- In F2, the fixed threshold ($N = 10$) forced 70% of arrivals to a single express counter, causing severe line imbalance (Queue Disparity Index $= 0.0111\text{ min}^2$).
- F3 handled the student rush with zero bottleneck ($W_q = 0.0000$ min) and zero disparity, preserving perfect FIFO fairness.

---

## Managerial Recommendations

1. **Top Recommendation — Framework 3 (Pooled Queue):**
   - Implements a single-line serpentine queue feeding all counters.
   - Eliminates line jockeying, avoids customer frustration, guarantees FIFO fairness, and provides the shortest customer cycle time ($W$).
2. **If Floor Space Restricts a Single Queue:**
   - **Weekdays:** Deploy **Framework 1 (Dynamic Counter Opening)** with automated counter opening triggers based on queue length $> 4$.
   - **Weekends:** Switch to **Framework 2 (Dedicated Express Lane)** to protect small-basket shoppers from long Negative Binomial transaction times.

---

## Reproducing the Analysis

**Requirements:** Python 3.9+, `pandas`, `numpy`, `matplotlib`, `scipy`

```bash
pip install pandas numpy matplotlib scipy
python scripts/analyse_simulation.py
```

The script automatically:
1. Ingests all 15 raw Arena SIMAN `.out.txt` files across the three frameworks.
2. Extracts replication tallies, discrete-change variables, and output statistics.
3. Computes 95% Student's $t$ confidence intervals across replications.
4. Generates publication-ready 300 DPI visualizations (`chart1_waiting_time_comparison.png` and `chart2_queue_breakdown.png`).
5. Updates `raw_simulation_metrics.csv`, `checkout_comparison_results.csv`, and `analytical_report.md`.

---

## Simulation Setup & Parameters

| Parameter | Specification |
|-----------|---------------|
| Total Run Horizon | 480.0 minutes |
| Warm-Up Period | 30.0 minutes |
| Effective Observation Horizon | 450.0 minutes |
| Replications | 30 per scenario (29 usable statistical blocks) |
| Simulation Engine | Rockwell Arena 16 SIMAN |
| Run Date | November 2026 |
