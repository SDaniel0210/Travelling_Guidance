import os
import requests

class RouteError(Exception):
    pass


def get_route_info(origin: str, destination: str, travelmode: str = "driving") -> dict:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RouteError("Nincs beállítva GOOGLE_MAPS_API_KEY környezeti változó.")

    url = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": origin,
        "destination": destination,
        "mode": travelmode,
        "key": api_key,
    }

    # Forgalmi időhöz / aktuális menetrendhez jól jön a departure_time=now (driving + transit)
    if travelmode in ("driving", "transit"):
        params["departure_time"] = "now"

    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        raise RouteError(f"HTTP hiba: {resp.status_code}")

    data = resp.json()
    status = data.get("status")
    if status != "OK":
        msg = data.get("error_message", status)
        raise RouteError(f"Directions API hiba: {msg}")

    routes = data.get("routes", [])
    if not routes:
        raise RouteError("Nem található útvonal a megadott pontok között.")

    route = routes[0]
    leg = route["legs"][0]

    distance_m = leg["distance"]["value"]
    duration_s = leg["duration"]["value"]

    distance_km = distance_m / 1000.0
    duration_min = duration_s / 60.0

    # Forgalommal számolt idő, ha van
    traffic_duration_min = None
    if "duration_in_traffic" in leg:
        traffic_duration_min = leg["duration_in_traffic"]["value"] / 60.0

    # Figyelmeztetések
    warnings = route.get("warnings", [])

    # ==== TRANSIT RÉSZLETEK KINYERÉSE (ha 'transit' mód) ====
    transit_segments = []
    if travelmode == "transit":
        for step in leg.get("steps", []):
            td = step.get("transit_details")
            if not td:
                continue

            line = td.get("line", {}) or {}
            vehicle = line.get("vehicle", {}) or {}

            seg = {
                "departure_stop": (td.get("departure_stop") or {}).get("name"),
                "arrival_stop": (td.get("arrival_stop") or {}).get("name"),
                "departure_time": (td.get("departure_time") or {}).get("text"),
                "arrival_time": (td.get("arrival_time") or {}).get("text"),
                "line_name": line.get("name"),
                "vehicle_type": vehicle.get("type"),
            }
            transit_segments.append(seg)

    return {
        "distance_km": distance_km,
        "duration_min": duration_min,
        "traffic_duration_min": traffic_duration_min,
        "warnings": warnings,
        "transit_segments": transit_segments,  # LISTA, lehet üres is
    }
