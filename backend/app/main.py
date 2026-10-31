from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import balance as bal
from app.chart import compute_chart
from app.cities import CITIES, find_city
from app.config import settings
from app.db import Base, engine, get_db
from app.models import Chart, User
from app.schemas import ActionOut, BalanceOut, BirthDetails, ChartOut, RequestIn, UserCreate


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


class CityNotSupported(Exception):
    pass


class ChartNotFound(Exception):
    pass


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


@app.exception_handler(CityNotSupported)
async def _city_not_supported(_, __):
    return JSONResponse(
        status_code=422,
        content={
            "code": "city_not_supported",
            "message": "We do not have this city yet. Pick the nearest big city from the list.",
        },
    )


@app.exception_handler(ChartNotFound)
async def _chart_not_found(_, __):
    return JSONResponse(
        status_code=404,
        content={"code": "chart_not_found", "message": "Add your birth details to see your chart."},
    )


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


@app.post("/users", response_model=BalanceOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    user = bal.create_user(db, body.name)
    return BalanceOut(user_id=user.id, balance=bal.get_balance(db, user.id))


@app.get("/users/{user_id}/balance", response_model=BalanceOut)
def get_balance(user_id: int, db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
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
    return _chart_out(row)


@app.get("/users/{user_id}/chart", response_model=ChartOut)
def get_chart(user_id: int, db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise bal.UserNotFound(user_id)
    row = db.scalar(select(Chart).where(Chart.user_id == user_id))
    if row is None:
        raise ChartNotFound(user_id)
    return _chart_out(row)
