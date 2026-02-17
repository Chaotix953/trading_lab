"""
Custom CSS styles for Trading Lab Pro.
"""

MAIN_CSS = """
<style>
    /* ── Global ─────────────────────────────────────────── */
    .block-container { padding-top: 1rem; }
    div[data-testid="stTabs"] button { font-size: 15px; font-weight: 600; }

    /* ── Metrics ────────────────────────────────────────── */
    div[data-testid="stMetric"] {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 12px 16px;
        background: rgba(255,255,255,0.02);
    }

    /* ── Profit / Loss coloring ─────────────────────────── */
    .profit { color: #00c853 !important; }
    .loss   { color: #ff1744 !important; }

    /* ── Sidebar ────────────────────────────────────────── */
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }

    /* ── DataFrames ─────────────────────────────────────── */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* ── Buttons ────────────────────────────────────────── */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }

    /* ── Expander ───────────────────────────────────────── */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 15px;
    }

    /* ── Alert banner ───────────────────────────────────── */
    .alert-banner {
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
        font-weight: 500;
    }
    .alert-warning { background: rgba(255,152,0,0.15); border-left: 4px solid #ff9800; }
    .alert-danger  { background: rgba(244,67,54,0.15);  border-left: 4px solid #f44336; }
    .alert-success { background: rgba(76,175,80,0.15);  border-left: 4px solid #4caf50; }

    /* ── Stat cards ─────────────────────────────────────── */
    .stat-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .stat-value { font-size: 24px; font-weight: 700; }
    .stat-label { font-size: 13px; color: rgba(255,255,255,0.6); margin-top: 4px; }
</style>
"""
