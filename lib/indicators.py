"""
Technical indicators for charting and analysis.

All functions take a DataFrame with at least OHLCV columns
and return Series or tuples of Series.
"""

import pandas as pd
import numpy as np


# ── Trend ─────────────────────────────────────────────────────

def sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["Close"].rolling(window=period).mean()


def ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["Close"].ewm(span=period, adjust=False).mean()


def wma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    weights = np.arange(1, period + 1)
    return df["Close"].rolling(window=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    cum_tp_vol = (typical * df["Volume"]).cumsum()
    cum_vol = df["Volume"].cumsum()
    return cum_tp_vol / cum_vol


def ichimoku(df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52):
    """Returns (tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou)."""
    high_t = df["High"].rolling(tenkan).max()
    low_t = df["Low"].rolling(tenkan).min()
    tenkan_sen = (high_t + low_t) / 2

    high_k = df["High"].rolling(kijun).max()
    low_k = df["Low"].rolling(kijun).min()
    kijun_sen = (high_k + low_k) / 2

    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)

    high_sb = df["High"].rolling(senkou_b).max()
    low_sb = df["Low"].rolling(senkou_b).min()
    senkou_b_line = ((high_sb + low_sb) / 2).shift(kijun)

    chikou = df["Close"].shift(-kijun)

    return tenkan_sen, kijun_sen, senkou_a, senkou_b_line, chikou


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """Basic SuperTrend indicator."""
    atr_val = atr(df, period)
    hl2 = (df["High"] + df["Low"]) / 2
    upper = hl2 + multiplier * atr_val
    lower = hl2 - multiplier * atr_val

    st_line = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=float)

    for i in range(period, len(df)):
        if df["Close"].iloc[i] > upper.iloc[i - 1]:
            st_line.iloc[i] = lower.iloc[i]
            direction.iloc[i] = 1
        elif df["Close"].iloc[i] < lower.iloc[i - 1]:
            st_line.iloc[i] = upper.iloc[i]
            direction.iloc[i] = -1
        else:
            if direction.iloc[i - 1] == 1:
                st_line.iloc[i] = max(lower.iloc[i], st_line.iloc[i - 1])
            else:
                st_line.iloc[i] = min(upper.iloc[i], st_line.iloc[i - 1])
            direction.iloc[i] = direction.iloc[i - 1]

    return st_line, direction


# ── Momentum ──────────────────────────────────────────────────

def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def stochastic_rsi(df: pd.DataFrame, rsi_period: int = 14, stoch_period: int = 14,
                    k_smooth: int = 3, d_smooth: int = 3):
    """Returns (%K, %D) of Stochastic RSI."""
    rsi_val = rsi(df, rsi_period)
    min_rsi = rsi_val.rolling(stoch_period).min()
    max_rsi = rsi_val.rolling(stoch_period).max()
    stoch_rsi = (rsi_val - min_rsi) / (max_rsi - min_rsi)
    k = stoch_rsi.rolling(k_smooth).mean() * 100
    d = k.rolling(d_smooth).mean()
    return k, d


def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad)


def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["High"].rolling(period).max()
    low = df["Low"].rolling(period).min()
    return -100 * (high - df["Close"]) / (high - low)


# ── Volatility ────────────────────────────────────────────────

def bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0):
    """Returns (upper, middle, lower)."""
    mid = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def keltner_channels(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 14,
                     multiplier: float = 2.0):
    """Returns (upper, middle, lower)."""
    mid = ema(df, ema_period)
    atr_val = atr(df, atr_period)
    upper = mid + multiplier * atr_val
    lower = mid - multiplier * atr_val
    return upper, mid, lower


# ── Volume ────────────────────────────────────────────────────

def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(df["Close"].diff())
    return (direction * df["Volume"]).cumsum()


def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["Volume"].rolling(period).mean()


def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Money Flow Index."""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    mf = tp * df["Volume"]
    delta = tp.diff()
    pos_mf = mf.where(delta > 0, 0).rolling(period).sum()
    neg_mf = mf.where(delta < 0, 0).rolling(period).sum()
    ratio = pos_mf / neg_mf
    return 100 - (100 / (1 + ratio))


# ── Trend Strength ────────────────────────────────────────────

def adx(df: pd.DataFrame, period: int = 14):
    """Returns (ADX, +DI, -DI)."""
    plus_dm = df["High"].diff()
    minus_dm = -df["Low"].diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    atr_val = atr(df, period)
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr_val)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr_val)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_val = dx.rolling(period).mean()
    return adx_val, plus_di, minus_di


# ── Support / Resistance ─────────────────────────────────────

def find_support_resistance(df: pd.DataFrame, window: int = 20, num_levels: int = 5):
    """Detect local min/max as support and resistance levels."""
    highs = df["High"].rolling(window=window, center=True).max()
    lows = df["Low"].rolling(window=window, center=True).min()

    resistance_mask = df["High"] == highs
    support_mask = df["Low"] == lows

    resistances = df.loc[resistance_mask, "High"].drop_duplicates().sort_values(ascending=False)
    supports = df.loc[support_mask, "Low"].drop_duplicates().sort_values()

    return supports.head(num_levels).tolist(), resistances.head(num_levels).tolist()


def pivot_points(df: pd.DataFrame):
    """Classic pivot points from last completed bar."""
    if len(df) < 2:
        return {}
    last = df.iloc[-2]  # Use prior bar
    h, l, c = last["High"], last["Low"], last["Close"]
    pp = (h + l + c) / 3
    return {
        "PP": round(pp, 2),
        "R1": round(2 * pp - l, 2),
        "R2": round(pp + (h - l), 2),
        "R3": round(h + 2 * (pp - l), 2),
        "S1": round(2 * pp - h, 2),
        "S2": round(pp - (h - l), 2),
        "S3": round(l - 2 * (h - pp), 2),
    }


# ── Fibonacci ─────────────────────────────────────────────────

def fibonacci_retracement(high: float, low: float) -> dict[str, float]:
    """Calculate Fibonacci retracement levels."""
    diff = high - low
    levels = {
        "0%": high,
        "23.6%": high - 0.236 * diff,
        "38.2%": high - 0.382 * diff,
        "50%": high - 0.5 * diff,
        "61.8%": high - 0.618 * diff,
        "78.6%": high - 0.786 * diff,
        "100%": low,
    }
    return {k: round(v, 2) for k, v in levels.items()}
