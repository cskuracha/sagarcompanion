"""
agent.py — Core agent orchestrator.

Framework-agnostic: contains zero Streamlit, Flask, or FastAPI imports.
It can be called from any interface layer.

Responsibilities:
  1. Build the system prompt (base + memory context + ritual context)
  2. Detect crisis signals → return hardcoded safe response
  3. Inject periodic professional-help reminder
  4. Trim message history to fit context windows
  5. Delegate LLM call to llm_client.py
"""

from typing import List, Dict, Optional

from config import MAX_MESSAGES_PER_SESSION, WELLBEING_REMINDER_EVERY_N
from memory import build_memory_context
from safety import is_crisis_message, CRISIS_RESPONSE
from llm_client import get_completion


# ── System Prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_BASE = """
You are a warm, compassionate support agent for IT professionals, educators, and startup workers experiencing burnout or emotional exhaustion.

## Your Core Mission
Your goal is NOT to fix the user. Your goal is to:
- Help them feel truly heard and understood
- Help them think through what they're experiencing
- Support them gently, without rushing or pushing
- Encourage professional help when the situation calls for it

## Tone & Style
- Speak in warm, conversational English — like a trusted, calm friend
- Use short paragraphs and simple language — never jargon
- Maintain a gentle tone (calm, reflective, or soft coaching)
- Use empathetic reflection, for example: "It sounds like you've been carrying a lot lately."
- Ask ONE thoughtful question at a time — never overwhelm
- Use gentle Socratic questions such as:
  - "What part of this feels hardest right now?"
  - "What would feeling slightly better look like for you?"
  - "Is there one small thing that felt okay today, even briefly?"
- Never rush the user or push them toward solutions
- Offer a gentle summary when helpful: "Here's what I'm hearing so far…"

## What You Help Explore
- Identifying the sources of burnout (overload, misalignment, isolation, loss of meaning)
- Reflecting on patterns and boundaries
- Exploring small, realistic next steps — never large life decisions
- Reconnecting the user with their strengths and what matters to them

## One Small Step
Occasionally — when the moment feels right, not formulaically — offer or invite a single small, concrete step the user could try before the next session. Keep it achievable (e.g. "a 10-minute walk before your first meeting" not "change your career"). If the user agrees, affirm it warmly.

## Hard Rules — Never Do These
- Do NOT give medical, diagnostic, or medication advice
- Do NOT tell the user what career decisions to make (never say "quit", "confront your manager", "take a leave")
- Do NOT be toxically positive ("You've got this!", "Just think positive!")
- Do NOT over-coach or dump a laundry list of advice
- Do NOT ask questions you have already asked in this conversation
- Do NOT make assumptions about what the user should feel or do

## Professional Help Reminder
Every 5 exchanges, include this note naturally in your response — woven in, never as a disclaimer header:
"Just a gentle note — I'm here to support you, but I'm not a replacement for therapy or professional mental-health care."

## Formatting Rules
- Use simple markdown only: ## headings, bullet points, short paragraphs
- Keep responses short and readable on a mobile screen
- Avoid tables, ASCII art, long code blocks, or complex formatting
- One idea per paragraph

## Memory & Continuity
If context from previous conversations is provided below, use it to:
- Maintain warmth and continuity across sessions
- Avoid repeating questions already explored
- Follow up on small steps the user committed to in previous sessions — gently and without pressure
""".strip()


# ── Prompt Builder ─────────────────────────────────────────────────────────────

def build_system_prompt(
    past_sessions_context: str = "",
    ritual_context: str = "",
) -> str:
    """
    Compose the final system prompt from base + memory + ritual context.

    Args:
        past_sessions_context: Memory context from build_memory_context().
        ritual_context:        Pre-session check-in info (energy, concern area).
    """
    parts = [_SYSTEM_PROMPT_BASE]

    if ritual_context:
        parts.append(
            "\n\n---\n\n"
            "## Pre-session check-in (from the user's ritual before chatting):\n"
            + ritual_context
            + "\n\nUse this context warmly from your very first response. "
            "Don't repeat it back verbatim — just let it inform your tone and first question."
        )

    if past_sessions_context:
        parts.append("\n\n---\n\n" + past_sessions_context)

    return "".join(parts)


# ── Reminder Injection ─────────────────────────────────────────────────────────

def _should_inject_reminder(exchange_count: int) -> bool:
    return exchange_count > 0 and exchange_count % WELLBEING_REMINDER_EVERY_N == 0


def _inject_reminder_into_system(system_prompt: str) -> str:
    return (
        system_prompt
        + "\n\n**IMPORTANT FOR THIS TURN:** Please include a gentle reminder "
        "that you are not a replacement for therapy or professional mental-health care."
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def get_agent_response(
    current_messages: List[Dict[str, str]],
    model_choice: str,
    past_sessions: Optional[List] = None,
    exchange_count: int = 0,
    ritual_context: str = "",
) -> str:
    """
    Generate the agent's next response.

    Args:
        current_messages: Current session [{role, content}] history.
        model_choice:     Key from SUPPORTED_MODELS in config.py.
        past_sessions:    Previous sessions for memory context (optional).
        exchange_count:   Number of full exchanges so far (for reminders).
        ritual_context:   Pre-session energy/concern check-in (optional).

    Returns:
        The agent's response as a plain string.

    This is the single integration point for any interface layer
    (Streamlit, Flask, FastAPI, mobile backend, CLI, etc.)
    """
    # 1. Safety check — always first, always hardcoded response
    if current_messages and current_messages[-1]["role"] == "user":
        if is_crisis_message(current_messages[-1]["content"]):
            return CRISIS_RESPONSE

    # 2. Build system prompt
    memory_context = build_memory_context(past_sessions or [])
    system_prompt = build_system_prompt(memory_context, ritual_context)

    # 3. Inject reminder if due
    if _should_inject_reminder(exchange_count):
        system_prompt = _inject_reminder_into_system(system_prompt)

    # 4. Trim history
    trimmed_messages = current_messages[-MAX_MESSAGES_PER_SESSION:]

    # 5. LLM call
    return get_completion(
        messages=trimmed_messages,
        system_prompt=system_prompt,
        model_choice=model_choice,
    )
