#!/usr/bin/env python3
"""Simple test runner for Travel Planning Agent - no pytest required."""

import sys
import traceback
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_test(test_name, test_func):
    """Run a single test and report results."""
    try:
        test_func()
        print(f"PASS {test_name}")
        return True
    except Exception as e:
        print(f"FAIL {test_name}")
        print(f"   Error: {e}")
        traceback.print_exc()
        return False


def test_imports():
    """Test that all modules can be imported."""
    from travel_agent import models
    from travel_agent.data import client as data_client
    from travel_agent import planner
    from travel_agent import agent
    from travel_agent.data import mock_server
    assert models is not None
    assert data_client is not None
    assert planner is not None
    assert agent is not None
    assert mock_server is not None


def test_models():
    """Test Pydantic models."""
    from travel_agent.models import (
        TravelRequest, Flight, Hotel, Activity, Itinerary, BookingConfirmation
    )
    from datetime import date
    
    # Test TravelRequest
    req = TravelRequest(
        destination="Tokyo",
        departure_date=date(2027, 6, 1),
        return_date=date(2027, 6, 8),
        budget=5000,
        travel_style=["luxury"],
    )
    assert req.destination == "Tokyo"
    assert req.budget == 5000
    
    # Test validation
    try:
        bad_req = TravelRequest(
            destination="Tokyo",
            departure_date=date(2027, 6, 1),
            return_date=date(2027, 6, 1),  # Same as departure
            budget=5000,
            travel_style=["luxury"],
        )
        raise AssertionError("Should have raised validation error for same dates")
    except ValueError:
        pass  # Expected
    
    # Test negative budget validation
    try:
        bad_req = TravelRequest(
            destination="Tokyo",
            departure_date=date(2027, 6, 1),
            return_date=date(2027, 6, 8),
            budget=-100,  # Negative
            travel_style=["luxury"],
        )
        raise AssertionError("Should have raised validation error for negative budget")
    except ValueError:
        pass  # Expected


def test_agent_state():
    """Test AgentState TypedDict."""
    from travel_agent.agent import AgentState
    
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
    
    assert state["phase"] == "onboard"
    assert state["backtrack_count"] == 0


def test_agent_onboard_node():
    """Test onboard node."""
    from travel_agent.agent import onboard_node, AgentState
    
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
    
    result = onboard_node(state)
    
    # Should have asked first question
    assert len(result["messages"]) > 0
    assert result["phase"] == "onboard"
    assert "destination" in result["messages"][-1]["content"].lower()


def test_agent_graph_builds():
    """Test that agent graph builds."""
    from travel_agent.agent import build_graph
    
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_planner_functions():
    """Test planner functions."""
    from travel_agent.planner import compute_raw_score, normalize_scores
    
    # Test compute_raw_score
    score = compute_raw_score(["luxury", "fast", "modern"], ["luxury", "adventure"])
    assert score == 1.0  # Only "luxury" matches
    
    # Test normalize_scores
    scores = [1.0, 2.0, 3.0, 4.0, 5.0]
    normalized = normalize_scores(scores)
    assert normalized[0] == 0.0
    assert normalized[-1] == 1.0
    assert len(normalized) == 5
    
    # Test edge case: all equal scores
    equal_scores = [2.0, 2.0, 2.0]
    normalized_equal = normalize_scores(equal_scores)
    assert all(s == 1.0 for s in normalized_equal)


def test_data_client_instantiation():
    """Test DataClient can be instantiated."""
    from travel_agent.data.client import LiveDataClient as DataClient

    client = DataClient()
    assert client is not None
    assert hasattr(client, "get_flights")
    assert hasattr(client, "get_hotels")
    assert hasattr(client, "get_activities")


def test_booking_confirmation_with_uuid():
    """Test BookingConfirmation generates valid UUIDs."""
    from travel_agent.models import BookingConfirmation, Itinerary, Flight, Hotel
    import uuid
    
    itinerary = Itinerary(
        flight=Flight(id="FL1", destination="Tokyo", price=1000.0, airline="JAL", duration_hours=12.0),
        hotel=Hotel(id="HT1", destination="Tokyo", name="Hotel", price_per_night=100.0, stars=5),
    )
    
    booking_id = str(uuid.uuid4())
    confirmation = BookingConfirmation(booking_id=booking_id, itinerary=itinerary)
    
    # Verify it's a valid UUID
    uuid.UUID(confirmation.booking_id)
    assert confirmation.itinerary == itinerary


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("RUNNING UNIT TESTS FOR TRAVEL PLANNING AGENT")
    print("="*70 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("Pydantic Models", test_models),
        ("AgentState TypedDict", test_agent_state),
        ("Onboard Node", test_agent_onboard_node),
        ("Agent Graph", test_agent_graph_builds),
        ("Planner Functions", test_planner_functions),
        ("DataClient Instantiation", test_data_client_instantiation),
        ("BookingConfirmation UUID", test_booking_confirmation_with_uuid),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*70)
    if failed == 0:
        print(f"ALL {passed} TESTS PASSED!")
    else:
        print(f"{failed} FAILED, {passed} PASSED")
    print("="*70 + "\n")
    
    sys.exit(0 if failed == 0 else 1)

