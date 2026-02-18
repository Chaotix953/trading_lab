"""
Trading page — chart, order entry, and market analysis.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from lib.state import init_session_state
from lib.styles import MAIN_CSS
from lib.config import PERIOD_MAP, INTERVAL_MAP, VALID_COMBOS
from lib.data_fetcher import (
    fetch_history, fetch_info, get_current_price,
    fetch_options_expirations, fetch_options_chain, fetch_news,
)
from lib.trading_engine import execute_trade, simulate_fill_price
from lib.orders import (
    place_order, place_oco_bracket, place_trailing_stop,
    check_pending_orders, cancel_order, get_active_orders,
)
from lib.scanner import add_alert
from lib.indicators import pivot_points, fibonacci_retracement, find_support_resistance
from lib.charts import build_main_chart

st.set_page_config(page_title="Trading", page_icon="⚡", layout="wide")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
init_session_state()

# ══════════════════════════════════════════════════════════════
#  SIDEBAR — Market config
# ══════════════════════════════════════════════════════════════

st.sidebar.header("📊 Market")
ticker_input = st.sidebar.text_input("Symbol", "AAPL").upper().strip()

col_p, col_i = st.sidebar.columns(2)
with col_p:
    period_label = st.selectbox("Period", list(PERIOD_MAP.keys()), index=3)
with col_i:
    interval_label = st.selectbox("Interval", list(INTERVAL_MAP.keys()), index=6)

period = PERIOD_MAP[period_label]
interval = INTERVAL_MAP[interval_label]

# Validate combo
valid_periods = VALID_COMBOS.get(interval, list(PERIOD_MAP.keys()))
if period_label not in valid_periods:
    st.sidebar.warning(f"⚠️ {interval_label} interval not valid with {period_label} period. Using 3M.")
    period = "3mo"

asset_class = st.sidebar.selectbox("Instrument", ["Stock / Forex / Crypto", "Options Chain"])

# ── Indicators config ─────────────────────────────────────────
st.sidebar.header("📐 Indicators")

# Overlays
show_sma = st.sidebar.checkbox("SMA", value=True)
sma_periods = []
if show_sma:
    sma_input = st.sidebar.text_input("SMA Periods (comma-sep)", "20, 50")
    sma_periods = [int(x.strip()) for x in sma_input.split(",") if x.strip().isdigit()]

show_ema = st.sidebar.checkbox("EMA")
ema_periods = []
if show_ema:
    ema_input = st.sidebar.text_input("EMA Periods", "12, 26")
    ema_periods = [int(x.strip()) for x in ema_input.split(",") if x.strip().isdigit()]

show_bb = st.sidebar.checkbox("Bollinger Bands")
show_vwap = st.sidebar.checkbox("VWAP")
show_ichimoku = st.sidebar.checkbox("Ichimoku Cloud")
show_keltner = st.sidebar.checkbox("Keltner Channels")

# Panels
show_volume = st.sidebar.checkbox("Volume", value=True)
show_rsi = st.sidebar.checkbox("RSI", value=True)
show_macd = st.sidebar.checkbox("MACD")
show_stoch_rsi = st.sidebar.checkbox("Stochastic RSI")
show_adx = st.sidebar.checkbox("ADX")
show_obv = st.sidebar.checkbox("OBV")
show_mfi = st.sidebar.checkbox("MFI")

# Levels
st.sidebar.header("📏 Levels")
show_sr = st.sidebar.checkbox("Support / Resistance")
show_fib = st.sidebar.checkbox("Fibonacci Retracement")
show_pivot = st.sidebar.checkbox("Pivot Points")

# ══════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ══════════════════════════════════════════════════════════════

try:
    hist = fetch_history(ticker_input, period, interval)
    info = fetch_info(ticker_input)
    current_price = float(
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or hist["Close"].iloc[-1]
    )

    # Check pending orders
    check_pending_orders(current_price, ticker_input)

    # ── Header metrics ────────────────────────────────────
    st.title(f"⚡ {ticker_input}")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        day_chg = hist["Close"].iloc[-1] - hist["Close"].iloc[-2] if len(hist) > 1 else 0
        day_pct = (day_chg / hist["Close"].iloc[-2] * 100) if len(hist) > 1 else 0
        st.metric("Price", f"${current_price:,.2f}", delta=f"{day_chg:+.2f} ({day_pct:+.2f}%)")
    with c2:
        vol = info.get("volume") or info.get("regularMarketVolume") or 0
        st.metric("Volume", f"{vol:,.0f}")
    with c3:
        mkt_cap = info.get("marketCap")
        if mkt_cap:
            label = f"${mkt_cap/1e12:.2f}T" if mkt_cap >= 1e12 else f"${mkt_cap/1e9:.2f}B" if mkt_cap >= 1e9 else f"${mkt_cap/1e6:.0f}M"
            st.metric("Market Cap", label)
        else:
            st.metric("Market Cap", "N/A")
    with c4:
        st.metric("💵 Cash", f"${st.session_state.balance:,.2f}")
    with c5:
        beta = info.get("beta")
        st.metric("Beta", f"{beta:.2f}" if beta else "N/A")

    # ── Chart ─────────────────────────────────────────────
    overlays = {
        "sma": sma_periods if show_sma else [],
        "ema": ema_periods if show_ema else [],
        "bollinger": show_bb,
        "vwap": show_vwap,
        "ichimoku": show_ichimoku,
        "keltner": show_keltner,
    }
    panels = {
        "volume": show_volume, "rsi": show_rsi, "macd": show_macd,
        "stoch_rsi": show_stoch_rsi, "adx": show_adx, "obv": show_obv, "mfi": show_mfi,
    }
    fig = build_main_chart(hist, overlays, panels,
                           support_resistance=show_sr, fib_levels=show_fib, pivot=show_pivot)
    st.plotly_chart(fig, use_container_width=True)

    # ── Multi-timeframe ───────────────────────────────────
    with st.expander("🔍 Multi-Timeframe View"):
        mtf_cols = st.columns(3)
        timeframes = {"Daily": ("6mo", "1d"), "4H": ("1mo", "1h"), "1H": ("5d", "1h")}
        from lib.charts import multi_timeframe_chart
        mtf_data = {}
        for label, (p, i) in timeframes.items():
            try:
                mtf_data[label] = fetch_history(ticker_input, p, i)
            except Exception:
                pass
        if mtf_data:
            st.plotly_chart(multi_timeframe_chart(mtf_data), use_container_width=True)

    # ── Trading Zone ──────────────────────────────────────
    st.markdown("---")
    trade_col, info_col = st.columns([2, 1])

    with trade_col:
        st.subheader("⚡ Order Entry")

        if asset_class == "Stock / Forex / Crypto":
            tab_market, tab_limit, tab_trailing, tab_oco, tab_short = st.tabs([
                "Market", "Limit / Stop", "Trailing Stop", "OCO Bracket", "Short Selling"
            ])

            with tab_market:
                mc1, mc2, mc3 = st.columns([1, 1, 1])
                with mc1:
                    action = st.selectbox("Action", ["Buy", "Sell"], key="mkt_act")
                with mc2:
                    qty = st.number_input("Quantity", min_value=1, value=10, key="mkt_qty")
                with mc3:
                    est_fill = simulate_fill_price(current_price, "buy" if action == "Buy" else "sell")
                    total = qty * est_fill
                    st.markdown(f"**Est. Total:** ${total:,.2f}")
                    st.caption(f"Est. fill: ${est_fill:.2f}")

                note = st.text_input("Trade note (optional)", key="mkt_note")
                tags = st.multiselect("Tags", ["Momentum", "Mean Reversion", "Breakout",
                    "Scalp", "Swing", "News", "Technical", "Fundamental"], key="mkt_tags")

                if st.button("🚀 Execute Market Order", use_container_width=True, type="primary"):
                    execute_trade(ticker_input, action, qty, current_price, note=note, tags=tags)
                    st.rerun()

            with tab_limit:
                lc1, lc2, lc3, lc4 = st.columns(4)
                with lc1:
                    order_type = st.selectbox("Type", ["Limit Buy", "Limit Sell", "Stop-Loss", "Take-Profit"])
                with lc2:
                    target = st.number_input("Target $", min_value=0.01,
                        value=round(current_price, 2), step=0.01, key="lim_target")
                with lc3:
                    lim_qty = st.number_input("Qty", min_value=1, value=10, key="lim_qty")
                with lc4:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("📋 Place Order", use_container_width=True, key="place_lim"):
                        o = place_order(ticker_input, order_type, target, lim_qty)
                        st.success(f"Order placed: {o['id']}")

            with tab_trailing:
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    trail_type = st.radio("Trail by", ["Percentage", "Fixed $"], horizontal=True)
                with tc2:
                    if trail_type == "Percentage":
                        trail_val = st.number_input("Trail %", min_value=0.1, value=5.0, step=0.5)
                    else:
                        trail_val = st.number_input("Trail $", min_value=0.01, value=5.0, step=0.5)
                with tc3:
                    trail_qty = st.number_input("Qty", min_value=1, value=10, key="trail_qty")

                st.caption(f"Current stop level: ${current_price * (1 - trail_val/100):,.2f}" if trail_type == "Percentage"
                          else f"Current stop level: ${current_price - trail_val:,.2f}")
                if st.button("📉 Place Trailing Stop", use_container_width=True):
                    place_trailing_stop(
                        ticker_input, trail_qty, current_price,
                        trail_pct=trail_val if trail_type == "Percentage" else None,
                        trail_amount=trail_val if trail_type == "Fixed $" else None,
                    )
                    st.success("Trailing stop placed!")

            with tab_oco:
                st.caption("One-Cancels-Other: Stop-Loss + Take-Profit linked together")
                oc1, oc2, oc3 = st.columns(3)
                with oc1:
                    sl_price = st.number_input("Stop-Loss $", value=round(current_price * 0.95, 2),
                        step=0.01, key="oco_sl")
                with oc2:
                    tp_price = st.number_input("Take-Profit $", value=round(current_price * 1.10, 2),
                        step=0.01, key="oco_tp")
                with oc3:
                    oco_qty = st.number_input("Qty", min_value=1, value=10, key="oco_qty")

                rr = abs(tp_price - current_price) / abs(current_price - sl_price) if current_price != sl_price else 0
                st.caption(f"Risk/Reward: 1:{rr:.2f}")
                if st.button("🔗 Place OCO Bracket", use_container_width=True):
                    place_oco_bracket(ticker_input, oco_qty, sl_price, tp_price)
                    st.success("OCO bracket placed!")

            with tab_short:
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    short_action = st.selectbox("Action", ["Short", "Cover"], key="short_act")
                with sc2:
                    short_qty = st.number_input("Qty", min_value=1, value=10, key="short_qty")
                with sc3:
                    if short_action == "Short":
                        margin = short_qty * current_price * 1.5
                        st.markdown(f"**Margin req:** ${margin:,.2f}")
                    else:
                        st.markdown(f"**Cost:** ${short_qty * current_price:,.2f}")
                if st.button("🔻 Execute", use_container_width=True, key="exec_short"):
                    execute_trade(ticker_input, short_action, short_qty, current_price)
                    st.rerun()

        elif asset_class == "Options Chain":
            st.info("📋 Options Chain — analyze and trade with Black-Scholes pricing")
            try:
                expirations = fetch_options_expirations(ticker_input)
                if expirations:
                    expiry = st.selectbox("Expiration", expirations)
                    calls_df, puts_df = fetch_options_chain(ticker_input, expiry)
                    opt_type = st.radio("Type", ["Calls", "Puts"], horizontal=True)
                    df_opt = calls_df if opt_type == "Calls" else puts_df
                    
                    # Filtrer autour du prix actuel
                    df_filtered = df_opt[
                        (df_opt["strike"] > current_price * 0.85) &
                        (df_opt["strike"] < current_price * 1.15)
                    ]
                    
                    display_cols = ["contractSymbol", "strike", "lastPrice", "bid", "ask",
                                    "volume", "openInterest", "impliedVolatility"]
                    available = [c for c in display_cols if c in df_filtered.columns]
                    st.dataframe(df_filtered[available], use_container_width=True)
                    
                    # ── Options Analysis & Trading ───────────────────────────
                    st.markdown("---")
                    st.write("### 🧮 Analyse & Trading d'Options")
                    
                    col_analysis, col_trade = st.columns(2)
                    
                    with col_analysis:
                        st.write("#### 📊 Analyse Black-Scholes")
                        selected_strike = st.selectbox(
                            "Sélectionner Strike", 
                            sorted(df_filtered['strike'].unique()),
                            key="opt_strike"
                        )
                        
                        # Récupérer les données de l'option
                        opt_data = df_filtered[df_filtered['strike'] == selected_strike].iloc[0]
                        
                        # Calcul du temps jusqu'à l'expiration
                        from datetime import datetime as dt
                        T = (dt.strptime(expiry, "%Y-%m-%d") - dt.now()).days / 365.0
                        
                        if T > 0:
                            # Import et calcul Black-Scholes
                            from lib.options_pricing import OptionCalculator
                            
                            bs = OptionCalculator(
                                S=current_price,
                                K=selected_strike,
                                T=T,
                                r=0.045,  # Taux sans risque approximé
                                sigma=opt_data.get('impliedVolatility', 0.2),
                                option_type=opt_type.lower()[:-1]  # "call" ou "put"
                            )
                            
                            theo_price = bs.price()
                            greeks = bs.greeks()
                            intrinsic = bs.intrinsic_value()
                            time_value = bs.time_value()
                            
                            # Affichage
                            st.metric(
                                "Prix Théorique (BS)",
                                f"${theo_price:.2f}",
                                delta=f"Marché: ${opt_data['lastPrice']:.2f}"
                            )
                            
                            st.write("**Greeks:**")
                            gc1, gc2, gc3, gc4 = st.columns(4)
                            with gc1:
                                st.metric("Δ (Delta)", greeks['Delta'])
                            with gc2:
                                st.metric("Γ (Gamma)", greeks['Gamma'])
                            with gc3:
                                st.metric("Θ (Theta)", greeks['Theta'])
                            with gc4:
                                st.metric("ν (Vega)", greeks['Vega'])
                            
                            st.caption(f"Intrinsic: ${intrinsic:.2f} | Time Value: ${time_value:.2f}")
                    
                    with col_trade:
                        st.write("#### 💼 Passer un Ordre d'Option")
                        
                        opt_qty = st.number_input(
                            "Nombre de Contrats",
                            min_value=1,
                            value=1,
                            step=1,
                            key="opt_qty"
                        )
                        
                        opt_action = st.selectbox(
                            "Action",
                            ["Buy", "Sell (Close)"],
                            key="opt_action"
                        )
                        
                        trade_price = opt_data['lastPrice']
                        total_cost = opt_qty * trade_price * 100
                        
                        st.info(f"**Coût Total:** ${total_cost:,.2f}")
                        st.caption(f"Prix unitaire: ${trade_price:.2f} | 100 actions par contrat")
                        
                        if st.button("🚀 Exécuter Ordre Option", use_container_width=True, type="primary"):
                            # Métadonnées cruciales pour le portefeuille
                            meta = {
                                "strike": float(selected_strike),
                                "expiry": expiry,
                                "type": opt_type.lower()[:-1],  # "call" ou "put"
                                "multiplier": 100
                            }
                            
                            success = execute_trade(
                                ticker=ticker_input,
                                action=opt_action,
                                quantity=opt_qty,
                                raw_price=trade_price,
                                asset_type="Option",
                                option_metadata=meta
                            )
                            
                            if success:
                                st.rerun()
                else:
                    st.warning("No options available for this ticker.")
            except Exception as e:
                st.error(f"Options error: {e}")

        # ── Pending orders display ────────────────────────
        active = get_active_orders()
        if active:
            st.markdown("---")
            st.subheader("📋 Pending Orders")
            for i, o in enumerate(st.session_state.pending_orders):
                oc1, oc2 = st.columns([5, 1])
                with oc1:
                    oco_tag = f" (OCO: {o['oco_pair_id']})" if o.get("oco_pair_id") else ""
                    trail_tag = ""
                    if o["type"] == "Trailing-Stop":
                        trail_tag = f" | High: ${o.get('highest_price', 0):.2f}"
                    st.caption(
                        f"**{o['id']}** — {o['type']} | {o['qty']} × {o['ticker']} "
                        f"@ ${o['target_price']:.2f}{oco_tag}{trail_tag} | {o['created']}"
                    )
                with oc2:
                    if st.button("❌", key=f"cancel_{i}"):
                        cancel_order(i)
                        st.rerun()

    with info_col:
        # News
        st.subheader("📰 News")
        news = fetch_news(ticker_input)
        if news:
            for n in news[:7]:
                title = n.get("title", "Untitled")
                publisher = n.get("publisher", "")
                link = n.get("link", "")
                with st.expander(f"**{title}**"):
                    st.caption(publisher)
                    if link:
                        st.markdown(f"[Read →]({link})")
        else:
            st.info("No news available.")

        # Price alerts
        st.markdown("---")
        st.subheader("🔔 Alerts")
        al1, al2 = st.columns(2)
        with al1:
            alert_cond = st.selectbox("Condition", ["above", "below"], key="alert_cond")
        with al2:
            alert_price = st.number_input("Price $", value=round(current_price, 2),
                step=0.01, key="alert_price")
        alert_note = st.text_input("Note", key="alert_note")
        if st.button("🔔 Set Alert", use_container_width=True):
            add_alert(ticker_input, alert_cond, alert_price, alert_note)
            st.success("Alert set!")

        if st.session_state.alerts:
            for i, a in enumerate(st.session_state.alerts):
                st.caption(f"{a['ticker']} {a['condition']} ${a['price']:.2f} — {a.get('note', '')}")

    # ── Risk Calculator ───────────────────────────────────
    st.markdown("---")
    with st.expander("🎯 Position Sizing & Risk Calculator"):
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            entry_price = st.number_input("Entry $", value=round(current_price, 2), step=0.01, key="rc_entry")
        with rc2:
            sl = st.number_input("Stop-Loss $", value=round(current_price * 0.95, 2), step=0.01, key="rc_sl")
        with rc3:
            tp = st.number_input("Take-Profit $", value=round(current_price * 1.10, 2), step=0.01, key="rc_tp")
        with rc4:
            risk_pct = st.number_input("Risk % of capital", value=2.0, step=0.5, key="rc_risk")

        if entry_price > 0 and sl > 0 and sl != entry_price:
            risk_per_share = abs(entry_price - sl)
            reward_per_share = abs(tp - entry_price)
            risk_amount = st.session_state.balance * (risk_pct / 100)
            optimal_qty = int(risk_amount / risk_per_share)
            rr = reward_per_share / risk_per_share if risk_per_share > 0 else 0

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Optimal Size", f"{optimal_qty} shares")
            r2.metric("Risk / Share", f"${risk_per_share:.2f}")
            r3.metric("Total Risk", f"${risk_per_share * optimal_qty:.2f}")
            r4.metric("R:R Ratio", f"1:{rr:.2f}")

except Exception as e:
    st.error(f"Error loading **{ticker_input}**: {e}")
    st.caption("Check the symbol (e.g., AAPL, MSFT, BTC-USD, EURUSD=X)")
