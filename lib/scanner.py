"""
Market scanner — screen stocks by technical criteria.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import indicators as ind
from lib.data_fetcher import fetch_history, get_current_price


@st.cache_data(ttl=300, show_spinner="Scanning market...")
def scan_universe(
    tickers: tuple,
    criteria: dict,
) -> list[dict]:
    """
    Scan a universe of tickers against technical criteria.

    criteria keys:
      - rsi_below: float
      - rsi_above: float
      - above_sma: int (period)
      - below_sma: int
      - volume_surge: float (multiplier vs 20-day avg)
      - price_min: float
      - price_max: float
      - macd_bullish: bool
      - bb_oversold: bool
    """
    results = []

    for ticker in tickers:
        try:
            df = fetch_history(ticker, period="3mo", interval="1d")
            if len(df) < 30:
                continue

            price = df["Close"].iloc[-1]
            rsi_val = ind.rsi(df).iloc[-1]
            vol_avg = ind.volume_sma(df, 20).iloc[-1]
            vol_today = df["Volume"].iloc[-1]
            sma_20 = ind.sma(df, 20).iloc[-1]
            sma_50 = ind.sma(df, 50).iloc[-1]
            sma_200 = ind.sma(df, 200).iloc[-1] if len(df) >= 200 else None
            macd_line, signal_line, _ = ind.macd(df)
            upper, mid, lower = ind.bollinger_bands(df)

            entry = {
                "ticker": ticker,
                "price": round(price, 2),
                "rsi": round(rsi_val, 1) if pd.notna(rsi_val) else None,
                "sma_20": round(sma_20, 2) if pd.notna(sma_20) else None,
                "sma_50": round(sma_50, 2) if pd.notna(sma_50) else None,
                "sma_200": round(sma_200, 2) if sma_200 and pd.notna(sma_200) else None,
                "volume": int(vol_today),
                "vol_ratio": round(vol_today / vol_avg, 2) if vol_avg > 0 else 0,
                "macd_bullish": bool(macd_line.iloc[-1] > signal_line.iloc[-1]),
                "bb_position": "oversold" if price <= lower.iloc[-1]
                    else "overbought" if price >= upper.iloc[-1]
                    else "neutral",
                "change_1d": round(
                    (price / df["Close"].iloc[-2] - 1) * 100, 2
                ) if len(df) > 1 else 0,
            }

            # Apply filters
            if criteria.get("rsi_below") and (entry["rsi"] is None or entry["rsi"] >= criteria["rsi_below"]):
                continue
            if criteria.get("rsi_above") and (entry["rsi"] is None or entry["rsi"] <= criteria["rsi_above"]):
                continue
            if criteria.get("above_sma"):
                p = criteria["above_sma"]
                sma_val = ind.sma(df, p).iloc[-1]
                if pd.isna(sma_val) or price <= sma_val:
                    continue
            if criteria.get("below_sma"):
                p = criteria["below_sma"]
                sma_val = ind.sma(df, p).iloc[-1]
                if pd.isna(sma_val) or price >= sma_val:
                    continue
            if criteria.get("volume_surge") and entry["vol_ratio"] < criteria["volume_surge"]:
                continue
            if criteria.get("price_min") and price < criteria["price_min"]:
                continue
            if criteria.get("price_max") and price > criteria["price_max"]:
                continue
            if criteria.get("macd_bullish") and not entry["macd_bullish"]:
                continue
            if criteria.get("bb_oversold") and entry["bb_position"] != "oversold":
                continue

            results.append(entry)

        except Exception:
            continue

    return results


# ── Alert system ──────────────────────────────────────────────

def check_alerts(ticker: str, current_price: float) -> list[str]:
    """Check price alerts and return triggered messages."""
    triggered = []
    remaining = []

    for alert in st.session_state.get("alerts", []):
        if alert["ticker"] != ticker:
            remaining.append(alert)
            continue

        fire = False
        if alert["condition"] == "above" and current_price >= alert["price"]:
            fire = True
        elif alert["condition"] == "below" and current_price <= alert["price"]:
            fire = True
        elif alert["condition"] == "cross_above" and current_price >= alert["price"]:
            fire = True
        elif alert["condition"] == "cross_below" and current_price <= alert["price"]:
            fire = True

        if fire:
            triggered.append(
                f"🔔 Alert: {ticker} is {'above' if 'above' in alert['condition'] else 'below'} "
                f"${alert['price']:.2f} (current: ${current_price:.2f}) — {alert.get('note', '')}"
            )
        else:
            remaining.append(alert)

    st.session_state.alerts = remaining
    return triggered


def add_alert(ticker: str, condition: str, price: float, note: str = ""):
    """Add a price alert."""
    st.session_state.alerts.append({
        "ticker": ticker,
        "condition": condition,
        "price": price,
        "note": note,
    })
