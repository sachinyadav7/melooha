from datetime import datetime, timedelta

import pytest

from app import stats
from app.experiment import group_for
from app.models import Event
from tests.conftest import FakeProvider

BODY = {"date": "2000-04-15", "time": "12:00:00", "city": "Nagpur"}
T0 = datetime(2026, 11, 1, 10, 0, 0)


def make_user(client):
    return client.post("/users", json={"name": "Sachin"}).json()["user_id"]


def names_for(db_session, user_id):
    return [e.name for e in db_session.query(Event).filter_by(user_id=user_id).order_by(Event.id)]


# ---- experiment split ----

def test_group_is_stable_and_valid():
    assert {group_for(i) for i in range(1, 50)} == {"chart", "control"}
    assert all(group_for(7) == group_for(7) for _ in range(5))


def test_split_is_roughly_half():
    chart = sum(group_for(i) == "chart" for i in range(1, 2001))
    assert 900 < chart < 1100


def test_user_response_includes_group(client):
    created = client.post("/users", json={"name": "Sachin"}).json()
    assert created["experiment_group"] == group_for(created["user_id"])
    fetched = client.get(f"/users/{created['user_id']}").json()
    assert fetched == created
    assert client.get("/users/999").status_code == 404


# ---- events from the app ----

def test_app_can_report_view_events(client, db_session):
    uid = make_user(client)
    res = client.post(f"/users/{uid}/events", json={"name": "chart_viewed"})
    assert res.status_code == 202
    client.post(f"/users/{uid}/events", json={"name": "evidence_tapped", "properties": {"fact": "P_SATURN_H3"}})
    assert names_for(db_session, uid) == ["chart_viewed", "evidence_tapped"]


def test_app_cannot_fake_server_events(client, db_session):
    uid = make_user(client)
    for name in ("add_questions_clicked", "free_answer_received", "onboarding_done", "made_up"):
        assert client.post(f"/users/{uid}/events", json={"name": name}).status_code == 422
    assert names_for(db_session, uid) == []


def test_event_for_unknown_user_is_404(client):
    assert client.post("/users/999/events", json={"name": "chart_viewed"}).status_code == 404


def test_too_many_properties_are_rejected(client):
    uid = make_user(client)
    props = {f"k{i}": i for i in range(11)}
    assert client.post(f"/users/{uid}/events", json={"name": "chart_viewed", "properties": props}).status_code == 422


# ---- events logged by the server ----

def test_saving_birth_details_logs_onboarding_once(client, db_session):
    uid = make_user(client)
    client.put(f"/users/{uid}/chart", json=BODY)
    client.put(f"/users/{uid}/chart", json={**BODY, "time": "23:00:00"})  # a correction
    assert names_for(db_session, uid) == ["onboarding_done"]


def test_add_questions_logs_once_even_if_repeated(client, db_session):
    uid = make_user(client)
    client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-1"})
    client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-1"})  # retry of the same tap
    assert names_for(db_session, uid) == ["add_questions_clicked"]
    client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-2"})
    assert names_for(db_session, uid).count("add_questions_clicked") == 2


def test_only_the_first_answer_logs_free_answer_received(client, providers, db_session):
    uid = make_user(client)
    chart = client.put(f"/users/{uid}/chart", json=BODY).json()
    house = next(p for p in chart["planets"] if p["key"] == "SATURN")["house"]
    providers.append(FakeProvider("gemini", [f"Saturn is in house {house}, about steady effort. [[P_SATURN_H{house}]]"]))
    client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-1"})

    for request_id in ("a", "b"):
        client.post(f"/users/{uid}/ask", json={"question": "Will I do well?", "request_id": request_id})

    assert names_for(db_session, uid).count("free_answer_received") == 1


def test_failed_answer_does_not_log_free_answer_received(client, providers, db_session):
    uid = make_user(client)
    client.put(f"/users/{uid}/chart", json=BODY)
    providers.append(FakeProvider("gemini", [RuntimeError("down")]))
    client.post(f"/users/{uid}/ask", json={"question": "Will I do well?", "request_id": "a"})
    assert "free_answer_received" not in names_for(db_session, uid)


# ---- the conversion metric ----

@pytest.fixture()
def odd_even_groups(monkeypatch):
    """Odd user ids are in the chart group, even ids in control, so the test can predict results."""
    monkeypatch.setattr(stats, "group_for", lambda uid: "chart" if uid % 2 else "control")


def add(db, user_id, name, when):
    db.add(Event(user_id=user_id, name=name, created_at=when))
    db.commit()


def test_empty_stats_have_no_rate(client):
    groups = client.get("/stats/conversion").json()["groups"]
    assert groups["chart"]["conversion_rate"] is None and groups["control"]["users"] == 0


def test_conversion_counts_only_purchases_within_24_hours(client, db_session, odd_even_groups):
    ids = [make_user(client) for _ in range(6)]  # ids 1..6
    u1, u2, u3, u4, u5, u6 = ids

    # chart group: u1 buys after 1 hour, u3 buys after 25 hours, u5 never buys
    for uid in (u1, u3, u5):
        add(db_session, uid, "chart_viewed", T0)
        add(db_session, uid, "free_answer_received", T0)
    add(db_session, u1, "add_questions_clicked", T0 + timedelta(hours=1))
    add(db_session, u3, "add_questions_clicked", T0 + timedelta(hours=25))
    add(db_session, u1, "evidence_tapped", T0)
    add(db_session, u5, "paywall_viewed", T0)

    # control group: u2 buys after 2 hours, u4 never buys, u6 never got an answer
    for uid in (u2, u4):
        add(db_session, uid, "free_answer_received", T0)
    add(db_session, u2, "add_questions_clicked", T0 + timedelta(hours=2))

    groups = client.get("/stats/conversion").json()["groups"]

    chart = groups["chart"]
    assert (chart["users"], chart["viewed_chart"], chart["tapped_evidence"]) == (3, 3, 1)
    assert (chart["got_first_answer"], chart["saw_paywall"], chart["converted"]) == (3, 1, 1)
    assert chart["conversion_rate"] == pytest.approx(0.3333, abs=0.0001)

    control = groups["control"]
    assert (control["users"], control["got_first_answer"], control["converted"]) == (3, 2, 1)
    assert control["conversion_rate"] == 0.5


def test_purchase_before_first_answer_does_not_count(client, db_session, odd_even_groups):
    uid = make_user(client)
    add(db_session, uid, "add_questions_clicked", T0 - timedelta(hours=1))
    add(db_session, uid, "free_answer_received", T0)
    chart = client.get("/stats/conversion").json()["groups"]["chart"]
    assert chart["got_first_answer"] == 1 and chart["converted"] == 0
