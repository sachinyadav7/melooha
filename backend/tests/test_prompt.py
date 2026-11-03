from datetime import date, time

import pytest

from app.chart import compute_chart
from app.cities import CITIES
from app.prompt import build_prompts, select_facts

CHART = compute_chart(date(2000, 4, 15), time(12, 0), *CITIES["Nagpur"])
# In this chart Sun, Mars, Jupiter and Saturn are in house 10; Venus and Mercury are in house 9.


def ids(facts):
    return {f["id"] for f in facts}


def test_career_question_keeps_career_planets_and_drops_unrelated_ones():
    chosen = ids(select_facts("How is my career area?", CHART))
    assert "P_SATURN_H10" in chosen and "P_SUN_H10" in chosen
    assert "P_VENUS_H9" not in chosen and "P_MERCURY_H9" not in chosen
    assert len(chosen) < len(CHART["facts"])


def test_rising_sign_and_moon_are_always_kept():
    chosen = ids(select_facts("What kind of work suits me?", CHART))
    assert any(i.startswith("ASC_") for i in chosen)
    assert any(i.startswith("P_MOON_") for i in chosen)
    assert any(i.startswith("MOON_NAK_") for i in chosen)


def test_unclear_topic_gets_every_fact():
    assert select_facts("Tell me something about me.", CHART) == CHART["facts"]
    assert select_facts("What is the capital of France?", CHART) == CHART["facts"]


def test_baseline_shows_every_fact():
    _, user = build_prompts("How is my career area?", CHART, "baseline")
    assert all(f"[[{f['id']}]]" in user for f in CHART["facts"])


def test_lean_prompt_is_smaller_than_baseline():
    base_system, base_user = build_prompts("How is my career area?", CHART, "baseline")
    lean_system, lean_user = build_prompts("How is my career area?", CHART, "lean")
    assert len(lean_system) < len(base_system)
    assert len(lean_user) < len(base_user)


@pytest.mark.parametrize("variant", ["baseline", "lean"])
def test_both_prompts_keep_the_safety_rules(variant):
    system, user = build_prompts("How is my career area?", CHART, variant)
    assert "[[P_SATURN_H3]]" in system  # citation format
    assert "timing data" in system  # no dates rule
    assert "<question>" in system and "<question>How is my career area?</question>" in user
    assert "professional" in system


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError):
        build_prompts("hi there", CHART, "mystery")


def test_default_prompt_still_works_for_the_app():
    system, user = build_prompts("How is my career area?", CHART)
    assert "Chart facts:" in user and system
