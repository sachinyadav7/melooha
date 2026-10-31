import json

from app.models import Question
from tests.conftest import FakeProvider

BODY = {"date": "2000-04-15", "time": "12:00:00", "city": "Nagpur"}


def parse_sse(text):
    events = []
    for block in text.strip().split("\n\n"):
        name, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        events.append((name, data))
    return events


def setup_user(client):
    uid = client.post("/users", json={"name": "Sachin"}).json()["user_id"]
    chart = client.put(f"/users/{uid}/chart", json=BODY).json()
    saturn = next(p for p in chart["planets"] if p["key"] == "SATURN")
    return uid, saturn["house"]


def good_answer(house):
    return (
        f"Saturn is in house {house}, which is about slow, steady effort. [[P_SATURN_H{house}]] "
        "Progress may come gradually rather than all at once."
    )


def ask(client, uid, request_id="r1", question="Will my career improve?"):
    res = client.post(f"/users/{uid}/ask", json={"question": question, "request_id": request_id})
    return res, (parse_sse(res.text) if res.headers.get("content-type", "").startswith("text/event-stream") else None)


def names(events):
    return [name for name, _ in events]


def test_grounded_answer_streams_and_spends_one_question(client, providers, db_session):
    uid, house = setup_user(client)
    providers.append(FakeProvider("gemini", [good_answer(house)]))

    res, events = ask(client, uid)

    assert res.status_code == 200
    assert names(events)[0] == "meta" and names(events)[-1] == "done"
    assert names(events).count("token") > 3  # streamed in pieces
    done = events[-1][1]
    assert done["provider"] == "gemini"
    assert done["cited_fact_ids"] == [f"P_SATURN_H{house}"]
    assert done["balance"] == 0

    saved = db_session.query(Question).one()
    assert saved.status == "answered" and saved.input_tokens == 100 and saved.output_tokens == 20


def test_falls_back_to_second_provider_without_showing_an_error(client, providers):
    uid, house = setup_user(client)
    first = FakeProvider("gemini", [RuntimeError("quota exceeded: secret details")])
    second = FakeProvider("groq", [good_answer(house)])
    providers.extend([first, second])

    res, events = ask(client, uid)

    assert names(events)[-1] == "done"
    assert events[-1][1]["provider"] == "groq"
    assert "secret details" not in res.text and "quota" not in res.text


def test_both_providers_failing_refunds_and_shows_a_friendly_message(client, providers):
    uid, _ = setup_user(client)
    providers.extend([FakeProvider("gemini", [RuntimeError("boom")]), FakeProvider("groq", [RuntimeError("boom")])])

    res, events = ask(client, uid)

    assert names(events)[-1] == "failed"
    failed = events[-1][1]
    assert failed["code"] == "providers_failed" and failed["balance"] == 1
    assert "boom" not in res.text and "Traceback" not in res.text
    assert client.get(f"/users/{uid}/balance").json()["balance"] == 1


def test_no_providers_configured_is_handled_like_a_failure(client, providers):
    uid, _ = setup_user(client)
    _, events = ask(client, uid)
    assert events[-1][0] == "failed"
    assert client.get(f"/users/{uid}/balance").json()["balance"] == 1


def test_answer_with_invented_fact_is_rejected_then_rewritten(client, providers):
    uid, house = setup_user(client)
    wrong = house % 12 + 1
    bad = f"Saturn is in house {wrong}. [[P_SATURN_H{wrong}]]"
    provider = FakeProvider("gemini", [bad, good_answer(house)])
    providers.append(provider)

    _, events = ask(client, uid)

    assert "reset" in names(events)
    assert names(events)[-1] == "done"
    assert provider.calls == 2
    assert "broke the rules" in provider.prompts[1]  # the rewrite is told what was wrong


def test_answer_that_stays_ungrounded_is_blocked_and_refunded(client, providers, db_session):
    uid, house = setup_user(client)
    wrong = house % 12 + 1
    providers.append(FakeProvider("gemini", [f"Saturn is in house {wrong}. [[P_SATURN_H{wrong}]]"]))

    res, events = ask(client, uid)

    assert names(events)[-1] == "failed"
    assert events[-1][1]["code"] == "not_grounded" and events[-1][1]["balance"] == 1
    saved = db_session.query(Question).one()
    assert saved.status == "failed" and saved.problems


def test_same_request_id_is_not_charged_or_answered_twice(client, providers):
    uid, house = setup_user(client)
    provider = FakeProvider("gemini", [good_answer(house)])
    providers.append(provider)
    client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-1"})  # balance 6

    ask(client, uid, "r1")
    _, again = ask(client, uid, "r1")

    assert provider.calls == 1
    assert again[-1][0] == "done" and again[-1][1]["replayed"] is True
    assert client.get(f"/users/{uid}/balance").json()["balance"] == 5


def test_no_questions_left_returns_402_before_any_model_call(client, providers):
    uid, house = setup_user(client)
    provider = FakeProvider("gemini", [good_answer(house)])
    providers.append(provider)
    ask(client, uid, "r1")

    res, _ = ask(client, uid, "r2")

    assert res.status_code == 402 and res.json()["code"] == "insufficient_balance"
    assert provider.calls == 1


def test_missing_chart_is_reported_without_charging(client, providers):
    uid = client.post("/users", json={"name": "Sachin"}).json()["user_id"]
    res, _ = ask(client, uid)
    assert res.status_code == 404 and res.json()["code"] == "chart_not_found"
    assert client.get(f"/users/{uid}/balance").json()["balance"] == 1


def test_question_must_be_a_sensible_length(client, providers):
    uid, _ = setup_user(client)
    assert ask(client, uid, question="hi")[0].status_code == 422
    assert ask(client, uid, question="x" * 501)[0].status_code == 422


def test_unknown_user_returns_404(client):
    res, _ = ask(client, 999)
    assert res.status_code == 404
