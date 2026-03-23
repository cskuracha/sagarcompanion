"""
flask_app.py — Flask adapter for the Burnout Support Agent.

This file demonstrates how agent.py can be used from a Flask backend
without modifying any core logic.

Run with:
    flask --app flask_app run

Endpoints:
    POST /chat      — Send a message, get a response
    POST /reset     — Archive current session and start fresh
    GET  /sessions  — List stored session summaries

In production, replace the in-memory SESSION_STORE with Redis or a database.
"""

import json
from flask import Flask, request, jsonify, session
from agent import get_agent_response
from memory import archive_session, summarise_session_for_display
from config import SUPPORTED_MODELS

app = Flask(__name__)
app.secret_key = "change-this-in-production"  # required for Flask session

# In-memory store keyed by session_id (swap for Redis/DB in production)
# Structure: { session_id: { "messages": [...], "past_sessions": [...], "exchange_count": int } }
SESSION_STORE: dict = {}


def _get_or_init_store(session_id: str) -> dict:
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = {
            "messages": [],
            "past_sessions": [],
            "exchange_count": 0,
        }
    return SESSION_STORE[session_id]


@app.route("/chat", methods=["POST"])
def chat():
    """
    POST /chat
    Body (JSON):
      {
        "session_id":   "abc123",
        "message":      "I'm feeling overwhelmed at work.",
        "model_choice": "Groq – LLaMA 3.3 70B"   (optional, defaults to first model)
      }

    Response (JSON):
      {
        "response":  "...",
        "exchange_count": 3
      }
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "default")
    user_message = (body.get("message") or "").strip()
    model_choice = body.get("model_choice", list(SUPPORTED_MODELS.keys())[0])

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    if model_choice not in SUPPORTED_MODELS:
        return jsonify({"error": f"Invalid model_choice. Options: {list(SUPPORTED_MODELS.keys())}"}), 400

    store = _get_or_init_store(session_id)
    store["messages"].append({"role": "user", "content": user_message})

    try:
        response = get_agent_response(
            current_messages=store["messages"],
            model_choice=model_choice,
            past_sessions=store["past_sessions"],
            exchange_count=store["exchange_count"],
        )
    except EnvironmentError as e:
        return jsonify({"error": str(e)}), 503
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502

    store["messages"].append({"role": "assistant", "content": response})
    store["exchange_count"] += 1

    return jsonify({
        "response": response,
        "exchange_count": store["exchange_count"],
    })


@app.route("/reset", methods=["POST"])
def reset():
    """
    POST /reset
    Body (JSON): { "session_id": "abc123" }

    Archives the current session and clears for a new one.
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "default")
    store = _get_or_init_store(session_id)

    store["past_sessions"] = archive_session(
        current_messages=store["messages"],
        past_sessions=store["past_sessions"],
    )
    store["messages"] = []
    store["exchange_count"] = 0

    return jsonify({"status": "reset", "past_sessions_count": len(store["past_sessions"])})


@app.route("/sessions", methods=["GET"])
def get_sessions():
    """
    GET /sessions?session_id=abc123

    Returns summaries of stored past sessions for the UI.
    """
    session_id = request.args.get("session_id", "default")
    store = _get_or_init_store(session_id)

    summaries = [
        summarise_session_for_display(s)
        for s in store["past_sessions"]
    ]

    return jsonify({
        "past_sessions_count": len(summaries),
        "summaries": summaries,
    })


if __name__ == "__main__":
    app.run(debug=True)
