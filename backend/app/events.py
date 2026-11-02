import logging

from sqlalchemy.orm import Session

from app.models import Event

log = logging.getLogger(__name__)

# Sent by the app. The server decides everything else, so the metric cannot be faked from the browser.
CLIENT_EVENTS = ("chart_viewed", "evidence_tapped", "paywall_viewed")

# Logged by the server when it happens:
#   onboarding_done       first time a user saves birth details
#   free_answer_received  the user's first answered question
#   add_questions_clicked a top-up was applied (not a repeated request)
SERVER_EVENTS = ("onboarding_done", "free_answer_received", "add_questions_clicked")


def log_event(db: Session, user_id: int, name: str, properties: dict | None = None) -> bool:
    """Record an event. Tracking must never break the real flow, so failures are logged and swallowed."""
    try:
        db.add(Event(user_id=user_id, name=name, properties=properties or None))
        db.commit()
        return True
    except Exception:
        db.rollback()
        log.exception("could not log event %s for user %s", name, user_id)
        return False
