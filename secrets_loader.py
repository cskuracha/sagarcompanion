"""
secrets_loader.py — Bridge between Streamlit secrets and os.environ.

Why this exists:
  - llm_client.py, config.py, agent.py must remain framework-agnostic
    (they contain zero Streamlit or Flask imports).
  - Streamlit on a server loads credentials from .streamlit/secrets.toml,
    NOT from a .env file.
  - This module is called ONCE at app startup (in app.py) and pushes
    Streamlit secrets into os.environ so that all downstream code
    can use os.getenv() uniformly regardless of deployment context.

Resolution order (first match wins):
  1. os.environ already set (e.g. shell export, CI/CD variable injection)
  2. st.secrets  (Streamlit server deployment via secrets.toml)
  3. .env file   (local development via python-dotenv)

Flask / FastAPI usage:
  - Do NOT import this file from flask_app.py.
  - Flask reads credentials from .env via python-dotenv (see config.py).
  - This file is Streamlit-only.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Keys this app needs — must match secrets.toml and .env.example
_REQUIRED_KEYS = [
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
]


def load_secrets_into_environ() -> None:
    """
    Copy Streamlit secrets into os.environ for any key not already set.

    Called once at the top of app.py before any LLM code runs.
    Safe to call multiple times (idempotent — skips keys already in environ).
    """
    try:
        import streamlit as st

        for key in _REQUIRED_KEYS:
            # Skip if already present (e.g. injected by the hosting platform)
            if os.environ.get(key):
                continue

            # Try st.secrets
            value = st.secrets.get(key, "").strip()
            if value and value != f"your_{key.lower()}_here":
                os.environ[key] = value
                logger.debug("Loaded '%s' from st.secrets into os.environ.", key)
            else:
                logger.warning(
                    "Key '%s' not found in st.secrets or is a placeholder. "
                    "Falling back to .env / os.environ.",
                    key,
                )

    except ImportError:
        # Streamlit not installed — this should never happen in app.py context
        logger.error("streamlit not installed; cannot load secrets from secrets.toml.")
    except Exception as exc:
        # Broad catch so a secrets misconfiguration doesn't crash at import time;
        # the actual LLM call will raise a clear EnvironmentError if the key is missing.
        logger.warning("Unexpected error loading Streamlit secrets: %s", exc)


def check_required_secrets() -> list[str]:
    """
    Return a list of keys that are missing or still placeholders after loading.

    Use this in app.py to show a friendly setup warning in the UI.

    Returns:
        List of missing key names (empty list = all good).
    """
    missing = []
    for key in _REQUIRED_KEYS:
        val = os.environ.get(key, "").strip()
        if not val or val.startswith("your_"):
            missing.append(key)
    return missing
