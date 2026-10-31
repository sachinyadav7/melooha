from datetime import date, time

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class RequestIn(BaseModel):
    # The app makes a fresh id per tap and re-sends the same id on retry.
    request_id: str = Field(min_length=1, max_length=64)


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    request_id: str = Field(min_length=1, max_length=64)


class BalanceOut(BaseModel):
    user_id: int
    balance: int


class ActionOut(BaseModel):
    user_id: int
    balance: int
    replayed: bool  # true if this request_id was already applied and nothing changed


class BirthDetails(BaseModel):
    date: date
    time: time
    city: str = Field(min_length=1, max_length=100)


class AscendantOut(BaseModel):
    sign: str
    degree: float


class HouseOut(BaseModel):
    number: int
    sign: str
    label: str


class PlanetOut(BaseModel):
    key: str
    name: str
    meaning: str
    sign: str
    degree: float
    house: int
    retrograde: bool
    nakshatra: str


class FactOut(BaseModel):
    id: str
    text: str


class ChartOut(BaseModel):
    city: str
    ascendant: AscendantOut
    houses: list[HouseOut]
    planets: list[PlanetOut]
    facts: list[FactOut]
