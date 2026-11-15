import json
import re
from pathlib import Path
from scripts.extract_all_metrics import parse_siman_file

def update_dashboard():
    # 1. Weekend Peak metrics
    f1_wp = parse_siman_file(Path("data/dynamic counter/weekendpeak.out.txt"))
    f2_wp = parse_siman_file(Path("data/express lane/weekendpeak.out.txt"))
    p2 = parse_siman_file(Path("data/pooled queue baseline (c=2)/weekendpeak.out.txt"))
    p3 = parse_siman_file(Path("data/pooled queue (c=3)/weekendpeak.out.txt"))
    p4 = parse_siman_file(Path("data/pooled queue (c=4)/weekendpeak.out.txt"))

    lam_wp = 0.75
    mu_wp = 1.0 / p2["Active_Service_Processing_Time_VATime_Ws_Minutes"]

    import math
    def erlang_c(c, rho):
        if rho >= 1.0 or rho <= 0: return 1.0
        a = c * rho
        sum_terms = sum((a**k) / math.factorial(k) for k in range(c))
        last_term = (a**c) / (math.factorial(c) * (1.0 - rho))
        return last_term / (sum_terms + last_term)

    cap_data = [
        {
            "Servers": 2,
            "StaffHours": 15.0,
            "OfferedLoad": round((lam_wp / (2 * mu_wp)) * 100, 1),
            "PWaitPct": round(erlang_c(2, lam_wp / (2 * mu_wp)) * 100, 1),
            "PooledWqTheoMin": round(erlang_c(2, lam_wp / (2 * mu_wp)) / (2 * mu_wp - lam_wp), 4),
            "PooledWqTheoSec": round((erlang_c(2, lam_wp / (2 * mu_wp)) / (2 * mu_wp - lam_wp)) * 60, 1),
            "PooledWqSimMin": round(p2["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "PooledWqSimSec": round(p2["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "PooledUtilSim": round(p2["Peak_Counter_Scheduled_Utilization_Percent"], 1),
            "BaselineFramework": "F1 Dynamic Counter (simulated 2 counters)",
            "BaselineWqMin": round(f1_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "BaselineWqSec": round(f1_wp["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "WaitReductionPct": round(((f1_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"] - p2["Customer_Waiting_Time_in_Queue_Wq_Minutes"]) / f1_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"]) * 100, 1),
            "ComparisonBasis": "Labor Parity with F1 (-42.6% delay, 15.0h)"
        },
        {
            "Servers": 3,
            "StaffHours": 22.5,
            "OfferedLoad": round((lam_wp / (3 * mu_wp)) * 100, 1),
            "PWaitPct": round(erlang_c(3, lam_wp / (3 * mu_wp)) * 100, 1),
            "PooledWqTheoMin": round(erlang_c(3, lam_wp / (3 * mu_wp)) / (3 * mu_wp - lam_wp), 4),
            "PooledWqTheoSec": round((erlang_c(3, lam_wp / (3 * mu_wp)) / (3 * mu_wp - lam_wp)) * 60, 1),
            "PooledWqSimMin": round(p3["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "PooledWqSimSec": round(p3["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "PooledUtilSim": round(p3["Peak_Counter_Scheduled_Utilization_Percent"], 1),
            "BaselineFramework": "F2 Express Lane (simulated 3 counters)",
            "BaselineWqMin": round(f2_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "BaselineWqSec": round(f2_wp["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "WaitReductionPct": round(((f2_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"] - p3["Customer_Waiting_Time_in_Queue_Wq_Minutes"]) / f2_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"]) * 100, 1),
            "ComparisonBasis": "Labor Parity with F2 (-84.2% delay, 22.5h)"
        },
        {
            "Servers": 4,
            "StaffHours": 30.0,
            "OfferedLoad": round((lam_wp / (4 * mu_wp)) * 100, 1),
            "PWaitPct": round(erlang_c(4, lam_wp / (4 * mu_wp)) * 100, 1),
            "PooledWqTheoMin": round(erlang_c(4, lam_wp / (4 * mu_wp)) / (4 * mu_wp - lam_wp), 4),
            "PooledWqTheoSec": round((erlang_c(4, lam_wp / (4 * mu_wp)) / (4 * mu_wp - lam_wp)) * 60, 1),
            "PooledWqSimMin": round(p4["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "PooledWqSimSec": round(p4["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "PooledUtilSim": round(p4["Peak_Counter_Scheduled_Utilization_Percent"], 1),
            "BaselineFramework": "F1 Dynamic Counter (simulated baseline)",
            "BaselineWqMin": round(f1_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "BaselineWqSec": round(f1_wp["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "WaitReductionPct": round(((f1_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"] - p4["Customer_Waiting_Time_in_Queue_Wq_Minutes"]) / f1_wp["Customer_Waiting_Time_in_Queue_Wq_Minutes"]) * 100, 1),
            "ComparisonBasis": "High Capacity Reference (-74.5% delay, 29.9% load)"
        }
    ]

    scenarios = [
        ("weekdaydaytime", "Weekday Daytime", "weekdaydaytime.out.txt", "weekdaynormal.out.txt"),
        ("weekdaystudent", "Weekday Student Rush", "weekdaystudent.out.txt", "weekdaystudent.out.txt"),
        ("weekdaypeak", "Weekday Peak", "weekdaypeak.out.txt", "weekdaypeak.out.txt"),
        ("weekendnormal", "Weekend Non-Peak", "weekendnormal.out.txt", "weekendnormal.out.txt"),
        ("weekendpeak", "Weekend Peak", "weekendpeak.out.txt", "weekendpeak.out.txt")
    ]

    all_sc_comp = []
    for key, label, f_std, f_c2 in scenarios:
        s2 = parse_siman_file(Path(f"data/pooled queue baseline (c=2)/{f_c2}"))
        s3 = parse_siman_file(Path(f"data/pooled queue (c=3)/{f_std}"))
        s4 = parse_siman_file(Path(f"data/pooled queue (c=4)/{f_std}"))
        all_sc_comp.append({
            "scenario": label,
            "c2_wq_m": round(s2["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "c2_wq_s": round(s2["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "c2_util": round(s2["Peak_Counter_Scheduled_Utilization_Percent"], 1),
            "c3_wq_m": round(s3["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "c3_wq_s": round(s3["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "c3_util": round(s3["Peak_Counter_Scheduled_Utilization_Percent"], 1),
            "c4_wq_m": round(s4["Customer_Waiting_Time_in_Queue_Wq_Minutes"], 4),
            "c4_wq_s": round(s4["Customer_Waiting_Time_in_Queue_Wq_Seconds"], 1),
            "c4_util": round(s4["Peak_Counter_Scheduled_Utilization_Percent"], 1),
        })

    html_path = Path("results/simulation_dashboard.html")
    html_text = html_path.read_text(encoding="utf-8")

    # 1. Update payload JSON
    html_text = re.sub(
        r"\"capacity_sensitivity\":\s*\[.*?\](?=,\s*\"curated_accumulators\")",
        f"\"capacity_sensitivity\": {json.dumps(cap_data)}, \"pooled_capacity_scenarios\": {json.dumps(all_sc_comp)}",
        html_text,
        flags=re.DOTALL
    )

    # 2. Update Plotly call in tab-verification
    old_plotly = """Plotly.newPlot('v_chart_capacity', [
            {
              x: ['2 Rostered Servers<br>(Simulated 2-Server Pooled)', '3 Rostered Servers<br>(F2 Express Parity)', '4 Rostered Servers<br>(Original 4-Server Model)'],
              y: [0.5418, 0.5223, 0.0150],
              name: 'Simulated Baseline Wq (min)',
              type: 'bar',
              marker: { color: '#38bdf8' }
            },
            {
              x: ['2 Rostered Servers<br>(Simulated 2-Server Pooled)', '3 Rostered Servers<br>(F2 Express Parity)', '4 Rostered Servers<br>(Original 4-Server Model)'],
              y: [0.8680, 0.1196, 0.0202],
              name: 'Pooled Queue Erlang-C Wq (min)',
              type: 'bar',
              marker: { color: '#34d399' }
            }
          ], {"""

    new_plotly = """Plotly.newPlot('v_chart_capacity', [
            {
              x: ['c = 2 Cashiers<br><b>(Labor Parity with F1)</b><br>15.0 Cashier-Hrs', 'c = 3 Cashiers<br><b>(Labor Parity with F2)</b><br>22.5 Cashier-Hrs', 'c = 4 Cashiers<br><b>(High-Capacity Roster)</b><br>30.0 Cashier-Hrs'],
              y: [0.9441, 0.5223, 0.9441],
              name: 'Baseline Framework Wait Wq (Simulated)',
              type: 'bar',
              marker: { color: '#f43f5e' }
            },
            {
              x: ['c = 2 Cashiers<br><b>(Labor Parity with F1)</b><br>15.0 Cashier-Hrs', 'c = 3 Cashiers<br><b>(Labor Parity with F2)</b><br>22.5 Cashier-Hrs', 'c = 4 Cashiers<br><b>(High-Capacity Roster)</b><br>30.0 Cashier-Hrs'],
              y: [0.5418, 0.0824, 0.2407],
              name: 'Pooled Queue Arena Simulation Wq',
              type: 'bar',
              marker: { color: '#38bdf8' }
            },
            {
              x: ['c = 2 Cashiers<br><b>(Labor Parity with F1)</b><br>15.0 Cashier-Hrs', 'c = 3 Cashiers<br><b>(Labor Parity with F2)</b><br>22.5 Cashier-Hrs', 'c = 4 Cashiers<br><b>(High-Capacity Roster)</b><br>30.0 Cashier-Hrs'],
              y: [0.8683, 0.1211, 0.0203],
              name: 'Pooled Queue Erlang-C M/M/c Wq (Theory)',
              type: 'bar',
              marker: { color: '#34d399' }
            }
          ], {"""

    if old_plotly in html_text:
        html_text = html_text.replace(old_plotly, new_plotly)
        print("Updated v_chart_capacity Plotly chart.")

    # 3. Update Table Header
    old_cap_table_hdr = """            <tr>
              <th>Rostered Servers</th>
              <th>Shift Labor Hours</th>
              <th>Offered Load (&rho;)</th>
              <th>Erlang-C P(Wait)</th>
              <th>Pooled Queue Wq (Theo)</th>
              <th>Simulated Framework Baseline</th>
              <th>Baseline Wait Wq</th>
              <th>Pure Pooling Advantage</th>
              <th>Operational Takeaway</th>
            </tr>"""

    new_cap_table_hdr = """            <tr>
              <th>Rostered Servers (c)</th>
              <th>Shift Labor Hours</th>
              <th>System Load (&rho;)</th>
              <th>Erlang-C P(Wait)</th>
              <th>Theoretical Wq (Erlang-C)</th>
              <th>Simulated Arena Wq (c=2,3,4)</th>
              <th>Simulated Baseline Comparison</th>
              <th>Baseline Wait Wq</th>
              <th>Delay Reduction vs Baseline</th>
              <th>Operational Interpretation</th>
            </tr>"""

    if old_cap_table_hdr in html_text:
        html_text = html_text.replace(old_cap_table_hdr, new_cap_table_hdr)
        print("Updated capacity sensitivity table header.")

    # 4. Update JS for rendering capacity rows
    old_cap_js = """    // Populate Tab 4 Capacity-Equalized Sensitivity Table
    const capTbody = document.getElementById('capacity-tbody');
    payload.capacity_sensitivity.forEach(c => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${c.Servers} Cashiers</strong></td>
        <td>${c.StaffHours.toFixed(1)} hrs</td>
        <td>${c.OfferedLoad.toFixed(1)}%</td>
        <td>${c.PWaitPct.toFixed(1)}%</td>
        <td class="f3-text">${c.PooledWqTheoMin.toFixed(4)} min (${c.PooledWqTheoSec}s)</td>
        <td>${c.BaselineFramework}</td>
        <td>${c.BaselineWqMin.toFixed(4)} min (${c.BaselineWqSec}s)</td>
        <td style="color: #34d399; font-weight: 700;">-${c.WaitReductionPct.toFixed(1)}%</td>
        <td><span class="chip blue" style="font-size: 11px;">${c.ComparisonBasis}</span></td>
      `;
      capTbody.appendChild(tr);
    });"""

    new_cap_js = """    // Populate Tab 4 Capacity-Equalized Sensitivity Table
    const capTbody = document.getElementById('capacity-tbody');
    payload.capacity_sensitivity.forEach(c => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>c = ${c.Servers} Cashiers</strong></td>
        <td>${c.StaffHours.toFixed(1)} hrs</td>
        <td>${c.OfferedLoad.toFixed(1)}%</td>
        <td>${c.PWaitPct.toFixed(1)}%</td>
        <td style="color: #34d399; font-weight: 600;">${c.PooledWqTheoMin.toFixed(4)} min (${c.PooledWqTheoSec}s)</td>
        <td class="f3-text" style="font-weight: 700; font-size: 13.5px;">${c.PooledWqSimMin.toFixed(4)} min (${c.PooledWqSimSec}s)</td>
        <td>${c.BaselineFramework}</td>
        <td>${c.BaselineWqMin.toFixed(4)} min (${c.BaselineWqSec}s)</td>
        <td style="color: #34d399; font-weight: 700; font-size: 13px;">-${c.WaitReductionPct.toFixed(1)}%</td>
        <td><span class="chip blue" style="font-size: 11px;">${c.ComparisonBasis}</span></td>
      `;
      capTbody.appendChild(tr);
    });"""

    if old_cap_js in html_text:
        html_text = html_text.replace(old_cap_js, new_cap_js)
        print("Updated capacity sensitivity row rendering JS.")

    # 5. Add All 5 Scenarios c=2 vs c=3 vs c=4 Table right after
    old_sec_marker = """    <div class="table-card" style="margin-top: 20px;">
      <div class="table-title">
        <span>Erlang-C Verification Across All 5 Scenarios (Simulated vs Analytical)</span>"""

    new_sc_table = """    <div class="table-card" style="margin-top: 20px;">
      <div class="table-title">
        <span>Cross-Regime Capacity Comparison: Simulated Arena Waiting Times Across c = 2, c = 3, and c = 4 Servers</span>
        <span class="chip green">30 Replications Average per Scenario</span>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Operating Scenario</th>
              <th>c = 2 Servers Wq (Simulated)</th>
              <th>c = 2 Server Util (%)</th>
              <th>c = 3 Servers Wq (Simulated)</th>
              <th>c = 3 Server Util (%)</th>
              <th>c = 4 Servers Wq (Simulated)</th>
              <th>c = 4 Server Util (%)</th>
              <th>Optimal Staffing Recommendation</th>
            </tr>
          </thead>
          <tbody id="capacity-all-sc-tbody">
            <!-- Populated via JS -->
          </tbody>
        </table>
      </div>
    </div>

    <div class="table-card" style="margin-top: 20px;">
      <div class="table-title">
        <span>Erlang-C Verification Across All 5 Scenarios (Simulated vs Analytical)</span>"""

    if old_sec_marker in html_text and "capacity-all-sc-tbody" not in html_text:
        html_text = html_text.replace(old_sec_marker, new_sc_table)
        print("Added cross-regime c=2, 3, 4 table.")

    # 6. Add JS population for capacity-all-sc-tbody
    old_erlang_render = "    const erlangTbody = document.getElementById('erlang-tbody');"
    new_erlang_render = """    // Populate Tab 4 All Scenarios Capacity Comparison
    const capAllTbody = document.getElementById('capacity-all-sc-tbody');
    payload.pooled_capacity_scenarios.forEach(row => {
      let recChip = '<span class="chip green">c=2 Sufficient</span>';
      if (row.scenario.includes('Weekend Peak')) {
        recChip = '<span class="chip amber">c=3 Recommended (4.9s)</span>';
      } else if (row.scenario.includes('Weekday Peak') || row.scenario.includes('Weekend Non-Peak')) {
        recChip = '<span class="chip green">c=2 Optimal</span>';
      }
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${row.scenario}</strong></td>
        <td class="f3-text" style="font-weight: 600;">${row.c2_wq_m.toFixed(4)} min (${row.c2_wq_s}s)</td>
        <td>${row.c2_util.toFixed(1)}%</td>
        <td style="color: #38bdf8; font-weight: 600;">${row.c3_wq_m.toFixed(4)} min (${row.c3_wq_s}s)</td>
        <td>${row.c3_util.toFixed(1)}%</td>
        <td style="color: #a78bfa; font-weight: 600;">${row.c4_wq_m.toFixed(4)} min (${row.c4_wq_s}s)</td>
        <td>${row.c4_util.toFixed(1)}%</td>
        <td>${recChip}</td>
      `;
      capAllTbody.appendChild(tr);
    });

    const erlangTbody = document.getElementById('erlang-tbody');"""

    if old_erlang_render in html_text and "capAllTbody" not in html_text:
        html_text = html_text.replace(old_erlang_render, new_erlang_render)
        print("Added JS rendering for cross-regime c=2, 3, 4 table.")

    # 7. Update Callout box in Tab 4
    old_callout = """    <div class="callout-box">
      <h3>Mathematical Verification: Erlang-C Analysis Under Labor Parity (c = 2 Servers)</h3>
      <p>The modified Pooled Queue simulation operates with <strong>c = 2 permanently scheduled servers</strong> across all 5 operating scenarios, achieving identical cashier staffing hours to Framework 1 (Dynamic Counter). <strong>Here is the mathematical analysis:</strong></p>
      <ul>
        <li><strong>1. Exact Empirical and Theoretical Queuing Alignment:</strong> In an M/M/2 queuing model with arrival intensity &lambda; = 0.75 cust/min and service rate &mu; = 0.630 cust/min, the offered workload is a = 1.19 servers. With 2 cashiers open, the multi-server load is &rho; = 59.5%. Erlang-C predicts an average wait time of Wq = 0.868 min (52.1 seconds). The simulated Arena Pooled Queue achieves Wq = 0.542 min (32.5 seconds), outperforming theoretical M/M/2 because Arena basket items have lower coefficient of variation than a pure Poisson/Exponential memoryless process!</li>
        <li><strong>2. Outperforming Dynamic Counter Under Identical Staffing:</strong> Dynamic Counter running 2 counters yields Wq = 0.944 min (56.6 seconds), whereas Pooled Queue with 2 counters achieves Wq = 0.542 min (32.5 seconds)&mdash;a <strong>42.6% delay reduction (24.1 seconds saved per customer)</strong> purely from pooling efficiency (eliminating lane starvation and slow-lane entrapment)!</li>
        <li><strong>3. Labor Parity Sensitivity Matrix:</strong> Below is the comparative sensitivity matrix benchmarking the 2-server model against 3-server and 4-server configurations:</li>
      </ul>
    </div>"""

    new_callout = """    <div class="callout-box">
      <h3>Mathematical Verification & Capacity Sensitivity: Comparing c = 2, c = 3, and c = 4 Pooled Servers</h3>
      <p>Using the newly completed <strong>30-replication datasets for c = 2, c = 3, and c = 4 Pooled Queues</strong> alongside the Erlang-C ($M/M/c$) analytical formulation, we benchmark performance under identical and flexed cashier rosters:</p>
      <ul>
        <li><strong>1. Baseline Labor Parity (c = 2 Cashiers, 15.0 Shift Hours):</strong> Directly matches Framework 1 (Dynamic Counter). Slashes average wait time from 56.6s down to <strong>32.5s (&minus;42.6% delay reduction)</strong> during Weekend Peak with zero extra labor cost, balancing both cashiers at 59.7% scheduled utilization.</li>
        <li><strong>2. Fair Labor Parity with Express Lane (c = 3 Cashiers, 22.5 Shift Hours):</strong> Directly matches Framework 2 (Express Lane) staffing. Pooling those 3 cashiers drops Weekend Peak queue wait to just <strong>4.9 seconds (0.0824 min)</strong>&mdash;an <strong>84.2% delay reduction</strong> compared to Express Lane (31.3s) under the exact same payroll budget!</li>
        <li><strong>3. High-Capacity Model (c = 4 Cashiers, 30.0 Shift Hours):</strong> Delivers rapid service across all traffic levels with low server utilization (~29.9% at peak), but represents 25% to 50% higher payroll cost. The sweet spot for supermarkets is staffing <strong>c = 2 baseline cashiers</strong> and flexing to <strong>c = 3 cashiers only during extreme weekend rush hours</strong>.</li>
      </ul>
    </div>"""

    if old_callout in html_text:
        html_text = html_text.replace(old_callout, new_callout)
        print("Updated callout text.")

    html_path.write_text(html_text, encoding="utf-8")
    print("Dashboard HTML successfully updated and saved!")

if __name__ == "__main__":
    update_dashboard()

