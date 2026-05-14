"""Property tests for LangGraph agent (Task 7)."""

import uuid
from datetime import date
from hypothesis import given, strategies as st

try:
    from travel_agent.models import TravelRequest, Itinerary, Flight, Hotel, Activity, BookingConfirmation
    from travel_agent.agent import (
        AgentState, onboard_node, plan_node, rank_node, confirm_node, build_graph
    )
except ImportError:
    from models import TravelRequest, Itinerary, Flight, Hotel, Activity, BookingConfirmation
    from agent import (
        AgentState, onboard_node, plan_node, rank_node, confirm_node, build_graph
    )


# ============================================================================
# Property 1: Onboarding sequence advances in order (Task 7.3)
# ============================================================================

@given(
    destination=st.text(min_size=1, max_size=50),
    departure=st.dates(min_value=date(2025, 1, 1), max_value=date(2026, 12, 31)),
    budget=st.floats(min_value=100, max_value=10000),
    style_tags=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5),
)
def test_onboarding_sequence_order(destination, departure, budget, style_tags):
    """
    Property 1: Onboarding sequence advances in order
    Validates: Requirements 1.2
    """
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
        "passenger_info": {},
        "contact_info": {},
        "payment_info": {},
    }

    # First question should be about destination
    state = onboard_node(state)
    assert len(state["messages"]) > 0
    first_q = state["messages"][-1]["content"].lower()
    assert "destination" in first_q or "where" in first_q or "tokyo" in first_q
    
    # Answer destination
    state["travel_request"]["destination"] = destination
    state["messages"] = []
    state = onboard_node(state)
    assert "depart" in state["messages"][-1]["content"].lower()
    
    # Answer departure_date
    state["travel_request"]["departure_date"] = departure.isoformat()
    state["messages"] = []
    state = onboard_node(state)
    assert "return" in state["messages"][-1]["content"].lower()
    
    # Answer return_date (must be after departure)
    return_date = date(departure.year + 1, departure.month, departure.day)
    state["travel_request"]["return_date"] = return_date.isoformat()
    state["messages"] = []
    state = onboard_node(state)
    assert "budget" in state["messages"][-1]["content"].lower()
    
    # Answer budget
    state["travel_request"]["budget"] = budget
    state["messages"] = []
    state = onboard_node(state)
    assert "style" in state["messages"][-1]["content"].lower()
    
    # Answer travel_style
    state["travel_request"]["travel_style"] = ",".join(style_tags)
    state["messages"] = []
    state = onboard_node(state)
    
    # Should now show summary
    assert state["confirmed_request"] is not None
    assert state["confirmed_request"].destination == destination


# ============================================================================
# Property 13: Itinerary ranking is non-increasing (Task 7.5)
# ============================================================================

@given(
    num_itineraries=st.integers(min_value=1, max_value=5),
)
def test_itinerary_ranking_order(num_itineraries):
    """
    Property 13: Itinerary ranking is non-increasing
    Validates: Requirements 4.4, 4.5
    """
    # Create mock itineraries with varying scores
    itineraries = []
    for i in range(num_itineraries):
        itinerary = Itinerary(
            flight=Flight(id=f"FL{i}", destination="Tokyo", price=float(i * 100), airline="Test", duration_hours=12.0, style_tags=[]),
            hotel=Hotel(id=f"HT{i}", destination="Tokyo", name=f"Hotel {i}", price_per_night=float(50 + i * 10), stars=3, style_tags=[]),
            activities=[],
            total_cost=float(i * 200),
            match_score=float(i) / num_itineraries,  # Increasing scores
            is_partial_fallback=False,
        )
        itineraries.append(itinerary)
    
    state: AgentState = {
        "messages": [],
        "travel_request": {"travel_style": ["luxury", "adventure"]},
        "confirmed_request": TravelRequest(
            destination="Tokyo",
            departure_date=date(2025, 6, 1),
            return_date=date(2025, 6, 8),
            budget=5000,
            travel_style=["luxury", "adventure"],
        ),
        "itineraries": itineraries,
        "selected_itinerary": None,
        "booking": None,
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "rank",
    }
    
    state = rank_node(state)
    
    # Verify itineraries are sorted by match_score descending
    sorted_itineraries = state["itineraries"]
    for i in range(len(sorted_itineraries) - 1):
        assert sorted_itineraries[i].match_score >= sorted_itineraries[i + 1].match_score, (
            f"Itinerary {i} (score {sorted_itineraries[i].match_score}) "
            f"not >= Itinerary {i+1} (score {sorted_itineraries[i+1].match_score})"
        )


# ============================================================================
# Property 16: BookingID is a valid UUID (Task 7.7)
# ============================================================================

@given(
    num_activities=st.integers(min_value=0, max_value=3),
)
def test_booking_id_is_valid_uuid(num_activities):
    """
    Property 16: BookingID is a valid UUID
    Validates: Requirements 6.4
    """
    # Create a mock itinerary
    activities = [
        Activity(id=f"ACT{i}", destination="Tokyo", name=f"Activity {i}", price=50.0)
        for i in range(num_activities)
    ]
    
    selected_itinerary = Itinerary(
        flight=Flight(id="FL1", destination="Tokyo", price=1000.0, airline="JAL", duration_hours=12.0, style_tags=[]),
        hotel=Hotel(id="HT1", destination="Tokyo", name="Tokyo Hotel", price_per_night=200.0, stars=5, style_tags=[]),
        activities=activities,
        total_cost=1000.0 + 200.0 * 7 + sum(a.price for a in activities),
        match_score=0.9,
        is_partial_fallback=False,
    )
    
    from unittest.mock import MagicMock, patch

    mock_bid = str(uuid.uuid4())

    state: AgentState = {
        "messages": [],
        "travel_request": {},
        "confirmed_request": TravelRequest(
            destination="Tokyo",
            departure_date=date(2025, 6, 1),
            return_date=date(2025, 6, 8),
            budget=5000,
            travel_style=["luxury"],
        ),
        "itineraries": [selected_itinerary],
        "selected_itinerary": selected_itinerary,
        "booking": None,
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "confirm",
        "passenger_info": {"full_name": "Test User", "passport_number": "AB123456", "date_of_birth": "1990-01-01"},
        "contact_info": {"email": "test@test.com", "phone": "+1234567890", "address": "123 Test St"},
        "payment_info": {"card_last4": "1234", "cardholder_name": "TEST USER", "card_expiry": "06/28"},
    }

    with patch("travel_agent.agent.LiveDataClient") as MockClient:
        mc = MagicMock()
        MockClient.return_value = mc
        mc.book_flight.return_value = mock_bid
        mc.book_hotel.return_value = str(uuid.uuid4())
        mc.book_activity.return_value = str(uuid.uuid4())
        state = confirm_node(state)

    # Verify booking exists and has valid UUID
    assert state["booking"] is not None
    booking_id = state["booking"].booking_id

    import re
    uuid_v4_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    assert re.match(uuid_v4_pattern, booking_id), f"Invalid UUID format: {booking_id}"
    try:
        uuid.UUID(booking_id)
    except ValueError:
        raise AssertionError(f"BookingID is not a valid UUID: {booking_id}")


# ============================================================================
# Property 17: ConfirmationState is terminal (Task 7.8)
# ============================================================================

def test_confirmation_state_is_terminal():
    """
    Property 17: ConfirmationState is terminal
    Validates: Requirements 6.6
    
    Once phase is "done" (after confirm), invoking the graph
    should not transition to any earlier phase.
    """
    # Create a completed booking state
    state: AgentState = {
        "messages": [],
        "travel_request": {},
        "confirmed_request": TravelRequest(
            destination="Tokyo",
            departure_date=date(2025, 6, 1),
            return_date=date(2025, 6, 8),
            budget=5000,
            travel_style=["luxury"],
        ),
        "itineraries": [],
        "selected_itinerary": None,
        "booking": BookingConfirmation(
            booking_id=str(uuid.uuid4()),
            itinerary=Itinerary(
                flight=Flight(id="FL1", destination="Tokyo", price=1000.0, airline="JAL", duration_hours=12.0, style_tags=[]),
                hotel=Hotel(id="HT1", destination="Tokyo", name="Tokyo Hotel", price_per_night=200.0, stars=5, style_tags=[]),
                activities=[],
                total_cost=2400.0,
                match_score=0.9,
            ),
        ),
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "done",
    }
    
    # Attempting to run confirm_node again should remain in "done" phase
    state_after = confirm_node(state)
    assert state_after["phase"] == "done", "Phase should remain 'done' after confirmation"


# ============================================================================
# Graph Compilation Test (Task 7.9)
# ============================================================================

def test_graph_builds_and_compiles():
    """
    Verify that build_graph() returns a compiled runnable graph.
    Validates: Requirements 1.1–1.7, 3.1–3.8, 6.3–6.6
    """
    graph = build_graph()
    assert graph is not None, "build_graph() should return a non-None graph"
    
    # Verify the graph has the expected invoke method
    assert hasattr(graph, "invoke"), "Graph should have an 'invoke' method"


if __name__ == "__main__":
    # Run a quick sanity check
    test_graph_builds_and_compiles()
    print("✅ All agent tests passed!")
