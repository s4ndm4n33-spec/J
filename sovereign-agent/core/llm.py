"""
LLM interface — talks to Ollama locally.
Supports both blocking and streaming responses.
Tuned to match J.'s Modelfile parameters.
"""

import json
import requests
from typing import Generator, Optional

# ── Defaults (matched to J.'s Modelfile) ────────────────────────
DEFAULT_MODEL = "brain"       # Mike's custom model (brain:latest)
OLLAMA_URL = "http://localhost:11434"
DEFAULT_CTX = 8192            # Vulkan-optimized context window
DEFAULT_TEMP = 0.8            # Warm — matches J.'s personality
DEFAULT_REPEAT_PENALTY = 1.1  # Prevents logic loops


def query(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMP,
    num_ctx: int = DEFAULT_CTX,
) -> str:
    """Blocking call — returns the full response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "repeat_penalty": DEFAULT_REPEAT_PENALTY,
        },
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.ConnectionError:
        return json.dumps({"message": "ERROR: Cannot connect to Ollama. Is it running? (ollama serve)"})
    except Exception as e:
        return json.dumps({"message": f"ERROR: {e}"})


def query_stream(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMP,
    num_ctx: int = DEFAULT_CTX,
) -> Generator[str, None, None]:
    """Streaming call — yields text chunks as they arrive."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "repeat_penalty": DEFAULT_REPEAT_PENALTY,
        },
    }
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate", json=payload, stream=True, timeout=180
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done"):
                    break
    except requests.ConnectionError:
        yield '{"message": "ERROR: Cannot connect to Ollama. Is it running?"}'
    except Exception as e:
        yield f'{{"message": "ERROR: {e}"}}'


def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMP,
    num_ctx: int = DEFAULT_CTX,
) -> str:
    """
    Chat-completion style call using Ollama's /api/chat endpoint.
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "repeat_penalty": DEFAULT_REPEAT_PENALTY,
        },
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()
    except requests.ConnectionError:
        return json.dumps({"message": "ERROR: Cannot connect to Ollama. Is it running? (ollama serve)"})
    except Exception as e:
        return json.dumps({"message": f"ERROR: {e}"})
