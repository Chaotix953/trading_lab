"""
Scanner page — screen the market by technical criteria.
"""

import streamlit as st
import pandas as pd

from lib.state import init_session_state
from lib.styles import MAIN_CSS
from lib.config import SCANNER_SP500_SAMPLE
from lib.scanner import scan_universe

st.set_page_config(page_title="Scanner", page_icon="🔍", layout="wide")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
init_session_state()

st.title("🔍 Market Scanner")

# ── Universe selection ────────────────────────────────────────
st.subheader("📌 Universe")
universe_choice = st.radio(
    "Select universe", ["S&P 500 Sample (~36)", "Watchlist", "Custom"],
    horizontal=True,
)

if universe_choice == "S&P 500 Sample (~36)":
    tickers = tuple(SCANNER_SP500_SAMPLE)
elif universe_choice == "Watchlist":
    tickers = tuple(st.session_state.watchlist)
else:
    custom = st.text_input("Tickers (comma-separated)", "AAPL, MSFT, GOOGL, AMZN, TSLA")
    tickers = tuple(t.strip().upper() for t in custom.split(",") if t.strip())

st.caption(f"{len(tickers)} tickers in universe")

# ── Filter criteria ───────────────────────────────────────────
st.markdown("---")
st.subheader("🎛️ Filters")

criteria: dict = {}

f1, f2, f3, f4 = st.columns(4)
with f1:
    use_rsi_low = st.checkbox("RSI Below")
    if use_rsi_low:
        criteria["rsi_below"] = st.number_input("RSI <", value=30, min_value=5, max_value=95)

with f2:
    use_rsi_high = st.checkbox("RSI Above")
    if use_rsi_high:
        criteria["rsi_above"] = st.number_input("RSI >", value=70, min_value=5, max_value=95)

with f3:
    use_above_sma = st.checkbox("Price > SMA")
    if use_above_sma:
        criteria["above_sma"] = st.selectbox("SMA Period (above)", [20, 50, 100, 200], index=1)

with f4:
    use_vol_surge = st.checkbox("Volume Surge")
    if use_vol_surge:
        criteria["volume_surge"] = st.number_input("Vol > x avg", value=2.0, min_value=1.1, step=0.5)

f5, f6, f7, f8 = st.columns(4)
with f5:
    use_below_sma = st.checkbox("Price < SMA")
    if use_below_sma:
        criteria["below_sma"] = st.selectbox("SMA Period (below)", [20, 50, 100, 200], index=0)

with f6:
    use_macd = st.checkbox("MACD Bullish")
    if use_macd:
        criteria["macd_bullish"] = True

with f7:
    use_bb = st.checkbox("BB Oversold")
    if use_bb:
        criteria["bb_oversold"] = True

with f8:
    use_price = st.checkbox("Price Range")
    if use_price:
        criteria["price_min"] = st.number_input("Min $", value=10.0, min_value=0.01)
        criteria["price_max"] = st.number_input("Max $", value=500.0, min_value=1.0)

# ── Run scan ──────────────────────────────────────────────────
st.markdown("---")

if st.button("🔍 Run Scanner", type="primary", use_container_width=True):
    if not criteria:
        st.warning("Select at least one filter.")
    else:
        results = scan_universe(tickers, criteria)

        if results:
            st.success(f"Found {len(results)} matches!")
            df = pd.DataFrame(results)

            # Sort by volume ratio (most unusual first)
            if "vol_ratio" in df.columns:
                df = df.sort_values("vol_ratio", ascending=False)

            st.dataframe(df, use_container_width=True, hide_index=True)

            # Quick add to watchlist
            st.markdown("---")
            st.caption("Click to add to watchlist:")
            cols = st.columns(min(len(results), 6))
            for i, r in enumerate(results):
                with cols[i % 6]:
                    if st.button(f"➕ {r['ticker']}", key=f"add_scan_{r['ticker']}"):
                        if r["ticker"] not in st.session_state.watchlist:
                            st.session_state.watchlist.append(r["ticker"])
                            st.success(f"Added {r['ticker']}!")
        else:
            st.info("No stocks match your criteria. Try relaxing filters.")
