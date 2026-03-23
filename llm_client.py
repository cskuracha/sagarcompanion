"""
llm_client.py — Unified LLM interface using the Adapter pattern.

Adding a new provider:
  1. Add its entry to SUPPORTED_MODELS in config.py.
  2. Write a `_call_<provider>()` function below.
  3. Add an elif branch in `get_completion()`.
  That's it — agent.py, memory.py, safety.py are untouched.

Guarantees across providers:
  - Input:  messages: [{role, content}], system_prompt: str, model_choice: str
  - Output: plain string
  - Errors: raise descriptive exceptions (never swallow silently)
"""

import os
from typing import List, Dict

from config import SUPPORTED_MODELS, MAX_TOKENS, TEMPERATURE


# ── Public interface ───────────────────────────────────────────────────────────

def get_completion(
    messages: List[Dict[str, str]],
    system_prompt: str,
    model_choice: str,
) -> str:
    """
    Dispatch a completion request to the correct LLM provider.

    Args:
        messages:      Chat history in [{role, content}] format.
                       role must be "user" or "assistant".
        system_prompt: Agent behavioral instructions.
        model_choice:  A key from SUPPORTED_MODELS in config.py.

    Returns:
        The model's text response as a plain string.

    Raises:
        ValueError:       Unknown model_choice or provider.
        EnvironmentError: Missing API key.
        RuntimeError:     Any provider-side error, wrapped for clarity.
    """
    if model_choice not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unknown model: '{model_choice}'. "
            f"Valid options: {list(SUPPORTED_MODELS.keys())}"
        )

    cfg = SUPPORTED_MODELS[model_choice]
    provider = cfg["provider"]
    model_id = cfg["model_id"]
    api_key = os.getenv(cfg["api_key_env"], "").strip()

    if not api_key:
        raise EnvironmentError(
            f"Missing API key for '{model_choice}'. "
            f"Please set the '{cfg['api_key_env']}' environment variable."
        )

    try:
        if provider == "groq":
            return _call_groq(messages, system_prompt, model_id, api_key)
        elif provider == "gemini":
            return _call_gemini(messages, system_prompt, model_id, api_key)
        else:
            raise ValueError(f"Unsupported provider: '{provider}'")
    except (ValueError, EnvironmentError):
        raise  # re-raise configuration errors as-is
    except Exception as exc:
        raise RuntimeError(
            f"LLM call failed for provider='{provider}', model='{model_id}': {exc}"
        ) from exc


# ── Provider adapters ──────────────────────────────────────────────────────────

def _call_groq(
    messages: List[Dict[str, str]],
    system_prompt: str,
    model_id: str,
    api_key: str,
) -> str:
    """
    Groq uses an OpenAI-compatible chat completions API.
    System prompt is injected as the first message with role="system".
    """
    from groq import Groq  # lazy import — only loaded when Groq is selected

    client = Groq(api_key=api_key)

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    response = client.chat.completions.create(
        model=model_id,
        messages=full_messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content.strip()


def _call_gemini(
    messages: List[Dict[str, str]],
    system_prompt: str,
    model_id: str,
    api_key: str,
) -> str:
    """
    Gemini uses the google-generativeai SDK.

    Role mapping:
      - "user"      → "user"
      - "assistant" → "model"  (Gemini's convention)

    The system prompt is passed via `system_instruction` at model init time.
    The last message is sent via chat.send_message() — it must be from the user.
    All prior messages are passed as `history`.
    """
    import google.generativeai as genai  # lazy import

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=model_id,
        system_instruction=system_prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        ),
    )

    # Gemini's chat history excludes the final message
    history = []
    for msg in messages[:-1]:
        gemini_role = "user" if msg["role"] == "user" else "model"
        history.append({"role": gemini_role, "parts": [msg["content"]]})

    chat = model.start_chat(history=history)

    # The last message must be from the user
    if not messages:
        return ""
    last_msg = messages[-1]
    if last_msg["role"] != "user":
        # Safety guard: if last message isn't from user, append a neutral prompt
        last_content = "(Please continue.)"
    else:
        last_content = last_msg["content"]

    response = chat.send_message(last_content)
    return response.text.strip()
