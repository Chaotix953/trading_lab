"""
Global configuration, constants, and default values for Trading Lab Pro.
"""

from dataclasses import dataclass, field
from datetime import datetime

# ── App metadata ──────────────────────────────────────────────
APP_NAME = "Trading Lab Pro"
APP_VERSION = "2.0.0"
APP_ICON = "🏦"

# ── Period / Interval maps ────────────────────────────────────
PERIOD_MAP = {
    "1D": "1d", "5D": "5d", "1M": "1mo", "3M": "3mo",
    "6M": "6mo", "1Y": "1y", "2Y": "2y", "5Y": "5y", "Max": "max",
}

INTERVAL_MAP = {
    "1min": "1m", "2min": "2m", "5min": "5m", "15min": "15m",
    "30min": "30m", "1H": "1h", "1D": "1d", "1W": "1wk", "1M": "1mo",
}

# Valid period-interval combos (yfinance constraints)
VALID_COMBOS: dict[str, list[str]] = {
    "1m":  ["1D"],
    "2m":  ["1D", "5D"],
    "5m":  ["1D", "5D", "1M"],
    "15m": ["1D", "5D", "1M"],
    "30m": ["1D", "5D", "1M"],
    "1h":  ["1D", "5D", "1M", "3M", "6M"],
    "1d":  ["1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "5Y", "Max"],
    "1wk": ["1M", "3M", "6M", "1Y", "2Y", "5Y", "Max"],
    "1mo": ["3M", "6M", "1Y", "2Y", "5Y", "Max"],
}

# ── Trading defaults ─────────────────────────────────────────
DEFAULT_BALANCE = 100_000.0
DEFAULT_COMMISSION_RATE = 0.001        # 0.1%
DEFAULT_SLIPPAGE_PCT = 0.0005          # 0.05%
DEFAULT_SPREAD_PCT = 0.0002            # 0.02%
SHORT_MARGIN_RATIO = 1.5               # 150% margin
MARGIN_CALL_THRESHOLD = 0.25           # 25% equity left → margin call

# ── Watchlist ─────────────────────────────────────────────────
DEFAULT_WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]

# ── Scanner universes ─────────────────────────────────────────
SCANNER_SP500_SAMPLE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "JNJ", "UNH", "HD", "PG", "MA", "DIS", "PYPL", "NFLX",
    "ADBE", "CRM", "INTC", "CSCO", "PFE", "ABT", "TMO", "NKE", "KO",
    "PEP", "MRK", "XOM", "CVX", "BAC", "WMT", "COST", "AMD", "QCOM",
]

# ── Sector colors ─────────────────────────────────────────────
SECTOR_COLORS = {
    "Technology":          "#2196f3",
    "Healthcare":          "#4caf50",
    "Financial Services":  "#ff9800",
    "Consumer Cyclical":   "#e91e63",
    "Communication Services": "#9c27b0",
    "Consumer Defensive":  "#00bcd4",
    "Energy":              "#f44336",
    "Industrials":         "#795548",
    "Basic Materials":     "#607d8b",
    "Real Estate":         "#ffeb3b",
    "Utilities":           "#8bc34a",
    "Other":               "#78909c",
}

# ── Chart colors ──────────────────────────────────────────────
BULL_COLOR = "#26a69a"
BEAR_COLOR = "#ef5350"
ACCENT_BLUE = "#2196f3"
ACCENT_ORANGE = "#ff9800"
ACCENT_PURPLE = "#ab47bc"
ACCENT_CYAN = "#00bcd4"
PROFIT_GREEN = "#00c853"
LOSS_RED = "#ff1744"

# ── Persistence ───────────────────────────────────────────────
DATA_DIR = "data"
SAVE_FILE = f"{DATA_DIR}/lab_state.json"
BACKUP_PREFIX = f"{DATA_DIR}/backup_"


@dataclass
class SessionDefaults:
    """All session-state default values in one place."""
    balance: float = DEFAULT_BALANCE
    initial_balance: float = DEFAULT_BALANCE
    portfolio: dict = field(default_factory=dict)
    history: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)
    watchlist: list = field(default_factory=lambda: list(DEFAULT_WATCHLIST))
    pending_orders: list = field(default_factory=list)
    alerts: list = field(default_factory=list)
    commission_rate: float = DEFAULT_COMMISSION_RATE
    slippage_pct: float = DEFAULT_SLIPPAGE_PCT
    spread_pct: float = DEFAULT_SPREAD_PCT
    trade_notes: dict = field(default_factory=dict)   # {trade_index: {note, tags, rating}}
    goals: dict = field(default_factory=lambda: {
        "daily_max_trades": 20,
        "daily_max_loss": 5000.0,
        "monthly_target_pnl": 10000.0,
        "max_drawdown_pct": 15.0,
    })
    accounts: dict = field(default_factory=lambda: {"Default": True})
    active_account: str = "Default"
