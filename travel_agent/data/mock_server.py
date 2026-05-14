from __future__ import annotations

import uuid

try:
    from ..models import Activity, BookingRequest, Flight, Hotel
except ImportError:
    try:
        from models import Activity, BookingRequest, Flight, Hotel
    except ImportError:
        from travel_agent.models import Activity, BookingRequest, Flight, Hotel

from fastapi import APIRouter, FastAPI, HTTPException, Query

app = FastAPI(title="Travel Mock API")

flights_router    = APIRouter(prefix="/flights",    tags=["flights"])
hotels_router     = APIRouter(prefix="/hotels",     tags=["hotels"])
activities_router = APIRouter(prefix="/activities", tags=["activities"])


# ── Static destination data ───────────────────────────────────────────────────
# All mock data lives here — no JSON files.
# Paris hotels all exceed $1 500/night to exercise the backtracking path.

_DATA: dict[str, dict] = {
    "Tokyo": {
        "flights": [
            Flight(id="f1", destination="Tokyo", price=650,  airline="ANA",  duration_hours=14, style_tags=["adventure", "culture"]),
            Flight(id="f2", destination="Tokyo", price=820,  airline="JAL",  duration_hours=12, style_tags=["luxury",    "culture"]),
        ],
        "hotels": [
            Hotel(id="h1", destination="Tokyo", name="Shinjuku Inn",    price_per_night=120, stars=3, style_tags=["budget",  "culture"]),
            Hotel(id="h2", destination="Tokyo", name="Park Hyatt Tokyo", price_per_night=450, stars=5, style_tags=["luxury"]),
        ],
        "activities": [
            Activity(id="a1", destination="Tokyo", name="Tsukiji Market Tour", price=30,  style_tags=["culture", "food"]),
            Activity(id="a2", destination="Tokyo", name="Mt. Fuji Day Trip",   price=80,  style_tags=["adventure", "nature"]),
            Activity(id="a3", destination="Tokyo", name="Akihabara Walk",      price=0,   style_tags=["culture"]),
        ],
    },
    "Paris": {
        "flights": [
            Flight(id="f3", destination="Paris", price=400, airline="Air France", duration_hours=8, style_tags=["romance", "culture"]),
            Flight(id="f4", destination="Paris", price=550, airline="Lufthansa",  duration_hours=9, style_tags=["luxury",  "romance"]),
        ],
        # All Paris hotels > $1 500/night — forces backtracking in PlanningLoop
        "hotels": [
            Hotel(id="h3", destination="Paris", name="Le Grand Hotel", price_per_night=1800, stars=5, style_tags=["luxury", "romance"]),
            Hotel(id="h4", destination="Paris", name="Hotel Lumiere",  price_per_night=1600, stars=4, style_tags=["romance"]),
        ],
        "activities": [
            Activity(id="a4", destination="Paris", name="Eiffel Tower Visit", price=25, style_tags=["romance", "culture"]),
            Activity(id="a5", destination="Paris", name="Louvre Museum",      price=17, style_tags=["culture", "art"]),
            Activity(id="a6", destination="Paris", name="Seine River Cruise", price=15, style_tags=["romance"]),
        ],
    },
    "Bali": {
        "flights": [
            Flight(id="f5", destination="Bali", price=700, airline="Garuda",    duration_hours=18, style_tags=["adventure", "nature"]),
            Flight(id="f6", destination="Bali", price=850, airline="Singapore", duration_hours=16, style_tags=["luxury",    "nature"]),
        ],
        "hotels": [
            Hotel(id="h5", destination="Bali", name="Ubud Jungle Resort",   price_per_night=90,  stars=3, style_tags=["nature", "adventure"]),
            Hotel(id="h6", destination="Bali", name="Seminyak Beach Villa", price_per_night=200, stars=4, style_tags=["luxury", "nature"]),
        ],
        "activities": [
            Activity(id="a7", destination="Bali", name="Rice Terrace Trek", price=20, style_tags=["adventure", "nature"]),
            Activity(id="a8", destination="Bali", name="Temple Ceremony",   price=10, style_tags=["culture",   "nature"]),
            Activity(id="a9", destination="Bali", name="Surf Lesson",       price=45, style_tags=["adventure"]),
        ],
    },
    "New York": {
        "flights": [
            Flight(id="f7", destination="New York", price=300, airline="Delta",   duration_hours=6, style_tags=["culture", "food"]),
            Flight(id="f8", destination="New York", price=420, airline="JetBlue", duration_hours=6, style_tags=["luxury",  "culture"]),
        ],
        "hotels": [
            Hotel(id="h7", destination="New York", name="Times Square Hotel", price_per_night=180, stars=3, style_tags=["culture", "food"]),
            Hotel(id="h8", destination="New York", name="The Plaza",          price_per_night=600, stars=5, style_tags=["luxury"]),
        ],
        "activities": [
            Activity(id="a10", destination="New York", name="Central Park Walk", price=0,   style_tags=["nature",  "culture"]),
            Activity(id="a11", destination="New York", name="Broadway Show",     price=120, style_tags=["culture", "art"]),
            Activity(id="a12", destination="New York", name="Food Tour",         price=65,  style_tags=["food",    "culture"]),
        ],
    },
}

# ── In-memory booking store ───────────────────────────────────────────────────
# Keyed by booking_id; each entry records the confirmed item and passenger.
_BOOKINGS: dict[str, dict] = {}


# ── Search endpoints (GET) ────────────────────────────────────────────────────

@flights_router.get("/search", response_model=list[Flight])
def search_flights(destination: str, date: str = Query(...)) -> list[Flight]:
    return _DATA.get(destination, {}).get("flights", [])


@hotels_router.get("/search", response_model=list[Hotel])
def search_hotels(
    destination: str,
    checkin: str,
    checkout: str,
    max_price: float = Query(default=99999),
) -> list[Hotel]:
    hotels = _DATA.get(destination, {}).get("hotels", [])
    return [h for h in hotels if h.price_per_night <= max_price]


@activities_router.get("/search", response_model=list[Activity])
def search_activities(destination: str) -> list[Activity]:
    return _DATA.get(destination, {}).get("activities", [])


@app.get("/destinations")
def list_destinations() -> dict[str, list[str]]:
    return {"destinations": list(_DATA.keys())}


# ── Booking endpoints (POST) ──────────────────────────────────────────────────

def _all_items(item_type: str) -> list[str]:
    """Collect all item IDs of the given type from _DATA."""
    key = {"flight": "flights", "hotel": "hotels", "activity": "activities"}[item_type]
    return [item.id for dest in _DATA.values() for item in dest[key]]


def _record_booking(req: BookingRequest) -> dict:
    """Validate item exists, store booking, return confirmation dict."""
    if req.item_id not in _all_items(req.item_type):
        raise HTTPException(status_code=404, detail=f"{req.item_type} '{req.item_id}' not found")
    booking_id = str(uuid.uuid4())
    _BOOKINGS[booking_id] = {
        "booking_id": booking_id,
        "item_type":  req.item_type,
        "item_id":    req.item_id,
        "passenger":  req.passenger.model_dump(),
        "status":     "confirmed",
    }
    return {"booking_id": booking_id, "status": "confirmed", "item_id": req.item_id}


@flights_router.post("/book")
def book_flight(req: BookingRequest) -> dict:
    return _record_booking(req)


@hotels_router.post("/book")
def book_hotel(req: BookingRequest) -> dict:
    return _record_booking(req)


@activities_router.post("/book")
def book_activity(req: BookingRequest) -> dict:
    return _record_booking(req)


@app.get("/bookings/{booking_id}")
def get_booking(booking_id: str) -> dict:
    if booking_id not in _BOOKINGS:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _BOOKINGS[booking_id]


app.include_router(flights_router)
app.include_router(hotels_router)
app.include_router(activities_router)
