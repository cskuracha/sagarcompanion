"""
memory.py — Conversation memory management.

Design:
  - Stores up to MAX_STORED_CONVERSATIONS past sessions per user.
  - Each session is a list of {role, content} dicts (standard chat format).
  - The *current* session lives in the calling layer (e.g., Streamlit session_state).
  - This module only handles archiving and context-building.

Extensibility:
  - Swap `archive_session` to write to a database without changing agent.py.
  - `build_memory_context` produces a plain string — model-agnostic.
"""

from typing import List, Dict
from config import MAX_STORED_CONVERSATIONS


# Type alias for clarity
Session = List[Dict[str, str]]


def build_memory_context(past_sessions: List[Session]) -> str:
    """
    Convert stored past sessions into a readable context string
    injected into the system prompt.

    Returns an empty string if there are no past sessions.
    """
    if not past_sessions:
        return ""

    lines = ["## Context from your previous conversations:"]
    lines.append(
        "_Use this to maintain warmth and continuity. "
        "Reference it gently when relevant._\n"
    )

    total = len(past_sessions)
    for i, session in enumerate(past_sessions):
        sessions_ago = total - i
        label = "last conversation" if sessions_ago == 1 else f"{sessions_ago} conversations ago"
        lines.append(f"### From your {label}:")

        for msg in session:
            role_label = "User" if msg["role"] == "user" else "You (Agent)"
            # Truncate very long messages to avoid bloating the context window
            content = msg["content"]
            if len(content) > 400:
                content = content[:397] + "…"
            lines.append(f"- **{role_label}:** {content}")

        lines.append("")  # blank line between sessions

    return "\n".join(lines)


def archive_session(
    current_messages: Session,
    past_sessions: List[Session],
) -> List[Session]:
    """
    Archive the current session into past_sessions and return the updated list.

    - Keeps only the last MAX_STORED_CONVERSATIONS sessions.
    - Filters out empty sessions.
    - Does NOT mutate the inputs — returns a new list.

    Args:
        current_messages: The session being archived (current chat history).
        past_sessions:    The existing memory store.

    Returns:
        Updated list of past sessions (new session appended, oldest dropped if needed).
    """
    if not current_messages:
        return list(past_sessions)  # nothing to archive

    # Append the current session and keep the tail
    updated = list(past_sessions) + [list(current_messages)]
    return updated[-MAX_STORED_CONVERSATIONS:]


def summarise_session_for_display(session: Session, max_exchanges: int = 3) -> str:
    """
    Produce a short human-readable summary of a session for the UI.
    Shows the first `max_exchanges` user messages as a preview.

    Args:
        session:       List of messages in the session.
        max_exchanges: How many user lines to include.

    Returns:
        A short summary string.
    """
    user_msgs = [m["content"] for m in session if m["role"] == "user"]
    preview = user_msgs[:max_exchanges]
    if not preview:
        return "Empty session."
    bullets = "\n".join(f"- {msg[:100]}{'…' if len(msg) > 100 else ''}" for msg in preview)
    suffix = f"\n…and {len(user_msgs) - max_exchanges} more messages." if len(user_msgs) > max_exchanges else ""
    return bullets + suffix
