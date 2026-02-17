"""
Market data fetching — wraps yfinance with caching and error handling.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@st.cache_data(ttl=60, show_spinner=False)
def fetch_history(ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """Return OHLCV DataFrame for *ticker*."""
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval)
    if df.empty:
        raise ValueError(f"No data returned for {ticker}")
    return df


@st.cache_data(ttl=30, show_spinner=False)
def fetch_info(ticker: str) -> dict:
    """Return the yfinance .info dict (cached 30 s)."""
    return yf.Ticker(ticker).info


def get_current_price(ticker: str) -> float | None:
    """Best-effort current price for *ticker*."""
    try:
        info = fetch_info(ticker)
        p = info.get("currentPrice") or info.get("regularMarketPrice")
        if p:
            return float(p)
        h = fetch_history(ticker, period="1d", interval="1d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except Exception:
        return None


@st.cache_data(ttl=30, show_spinner=False)
def get_batch_prices(tickers: tuple) -> dict[str, float | None]:
    """Fetch current prices for a batch of tickers."""
    prices: dict[str, float | None] = {}
    for t in tickers:
        prices[t] = get_current_price(t)
    return prices


@st.cache_data(ttl=300, show_spinner=False)
def get_sector_info(tickers: tuple) -> dict[str, str]:
    """Return {ticker: sector} mapping."""
    mapping: dict[str, str] = {}
    for t in tickers:
        try:
            info = fetch_info(t)
            mapping[t] = info.get("sector", "Other")
        except Exception:
            mapping[t] = "Other"
    return mapping


@st.cache_data(ttl=600, show_spinner=False)
def fetch_benchmark(symbol: str = "SPY", period: str = "1y") -> pd.DataFrame:
    """Fetch benchmark returns for comparison."""
    return fetch_history(symbol, period=period, interval="1d")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_options_chain(ticker: str, expiry: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch options chain for a given expiry. Returns (calls_df, puts_df)."""
    t = yf.Ticker(ticker)
    chain = t.option_chain(expiry)
    return chain.calls, chain.puts


@st.cache_data(ttl=300, show_spinner=False)
def fetch_options_expirations(ticker: str) -> tuple:
    """Available option expiration dates."""
    t = yf.Ticker(ticker)
    return t.options


def fetch_news(ticker: str) -> list[dict]:
    """Fetch recent news (not cached — lightweight)."""
    try:
        t = yf.Ticker(ticker)
        return t.news or []
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_correlation_data(tickers: tuple, period: str = "6mo") -> pd.DataFrame:
    """Download close prices for multiple tickers and return correlation matrix."""
    data = yf.download(list(tickers), period=period, interval="1d", progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        closes = data["Close"]
    else:
        closes = data[["Close"]]
        closes.columns = list(tickers)
    returns = closes.pct_change().dropna()
    return returns.corr()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_multi_close(tickers: tuple, period: str = "6mo") -> pd.DataFrame:
    """Download daily close prices for multiple tickers."""
    data = yf.download(list(tickers), period=period, interval="1d", progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        return data["Close"].dropna()
    return data[["Close"]].dropna()
