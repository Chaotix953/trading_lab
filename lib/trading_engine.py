"""
Trading engine — execute trades with realistic slippage, commissions, and decimal precision.
Supports both stocks and options trading.
"""

from decimal import Decimal, getcontext
from typing import Optional, List, Dict, Any
import numpy as np
import streamlit as st
from datetime import datetime

# Configuration de la précision financière
getcontext().prec = 28
D = Decimal


def _to_decimal(val: Any) -> Decimal:
    """Helper pour convertir float -> Decimal proprement"""
    return D(str(val)) if val is not None else D(0)


def _apply_slippage(price: Decimal, side: str, volatility: float = 0.01) -> Decimal:
    """
    Slippage réaliste basé sur une distribution normale (Gaussienne).
    On suppose que le slippage moyen est nul mais que l'écart-type dépend de la volatilité.

    95% des trades ont un slippage < 0.05%
    """
    # Simulation: on utilise numpy pour une distribution normale
    slip_factor = np.random.normal(0, 0.0005)

    # Impact de marché (Market Impact) : plus on achète, plus on pousse le prix
    slippage = price * D(str(slip_factor))

    if side == "buy":
        return price + abs(slippage)  # On paie souvent plus cher
    else:
        return price - abs(slippage)  # On vend souvent moins cher


def execute_trade(
    ticker: str,
    action: str,
    quantity: int,
    raw_price: float,
    asset_type: str = "Stock",  # "Stock" ou "Option"
    note: str = "",
    tags: Optional[List[str]] = None,
    option_metadata: Optional[Dict[str, Any]] = None,  # Pour stocker strike, exp, type (Call/Put)
) -> bool:
    """
    Exécute un trade avec conversion Decimal et calcul du slippage.

    Parameters:
    -----------
    ticker : str
        Symbole du titre
    action : str
        "Buy", "Sell", "Short", "Cover"
    quantity : int
        Nombre de parts/contrats
    raw_price : float
        Prix marché actuel
    asset_type : str
        "Stock" ou "Option"
    note : str
        Note personnelle sur le trade
    tags : list
        Tags pour catégoriser le trade
    option_metadata : dict
        Métadonnées pour les options (strike, expiry, type)

    Returns:
    --------
    bool : True si le trade a été exécuté, False sinon
    """
    # Conversion en Decimal
    d_qty = D(quantity)
    d_raw_price = _to_decimal(raw_price)

    # Récupérer la balance actuelle en Decimal
    d_balance = _to_decimal(st.session_state.balance)

    side_map = {"Buy": "buy", "Sell": "sell", "Short": "sell", "Cover": "buy"}
    side = side_map.get(action, "buy")

    # Calcul du prix d'exécution avec slippage réaliste
    fill_price = _apply_slippage(d_raw_price, side)

    # Multiplicateur pour les options (100 pour contrats US)
    multiplier = 1
    if asset_type == "Option":
        multiplier = 100

    gross_amount = d_qty * fill_price * D(multiplier)
    commission_rate = _to_decimal(st.session_state.get("commission_rate", 0.001))
    commission = gross_amount * commission_rate

    success = False

    # Logique Achat (Long Stock ou Long Option)
    if action == "Buy":
        total_cost = gross_amount + commission
        if d_balance >= total_cost:
            st.session_state.balance = float(d_balance - total_cost)

            # Gestion clé unique pour les options (ex: AAPL_230915_C_150)
            if asset_type == "Option" and option_metadata:
                pf_key = f"{ticker}_{option_metadata['expiry']}_{option_metadata['type']}_{option_metadata['strike']}"
            else:
                pf_key = ticker

            _add_to_portfolio(
                pf_key,
                quantity,
                float(fill_price),
                asset_type,
                "long",
                option_metadata,
            )
            success = True
            st.success(f"✅ BUY {quantity} {pf_key} @ ${fill_price:.2f}")
        else:
            st.error(f"Fonds insuffisants. Requis: ${total_cost:.2f}")

    # Logique Vente (Close position)
    elif action == "Sell":
        if asset_type == "Option" and option_metadata:
            pf_key = f"{ticker}_{option_metadata['expiry']}_{option_metadata['type']}_{option_metadata['strike']}"
        else:
            pf_key = ticker

        pf = st.session_state.portfolio
        if pf_key in pf and pf[pf_key]["qty"] > 0:
            position = pf[pf_key]
            revenue = gross_amount - commission
            pnl = revenue - (position["qty"] * D(str(position["avg_price"])) * D(multiplier))
            st.session_state.balance = float(d_balance + revenue)

            # Supprimer la position
            del pf[pf_key]

            success = True
            st.success(
                f"✅ SELL {quantity} {pf_key} @ ${fill_price:.2f} | PnL: ${float(pnl):.2f}"
            )
        else:
            st.error(f"Pas de position à vendre pour {pf_key}")

    # Logique Short (vente à découvert)
    elif action == "Short":
        if asset_type != "Stock":
            st.error("Shorting non disponible pour les options")
        else:
            total_proceeds = gross_amount - commission
            st.session_state.balance = float(d_balance + total_proceeds)

            if asset_type == "Stock":
                pf_key = ticker
            else:
                pf_key = f"{ticker}_{option_metadata['expiry']}_{option_metadata['type']}_{option_metadata['strike']}"

            _add_to_portfolio(pf_key, quantity, float(fill_price), asset_type, "short", option_metadata)
            success = True
            st.success(f"📉 SHORT {quantity} {pf_key} @ ${fill_price:.2f}")

    # Logique Cover (fermer une position short)
    elif action == "Cover":
        if asset_type != "Stock":
            st.error("Covering non disponible pour les options")
        else:
            pf = st.session_state.portfolio
            if ticker in pf and pf[ticker]["side"] == "short":
                position = pf[ticker]
                cost = gross_amount + commission
                pnl = (position["qty"] * D(str(position["avg_price"]))) - gross_amount
                st.session_state.balance = float(d_balance - cost)

                # Supprimer la position
                del pf[ticker]

                success = True
                st.success(
                    f"✅ COVER {quantity} {ticker} @ ${fill_price:.2f} | PnL: ${float(pnl):.2f}"
                )
            else:
                st.error(f"Pas de position short à couvrir pour {ticker}")

    if success:
        # Log using floats for display/JSON compatibility but calculations were safe
        _log_trade(
            ticker,
            action,
            quantity,
            float(fill_price),
            raw_price,
            asset_type,
            float(commission),
            note,
            tags,
        )

    return success


def _add_to_portfolio(
    key: str, qty: int, price: float, asset_type: str, side: str, 
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Ajoute ou met à jour une position dans le portefeuille.
    Utilise la moyenne pondérée (VWAP) pour le prix moyen d'entrée.
    """
    pf = st.session_state.portfolio
    if key in pf:
        old = pf[key]
        # Moyenne pondérée (VWAP)
        new_qty = old["qty"] + qty
        new_avg = (
            (old["qty"] * old["avg_price"]) + (qty * price)
        ) / new_qty
        pf[key].update({"qty": new_qty, "avg_price": new_avg})
    else:
        entry: Dict[str, Any] = {
            "qty": qty,
            "avg_price": price,
            "type": asset_type,
            "side": side,
        }
        if metadata:
            entry.update(metadata)  # Ajoute strike, greeks initiaux, etc.
        pf[key] = entry


def _log_trade(
    ticker: str, action: str, quantity: int, fill_price: float, raw_price: float, 
    asset_type: str, commission: float, note: str, tags: Optional[List[str]]
) -> None:
    """Log trade to session state for history."""
    trade_log: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "action": action,
        "quantity": quantity,
        "fill_price": fill_price,
        "raw_price": raw_price,
        "asset_type": asset_type,
        "commission": commission,
        "note": note,
        "tags": tags or [],
    }

    if "trade_history" not in st.session_state:
        st.session_state.trade_history = []

    st.session_state.trade_history.append(trade_log)


def simulate_fill_price(price: float, side: str) -> float:
    """Simule le prix de remplissage avec slippage."""
    d_price = D(str(price))
    fill = _apply_slippage(d_price, side)
    return float(fill)


def get_portfolio_summary() -> Dict[str, Any]:
    """Retourne un résumé du portefeuille actuel."""
    pf = st.session_state.portfolio
    summary: Dict[str, Any] = {
        "total_positions": len(pf),
        "cash": st.session_state.balance,
        "positions": {},
    }

    for key, pos in pf.items():
        summary["positions"][key] = {
            "qty": pos["qty"],
            "avg_price": pos["avg_price"],
            "type": pos["type"],
            "side": pos["side"],
        }

    return summary


def get_portfolio_value(current_prices: Optional[Dict[str, float]] = None) -> float:
    """
    Calcule la valeur totale du portefeuille (cash + positions évaluées).
    
    Parameters:
    -----------
    current_prices : dict, optional
        Dictionnaire {ticker: prix_courant}. Si None, utilise le cash seulement.
    
    Returns:
    --------
    float : Valeur totale du portefeuille
    """
    pf = st.session_state.portfolio
    total = st.session_state.balance
    
    if current_prices:
        for key, pos in pf.items():
            # Extraire le ticker du portefeuille (key peut être "AAPL" ou "AAPL_230915_C_150")
            ticker = key.split("_")[0]
            if ticker in current_prices:
                price = current_prices[ticker]
                multiplier = pos.get("multiplier", 1)
                value = pos["qty"] * price * multiplier
                
                # Pour les shorts, la valeur change inversement
                if pos.get("side") == "short":
                    value = -value
                    
                total += value
    
    return total


def get_margin_usage() -> Dict[str, Any]:
    """
    Calcule l'utilisation du margin (pour le short selling).
    
    Returns:
    --------
    dict : {"positions": int, "margin_used": float, "margin_pct": float, "margin_available": float}
    """
    pf = st.session_state.portfolio
    margin_used = 0.0
    short_positions = 0
    
    # Margin requirement: 50% de la valeur pour shorting
    for _, pos in pf.items():
        if pos.get("side") == "short":
            short_positions += 1
            multiplier = pos.get("multiplier", 1)
            margin_used += pos["qty"] * pos["avg_price"] * multiplier * 0.5
    
    initial_margin = 100_000.0  # Capital initial approximatif
    margin_available = initial_margin - margin_used
    margin_pct = (margin_used / initial_margin * 100) if initial_margin > 0 else 0.0
    
    return {
        "positions": short_positions,
        "margin_used": margin_used,
        "margin_pct": margin_pct,
        "margin_available": max(margin_available, 0.0),
    }
