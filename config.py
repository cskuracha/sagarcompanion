"""
config.py — Single source of truth for all settings.

To add a new LLM provider:
  1. Add an entry to SUPPORTED_MODELS
  2. Add a handler in llm_client.py
  3. Nothing else changes.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Supported Models ───────────────────────────────────────────────────────────
SUPPORTED_MODELS: dict = {
    "Groq – LLaMA 3.3 70B": {
        "provider": "groq",
        "model_id": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
        "description": "Fast, open-weight model via Groq inference.",
    },
    "Gemini – Flash Lite": {
        "provider": "gemini",
        "model_id": "gemini-2.5-flash-lite",
        "api_key_env": "GEMINI_API_KEY",
        "description": "Lightweight Gemini model from Google.",
    },
}

# ── Memory ─────────────────────────────────────────────────────────────────────
MAX_STORED_CONVERSATIONS: int = 2    # rolling window of past sessions
MAX_MESSAGES_PER_SESSION: int = 40   # trim before sending to LLM

# ── Generation ─────────────────────────────────────────────────────────────────
MAX_TOKENS: int = 1024
TEMPERATURE: float = 0.7

# ── Safety: crisis detection keywords ─────────────────────────────────────────
SAFETY_TRIGGERS: list[str] = [
    "kill myself",
    "end my life",
    "suicide",
    "suicidal",
    "self-harm",
    "self harm",
    "hurt myself",
    "cutting myself",
    "can't go on",
    "no reason to live",
    "want to die",
    "harm others",
    "hurt someone",
    "can't function",
    "completely unable to function",
    "medical emergency",
    "overdose",
]

# ── Tone scale reminder intervals ──────────────────────────────────────────────
WELLBEING_REMINDER_EVERY_N: int = 5

# ── Feature: Burnout Fingerprint Radar ────────────────────────────────────────
# Maslach's 6 Areas of Worklife — the dimensions shown on the radar chart.
RADAR_DIMENSIONS: list[str] = [
    "Workload",
    "Control",
    "Reward",
    "Community",
    "Fairness",
    "Values",
]
# Radar scores are re-inferred from the conversation every N exchanges.
RADAR_UPDATE_EVERY_N: int = 3

# ── Feature: One Small Step ────────────────────────────────────────────────────
# Step extraction runs every N exchanges (keeps API calls manageable).
STEP_CHECK_EVERY_N: int = 2

# ── Pre-session ritual options ─────────────────────────────────────────────────
ENERGY_OPTIONS: list[str] = [
    "😶 Numb",
    "😔 Low",
    "😐 Okay",
    "🙂 Alright",
    "😤 Overwhelmed",
]
CONCERN_OPTIONS: list[str] = [
    "Work overload",
    "Team / people issues",
    "Personal burnout",
    "Not sure yet",
]
