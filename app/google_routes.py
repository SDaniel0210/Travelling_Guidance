import os
import requests


class RouteError(Exception):
    pass


def get_route_info(origin: str, destination: str, mode: str = "driving"):
    """
    origin / destination: sima cím string (pl. 'Budapest, Hungary')
    mode: 'driving' | 'transit' | 'walking' | 'bicycling'
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RouteError("Nincs beállítva GOOGLE_MAPS_API_KEY környezeti változó.")

    url = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        # forgalom miatt (driving, transit esetén)
        "departure_time": "now",
        "alternatives": "false",
        "key": api_key,
    }

    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()

    if data.get("status") != "OK":
        msg = data.get("error_message", data.get("status", "Ismeretlen hiba"))
        raise RouteError(f"Directions API hiba: {msg}")

    route = data["routes"][0]
    leg = route["legs"][0]

    distance_m = leg["distance"]["value"]        # méter
    duration_s = leg["duration"]["value"]        # másodperc

    distance_km = distance_m / 1000.0
    duration_min = duration_s / 60.0

    # Forgalommal módosított idő (csak bizonyos mode-oknál)
    traffic_duration_min = None
    if "duration_in_traffic" in leg:
        traffic_duration_min = leg["duration_in_traffic"]["value"] / 60.0

    # Warnings: útlezárás, komp, útdíj, határ, stb.
    warnings = route.get("warnings", [])

    return {
        "distance_km": distance_km,
        "duration_min": duration_min,
        "traffic_duration_min": traffic_duration_min,
        "warnings": warnings,
        "raw": data,
    }
