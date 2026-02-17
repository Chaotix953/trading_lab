"""
Trading engine — execute trades with realistic simulation features:
  • Commissions
  • Slippage
  • Bid-ask spread
  • Market / Limit / Stop / Trailing / OCO orders
  • Long & Short positions
"""

from __future__ import annotations

import random
from datetime import datetime

import streamlit as st

from lib.config import SHORT_MARGIN_RATIO, MARGIN_CALL_THRESHOLD


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _commission(amount: float) -> float:
    return amount * st.session_state.get("commission_rate", 0.001)


def _apply_slippage(price: float, side: str) -> float:
    """Add random slippage: positive for buys, negative for sells."""
    slip_pct = st.session_state.get("slippage_pct", 0.0005)
    if slip_pct == 0:
        return price
    slip = price * random.uniform(0, slip_pct)
    return price + slip if side == "buy" else price - slip


def _apply_spread(price: float, side: str) -> float:
    """Shift price by half-spread."""
    spread_pct = st.session_state.get("spread_pct", 0.0002)
    half = price * spread_pct / 2
    return price + half if side == "buy" else price - half


def simulate_fill_price(price: float, side: str) -> float:
    """Return a realistic fill price after spread + slippage."""
    p = _apply_spread(price, side)
    p = _apply_slippage(p, side)
    return round(p, 4)


# ──────────────────────────────────────────────────────────────
#  Core execution
# ──────────────────────────────────────────────────────────────

def execute_trade(
    ticker: str,
    action: str,       # Buy | Sell | Short | Cover
    quantity: int,
    raw_price: float,
    asset_type: str = "Stock",
    note: str = "",
    tags: list[str] | None = None,
) -> bool:
    """
    Execute an order. Returns True on success.
    """
    side_map = {"Buy": "buy", "Sell": "sell", "Short": "sell", "Cover": "buy"}
    fill_price = simulate_fill_price(raw_price, side_map.get(action, "buy"))
    gross = quantity * fill_price
    commission = _commission(gross)

    success = False

    if action == "Buy":
        total_cost = gross + commission
        if st.session_state.balance >= total_cost:
            st.session_state.balance -= total_cost
            _add_to_portfolio(ticker, quantity, fill_price, asset_type, "long")
            success = True
            st.success(
                f"✅ BUY {quantity} × {ticker} @ ${fill_price:.2f} "
                f"| Commission: ${commission:.2f} | Slippage-adjusted"
            )
        else:
            st.error(
                f"Insufficient funds: need ${total_cost:,.2f}, "
                f"available ${st.session_state.balance:,.2f}"
            )

    elif action == "Sell":
        avg_price = _get_avg_price(ticker)
        if ticker in st.session_state.portfolio and st.session_state.portfolio[ticker]["qty"] >= quantity:
            revenue = gross - commission
            st.session_state.balance += revenue
            pnl = (fill_price - avg_price) * quantity - commission
            _remove_from_portfolio(ticker, quantity)
            success = True
            color = "success" if pnl >= 0 else "warning"
            getattr(st, color)(
                f"✅ SELL {quantity} × {ticker} @ ${fill_price:.2f} "
                f"| P&L: ${pnl:+,.2f} | Commission: ${commission:.2f}"
            )
        else:
            st.error("Insufficient shares in portfolio!")

    elif action == "Short":
        margin_required = gross * SHORT_MARGIN_RATIO
        if st.session_state.balance >= margin_required:
            st.session_state.balance += gross - commission
            key = f"{ticker}_SHORT"
            _add_to_portfolio(key, quantity, fill_price, asset_type, "short")
            success = True
            st.success(
                f"✅ SHORT {quantity} × {ticker} @ ${fill_price:.2f} "
                f"| Margin reserved: ${margin_required:,.2f}"
            )
        else:
            st.error(f"Insufficient margin: need ${margin_required:,.2f}")

    elif action == "Cover":
        key = f"{ticker}_SHORT"
        avg_price = _get_avg_price(key)
        if key in st.session_state.portfolio and st.session_state.portfolio[key]["qty"] >= quantity:
            total_cost = gross + commission
            st.session_state.balance -= total_cost
            pnl = (avg_price - fill_price) * quantity - commission
            _remove_from_portfolio(key, quantity)
            success = True
            color = "success" if pnl >= 0 else "warning"
            getattr(st, color)(
                f"✅ COVER {quantity} × {ticker} @ ${fill_price:.2f} "
                f"| P&L: ${pnl:+,.2f}"
            )
        else:
            st.error("No short position to cover!")

    if success:
        _log_trade(ticker, action, quantity, fill_price, raw_price, asset_type, commission, note, tags)
        _update_equity_curve()
        _check_goals()

    return success


# ──────────────────────────────────────────────────────────────
#  Portfolio helpers
# ──────────────────────────────────────────────────────────────

def _get_avg_price(key: str) -> float:
    """Get average price BEFORE modifying portfolio (bug fix #2)."""
    pos = st.session_state.portfolio.get(key)
    return pos["avg_price"] if pos else 0.0


def _add_to_portfolio(key: str, qty: int, price: float, asset_type: str, side: str):
    pf = st.session_state.portfolio
    if key in pf:
        old = pf[key]
        new_qty = old["qty"] + qty
        new_avg = ((old["qty"] * old["avg_price"]) + (qty * price)) / new_qty
        pf[key].update({"qty": new_qty, "avg_price": round(new_avg, 4)})
    else:
        pf[key] = {"qty": qty, "avg_price": round(price, 4), "type": asset_type, "side": side}


def _remove_from_portfolio(key: str, qty: int):
    pf = st.session_state.portfolio
    if key in pf:
        pf[key]["qty"] -= qty
        if pf[key]["qty"] <= 0:
            del pf[key]


def _log_trade(
    ticker: str, action: str, qty: int, fill_price: float, raw_price: float,
    asset_type: str, commission: float, note: str = "", tags: list | None = None,
):
    """Append trade to history with realized P&L computation."""
    pnl = None

    # Compute realized P&L for closing trades
    if action == "Sell":
        key = ticker
        pos = st.session_state.portfolio.get(key)
        if pos:
            pnl = (fill_price - pos["avg_price"]) * qty - commission
    elif action == "Cover":
        key = f"{ticker}_SHORT"
        pos = st.session_state.portfolio.get(key)
        if pos:
            pnl = (pos["avg_price"] - fill_price) * qty - commission

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticker": ticker,
        "action": action,
        "qty": qty,
        "fill_price": round(fill_price, 4),
        "raw_price": round(raw_price, 4),
        "amount": round(qty * fill_price, 2),
        "commission": round(commission, 2),
        "slippage": round(abs(fill_price - raw_price) * qty, 2),
        "pnl": round(pnl, 2) if pnl is not None else None,
        "type": asset_type,
        "note": note,
        "tags": tags or [],
    }
    st.session_state.history.append(entry)

    # Save note/tags for journal
    idx = len(st.session_state.history) - 1
    if note or tags:
        st.session_state.trade_notes[str(idx)] = {"note": note, "tags": tags or []}


def _update_equity_curve():
    """Snapshot total portfolio value (uses avg_price as approximation)."""
    total = st.session_state.balance
    for _key, pos in st.session_state.portfolio.items():
        total += pos["qty"] * pos["avg_price"]
    st.session_state.equity_curve.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "value": round(total, 2),
    })


def _check_goals():
    """Check trading discipline goals and warn if breached."""
    goals = st.session_state.get("goals", {})
    history = st.session_state.history
    today = datetime.now().strftime("%Y-%m-%d")

    # Daily trade count
    today_trades = [t for t in history if t["date"].startswith(today)]
    max_trades = goals.get("daily_max_trades", 999)
    if len(today_trades) >= max_trades:
        st.warning(f"⚠️ You've reached your daily trade limit ({max_trades} trades)!")

    # Daily loss limit
    today_pnls = [t["pnl"] for t in today_trades if t.get("pnl") is not None]
    daily_loss = abs(min(0, sum(today_pnls))) if today_pnls else 0
    max_loss = goals.get("daily_max_loss", 999999)
    if daily_loss >= max_loss:
        st.error(f"🛑 Daily loss limit breached (${daily_loss:,.2f} ≥ ${max_loss:,.2f})!")


def get_portfolio_value(live_prices: dict[str, float | None] = None) -> float:
    """
    Compute total portfolio value using live prices when available.
    Falls back to avg_price if live price is missing.
    """
    total = st.session_state.balance
    live_prices = live_prices or {}
    for key, pos in st.session_state.portfolio.items():
        clean = key.replace("_SHORT", "")
        price = live_prices.get(clean) or pos["avg_price"]
        total += pos["qty"] * price
    return total


def get_margin_usage() -> dict:
    """Compute margin used by short positions."""
    total_short_value = 0
    positions = 0
    for key, pos in st.session_state.portfolio.items():
        if pos.get("side") == "short":
            total_short_value += pos["qty"] * pos["avg_price"]
            positions += 1
    margin_used = total_short_value * SHORT_MARGIN_RATIO
    return {
        "short_value": total_short_value,
        "margin_used": margin_used,
        "positions": positions,
        "margin_pct": (margin_used / st.session_state.balance * 100) if st.session_state.balance > 0 else 0,
    }
