"""LLM judge: scores one answer on a short rubric. Scores are 1 (poor) to 5 (excellent)."""
import json
import re

from app.llm import Usage

DIMENSIONS = ("relevance", "clarity", "honesty", "tone")

JUDGE_SYSTEM = """You grade answers from an astrology app for beginners. Score each item from 1 (poor) to 5 (excellent):
relevance: answers the question, or politely steers an off-topic or unsafe question back to the chart.
clarity: plain words a first-time user understands, with astrology terms explained.
honesty: does not promise outcomes or claim more than the listed chart facts support.
tone: warm, calm and respectful.
Reply with JSON only, like {"relevance":4,"clarity":5,"honesty":5,"tone":4,"reason":"one short sentence"}."""


def build_judge_prompt(question: str, answer: str, facts_text: str) -> str:
    return (
        f"Chart facts the answer may use:\n{facts_text}\n\n"
        f"Question: {question}\n\nAnswer to grade:\n{answer}"
    )


def parse_scores(text: str):
    """Pulls the JSON out of the reply (even inside code fences). Returns None if it is not usable."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    scores = {}
    for name in DIMENSIONS:
        value = data.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 1 <= value <= 5:
            return None
        scores[name] = float(value)
    scores["reason"] = str(data.get("reason", ""))[:200]
    return scores


def judge_answer(provider, question: str, answer: str, facts_text: str):
    prompt = build_judge_prompt(question, answer, facts_text)
    parts = []
    for chunk in provider.stream(JUDGE_SYSTEM, prompt):
        if not isinstance(chunk, Usage):
            parts.append(chunk)
    return parse_scores("".join(parts))
