"""LLM access through Ollama, behind a small interface so tests can mock it."""
from __future__ import annotations

from typing import Protocol

import httpx

SYSTEM_PROMPT = """You are BMSCE Campus, a friendly AI assistant.

You can answer both general questions and college placement-policy questions.

Choose how to answer based on the user's question:

1. GENERAL QUESTIONS
- Answer general questions using your general knowledge.
- Examples include greetings, introductions, programming, AI, machine learning,
  mathematics, technology, writing, and everyday questions.
- Explain concepts in simple, everyday English.
- Use short sentences and examples when helpful.
- Do not require retrieved placement-policy text for general questions.
- If asked who you are, say:
  "I'm BMSCE Campus, your AI assistant. I can answer general questions
  and help students understand college placement policies."

2. PLACEMENT-POLICY QUESTIONS
- Use only the retrieved official placement-policy excerpts for college-specific rules.
- Never invent eligibility criteria, CGPA cutoffs, deadlines, company restrictions,
  offer rules, punishments, or exceptions.
- If the retrieved evidence is insufficient, say:
  "The available placement policy does not give a clear answer to this question.
  Please contact the placement office to confirm."
- Explain policy rules in simple English.
- Preserve the meaning of words such as "may", "must", "can", and "will".
- Never describe a possible punishment as automatic or guaranteed.
- Do not include PDF filenames, page numbers, or bracketed citations in the answer.
- Do not pretend to be an official college decision-maker.

3. ANSWER STYLE
- Answer the user's exact question first.
- Use short, clear sentences and common words.
- Avoid unnecessary technical terms and repetition.
- Use bullet points when they improve readability.
- Give a concise answer unless the user asks for more detail.
- If a general question and a placement-policy question are combined,
  answer the general part normally and the policy part using retrieved evidence.
"""


class LLMError(RuntimeError):
    """The LLM backend is unreachable or returned an unusable response."""


class ConfigurationError(ValueError):
    """The LLM settings are missing or inconsistent."""


PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "xai": "https://api.x.ai/v1",
}


class LLM(Protocol):
    model_name: str

    def generate(self, system: str, prompt: str) -> str: ...

    def is_available(self) -> bool: ...


class OllamaLLM:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        temperature: float = 0.1,
        timeout: float = 120.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self.model_name = model_name
        self._temperature = temperature
        self._timeout = timeout

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self._base}/api/tags", timeout=3.0)
            if r.status_code != 200:
                return False
            names = {m.get("name") for m in r.json().get("models", [])}
            return any(n == self.model_name or (n or "").startswith(self.model_name + ":") for n in names)
        except (httpx.HTTPError, ValueError):
            return False

    def generate(self, system: str, prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "stream": False,
            "options": {"temperature": self._temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            r = httpx.post(f"{self._base}/api/chat", json=payload, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach Ollama at {self._base}: {exc}") from exc
        if r.status_code != 200:
            raise LLMError(f"Ollama returned HTTP {r.status_code}: {r.text[:200]}")
        try:
            content = r.json()["message"]["content"]
        except (KeyError, ValueError) as exc:
            raise LLMError("Unexpected response format from Ollama.") from exc
        if not content or not content.strip():
            raise LLMError("Ollama returned an empty answer.")
        return content.strip()


def _api_error_detail(response, api_key: str) -> str:
    """Short provider error message, with the API key redacted. Empty if unavailable."""
    try:
        err = response.json().get("error")
    except Exception:
        return ""
    msg = err.get("message") if isinstance(err, dict) else None
    if not isinstance(msg, str):
        return ""
    if api_key:
        msg = msg.replace(api_key, "[redacted]")
    return " Provider says: " + msg.strip()[:240]


class OpenAICompatibleLLM:
    """Chat-completions client for OpenAI-compatible APIs (Groq, xAI, ...).

    The API key is only ever sent in the Authorization header and is never
    included in logs or error messages.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        temperature: float = 0.1,
        timeout: float = 60.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._key = api_key
        self.model_name = model_name
        self._temperature = temperature
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self._base}/models", headers=self._headers(), timeout=5.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def generate(self, system: str, prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "temperature": self._temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            r = httpx.post(
                f"{self._base}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach the LLM API: {type(exc).__name__}") from exc

        detail = _api_error_detail(r, self._key)
        if r.status_code in (401, 403):
            raise LLMError("The LLM API rejected the API key (check LLM_API_KEY)." + detail)
        if r.status_code == 404:
            raise LLMError(
                f"The LLM API returned 'not found' for model '{self.model_name}' "
                f"or the endpoint (check LLM_MODEL, LLM_PROVIDER and LLM_BASE_URL)." + detail
            )
        if r.status_code in (400, 422):
            raise LLMError(f"The LLM API rejected the request (HTTP {r.status_code})." + detail)
        if r.status_code == 429:
            raise LLMError("The LLM API rate limit was hit. Try again shortly.")
        if r.status_code != 200:
            raise LLMError(f"The LLM API returned HTTP {r.status_code}." + detail)
        try:
            content = r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("Unexpected response format from the LLM API.") from exc
        if not content or not content.strip():
            raise LLMError("The LLM API returned an empty answer.")
        return content.strip()


def build_llm(
    *,
    provider: str,
    model: str,
    ollama_base_url: str,
    api_key: str = "",
    base_url: str = "",
    temperature: float = 0.1,
    timeout: float = 120.0,
) -> LLM:
    provider = provider.lower()
    if provider == "ollama":
        return OllamaLLM(ollama_base_url, model, temperature, timeout)
    if provider in {"groq", "xai", "openai_compatible"}:
        if not api_key:
            raise ConfigurationError(f"LLM_API_KEY is required when LLM_PROVIDER={provider}.")
        if model == "llama3.2:3b" or not model:
            raise ConfigurationError(
                "Set LLM_MODEL to a model name from your provider's console "
                "(the Ollama default 'llama3.2:3b' is not valid for a cloud API)."
            )
        url = base_url or PROVIDER_BASE_URLS.get(provider, "")
        if not url:
            raise ConfigurationError("LLM_BASE_URL is required when LLM_PROVIDER=openai_compatible.")
        return OpenAICompatibleLLM(url, api_key, model, temperature, min(timeout, 60.0))
    raise ConfigurationError(
        f"Unknown LLM_PROVIDER '{provider}'. Use ollama, groq, xai or openai_compatible."
    )
