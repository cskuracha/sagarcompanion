"""
app.py — Streamlit UI for the Burnout Support Agent.

This is the ONLY file that contains Streamlit imports.
The agent logic lives entirely in agent.py — this file is just presentation.

Secrets resolution order (handled by secrets_loader.py):
  1. os.environ (platform-injected, e.g. Heroku config vars)
  2. .streamlit/secrets.toml  (Streamlit Cloud / self-hosted Streamlit server)
  3. .env file  (local development fallback via python-dotenv in config.py)

Run with:
    streamlit run app.py
"""

import streamlit as st

# ── Load secrets BEFORE any LLM imports ───────────────────────────────────────
# secrets_loader pushes .streamlit/secrets.toml values into os.environ so that
# llm_client.py and config.py can use os.getenv() regardless of environment.
from secrets_loader import load_secrets_into_environ, check_required_secrets
load_secrets_into_environ()

from agent import get_agent_response
from memory import archive_session, summarise_session_for_display
from config import SUPPORTED_MODELS

# ── Page Configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Burnout Support",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS — Warm Minimalist Theme ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&family=DM+Serif+Display:ital@0;1&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #F8F5F0 !important;
    color: #2E2B26 !important;
}

/* ── App container ── */
.block-container {
    max-width: 700px !important;
    padding: 2rem 1.5rem 5rem !important;
}

/* ── Header typography ── */
.burnout-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem;
    color: #2E2B26;
    text-align: center;
    margin-bottom: 0.2rem;
}

.burnout-tagline {
    text-align: center;
    color: #7A7265;
    font-size: 1rem;
    font-style: italic;
    margin-bottom: 2rem;
}

/* ── Chat bubbles ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* User bubble */
[data-testid="stChatMessage"][data-role="user"] .stChatMessageContent {
    background: #EAE3D8 !important;
    border-radius: 20px 20px 4px 20px !important;
    padding: 12px 18px !important;
    max-width: 85% !important;
    margin-left: auto !important;
    font-size: 0.95rem;
    line-height: 1.6;
}

/* Assistant bubble */
[data-testid="stChatMessage"][data-role="assistant"] .stChatMessageContent {
    background: #FFFFFF !important;
    border: 1px solid #E5DDD3 !important;
    border-radius: 20px 20px 20px 4px !important;
    padding: 14px 18px !important;
    max-width: 92% !important;
    font-size: 0.95rem;
    line-height: 1.65;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    border-radius: 24px !important;
    border: 1.5px solid #C8BEB0 !important;
    background: #FFFFFF !important;
    padding: 12px 20px !important;
    font-size: 0.95rem !important;
    font-family: 'DM Sans', sans-serif !important;
    color: #2E2B26 !important;
}

[data-testid="stChatInput"] textarea:focus {
    border-color: #5C7A6E !important;
    box-shadow: 0 0 0 3px rgba(92, 122, 110, 0.1) !important;
}

/* ── Quick reply buttons ── */
.stButton > button {
    border-radius: 20px !important;
    background: #FFFFFF !important;
    color: #5C7A6E !important;
    border: 1.5px solid #5C7A6E !important;
    padding: 6px 16px !important;
    font-size: 0.85rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    white-space: nowrap !important;
}

.stButton > button:hover {
    background: #5C7A6E !important;
    color: #FFFFFF !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #F0EBE3 !important;
    border-right: 1px solid #E5DDD3 !important;
}

[data-testid="stSidebar"] .stButton > button {
    background: #5C7A6E !important;
    color: #FFFFFF !important;
    border: none !important;
    width: 100% !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: #4A6358 !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    border-radius: 12px !important;
    background: #FFFFFF !important;
    border-color: #C8BEB0 !important;
}

/* ── Divider ── */
hr {
    border-color: #E5DDD3 !important;
    margin: 1rem 0 !important;
}

/* ── Summary card ── */
.summary-card {
    background: #FFFFFF;
    border-left: 3px solid #5C7A6E;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.88rem;
    color: #4A4035;
    line-height: 1.5;
}

/* ── Warning note ── */
.safety-note {
    font-size: 0.82rem;
    color: #9A8F82;
    text-align: center;
    padding: 6px 0;
}
</style>
""", unsafe_allow_html=True)


# ── Session State ──────────────────────────────────────────────────────────────

def _init_session_state() -> None:
    """Initialise all session_state keys on first load."""
    defaults = {
        "messages": [],
        "past_sessions": [],
        "model_choice": list(SUPPORTED_MODELS.keys())[0],
        "exchange_count": 0,
        "show_memory_summary": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_session_state()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _send_message(user_text: str) -> None:
    """
    Append a user message, get the agent response, and update state.
    Separated from the UI so it can be reused by quick-reply buttons.
    """
    if not user_text.strip():
        return

    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_text.strip()})

    # Get agent response
    with st.spinner(""):
        response = get_agent_response(
            current_messages=st.session_state.messages,
            model_choice=st.session_state.model_choice,
            past_sessions=st.session_state.past_sessions,
            exchange_count=st.session_state.exchange_count,
        )

    # Append assistant message and increment counter
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.exchange_count += 1


def _start_new_conversation() -> None:
    """Archive the current session and reset for a new one."""
    if st.session_state.messages:
        st.session_state.past_sessions = archive_session(
            current_messages=st.session_state.messages,
            past_sessions=st.session_state.past_sessions,
        )
    st.session_state.messages = []
    st.session_state.exchange_count = 0
    st.rerun()


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")

    selected_model = st.selectbox(
        "AI Model",
        options=list(SUPPORTED_MODELS.keys()),
        index=list(SUPPORTED_MODELS.keys()).index(st.session_state.model_choice),
        help="Both models are configured to behave consistently.",
    )
    st.session_state.model_choice = selected_model

    model_info = SUPPORTED_MODELS[selected_model]
    st.caption(f"_{model_info['description']}_")

    st.markdown("---")
    st.markdown("### 🔄 Conversation")

    if st.button("✦ Start New Conversation", use_container_width=True):
        _start_new_conversation()

    if st.session_state.past_sessions:
        memory_count = len(st.session_state.past_sessions)
        st.markdown(f"📚 **{memory_count}** past session(s) in memory")

        if st.checkbox("Show past session summaries"):
            for i, session in enumerate(reversed(st.session_state.past_sessions)):
                label = "Last session" if i == 0 else f"{i+1} sessions ago"
                with st.expander(label):
                    summary = summarise_session_for_display(session)
                    st.markdown(
                        f'<div class="summary-card">{summary}</div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    st.markdown(
        '<p class="safety-note">⚠️ This is not therapy. '
        'If you\'re in crisis, please contact a mental-health professional.<br>'
        '<strong>India:</strong> iCall 9152987821 &nbsp;|&nbsp; '
        'Crisis Text: Text HOME to 741741</p>',
        unsafe_allow_html=True,
    )


# ── Main UI ────────────────────────────────────────────────────────────────────

# Header
st.markdown('<h1 class="burnout-title">🌱 Burnout Support</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="burnout-tagline">A gentle space to think, breathe, and be heard.</p>',
    unsafe_allow_html=True,
)

# ── Setup Warning — shown if API keys are missing ────────────────────────────
_missing_keys = check_required_secrets()
if _missing_keys:
    st.warning(
        "**Setup needed:** The following API keys are missing or contain placeholder values:\n\n"
        + "\n".join(f"- `{k}`" for k in _missing_keys)
        + "\n\nAdd them to `.streamlit/secrets.toml` (server) or `.env` (local).",
        icon="🔑",
    )

# Welcome + Quick replies — shown only on an empty session
if not st.session_state.messages:
    st.markdown("**How are you feeling today?** You can type anything, or choose a starting point:")

    QUICK_REPLIES = [
        "I feel overwhelmed",
        "Work stress",
        "I can't sleep",
        "I feel disconnected",
        "Personal burnout",
        "I don't know where to start",
    ]

    # Layout quick replies in two rows of three
    row1 = st.columns(3)
    row2 = st.columns(3)
    button_grid = row1 + row2

    for col, reply in zip(button_grid, QUICK_REPLIES):
        with col:
            if st.button(reply, key=f"qr_{reply}"):
                _send_message(reply)
                st.rerun()

    st.markdown("---")

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if user_input := st.chat_input("Share what's on your mind…"):
    _send_message(user_input)
    st.rerun()
