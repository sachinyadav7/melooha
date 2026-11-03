"""Runs the fixed question set through the answer pipeline and scores every answer."""
import json
import statistics
import time
from datetime import date, datetime, time as dtime, timezone
from pathlib import Path

from app import grounding
from app.chart import compute_chart
from app.cities import CITIES
from app.llm import Usage
from app.prompt import build_prompts
from evalkit.checks import run_checks
from evalkit.judge import DIMENSIONS, judge_answer

HERE = Path(__file__).parent

# Three fixed charts, so every run sees the same facts.
TEST_CHARTS = [
    ("A", date(2000, 4, 15), dtime(12, 0), "Nagpur"),
    ("B", date(1995, 8, 20), dtime(9, 15), "Mumbai"),
    ("C", date(1988, 11, 3), dtime(22, 40), "Delhi"),
]


class AllProvidersFailed(Exception):
    pass


def load_questions():
    return json.loads((HERE / "questions.json").read_text(encoding="utf-8"))


def load_pricing():
    return json.loads((HERE / "pricing.json").read_text(encoding="utf-8"))


def build_charts():
    charts = {}
    for name, birth_date, birth_time, city in TEST_CHARTS:
        lat, lon = CITIES[city]
        charts[name] = compute_chart(birth_date, birth_time, lat, lon)
    return charts


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


def single_attempt(providers, system, user):
    """One try per provider, no rewrite, so the harness sees the model's real first-try behaviour."""
    errors = []
    for provider in providers:
        parts, usage, first_token = [], None, None
        start = time.perf_counter()
        try:
            for chunk in provider.stream(system, user):
                if isinstance(chunk, Usage):
                    usage = chunk
                else:
                    if first_token is None:
                        first_token = time.perf_counter() - start
                    parts.append(chunk)
            text = "".join(parts)
            if not text.strip():
                raise RuntimeError("empty answer")
            return {
                "text": text,
                "provider": provider.name,
                "usage": usage,
                "latency": time.perf_counter() - start,
                "first_token": first_token,
            }
        except Exception as error:
            errors.append(f"{getattr(provider, 'name', '?')}: {type(error).__name__}")
    raise AllProvidersFailed("; ".join(errors))


def evaluate_one(providers, judge, variant, entry, chart_name, chart):
    system, user = build_prompts(entry["question"], chart, variant)
    row = {
        "id": entry["id"], "category": entry["category"], "chart": chart_name,
        "question": entry["question"], "variant": variant, "error": None,
    }
    try:
        result = single_attempt(providers, system, user)
    except AllProvidersFailed as error:
        row["error"] = str(error)
        return row

    answer = result["text"]
    usage = result["usage"]
    estimated = usage is None
    grounded = grounding.validate(answer, chart)

    row.update(
        answer=answer,
        provider=result["provider"],
        input_tokens=usage.input_tokens if usage else estimate_tokens(system + user),
        output_tokens=usage.output_tokens if usage else estimate_tokens(answer),
        tokens_estimated=estimated,
        latency_s=round(result["latency"], 3),
        first_token_s=round(result["first_token"], 3) if result["first_token"] is not None else None,
        first_try_grounded=grounded.ok,
        grounding_problems=grounded.problems,
        checks=run_checks(answer, entry),
        judge=None,
    )

    if judge is not None:
        facts_text = "\n".join(f"{f['id']}: {f['text']}" for f in chart["facts"])
        try:
            row["judge"] = judge_answer(judge, entry["question"], answer, facts_text)
        except Exception:
            row["judge"] = None
    return row


def _mean(values):
    return round(statistics.mean(values), 3) if values else None


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(fraction * len(ordered)))], 3)


def summarize(rows, pricing):
    ok = [r for r in rows if not r["error"]]
    summary = {"questions": len(rows), "errors": len(rows) - len(ok)}

    summary["first_try_grounded_rate"] = _mean([1.0 if r["first_try_grounded"] else 0.0 for r in ok])

    check_names = sorted({name for r in ok for name in r["checks"]})
    summary["check_pass_rates"] = {}
    for name in check_names:
        applicable = [r["checks"][name] for r in ok if r["checks"].get(name) is not None]
        summary["check_pass_rates"][name] = _mean([1.0 if v else 0.0 for v in applicable])

    judged = [r["judge"] for r in ok if r.get("judge")]
    summary["judged"] = len(judged)
    summary["judge_means"] = {d: _mean([j[d] for j in judged]) for d in DIMENSIONS} if judged else {}

    summary["avg_input_tokens"] = _mean([r["input_tokens"] for r in ok])
    summary["avg_output_tokens"] = _mean([r["output_tokens"] for r in ok])
    summary["tokens_estimated_rows"] = sum(1 for r in ok if r["tokens_estimated"])
    summary["latency_p50_s"] = _percentile([r["latency_s"] for r in ok], 0.5)
    summary["latency_p95_s"] = _percentile([r["latency_s"] for r in ok], 0.95)

    costs = []
    for r in ok:
        price = pricing.get(r["provider"], {"input_per_million": 0, "output_per_million": 0})
        costs.append(
            r["input_tokens"] / 1e6 * price["input_per_million"]
            + r["output_tokens"] / 1e6 * price["output_per_million"]
        )
    summary["est_cost_per_1000_questions_usd"] = round(statistics.mean(costs) * 1000, 4) if costs else None
    return summary


def run_eval(providers, judge, variant, label, charts="one", limit=None, sleep=0.0, pricing=None, progress=None):
    questions = load_questions()[:limit] if limit else load_questions()
    chart_map = build_charts()
    chart_names = list(chart_map)
    pricing = pricing if pricing is not None else load_pricing()

    jobs = []
    for index, entry in enumerate(questions):
        names = chart_names if charts == "all" else [chart_names[index % len(chart_names)]]
        jobs.extend((entry, name) for name in names)

    rows = []
    for number, (entry, name) in enumerate(jobs, start=1):
        row = evaluate_one(providers, judge, variant, entry, name, chart_map[name])
        rows.append(row)
        if progress:
            progress(number, len(jobs), row)
        if sleep and number < len(jobs):
            time.sleep(sleep)

    return {
        "label": label,
        "variant": variant,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
        "summary": summarize(rows, pricing),
    }
