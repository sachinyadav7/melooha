import json

import pytest

from app.llm import Usage
from evalkit import checks, judge, report, runner
from tests.conftest import FakeProvider


# ---------- helpers ----------

class EchoProvider:
    """Answers any question using the first planet-in-house fact it is shown, so the answer is always grounded."""

    def __init__(self, name="fake", input_tokens=100, output_tokens=20):
        self.name, self.usage = name, Usage(input_tokens, output_tokens)

    def stream(self, system, user):
        import re

        planet, house = re.search(r"\[\[P_([A-Z]+)_H(\d+)\]\]", user).groups()
        yield f"{planet.title()} is in house {house}, about steady effort. [[P_{planet}_H{house}]]"
        yield self.usage


class TextProvider:
    def __init__(self, text, name="fake"):
        self.text, self.name = text, name

    def stream(self, system, user):
        yield self.text
        yield Usage(50, 10)


FREE = {"fake": {"input_per_million": 0, "output_per_million": 0}}


def run(providers, judge_provider=None, variant="baseline", **kwargs):
    return runner.run_eval(providers, judge_provider, variant, "test", pricing=kwargs.pop("pricing", FREE), **kwargs)


# ---------- code checks ----------

@pytest.mark.parametrize("text,ok", [
    ("Saturn is in house 10, about steady effort.", True),
    ("You may feel calm and focused.", True),
    ("A big change comes in 2027.", False),
    ("Expect progress in March.", False),
    ("Things improve in May.", False),
    ("Try again next year.", False),
    ("You will see results in 3 months.", False),
    ("Saturn is in house 10. [[P_SATURN_H10]]", True),
])
def test_no_dates(text, ok):
    assert checks.no_dates(text, {}) is ok


def test_no_guarantees():
    assert checks.no_guarantees("This will definitely happen.", {}) is False
    assert checks.no_guarantees("This may help you grow.", {}) is True


def test_length_ignores_markers():
    assert checks.length_ok("word " * 140 + "[[P_SUN_H10]]", {}) is True
    assert checks.length_ok("word " * 141, {}) is False


def test_professional_referral_only_applies_when_asked_for():
    plain = {"checks": []}
    asked = {"checks": ["professional_referral"]}
    assert checks.professional_referral("Anything.", plain) is None
    assert checks.professional_referral("Please see a doctor.", asked) is True
    assert checks.professional_referral("You will be fine.", asked) is False


def test_injection_marker():
    assert checks.no_injection_marker("PWNED", {}) is False
    assert checks.no_injection_marker("Saturn is in house 10.", {}) is True


# ---------- judge ----------

def test_judge_parses_clean_and_fenced_json():
    raw = '{"relevance":4,"clarity":5,"honesty":5,"tone":4,"reason":"Clear."}'
    assert judge.parse_scores(raw)["clarity"] == 5.0
    assert judge.parse_scores(f"```json\n{raw}\n```")["relevance"] == 4.0


@pytest.mark.parametrize("raw", [
    "no json here",
    '{"relevance":4,"clarity":5,"honesty":5}',  # missing tone
    '{"relevance":9,"clarity":5,"honesty":5,"tone":4}',  # out of range
    '{"relevance":"high","clarity":5,"honesty":5,"tone":4}',
    "{broken json}",
])
def test_judge_rejects_unusable_replies(raw):
    assert judge.parse_scores(raw) is None


# ---------- runner ----------

def test_run_scores_every_question_and_aggregates():
    judge_provider = TextProvider('{"relevance":4,"clarity":5,"honesty":5,"tone":3,"reason":"ok"}')
    result = run([EchoProvider()], judge_provider, limit=4)
    summary = result["summary"]

    assert len(result["rows"]) == 4 and summary["errors"] == 0
    assert summary["first_try_grounded_rate"] == 1.0
    assert summary["avg_input_tokens"] == 100 and summary["avg_output_tokens"] == 20
    assert summary["judged"] == 4 and summary["judge_means"]["clarity"] == 5.0
    assert summary["judge_means"]["tone"] == 3.0
    assert summary["check_pass_rates"]["no_dates"] == 1.0


def test_charts_all_runs_each_question_on_every_chart():
    result = run([EchoProvider()], None, limit=2, charts="all")
    assert len(result["rows"]) == 2 * len(runner.TEST_CHARTS)


def test_ungrounded_and_rule_breaking_answers_are_caught():
    result = run([TextProvider("In 2027 you will definitely get promoted. [[P_FAKE_H1]]")], None, limit=3)
    row = result["rows"][0]
    assert row["first_try_grounded"] is False and row["grounding_problems"]
    assert row["checks"]["no_dates"] is False and row["checks"]["no_guarantees"] is False
    assert result["summary"]["first_try_grounded_rate"] == 0.0


def test_provider_failure_is_recorded_not_raised():
    failing = FakeProvider("gemini", [RuntimeError("quota")])
    result = run([failing], None, limit=2)
    assert all(row["error"] for row in result["rows"])
    assert result["summary"]["errors"] == 2 and result["summary"]["avg_input_tokens"] is None


def test_falls_back_to_the_second_provider():
    failing = FakeProvider("gemini", [RuntimeError("quota")])
    result = run([failing, EchoProvider(name="groq")], None, limit=2, pricing={"groq": FREE["fake"]})
    assert {row["provider"] for row in result["rows"]} == {"groq"}


def test_missing_token_counts_are_estimated_and_flagged():
    class NoUsage(TextProvider):
        def stream(self, system, user):
            yield self.text

    result = run([NoUsage("Saturn is in house 10. [[P_SATURN_H10]]")], None, limit=2)
    assert result["summary"]["tokens_estimated_rows"] == 2
    assert result["summary"]["avg_input_tokens"] > 0


def test_unusable_judge_reply_leaves_the_answer_unjudged():
    result = run([EchoProvider()], TextProvider("sorry, I cannot grade"), limit=2)
    assert result["summary"]["judged"] == 0 and result["summary"]["errors"] == 0


def test_cost_uses_the_price_table():
    # $1 per input token, free output: 100 input tokens = $100 a question = $100,000 per 1000.
    pricing = {"fake": {"input_per_million": 1_000_000, "output_per_million": 0}}
    result = run([EchoProvider()], None, limit=2, pricing=pricing)
    assert result["summary"]["est_cost_per_1000_questions_usd"] == pytest.approx(100_000)


def test_lean_prompt_uses_fewer_input_tokens_than_baseline():
    # With no real provider counts, tokens are estimated from the prompt text, so the saving is visible offline.
    class NoUsageEcho(EchoProvider):
        def stream(self, system, user):
            for chunk in super().stream(system, user):
                if not isinstance(chunk, Usage):
                    yield chunk

    before = run([NoUsageEcho()], None, variant="baseline")
    after = run([NoUsageEcho()], None, variant="lean")
    assert after["summary"]["avg_input_tokens"] < before["summary"]["avg_input_tokens"]


# ---------- reports ----------

def test_report_and_comparison_render():
    judge_provider = TextProvider('{"relevance":4,"clarity":4,"honesty":4,"tone":4,"reason":"ok"}')
    before = runner.run_eval([EchoProvider(input_tokens=200)], judge_provider, "baseline", "before", pricing=FREE, limit=3)
    after = runner.run_eval([EchoProvider(input_tokens=100)], judge_provider, "lean", "after", pricing=FREE, limit=3)

    text = report.format_summary(before)
    assert "First-try grounded" in text and "Avg input tokens" in text

    table = report.compare(before, after)
    assert "before" in table and "after" in table
    assert "-50%" in table  # input tokens halved


def test_report_works_without_a_judge():
    result = run([EchoProvider()], None, limit=2)
    assert "Judged: 0" in report.format_summary(result)


def test_results_are_json_serialisable():
    result = run([EchoProvider()], None, limit=2)
    assert json.loads(json.dumps(result))["label"] == "test"
