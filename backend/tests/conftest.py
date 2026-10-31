import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.llm import Usage
from app.main import app, get_providers, get_session_factory


@pytest.fixture()
def engine():
    """A fresh in-memory database for every test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def db_session(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def providers():
    """The fake providers the app uses in a test. Tests fill this list."""
    return []


@pytest.fixture()
def client(db_session, session_factory, providers):
    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_providers] = lambda: providers
    yield TestClient(app)
    app.dependency_overrides.clear()


class FakeProvider:
    """Stands in for Gemini or Groq. `responses` is used one per call: text, or an Exception to raise."""

    def __init__(self, name, responses):
        self.name = name
        self.responses = list(responses)
        self.calls = 0
        self.prompts = []

    def stream(self, system, user):
        self.prompts.append(user)
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        for word in response.split(" "):
            yield word + " "
        yield Usage(input_tokens=100, output_tokens=20)
