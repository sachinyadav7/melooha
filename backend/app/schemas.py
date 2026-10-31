from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class RequestIn(BaseModel):
    # The app makes a fresh id per tap and re-sends the same id on retry.
    request_id: str = Field(min_length=1, max_length=64)


class BalanceOut(BaseModel):
    user_id: int
    balance: int


class ActionOut(BaseModel):
    user_id: int
    balance: int
    replayed: bool  # true if this request_id was already applied and nothing changed
