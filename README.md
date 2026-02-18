# 🏦 Trading Lab Pro

**Professional Paper Trading Simulator** — Practice trading with real market data, zero financial risk.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-red)
![License](https://img.shields.io/badge/License-MIT-green)

A full-featured paper trading platform built with Streamlit and yfinance. Designed for traders who want to test strategies, practice execution, and analyze performance — all with realistic market simulation.

---

## ✨ Features

### 📊 Trading
- **Market orders** with realistic Gaussian slippage and bid-ask spread simulation
- **Limit / Stop orders** — Limit Buy, Limit Sell, Stop-Loss, Take-Profit
- **Trailing Stop** — percentage-based or fixed-dollar trailing
- **OCO Bracket orders** — linked Stop-Loss + Take-Profit (one triggers, other cancels)
- **Short Selling** with margin tracking and margin call warnings
- **Options Trading** — Full support with Black-Scholes pricing, Greeks (Δ, Γ, Θ, ν, ρ)
- **Options Chain** viewer with strike filtering and volatility analysis
- **Real-time data** — Intraday minute-level pricing with optimized yfinance calls
- **Decimal Precision** — 28-digit financial accuracy to eliminate rounding errors
- **Commission simulation** — configurable per-trade costs
- **Trade notes & tagging** — annotate every trade for journaling

### 📈 Analysis & Performance
- **30+ metrics**: Win Rate, Profit Factor, Sharpe, Sortino, Calmar, Kelly %, Expectancy, Max Drawdown, etc.
- **Equity curve** with S&P 500 benchmark comparison
- **P&L distribution** chart and statistical analysis (mean, median, skew, kurtosis)
- **Value at Risk (VaR)** — Historical, Parametric, and Conditional VaR at 95% and 99%
- **Portfolio Beta** relative to benchmark
- **Sector exposure** breakdown
- **Correlation heatmap** across watchlist
- **Long vs Short P&L** breakdown
- **Win/Loss streak tracking**

### 📐 Technical Indicators (20+)
| Trend | Momentum | Volatility | Volume |
|-------|----------|------------|--------|
| SMA (multi) | RSI | Bollinger Bands | Volume + SMA |
| EMA (multi) | Stochastic RSI | ATR | OBV |
| VWAP | MACD | Keltner Channels | MFI |
| Ichimoku Cloud | CCI | — | — |
| SuperTrend | Williams %R | — | — |
| — | ADX (+DI/-DI) | — | — |

Plus: **Support/Resistance detection**, **Fibonacci retracement**, **Pivot Points**

### 🔄 Backtesting Engine
- **5 built-in strategies**: SMA Crossover, RSI Mean Reversion, MACD Cross, Bollinger Bounce, Combined Momentum
- Configurable parameters for each strategy
- Optional Stop-Loss / Take-Profit in backtest
- **Intra-bar execution** — Eliminates Look-Ahead Bias using OHLC data correctly
  - Entry orders executed on Open price
  - Stop-Loss triggered on Low price
  - Take-Profit triggered on High price
  - Exit orders at Close price
- **Strategy comparison mode** — test all strategies on the same data
- Visual trade markers on equity curve
- Alpha vs Buy & Hold calculation

### 🔍 Market Scanner
- Screen stocks by technical criteria (RSI, SMA, Volume surge, MACD, Bollinger)
- Pre-built S&P 500 sample universe
- Scan your watchlist or custom ticker lists
- One-click add results to watchlist

### 🎯 Risk Management
- **Position sizing calculator** with Risk/Reward ratio
- **Kelly Criterion** optimal sizing
- **Margin tracking** for short positions
- **Trading discipline goals**: max trades/day, max daily loss, drawdown limit, monthly target
- Real-time goal monitoring with warnings

### 💾 Persistence
- Save/Load sessions as JSON
- Create timestamped backups
- Export/Import state files
- CSV export for trade journal

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation with uv

```bash
# Clone the repo
git clone https://github.com/yourusername/trading-lab-pro.git
cd trading-lab-pro

# Install dependencies with uv
uv sync

# Run the app
uv run streamlit run app.py
```

### Installation with pip

```bash
# Clone the repo
git clone https://github.com/yourusername/trading-lab-pro.git
cd trading-lab-pro

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e .

# Run the app
streamlit run app.py
```

The app will open at **http://localhost:8501**

---

## 📁 Project Structure

```
trading-lab-pro/
├── app.py                          # Main Dashboard
├── pages/
│   ├── 1_⚡_Trading.py             # Chart + Order entry
│   ├── 2_📈_Analysis.py            # Performance & Risk analytics
│   ├── 3_🔄_Backtester.py          # Strategy backtesting
│   ├── 4_🔍_Scanner.py             # Market screening
│   └── 5_⚙️_Settings.py            # Configuration & persistence
├── lib/
│   ├── __init__.py
│   ├── config.py                   # Constants & defaults
│   ├── state.py                    # Session state management
│   ├── data_fetcher.py             # Market data (yfinance wrapper)
│   ├── trading_engine.py           # Order execution engine (Decimal-based)
│   ├── orders.py                   # Pending order management
│   ├── indicators.py               # 20+ technical indicators
│   ├── performance.py              # Performance analytics
│   ├── backtester.py               # Backtesting engine (no Look-Ahead Bias)
│   ├── scanner.py                  # Market scanner & alerts
│   ├── options_pricing.py          # Black-Scholes option pricing & Greeks
│   ├── charts.py                   # Plotly chart factories
│   └── styles.py                   # CSS styling
├── data/                           # Local saves & backups
├── .streamlit/
│   └── config.toml                 # Streamlit theme
├── pyproject.toml                  # Project config (uv/pip)
├── .gitignore
└── README.md
```

---

## 🎮 Usage Guide

### Getting Started
1. **Dashboard** — Overview of cash, portfolio, watchlist, and quick stats
2. **Trading** — Select a ticker, analyze the chart, and place orders
3. **Analysis** — Deep dive into your performance after some trades
4. **Backtester** — Test a strategy before risking your paper capital
5. **Scanner** — Find opportunities across the market
6. **Settings** — Adjust commissions, slippage, goals, and save your progress

### Trading Workflow
1. Search for a ticker (e.g., `AAPL`, `BTC-USD`, `EURUSD=X`)
2. Analyze the chart with your preferred indicators
3. Use the **Position Size Calculator** to determine optimal quantity
4. Place an order (Market, Limit, or OCO Bracket)
5. Monitor in the Portfolio tab
6. Review performance in Analysis

### Supported Instruments
- **US Stocks**: AAPL, MSFT, GOOGL, TSLA, etc.
- **Crypto**: BTC-USD, ETH-USD, SOL-USD, etc.
- **Forex**: EURUSD=X, GBPUSD=X, USDJPY=X, etc.
- **ETFs**: SPY, QQQ, IWM, etc.
- **Options chains**: Full support with Black-Scholes pricing and Greeks

---

## 🎓 Advanced Features

### Options Pricing & Analysis
- **Black-Scholes Model** — Academic-grade option pricing
- **Greeks Calculation**:
  - **Delta (Δ)** — Price sensitivity (0-1 for calls, -1-0 for puts)
  - **Gamma (Γ)** — Delta acceleration and risk concentration
  - **Theta (Θ)** — Daily time decay per percentage point
  - **Vega (ν)** — Volatility sensitivity (per 1% change)
  - **Rho (ρ)** — Interest rate sensitivity (per 1% change)
- **Intrinsic vs Time Value** — Understand option decomposition
- **Implied Volatility display** — From market data
- **Real-time option chain** with strike filtering (±15% around spot)

### Financial Precision
- **Decimal Arithmetic** — 28-digit precision eliminates floating-point errors
- **Realistic Slippage** — Gaussian distribution N(0, 0.05%) simulates market microstructure
- **Market Impact** — Fill prices reflect realistic bid-ask dynamics
- **Margin Calculation** — 50% requirement for short selling

---

## Supported Instruments

### Simulation Realism
| Parameter | Default | Description |
|-----------|---------|-------------|
| Commission | 0.1% | Per-trade fee |
| Slippage | 0.05% | Random price impact |
| Spread | 0.02% | Bid-ask spread simulation |
| Short Margin | 150% | Required margin for shorts |

### Trading Goals
| Goal | Default | Description |
|------|---------|-------------|
| Max trades/day | 20 | Prevents overtrading |
| Max daily loss | $5,000 | Daily stop-loss |
| Monthly target | $10,000 | P&L goal |
| Max drawdown | 15% | Portfolio risk limit |

---

## 🤝 Contributing

Contributions are welcome! Here are some areas where help is appreciated:

- [ ] Market replay mode (bar-by-bar historical replay)
- [ ] Additional strategies for backtester
- [ ] Stochastic volatility models (Heston, SABR)
- [ ] Monte Carlo option pricing alternative to Black-Scholes
- [ ] Multi-account support
- [ ] More data sources (alternatives to yfinance)
- [ ] Unit tests
- [ ] Localization (i18n)

### Development Setup

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest
```

---

## ⚠️ Disclaimer

This is a **paper trading simulator** for educational purposes only. It does not involve real money or real market execution. Past simulated performance does not guarantee future results. Always do your own research before trading with real capital.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io/) — The UI framework
- [yfinance](https://github.com/ranaroussi/yfinance) — Market data
- [Plotly](https://plotly.com/) — Interactive charts
- [ta](https://github.com/bukosabino/ta) — Technical analysis library
