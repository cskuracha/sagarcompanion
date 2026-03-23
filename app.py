"""
app.py — Streamlit UI for the Burnout Support Agent.

This is the ONLY file that contains Streamlit imports.
All agent logic lives in agent.py, features.py, memory.py — framework-agnostic.

Three unique features added in this version:
  1. Burnout Fingerprint Radar  — sidebar SVG radar, updated from conversation
  2. One Small Step Tracker     — micro-commitments extracted and tracked
  3. Session Insight Card       — compassionate reflection generated at session end

Plus: Pre-session ritual (energy + concern check-in before first message).

Secrets resolution order (handled by secrets_loader.py):
  1. os.environ  (platform-injected)
  2. .streamlit/secrets.toml  (Streamlit Cloud / self-hosted server)
  3. .env        (local development fallback)

Run with:
    streamlit run app.py
"""

import streamlit as st

# ── Load secrets BEFORE any LLM imports ───────────────────────────────────────
from secrets_loader import load_secrets_into_environ, check_required_secrets
load_secrets_into_environ()

from agent import get_agent_response
from memory import archive_session, summarise_session_for_display
from features import (
    infer_radar_scores,
    render_radar_svg,
    extract_small_step,
    generate_insight_card,
    is_farewell,
)
from config import (
    SUPPORTED_MODELS,
    RADAR_DIMENSIONS,
    RADAR_UPDATE_EVERY_N,
    STEP_CHECK_EVERY_N,
    ENERGY_OPTIONS,
    CONCERN_OPTIONS,
)

# ── Page Configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Burnout Support",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&family=DM+Serif+Display:ital@0;1&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #F8F5F0 !important;
    color: #2E2B26 !important;
}
.block-container { max-width: 700px !important; padding: 2rem 1.5rem 5rem !important; }

/* ── Header ── */
.burnout-title  { font-family:'DM Serif Display',serif; font-size:2.1rem; color:#2E2B26; text-align:center; margin-bottom:0.2rem; }
.burnout-tagline{ text-align:center; color:#7A7265; font-size:1rem; font-style:italic; margin-bottom:1.5rem; }

/* ── Chat bubbles ── */
[data-testid="stChatMessage"] { background:transparent !important; border:none !important; padding:0 !important; }
[data-testid="stChatMessage"][data-role="user"]      .stChatMessageContent { background:#EAE3D8 !important; border-radius:20px 20px 4px 20px !important; padding:12px 18px !important; max-width:85% !important; margin-left:auto !important; font-size:.95rem; line-height:1.6; }
[data-testid="stChatMessage"][data-role="assistant"] .stChatMessageContent { background:#FFFFFF !important; border:1px solid #E5DDD3 !important; border-radius:20px 20px 20px 4px !important; padding:14px 18px !important; max-width:92% !important; font-size:.95rem; line-height:1.65; box-shadow:0 1px 4px rgba(0,0,0,.04); }

/* ── Chat input ── */
[data-testid="stChatInput"] textarea { border-radius:24px !important; border:1.5px solid #C8BEB0 !important; background:#FFFFFF !important; padding:12px 20px !important; font-size:.95rem !important; font-family:'DM Sans',sans-serif !important; color:#2E2B26 !important; }
[data-testid="stChatInput"] textarea:focus { border-color:#5C7A6E !important; box-shadow:0 0 0 3px rgba(92,122,110,.1) !important; }

/* ── Buttons ── */
.stButton > button { border-radius:20px !important; background:#FFFFFF !important; color:#5C7A6E !important; border:1.5px solid #5C7A6E !important; padding:6px 16px !important; font-size:.85rem !important; font-family:'DM Sans',sans-serif !important; font-weight:500 !important; transition:all .2s ease !important; }
.stButton > button:hover { background:#5C7A6E !important; color:#FFFFFF !important; }

/* ── Ritual buttons (energy / concern) ── */
.ritual-btn > button { border-radius:20px !important; background:#FFFFFF !important; color:#7A7265 !important; border:1.5px solid #C8BEB0 !important; padding:5px 14px !important; font-size:.83rem !important; width:100% !important; }
.ritual-btn-active > button { background:#EAF3DE !important; color:#3B6D11 !important; border-color:#639922 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background:#F0EBE3 !important; border-right:1px solid #E5DDD3 !important; }
[data-testid="stSidebar"] .stButton > button { background:#5C7A6E !important; color:#FFFFFF !important; border:none !important; width:100% !important; }
[data-testid="stSidebar"] .stButton > button:hover { background:#4A6358 !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div { border-radius:12px !important; background:#FFFFFF !important; border-color:#C8BEB0 !important; }

/* ── Insight card ── */
.insight-card { background:#FFFFFF; border:1px solid #E5DDD3; border-radius:16px; padding:20px 22px; margin:12px 0; box-shadow:0 2px 8px rgba(0,0,0,.05); }
.insight-themes { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:14px; }
.insight-theme-chip { background:#EAF3DE; color:#3B6D11; border-radius:20px; padding:3px 12px; font-size:.78rem; font-weight:500; }
.insight-pattern { color:#4A4035; font-size:.93rem; line-height:1.6; margin-bottom:10px; border-left:3px solid #5C7A6E; padding-left:12px; }
.insight-carry { color:#5C7A6E; font-size:.88rem; font-style:italic; line-height:1.55; }
.insight-label { font-size:.75rem; font-weight:500; color:#9A8F82; text-transform:uppercase; letter-spacing:.06em; margin-bottom:4px; }

/* ── Step tracker ── */
.step-item { background:#FFFFFF; border-left:3px solid #5C7A6E; border-radius:0 8px 8px 0; padding:8px 12px; margin:6px 0; font-size:.82rem; color:#4A4035; line-height:1.5; }
.step-old  { border-left-color:#C8BEB0; color:#7A7265; }

/* ── Radar section label ── */
.section-label { font-size:.72rem; font-weight:500; color:#9A8F82; text-transform:uppercase; letter-spacing:.08em; margin:0 0 6px; }

/* ── Safety note ── */
.safety-note { font-size:.78rem; color:#9A8F82; text-align:center; padding:6px 0; line-height:1.5; }

hr { border-color:#E5DDD3 !important; margin:1rem 0 !important; }
</style>
""", unsafe_allow_html=True)


# ── Session State Initialisation ───────────────────────────────────────────────

def _init_session_state() -> None:
    defaults = {
        # Core chat
        "messages":       [],
        "past_sessions":  [],
        "model_choice":   list(SUPPORTED_MODELS.keys())[0],
        "exchange_count": 0,
        # Pre-session ritual
        "ritual_done":    False,
        "ritual_energy":  None,     # selected energy label
        "ritual_concern": None,     # selected concern label
        # Feature 1: Radar
        "radar_scores":   {d: 5.0 for d in RADAR_DIMENSIONS},
        "radar_ready":    False,    # True after first inference
        # Feature 2: Steps
        "small_steps":    [],       # list of step strings this session
        # Feature 3: Insight card
        "insight_card":   None,     # dict or None
        "insight_shown":  False,
        "suggest_insight":False,    # True when farewell detected
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_session_state()


# ── Helper: ritual context string ─────────────────────────────────────────────

def _build_ritual_context() -> str:
    """Build the ritual context string injected into the system prompt."""
    parts = []
    if st.session_state.ritual_energy:
        parts.append(f"Energy level: {st.session_state.ritual_energy}")
    if st.session_state.ritual_concern:
        parts.append(f"Primary concern: {st.session_state.ritual_concern}")
    return ". ".join(parts) + "." if parts else ""


# ── Helper: send message ──────────────────────────────────────────────────────

def _send_message(user_text: str) -> None:
    """
    Core message handler — appends user msg, fetches agent response,
    then runs background feature inference.
    """
    if not user_text.strip():
        return

    user_text = user_text.strip()

    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_text})

    # ── Main agent response ────────────────────────────────────────────────
    # Only pass ritual context on first exchange
    ritual_ctx = _build_ritual_context() if st.session_state.exchange_count == 0 else ""

    with st.spinner(""):
        response = get_agent_response(
            current_messages=st.session_state.messages,
            model_choice=st.session_state.model_choice,
            past_sessions=st.session_state.past_sessions,
            exchange_count=st.session_state.exchange_count,
            ritual_context=ritual_ctx,
        )

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.exchange_count += 1
    count = st.session_state.exchange_count

    # ── Feature 1: Radar inference (every RADAR_UPDATE_EVERY_N exchanges) ─
    if count % RADAR_UPDATE_EVERY_N == 0 or count == 1:
        try:
            st.session_state.radar_scores = infer_radar_scores(
                messages=st.session_state.messages,
                model_choice=st.session_state.model_choice,
                previous_scores=st.session_state.radar_scores,
            )
            st.session_state.radar_ready = True
        except Exception:
            pass  # silent fail — radar not critical

    # ── Feature 2: Step extraction (every STEP_CHECK_EVERY_N exchanges) ──
    if count % STEP_CHECK_EVERY_N == 0:
        try:
            step = extract_small_step(
                messages=st.session_state.messages,
                model_choice=st.session_state.model_choice,
            )
            if step and step not in st.session_state.small_steps:
                st.session_state.small_steps.append(step)
        except Exception:
            pass  # silent fail — step tracking not critical

    # ── Farewell detection → suggest insight card ──────────────────────────
    if is_farewell(user_text) and not st.session_state.insight_shown:
        st.session_state.suggest_insight = True


# ── Helper: new conversation ──────────────────────────────────────────────────

def _start_new_conversation() -> None:
    """Archive current session and reset all state for a fresh start."""
    if st.session_state.messages:
        st.session_state.past_sessions = archive_session(
            current_messages=st.session_state.messages,
            past_sessions=st.session_state.past_sessions,
            small_steps=st.session_state.small_steps,
            radar_scores=st.session_state.radar_scores,
        )
    # Reset everything except past_sessions, model_choice
    st.session_state.messages       = []
    st.session_state.exchange_count = 0
    st.session_state.ritual_done    = False
    st.session_state.ritual_energy  = None
    st.session_state.ritual_concern = None
    st.session_state.radar_scores   = {d: 5.0 for d in RADAR_DIMENSIONS}
    st.session_state.radar_ready    = False
    st.session_state.small_steps    = []
    st.session_state.insight_card   = None
    st.session_state.insight_shown  = False
    st.session_state.suggest_insight= False
    st.rerun()


# ── Helper: render insight card HTML ─────────────────────────────────────────

def _render_insight_card(card: dict) -> str:
    themes_html = "".join(
        f'<span class="insight-theme-chip">{t}</span>'
        for t in card.get("themes", [])
    )
    return f"""
<div class="insight-card">
  <p class="section-label">✦ Session reflection</p>
  <div class="insight-themes">{themes_html}</div>
  <p class="insight-label">Something noticed</p>
  <p class="insight-pattern">{card.get("pattern", "")}</p>
  <p class="insight-label">Carry forward</p>
  <p class="insight-carry">{card.get("carry_forward", "")}</p>
</div>
"""


# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════

with st.sidebar:

    # ── Settings ──────────────────────────────────────────────────────────────
    st.markdown("### ⚙️ Settings")
    selected_model = st.selectbox(
        "AI Model",
        options=list(SUPPORTED_MODELS.keys()),
        index=list(SUPPORTED_MODELS.keys()).index(st.session_state.model_choice),
    )
    st.session_state.model_choice = selected_model
    st.caption(f"_{SUPPORTED_MODELS[selected_model]['description']}_")

    st.markdown("---")

    # ── Feature 1: Burnout Fingerprint Radar ──────────────────────────────────
    st.markdown('<p class="section-label">🔬 Burnout fingerprint</p>', unsafe_allow_html=True)

    if not st.session_state.radar_ready or not st.session_state.messages:
        st.caption("_Your profile will appear after a few exchanges._")
    else:
        radar_svg_html = render_radar_svg(st.session_state.radar_scores, size=220)
        st.markdown(radar_svg_html, unsafe_allow_html=True)
        st.caption("_Inferred from your conversation · Maslach's 6 dimensions_")

        # Score breakdown as a small detail
        with st.expander("View scores"):
            for dim in RADAR_DIMENSIONS:
                score = st.session_state.radar_scores.get(dim, 5.0)
                bar_pct = int(score * 10)
                color = "#D85A30" if score >= 7 else "#5C7A6E" if score <= 4 else "#BA7517"
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
                    f'<span style="font-size:.75rem;color:#7A7265;width:72px;">{dim}</span>'
                    f'<div style="flex:1;background:#E5DDD3;border-radius:4px;height:5px;">'
                    f'<div style="width:{bar_pct}%;background:{color};border-radius:4px;height:5px;"></div>'
                    f'</div>'
                    f'<span style="font-size:.75rem;color:#7A7265;width:24px;text-align:right;">{score:.0f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # ── Feature 2: One Small Step Tracker ─────────────────────────────────────
    st.markdown('<p class="section-label">✦ One small step</p>', unsafe_allow_html=True)

    # Steps from previous sessions
    prev_steps = []
    for raw_session in st.session_state.past_sessions:
        if isinstance(raw_session, dict):
            prev_steps.extend(raw_session.get("small_steps", []))
        # legacy sessions have no steps

    if prev_steps:
        st.caption("_From last time — how did these go?_")
        for step in prev_steps[-3:]:  # show last 3 at most
            st.markdown(
                f'<div class="step-item step-old">↩ {step}</div>',
                unsafe_allow_html=True,
            )

    if st.session_state.small_steps:
        if prev_steps:
            st.caption("_This session:_")
        for step in st.session_state.small_steps:
            st.markdown(
                f'<div class="step-item">✦ {step}</div>',
                unsafe_allow_html=True,
            )
    elif not prev_steps:
        st.caption("_Small steps you commit to will appear here._")

    st.markdown("---")

    # ── Conversation controls ─────────────────────────────────────────────────
    st.markdown("### 🔄 Conversation")

    if st.button("✦ Start New Conversation", use_container_width=True):
        _start_new_conversation()

    # Feature 3 trigger: "Wrap up & reflect"
    if st.session_state.messages and not st.session_state.insight_shown:
        if st.button("🌿 Wrap up & reflect", use_container_width=True):
            with st.spinner("Creating your reflection…"):
                card = generate_insight_card(
                    messages=st.session_state.messages,
                    model_choice=st.session_state.model_choice,
                )
            if card:
                st.session_state.insight_card   = card
                st.session_state.insight_shown  = True
                st.session_state.suggest_insight = False
            st.rerun()

    if st.session_state.past_sessions:
        memory_count = len(st.session_state.past_sessions)
        st.markdown(f"📚 **{memory_count}** past session(s) in memory")
        if st.checkbox("Show past session summaries"):
            for i, session in enumerate(reversed(st.session_state.past_sessions)):
                label = "Last session" if i == 0 else f"{i+1} sessions ago"
                with st.expander(label):
                    summary = summarise_session_for_display(session)
                    st.markdown(
                        f'<div style="background:#FFFFFF;border-left:3px solid #5C7A6E;'
                        f'border-radius:0 8px 8px 0;padding:10px 14px;font-size:.83rem;'
                        f'color:#4A4035;line-height:1.5;">{summary}</div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    st.markdown(
        '<p class="safety-note">⚠️ Not a substitute for therapy.<br>'
        '<strong>India:</strong> iCall 9152987821<br>'
        'Crisis Text: Text HOME to 741741</p>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ════════════════════════════════════════════════════════════════════════════════

# ── Setup Warning ──────────────────────────────────────────────────────────────
_missing_keys = check_required_secrets()
if _missing_keys:
    st.warning(
        "**Setup needed:** Missing API keys:\n\n"
        + "\n".join(f"- `{k}`" for k in _missing_keys)
        + "\n\nAdd them to `.streamlit/secrets.toml` (server) or `.env` (local).",
        icon="🔑",
    )

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="burnout-title">🌱 Burnout Support</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="burnout-tagline">A gentle space to think, breathe, and be heard.</p>',
    unsafe_allow_html=True,
)

# ── Pre-session Ritual ─────────────────────────────────────────────────────────
# Shown only on empty sessions before the ritual is complete.
if not st.session_state.messages and not st.session_state.ritual_done:

    st.markdown("#### Before we begin — a quick check-in")
    st.markdown("_Two taps, then we'll start. No right answers._")
    st.markdown("")

    # Energy level
    st.markdown("**How's your energy right now?**")
    energy_cols = st.columns(len(ENERGY_OPTIONS))
    for col, opt in zip(energy_cols, ENERGY_OPTIONS):
        css_class = (
            "ritual-btn-active" if st.session_state.ritual_energy == opt else "ritual-btn"
        )
        with col:
            # Wrap in a div with the right class
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            if st.button(opt, key=f"energy_{opt}"):
                st.session_state.ritual_energy = opt
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("")
    # Concern area
    st.markdown("**What's on your mind today?**")
    concern_cols = st.columns(len(CONCERN_OPTIONS))
    for col, opt in zip(concern_cols, CONCERN_OPTIONS):
        css_class = (
            "ritual-btn-active" if st.session_state.ritual_concern == opt else "ritual-btn"
        )
        with col:
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            if st.button(opt, key=f"concern_{opt}"):
                st.session_state.ritual_concern = opt
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("")

    # Begin button (always available — ritual selections are optional)
    begin_label = "Begin →" if not (st.session_state.ritual_energy or st.session_state.ritual_concern) else "Begin with this context →"
    if st.button(begin_label, type="primary"):
        st.session_state.ritual_done = True
        st.rerun()

    st.markdown("---")

# ── Quick Replies (shown after ritual, on empty chat) ─────────────────────────
elif not st.session_state.messages and st.session_state.ritual_done:
    st.markdown("**How are you feeling today?** You can type anything, or choose a starting point:")

    QUICK_REPLIES = [
        "I feel overwhelmed",
        "Work stress",
        "I can't sleep",
        "I feel disconnected",
        "Personal burnout",
        "I don't know where to start",
    ]
    row1 = st.columns(3)
    row2 = st.columns(3)
    for col, reply in zip(row1 + row2, QUICK_REPLIES):
        with col:
            if st.button(reply, key=f"qr_{reply}"):
                _send_message(reply)
                st.rerun()

    st.markdown("---")

# ── Insight card suggestion (auto-detected farewell) ──────────────────────────
if st.session_state.suggest_insight and not st.session_state.insight_shown:
    st.info(
        "It sounds like you're wrapping up. Would you like a gentle reflection on what we explored today?",
        icon="🌿",
    )
    col_yes, col_no, _ = st.columns([1, 1, 2])
    with col_yes:
        if st.button("Yes, reflect", key="insight_yes"):
            with st.spinner("Creating your reflection…"):
                card = generate_insight_card(
                    messages=st.session_state.messages,
                    model_choice=st.session_state.model_choice,
                )
            if card:
                st.session_state.insight_card  = card
                st.session_state.insight_shown = True
            st.session_state.suggest_insight = False
            st.rerun()
    with col_no:
        if st.button("Not now", key="insight_no"):
            st.session_state.suggest_insight = False
            st.rerun()

# ── Chat History ───────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Feature 3: Insight Card (inline in chat after messages) ───────────────────
if st.session_state.insight_card and st.session_state.insight_shown:
    st.markdown(
        _render_insight_card(st.session_state.insight_card),
        unsafe_allow_html=True,
    )

# ── Chat Input ────────────────────────────────────────────────────────────────
# Always show — even before ritual (skip button is available)
if st.session_state.ritual_done or st.session_state.messages:
    if user_input := st.chat_input("Share what's on your mind…"):
        _send_message(user_input)
        st.rerun()
