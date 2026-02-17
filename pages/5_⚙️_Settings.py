"""
Settings page — trading parameters, goals, persistence, reset.
"""

import streamlit as st
import json

from lib.state import init_session_state, reset_session_state
from lib.styles import MAIN_CSS
from lib.persistence import (
    save_state, load_state, create_backup, list_backups,
    export_state_string, import_state_string,
)

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
init_session_state()

st.title("⚙️ Settings")

# ── Trading parameters ────────────────────────────────────────
st.subheader("💰 Trading Parameters")

tc1, tc2, tc3 = st.columns(3)
with tc1:
    new_comm = st.number_input(
        "Commission (%)", min_value=0.0, max_value=5.0,
        value=st.session_state.commission_rate * 100, step=0.01,
    )
    st.session_state.commission_rate = new_comm / 100

with tc2:
    new_slip = st.number_input(
        "Slippage (%)", min_value=0.0, max_value=2.0,
        value=st.session_state.slippage_pct * 100, step=0.01,
    )
    st.session_state.slippage_pct = new_slip / 100

with tc3:
    new_spread = st.number_input(
        "Spread (%)", min_value=0.0, max_value=2.0,
        value=st.session_state.spread_pct * 100, step=0.01,
    )
    st.session_state.spread_pct = new_spread / 100

st.caption("Commission, slippage, and spread are applied to every trade for realistic simulation.")

# ── Capital ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏦 Capital")

cap1, cap2 = st.columns(2)
with cap1:
    new_capital = st.number_input(
        "Initial Capital ($)", min_value=1000,
        value=int(st.session_state.initial_balance), step=1000,
    )
    if new_capital != st.session_state.initial_balance and not st.session_state.portfolio:
        st.session_state.initial_balance = float(new_capital)
        st.session_state.balance = float(new_capital)
        st.success("Capital updated!")
    elif new_capital != st.session_state.initial_balance and st.session_state.portfolio:
        st.warning("Close all positions before changing capital.")
with cap2:
    st.metric("Current Cash", f"${st.session_state.balance:,.2f}")
    st.metric("Initial Capital", f"${st.session_state.initial_balance:,.2f}")

# ── Goals ─────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🎯 Trading Goals & Discipline")

goals = st.session_state.get("goals", {})
g1, g2, g3, g4 = st.columns(4)
with g1:
    goals["daily_max_trades"] = st.number_input(
        "Max trades / day", min_value=1, value=goals.get("daily_max_trades", 20),
    )
with g2:
    goals["daily_max_loss"] = st.number_input(
        "Max daily loss ($)", min_value=100.0, value=goals.get("daily_max_loss", 5000.0),
        step=500.0,
    )
with g3:
    goals["monthly_target_pnl"] = st.number_input(
        "Monthly P&L target ($)", min_value=0.0, value=goals.get("monthly_target_pnl", 10000.0),
        step=1000.0,
    )
with g4:
    goals["max_drawdown_pct"] = st.number_input(
        "Max drawdown (%)", min_value=1.0, value=goals.get("max_drawdown_pct", 15.0),
        step=1.0,
    )
st.session_state.goals = goals

# ── Persistence ───────────────────────────────────────────────
st.markdown("---")
st.subheader("💾 Save & Load")

sc1, sc2, sc3 = st.columns(3)
with sc1:
    if st.button("💾 Save Session", use_container_width=True):
        path = save_state()
        st.success(f"Saved to {path}")

with sc2:
    if st.button("📂 Load Session", use_container_width=True):
        if load_state():
            st.success("Session loaded!")
            st.rerun()
        else:
            st.warning("No saved session found.")

with sc3:
    if st.button("📦 Create Backup", use_container_width=True):
        path = create_backup()
        st.success(f"Backup: {path}")

# Backups list
backups = list_backups()
if backups:
    st.markdown("**Available backups:**")
    for b in backups[:5]:
        bc1, bc2 = st.columns([4, 1])
        with bc1:
            st.caption(b)
        with bc2:
            if st.button("Load", key=f"load_{b}"):
                load_state(b)
                st.success("Loaded!")
                st.rerun()

# Export / Import
st.markdown("---")
st.subheader("📤 Export / Import")

exp1, exp2 = st.columns(2)
with exp1:
    st.download_button(
        "📥 Export State (JSON)",
        export_state_string(),
        file_name="trading_lab_state.json",
        mime="application/json",
    )
with exp2:
    uploaded = st.file_uploader("📤 Import State (JSON)", type=["json"])
    if uploaded:
        content = uploaded.read().decode("utf-8")
        if st.button("Import"):
            if import_state_string(content):
                st.success("State imported!")
                st.rerun()
            else:
                st.error("Invalid file format.")

# ── Reset ─────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🗑️ Reset")
st.warning("This will erase ALL data: trades, portfolio, equity curve, settings.")
if st.button("🗑️ Full Reset", type="primary"):
    reset_session_state()
    st.success("Lab reset to defaults!")
    st.rerun()
