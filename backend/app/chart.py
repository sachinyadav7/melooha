"""Birth chart engine (Vedic / sidereal, Lahiri ayanamsa, whole-sign houses).

All positions are computed here in code. The LLM never calculates or invents them: it only
receives the facts this module produces, each with a fixed ID.
"""
import threading
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import swisseph as swe

from app.cities import TIMEZONE
from app.meanings import HOUSES, NAKSHATRAS, PLANETS, SIGNS

# Built-in Moshier ephemeris (no data files needed), sidereal positions, with speed for retrograde.
_FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

_SWE_IDS = {
    "SUN": swe.SUN,
    "MOON": swe.MOON,
    "MARS": swe.MARS,
    "MERCURY": swe.MERCURY,
    "JUPITER": swe.JUPITER,
    "VENUS": swe.VENUS,
    "SATURN": swe.SATURN,
    "RAHU": swe.MEAN_NODE,
}

# pyswisseph keeps global settings, and the web server runs requests in threads.
_lock = threading.Lock()

NAKSHATRA_SPAN = 360 / 27


def _julian_day_utc(birth_date: date, birth_time: time) -> float:
    local = datetime.combine(birth_date, birth_time).replace(tzinfo=ZoneInfo(TIMEZONE))
    utc = local.astimezone(ZoneInfo("UTC"))
    hour = utc.hour + utc.minute / 60 + utc.second / 3600
    return swe.julday(utc.year, utc.month, utc.day, hour)


def _sign_index(longitude: float) -> int:
    return int(longitude // 30) % 12


def compute_chart(birth_date: date, birth_time: time, lat: float, lon: float) -> dict:
    jd = _julian_day_utc(birth_date, birth_time)

    with _lock:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        positions = {}
        retrograde = {}
        for key, swe_id in _SWE_IDS.items():
            values, _ = swe.calc_ut(jd, swe_id, _FLAGS)
            positions[key] = values[0] % 360
            retrograde[key] = values[3] < 0
        _, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
        ascendant = ascmc[0] % 360

    # Ketu is always exactly opposite Rahu. Both nodes move backward by convention.
    positions["KETU"] = (positions["RAHU"] + 180) % 360
    retrograde["RAHU"] = True
    retrograde["KETU"] = True

    asc_sign = _sign_index(ascendant)

    houses = []
    for number in range(1, 13):
        sign = SIGNS[(asc_sign + number - 1) % 12]
        houses.append({"number": number, "sign": sign, "label": HOUSES[number]})

    planets = []
    for key, (name, meaning) in PLANETS.items():
        longitude = positions[key]
        sign_idx = _sign_index(longitude)
        planets.append(
            {
                "key": key,
                "name": name,
                "meaning": meaning,
                "sign": SIGNS[sign_idx],
                "degree": round(longitude % 30, 2),
                "house": ((sign_idx - asc_sign) % 12) + 1,
                "retrograde": retrograde[key],
                "nakshatra": NAKSHATRAS[int(longitude // NAKSHATRA_SPAN) % 27],
            }
        )

    result = {
        "ascendant": {"sign": SIGNS[asc_sign], "degree": round(ascendant % 30, 2)},
        "houses": houses,
        "planets": planets,
    }
    result["facts"] = build_facts(result)
    return result


def build_facts(chart: dict) -> list[dict]:
    """The only statements an answer is allowed to rely on. Each has a stable ID."""
    facts = [
        {
            "id": f"ASC_{chart['ascendant']['sign'].upper()}",
            "text": f"Your rising sign (ascendant) is {chart['ascendant']['sign']}.",
        }
    ]
    for p in chart["planets"]:
        area = HOUSES[p["house"]]
        facts.append(
            {
                "id": f"P_{p['key']}_S_{p['sign'].upper()}",
                "text": f"{p['name']} is in {p['sign']}.",
            }
        )
        facts.append(
            {
                "id": f"P_{p['key']}_H{p['house']}",
                "text": f"{p['name']} is in house {p['house']} ({area}).",
            }
        )
        if p["key"] == "MOON":
            facts.append(
                {
                    "id": f"MOON_NAK_{p['nakshatra'].upper().replace(' ', '_')}",
                    "text": f"Your Moon is in the {p['nakshatra']} nakshatra.",
                }
            )
    return facts
