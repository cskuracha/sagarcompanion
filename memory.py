"""
memory.py — Conversation memory management.

Session format (what gets archived and loaded):
    {
        "messages":    [{role, content}, ...],
        "small_steps": ["step text", ...],   # micro-commitments from session
        "radar":       {"Workload": 7.2, ...}, # final radar scores
    }

Older sessions stored as bare lists of messages are handled transparently
(see _normalise_session).

Extensibility:
  - Swap archive_session() to write to a database without changing agent.py.
  - build_memory_context() produces a plain string — model-agnostic.
"""

from typing import List, Dict, Optional, Union
from config import MAX_STORED_CONVERSATIONS, RADAR_DIMENSIONS


# Type aliases
Message = Dict[str, str]
Session = Dict                      # {messages, small_steps, radar}
LegacySession = List[Message]      # backward-compat: bare list


def _normalise_session(raw: Union[Session, LegacySession]) -> Session:
    """
    Accept either the new dict format or the legacy bare-list format.
    Always returns a consistent dict.
    """
    if isinstance(raw, list):
        return {"messages": raw, "small_steps": [], "radar": {}}
    return {
        "messages":    raw.get("messages", []),
        "small_steps": raw.get("small_steps", []),
        "radar":       raw.get("radar", {}),
    }


def build_memory_context(past_sessions: List) -> str:
    """
    Convert stored past sessions into a readable context string injected
    into the system prompt.

    Includes:
      - A brief summary of past messages (truncated)
      - Any small steps the user committed to in that session

    Returns an empty string if there are no past sessions.
    """
    if not past_sessions:
        return ""

    lines = ["## Context from your previous conversations:"]
    lines.append(
        "_Use this to maintain continuity. Reference it gently when relevant._\n"
    )

    total = len(past_sessions)
    for i, raw in enumerate(past_sessions):
        session = _normalise_session(raw)
        sessions_ago = total - i
        label = "last conversation" if sessions_ago == 1 else f"{sessions_ago} conversations ago"
        lines.append(f"### From your {label}:")

        # Previous small steps (highest value for continuity)
        if session["small_steps"]:
            lines.append("**Small steps the user committed to:**")
            for step in session["small_steps"]:
                lines.append(f"- \"{step}\"")
            lines.append(
                "_If this is the start of a new session, gently ask how these went._"
            )

        # Message summaries
        for msg in session["messages"]:
            role_label = "User" if msg["role"] == "user" else "You (Agent)"
            content = msg["content"]
            if len(content) > 400:
                content = content[:397] + "…"
            lines.append(f"- **{role_label}:** {content}")

        lines.append("")  # blank line between sessions

    return "\n".join(lines)


def archive_session(
    current_messages: List[Message],
    past_sessions: List,
    small_steps: Optional[List[str]] = None,
    radar_scores: Optional[Dict[str, float]] = None,
) -> List[Session]:
    """
    Archive the current session and return the updated sessions list.

    - Appends the current session (enriched with steps and radar).
    - Keeps only the last MAX_STORED_CONVERSATIONS sessions.
    - Does NOT mutate inputs — returns a new list.

    Args:
        current_messages: The session being archived.
        past_sessions:    Existing memory store (any format).
        small_steps:      Micro-commitments extracted during the session.
        radar_scores:     Final radar scores at session end.

    Returns:
        Updated list of Session dicts.
    """
    if not current_messages:
        return [_normalise_session(s) for s in past_sessions]

    new_session: Session = {
        "messages":    list(current_messages),
        "small_steps": list(small_steps or []),
        "radar":       dict(radar_scores or {}),
    }

    normalised_past = [_normalise_session(s) for s in past_sessions]
    updated = normalised_past + [new_session]
    return updated[-MAX_STORED_CONVERSATIONS:]


def summarise_session_for_display(raw: Union[Session, LegacySession], max_exchanges: int = 3) -> str:
    """
    Produce a short human-readable summary of a session for the UI.

    Args:
        raw:           Session in any supported format.
        max_exchanges: How many user lines to preview.

    Returns:
        A short Markdown summary string.
    """
    session = _normalise_session(raw)
    user_msgs = [m["content"] for m in session["messages"] if m["role"] == "user"]
    preview = user_msgs[:max_exchanges]

    if not preview:
        return "Empty session."

    bullets = "\n".join(
        f"- {msg[:100]}{'…' if len(msg) > 100 else ''}"
        for msg in preview
    )
    suffix = (
        f"\n…and {len(user_msgs) - max_exchanges} more messages."
        if len(user_msgs) > max_exchanges
        else ""
    )

    steps_section = ""
    if session["small_steps"]:
        step_lines = "\n".join(f"  ✦ {s}" for s in session["small_steps"])
        steps_section = f"\n\n**Small steps committed:**\n{step_lines}"

    return bullets + suffix + steps_section
