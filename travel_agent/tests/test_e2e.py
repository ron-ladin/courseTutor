"""Tasks 11.1 & 11.2: End-to-end integration and wiring verification."""

import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from unittest.mock import patch

from models import TravelRequest, Itinerary, Flight, Hotel, Activity
from agent import AgentState, build_graph, confirm_node
from planner import run_planning_loop


class _InMemoryDataClient:
    """Reads from mock_server._DATA directly — no HTTP server needed."""

    def get_flights(self, destination: str, date: str):
        from mock_server import _DATA
        return list(_DATA.get(destination, {}).get("flights", []))

    def get_hotels(self, destination: str, checkin: str, checkout: str, max_price: float = 99999):
        from mock_server import _DATA
        return [h for h in _DATA.get(destination, {}).get("hotels", []) if h.price_per_night <= max_price]

    def get_activities(self, destination: str):
        from mock_server import _DATA
        return list(_DATA.get(destination, {}).get("activities", []))

    def destinations(self):
        from mock_server import _DATA
        return list(_DATA.keys())


def _fresh_state() -> AgentState:
    return {
        "messages": [],
        "travel_request": {},
        "confirmed_request": None,
        "itineraries": [],
        "selected_itinerary": None,
        "booking": None,
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "onboard",
        "passenger_info": {},
        "contact_info": {},
        "payment_info": {},
    }


_SAMPLE_PASSENGER = {
    "full_name": "Alon Cohen",
    "passport_number": "AB123456",
    "date_of_birth": "1990-01-15",
}
_SAMPLE_CONTACT = {
    "email": "alon@example.com",
    "phone": "+972501234567",
    "address": "123 Main St, Tel Aviv",
}
_SAMPLE_PAYMENT = {
    "card_last4": "4242",
    "cardholder_name": "ALON COHEN",
    "card_expiry": "06/28",
}


# ── Task 11.1: Full end-to-end flow ──────────────────────────────────────────

def test_11_1_full_graph_onboard_to_rank():
    """Task 11.1: Full agent graph from first message through plan/rank using in-memory data."""
    graph = build_graph()

    with patch("agent.DataClient", _InMemoryDataClient):
        state = _fresh_state()

        # First invoke — graph asks for destination
        state = graph.invoke(state)
        assert any(
            "destination" in m["content"].lower()
            for m in state["messages"] if m["role"] == "assistant"
        )

        # Answer each onboarding question
        for answer in ["Tokyo", "2025-06-01", "2025-06-08", "2000", "adventure, culture"]:
            state["messages"].append({"role": "user", "content": answer})
            state = graph.invoke(state)

        # After travel_style, phase is still onboard — awaiting yes/no confirmation
        assert state["phase"] == "onboard"

        # Confirm — triggers onboard → plan → rank in one invoke()
        state["messages"].append({"role": "user", "content": "yes"})
        state = graph.invoke(state)

        assert state["phase"] == "rank", f"Expected 'rank', got '{state['phase']}'"
        assert 1 <= len(state["itineraries"]) <= 3

        for itin in state["itineraries"]:
            assert itin.flight.destination == "Tokyo"
            assert itin.hotel.destination == "Tokyo"
            assert itin.total_cost > 0
            assert 0.0 <= itin.match_score <= 1.0

        # Itineraries ranked highest-first
        scores = [it.match_score for it in state["itineraries"]]
        assert scores == sorted(scores, reverse=True)

        # Reasoning log populated
        assert len(state["reasoning_log"]) > 0


def test_11_1_confirm_node_produces_valid_booking():
    """Task 11.1: confirm_node integration — produces a valid UUID v4 booking."""
    from unittest.mock import MagicMock
    from mock_server import _DATA

    flight = _DATA["Tokyo"]["flights"][0]
    hotel = _DATA["Tokyo"]["hotels"][0]
    itin = Itinerary(
        flight=flight,
        hotel=hotel,
        activities=[],
        total_cost=flight.price + hotel.price_per_night * 7,
        match_score=0.8,
    )

    state = _fresh_state()
    state["selected_itinerary"] = itin
    state["phase"] = "confirm"
    state["passenger_info"] = _SAMPLE_PASSENGER
    state["contact_info"] = _SAMPLE_CONTACT
    state["payment_info"] = _SAMPLE_PAYMENT

    mock_bid = str(uuid.uuid4())
    with patch("agent.DataClient") as MockClient:
        mc = MagicMock()
        MockClient.return_value = mc
        mc.book_flight.return_value = mock_bid
        mc.book_hotel.return_value = str(uuid.uuid4())
        mc.book_activity.return_value = str(uuid.uuid4())
        state = confirm_node(state)

    assert state["phase"] == "done"
    assert state["booking"] is not None
    booking_uuid = uuid.UUID(state["booking"].booking_id)
    assert booking_uuid.version == 4


def test_11_1_no_restart_after_done():
    """Task 11.1: Once phase is 'done', the graph's onboard node re-confirms (state preserved)."""
    with patch("agent.DataClient", _InMemoryDataClient):
        state = _fresh_state()
        # Pre-fill all travel_request fields so onboard auto-confirms
        state["travel_request"] = {
            "destination": "Tokyo",
            "departure_date": "2025-06-01",
            "return_date": "2025-06-08",
            "budget": 2000.0,
            "travel_style": "adventure",
        }
        graph = build_graph()
        state = graph.invoke(state)

        # Should have gone through planning automatically
        assert state["confirmed_request"] is not None
        assert len(state["itineraries"]) >= 1


# ── Task 11.2: Paris backtracking verification ────────────────────────────────

def test_11_2_paris_low_budget_triggers_backtrack():
    """Task 11.2: Paris with budget below hotel prices triggers backtrack + partial fallback."""
    request = TravelRequest(
        destination="Paris",
        departure_date=date(2025, 4, 1),
        return_date=date(2025, 4, 8),
        budget=1500.0,  # all Paris hotels > $1,500/night
        travel_style=["romance", "culture"],
    )
    log: list[str] = []
    itineraries = run_planning_loop(request, _InMemoryDataClient(), log)

    assert len(itineraries) >= 1, "Must produce at least one partial fallback itinerary"
    assert any(itin.is_partial_fallback for itin in itineraries), (
        "Expected is_partial_fallback=True for Paris over-budget scenario"
    )

    backtrack_entries = [e for e in log if "Backtrack" in e or "backtrack" in e]
    assert len(backtrack_entries) >= 1, f"Expected backtrack log entry, got:\n{log}"


def test_11_2_paris_reasoning_log_contains_hotel_search():
    """Task 11.2: Reasoning log shows GET /hotels/search?destination=Paris&max_price=<amount>."""
    request = TravelRequest(
        destination="Paris",
        departure_date=date(2025, 4, 1),
        return_date=date(2025, 4, 8),
        budget=1500.0,
        travel_style=["romance"],
    )
    log: list[str] = []
    run_planning_loop(request, _InMemoryDataClient(), log)

    hotel_search_entries = [
        e for e in log
        if "GET /hotels/search" in e and "destination=Paris" in e and "max_price=" in e
    ]
    assert len(hotel_search_entries) >= 1, (
        f"Expected hotel search entry for Paris in reasoning log. Got:\n{chr(10).join(log)}"
    )

    # max_price is now per-night: (budget - flight) / nights
    from mock_server import _DATA
    cheapest_flight = min(_DATA["Paris"]["flights"], key=lambda f: f.price)
    nights = (date(2025, 4, 8) - date(2025, 4, 1)).days
    expected_max_per_night = (1500.0 - cheapest_flight.price) / nights
    assert any(
        f"max_price={expected_max_per_night:.0f}" in e for e in hotel_search_entries
    ), (
        f"Expected max_price={expected_max_per_night:.0f} in log entries:\n{hotel_search_entries}"
    )


def test_11_2_paris_reasoning_log_shows_fallback_assembly():
    """Task 11.2: Reasoning log includes partial-fallback assembly message."""
    request = TravelRequest(
        destination="Paris",
        departure_date=date(2025, 4, 1),
        return_date=date(2025, 4, 8),
        budget=1500.0,
        travel_style=["romance"],
    )
    log: list[str] = []
    itineraries = run_planning_loop(request, _InMemoryDataClient(), log)

    fallback_entries = [e for e in log if "fallback" in e.lower()]
    assert len(fallback_entries) >= 1, (
        f"Expected 'fallback' entry in reasoning log. Got:\n{chr(10).join(log)}"
    )

    fallback_itin = next((it for it in itineraries if it.is_partial_fallback), None)
    assert fallback_itin is not None
    assert fallback_itin.flight.destination == "Paris"
    assert fallback_itin.hotel.destination == "Paris"
    assert fallback_itin.activities == []


def test_11_2_paris_itinerary_exceeds_budget():
    """Task 11.2: Paris partial fallback itinerary total_cost is above budget (correctly flagged)."""
    budget = 1500.0
    request = TravelRequest(
        destination="Paris",
        departure_date=date(2025, 4, 1),
        return_date=date(2025, 4, 8),
        budget=budget,
        travel_style=["romance"],
    )
    itineraries = run_planning_loop(request, _InMemoryDataClient(), [])

    fallback = next(it for it in itineraries if it.is_partial_fallback)
    # total_cost for fallback = flight + hotel (no activities) — must exceed budget
    assert fallback.total_cost > budget, (
        f"Fallback total ${fallback.total_cost:.2f} should exceed budget ${budget:.2f}"
    )
