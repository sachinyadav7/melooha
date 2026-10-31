"""Plain-language meanings, so a first-time user understands the chart without astrology words."""

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
    "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
    "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]

# key -> (display name, what it stands for in plain words)
PLANETS = {
    "SUN": ("Sun", "Your core self, confidence and goals"),
    "MOON": ("Moon", "Your mind, moods and emotional needs"),
    "MARS": ("Mars", "Your energy, courage and drive"),
    "MERCURY": ("Mercury", "How you think, learn and communicate"),
    "JUPITER": ("Jupiter", "Luck, wisdom and growth"),
    "VENUS": ("Venus", "Love, comfort and relationships"),
    "SATURN": ("Saturn", "Discipline, delays and long-term effort"),
    "RAHU": ("Rahu", "Strong desires and restless ambition"),
    "KETU": ("Ketu", "Detachment and letting go"),
}

# house number -> plain-language area of life
HOUSES = {
    1: "You and your personality",
    2: "Money and family",
    3: "Effort, courage and communication",
    4: "Home and peace of mind",
    5: "Learning, creativity and children",
    6: "Daily work and obstacles",
    7: "Partnerships and marriage",
    8: "Sudden changes and hidden things",
    9: "Luck and higher learning",
    10: "Career and status",
    11: "Gains and friends",
    12: "Expenses, rest and foreign places",
}
