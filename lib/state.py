"""
Session state initialization and helpers for Trading Lab Pro.
"""

import streamlit as st
from dataclasses import asdict
from lib.config import SessionDefaults


def init_session_state():
    """Initialize all session-state keys with defaults (idempotent)."""
    defaults = asdict(SessionDefaults())
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset_session_state():
    """Hard-reset all session state to defaults."""
    defaults = asdict(SessionDefaults())
    for key, val in defaults.items():
        st.session_state[key] = val


def get(key: str, default=None):
    """Safe getter for session state."""
    return st.session_state.get(key, default)


def set_key(key: str, value):
    """Safe setter for session state."""
    st.session_state[key] = value
