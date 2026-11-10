"""
Supermarket Checkout Queuing Simulation Streamlit Application
=============================================================
Directly wraps and hosts the interactive simulation_dashboard.html,
while providing quick access to raw CSV downloads, project documentation,
and live metrics.
"""

import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Supermarket Queuing Simulation Executive Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom minimal CSS for Streamlit container
st.markdown("""
<style>
    /* Remove default Streamlit top padding to let dashboard fill screen */
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    /* Style sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0d1321;
        border-right: 1px solid #1f2937;
    }
    .stDownloadButton button {
        width: 100%;
        background-color: #1e293b;
        color: #38bdf8;
        border: 1px solid #334155;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    .stDownloadButton button:hover {
        background-color: #273549;
        border-color: #38bdf8;
        color: #38bdf8;
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent.resolve()

def find_file(fname):
    # Check current directory first
    p1 = BASE_DIR / fname
    if p1.exists():
        return p1
    # Check results/ subfolder
    p2 = BASE_DIR / "results" / fname
    if p2.exists():
        return p2
    return None

html_path = find_file("simulation_dashboard.html")

# Sidebar Controls & File Downloads
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1869px-Python-logo-notext.svg.png",
        width=45
    )
    st.title("Simulation Lab")
    st.caption("Rockwell Arena 16 SIMAN · Multi-Framework Analysis")
    
    st.divider()
    st.markdown("### 📥 Data Downloads")
    
    csv_kpi = find_file("checkout_comparison_results.csv")
    if csv_kpi and csv_kpi.exists():
        st.download_button(
            label="📊 Comparison KPI Matrix (CSV)",
            data=csv_kpi.read_bytes(),
            file_name="checkout_comparison_results.csv",
            mime="text/csv"
        )
        
    csv_acc = find_file("all_statistical_accumulators.csv")
    if csv_acc and csv_acc.exists():
        st.download_button(
            label="📈 All Accumulators (434 Variables)",
            data=csv_acc.read_bytes(),
            file_name="all_statistical_accumulators.csv",
            mime="text/csv"
        )
        
    csv_raw = find_file("raw_simulation_metrics.csv")
    if csv_raw and csv_raw.exists():
        st.download_button(
            label="📑 Raw Simulation Data (14k Rows)",
            data=csv_raw.read_bytes(),
            file_name="raw_simulation_metrics.csv",
            mime="text/csv"
        )
        
    png_dash = find_file("dashboard_overview.png")
    if png_dash and png_dash.exists():
        st.download_button(
            label="🖼️ Overview Infographic (300 DPI)",
            data=png_dash.read_bytes(),
            file_name="dashboard_overview.png",
            mime="image/png"
        )
        
    st.divider()
    st.markdown("""
    **Architectures Evaluated:**
    - **F1:** Dynamic Counter Opening (2 active)
    - **F2:** Dedicated Express Lane (3 servers)
    - **F3:** Pooled Queue (2-Server Labor Parity)
    
    **Simulation Rigor:**
    - 30 Replications / Scenario
    - 450-minute Operating Horizon
    - 95% Confidence Intervals
    """)
    st.caption("Author: saishashankreddypuchala@gmail.com")

# Main Page: Embed the Full Interactive HTML Dashboard
if html_path and html_path.exists():
    html_content = html_path.read_text(encoding="utf-8")
    components.html(html_content, height=1250, scrolling=True)
else:
    st.error("simulation_dashboard.html not found. Please ensure build_dashboard.py has run.")
