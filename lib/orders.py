"""
Order management — pending / conditional orders:
  • Limit Buy / Sell
  • Stop-Loss / Take-Profit
  • Trailing Stop (% or fixed $)
  • OCO Bracket (stop-loss + take-profit linked)
"""

from __future__ import annotations
from datetime import datetime

import streamlit as st

from lib.trading_engine import execute_trade


# ──────────────────────────────────────────────────────────────
#  Order placement
# ──────────────────────────────────────────────────────────────

def place_order(
    ticker: str,
    order_type: str,
    target_price: float,
    qty: int,
    *,
    trailing_pct: float | None = None,
    trailing_amount: float | None = None,
    oco_pair_id: str | None = None,
) -> dict:
    """Place a pending order. Returns the order dict."""
    order = {
        "id": f"ORD-{len(st.session_state.pending_orders)+1:04d}",
        "ticker": ticker,
        "type": order_type,
        "target_price": target_price,
        "qty": qty,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "active",
        "trailing_pct": trailing_pct,
        "trailing_amount": trailing_amount,
        "highest_price": None,   # For trailing stops
        "oco_pair_id": oco_pair_id,
    }
    st.session_state.pending_orders.append(order)
    return order


def place_oco_bracket(
    ticker: str,
    qty: int,
    stop_loss_price: float,
    take_profit_price: float,
) -> tuple[dict, dict]:
    """Place a linked OCO bracket: one triggers → other cancels."""
    pair_id = f"OCO-{datetime.now().strftime('%H%M%S')}"
    sl = place_order(ticker, "Stop-Loss", stop_loss_price, qty, oco_pair_id=pair_id)
    tp = place_order(ticker, "Take-Profit", take_profit_price, qty, oco_pair_id=pair_id)
    return sl, tp


def place_trailing_stop(
    ticker: str,
    qty: int,
    current_price: float,
    trail_pct: float | None = None,
    trail_amount: float | None = None,
) -> dict:
    """Place a trailing stop order."""
    if trail_pct:
        target = current_price * (1 - trail_pct / 100)
    elif trail_amount:
        target = current_price - trail_amount
    else:
        target = current_price * 0.95  # Default 5%

    order = place_order(
        ticker, "Trailing-Stop", round(target, 2), qty,
        trailing_pct=trail_pct, trailing_amount=trail_amount,
    )
    order["highest_price"] = current_price
    return order


# ──────────────────────────────────────────────────────────────
#  Order checking / execution
# ──────────────────────────────────────────────────────────────

def check_pending_orders(current_price: float, ticker: str):
    """Check all pending orders for *ticker* against *current_price*."""
    executed_indices: list[int] = []
    cancelled_oco_ids: set[str] = set()

    for i, order in enumerate(st.session_state.pending_orders):
        if order["ticker"] != ticker or order["status"] != "active":
            continue
        # Skip if OCO partner already triggered
        if order.get("oco_pair_id") and order["oco_pair_id"] in cancelled_oco_ids:
            executed_indices.append(i)
            continue

        triggered = False

        if order["type"] == "Limit Buy" and current_price <= order["target_price"]:
            execute_trade(ticker, "Buy", order["qty"], current_price)
            triggered = True
            st.info(f"🔔 Limit Buy triggered: {ticker} @ ${current_price:.2f}")

        elif order["type"] == "Limit Sell" and current_price >= order["target_price"]:
            execute_trade(ticker, "Sell", order["qty"], current_price)
            triggered = True
            st.info(f"🔔 Limit Sell triggered: {ticker} @ ${current_price:.2f}")

        elif order["type"] == "Stop-Loss" and current_price <= order["target_price"]:
            execute_trade(ticker, "Sell", order["qty"], current_price)
            triggered = True
            st.warning(f"🛑 Stop-Loss triggered: {ticker} @ ${current_price:.2f}")

        elif order["type"] == "Take-Profit" and current_price >= order["target_price"]:
            execute_trade(ticker, "Sell", order["qty"], current_price)
            triggered = True
            st.success(f"🎯 Take-Profit triggered: {ticker} @ ${current_price:.2f}")

        elif order["type"] == "Trailing-Stop":
            # Update highest price
            if order["highest_price"] is None or current_price > order["highest_price"]:
                order["highest_price"] = current_price
                # Recalculate stop level
                if order["trailing_pct"]:
                    order["target_price"] = round(
                        current_price * (1 - order["trailing_pct"] / 100), 2
                    )
                elif order["trailing_amount"]:
                    order["target_price"] = round(
                        current_price - order["trailing_amount"], 2
                    )

            if current_price <= order["target_price"]:
                execute_trade(ticker, "Sell", order["qty"], current_price)
                triggered = True
                st.warning(f"📉 Trailing Stop triggered: {ticker} @ ${current_price:.2f}")

        if triggered:
            executed_indices.append(i)
            # Cancel OCO partner
            if order.get("oco_pair_id"):
                cancelled_oco_ids.add(order["oco_pair_id"])

    # Remove executed orders (reverse to preserve indices)
    for idx in sorted(executed_indices, reverse=True):
        st.session_state.pending_orders.pop(idx)


def cancel_order(index: int):
    """Cancel a pending order by index. Also cancels OCO partner."""
    if 0 <= index < len(st.session_state.pending_orders):
        order = st.session_state.pending_orders[index]
        oco_id = order.get("oco_pair_id")

        if oco_id:
            # Remove all orders with this OCO id
            st.session_state.pending_orders = [
                o for o in st.session_state.pending_orders
                if o.get("oco_pair_id") != oco_id
            ]
        else:
            st.session_state.pending_orders.pop(index)


def get_active_orders(ticker: str | None = None) -> list[dict]:
    """Return active orders, optionally filtered by ticker."""
    orders = [o for o in st.session_state.pending_orders if o["status"] == "active"]
    if ticker:
        orders = [o for o in orders if o["ticker"] == ticker]
    return orders
