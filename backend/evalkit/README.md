# Evaluation harness and cost control

Scores answer quality on a fixed set of 20 questions and measures tokens and cost per answer.
Offline tests run in CI. The real run uses your Gemini and Groq keys.

## What it checks

Code checks (no model needed):
- **First-try grounded**: the answer passes the same grounding check production uses, with no rewrite allowed.
- **no_dates**: no years, months or "next year" style timing (the app has no timing data).
- **no_guarantees**: no "definitely" or "guaranteed".
- **length_ok**: 140 words or fewer.
- **no_injection_marker**: ignores the prompt-injection question that asks for "PWNED".
- **professional_referral**: health and risky-money questions point to a doctor or advisor.

LLM judge (1 to 5): relevance, clarity, honesty, tone. The judge is a different provider from the main one by default (Groq judges Gemini answers) to reduce a model rating its own style.

The 20 questions cover career, love, strengths, money, family, education, timing, health, risky money, prompt injection, off-topic and vague questions. They run on 3 fixed birth charts.

## Run it

From the `backend` folder, with your keys in `.env`:

```bash
python scripts/run_eval.py --variant baseline --label before
python scripts/run_eval.py --variant lean --label after
python scripts/run_eval.py --compare evalkit/results/before.json evalkit/results/after.json
```

Options: `--charts all` (60 answers instead of 20), `--limit 5` (quick test), `--sleep 4` (slower, for rate limits), `--judge none`.

## Cost control: what "lean" changes

1. **Only the chart facts related to the question** are sent (`select_facts` in `app/prompt.py`). Unclear topics still get every fact.
2. **A shorter rule prompt** and a 90 word answer limit.

Grounding is still checked against the full chart, so a smaller prompt cannot make the checks easier to pass.

Cost uses the placeholder prices in `pricing.json`. The free tiers cost nothing, so update the prices from each provider's pricing page before quoting a dollar figure. Token counts come from the provider.

Prompt caching: it only applies to long, repeated prompt prefixes. These prompts are a few hundred tokens, so it would not help here.

## After the comparison

If quality holds (grounded rate and judge scores close to baseline), set `DEFAULT_VARIANT = "lean"` in `app/prompt.py` so the app uses it. Commit the two result files in `evalkit/results/` as evidence.
