from datetime import date, time

import pytest

from app.chart import compute_chart
from app.cities import CITIES
from app.grounding import validate

CHART = compute_chart(date(2000, 4, 15), time(12, 0), *CITIES["Nagpur"])
SATURN = next(p for p in CHART["planets"] if p["key"] == "SATURN")
VENUS = next(p for p in CHART["planets"] if p["key"] == "VENUS")
H = SATURN["house"]
WRONG_HOUSE = H % 12 + 1


def test_correct_answer_passes():
    text = f"Saturn is in house {H}, the area of slow and steady effort. [[P_SATURN_H{H}]]"
    result = validate(text, CHART)
    assert result.ok and result.cited_ids == [f"P_SATURN_H{H}"]


def test_answer_without_citations_is_rejected():
    result = validate("Things look fine for you.", CHART)
    assert not result.ok


def test_invented_fact_id_is_rejected():
    result = validate(f"Saturn matters. [[P_SATURN_H{WRONG_HOUSE}]]", CHART)
    assert not result.ok
    assert any("not a fact" in p for p in result.problems)


def test_planet_named_without_a_citation_is_rejected():
    text = f"Saturn is in house {H}. [[P_SATURN_H{H}]] Venus will bring luck."
    result = validate(text, CHART)
    assert not result.ok
    assert any("Venus" in p for p in result.problems)


def test_wrong_house_number_for_a_planet_is_rejected():
    text = f"Saturn is in house {WRONG_HOUSE}. [[P_SATURN_H{H}]]"
    result = validate(text, CHART)
    assert not result.ok
    assert any("house" in p for p in result.problems)


def test_ordinal_house_wording_is_checked_too():
    text = f"Saturn sits in your {WRONG_HOUSE}th house. [[P_SATURN_H{H}]]"
    assert not validate(text, CHART).ok


def test_wrong_sign_for_a_planet_is_rejected():
    wrong = "Aries" if SATURN["sign"] != "Aries" else "Taurus"
    text = f"Saturn is in {wrong}. [[P_SATURN_H{H}]]"
    assert not validate(text, CHART).ok


def test_rising_sign_is_allowed_next_to_a_planet():
    asc = CHART["ascendant"]["sign"]
    text = f"With {asc} rising, Saturn is in house {H}. [[ASC_{asc.upper()}]] [[P_SATURN_H{H}]]"
    assert validate(text, CHART).ok


def test_sentence_with_two_planets_skips_the_sign_check_but_needs_both_cited():
    text = f"Saturn and Venus work together. [[P_SATURN_H{H}]] [[P_VENUS_H{VENUS['house']}]]"
    assert validate(text, CHART).ok
    assert not validate(f"Saturn and Venus work together. [[P_SATURN_H{H}]]", CHART).ok
