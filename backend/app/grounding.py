"""Code-level check that an answer only uses facts from the user's chart.

The prompt asks the model to cite facts as [[FACT_ID]]. This module does not trust that: it checks
the finished answer against the stored chart and rejects it if anything does not match.
"""
import re
from dataclasses import dataclass

from app.meanings import PLANETS, SIGNS

MARKER = re.compile(r"\[\[([A-Z0-9_]+)\]\]")
HOUSE_NUMBER = re.compile(r"\bhouse\s+(\d{1,2})\b|\b(\d{1,2})(?:st|nd|rd|th)\s+house\b", re.IGNORECASE)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass
class GroundingResult:
    ok: bool
    cited_ids: list[str]
    problems: list[str]


def strip_markers(text: str) -> str:
    return MARKER.sub("", text)


def validate(text: str, chart: dict) -> GroundingResult:
    """Rules:
    1. The answer cites at least one fact.
    2. Every cited ID exists in this user's chart.
    3. Every planet named in the answer has at least one cited fact about it.
    4. In a sentence that names exactly one planet, any sign or house number must match that planet
       (the rising sign is also allowed).
    """
    fact_ids = {f["id"] for f in chart["facts"]}
    cited = list(dict.fromkeys(MARKER.findall(text)))
    problems: list[str] = []

    if not cited:
        problems.append("The answer cites no chart facts.")
    for fact_id in cited:
        if fact_id not in fact_ids:
            problems.append(f"[[{fact_id}]] is not a fact in this chart.")

    cited_planets = set()
    for fact_id in cited:
        if fact_id not in fact_ids:
            continue
        match = re.match(r"P_([A-Z]+)_", fact_id)
        if match:
            cited_planets.add(match.group(1))
        elif fact_id.startswith("MOON_NAK_"):
            cited_planets.add("MOON")

    planets_by_key = {p["key"]: p for p in chart["planets"]}
    ascendant_sign = chart["ascendant"]["sign"]

    for sentence in SENTENCE_SPLIT.split(strip_markers(text)):
        named = [key for key, (name, _) in PLANETS.items() if re.search(rf"\b{name}\b", sentence)]

        for key in named:
            if key not in cited_planets:
                problems.append(f"{PLANETS[key][0]} is mentioned without citing a fact about it.")

        if len(named) != 1:
            continue
        planet = planets_by_key[named[0]]
        for sign in SIGNS:
            if re.search(rf"\b{sign}\b", sentence) and sign not in (planet["sign"], ascendant_sign):
                problems.append(f"{planet['name']} is in {planet['sign']}, not {sign}.")
        for found in HOUSE_NUMBER.finditer(sentence):
            number = int(found.group(1) or found.group(2))
            if number != planet["house"]:
                problems.append(f"{planet['name']} is in house {planet['house']}, not house {number}.")

    problems = list(dict.fromkeys(problems))
    return GroundingResult(ok=not problems, cited_ids=cited, problems=problems)
