"""Embedded static travel data — used as fallback when Amadeus API is unavailable."""

from __future__ import annotations

try:
    from ..models import Activity, Flight, Hotel
except ImportError:
    from models import Activity, Flight, Hotel

# Paris hotels intentionally exceed $1 500/night to exercise the backtracking path.
STATIC_DATA: dict[str, dict] = {
    "Tokyo": {
        "flights": [
            Flight(id="f1", destination="Tokyo", price=650,  airline="ANA",  duration_hours=14, style_tags=["adventure", "culture"]),
            Flight(id="f2", destination="Tokyo", price=820,  airline="JAL",  duration_hours=12, style_tags=["luxury",    "culture"]),
        ],
        "hotels": [
            Hotel(id="h1", destination="Tokyo", name="Shinjuku Inn",     price_per_night=120, stars=3, style_tags=["budget",  "culture"]),
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
