"""
Backtesting engine — test strategies on historical data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from lib import indicators as ind


@dataclass
class BacktestResult:
    """Container for backtest output."""
    trades: list[dict] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    dates: list = field(default_factory=list)
    total_return_pct: float = 0
    buy_hold_return_pct: float = 0
    total_trades: int = 0
    win_rate: float = 0
    profit_factor: float = 0
    max_drawdown: float = 0
    sharpe: float = 0
    total_pnl: float = 0
    avg_trade: float = 0
    best_trade: float = 0
    worst_trade: float = 0


# ── Built-in strategies ───────────────────────────────────────

def strategy_sma_cross(df: pd.DataFrame, fast: int = 10, slow: int = 50) -> pd.Series:
    """SMA crossover: +1 when fast > slow, -1 otherwise."""
    sma_fast = ind.sma(df, fast)
    sma_slow = ind.sma(df, slow)
    signal = pd.Series(0, index=df.index)
    signal[sma_fast > sma_slow] = 1
    signal[sma_fast <= sma_slow] = -1
    return signal


def strategy_rsi_mean_reversion(df: pd.DataFrame, period: int = 14,
                                  oversold: int = 30, overbought: int = 70) -> pd.Series:
    """Buy when RSI < oversold, sell when RSI > overbought."""
    rsi_val = ind.rsi(df, period)
    signal = pd.Series(0, index=df.index)
    signal[rsi_val < oversold] = 1
    signal[rsi_val > overbought] = -1
    return signal


def strategy_macd_cross(df: pd.DataFrame) -> pd.Series:
    """MACD line crosses signal line."""
    macd_line, signal_line, _ = ind.macd(df)
    signal = pd.Series(0, index=df.index)
    signal[macd_line > signal_line] = 1
    signal[macd_line <= signal_line] = -1
    return signal


def strategy_bollinger_bounce(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.Series:
    """Buy near lower band, sell near upper band."""
    upper, mid, lower = ind.bollinger_bands(df, period, std)
    signal = pd.Series(0, index=df.index)
    signal[df["Close"] <= lower] = 1
    signal[df["Close"] >= upper] = -1
    return signal


def strategy_combined_momentum(df: pd.DataFrame) -> pd.Series:
    """Combined: SMA trend + RSI confirmation."""
    sma_20 = ind.sma(df, 20)
    sma_50 = ind.sma(df, 50)
    rsi_val = ind.rsi(df, 14)

    signal = pd.Series(0, index=df.index)
    # Buy: price above both SMAs AND RSI not overbought
    buy_cond = (df["Close"] > sma_20) & (sma_20 > sma_50) & (rsi_val < 70)
    sell_cond = (df["Close"] < sma_20) | (rsi_val > 80)
    signal[buy_cond] = 1
    signal[sell_cond] = -1
    return signal


STRATEGIES = {
    "SMA Crossover": {
        "fn": strategy_sma_cross,
        "description": "Buy when fast SMA crosses above slow SMA",
        "params": {"fast": 10, "slow": 50},
    },
    "RSI Mean Reversion": {
        "fn": strategy_rsi_mean_reversion,
        "description": "Buy when RSI is oversold, sell when overbought",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
    },
    "MACD Crossover": {
        "fn": strategy_macd_cross,
        "description": "Buy when MACD crosses above signal line",
        "params": {},
    },
    "Bollinger Bounce": {
        "fn": strategy_bollinger_bounce,
        "description": "Buy at lower band, sell at upper band",
        "params": {"period": 20, "std": 2.0},
    },
    "Combined Momentum": {
        "fn": strategy_combined_momentum,
        "description": "SMA trend + RSI confirmation filter",
        "params": {},
    },
}


# ── Backtesting engine ───────────────────────────────────────

def run_backtest(
    df: pd.DataFrame,
    signal_fn: Callable,
    initial_capital: float = 100_000,
    commission_rate: float = 0.001,
    position_size_pct: float = 100,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    **strategy_params,
) -> BacktestResult:
    """
    Run a vectorized backtest with optional SL/TP.

    signal_fn: function(df, **params) → pd.Series of {-1, 0, +1}
    """
    result = BacktestResult()

    signals = signal_fn(df, **strategy_params)
    signals = signals.fillna(0)

    cash = initial_capital
    position = 0
    entry_price = 0.0
    equity = []
    trades = []

    for i in range(len(df)):
        close_price = df["Close"].iloc[i]
        date = df.index[i]
        
        # Intra-bar OHLC pour éviter le Look-Ahead Bias
        current_high = df["High"].iloc[i]
        current_low = df["Low"].iloc[i]
        open_price = df["Open"].iloc[i]

        # Check SL / TP if in position
        if position > 0:
            # Stop Loss : On vérifie si le PLUS BAS a touché le stop
            if stop_loss_pct:
                sl_price = entry_price * (1 - stop_loss_pct / 100)
                if current_low <= sl_price:
                    # On est sorti au pire des cas : au prix du SL (ou Open si gap baissier)
                    exit_price = min(open_price, sl_price) if i > 0 else sl_price
                    revenue = position * exit_price * (1 - commission_rate)
                    pnl = revenue - (position * entry_price)
                    cash += revenue
                    trades.append({
                        "date": str(date), "action": "Sell (SL)", "price": exit_price,
                        "qty": position, "pnl": round(pnl, 2),
                    })
                    position = 0
                    entry_price = 0
                    equity.append(cash)
                    continue

            # Take Profit : On vérifie si le PLUS HAUT a touché la cible
            if take_profit_pct and position > 0:
                tp_price = entry_price * (1 + take_profit_pct / 100)
                if current_high >= tp_price:
                    revenue = position * tp_price * (1 - commission_rate)
                    pnl = revenue - (position * entry_price)
                    cash += revenue
                    trades.append({
                        "date": str(date), "action": "Sell (TP)", "price": tp_price,
                        "qty": position, "pnl": round(pnl, 2),
                    })
                    position = 0
                    entry_price = 0
                    equity.append(cash)
                    continue

        sig = signals.iloc[i]

        # Buy signal, no position
        if sig == 1 and position == 0:
            invest = cash * (position_size_pct / 100)
            qty = int(invest / open_price)
            if qty > 0:
                cost = qty * open_price * (1 + commission_rate)
                cash -= cost
                position = qty
                entry_price = open_price
                trades.append({
                    "date": str(date), "action": "Buy", "price": open_price, "qty": qty, "pnl": 0,
                })

        # Sell signal, has position
        elif sig == -1 and position > 0:
            revenue = position * close_price * (1 - commission_rate)
            pnl = revenue - (position * entry_price)
            cash += revenue
            trades.append({
                "date": str(date), "action": "Sell", "price": close_price,
                "qty": position, "pnl": round(pnl, 2),
            })
            position = 0
            entry_price = 0

        equity.append(cash + position * close_price)

    # Close any open position at end
    if position > 0:
        price = df["Close"].iloc[-1]
        revenue = position * price * (1 - commission_rate)
        pnl = revenue - (position * entry_price)
        cash += revenue
        trades.append({
            "date": str(df.index[-1]), "action": "Sell (Close)", "price": price,
            "qty": position, "pnl": round(pnl, 2),
        })
        equity[-1] = cash

    # Compute stats
    result.trades = trades
    result.equity_curve = equity
    result.dates = df.index.tolist()
    result.total_trades = len(trades)

    pnls = [t["pnl"] for t in trades if t["action"].startswith("Sell")]
    if pnls:
        wins = [p for p in pnls if p > 0]
        losses_list = [p for p in pnls if p < 0]
        result.total_pnl = sum(pnls)
        result.win_rate = len(wins) / len(pnls) * 100
        result.avg_trade = np.mean(pnls)
        result.best_trade = max(pnls)
        result.worst_trade = min(pnls)
        result.profit_factor = abs(sum(wins) / sum(losses_list)) if losses_list else float("inf")

    result.total_return_pct = (equity[-1] / initial_capital - 1) * 100 if equity else 0
    result.buy_hold_return_pct = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100

    # Max drawdown
    if equity:
        peak = equity[0]
        max_dd = 0
        for v in equity:
            peak = max(peak, v)
            dd = (peak - v) / peak * 100
            max_dd = max(max_dd, dd)
        result.max_drawdown = round(max_dd, 2)

    # Sharpe
    if len(equity) > 1:
        returns = pd.Series(equity).pct_change().dropna()
        if returns.std() > 0:
            result.sharpe = round(returns.mean() / returns.std() * np.sqrt(252), 2)

    return result
