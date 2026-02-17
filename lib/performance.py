"""
Performance analytics — comprehensive statistics for trading evaluation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from scipy import stats as sp_stats


def compute_performance_stats() -> dict:
    """Full performance statistics dashboard."""
    history = st.session_state.history
    closed_pnls = [t["pnl"] for t in history if isinstance(t.get("pnl"), (int, float))]

    result: dict = {}
    result["total_trades"] = len(history)
    result["closed_trades"] = len(closed_pnls)
    result["open_positions"] = len(st.session_state.portfolio)
    result["total_commissions"] = sum(t.get("commission", 0) for t in history)
    result["total_slippage"] = sum(t.get("slippage", 0) for t in history)

    if not closed_pnls:
        result.update({
            "win_rate": 0, "total_pnl": 0, "avg_win": 0, "avg_loss": 0,
            "profit_factor": 0, "best_trade": 0, "worst_trade": 0,
            "max_drawdown": 0, "sharpe": 0, "sortino": 0, "calmar": 0,
            "avg_holding_pnl": 0, "expectancy": 0, "kelly_pct": 0,
            "consecutive_wins": 0, "consecutive_losses": 0,
            "long_pnl": 0, "short_pnl": 0,
        })
        return result

    wins = [p for p in closed_pnls if p > 0]
    losses = [p for p in closed_pnls if p < 0]
    breakeven = [p for p in closed_pnls if p == 0]

    result["win_rate"] = len(wins) / len(closed_pnls) * 100
    result["total_pnl"] = sum(closed_pnls)
    result["avg_win"] = np.mean(wins) if wins else 0
    result["avg_loss"] = np.mean(losses) if losses else 0
    result["avg_holding_pnl"] = np.mean(closed_pnls)
    result["best_trade"] = max(closed_pnls)
    result["worst_trade"] = min(closed_pnls)
    result["profit_factor"] = abs(sum(wins) / sum(losses)) if losses else float("inf")

    # Expectancy
    win_prob = len(wins) / len(closed_pnls) if closed_pnls else 0
    loss_prob = 1 - win_prob
    avg_w = np.mean(wins) if wins else 0
    avg_l = abs(np.mean(losses)) if losses else 0
    result["expectancy"] = win_prob * avg_w - loss_prob * avg_l

    # Kelly Criterion
    if avg_l > 0 and win_prob > 0:
        b = avg_w / avg_l  # Win/Loss ratio
        result["kelly_pct"] = max(0, (win_prob * b - loss_prob) / b * 100)
    else:
        result["kelly_pct"] = 0

    # Consecutive streaks
    result["consecutive_wins"] = _max_streak(closed_pnls, positive=True)
    result["consecutive_losses"] = _max_streak(closed_pnls, positive=False)

    # Long vs short P&L
    long_trades = [t["pnl"] for t in history if t.get("pnl") is not None and t["action"] in ("Sell",)]
    short_trades = [t["pnl"] for t in history if t.get("pnl") is not None and t["action"] in ("Cover",)]
    result["long_pnl"] = sum(long_trades)
    result["short_pnl"] = sum(short_trades)

    # Max Drawdown from equity curve
    result["max_drawdown"] = _max_drawdown()

    # Risk-adjusted ratios
    initial = st.session_state.initial_balance
    if len(closed_pnls) > 1:
        returns = np.array(closed_pnls) / initial
        mean_r = np.mean(returns)
        std_r = np.std(returns)

        # Sharpe (annualized)
        result["sharpe"] = mean_r / std_r * np.sqrt(252) if std_r > 0 else 0

        # Sortino (downside deviation only)
        downside = returns[returns < 0]
        downside_std = np.std(downside) if len(downside) > 0 else 0
        result["sortino"] = mean_r / downside_std * np.sqrt(252) if downside_std > 0 else 0

        # Calmar = annualized return / max drawdown
        total_return_pct = result["total_pnl"] / initial * 100
        result["calmar"] = total_return_pct / result["max_drawdown"] if result["max_drawdown"] > 0 else 0
    else:
        result["sharpe"] = result["sortino"] = result["calmar"] = 0

    return result


def _max_drawdown() -> float:
    """Compute max drawdown % from equity curve."""
    curve = st.session_state.equity_curve
    if not curve:
        return 0
    values = [e["value"] for e in curve]
    peak = values[0]
    max_dd = 0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return round(max_dd, 2)


def current_drawdown() -> float:
    """Current drawdown % from peak."""
    curve = st.session_state.equity_curve
    if not curve:
        return 0
    values = [e["value"] for e in curve]
    peak = max(values)
    current = values[-1]
    return round((peak - current) / peak * 100, 2) if peak > 0 else 0


def _max_streak(pnls: list[float], positive: bool = True) -> int:
    """Count max consecutive wins or losses."""
    max_s = 0
    current = 0
    for p in pnls:
        if (positive and p > 0) or (not positive and p < 0):
            current += 1
            max_s = max(max_s, current)
        else:
            current = 0
    return max_s


# ──────────────────────────────────────────────────────────────
#  Risk metrics
# ──────────────────────────────────────────────────────────────

def compute_var(confidence: float = 0.95) -> dict:
    """
    Value at Risk — historical and parametric.
    Based on daily P&L from equity curve.
    """
    curve = st.session_state.equity_curve
    if len(curve) < 3:
        return {"historical_var": 0, "parametric_var": 0, "cvar": 0}

    values = [e["value"] for e in curve]
    returns = pd.Series(values).pct_change().dropna()

    if len(returns) < 2:
        return {"historical_var": 0, "parametric_var": 0, "cvar": 0}

    portfolio_value = values[-1]

    # Historical VaR
    hist_var = np.percentile(returns, (1 - confidence) * 100) * portfolio_value

    # Parametric VaR (assumes normal distribution)
    z = sp_stats.norm.ppf(1 - confidence)
    param_var = (returns.mean() + z * returns.std()) * portfolio_value

    # Conditional VaR (Expected Shortfall)
    threshold = np.percentile(returns, (1 - confidence) * 100)
    tail_returns = returns[returns <= threshold]
    cvar = tail_returns.mean() * portfolio_value if len(tail_returns) > 0 else hist_var

    return {
        "historical_var": round(abs(hist_var), 2),
        "parametric_var": round(abs(param_var), 2),
        "cvar": round(abs(cvar), 2),
    }


def compute_portfolio_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Portfolio beta relative to benchmark."""
    if len(portfolio_returns) < 5 or len(benchmark_returns) < 5:
        return 0.0
    # Align lengths
    min_len = min(len(portfolio_returns), len(benchmark_returns))
    pr = portfolio_returns.iloc[-min_len:].values
    br = benchmark_returns.iloc[-min_len:].values
    cov = np.cov(pr, br)
    if cov[1, 1] == 0:
        return 0.0
    return round(cov[0, 1] / cov[1, 1], 3)


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Kelly % = W - (1-W)/R where R = avg_win/avg_loss."""
    if avg_loss == 0 or win_rate <= 0:
        return 0
    r = avg_win / abs(avg_loss)
    kelly = win_rate - (1 - win_rate) / r
    return max(0, round(kelly * 100, 2))


def get_trade_distribution() -> dict:
    """Trade P&L distribution stats."""
    pnls = [t["pnl"] for t in st.session_state.history if isinstance(t.get("pnl"), (int, float))]
    if not pnls:
        return {"mean": 0, "median": 0, "std": 0, "skew": 0, "kurtosis": 0}
    s = pd.Series(pnls)
    return {
        "mean": round(s.mean(), 2),
        "median": round(s.median(), 2),
        "std": round(s.std(), 2),
        "skew": round(s.skew(), 2),
        "kurtosis": round(s.kurtosis(), 2),
    }
