"""Evaluate answer quality and cost on a fixed question set (uses your real Gemini and Groq keys).

    python scripts/run_eval.py --variant baseline --label before
    python scripts/run_eval.py --variant lean --label after
    python scripts/run_eval.py --compare evalkit/results/before.json evalkit/results/after.json

Free tiers have rate limits. If you see errors, raise --sleep.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm import default_providers  # noqa: E402
from evalkit.report import compare, format_summary  # noqa: E402
from evalkit.runner import run_eval  # noqa: E402

RESULTS = Path(__file__).resolve().parent.parent / "evalkit" / "results"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["baseline", "lean"], default="baseline")
    parser.add_argument("--label", default=None)
    parser.add_argument("--charts", choices=["one", "all"], default="one", help="one chart per question, or every chart")
    parser.add_argument("--limit", type=int, default=None, help="only the first N questions")
    parser.add_argument("--judge", choices=["gemini", "groq", "none"], default="groq")
    parser.add_argument("--sleep", type=float, default=2.0, help="seconds to wait between questions")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    args = parser.parse_args()

    if args.compare:
        print(compare(load(args.compare[0]), load(args.compare[1])))
        return

    providers = default_providers()
    if not providers:
        raise SystemExit("No API keys found. Add GEMINI_API_KEY and GROQ_API_KEY to your .env file.")

    judge = None
    if args.judge != "none":
        judge = next((p for p in providers if p.name == args.judge), None)
        if judge is None:
            print(f"Judge '{args.judge}' has no API key, so answers will not be judged.")

    label = args.label or args.variant

    def progress(number, total, row):
        status = row["error"] or f"grounded={row['first_try_grounded']} tokens={row['input_tokens']}+{row['output_tokens']}"
        print(f"[{number}/{total}] {row['id']:<14} {status}", flush=True)

    result = run_eval(providers, judge, args.variant, label, charts=args.charts, limit=args.limit,
                      sleep=args.sleep, progress=progress)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{label}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print()
    print(format_summary(result))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
