"""Plain-text reports for one run, and a before/after comparison of two runs."""


def _pct(value):
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _num(value, digits=1):
    return "n/a" if value is None else f"{value:.{digits}f}"


def format_summary(result) -> str:
    s = result["summary"]
    lines = [
        f"Run: {result['label']}  (prompt variant: {result['variant']})",
        f"Questions: {s['questions']}   Errors: {s['errors']}   Judged: {s['judged']}",
        "",
        f"First-try grounded:  {_pct(s['first_try_grounded_rate'])}",
    ]
    for name, rate in s["check_pass_rates"].items():
        lines.append(f"{name + ':':21}{_pct(rate)}")
    for name, mean in s["judge_means"].items():
        lines.append(f"judge {name + ':':15}{_num(mean, 2)} / 5")
    lines += [
        "",
        f"Avg input tokens:    {_num(s['avg_input_tokens'])}",
        f"Avg output tokens:   {_num(s['avg_output_tokens'])}",
        f"Latency p50 / p95:   {_num(s['latency_p50_s'], 2)}s / {_num(s['latency_p95_s'], 2)}s",
        f"Est. cost per 1000:  ${_num(s['est_cost_per_1000_questions_usd'], 4)} (placeholder prices)",
    ]
    if s["tokens_estimated_rows"]:
        lines.append(f"Note: {s['tokens_estimated_rows']} rows had no token counts from the provider and were estimated.")
    return "\n".join(lines)


def _change(before, after, as_percent_points=False):
    if before is None or after is None:
        return "n/a"
    delta = after - before
    if as_percent_points:
        return f"{delta * 100:+.0f} pts"
    if before == 0:
        return f"{delta:+.2f}"
    return f"{delta / before * 100:+.0f}%"


def compare(before, after) -> str:
    b, a = before["summary"], after["summary"]
    rows = [
        ("Avg input tokens", _num(b["avg_input_tokens"]), _num(a["avg_input_tokens"]), _change(b["avg_input_tokens"], a["avg_input_tokens"])),
        ("Avg output tokens", _num(b["avg_output_tokens"]), _num(a["avg_output_tokens"]), _change(b["avg_output_tokens"], a["avg_output_tokens"])),
        ("Est. cost per 1000 ($)", _num(b["est_cost_per_1000_questions_usd"], 4), _num(a["est_cost_per_1000_questions_usd"], 4),
         _change(b["est_cost_per_1000_questions_usd"], a["est_cost_per_1000_questions_usd"])),
        ("Latency p50 (s)", _num(b["latency_p50_s"], 2), _num(a["latency_p50_s"], 2), _change(b["latency_p50_s"], a["latency_p50_s"])),
        ("First-try grounded", _pct(b["first_try_grounded_rate"]), _pct(a["first_try_grounded_rate"]),
         _change(b["first_try_grounded_rate"], a["first_try_grounded_rate"], True)),
    ]
    for name in sorted(set(b["check_pass_rates"]) | set(a["check_pass_rates"])):
        rows.append((name, _pct(b["check_pass_rates"].get(name)), _pct(a["check_pass_rates"].get(name)),
                     _change(b["check_pass_rates"].get(name), a["check_pass_rates"].get(name), True)))
    for name in sorted(set(b["judge_means"]) | set(a["judge_means"])):
        rows.append((f"judge {name} (of 5)", _num(b["judge_means"].get(name), 2), _num(a["judge_means"].get(name), 2),
                     _change(b["judge_means"].get(name), a["judge_means"].get(name))))

    header = ("Metric", before["label"], after["label"], "Change")
    widths = [max(len(str(r[i])) for r in rows + [header]) for i in range(4)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    out = [fmt.format(*header), fmt.format(*["-" * w for w in widths])]
    out += [fmt.format(*[str(c) for c in r]) for r in rows]
    return "\n".join(out)
