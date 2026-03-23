"""
features.py — Three differentiating features for the Burnout Support Agent.

All functions make silent, structured LLM calls completely separate from the
main conversation. They return typed data — not chat messages — and fail
gracefully without ever surfacing errors to the user.

Feature 1: Burnout Fingerprint Radar
  Silently scores Maslach's 6 Areas of Worklife (0–10) from conversation
  context. Updated every RADAR_UPDATE_EVERY_N exchanges. No forms, no
  questionnaires — the profile emerges from what the user says.

Feature 2: One Small Step Tracker
  Extracts micro-commitments from conversation exchanges. Stored in session
  memory and carried into the next session so the agent can follow up.

Feature 3: Session Insight Card
  Generates a compassionate 3-part reflection (themes, pattern, carry-forward)
  at the end of a session. Triggered by a button or auto-detected farewell.
"""

import json
import logging
import math
from typing import Optional

from llm_client import get_completion
from config import RADAR_DIMENSIONS

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Feature 1 — Burnout Fingerprint Radar
# ─────────────────────────────────────────────────────────────────────────────

_RADAR_SYSTEM = """You are a silent burnout analyst. Analyze the conversation and score each of Maslach's 6 Areas of Worklife based on what the user has shared.

Return ONLY valid JSON with exactly these keys and float values 0.0–10.0:
{
  "Workload": 5.0,
  "Control": 5.0,
  "Reward": 5.0,
  "Community": 5.0,
  "Fairness": 5.0,
  "Values": 5.0
}

Scoring guide (higher = more stressed/depleted in that dimension):
- Workload:   0=light and manageable,  10=crushing/overwhelming
- Control:    0=full autonomy,          10=no control over decisions
- Reward:     0=well recognised,        10=zero recognition or reward
- Community:  0=strong support network, 10=complete isolation/conflict
- Fairness:   0=feels treated fairly,   10=deep sense of injustice
- Values:     0=work fully aligned,     10=serious values mismatch

If there is insufficient information for a dimension, return 5.0 (neutral).
Return ONLY the JSON object. No explanation, no markdown backticks, no extra text."""


def infer_radar_scores(
    messages: list,
    model_choice: str,
    previous_scores: Optional[dict] = None,
) -> dict:
    """
    Silently infer Maslach dimension scores from the conversation.

    Args:
        messages:        Full current message history.
        model_choice:    LLM to use (key from SUPPORTED_MODELS).
        previous_scores: Fallback scores if inference fails.

    Returns:
        Dict of {dimension: score} where score is 0.0–10.0.
    """
    default = previous_scores or {d: 5.0 for d in RADAR_DIMENSIONS}

    if not messages:
        return default

    # Only send user messages — they carry the signal
    user_lines = [
        f"User: {m['content'][:350]}"
        for m in messages[-20:]
        if m["role"] == "user"
    ]
    if not user_lines:
        return default

    convo_text = "\n".join(user_lines)
    prompt = (
        "Analyze this conversation and score the 6 burnout dimensions:\n\n"
        + convo_text
    )

    try:
        raw = get_completion(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_RADAR_SYSTEM,
            model_choice=model_choice,
        )
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        scores = json.loads(cleaned)

        result = {}
        for dim in RADAR_DIMENSIONS:
            val = float(scores.get(dim, 5.0))
            result[dim] = round(max(0.0, min(10.0, val)), 1)
        return result

    except Exception as exc:
        logger.warning("Radar inference failed: %s", exc)
        return default


def render_radar_svg(scores: dict, size: int = 220) -> str:
    """
    Generate a compact SVG radar chart for the 6 Maslach dimensions.

    Colors use hardcoded warm-palette values that work in Streamlit's
    light and dark themes.

    Args:
        scores: Dict of {dimension: score (0–10)}.
        size:   SVG canvas size in pixels.

    Returns:
        An HTML string containing the SVG.
    """
    dims = RADAR_DIMENSIONS
    cx = cy = size / 2
    R = size * 0.32          # data radius
    label_R = size * 0.42   # label radius

    # Hexagon angles: start at top (−90°), step 60° clockwise
    angles = [math.radians(-90 + 60 * i) for i in range(6)]

    def pt(score: float, angle: float, radius: float = R) -> tuple:
        s = max(0.0, min(10.0, score)) / 10.0
        return (cx + s * radius * math.cos(angle),
                cy + s * radius * math.sin(angle))

    # ── Grid rings ──────────────────────────────────────────────────────────
    rings = []
    for pct in (0.33, 0.67, 1.0):
        pts = " ".join(
            f"{cx + pct*R*math.cos(a):.1f},{cy + pct*R*math.sin(a):.1f}"
            for a in angles
        )
        rings.append(
            f'<polygon points="{pts}" fill="none" '
            f'stroke="rgba(200,190,176,0.55)" stroke-width="0.5"/>'
        )

    # ── Spokes ───────────────────────────────────────────────────────────────
    spokes = [
        f'<line x1="{cx:.1f}" y1="{cy:.1f}" '
        f'x2="{cx+R*math.cos(a):.1f}" y2="{cy+R*math.sin(a):.1f}" '
        f'stroke="rgba(200,190,176,0.55)" stroke-width="0.5"/>'
        for a in angles
    ]

    # ── Data polygon ─────────────────────────────────────────────────────────
    data_pts = " ".join(
        f"{pt(scores.get(d, 5.0), a)[0]:.1f},{pt(scores.get(d, 5.0), a)[1]:.1f}"
        for d, a in zip(dims, angles)
    )
    data_poly = (
        f'<polygon points="{data_pts}" '
        f'fill="rgba(92,122,110,0.22)" stroke="#5C7A6E" stroke-width="1.5"/>'
    )

    # ── Labels and dots ──────────────────────────────────────────────────────
    labels = []
    for dim, angle in zip(dims, angles):
        score = scores.get(dim, 5.0)
        dx, dy = pt(score, angle)

        # Dot at data point
        labels.append(
            f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3" fill="#5C7A6E" opacity="0.9"/>'
        )

        # Label position
        lx = cx + label_R * math.cos(angle)
        ly = cy + label_R * math.sin(angle)
        cos_a = math.cos(angle)
        anchor = "middle" if abs(cos_a) < 0.28 else ("start" if cos_a > 0 else "end")

        labels.append(
            f'<text x="{lx:.1f}" y="{ly + 3.5:.1f}" '
            f'text-anchor="{anchor}" font-size="9" fill="#7A7265" '
            f'font-family="DM Sans, sans-serif">{dim}</text>'
        )

    svg_body = "\n".join(rings + spokes + [data_poly] + labels)

    return (
        f'<div style="display:flex;justify-content:center;padding:4px 0 0;">'
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">\n{svg_body}\n</svg></div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Feature 2 — One Small Step Tracker
# ─────────────────────────────────────────────────────────────────────────────

_STEP_SYSTEM = """You are a gentle observer of conversations. Your only job is to detect if a specific, concrete, actionable commitment was made in the last exchange.

Return ONLY valid JSON:
{"step": "description of the step"} — if a real commitment exists
{"step": null}                       — if no commitment was made

Rules:
- The step must be specific and achievable in the next 24–48 hours.
- Vague statements do NOT count ("I'll try to rest more" → null).
- Good examples: "take a 10-minute walk before my first meeting", "write down three things that felt okay today", "turn off Slack notifications after 7pm".
- If multiple commitments exist, extract only the most recent.
- Return ONLY the JSON object. No explanation, no markdown, no extra text."""


def extract_small_step(messages: list, model_choice: str) -> Optional[str]:
    """
    Extract a micro-commitment from the most recent exchange.

    Args:
        messages:     Full current message history.
        model_choice: LLM to use.

    Returns:
        Step string if a real commitment was detected, otherwise None.
    """
    if len(messages) < 2:
        return None

    # Only examine the last user + assistant pair
    last_two = messages[-2:]
    exchange_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Agent'}: {m['content'][:500]}"
        for m in last_two
    )
    prompt = (
        "Did this exchange contain a specific, actionable small step?\n\n"
        + exchange_text
    )

    try:
        raw = get_completion(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_STEP_SYSTEM,
            model_choice=model_choice,
        )
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(cleaned)
        step = result.get("step")
        return step if isinstance(step, str) and len(step) > 10 else None

    except Exception as exc:
        logger.warning("Step extraction failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Feature 3 — Session Insight Card
# ─────────────────────────────────────────────────────────────────────────────

_INSIGHT_SYSTEM = """You are a compassionate, perceptive listener. A conversation has just ended. Write a gentle reflection card — like a page from a thoughtful journal.

Return ONLY valid JSON:
{
  "themes": ["theme1", "theme2"],
  "pattern": "One sentence naming something you noticed — compassionate, never diagnostic.",
  "carry_forward": "One warm, specific thing to hold onto — a realisation, a permission, or a small truth."
}

Rules:
- themes: 2–4 short keywords (e.g. "Overload", "Isolation", "Loss of meaning", "Sleep")
- pattern: max 20 words, warm and human (e.g. "You're carrying more than you're letting yourself acknowledge.")
- carry_forward: max 28 words, specific and gentle (e.g. "You already know what needs to change — you're waiting for permission to say it.")
- Never be diagnostic, prescriptive, or toxic-positive.
- Never mention therapy or professional help here — that's handled separately.
- Return ONLY the JSON object. No explanation, no markdown, no extra text."""


def generate_insight_card(messages: list, model_choice: str) -> Optional[dict]:
    """
    Generate a compassionate end-of-session reflection card.

    Args:
        messages:     Full current message history.
        model_choice: LLM to use.

    Returns:
        Dict with keys: themes (list[str]), pattern (str), carry_forward (str).
        Returns None if there isn't enough conversation or if the call fails.
    """
    if len(messages) < 4:
        return None

    # Only send user messages — sufficient signal, lighter on tokens
    user_lines = [
        f"- {m['content'][:300]}"
        for m in messages
        if m["role"] == "user"
    ]
    convo_summary = "\n".join(user_lines[-12:])
    prompt = f"Generate a reflection card for this session. The user shared:\n{convo_summary}"

    try:
        raw = get_completion(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=_INSIGHT_SYSTEM,
            model_choice=model_choice,
        )
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(cleaned)

        if not all(k in result for k in ("themes", "pattern", "carry_forward")):
            return None
        if not isinstance(result["themes"], list):
            result["themes"] = []

        # Sanitise theme list
        result["themes"] = [str(t) for t in result["themes"][:5]]
        return result

    except Exception as exc:
        logger.warning("Insight card generation failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Farewell detection (shared utility)
# ─────────────────────────────────────────────────────────────────────────────

_FAREWELL_SIGNALS = [
    "bye", "goodbye", "good bye", "thank you", "thanks", "that's all",
    "that's enough", "i'm done", "im done", "gotta go", "have to go",
    "talk later", "see you", "see ya", "take care", "appreciate it",
    "signing off", "i think that's it", "i think thats it",
]


def is_farewell(text: str) -> bool:
    """Return True if the message looks like a session-ending message."""
    lowered = text.lower().strip()
    return any(signal in lowered for signal in _FAREWELL_SIGNALS)
