"""
Backtester page — test strategies on historical data.
"""

import streamlit as st
import pandas as pd

from lib.state import init_session_state
from lib.styles import MAIN_CSS
from lib.config import PERIOD_MAP
from lib.data_fetcher import fetch_history
from lib.backtester import STRATEGIES, run_backtest
from lib.charts import backtest_chart

st.set_page_config(page_title="Backtester", page_icon="🔄", layout="wide")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
init_session_state()

st.title("🔄 Strategy Backtester")

# ── Config ────────────────────────────────────────────────────
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    bt_ticker = st.text_input("Symbol", "AAPL", key="bt_ticker").upper().strip()
with c2:
    bt_period = st.selectbox("Period", ["6M", "1Y", "2Y", "5Y"], index=1, key="bt_period")
with c3:
    bt_strategy = st.selectbox("Strategy", list(STRATEGIES.keys()), key="bt_strat")

strat_info = STRATEGIES[bt_strategy]
st.caption(f"📖 {strat_info['description']}")

# Strategy parameters
st.markdown("---")
st.subheader("⚙️ Parameters")

pc1, pc2, pc3 = st.columns(3)
strategy_params = {}

with pc1:
    if "fast" in strat_info["params"]:
        strategy_params["fast"] = st.number_input("Fast Period",
            value=strat_info["params"]["fast"], min_value=2, max_value=100)
    if "period" in strat_info["params"]:
        strategy_params["period"] = st.number_input("Period",
            value=strat_info["params"]["period"], min_value=2, max_value=100)
    if "oversold" in strat_info["params"]:
        strategy_params["oversold"] = st.number_input("Oversold",
            value=strat_info["params"]["oversold"], min_value=5, max_value=50)

with pc2:
    if "slow" in strat_info["params"]:
        strategy_params["slow"] = st.number_input("Slow Period",
            value=strat_info["params"]["slow"], min_value=5, max_value=300)
    if "overbought" in strat_info["params"]:
        strategy_params["overbought"] = st.number_input("Overbought",
            value=strat_info["params"]["overbought"], min_value=50, max_value=95)
    if "std" in strat_info["params"]:
        strategy_params["std"] = st.number_input("Std Dev",
            value=strat_info["params"]["std"], min_value=0.5, max_value=4.0, step=0.5)

with pc3:
    bt_capital = st.number_input("Initial Capital $", value=100000, min_value=1000, step=1000)
    bt_commission = st.number_input("Commission %", value=0.1, min_value=0.0, max_value=2.0, step=0.01) / 100
    bt_position_size = st.slider("Position Size %", 10, 100, 100, 10)

# Advanced options
with st.expander("Advanced: Stop-Loss / Take-Profit"):
    adv1, adv2 = st.columns(2)
    with adv1:
        use_sl = st.checkbox("Use Stop-Loss")
        sl_pct = st.number_input("SL %", value=5.0, min_value=0.5, max_value=50.0, step=0.5) if use_sl else None
    with adv2:
        use_tp = st.checkbox("Use Take-Profit")
        tp_pct = st.number_input("TP %", value=10.0, min_value=0.5, max_value=100.0, step=0.5) if use_tp else None

# ── Run ───────────────────────────────────────────────────────
st.markdown("---")

if st.button("🚀 Run Backtest", type="primary", use_container_width=True):
    try:
        with st.spinner("Running backtest..."):
            period_val = PERIOD_MAP[bt_period]
            df = fetch_history(bt_ticker, period_val, "1d")

            result = run_backtest(
                df=df,
                signal_fn=strat_info["fn"],
                initial_capital=bt_capital,
                commission_rate=bt_commission,
                position_size_pct=bt_position_size,
                stop_loss_pct=sl_pct if use_sl else None,
                take_profit_pct=tp_pct if use_tp else None,
                **strategy_params,
            )

        # ── Results ───────────────────────────────────────
        st.markdown("---")
        st.subheader("📊 Results")

        # Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        delta_color = "normal" if result.total_return_pct >= 0 else "inverse"
        m1.metric("Strategy Return", f"{result.total_return_pct:+.2f}%")
        m2.metric("Buy & Hold", f"{result.buy_hold_return_pct:+.2f}%")
        m3.metric("Total Trades", result.total_trades)
        m4.metric("Win Rate", f"{result.win_rate:.1f}%")
        m5.metric("Sharpe", f"{result.sharpe:.2f}")

        m6, m7, m8, m9, m10 = st.columns(5)
        m6.metric("Total P&L", f"${result.total_pnl:+,.2f}")
        m7.metric("Profit Factor", f"{result.profit_factor:.2f}")
        m8.metric("Max Drawdown", f"{result.max_drawdown:.2f}%")
        m9.metric("Best Trade", f"${result.best_trade:+,.2f}")
        m10.metric("Worst Trade", f"${result.worst_trade:+,.2f}")

        # Alpha
        alpha = result.total_return_pct - result.buy_hold_return_pct
        st.markdown(f"**Alpha vs Buy & Hold: {alpha:+.2f}%**"
                    f" {'✅' if alpha > 0 else '❌'}")

        # Chart
        buy_hold_curve = (df["Close"] / df["Close"].iloc[0] * bt_capital).tolist()
        fig = backtest_chart(
            result.dates, result.equity_curve,
            buy_hold_curve=buy_hold_curve,
            trades=result.trades,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Trade list
        if result.trades:
            st.subheader("📋 Trade Log")
            df_trades = pd.DataFrame(result.trades)
            st.dataframe(df_trades, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Backtest error: {e}")

# ── Strategy comparison ───────────────────────────────────────
st.markdown("---")
st.subheader("🏆 Strategy Comparison")
st.caption("Compare all built-in strategies on the same data")

if st.button("🔄 Run All Strategies", use_container_width=True):
    try:
        period_val = PERIOD_MAP[bt_period]
        df = fetch_history(bt_ticker, period_val, "1d")

        comparison = []
        for name, sinfo in STRATEGIES.items():
            with st.spinner(f"Testing {name}..."):
                r = run_backtest(
                    df=df,
                    signal_fn=sinfo["fn"],
                    initial_capital=bt_capital,
                    commission_rate=bt_commission,
                    **{k: v for k, v in sinfo["params"].items()},
                )
                comparison.append({
                    "Strategy": name,
                    "Return %": f"{r.total_return_pct:+.2f}%",
                    "Win Rate": f"{r.win_rate:.1f}%",
                    "Trades": r.total_trades,
                    "P&L": f"${r.total_pnl:+,.2f}",
                    "Sharpe": f"{r.sharpe:.2f}",
                    "Max DD": f"{r.max_drawdown:.2f}%",
                    "Profit Factor": f"{r.profit_factor:.2f}",
                })

        comparison.append({
            "Strategy": "Buy & Hold",
            "Return %": f"{(df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100:+.2f}%",
            "Win Rate": "—", "Trades": 1, "P&L": "—",
            "Sharpe": "—", "Max DD": "—", "Profit Factor": "—",
        })

        st.dataframe(pd.DataFrame(comparison), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Comparison error: {e}")
