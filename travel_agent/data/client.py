"""
LiveDataClient — single API source for all travel data.

All three data types fetched from Amadeus sandbox when credentials are set;
each falls back independently to embedded static data on any error.

Bookings generate local UUIDs — no external server required.

Setup (free at https://developers.amadeus.com/):
  export AMADEUS_CLIENT_ID="your_id"
  export AMADEUS_CLIENT_SECRET="your_secret"
  export ORIGIN_IATA="TLV"   # optional, default JFK
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import date as _date

try:
    from ..models import Activity, ContactInfo, Flight, Hotel, PassengerInfo, PaymentInfo
    from .static import STATIC_DATA
except ImportError:
    from models import Activity, ContactInfo, Flight, Hotel, PassengerInfo, PaymentInfo
    from data.static import STATIC_DATA


# ── Destination → IATA / coordinates ──────────────────────────────────────────

_DEST_IATA: dict[str, str] = {
    "Tokyo":    "TYO",
    "Paris":    "PAR",
    "Bali":     "DPS",
    "New York": "NYC",
    "Japan": "TYO",
    "France": "PAR",
    "Italy": "ROM",
    "Greece": "ATH",
    "Thailand": "BKK",
    "Spain": "MAD",
    "United Kingdom": "LON",
    "Mexico": "MEX",
    "Israel": "TLV",
}

_DEST_COORDS: dict[str, tuple[float, float]] = {
    "Tokyo":    (35.6762,  139.6503),
    "Paris":    (48.8566,    2.3522),
    "Bali":     (-8.4095,  115.1889),
    "New York": (40.7128,  -74.0060),
    "Japan": (35.6762, 139.6503),
    "France": (46.2276, 2.2137),
    "Italy": (41.9028, 12.4964),
    "Greece": (37.9838, 23.7275),
    "Thailand": (13.7563, 100.5018),
    "Spain": (40.4168, -3.7038),
    "United Kingdom": (51.5072, -0.1276),
    "Mexico": (19.4326, -99.1332),
    "Israel": (32.0853, 34.7818),
}

_ORIGIN_IATA: str = os.environ.get("ORIGIN_IATA", "JFK")

_CARRIERS: dict[str, str] = {
    "JL": "Japan Airlines",       "NH": "All Nippon Airways",
    "AA": "American Airlines",    "UA": "United Airlines",
    "DL": "Delta Air Lines",      "BA": "British Airways",
    "AF": "Air France",           "LH": "Lufthansa",
    "SQ": "Singapore Airlines",   "GA": "Garuda Indonesia",
    "EK": "Emirates",             "CX": "Cathay Pacific",
    "KL": "KLM",                  "IB": "Iberia",
    "TK": "Turkish Airlines",     "B6": "JetBlue",
    "WN": "Southwest",            "AS": "Alaska Airlines",
    "LX": "Swiss",                "OS": "Austrian Airlines",
    "AY": "Finnair",              "SK": "SAS",
    "TG": "Thai Airways",         "CA": "Air China",
    "MH": "Malaysia Airlines",    "QR": "Qatar Airways",
    "EY": "Etihad Airways",       "LY": "El Al",
}

_ACTIVITY_TAGS: dict[str, str] = {
    "SIGHTSEEING":       "culture",
    "FOOD_AND_DRINK":    "food",
    "ADVENTURE_AND_SPORT": "adventure",
    "NATURE_AND_OUTDOOR": "nature",
    "ENTERTAINMENT":     "culture",
    "LUXURY":            "luxury",
    "CULTURE":           "culture",
    "ART_AND_MUSEUMS":   "culture",
    "WELLNESS":          "luxury",
    "BEACH":             "nature",
    "ROMANCE":           "romance",
}


# ── Tag derivation helpers ─────────────────────────────────────────────────────

def _carrier_name(code: str) -> str:
    return _CARRIERS.get(code.upper(), code)


def _parse_duration_hours(iso_str: str) -> float:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso_str or "")
    if not m:
        return 0.0
    return round(int(m.group(1) or 0) + int(m.group(2) or 0) / 60, 1)


def _flight_style_tags(offer: dict) -> list[str]:
    tags: set[str] = set()
    itin     = offer["itineraries"][0]
    segments = itin["segments"]
    hours    = _parse_duration_hours(itin["duration"])
    price    = float(offer["price"]["total"])
    tags.add("luxury" if len(segments) == 1 else "budget")
    if hours > 12:
        tags.add("adventure")
    elif hours < 6:
        tags.add("culture")
    if price > 1200:
        tags.add("luxury")
    elif price < 600:
        tags.add("budget")
    return list(tags) or ["culture"]


def _hotel_style_tags(price_per_night: float, stars: int) -> list[str]:
    tags: set[str] = set()
    if stars >= 5 or price_per_night > 300:
        tags.add("luxury")
    elif price_per_night < 100:
        tags.add("budget")
    else:
        tags.add("culture")
    return list(tags) or ["culture"]


def _activity_style_tags(categories: list[str]) -> list[str]:
    tags = {_ACTIVITY_TAGS.get(c, "culture") for c in categories}
    return list(tags) or ["culture"]


# ── Client ─────────────────────────────────────────────────────────────────────

class LiveDataClient:
    """
    Single-source travel data client.

    Flights / Hotels / Activities: Amadeus API → embedded static fallback.
    Bookings: local UUID generation (no external server).

    The app runs standalone with no mock server; Amadeus credentials are
    optional but deliver real prices and real venue names.
    """

    def __init__(self) -> None:
        self._amadeus = None
        self._serpapi_key = os.environ.get("SERPAPI_API_KEY", "").strip()

        cid     = os.environ.get("AMADEUS_CLIENT_ID",     "").strip()
        csecret = os.environ.get("AMADEUS_CLIENT_SECRET", "").strip()
        if cid and csecret:
            try:
                from amadeus import Client as _AC
                self._amadeus = _AC(client_id=cid, client_secret=csecret, log_level="silent")
            except Exception:
                pass

    @property
    def using_live_data(self) -> bool:
        return self._amadeus is not None

    # ── Flights ───────────────────────────────────────────────────────────────

    def get_flights(self, destination: str, date: str, origin: str = "Tel Aviv") -> list[Flight]:
        if self._amadeus and destination in _DEST_IATA:
            try:
                origin_iata = os.environ.get("ORIGIN_IATA", _ORIGIN_IATA)
                resp = self._amadeus.shopping.flight_offers_search.get(
                    originLocationCode=origin_iata,
                    destinationLocationCode=_DEST_IATA[destination],
                    departureDate=date,
                    adults=1,
                    currencyCode="USD",
                    max=6,
                )
                if resp.data:
                    flights, seen = [], set()
                    for offer in resp.data:
                        fid = offer.get("id", "")
                        if fid in seen:
                            continue
                        seen.add(fid)
                        itin    = offer["itineraries"][0]
                        carrier = (
                            offer.get("validatingAirlineCodes")
                            or [itin["segments"][0]["carrierCode"]]
                        )[0]
                        flights.append(Flight(
                            id=fid,
                            origin=origin,
                            destination=destination,
                            price=float(offer["price"]["total"]),
                            airline=_carrier_name(carrier),
                            duration_hours=_parse_duration_hours(itin["duration"]),
                            style_tags=_flight_style_tags(offer),
                        ))
                    if flights:
                        return flights
            except Exception:
                pass
        all_flights = STATIC_DATA.get(destination, {}).get("flights", [])
        return [f for f in all_flights if f.origin == origin]

    # ── Hotels ────────────────────────────────────────────────────────────────

    def get_hotels(
        self,
        destination: str,
        checkin: str,
        checkout: str,
        max_price: float = 99999,
    ) -> list[Hotel]:
        if self._amadeus and destination in _DEST_IATA:
            try:
                city_code = _DEST_IATA[destination]

                # Step 1: get hotel IDs for the city
                hotel_list = self._amadeus.reference_data.locations.hotels.by_city.get(
                    cityCode=city_code,
                    radius=5,
                    radiusUnit="KM",
                    hotelSource="ALL",
                )
                hotel_ids = [h["hotelId"] for h in (hotel_list.data or [])[:20]]

                if hotel_ids:
                    # Step 2: fetch pricing for those hotels
                    offers_resp = self._amadeus.shopping.hotel_offers_search.get(
                        hotelIds=hotel_ids,
                        checkInDate=checkin,
                        checkOutDate=checkout,
                        adults=1,
                        currency="USD",
                    )
                    nights = max(
                        1,
                        (_date.fromisoformat(checkout) - _date.fromisoformat(checkin)).days,
                    )
                    hotels: list[Hotel] = []
                    for item in (offers_resp.data or []):
                        info   = item["hotel"]
                        offers = item.get("offers", [])
                        if not offers:
                            continue
                        cheapest      = min(offers, key=lambda o: float(o["price"]["total"]))
                        price_per_night = float(cheapest["price"]["total"]) / nights
                        if price_per_night > max_price:
                            continue
                        raw_stars = info.get("rating", "3")
                        stars = int(raw_stars) if str(raw_stars).isdigit() else 3
                        stars = max(1, min(5, stars))
                        hotels.append(Hotel(
                            id=info["hotelId"],
                            destination=destination,
                            name=info.get("name", "Hotel"),
                            price_per_night=round(price_per_night, 2),
                            stars=stars,
                            style_tags=_hotel_style_tags(price_per_night, stars),
                        ))
                    if hotels:
                        return hotels
            except Exception:
                pass
        hotels_static = STATIC_DATA.get(destination, {}).get("hotels", [])
        return [h for h in hotels_static if h.price_per_night <= max_price]

    # ── Activities ────────────────────────────────────────────────────────────

    def get_activities(self, destination: str) -> list[Activity]:
        if self._amadeus and destination in _DEST_COORDS:
            try:
                lat, lon = _DEST_COORDS[destination]
                resp = self._amadeus.shopping.activities.get(
                    latitude=lat,
                    longitude=lon,
                    radius=20,
                )
                if resp.data:
                    activities: list[Activity] = []
                    for act in resp.data[:10]:
                        price_info = act.get("price", {})
                        price      = float(price_info.get("amount", "0") or "0")
                        categories = act.get("categories", [])
                        activities.append(Activity(
                            id=str(act.get("id", uuid.uuid4())),
                            destination=destination,
                            name=act.get("name", "Activity"),
                            price=price,
                            style_tags=_activity_style_tags(categories),
                        ))
                    if activities:
                        return activities
            except Exception:
                pass
        return list(STATIC_DATA.get(destination, {}).get("activities", []))

    def destinations(self) -> list[str]:
        return list(STATIC_DATA.keys())

    # ── Bookings (local UUID — no external server) ────────────────────────────

    def book_flight(
        self, flight_id: str,
        passenger: PassengerInfo, contact: ContactInfo, payment: PaymentInfo,
    ) -> str:
        return str(uuid.uuid4())

    def book_hotel(
        self, hotel_id: str,
        passenger: PassengerInfo, contact: ContactInfo, payment: PaymentInfo,
    ) -> str:
        return str(uuid.uuid4())

    def book_activity(
        self, activity_id: str,
        passenger: PassengerInfo, contact: ContactInfo, payment: PaymentInfo,
    ) -> str:
        return str(uuid.uuid4())
