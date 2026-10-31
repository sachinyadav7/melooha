from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import balance as bal
from app.config import settings
from app.db import Base, engine, get_db
from app.schemas import ActionOut, BalanceOut, RequestIn, UserCreate


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Simple for now. Switch to migrations (Alembic) if the schema keeps changing.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Melooha Show Your Work API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(bal.UserNotFound)
async def _user_not_found(_, __):
    return JSONResponse(
        status_code=404,
        content={"code": "user_not_found", "message": "We could not find this account."},
    )


@app.exception_handler(bal.InsufficientBalance)
async def _insufficient(_, __):
    return JSONResponse(
        status_code=402,
        content={
            "code": "insufficient_balance",
            "message": "You have no questions left. Add questions to continue.",
        },
    )


@app.exception_handler(bal.NothingToRefund)
async def _nothing_to_refund(_, __):
    return JSONResponse(
        status_code=409,
        content={"code": "nothing_to_refund", "message": "That question was not charged."},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/hello")
def hello():
    return {"message": "Hello from the Melooha backend"}


@app.post("/users", response_model=BalanceOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    user = bal.create_user(db, body.name)
    return BalanceOut(user_id=user.id, balance=bal.get_balance(db, user.id))


@app.get("/users/{user_id}/balance", response_model=BalanceOut)
def get_balance(user_id: int, db: Session = Depends(get_db)):
    if db.get(bal.User, user_id) is None:
        raise bal.UserNotFound(user_id)
    return BalanceOut(user_id=user_id, balance=bal.get_balance(db, user_id))


@app.post("/users/{user_id}/add-questions", response_model=ActionOut)
def add_questions(user_id: int, body: RequestIn, db: Session = Depends(get_db)):
    balance, replayed = bal.add_questions(db, user_id, body.request_id)
    return ActionOut(user_id=user_id, balance=balance, replayed=replayed)


@app.post("/users/{user_id}/spend", response_model=ActionOut)
def spend_question(user_id: int, body: RequestIn, db: Session = Depends(get_db)):
    balance, replayed = bal.spend_question(db, user_id, body.request_id)
    return ActionOut(user_id=user_id, balance=balance, replayed=replayed)
