"""
Persistence — save / load session state to JSON files.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from lib.config import DATA_DIR, SAVE_FILE, BACKUP_PREFIX

# Keys that should be persisted
PERSIST_KEYS = [
    "balance", "initial_balance", "portfolio", "history",
    "equity_curve", "watchlist", "pending_orders", "alerts",
    "commission_rate", "slippage_pct", "spread_pct",
    "trade_notes", "goals", "accounts", "active_account",
]


def _ensure_dir():
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def save_state(filepath: str | None = None) -> str:
    """Serialize session state to JSON. Returns the filepath used."""
    _ensure_dir()
    filepath = filepath or SAVE_FILE
    data = {}
    for key in PERSIST_KEYS:
        if key in st.session_state:
            data[key] = st.session_state[key]
    data["_saved_at"] = datetime.now().isoformat()
    data["_version"] = "2.0.0"
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def load_state(filepath: str | None = None) -> bool:
    """Load state from JSON into session_state. Returns True on success."""
    filepath = filepath or SAVE_FILE
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath) as f:
            data = json.load(f)
        for key in PERSIST_KEYS:
            if key in data:
                st.session_state[key] = data[key]
        return True
    except (json.JSONDecodeError, KeyError):
        return False


def create_backup() -> str:
    """Create a timestamped backup."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{BACKUP_PREFIX}{ts}.json"
    return save_state(path)


def list_backups() -> list[str]:
    """Return sorted list of backup files."""
    _ensure_dir()
    backups = sorted(
        [f for f in os.listdir(DATA_DIR) if f.startswith("backup_") and f.endswith(".json")],
        reverse=True,
    )
    return [os.path.join(DATA_DIR, b) for b in backups]


def export_state_string() -> str:
    """Return the full state as a JSON string (for download)."""
    data = {}
    for key in PERSIST_KEYS:
        if key in st.session_state:
            data[key] = st.session_state[key]
    data["_exported_at"] = datetime.now().isoformat()
    return json.dumps(data, indent=2, default=str)


def import_state_string(json_str: str) -> bool:
    """Import state from a JSON string."""
    try:
        data = json.loads(json_str)
        for key in PERSIST_KEYS:
            if key in data:
                st.session_state[key] = data[key]
        return True
    except (json.JSONDecodeError, KeyError):
        return False
