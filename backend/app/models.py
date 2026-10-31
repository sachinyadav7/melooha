from datetime import date, datetime, time, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LedgerEntry(Base):
    """One row per balance change. The balance is the sum of `change` for a user."""

    __tablename__ = "balance_ledger"
    __table_args__ = (
        # The same request can only apply once per reason, so a double-tap or retry cannot charge twice.
        UniqueConstraint("user_id", "request_id", "reason", name="uq_ledger_request"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    change: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(20))  # signup_free, purchase, spend, refund
    request_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Chart(Base):
    """One birth chart per user. `data` holds planets, houses and the fact list."""

    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    birth_date: Mapped[date] = mapped_column(Date)
    birth_time: Mapped[time] = mapped_column(Time)
    city: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Question(Base):
    """A question and its answer. One row per ask, tied to the request_id that paid for it."""

    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("user_id", "request_id", name="uq_question_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending, answered, failed
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    cited_fact_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    problems: Mapped[list | None] = mapped_column(JSON, nullable=True)  # why a failed answer was rejected
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
