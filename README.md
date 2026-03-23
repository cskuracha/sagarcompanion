# 🌱 Burnout Support Agent

A warm, empathetic conversational AI agent for IT professionals, educators, and startup workers experiencing burnout or emotional exhaustion.

---

## Quick Start

### Local development

```bash
# 1. Clone / copy the project folder
cd burnout_agent

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4a. Local: use a .env file
cp .env.example .env
# Edit .env and paste in your API keys

# 4b. OR use Streamlit secrets (works locally too)
# Edit .streamlit/secrets.toml and paste in your API keys

# 5. Run the Streamlit app
streamlit run app.py
```

### Server deployment (Streamlit Community Cloud or self-hosted)

```
1. Push your code to GitHub — secrets.toml is in .gitignore, so keys stay local.
2. In Streamlit Cloud → App Settings → Secrets, paste the contents of secrets.toml.
   For a self-hosted server, place the filled-in secrets.toml at:
       <your_app_dir>/.streamlit/secrets.toml
3. Deploy. The app reads credentials from st.secrets automatically.
```

**Secrets resolution order** (first match wins):
1. `os.environ` — platform-injected variables (Heroku config vars, Docker env, etc.)
2. `.streamlit/secrets.toml` — Streamlit server / Cloud
3. `.env` — local development fallback

If keys are missing or still contain placeholders, a warning banner appears in the UI.

---

## Project Structure

```
burnout_agent/
├── .streamlit/
│   ├── secrets.toml    ← API keys for server deployment (gitignored)
│   └── config.toml     ← Streamlit server + theme settings
├── config.py           ← Single source of truth (models, limits, safety triggers)
├── secrets_loader.py   ← Bridges st.secrets → os.environ at startup
├── memory.py           ← Memory management (last 2 sessions, context building)
├── safety.py           ← Crisis detection + hardcoded safe response
├── llm_client.py       ← Unified LLM adapter (Groq + Gemini)
├── agent.py            ← Core orchestrator — framework-agnostic
├── app.py              ← Streamlit UI (thin layer over agent.py)
├── flask_app.py        ← Flask adapter (ready for backend migration)
├── requirements.txt
├── .env.example        ← Template for local .env
├── .gitignore          ← Ensures secrets are never committed
└── README.md
```

---

## Architecture Philosophy

**Strict layering** — each file has one job:

```
app.py / flask_app.py   ← UI / API layer (framework-specific)
        ↓
    agent.py            ← Orchestration (framework-agnostic)
        ↓
llm_client.py           ← LLM dispatch (provider-specific adapters)
memory.py               ← Session memory (pure Python, swappable storage)
safety.py               ← Crisis detection (no LLM dependency)
config.py               ← Configuration (all magic numbers live here)
```

**Extension points:**

| To add...                | Change only...                              |
|--------------------------|---------------------------------------------|
| A new LLM provider       | `config.py` (entry) + `llm_client.py` (handler) |
| A new UI framework       | Create a new adapter file (like `flask_app.py`) |
| Database-backed memory   | Swap `archive_session()` in `memory.py`     |
| New safety triggers      | Add strings to `SAFETY_TRIGGERS` in `config.py` |
| Different tone rules     | Edit `_SYSTEM_PROMPT_BASE` in `agent.py`    |

---

## Supported Models

| Display Name            | Provider | Model ID                  |
|-------------------------|----------|---------------------------|
| Groq – LLaMA 3.3 70B   | Groq     | llama-3.3-70b-versatile   |
| Gemini – Flash Lite     | Google   | gemini-2.5-flash-lite     |

---

## Safety

- Crisis detection runs **before** the LLM call — the safe response is always hardcoded.
- The agent never gives medical, diagnostic, or medication advice.
- The agent never tells the user what career decisions to make.
- A professional-help reminder is injected every 5 exchanges.

---

## Memory

- Up to 2 past sessions are stored per user.
- Memory is injected into the system prompt as context.
- The agent uses it to maintain continuity and avoid repeating questions.
- **Current storage:** Streamlit `session_state` (in-memory, per browser tab).
- **Production:** Swap `archive_session()` to write to Redis / PostgreSQL.

---

## Migrating to Flask

The Flask adapter is already written (`flask_app.py`). Steps to migrate:

1. Run `flask --app flask_app run`
2. Point your frontend at the `/chat` endpoint
3. Replace the in-memory `SESSION_STORE` with Redis or a database

No changes needed to `agent.py`, `memory.py`, `safety.py`, or `config.py`.

---

## ⚠️ Disclaimer

This agent is a supportive tool, not a replacement for therapy or professional mental-health care. If you or someone you know is in crisis, please contact:

- **iCall (India):** 9152987821
- **Crisis Text Line:** Text HOME to 741741
- **IASP crisis centres:** https://www.iasp.info/resources/Crisis_Centres/
