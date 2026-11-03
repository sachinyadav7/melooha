import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import answering, events, stats
from app import balance as bal
from app import llm
from app.chart import compute_chart
from app.cities import CITIES, find_city
from app.config import settings
from app.db import Base, SessionLocal, engine, get_db
from app.experiment import group_for
from app.models import Chart, Question, User
from app.prompt import build_prompts
from app.schemas import ActionOut, AskIn, BalanceOut, BirthDetails, ChartOut, EventIn, RequestIn, UserCreate, UserOut

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Simple for now. Switch to migrations (Alembic) if the schema keeps changing.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Melooha Show Your Work API", lifespan=lifespan)

origins = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- dependencies (tests replace these) ----------

def get_providers():
    return llm.default_providers()


def get_session_factory():
    # The answer stream outlives the request's own database session, so it opens its own.
    return SessionLocal


# ---------- errors ----------

class CityNotSupported(Exception):
    pass


class ChartNotFound(Exception):
    pass


class AnswerInProgress(Exception):
    pass


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


@app.exception_handler(bal.UserNotFound)
async def _user_not_found(_, __):
    return _error(404, "user_not_found", "We could not find this account.")


@app.exception_handler(bal.InsufficientBalance)
async def _insufficient(_, __):
    return _error(402, "insufficient_balance", "You have no questions left. Add questions to continue.")


@app.exception_handler(bal.NothingToRefund)
async def _nothing_to_refund(_, __):
    return _error(409, "nothing_to_refund", "That question was not charged.")


@app.exception_handler(CityNotSupported)
async def _city_not_supported(_, __):
    return _error(422, "city_not_supported", "We do not have this city yet. Pick the nearest big city from the list.")


@app.exception_handler(ChartNotFound)
async def _chart_not_found(_, __):
    return _error(404, "chart_not_found", "Add your birth details to see your chart.")


@app.exception_handler(AnswerInProgress)
async def _answer_in_progress(_, __):
    return _error(409, "answer_in_progress", "Your answer is still being prepared. Please wait a moment.")


# ---------- basics ----------

def _chart_out(row: Chart) -> ChartOut:
    return ChartOut(city=row.city, **row.data)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/hello")
def hello():
    return {"message": "Hello from the Melooha backend"}


@app.get("/cities")
def list_cities():
    return {"cities": sorted(CITIES)}


# ---------- balance ----------

@app.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    user = bal.create_user(db, body.name)
    return UserOut(user_id=user.id, balance=bal.get_balance(db, user.id), experiment_group=group_for(user.id))


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise bal.UserNotFound(user_id)
    return UserOut(user_id=user_id, balance=bal.get_balance(db, user_id), experiment_group=group_for(user_id))


@app.get("/users/{user_id}/balance", response_model=BalanceOut)
def get_balance(user_id: int, db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise bal.UserNotFound(user_id)
    return BalanceOut(user_id=user_id, balance=bal.get_balance(db, user_id))


@app.post("/users/{user_id}/add-questions", response_model=ActionOut)
def add_questions(user_id: int, body: RequestIn, db: Session = Depends(get_db)):
    balance, replayed = bal.add_questions(db, user_id, body.request_id)
    if not replayed:
        events.log_event(db, user_id, "add_questions_clicked", {"balance_after": balance})
    return ActionOut(user_id=user_id, balance=balance, replayed=replayed)


@app.post("/users/{user_id}/spend", response_model=ActionOut)
def spend_question(user_id: int, body: RequestIn, db: Session = Depends(get_db)):
    balance, replayed = bal.spend_question(db, user_id, body.request_id)
    return ActionOut(user_id=user_id, balance=balance, replayed=replayed)


# ---------- chart ----------

@app.put("/users/{user_id}/chart", response_model=ChartOut)
def save_chart(user_id: int, body: BirthDetails, db: Session = Depends(get_db)):
    """Create the user's chart, or replace it if they correct their birth details."""
    if db.get(User, user_id) is None:
        raise bal.UserNotFound(user_id)
    found = find_city(body.city)
    if found is None:
        raise CityNotSupported(body.city)
    city, lat, lon = found

    data = compute_chart(body.date, body.time, lat, lon)

    row = db.scalar(select(Chart).where(Chart.user_id == user_id))
    is_first_chart = row is None
    if row is None:
        row = Chart(user_id=user_id)
        db.add(row)
    row.birth_date = body.date
    row.birth_time = body.time
    row.city = city
    row.latitude = lat
    row.longitude = lon
    row.data = data
    db.commit()
    if is_first_chart:
        events.log_event(db, user_id, "onboarding_done", {"city": city})
    return _chart_out(row)


@app.get("/users/{user_id}/chart", response_model=ChartOut)
def get_chart(user_id: int, db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise bal.UserNotFound(user_id)
    row = db.scalar(select(Chart).where(Chart.user_id == user_id))
    if row is None:
        raise ChartNotFound(user_id)
    return _chart_out(row)


# ---------- ask (streamed answer) ----------

FAILED_MESSAGES = {
    "providers_failed": "We could not get your answer right now. This question was not used, so you can try again.",
    "not_grounded": "We could not check this answer against your chart, so we did not show it. "
    "This question was not used. Try asking it in a different way.",
    "interrupted": "The answer was interrupted. This question was not used.",
}


def _sse(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data)}\n\n"


def _fail_and_refund(session_factory, user_id: int, question_id: int, request_id: str, reason: str, problems) -> int:
    """Mark the question failed and give the question back. Returns the new balance."""
    session = session_factory()
    try:
        question = session.get(Question, question_id)
        question.status = "failed"
        question.problems = list(problems or []) or [reason]
        session.commit()
        balance, _ = bal.refund_question(session, user_id, request_id)
        return balance
    finally:
        session.close()


def _answer_stream(session_factory, providers, user_id, question_id, request_id, question_text, chart):
    system, user_prompt = build_prompts(question_text, chart)
    finished = False
    try:
        yield _sse("meta", {"question_id": question_id})
        final, failure = None, None

        for kind, payload in answering.generate(providers, system, user_prompt, chart):
            if kind == "token":
                yield _sse("token", {"text": payload})
            elif kind == "reset":
                yield _sse("reset", {})
            elif kind == "final":
                final = payload
            elif kind == "failed":
                failure = payload

        if final is not None:
            session = session_factory()
            try:
                question = session.get(Question, question_id)
                question.status = "answered"
                question.answer = final["text"]
                question.cited_fact_ids = final["cited_ids"]
                question.provider = final["provider"]
                if final["usage"]:
                    question.input_tokens = final["usage"].input_tokens
                    question.output_tokens = final["usage"].output_tokens
                session.commit()
                balance = bal.get_balance(session, user_id)
                answered = session.scalar(
                    select(func.count()).select_from(Question).where(
                        Question.user_id == user_id, Question.status == "answered"
                    )
                )
                if answered == 1:  # the user's first answer is the start of the conversion window
                    events.log_event(session, user_id, "free_answer_received", {"provider": final["provider"]})
            finally:
                session.close()
            finished = True
            yield _sse(
                "done",
                {
                    "question_id": question_id,
                    "answer": final["text"],
                    "cited_fact_ids": final["cited_ids"],
                    "provider": final["provider"],
                    "balance": balance,
                    "replayed": False,
                },
            )
        else:
            reason = failure["reason"] if failure else "providers_failed"
            balance = _fail_and_refund(
                session_factory, user_id, question_id, request_id, reason, failure["problems"] if failure else []
            )
            finished = True
            yield _sse("failed", {"code": reason, "message": FAILED_MESSAGES[reason], "balance": balance})
    finally:
        # The app was closed or the connection dropped before the answer finished: give the question back.
        if not finished:
            try:
                _fail_and_refund(session_factory, user_id, question_id, request_id, "interrupted", [])
            except Exception:
                log.exception("could not refund interrupted question %s", question_id)


def _replay_stream(question: Question, balance: int):
    if question.status == "answered":
        yield _sse(
            "done",
            {
                "question_id": question.id,
                "answer": question.answer,
                "cited_fact_ids": question.cited_fact_ids or [],
                "provider": question.provider,
                "balance": balance,
                "replayed": True,
            },
        )
    else:
        yield _sse("failed", {"code": "failed_earlier", "message": FAILED_MESSAGES["providers_failed"], "balance": balance})


@app.post("/users/{user_id}/ask")
def ask(
    user_id: int,
    body: AskIn,
    db: Session = Depends(get_db),
    providers=Depends(get_providers),
    session_factory=Depends(get_session_factory),
):
    """Spend one question and stream a grounded answer as server-sent events.

    Events: meta, token (many), reset, then done or failed. Sending the same request_id again
    returns the stored result without charging or calling the model again.
    """
    if db.get(User, user_id) is None:
        raise bal.UserNotFound(user_id)
    chart_row = db.scalar(select(Chart).where(Chart.user_id == user_id))
    if chart_row is None:
        raise ChartNotFound(user_id)  # checked before charging

    balance, replayed = bal.spend_question(db, user_id, body.request_id)  # raises 402 when empty

    existing = db.scalar(
        select(Question).where(Question.user_id == user_id, Question.request_id == body.request_id)
    )
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

    if replayed:
        if existing is None or existing.status == "pending":
            raise AnswerInProgress(body.request_id)
        return StreamingResponse(_replay_stream(existing, balance), media_type="text/event-stream", headers=headers)

    question = Question(user_id=user_id, request_id=body.request_id, text=body.question, status="pending")
    db.add(question)
    db.commit()

    return StreamingResponse(
        _answer_stream(session_factory, providers, user_id, question.id, body.request_id, body.question, chart_row.data),
        media_type="text/event-stream",
        headers=headers,
    )


# ---------- tracking ----------

@app.post("/users/{user_id}/events", status_code=202)
def track_event(user_id: int, body: EventIn, db: Session = Depends(get_db)):
    """The app reports what the user looked at. Only these events can come from the app."""
    if db.get(User, user_id) is None:
        raise bal.UserNotFound(user_id)
    events.log_event(db, user_id, body.name, body.properties)
    return {"status": "recorded"}


@app.get("/stats/conversion")
def conversion(db: Session = Depends(get_db)):
    """Counts only, no personal data. Compares the chart group with the control group."""
    return stats.conversion_stats(db)
