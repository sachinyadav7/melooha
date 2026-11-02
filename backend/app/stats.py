"""The one metric: free-question-to-purchase conversion, for the chart group vs the control group.

Conversion = of users who received their first free answer, the share who tapped "Add questions"
within 24 hours of that answer.
"""
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.experiment import GROUPS, group_for
from app.models import Event, User

WINDOW = timedelta(hours=24)


def conversion_stats(db: Session) -> dict:
    events_by_user: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for user_id, name, created_at in db.execute(select(Event.user_id, Event.name, Event.created_at)):
        events_by_user[user_id][name].append(created_at)

    groups = {
        g: {"users": 0, "viewed_chart": 0, "tapped_evidence": 0, "got_first_answer": 0,
            "saw_paywall": 0, "converted": 0, "conversion_rate": None}
        for g in GROUPS
    }

    for user_id in db.scalars(select(User.id)):
        stats = groups[group_for(user_id)]
        events = events_by_user.get(user_id, {})
        stats["users"] += 1
        if "chart_viewed" in events:
            stats["viewed_chart"] += 1
        if "evidence_tapped" in events:
            stats["tapped_evidence"] += 1
        if "free_answer_received" not in events:
            continue

        stats["got_first_answer"] += 1
        if "paywall_viewed" in events:
            stats["saw_paywall"] += 1
        first_answer = min(events["free_answer_received"])
        if any(first_answer <= t <= first_answer + WINDOW for t in events.get("add_questions_clicked", [])):
            stats["converted"] += 1

    for stats in groups.values():
        if stats["got_first_answer"]:
            stats["conversion_rate"] = round(stats["converted"] / stats["got_first_answer"], 4)

    return {
        "metric": "Share of users who tap Add questions within 24 hours of their first free answer",
        "window_hours": 24,
        "groups": groups,
        "note": "Small samples. Treat differences as a signal to investigate, not proof.",
    }
