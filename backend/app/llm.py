"""LLM providers. Each one streams text and, at the end, a Usage object with token counts."""
import json
import logging
from dataclasses import dataclass
from typing import Iterator

import httpx

from app.config import settings

log = logging.getLogger(__name__)


class ProviderError(Exception):
    """A provider failed. The message is for server logs only and is never shown to users."""


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def stream(self, system: str, user: str) -> Iterator[str | Usage]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?alt=sse"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
        }
        headers = {"x-goog-api-key": self.api_key}  # in a header so it never shows up in logged URLs
        usage = None
        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=5.0)) as client:
                with client.stream("POST", url, json=body, headers=headers) as response:
                    if response.status_code != 200:
                        raise ProviderError(f"gemini returned HTTP {response.status_code}")
                    for line in response.iter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = json.loads(line[5:].strip() or "{}")
                        for candidate in data.get("candidates", []):
                            for part in candidate.get("content", {}).get("parts", []):
                                if part.get("text"):
                                    yield part["text"]
                        meta = data.get("usageMetadata")
                        if meta:
                            usage = Usage(meta.get("promptTokenCount", 0), meta.get("candidatesTokenCount", 0))
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderError(f"gemini failed: {type(error).__name__}") from error
        if usage:
            yield usage


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str, timeout: float):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def stream(self, system: str, user: str) -> Iterator[str | Usage]:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": True,
            "temperature": 0.4,
            "max_tokens": 600,
            "stream_options": {"include_usage": True},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        usage = None
        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=5.0)) as client:
                with client.stream(
                    "POST", "https://api.groq.com/openai/v1/chat/completions", json=body, headers=headers
                ) as response:
                    if response.status_code != 200:
                        raise ProviderError(f"groq returned HTTP {response.status_code}")
                    for line in response.iter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if not payload or payload == "[DONE]":
                            continue
                        data = json.loads(payload)
                        for choice in data.get("choices", []):
                            text = choice.get("delta", {}).get("content")
                            if text:
                                yield text
                        raw = data.get("usage") or data.get("x_groq", {}).get("usage")
                        if raw:
                            usage = Usage(raw.get("prompt_tokens", 0), raw.get("completion_tokens", 0))
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderError(f"groq failed: {type(error).__name__}") from error
        if usage:
            yield usage


def default_providers() -> list:
    """Providers in the order they are tried. A provider without an API key is skipped."""
    providers = []
    if settings.gemini_api_key:
        providers.append(GeminiProvider(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_seconds))
    if settings.groq_api_key:
        providers.append(GroqProvider(settings.groq_api_key, settings.groq_model, settings.llm_timeout_seconds))
    return providers
