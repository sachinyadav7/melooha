import pytest

from app import balance as bal


def make_user(client, name="Sachin"):
    res = client.post("/users", json={"name": name})
    assert res.status_code == 201
    return res.json()["user_id"]


def test_new_user_gets_one_free_question(client):
    res = client.post("/users", json={"name": "Sachin"})
    assert res.json()["balance"] == 1


def test_spend_reduces_balance(client):
    uid = make_user(client)
    res = client.post(f"/users/{uid}/spend", json={"request_id": "q-1"})
    assert res.status_code == 200
    assert res.json() == {"user_id": uid, "balance": 0, "replayed": False}


def test_spend_with_zero_balance_is_blocked(client):
    uid = make_user(client)
    client.post(f"/users/{uid}/spend", json={"request_id": "q-1"})
    res = client.post(f"/users/{uid}/spend", json={"request_id": "q-2"})
    assert res.status_code == 402
    assert res.json()["code"] == "insufficient_balance"
    assert client.get(f"/users/{uid}/balance").json()["balance"] == 0


def test_same_spend_request_is_not_charged_twice(client):
    uid = make_user(client)
    client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-1"})  # balance 6
    first = client.post(f"/users/{uid}/spend", json={"request_id": "q-1"}).json()
    again = client.post(f"/users/{uid}/spend", json={"request_id": "q-1"}).json()
    assert first["balance"] == 5 and first["replayed"] is False
    assert again["balance"] == 5 and again["replayed"] is True


def test_add_questions_adds_a_pack(client):
    uid = make_user(client)
    res = client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-1"})
    assert res.json()["balance"] == 1 + 5


def test_same_add_request_is_not_applied_twice(client):
    uid = make_user(client)
    client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-1"})
    again = client.post(f"/users/{uid}/add-questions", json={"request_id": "buy-1"}).json()
    assert again["balance"] == 6 and again["replayed"] is True


def test_unknown_user_returns_404(client):
    res = client.post("/users/999/spend", json={"request_id": "q-1"})
    assert res.status_code == 404
    assert res.json()["code"] == "user_not_found"
    assert client.get("/users/999/balance").status_code == 404


def test_empty_request_id_is_rejected(client):
    uid = make_user(client)
    res = client.post(f"/users/{uid}/spend", json={"request_id": ""})
    assert res.status_code == 422


def test_refund_returns_a_spent_question_once(db_session, client):
    uid = make_user(client)
    client.post(f"/users/{uid}/spend", json={"request_id": "q-1"})
    balance, replayed = bal.refund_question(db_session, uid, "q-1")
    assert (balance, replayed) == (1, False)
    balance, replayed = bal.refund_question(db_session, uid, "q-1")
    assert (balance, replayed) == (1, True)


def test_refund_without_a_spend_is_refused(db_session, client):
    uid = make_user(client)
    with pytest.raises(bal.NothingToRefund):
        bal.refund_question(db_session, uid, "never-spent")
