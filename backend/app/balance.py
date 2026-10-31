"""Question balance rules. All balance changes go through here so the checks live in one place."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import LedgerEntry, User


class UserNotFound(Exception):
    pass


class InsufficientBalance(Exception):
    pass


class NothingToRefund(Exception):
    pass


def get_balance(db: Session, user_id: int) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.change), 0)).where(LedgerEntry.user_id == user_id)
    )
    return int(total)


def create_user(db: Session, name: str) -> User:
    user = User(name=name)
    db.add(user)
    db.flush()
    db.add(
        LedgerEntry(
            user_id=user.id,
            change=settings.free_questions,
            reason="signup_free",
            request_id="signup",
        )
    )
    db.commit()
    return user


def _find(db: Session, user_id: int, request_id: str, reason: str):
    return db.scalar(
        select(LedgerEntry).where(
            LedgerEntry.user_id == user_id,
            LedgerEntry.request_id == request_id,
            LedgerEntry.reason == reason,
        )
    )


def _apply(db: Session, user_id: int, request_id: str, reason: str, change: int, needs_funds=False):
    """Apply one balance change safely.

    1. Lock the user's row, so two requests for the same user run one after the other.
    2. If this request_id was already applied, return the current balance and change nothing.
    3. Check funds, write one ledger row, commit.
    Returns (balance, replayed).
    """
    locked = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if locked is None:
        db.rollback()
        raise UserNotFound(user_id)

    if _find(db, user_id, request_id, reason) is not None:
        balance = get_balance(db, user_id)
        db.rollback()
        return balance, True

    if needs_funds and get_balance(db, user_id) + change < 0:
        db.rollback()
        raise InsufficientBalance(user_id)

    db.add(LedgerEntry(user_id=user_id, change=change, reason=reason, request_id=request_id))
    db.commit()
    return get_balance(db, user_id), False


def spend_question(db: Session, user_id: int, request_id: str):
    return _apply(db, user_id, request_id, "spend", -1, needs_funds=True)


def add_questions(db: Session, user_id: int, request_id: str):
    return _apply(db, user_id, request_id, "purchase", settings.questions_per_pack)


def refund_question(db: Session, user_id: int, request_id: str):
    """Give back a question when an answer failed. Only works for a question that was actually spent."""
    if _find(db, user_id, request_id, "spend") is None:
        if db.get(User, user_id) is None:
            raise UserNotFound(user_id)
        raise NothingToRefund(request_id)
    return _apply(db, user_id, request_id, "refund", 1)
