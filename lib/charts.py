"""
Chart builders — reusable Plotly figure factories.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lib import indicators as ind
from lib.config import BULL_COLOR, BEAR_COLOR, PROFIT_GREEN, LOSS_RED, SECTOR_COLORS


# ──────────────────────────────────────────────────────────────
#  Main price chart
# ──────────────────────────────────────────────────────────────

def build_main_chart(
    df: pd.DataFrame,
    overlays: dict,
    panels: dict,
    support_resistance: bool = False,
    fib_levels: bool = False,
    pivot: bool = False,
) -> go.Figure:
    """
    Build the main candlestick chart with overlays and sub-panels.

    overlays: dict of indicator flags & params
    panels: dict of {volume, rsi, macd, stoch_rsi, adx, obv, mfi, ...}
    """
    num_rows = 1
    row_heights = [0.55]
    subplot_titles = [""]

    panel_order = []
    for panel_name in ["volume", "rsi", "macd", "stoch_rsi", "adx", "obv", "mfi"]:
        if panels.get(panel_name):
            num_rows += 1
            panel_order.append(panel_name)
            row_heights.append(0.12 if panel_name == "volume" else 0.15)
            subplot_titles.append(panel_name.upper().replace("_", " "))

    # Normalize heights
    total = sum(row_heights)
    row_heights = [h / total for h in row_heights]

    fig = make_subplots(
        rows=num_rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # ── Candlestick ───────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color=BULL_COLOR,
        decreasing_line_color=BEAR_COLOR,
    ), row=1, col=1)

    # ── Overlays ──────────────────────────────────────────────
    if overlays.get("sma"):
        for p in overlays["sma"]:
            fig.add_trace(go.Scatter(
                x=df.index, y=ind.sma(df, p),
                name=f"SMA {p}", line=dict(width=1.3),
            ), row=1, col=1)

    if overlays.get("ema"):
        for p in overlays["ema"]:
            fig.add_trace(go.Scatter(
                x=df.index, y=ind.ema(df, p),
                name=f"EMA {p}", line=dict(width=1.3, dash="dot"),
            ), row=1, col=1)

    if overlays.get("bollinger"):
        upper, mid, lower = ind.bollinger_bands(df)
        fig.add_trace(go.Scatter(x=df.index, y=upper, name="BB+",
            line=dict(width=1, color="gray", dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=lower, name="BB-",
            line=dict(width=1, color="gray", dash="dot"),
            fill="tonexty", fillcolor="rgba(128,128,128,0.08)"), row=1, col=1)

    if overlays.get("vwap"):
        fig.add_trace(go.Scatter(x=df.index, y=ind.vwap(df),
            name="VWAP", line=dict(width=1.5, color="purple")), row=1, col=1)

    if overlays.get("ichimoku"):
        tenkan, kijun, senkou_a, senkou_b, _ = ind.ichimoku(df)
        fig.add_trace(go.Scatter(x=df.index, y=tenkan, name="Tenkan",
            line=dict(width=1, color="#e91e63")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=kijun, name="Kijun",
            line=dict(width=1, color="#2196f3")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=senkou_a, name="Senkou A",
            line=dict(width=0.5, color="green")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=senkou_b, name="Senkou B",
            line=dict(width=0.5, color="red"),
            fill="tonexty", fillcolor="rgba(0,255,0,0.05)"), row=1, col=1)

    if overlays.get("keltner"):
        ku, km, kl = ind.keltner_channels(df)
        fig.add_trace(go.Scatter(x=df.index, y=ku, name="Keltner+",
            line=dict(width=1, color="#ff9800", dash="dash")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=kl, name="Keltner-",
            line=dict(width=1, color="#ff9800", dash="dash")), row=1, col=1)

    # Support / Resistance
    if support_resistance:
        supports, resistances = ind.find_support_resistance(df)
        for s in supports:
            fig.add_hline(y=s, line_dash="dash", line_color="#4caf50",
                          opacity=0.4, annotation_text=f"S: {s:.2f}", row=1, col=1)
        for r in resistances:
            fig.add_hline(y=r, line_dash="dash", line_color="#f44336",
                          opacity=0.4, annotation_text=f"R: {r:.2f}", row=1, col=1)

    # Fibonacci
    if fib_levels:
        high = df["High"].max()
        low = df["Low"].min()
        fibs = ind.fibonacci_retracement(high, low)
        fib_colors = ["#f44336", "#ff9800", "#ffeb3b", "#4caf50", "#2196f3", "#9c27b0", "#607d8b"]
        for (label, level), color in zip(fibs.items(), fib_colors):
            fig.add_hline(y=level, line_dash="dot", line_color=color, opacity=0.5,
                          annotation_text=f"Fib {label}: {level}", row=1, col=1)

    # Pivot points
    if pivot:
        pivots = ind.pivot_points(df)
        for label, level in pivots.items():
            color = "#4caf50" if label.startswith("S") else "#f44336" if label.startswith("R") else "#ffffff"
            fig.add_hline(y=level, line_dash="dot", line_color=color,
                          opacity=0.3, annotation_text=f"{label}: {level}", row=1, col=1)

    # ── Sub-panels ────────────────────────────────────────────
    current_row = 2

    for panel_name in panel_order:
        if panel_name == "volume":
            colors = [BULL_COLOR if c >= o else BEAR_COLOR for o, c in zip(df["Open"], df["Close"])]
            fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                marker_color=colors, opacity=0.7), row=current_row, col=1)
            # Volume SMA
            fig.add_trace(go.Scatter(x=df.index, y=ind.volume_sma(df, 20),
                name="Vol SMA 20", line=dict(width=1, color="yellow")), row=current_row, col=1)

        elif panel_name == "rsi":
            rsi_val = ind.rsi(df)
            fig.add_trace(go.Scatter(x=df.index, y=rsi_val, name="RSI",
                line=dict(width=1.5, color="#ab47bc")), row=current_row, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red", opacity=0.5, row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", opacity=0.5, row=current_row, col=1)
            fig.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.04, row=current_row, col=1)

        elif panel_name == "macd":
            ml, sl, hist = ind.macd(df)
            fig.add_trace(go.Scatter(x=df.index, y=ml, name="MACD",
                line=dict(width=1.5, color="#2196f3")), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=sl, name="Signal",
                line=dict(width=1.5, color="#ff9800")), row=current_row, col=1)
            colors_h = [BULL_COLOR if v >= 0 else BEAR_COLOR for v in hist]
            fig.add_trace(go.Bar(x=df.index, y=hist, name="Histogram",
                marker_color=colors_h, opacity=0.6), row=current_row, col=1)

        elif panel_name == "stoch_rsi":
            k, d = ind.stochastic_rsi(df)
            fig.add_trace(go.Scatter(x=df.index, y=k, name="%K",
                line=dict(width=1.3, color="#2196f3")), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=d, name="%D",
                line=dict(width=1.3, color="#ff9800")), row=current_row, col=1)
            fig.add_hline(y=80, line_dash="dot", line_color="red", opacity=0.4, row=current_row, col=1)
            fig.add_hline(y=20, line_dash="dot", line_color="green", opacity=0.4, row=current_row, col=1)

        elif panel_name == "adx":
            adx_val, plus_di, minus_di = ind.adx(df)
            fig.add_trace(go.Scatter(x=df.index, y=adx_val, name="ADX",
                line=dict(width=2, color="white")), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=plus_di, name="+DI",
                line=dict(width=1, color=BULL_COLOR)), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=minus_di, name="-DI",
                line=dict(width=1, color=BEAR_COLOR)), row=current_row, col=1)
            fig.add_hline(y=25, line_dash="dot", line_color="gray", opacity=0.3, row=current_row, col=1)

        elif panel_name == "obv":
            fig.add_trace(go.Scatter(x=df.index, y=ind.obv(df), name="OBV",
                line=dict(width=1.5, color="#00bcd4")), row=current_row, col=1)

        elif panel_name == "mfi":
            fig.add_trace(go.Scatter(x=df.index, y=ind.mfi(df), name="MFI",
                line=dict(width=1.5, color="#ffeb3b")), row=current_row, col=1)
            fig.add_hline(y=80, line_dash="dot", line_color="red", opacity=0.4, row=current_row, col=1)
            fig.add_hline(y=20, line_dash="dot", line_color="green", opacity=0.4, row=current_row, col=1)

        current_row += 1

    fig.update_layout(
        height=300 + 180 * num_rows,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=True,
        hovermode="x unified",
    )

    return fig


# ──────────────────────────────────────────────────────────────
#  Utility charts
# ──────────────────────────────────────────────────────────────

def equity_curve_chart(
    equity_data: list[dict],
    initial_balance: float,
    benchmark_data: pd.DataFrame | None = None,
) -> go.Figure:
    """Equity curve with optional benchmark comparison."""
    fig = go.Figure()

    if equity_data:
        df_eq = pd.DataFrame(equity_data)
        fig.add_trace(go.Scatter(
            x=df_eq["time"], y=df_eq["value"],
            mode="lines", name="Portfolio",
            fill="tozeroy", fillcolor="rgba(0,200,83,0.1)",
            line=dict(color=PROFIT_GREEN, width=2),
        ))

    fig.add_hline(y=initial_balance, line_dash="dot",
        line_color="white", opacity=0.5, annotation_text="Initial Capital")

    if benchmark_data is not None and not benchmark_data.empty:
        # Normalize benchmark to same starting value
        bench_norm = benchmark_data["Close"] / benchmark_data["Close"].iloc[0] * initial_balance
        fig.add_trace(go.Scatter(
            x=benchmark_data.index, y=bench_norm,
            mode="lines", name="S&P 500 (SPY)",
            line=dict(color="#ff9800", width=1.5, dash="dash"),
        ))

    fig.update_layout(
        height=350, template="plotly_dark",
        margin=dict(l=0, r=0, t=30, b=0),
        title="Equity Curve",
        hovermode="x unified",
    )
    return fig


def pnl_distribution_chart(pnls: list[float]) -> go.Figure:
    """Bar chart of P&L per trade."""
    fig = go.Figure()
    colors = [PROFIT_GREEN if p > 0 else LOSS_RED for p in pnls]
    fig.add_trace(go.Bar(
        x=list(range(1, len(pnls) + 1)), y=pnls,
        marker_color=colors, name="P&L per Trade",
    ))
    fig.add_hline(y=0, line_color="white", opacity=0.3)
    fig.update_layout(
        height=280, template="plotly_dark",
        margin=dict(l=0, r=0, t=30, b=0),
        title="P&L Distribution",
        xaxis_title="Trade #", yaxis_title="P&L ($)",
    )
    return fig


def allocation_pie(portfolio: dict, balance: float) -> go.Figure:
    """Portfolio allocation donut chart."""
    labels = []
    values = []
    for t, d in portfolio.items():
        labels.append(t)
        values.append(d["qty"] * d["avg_price"])
    labels.append("Cash")
    values.append(balance)

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.4,
        marker=dict(colors=[
            "#2196f3", "#ff9800", "#4caf50", "#e91e63",
            "#9c27b0", "#00bcd4", "#ffeb3b", "#795548",
        ] + ["#78909c"]),
        textinfo="label+percent",
    )])
    fig.update_layout(
        height=400, template="plotly_dark",
        margin=dict(l=0, r=0, t=30, b=0),
        title="Portfolio Allocation",
    )
    return fig


def sector_pie(sector_data: dict[str, float]) -> go.Figure:
    """Sector exposure pie chart."""
    fig = go.Figure(data=[go.Pie(
        labels=list(sector_data.keys()),
        values=list(sector_data.values()),
        hole=0.4,
        marker=dict(colors=[SECTOR_COLORS.get(s, "#78909c") for s in sector_data.keys()]),
        textinfo="label+percent",
    )])
    fig.update_layout(
        height=400, template="plotly_dark",
        margin=dict(l=0, r=0, t=30, b=0),
        title="Sector Exposure",
    )
    return fig


def correlation_heatmap(corr_matrix: pd.DataFrame) -> go.Figure:
    """Correlation heatmap."""
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        colorscale="RdBu_r",
        zmid=0,
        text=np.round(corr_matrix.values, 2),
        texttemplate="%{text}",
        textfont={"size": 11},
        hovertemplate="<b>%{x}</b> vs <b>%{y}</b><br>Correlation: %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        height=500, template="plotly_dark",
        margin=dict(l=0, r=0, t=30, b=0),
        title="Correlation Matrix",
    )
    return fig


def backtest_chart(
    dates, equity_curve: list[float], buy_hold_curve: list[float] | None = None,
    trades: list[dict] | None = None,
) -> go.Figure:
    """Backtest equity curve with trade markers."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=equity_curve,
        mode="lines", name="Strategy",
        fill="tozeroy", fillcolor="rgba(33,150,243,0.1)",
        line=dict(color="#2196f3", width=2),
    ))

    if buy_hold_curve:
        fig.add_trace(go.Scatter(
            x=dates, y=buy_hold_curve,
            mode="lines", name="Buy & Hold",
            line=dict(color="#ff9800", width=1.5, dash="dash"),
        ))

    if trades:
        buys = [t for t in trades if t["action"] == "Buy"]
        sells = [t for t in trades if t["action"].startswith("Sell")]
        if buys:
            fig.add_trace(go.Scatter(
                x=[t["date"] for t in buys],
                y=[t["price"] for t in buys],
                mode="markers", name="Buy",
                marker=dict(symbol="triangle-up", size=10, color=BULL_COLOR),
                yaxis="y2",
            ))
        if sells:
            fig.add_trace(go.Scatter(
                x=[t["date"] for t in sells],
                y=[t["price"] for t in sells],
                mode="markers", name="Sell",
                marker=dict(symbol="triangle-down", size=10, color=BEAR_COLOR),
                yaxis="y2",
            ))

    fig.update_layout(
        height=450, template="plotly_dark",
        margin=dict(l=0, r=0, t=30, b=0),
        title="Backtest Results",
        hovermode="x unified",
    )
    return fig


def multi_timeframe_chart(
    data_dict: dict[str, pd.DataFrame],
) -> go.Figure:
    """Side-by-side candlestick charts for multiple timeframes."""
    n = len(data_dict)
    fig = make_subplots(rows=1, cols=n, shared_yaxes=True,
                         subplot_titles=list(data_dict.keys()))

    for i, (label, df) in enumerate(data_dict.items(), 1):
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"],
            name=label, increasing_line_color=BULL_COLOR,
            decreasing_line_color=BEAR_COLOR,
        ), row=1, col=i)

    fig.update_layout(
        height=400, template="plotly_dark",
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
        xaxis_rangeslider_visible=False,
    )
    # Disable all range sliders
    for i in range(1, n + 1):
        fig.update_xaxes(rangeslider_visible=False, row=1, col=i)

    return fig
