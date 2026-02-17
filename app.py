"""
Trading Lab Pro — Main Dashboard
"""

import streamlit as st

from lib.config import APP_NAME, APP_ICON, APP_VERSION
from lib.state import init_session_state
from lib.styles import MAIN_CSS
from lib.persistence import save_state, load_state
from lib.data_fetcher import get_batch_prices, fetch_history, fetch_info, get_current_price
from lib.trading_engine import get_portfolio_value, get_margin_usage
from lib.performance import compute_performance_stats, current_drawdown, compute_var
from lib.scanner import check_alerts

import pandas as pd
from datetime import datetime

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(MAIN_CSS, unsafe_allow_html=True)

# ── State init ────────────────────────────────────────────────
init_session_state()

# Auto-load saved state on first run
if "loaded" not in st.session_state:
    load_state()
    st.session_state.loaded = True

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.title(f"{APP_ICON} {APP_NAME}")
st.sidebar.caption(f"v{APP_VERSION}")
st.sidebar.markdown("---")

# Quick actions
st.sidebar.header("💾 Session")
col_save, col_load = st.sidebar.columns(2)
with col_save:
    if st.button("💾 Save", use_container_width=True):
        path = save_state()
        st.success(f"Saved!")
with col_load:
    if st.button("📂 Load", use_container_width=True):
        if load_state():
            st.success("Loaded!")
            st.rerun()
        else:
            st.warning("No save found")

st.sidebar.markdown("---")

# Watchlist in sidebar
st.sidebar.header("👁️ Watchlist")
new_ticker = st.sidebar.text_input("Add ticker", key="dash_add_watch")
if st.sidebar.button("➕ Add") and new_ticker:
    t = new_ticker.upper().strip()
    if t and t not in st.session_state.watchlist:
        st.session_state.watchlist.append(t)
        st.rerun()

# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════

st.title("📊 Dashboard")

# ── Top metrics ───────────────────────────────────────────────
# Fetch watchlist prices for portfolio valuation
portfolio_tickers = tuple(
    k.replace("_SHORT", "") for k in st.session_state.portfolio.keys()
)
all_tickers = tuple(set(portfolio_tickers + tuple(st.session_state.watchlist)))

if all_tickers:
    live_prices = get_batch_prices(all_tickers)
else:
    live_prices = {}

total_value = get_portfolio_value(live_prices)
delta = total_value - st.session_state.initial_balance
delta_pct = (delta / st.session_state.initial_balance) * 100 if st.session_state.initial_balance > 0 else 0
dd = current_drawdown()
margin = get_margin_usage()

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("💵 Cash", f"${st.session_state.balance:,.2f}")
with c2:
    st.metric("📊 Total Value", f"${total_value:,.2f}",
              delta=f"{delta:+,.2f} ({delta_pct:+.2f}%)")
with c3:
    st.metric("📈 Positions", len(st.session_state.portfolio))
with c4:
    st.metric("📉 Drawdown", f"{dd:.2f}%")
with c5:
    st.metric("⚠️ Margin Used", f"{margin['margin_pct']:.1f}%")
with c6:
    st.metric("📋 Pending Orders", len(st.session_state.pending_orders))

# ── Check alerts ──────────────────────────────────────────────
for ticker, price in live_prices.items():
    if price:
        alerts = check_alerts(ticker, price)
        for a in alerts:
            st.toast(a)

# ── Goal tracking ─────────────────────────────────────────────
goals = st.session_state.get("goals", {})
today = datetime.now().strftime("%Y-%m-%d")
today_trades = [t for t in st.session_state.history if t["date"].startswith(today)]
today_pnls = [t["pnl"] for t in today_trades if t.get("pnl") is not None]
daily_pnl = sum(today_pnls) if today_pnls else 0

with st.expander("🎯 Trading Goals & Discipline", expanded=False):
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        max_t = goals.get("daily_max_trades", 20)
        st.metric("Trades Today", f"{len(today_trades)} / {max_t}",
                  delta="OK" if len(today_trades) < max_t else "LIMIT!")
    with g2:
        st.metric("Daily P&L", f"${daily_pnl:+,.2f}")
    with g3:
        max_dd = goals.get("max_drawdown_pct", 15)
        color = "normal" if dd < max_dd else "inverse"
        st.metric("Max DD Target", f"{dd:.1f}% / {max_dd}%")
    with g4:
        target = goals.get("monthly_target_pnl", 10000)
        stats = compute_performance_stats()
        st.metric("Monthly Target", f"${stats['total_pnl']:+,.0f} / ${target:,.0f}")

# ── Watchlist ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("👁️ Watchlist")

if st.session_state.watchlist:
    num_cols = min(len(st.session_state.watchlist), 6)
    rows_needed = (len(st.session_state.watchlist) + num_cols - 1) // num_cols

    for row_idx in range(rows_needed):
        cols = st.columns(num_cols)
        for col_idx in range(num_cols):
            i = row_idx * num_cols + col_idx
            if i >= len(st.session_state.watchlist):
                break
            t = st.session_state.watchlist[i]
            with cols[col_idx]:
                p = live_prices.get(t)
                if p:
                    st.metric(t, f"${p:,.2f}")
                else:
                    st.metric(t, "N/A")
                if st.button("❌", key=f"rm_{t}"):
                    st.session_state.watchlist.remove(t)
                    st.rerun()
else:
    st.info("Watchlist empty — add tickers in the sidebar.")

# ── Portfolio summary ─────────────────────────────────────────
st.markdown("---")
st.subheader("💼 Portfolio")

if st.session_state.portfolio:
    pf_rows = []
    for key, pos in st.session_state.portfolio.items():
        clean = key.replace("_SHORT", "")
        price = live_prices.get(clean) or pos["avg_price"]
        if pos["side"] == "short":
            unrealized = (pos["avg_price"] - price) * pos["qty"]
        else:
            unrealized = (price - pos["avg_price"]) * pos["qty"]
        pf_rows.append({
            "Ticker": key,
            "Side": pos["side"].upper(),
            "Qty": pos["qty"],
            "Avg Price": f"${pos['avg_price']:.2f}",
            "Current": f"${price:.2f}",
            "Value": f"${pos['qty'] * price:,.2f}",
            "Unrealized P&L": f"${unrealized:+,.2f}",
            "P&L %": f"{(unrealized / (pos['avg_price'] * pos['qty'])) * 100:+.2f}%",
        })
    st.dataframe(pd.DataFrame(pf_rows), use_container_width=True, hide_index=True)
else:
    st.info("No open positions. Head to the **Trading** page to get started!")

# ── Quick stats ───────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 Quick Stats")

stats = compute_performance_stats()
if stats["total_trades"] > 0:
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("Total Trades", stats["total_trades"])
    s2.metric("Win Rate", f"{stats['win_rate']:.1f}%")
    s3.metric("Total P&L", f"${stats['total_pnl']:+,.2f}")
    s4.metric("Profit Factor", f"{stats['profit_factor']:.2f}")
    s5.metric("Sharpe", f"{stats['sharpe']:.2f}")
    s6.metric("Kelly %", f"{stats['kelly_pct']:.1f}%")
else:
    st.info("No trades yet — statistics will appear after your first closed trade.")

# ── Recent trades ─────────────────────────────────────────────
if st.session_state.history:
    st.markdown("---")
    st.subheader("🕐 Recent Trades")
    recent = st.session_state.history[-10:][::-1]
    df_recent = pd.DataFrame(recent)
    display_cols = ["date", "ticker", "action", "qty", "fill_price", "pnl", "commission"]
    available = [c for c in display_cols if c in df_recent.columns]
    st.dataframe(df_recent[available], use_container_width=True, hide_index=True)
