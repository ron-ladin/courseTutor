"""
Comprehensive test suite — sanity, negative, boundary, and edge cases.

Run from the repo root:
    cd travel_agent && pytest ../tests/test_system.py -v

The FastAPI TestClient runs the mock server in-process, so no uvicorn needed.
The MockDataClient replaces real HTTP calls in planner/agent unit tests.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from travel_agent.data.mock_server import app, _BOOKINGS
from travel_agent.models import (
    Activity, BookingConfirmation, BookingRequest, ContactInfo, Flight,
    Hotel, Itinerary, PassengerInfo, PaymentInfo, TravelRequest,
)
from travel_agent.planner import (
    aggregate_itinerary_tags, compute_raw_score, normalize_scores,
    run_planning_loop,
)

# ── Shared fixtures ───────────────────────────────────────────────────────────

client = TestClient(app)

PASSENGER = PassengerInfo(full_name="Ada Lovelace", passport_number="P123456", date_of_birth=date(1990, 1, 1))
CONTACT   = ContactInfo(email="ada@example.com", phone="+1-555-0100", address="1 Main St, London")
PAYMENT   = PaymentInfo(card_last4="4242", cardholder_name="Ada Lovelace", card_expiry="12/30")


def _booking_payload(item_id: str, item_type: str) -> dict[str, Any]:
    return BookingRequest(
        item_id=item_id, item_type=item_type,
        passenger=PASSENGER, contact=CONTACT, payment=PAYMENT,
    ).model_dump(mode="json")


class MockDataClient:
    """In-process substitute that bypasses HTTP for planner unit tests."""
    def __init__(self, flights: list, hotels: list, activities: list):
        self._flights    = flights
        self._hotels     = hotels
        self._activities = activities

    def get_flights(self, destination: str, date: str) -> list:
        return list(self._flights)

    def get_hotels(self, destination: str, checkin: str, checkout: str, max_price: float = 99999) -> list:
        return [h for h in self._hotels if h.price_per_night <= max_price]

    def get_activities(self, destination: str) -> list:
        return list(self._activities)


def _make_request(budget: float = 2000.0, nights: int = 5, style: list | None = None) -> TravelRequest:
    dep = date(2026, 8, 1)
    return TravelRequest(
        destination="Tokyo",
        departure_date=dep,
        return_date=dep + timedelta(days=nights),
        budget=budget,
        travel_style=style or ["culture", "adventure"],
    )


def _make_flight(fid: str, price: float, tags: list | None = None) -> Flight:
    return Flight(id=fid, destination="Tokyo", price=price, airline="TestAir", duration_hours=10, style_tags=tags or [])


def _make_hotel(hid: str, ppn: float, tags: list | None = None) -> Hotel:
    return Hotel(id=hid, destination="Tokyo", name=f"Hotel-{hid}", price_per_night=ppn, stars=3, style_tags=tags or [])


def _make_activity(aid: str, price: float, tags: list | None = None) -> Activity:
    return Activity(id=aid, destination="Tokyo", name=f"Act-{aid}", price=price, style_tags=tags or [])


# =============================================================================
# 1. MODEL TESTS
# =============================================================================

class TestTravelRequest:

    # Sanity
    def test_valid_request_created(self):
        r = TravelRequest(destination="Tokyo", departure_date=date(2026,8,1), return_date=date(2026,8,10), budget=3000.0)
        assert r.destination == "Tokyo"
        assert r.budget == 3000.0

    def test_travel_style_defaults_to_empty(self):
        r = TravelRequest(destination="Tokyo", departure_date=date(2026,8,1), return_date=date(2026,8,10), budget=100)
        assert r.travel_style == []

    # Negative
    def test_budget_zero_rejected(self):
        with pytest.raises(ValidationError, match="budget must be positive"):
            TravelRequest(destination="X", departure_date=date(2026,8,1), return_date=date(2026,8,10), budget=0)

    def test_budget_negative_rejected(self):
        with pytest.raises(ValidationError, match="budget must be positive"):
            TravelRequest(destination="X", departure_date=date(2026,8,1), return_date=date(2026,8,10), budget=-500)

    def test_return_before_departure_rejected(self):
        with pytest.raises(ValidationError, match="return_date must be after departure_date"):
            TravelRequest(destination="X", departure_date=date(2026,8,10), return_date=date(2026,8,1), budget=1000)

    def test_same_day_departure_return_rejected(self):
        with pytest.raises(ValidationError, match="return_date must be after departure_date"):
            TravelRequest(destination="X", departure_date=date(2026,8,1), return_date=date(2026,8,1), budget=1000)

    # Boundary
    def test_budget_one_cent_accepted(self):
        r = TravelRequest(destination="X", departure_date=date(2026,8,1), return_date=date(2026,8,2), budget=0.01)
        assert r.budget == 0.01

    def test_single_night_trip_accepted(self):
        r = TravelRequest(destination="X", departure_date=date(2026,8,1), return_date=date(2026,8,2), budget=500)
        assert (r.return_date - r.departure_date).days == 1


class TestPassengerInfo:

    # Sanity
    def test_valid_passenger(self):
        p = PassengerInfo(full_name="Ada", passport_number="X1", date_of_birth=date(1990,1,1))
        assert p.full_name == "Ada"


class TestPaymentInfo:

    # Sanity
    def test_valid_payment(self):
        p = PaymentInfo(card_last4="1234", cardholder_name="Ada", card_expiry="06/28")
        assert p.card_last4 == "1234"

    # Negative — card_last4
    def test_card_letters_rejected(self):
        with pytest.raises(ValidationError, match="exactly 4 digits"):
            PaymentInfo(card_last4="ABCD", cardholder_name="Ada", card_expiry="06/28")

    def test_card_too_short_rejected(self):
        with pytest.raises(ValidationError, match="exactly 4 digits"):
            PaymentInfo(card_last4="123", cardholder_name="Ada", card_expiry="06/28")

    def test_card_too_long_rejected(self):
        with pytest.raises(ValidationError, match="exactly 4 digits"):
            PaymentInfo(card_last4="12345", cardholder_name="Ada", card_expiry="06/28")

    # Negative — card_expiry
    def test_expiry_month_13_rejected(self):
        with pytest.raises(ValidationError, match="MM/YY"):
            PaymentInfo(card_last4="1234", cardholder_name="Ada", card_expiry="13/25")

    def test_expiry_month_00_rejected(self):
        with pytest.raises(ValidationError, match="MM/YY"):
            PaymentInfo(card_last4="1234", cardholder_name="Ada", card_expiry="00/25")

    def test_expiry_no_slash_rejected(self):
        with pytest.raises(ValidationError, match="MM/YY"):
            PaymentInfo(card_last4="1234", cardholder_name="Ada", card_expiry="1225")

    # Boundary
    def test_card_all_zeros_accepted(self):
        p = PaymentInfo(card_last4="0000", cardholder_name="Ada", card_expiry="01/25")
        assert p.card_last4 == "0000"

    def test_expiry_january_accepted(self):
        p = PaymentInfo(card_last4="1234", cardholder_name="Ada", card_expiry="01/25")
        assert p.card_expiry == "01/25"

    def test_expiry_december_accepted(self):
        p = PaymentInfo(card_last4="1234", cardholder_name="Ada", card_expiry="12/99")
        assert p.card_expiry == "12/99"


# =============================================================================
# 2. MOCK SERVER TESTS
# =============================================================================

class TestServerSearch:

    # Sanity
    def test_flights_tokyo_returns_two(self):
        r = client.get("/flights/search", params={"destination": "Tokyo", "date": "2026-08-01"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 2
        assert all(f["price"] > 0 for f in data)
        assert all(len(f["style_tags"]) > 0 for f in data)

    def test_hotels_tokyo_returns_results(self):
        r = client.get("/hotels/search", params={"destination": "Tokyo", "checkin": "2026-08-01", "checkout": "2026-08-10", "max_price": 99999})
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_activities_tokyo_returns_three(self):
        r = client.get("/activities/search", params={"destination": "Tokyo"})
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_destinations_include_required_demo_and_city_options(self):
        r = client.get("/destinations")
        assert r.status_code == 200
        dests = r.json()["destinations"]
        assert {"Tokyo", "Paris", "Bali", "New York"}.issubset(set(dests))
        assert {"Kyoto", "Nice", "Rome", "Athens", "Bangkok", "Barcelona", "London", "Mexico City", "Tel Aviv"}.issubset(set(dests))
        assert not {"Japan", "France", "Italy", "Greece", "Thailand", "Spain", "United Kingdom", "Mexico", "Israel"}.intersection(set(dests))

    # Negative
    def test_unknown_destination_returns_empty(self):
        r = client.get("/flights/search", params={"destination": "Atlantis", "date": "2026-08-01"})
        assert r.status_code == 200
        assert r.json() == []

    # Boundary — Paris hotel filter
    def test_paris_hotels_max_500_empty(self):
        """All Paris hotels cost > $1500; max_price=500 must return empty."""
        r = client.get("/hotels/search", params={"destination": "Paris", "checkin": "2026-08-01", "checkout": "2026-08-10", "max_price": 500})
        assert r.status_code == 200
        assert r.json() == []

    def test_paris_hotels_max_99999_returns_all(self):
        r = client.get("/hotels/search", params={"destination": "Paris", "checkin": "2026-08-01", "checkout": "2026-08-10"})
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_hotel_filter_returns_only_within_price(self):
        """Only hotels at or below max_price should be returned."""
        r = client.get("/hotels/search", params={"destination": "Tokyo", "checkin": "2026-08-01", "checkout": "2026-08-10", "max_price": 200})
        data = r.json()
        assert all(h["price_per_night"] <= 200 for h in data)


class TestServerBooking:

    def setup_method(self):
        _BOOKINGS.clear()

    # Sanity
    def test_book_flight_returns_booking_id(self):
        r = client.post("/flights/book", json=_booking_payload("f1", "flight"))
        assert r.status_code == 200
        body = r.json()
        assert "booking_id" in body
        assert body["status"] == "confirmed"
        assert len(body["booking_id"]) == 36  # UUID format

    def test_book_hotel_returns_booking_id(self):
        r = client.post("/hotels/book", json=_booking_payload("h1", "hotel"))
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_book_activity_returns_booking_id(self):
        r = client.post("/activities/book", json=_booking_payload("a1", "activity"))
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_booking_stored_and_retrievable(self):
        r = client.post("/flights/book", json=_booking_payload("f1", "flight"))
        bid = r.json()["booking_id"]
        r2 = client.get(f"/bookings/{bid}")
        assert r2.status_code == 200
        assert r2.json()["booking_id"] == bid

    def test_each_booking_gets_unique_id(self):
        r1 = client.post("/flights/book", json=_booking_payload("f1", "flight"))
        r2 = client.post("/flights/book", json=_booking_payload("f1", "flight"))
        assert r1.json()["booking_id"] != r2.json()["booking_id"]

    # Negative
    def test_book_unknown_flight_returns_404(self):
        r = client.post("/flights/book", json=_booking_payload("f999", "flight"))
        assert r.status_code == 404

    def test_book_unknown_hotel_returns_404(self):
        r = client.post("/hotels/book", json=_booking_payload("h999", "hotel"))
        assert r.status_code == 404

    def test_get_nonexistent_booking_returns_404(self):
        r = client.get("/bookings/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    # Edge
    def test_all_components_booked_separately(self):
        """Flight, hotel, activity each produce their own distinct booking IDs."""
        rf = client.post("/flights/book",    json=_booking_payload("f1", "flight")).json()["booking_id"]
        rh = client.post("/hotels/book",     json=_booking_payload("h1", "hotel")).json()["booking_id"]
        ra = client.post("/activities/book", json=_booking_payload("a1", "activity")).json()["booking_id"]
        assert len({rf, rh, ra}) == 3


# =============================================================================
# 3. PLANNER TESTS
# =============================================================================

class TestComputeRawScore:

    # Sanity
    def test_two_overlapping_tags(self):
        assert compute_raw_score(["culture", "adventure", "food"], ["culture", "adventure"]) == 2.0

    def test_one_overlapping_tag(self):
        assert compute_raw_score(["culture", "food"], ["luxury", "culture"]) == 1.0

    # Negative
    def test_no_overlap_returns_zero(self):
        assert compute_raw_score(["luxury"], ["adventure", "nature"]) == 0.0

    def test_empty_user_style_returns_zero(self):
        assert compute_raw_score(["culture", "luxury"], []) == 0.0

    def test_empty_item_tags_returns_zero(self):
        assert compute_raw_score([], ["culture"]) == 0.0

    # Boundary
    def test_identical_tag_lists(self):
        tags = ["culture", "adventure", "luxury"]
        assert compute_raw_score(tags, tags) == 3.0

    # Edge — duplicates in item_tags should not inflate the score (uses set intersection)
    def test_duplicate_item_tags_not_double_counted(self):
        assert compute_raw_score(["culture", "culture"], ["culture"]) == 1.0


class TestNormalizeScores:

    # Sanity
    def test_distinct_scores_max_is_one_min_is_zero(self):
        result = normalize_scores([1.0, 2.0, 3.0])
        assert result[2] == pytest.approx(1.0)
        assert result[0] == pytest.approx(0.0)

    def test_two_values(self):
        result = normalize_scores([0.0, 4.0])
        assert result == pytest.approx([0.0, 1.0])

    # Boundary
    def test_single_score_returns_one(self):
        assert normalize_scores([7.5]) == [1.0]

    def test_empty_list_returns_empty(self):
        assert normalize_scores([]) == []

    # Edge
    def test_all_equal_scores_return_ones(self):
        """When all scores are the same the list must not collapse to zeros."""
        assert normalize_scores([5.0, 5.0, 5.0]) == [1.0, 1.0, 1.0]

    def test_all_zero_scores_return_ones(self):
        assert normalize_scores([0.0, 0.0]) == [1.0, 1.0]

    def test_negative_scores_handled(self):
        result = normalize_scores([-2.0, 0.0, 2.0])
        assert result[0] == pytest.approx(0.0)
        assert result[2] == pytest.approx(1.0)


class TestAggregateItineraryTags:

    def test_collects_all_tags(self):
        itin = Itinerary(
            flight=_make_flight("f1", 500, ["adventure"]),
            hotel=_make_hotel("h1", 100, ["luxury"]),
            activities=[_make_activity("a1", 20, ["culture"]), _make_activity("a2", 10, ["food"])],
        )
        tags = aggregate_itinerary_tags(itin)
        assert set(tags) == {"adventure", "luxury", "culture", "food"}

    def test_no_activity_tags(self):
        itin = Itinerary(
            flight=_make_flight("f1", 500, ["romance"]),
            hotel=_make_hotel("h1", 100, ["luxury"]),
            activities=[],
        )
        assert set(aggregate_itinerary_tags(itin)) == {"romance", "luxury"}


class TestRunPlanningLoop:

    # Sanity — normal Tokyo trip
    def test_returns_itinerary_for_valid_request(self):
        mock = MockDataClient(
            flights=[_make_flight("f1", 300, ["culture"])],
            hotels=[_make_hotel("h1", 100, ["culture"])],
            activities=[_make_activity("a1", 20, ["culture"])],
        )
        log: list[str] = []
        result = run_planning_loop(_make_request(budget=2000, nights=5), mock, log)
        assert len(result) == 1
        assert result[0].flight.id == "f1"
        assert result[0].hotel.id == "h1"
        assert not result[0].is_partial_fallback
        assert len(log) > 0

    def test_cheapest_flight_selected_first(self):
        """The loop must sort by price ascending; the cheapest must be in the first itinerary."""
        mock = MockDataClient(
            flights=[_make_flight("expensive", 800), _make_flight("cheap", 200)],
            hotels=[_make_hotel("h1", 50)],
            activities=[],
        )
        result = run_planning_loop(_make_request(budget=2000, nights=3), mock, [])
        assert result[0].flight.id == "cheap"

    def test_hotel_with_best_score_selected(self):
        mock = MockDataClient(
            flights=[_make_flight("f1", 300)],
            hotels=[
                _make_hotel("low_score",  80, ["luxury"]),
                _make_hotel("high_score", 90, ["culture", "adventure"]),
            ],
            activities=[],
        )
        result = run_planning_loop(_make_request(budget=2000, nights=5, style=["culture", "adventure"]), mock, [])
        assert result[0].hotel.id == "high_score"

    def test_activities_within_remaining_budget(self):
        mock = MockDataClient(
            flights=[_make_flight("f1", 300)],
            hotels=[_make_hotel("h1", 100)],
            activities=[
                _make_activity("cheap",     10),
                _make_activity("expensive", 10000),
            ],
        )
        result = run_planning_loop(_make_request(budget=1000, nights=5), mock, [])
        for a in result[0].activities:
            assert a.id != "expensive"

    def test_returns_at_most_three_itineraries(self):
        flights = [_make_flight(f"f{i}", 100 + i * 50) for i in range(10)]
        mock = MockDataClient(flights=flights, hotels=[_make_hotel("h1", 50)], activities=[])
        result = run_planning_loop(_make_request(budget=5000, nights=2), mock, [])
        assert 1 <= len(result) <= 3

    # Negative
    def test_no_flights_returns_empty(self):
        mock = MockDataClient(flights=[], hotels=[_make_hotel("h1", 100)], activities=[])
        result = run_planning_loop(_make_request(), mock, [])
        assert result == []

    def test_all_flights_exceed_budget_returns_empty(self):
        mock = MockDataClient(
            flights=[_make_flight("f1", 5000), _make_flight("f2", 6000)],
            hotels=[_make_hotel("h1", 100)],
            activities=[],
        )
        result = run_planning_loop(_make_request(budget=100, nights=5), mock, [])
        assert result == []

    # Boundary
    def test_budget_exactly_flight_plus_hotel_zero_activities(self):
        """Budget = flight + hotel*nights exactly → activities budget is 0."""
        nights = 5
        flight_price = 300.0
        hotel_ppn = (2000.0 - flight_price) / nights   # = 340/night
        mock = MockDataClient(
            flights=[_make_flight("f1", flight_price)],
            hotels=[_make_hotel("h1", hotel_ppn)],
            activities=[_make_activity("a1", 1.0)],  # any price > 0 should be skipped
        )
        result = run_planning_loop(_make_request(budget=2000.0, nights=nights), mock, [])
        assert len(result) == 1
        assert result[0].activities == []

    # Edge — backtracking (Paris-style scenario)
    def test_backtrack_triggered_once_on_no_hotels(self):
        """
        Two flights. First flight leaves no hotel budget → backtrack.
        Second flight is cheaper → hotel fits → no fallback.
        """
        mock = MockDataClient(
            flights=[
                _make_flight("expensive", 1900),  # remaining $100 over 5 nights = $20/night, hotel costs $50 → no match
                _make_flight("cheap",     300),   # remaining $1700 → hotel fits
            ],
            hotels=[_make_hotel("h1", 50)],
            activities=[],
        )
        log: list[str] = []
        result = run_planning_loop(_make_request(budget=2000, nights=5), mock, log)
        assert len(result) >= 1
        assert not result[0].is_partial_fallback
        assert any("Backtracking" in e for e in log)

    def test_partial_fallback_when_all_flights_leave_no_hotel_budget(self):
        """Both flights leave no affordable hotel → partial fallback assembled."""
        mock = MockDataClient(
            flights=[_make_flight("f1", 1990), _make_flight("f2", 1980)],
            hotels=[_make_hotel("h1", 500)],  # never fits after flight
            activities=[],
        )
        log: list[str] = []
        result = run_planning_loop(_make_request(budget=2000, nights=5), mock, log)
        assert len(result) == 1
        assert result[0].is_partial_fallback

    def test_empty_style_tags_all_scores_equal(self):
        """With no travel style, all match scores are 0 → normalize to [1.0, 1.0]."""
        mock = MockDataClient(
            flights=[_make_flight("f1", 200), _make_flight("f2", 250)],
            hotels=[_make_hotel("h1", 50, ["luxury"]), _make_hotel("h2", 60, ["adventure"])],
            activities=[],
        )
        result = run_planning_loop(_make_request(budget=5000, nights=3, style=[]), mock, [])
        assert len(result) >= 1  # produced some output even with no style

    def test_reasoning_log_populated(self):
        mock = MockDataClient(
            flights=[_make_flight("f1", 300)],
            hotels=[_make_hotel("h1", 100)],
            activities=[_make_activity("a1", 20)],
        )
        log: list[str] = []
        run_planning_loop(_make_request(), mock, log)
        assert len(log) > 0
        # The exact GET URL should appear in the log for transparency (Req 4)
        assert any("GET /hotels/search" in entry for entry in log)

    def test_all_activities_exceed_budget_none_selected(self):
        mock = MockDataClient(
            flights=[_make_flight("f1", 300)],
            hotels=[_make_hotel("h1", 330)],  # 330 * 5 = 1650, remaining = 50
            activities=[
                _make_activity("a1", 100),
                _make_activity("a2", 200),
            ],
        )
        result = run_planning_loop(_make_request(budget=2000, nights=5), mock, [])
        assert len(result) == 1
        assert result[0].activities == []


# =============================================================================
# 4. INTEGRATION — full booking via TestClient
# =============================================================================

class TestFullBookingFlow:

    def setup_method(self):
        _BOOKINGS.clear()

    def test_search_then_book_flight(self):
        flights = client.get("/flights/search", params={"destination": "Tokyo", "date": "2026-08-01"}).json()
        fid = flights[0]["id"]
        r = client.post("/flights/book", json=_booking_payload(fid, "flight"))
        assert r.status_code == 200
        bid = r.json()["booking_id"]

        r2 = client.get(f"/bookings/{bid}")
        assert r2.json()["item_id"] == fid

    def test_full_three_component_booking(self):
        """Book flight + hotel + activity for Tokyo; all IDs must be distinct."""
        f_bid = client.post("/flights/book",    json=_booking_payload("f1", "flight")).json()["booking_id"]
        h_bid = client.post("/hotels/book",     json=_booking_payload("h1", "hotel")).json()["booking_id"]
        a_bid = client.post("/activities/book", json=_booking_payload("a1", "activity")).json()["booking_id"]
        assert len({f_bid, h_bid, a_bid}) == 3
        assert len(_BOOKINGS) == 3

    def test_paris_backtrack_scenario(self):
        """
        Paris budget $1 500: cheapest flight is $400 → remaining $1100 over 5 nights = $220/night.
        All Paris hotels cost > $1 500/night → no hotel fits → backtrack triggered.
        """
        paris_request = TravelRequest(
            destination="Paris",
            departure_date=date(2026, 9, 1),
            return_date=date(2026, 9, 6),
            budget=1500.0,
            travel_style=["romance"],
        )
        from travel_agent.data.client import LiveDataClient as DataClient

        # We can't call DataClient directly without a running server, so use TestClient
        # instead by hitting the server endpoints manually through a test-only DataClient wrapper.
        flights = client.get("/flights/search", params={"destination": "Paris", "date": "2026-09-01"}).json()
        cheapest_flight = min(flights, key=lambda f: f["price"])
        remaining = 1500 - cheapest_flight["price"]
        nights = 5
        max_hotel = remaining / nights

        hotels = client.get("/hotels/search", params={
            "destination": "Paris", "checkin": "2026-09-01",
            "checkout": "2026-09-06", "max_price": max_hotel,
        }).json()
        # All Paris hotels must be over this ceiling — this is the backtrack trigger
        assert hotels == [], (
            f"Expected no hotels under ${max_hotel:.0f}/night in Paris, got {hotels}"
        )
