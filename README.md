# 🌱 Burnout Support Agent

A warm, empathetic conversational AI agent for IT professionals, educators, and startup workers experiencing burnout or emotional exhaustion — with three unique features that set it apart from any generic chatbot.

---

## What Makes This Different

### 1 · Burnout Fingerprint Radar
A live hexagonal radar chart in the sidebar, silently updated from conversation context. It maps the discussion against **Maslach's 6 Areas of Worklife** (Workload, Control, Reward, Community, Fairness, Values) — no questionnaires, no forms. The profile emerges from what the user says.

- Runs a silent background LLM call every 3 exchanges
- Scores each dimension 0–10 (higher = more depleted)
- Includes a score breakdown bar chart (collapsible)
- Colour-coded: green (low stress) → amber (moderate) → coral (high)

### 2 · One Small Step Tracker
After every 2 exchanges, the agent silently checks whether a micro-commitment was made. If so, it's captured and shown in the sidebar — and carried into the **next session's memory** so the agent can gently follow up.

- Steps persist across sessions via the memory system
- Previous-session steps are shown separately ("From last time")
- Only specific, actionable steps qualify (vague statements are ignored)

### 3 · Session Insight Card
At session end — triggered by a "Wrap up & reflect" button or auto-detected farewell — a compassionate 3-part reflection card is generated and shown inline in the chat:

- **Themes** — 2–4 keywords extracted from the conversation
- **Something noticed** — a gentle pattern named, non-diagnostic
- **Carry forward** — one warm thing to hold onto

### Pre-session Ritual
Before the first message, users complete a 2-tap check-in:
- Energy level (Numb / Low / Okay / Alright / Overwhelmed)
- Primary concern (Work overload / Team issues / Personal burnout / Not sure)

This context is injected into the system prompt for the first exchange only, letting the agent personalise its opening without interrogating the user.

---

## Quick Start

### Local development

```bash
cd burnout_agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Option A: .env file
cp .env.example .env
# Paste your API keys into .env

# Option B: Streamlit secrets (also works locally)
# Edit .streamlit/secrets.toml and paste your API keys

streamlit run app.py
```

### Server deployment (Streamlit Cloud or self-hosted)

```
1. Push code to GitHub — secrets.toml is gitignored.
2. Streamlit Cloud → App Settings → Secrets → paste secrets.toml contents.
   Self-hosted → place filled secrets.toml at <app_dir>/.streamlit/secrets.toml.
3. Deploy. The app reads credentials from st.secrets automatically.
```

**Secrets resolution order** (first match wins):
1. `os.environ` — platform variables (Heroku, Docker, CI/CD)
2. `.streamlit/secrets.toml` — Streamlit server / Cloud
3. `.env` — local development fallback

If keys are missing or placeholder, a warning banner appears in the UI.

---

## Project Structure

```
burnout_agent/
├── .streamlit/
│   ├── secrets.toml    ← API keys for server (gitignored)
│   └── config.toml     ← Streamlit server + theme settings
│
├── config.py           ← All settings (models, limits, feature constants)
├── secrets_loader.py   ← Bridges st.secrets → os.environ at startup
├── memory.py           ← Session memory: messages + steps + radar scores
├── safety.py           ← Crisis detection + hardcoded safe response
├── llm_client.py       ← Unified LLM adapter (Groq + Gemini)
├── agent.py            ← Core orchestrator — framework-agnostic
├── features.py         ← Three unique features (radar, steps, insight card)
├── app.py              ← Streamlit UI — thin layer over everything above
├── flask_app.py        ← Flask adapter (ready for backend migration)
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Architecture

```
app.py / flask_app.py   ← UI / API layer (framework-specific)
         ↓
     agent.py           ← Orchestration (zero framework imports)
     features.py        ← Three unique features (silent LLM calls)
         ↓
 llm_client.py          ← LLM dispatch (Groq adapter, Gemini adapter)
 memory.py              ← Session memory (pure Python, storage-agnostic)
 safety.py              ← Crisis detection (no LLM, always first)
 config.py              ← All magic numbers in one place
```

**Strict layering** — each file has one job. `app.py` is the only file with Streamlit imports.

### LLM Call Budget

| Action | Calls | Frequency |
|---|---|---|
| Main agent response | 1 | Every message |
| Radar inference | 1 | Every 3rd exchange |
| Step extraction | 1 | Every 2nd exchange |
| Insight card | 1 | On demand (button) |
| **Max per message** | **2** | |

---

## Extension Points

| To add… | Change only… |
|---|---|
| A new LLM provider | `config.py` (entry) + `llm_client.py` (adapter) |
| A new UI framework | Create a new adapter (like `flask_app.py`) |
| Database-backed memory | Swap `archive_session()` in `memory.py` |
| New safety triggers | Add strings to `SAFETY_TRIGGERS` in `config.py` |
| New radar dimensions | Update `RADAR_DIMENSIONS` + `_RADAR_SYSTEM` in `features.py` |
| Different tone | Edit `_SYSTEM_PROMPT_BASE` in `agent.py` |

---

## Supported Models

| Display Name | Provider | Model ID |
|---|---|---|
| Groq – LLaMA 3.3 70B | Groq | llama-3.3-70b-versatile |
| Gemini – Flash Lite | Google | gemini-2.5-flash-lite |

---

## Safety

- Crisis detection runs **before** every LLM call — the safe response is always hardcoded.
- The agent never gives medical, diagnostic, or medication advice.
- The agent never tells the user what career decisions to make.
- A professional-help reminder is injected into the system prompt every 5 exchanges.
- India: iCall 9152987821 · Crisis Text: Text HOME to 741741

---

## Memory

- Up to 2 past sessions stored per user.
- Each session stores: messages, extracted small steps, and final radar scores.
- Steps from previous sessions surface in the sidebar ("From last time") and in the system prompt (so the agent can gently follow up).
- **Current storage:** Streamlit `session_state` (in-memory, per browser tab).
- **Production:** Swap `archive_session()` to write to Redis / PostgreSQL.

---

## Migrating to Flask

The Flask adapter is already written (`flask_app.py`). Steps:

1. Run `flask --app flask_app run`
2. Point your frontend at `/chat`
3. Replace the in-memory `SESSION_STORE` with Redis or a database
4. Feature functions (`features.py`) work identically — no changes needed

---

## ⚠️ Disclaimer

This agent is a supportive tool, not a replacement for therapy or professional mental-health care.

- **iCall (India):** 9152987821
- **Crisis Text Line:** Text HOME to 741741
- **IASP crisis centres:** https://www.iasp.info/resources/Crisis_Centres/
