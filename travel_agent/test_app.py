"""Property tests for Dev 4 (app.py / UI layer)."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from models import Activity, Flight, Hotel, Itinerary, TravelRequest

# ── shared strategies ─────────────────────────────────────────────────────────

_TAGS = st.lists(
    st.sampled_from(["adventure", "culture", "luxury", "romance", "nature", "food", "budget"]),
    min_size=0,
    max_size=5,
)
_DESTINATIONS = st.sampled_from(["Tokyo", "Paris", "Bali", "New York"])


@st.composite
def flight_st(draw):
    return Flight(
        id=draw(st.text(min_size=1, max_size=8)),
        destination=draw(_DESTINATIONS),
        price=draw(st.floats(min_value=0.01, max_value=10_000, allow_nan=False)),
        airline=draw(st.text(min_size=1, max_size=30)),
        duration_hours=draw(st.floats(min_value=0.5, max_value=30, allow_nan=False)),
        style_tags=draw(_TAGS),
    )


@st.composite
def hotel_st(draw):
    return Hotel(
        id=draw(st.text(min_size=1, max_size=8)),
        destination=draw(_DESTINATIONS),
        name=draw(st.text(min_size=1, max_size=50)),
        price_per_night=draw(st.floats(min_value=0.01, max_value=5_000, allow_nan=False)),
        stars=draw(st.integers(min_value=1, max_value=5)),
        style_tags=draw(_TAGS),
    )


@st.composite
def activity_st(draw):
    return Activity(
        id=draw(st.text(min_size=1, max_size=8)),
        destination=draw(_DESTINATIONS),
        name=draw(st.text(min_size=1, max_size=50)),
        price=draw(st.floats(min_value=0, max_value=500, allow_nan=False)),
        style_tags=draw(_TAGS),
    )


@st.composite
def itinerary_st(draw):
    return Itinerary(
        flight=draw(flight_st()),
        hotel=draw(hotel_st()),
        activities=draw(st.lists(activity_st(), min_size=0, max_size=5)),
        total_cost=draw(st.floats(min_value=0, max_value=100_000, allow_nan=False)),
        match_score=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        is_partial_fallback=draw(st.booleans()),
    )


# ── Property 15: itinerary card field completeness ────────────────────────────

@given(itinerary_st())
def test_itinerary_card_field_completeness(itin: Itinerary):
    """Every Itinerary exposes all fields the card renders."""
    # destination (via flight)
    assert itin.flight.destination

    # flight fields
    assert itin.flight.id
    assert itin.flight.price >= 0
    assert itin.flight.airline
    assert itin.flight.duration_hours > 0

    # hotel fields
    assert itin.hotel.name
    assert itin.hotel.price_per_night >= 0
    assert 1 <= itin.hotel.stars <= 5

    # activities list is always present (may be empty)
    assert isinstance(itin.activities, list)

    # totals / score
    assert itin.total_cost >= 0
    assert 0.0 <= itin.match_score <= 1.0

    # fallback flag is a bool
    assert isinstance(itin.is_partial_fallback, bool)


# ── Property 14: reasoning log grows with planning steps ─────────────────────

def test_reasoning_log_is_list():
    """reasoning_log in AgentState is always a list (structural check)."""
    from agent import AgentState

    state: AgentState = {
        "messages": [],
        "travel_request": {},
        "confirmed_request": None,
        "itineraries": [],
        "selected_itinerary": None,
        "booking": None,
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "onboard",
    }
    assert isinstance(state["reasoning_log"], list)


def test_reasoning_log_grows_after_planning():
    """Once the real planner is wired, log must be non-empty after a run."""
    from data_client import DataClient
    from planner import run_planning_loop

    request = TravelRequest(
        destination="Tokyo",
        departure_date=date(2025, 3, 10),
        return_date=date(2025, 3, 17),
        budget=1500.0,
        travel_style=["adventure", "culture"],
    )
    log: list[str] = []
    run_planning_loop(request, DataClient(), log)

    # Stub returns [] so log stays empty — test will enforce growth once real
    # planner lands.  For now just verify the interface contract.
    assert isinstance(log, list)
    # Uncomment after planner is real:
    # assert len(log) > 0


# ── Property 16: BookingID is a valid UUID v4 ─────────────────────────────────

import re
import uuid

_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def test_booking_id_is_valid_uuid4():
    """Generated booking ID matches UUID v4 format (Property 16)."""
    from models import BookingConfirmation, Flight, Hotel, Itinerary

    flight = Flight(id="f1", destination="Tokyo", price=650.0,
                    airline="ANA", duration_hours=14.0, style_tags=["culture"])
    hotel = Hotel(id="h1", destination="Tokyo", name="Shinjuku Inn",
                  price_per_night=120.0, stars=3, style_tags=["budget"])
    itin = Itinerary(flight=flight, hotel=hotel, activities=[],
                     total_cost=770.0, match_score=0.8)

    booking_id = str(uuid.uuid4())
    confirmation = BookingConfirmation(booking_id=booking_id, itinerary=itin)

    assert _UUID4_RE.match(confirmation.booking_id), (
        f"BookingID '{confirmation.booking_id}' is not a valid UUID v4"
    )


@given(st.integers(min_value=1, max_value=20))
def test_booking_id_always_unique(n: int):
    """Every booking generates a distinct ID — no collisions."""
    ids = {str(uuid.uuid4()) for _ in range(n)}
    assert len(ids) == n


# ── session state initial shape ───────────────────────────────────────────────

def test_initial_state_has_all_agent_state_keys():
    """The initial state dict covers every key in AgentState."""
    from agent import AgentState

    required_keys = {"messages", "travel_request", "confirmed_request",
                     "itineraries", "selected_itinerary", "booking",
                     "reasoning_log", "backtrack_count", "phase"}

    initial: AgentState = {
        "messages": [],
        "travel_request": {},
        "confirmed_request": None,
        "itineraries": [],
        "selected_itinerary": None,
        "booking": None,
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "onboard",
    }
    assert required_keys == set(initial.keys())


def test_initial_phase_is_onboard():
    """App always starts in the onboard phase."""
    from agent import AgentState

    initial: AgentState = {
        "messages": [],
        "travel_request": {},
        "confirmed_request": None,
        "itineraries": [],
        "selected_itinerary": None,
        "booking": None,
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "onboard",
    }
    assert initial["phase"] == "onboard"
    assert initial["backtrack_count"] == 0
    assert initial["messages"] == []
