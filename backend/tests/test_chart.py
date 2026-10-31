from datetime import date, time

import pytest

from app.chart import compute_chart
from app.cities import CITIES

NAGPUR = CITIES["Nagpur"]
BODY = {"date": "2000-04-15", "time": "12:00:00", "city": "Nagpur"}


def make_user(client):
    return client.post("/users", json={"name": "Sachin"}).json()["user_id"]


def planet(chart, key):
    return next(p for p in chart["planets"] if p["key"] == key)


# ---- engine: check against known astronomy ----

def test_sun_matches_known_sidereal_position():
    # 1 Jan 2000, 12:00 UTC (17:30 IST). Sun is about 16.5 degrees Sagittarius in the Lahiri zodiac.
    chart = compute_chart(date(2000, 1, 1), time(17, 30), *NAGPUR)
    sun = planet(chart, "SUN")
    assert sun["sign"] == "Sagittarius"
    assert sun["degree"] == pytest.approx(16.52, abs=0.1)


def test_ketu_is_opposite_rahu():
    chart = compute_chart(date(1995, 8, 20), time(9, 15), *NAGPUR)
    rahu, ketu = planet(chart, "RAHU"), planet(chart, "KETU")
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    assert (signs.index(rahu["sign"]) + 6) % 12 == signs.index(ketu["sign"])
    assert rahu["degree"] == pytest.approx(ketu["degree"], abs=0.01)


def test_ascendant_is_house_one_and_houses_follow_in_order():
    chart = compute_chart(date(2000, 4, 15), time(12, 0), *NAGPUR)
    assert chart["houses"][0]["sign"] == chart["ascendant"]["sign"]
    signs = [h["sign"] for h in chart["houses"]]
    assert len(set(signs)) == 12


def test_ascendant_near_sun_at_sunrise():
    # Around sunrise the rising sign is close to the Sun's sign (within one sign).
    chart = compute_chart(date(2000, 4, 15), time(6, 0), *NAGPUR)
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    gap = (signs.index(chart["ascendant"]["sign"]) - signs.index(planet(chart, "SUN")["sign"])) % 12
    assert gap in (0, 1, 11)


def test_every_planet_has_a_house_between_1_and_12():
    chart = compute_chart(date(1998, 11, 3), time(22, 40), *NAGPUR)
    assert len(chart["planets"]) == 9
    assert all(1 <= p["house"] <= 12 for p in chart["planets"])


def test_same_input_gives_same_chart():
    a = compute_chart(date(1998, 11, 3), time(22, 40), *NAGPUR)
    b = compute_chart(date(1998, 11, 3), time(22, 40), *NAGPUR)
    assert a == b


# ---- facts: IDs the answers will be checked against ----

def test_facts_have_unique_ids_and_match_planets():
    chart = compute_chart(date(2000, 4, 15), time(12, 0), *NAGPUR)
    ids = [f["id"] for f in chart["facts"]]
    assert len(ids) == len(set(ids))
    sun = planet(chart, "SUN")
    assert f"P_SUN_H{sun['house']}" in ids
    assert f"P_SUN_S_{sun['sign'].upper()}" in ids
    assert any(i.startswith("ASC_") for i in ids)
    assert any(i.startswith("MOON_NAK_") for i in ids)


# ---- API ----

def test_save_and_read_chart(client):
    uid = make_user(client)
    res = client.put(f"/users/{uid}/chart", json=BODY)
    assert res.status_code == 200
    saved = res.json()
    assert saved["city"] == "Nagpur"
    assert len(saved["planets"]) == 9 and len(saved["houses"]) == 12
    assert client.get(f"/users/{uid}/chart").json() == saved


def test_city_lookup_ignores_case_and_spaces(client):
    uid = make_user(client)
    res = client.put(f"/users/{uid}/chart", json={**BODY, "city": "  nagpur "})
    assert res.status_code == 200 and res.json()["city"] == "Nagpur"


def test_correcting_birth_details_replaces_the_chart(client):
    uid = make_user(client)
    first = client.put(f"/users/{uid}/chart", json=BODY).json()
    second = client.put(f"/users/{uid}/chart", json={**BODY, "time": "23:30:00"}).json()
    assert first["ascendant"] != second["ascendant"]
    assert client.get(f"/users/{uid}/chart").json() == second


def test_unknown_city_gets_a_friendly_error(client):
    uid = make_user(client)
    res = client.put(f"/users/{uid}/chart", json={**BODY, "city": "Atlantis"})
    assert res.status_code == 422
    assert res.json()["code"] == "city_not_supported"


def test_chart_before_birth_details_returns_404(client):
    uid = make_user(client)
    res = client.get(f"/users/{uid}/chart")
    assert res.status_code == 404 and res.json()["code"] == "chart_not_found"


def test_chart_for_unknown_user_returns_404(client):
    assert client.put("/users/999/chart", json=BODY).status_code == 404
    assert client.get("/users/999/chart").status_code == 404


def test_cities_list_includes_nagpur(client):
    assert "Nagpur" in client.get("/cities").json()["cities"]
