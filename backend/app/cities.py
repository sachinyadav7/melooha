"""Bundled list of Indian cities (name, latitude, longitude). All use Asia/Kolkata time.

A fixed list avoids a live geocoding call, which is slower and can fail on free hosting.
Trade-off: only these cities are supported for now.
"""

TIMEZONE = "Asia/Kolkata"

CITIES = {
    "Agra": (27.1767, 78.0081),
    "Ahmedabad": (23.0225, 72.5714),
    "Amravati": (20.9374, 77.7796),
    "Amritsar": (31.6340, 74.8723),
    "Aurangabad": (19.8762, 75.3433),
    "Bengaluru": (12.9716, 77.5946),
    "Bhopal": (23.2599, 77.4126),
    "Bhubaneswar": (20.2961, 85.8245),
    "Chandigarh": (30.7333, 76.7794),
    "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558),
    "Dehradun": (30.3165, 78.0322),
    "Delhi": (28.6139, 77.2090),
    "Guwahati": (26.1445, 91.7362),
    "Hyderabad": (17.3850, 78.4867),
    "Indore": (22.7196, 75.8577),
    "Jaipur": (26.9124, 75.7873),
    "Kanpur": (26.4499, 80.3319),
    "Kochi": (9.9312, 76.2673),
    "Kolhapur": (16.7050, 74.2433),
    "Kolkata": (22.5726, 88.3639),
    "Lucknow": (26.8467, 80.9462),
    "Madurai": (9.9252, 78.1198),
    "Mumbai": (19.0760, 72.8777),
    "Nagpur": (21.1458, 79.0882),
    "Nashik": (19.9975, 73.7898),
    "Patna": (25.5941, 85.1376),
    "Pune": (18.5204, 73.8567),
    "Raipur": (21.2514, 81.6296),
    "Ranchi": (23.3441, 85.3096),
    "Surat": (21.1702, 72.8311),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Vadodara": (22.3072, 73.1812),
    "Varanasi": (25.3176, 82.9739),
    "Visakhapatnam": (17.6868, 83.2185),
}


def find_city(name: str):
    """Case-insensitive lookup. Returns (canonical_name, lat, lon) or None."""
    wanted = name.strip().lower()
    for city, (lat, lon) in CITIES.items():
        if city.lower() == wanted:
            return city, lat, lon
    return None
