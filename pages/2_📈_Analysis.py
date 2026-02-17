"""
Analysis page — deep performance analytics, risk metrics, correlation, sectors.
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime

from lib.state import init_session_state
from lib.styles import MAIN_CSS
from lib.performance import (
    compute_performance_stats, current_drawdown, compute_var,
    get_trade_distribution, compute_portfolio_beta,
)
from lib.trading_engine import get_portfolio_value
from lib.data_fetcher import (
    get_batch_prices, fetch_benchmark, fetch_correlation_data, get_sector_info,
)
from lib.charts import (
    equity_curve_chart, pnl_distribution_chart, allocation_pie,
    sector_pie, correlation_heatmap,
)

st.set_page_config(page_title="Analysis", page_icon="📈", layout="wide")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
init_session_state()

st.title("📈 Performance & Analysis")

# ══════════════════════════════════════════════════════════════
#  PERFORMANCE TAB SYSTEM
# ══════════════════════════════════════════════════════════════

tab_perf, tab_risk, tab_journal, tab_alloc, tab_corr = st.tabs([
    "📊 Performance", "⚠️ Risk", "📜 Journal", "🥧 Allocation", "🔗 Correlation",
])

stats = compute_performance_stats()

# ── Performance ───────────────────────────────────────────────
with tab_perf:
    if stats["total_trades"] > 0:
        # Row 1: Core metrics
        p1, p2, p3, p4, p5, p6 = st.columns(6)
        p1.metric("Total Trades", stats["total_trades"])
        p2.metric("Win Rate", f"{stats['win_rate']:.1f}%")
        p3.metric("Total P&L", f"${stats['total_pnl']:+,.2f}")
        p4.metric("Profit Factor", f"{stats['profit_factor']:.2f}")
        p5.metric("Expectancy", f"${stats['expectancy']:+,.2f}")
        p6.metric("Kelly %", f"{stats['kelly_pct']:.1f}%")

        # Row 2: Detailed
        p7, p8, p9, p10, p11, p12 = st.columns(6)
        p7.metric("Avg Win", f"${stats['avg_win']:+,.2f}")
        p8.metric("Avg Loss", f"${stats['avg_loss']:+,.2f}")
        p9.metric("Best Trade", f"${stats['best_trade']:+,.2f}")
        p10.metric("Worst Trade", f"${stats['worst_trade']:+,.2f}")
        p11.metric("Max DD", f"{stats['max_drawdown']:.2f}%")
        p12.metric("Commissions", f"${stats['total_commissions']:,.2f}")

        # Row 3: Ratios
        st.markdown("---")
        r1, r2, r3, r4, r5, r6 = st.columns(6)
        r1.metric("Sharpe Ratio", f"{stats['sharpe']:.2f}")
        r2.metric("Sortino Ratio", f"{stats['sortino']:.2f}")
        r3.metric("Calmar Ratio", f"{stats['calmar']:.2f}")
        r4.metric("Win Streak", stats["consecutive_wins"])
        r5.metric("Loss Streak", stats["consecutive_losses"])
        r6.metric("Total Slippage", f"${stats['total_slippage']:.2f}")

        # Long vs Short performance
        st.markdown("---")
        ls1, ls2 = st.columns(2)
        with ls1:
            st.metric("Long P&L", f"${stats['long_pnl']:+,.2f}")
        with ls2:
            st.metric("Short P&L", f"${stats['short_pnl']:+,.2f}")

        # Equity curve with benchmark
        st.markdown("---")
        st.subheader("Equity Curve")
        show_bench = st.checkbox("Compare with S&P 500 (SPY)", value=False)
        benchmark = None
        if show_bench:
            try:
                benchmark = fetch_benchmark("SPY", "1y")
            except Exception:
                st.warning("Could not fetch benchmark data.")

        if st.session_state.equity_curve:
            fig_eq = equity_curve_chart(
                st.session_state.equity_curve,
                st.session_state.initial_balance,
                benchmark,
            )
            st.plotly_chart(fig_eq, use_container_width=True)

        # P&L distribution
        closed_pnls = [t["pnl"] for t in st.session_state.history
                       if isinstance(t.get("pnl"), (int, float))]
        if closed_pnls:
            st.plotly_chart(pnl_distribution_chart(closed_pnls), use_container_width=True)

        # Distribution stats
        dist = get_trade_distribution()
        st.markdown("**P&L Distribution Stats**")
        d1, d2, d3, d4, d5 = st.columns(5)
        d1.metric("Mean", f"${dist['mean']:+,.2f}")
        d2.metric("Median", f"${dist['median']:+,.2f}")
        d3.metric("Std Dev", f"${dist['std']:,.2f}")
        d4.metric("Skewness", f"{dist['skew']:.2f}")
        d5.metric("Kurtosis", f"{dist['kurtosis']:.2f}")
    else:
        st.info("No trades yet. Start trading to see analytics!")

# ── Risk ──────────────────────────────────────────────────────
with tab_risk:
    st.subheader("⚠️ Risk Metrics")

    dd = current_drawdown()
    var_data = compute_var(0.95)

    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Current Drawdown", f"{dd:.2f}%")
    v2.metric("VaR 95% (Hist)", f"${var_data['historical_var']:,.2f}")
    v3.metric("VaR 95% (Param)", f"${var_data['parametric_var']:,.2f}")
    v4.metric("CVaR (Exp. Shortfall)", f"${var_data['cvar']:,.2f}")

    # Also show 99% VaR
    var99 = compute_var(0.99)
    v5, v6, v7, v8 = st.columns(4)
    v5.metric("VaR 99% (Hist)", f"${var99['historical_var']:,.2f}")
    v6.metric("VaR 99% (Param)", f"${var99['parametric_var']:,.2f}")
    v7.metric("Max Drawdown", f"{stats['max_drawdown']:.2f}%")
    v8.metric("Kelly Optimal %", f"{stats['kelly_pct']:.1f}%")

    # Margin info
    from lib.trading_engine import get_margin_usage
    margin = get_margin_usage()
    if margin["positions"] > 0:
        st.markdown("---")
        st.subheader("📊 Margin")
        m1, m2, m3 = st.columns(3)
        m1.metric("Short Positions", margin["positions"])
        m2.metric("Margin Used", f"${margin['margin_used']:,.2f}")
        m3.metric("Margin %", f"{margin['margin_pct']:.1f}%")

# ── Journal ───────────────────────────────────────────────────
with tab_journal:
    st.subheader("📜 Trade Journal")

    if st.session_state.history:
        df_hist = pd.DataFrame(st.session_state.history)[::-1].reset_index(drop=True)

        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            filter_ticker = st.text_input("Filter by ticker", key="journal_filter")
        with f2:
            filter_action = st.multiselect("Filter by action",
                ["Buy", "Sell", "Short", "Cover"], key="journal_action")
        with f3:
            filter_result = st.selectbox("P&L filter",
                ["All", "Winners only", "Losers only"], key="journal_result")

        # Apply filters
        if filter_ticker:
            df_hist = df_hist[df_hist["ticker"].str.contains(filter_ticker.upper())]
        if filter_action:
            df_hist = df_hist[df_hist["action"].isin(filter_action)]
        if filter_result == "Winners only":
            df_hist = df_hist[df_hist["pnl"].apply(lambda x: isinstance(x, (int, float)) and x > 0)]
        elif filter_result == "Losers only":
            df_hist = df_hist[df_hist["pnl"].apply(lambda x: isinstance(x, (int, float)) and x < 0)]

        st.dataframe(df_hist, use_container_width=True, hide_index=True)

        # Notes for individual trades
        st.markdown("---")
        st.subheader("📝 Trade Notes")
        trade_idx = st.number_input("Trade # (from history)", min_value=0,
            max_value=len(st.session_state.history)-1, value=0, key="note_idx")
        trade = st.session_state.history[trade_idx]
        st.caption(f"{trade['date']} — {trade['action']} {trade['qty']}×{trade['ticker']} @ ${trade['fill_price']:.2f}")
        existing_note = st.session_state.trade_notes.get(str(trade_idx), {})
        note_text = st.text_area("Note", value=existing_note.get("note", ""), key="trade_note")
        note_tags = st.multiselect("Tags", ["Momentum", "Mean Reversion", "Breakout",
            "Scalp", "Swing", "News", "Technical", "Mistake", "Good Setup"],
            default=existing_note.get("tags", []), key="trade_note_tags")
        if st.button("💾 Save Note"):
            st.session_state.trade_notes[str(trade_idx)] = {"note": note_text, "tags": note_tags}
            st.success("Note saved!")

        # Export
        st.markdown("---")
        csv_buf = io.StringIO()
        df_hist.to_csv(csv_buf, index=False)
        st.download_button(
            "📥 Export Journal (CSV)", csv_buf.getvalue(),
            file_name=f"trading_journal_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No trades yet.")

# ── Allocation ────────────────────────────────────────────────
with tab_alloc:
    st.subheader("🥧 Portfolio Allocation")

    if st.session_state.portfolio:
        # Asset allocation
        fig_alloc = allocation_pie(st.session_state.portfolio, st.session_state.balance)
        st.plotly_chart(fig_alloc, use_container_width=True)

        # Sector exposure
        st.markdown("---")
        st.subheader("🏗️ Sector Exposure")
        portfolio_tickers = tuple(
            k.replace("_SHORT", "") for k in st.session_state.portfolio.keys()
        )
        if portfolio_tickers:
            try:
                sectors = get_sector_info(portfolio_tickers)
                sector_values: dict[str, float] = {}
                for key, pos in st.session_state.portfolio.items():
                    clean = key.replace("_SHORT", "")
                    sect = sectors.get(clean, "Other")
                    val = pos["qty"] * pos["avg_price"]
                    sector_values[sect] = sector_values.get(sect, 0) + val

                fig_sect = sector_pie(sector_values)
                st.plotly_chart(fig_sect, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not fetch sector data: {e}")
    else:
        st.info("Portfolio is empty — all cash.")

# ── Correlation ───────────────────────────────────────────────
with tab_corr:
    st.subheader("🔗 Correlation Matrix")

    default_tickers = list(st.session_state.watchlist)[:8]
    corr_input = st.text_input(
        "Tickers (comma-separated)",
        value=", ".join(default_tickers),
        key="corr_tickers",
    )
    corr_tickers = tuple(t.strip().upper() for t in corr_input.split(",") if t.strip())

    if len(corr_tickers) >= 2:
        try:
            corr_matrix = fetch_correlation_data(corr_tickers)
            fig_corr = correlation_heatmap(corr_matrix)
            st.plotly_chart(fig_corr, use_container_width=True)
        except Exception as e:
            st.error(f"Correlation error: {e}")
    else:
        st.info("Enter at least 2 tickers to compute correlation.")
