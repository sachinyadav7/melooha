"""Runs one question through the providers and the grounding check.

Yields events for the API to stream:
  ("token", text)   a piece of the answer
  ("reset", None)   throw away what was streamed so far (a provider failed or the answer was rejected)
  ("final", dict)   a grounded answer: text, provider, usage, cited_ids
  ("failed", dict)  no grounded answer could be produced: reason, problems
"""
import logging
from typing import Iterator

from app import grounding
from app.llm import Usage
from app.prompt import retry_prompt

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 2  # one try, plus one rewrite if the answer is not grounded


def generate(providers: list, system: str, user: str, chart: dict) -> Iterator[tuple[str, object]]:
    problems: list[str] = []
    for attempt in range(MAX_ATTEMPTS):
        prompt = user if not problems else retry_prompt(user, problems)
        text, provider_name, usage = None, None, None

        for provider in providers:
            parts: list[str] = []
            try:
                for chunk in provider.stream(system, prompt):
                    if isinstance(chunk, Usage):
                        usage = chunk
                        continue
                    parts.append(chunk)
                    yield ("token", chunk)
                if not parts:
                    raise RuntimeError("empty answer")
                text, provider_name = "".join(parts), provider.name
                break
            except Exception as error:  # any provider failure moves on to the next provider
                log.warning("provider %s failed: %s", getattr(provider, "name", "?"), error)
                if parts:
                    yield ("reset", None)

        if text is None:
            yield ("failed", {"reason": "providers_failed", "problems": []})
            return

        result = grounding.validate(text, chart)
        if result.ok:
            yield ("final", {"text": text, "provider": provider_name, "usage": usage, "cited_ids": result.cited_ids})
            return

        log.warning("answer rejected (attempt %s): %s", attempt + 1, result.problems)
        problems = result.problems
        yield ("reset", None)

    yield ("failed", {"reason": "not_grounded", "problems": problems})
