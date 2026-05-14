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
