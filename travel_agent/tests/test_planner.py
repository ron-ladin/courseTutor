from datetime import date

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st

from travel_agent.models import Activity, Flight, Hotel, TravelRequest
from travel_agent.planner import run_planning_loop


class FakeClient:
    def __init__(
        self,
        flights: list[Flight],
        hotels: list[Hotel],
        activities: list[Activity] | None = None,
    ):
        self.flights = flights
        self.hotels = hotels
        self.activities = activities or []
        self.hotel_queries: list[float] = []

    def get_flights(self, destination: str, date: str) -> list[Flight]:
        return self.flights

    def get_hotels(
        self,
        destination: str,
        checkin: str,
        checkout: str,
        max_price: float = 99999,
    ) -> list[Hotel]:
        self.hotel_queries.append(max_price)
        return [hotel for hotel in self.hotels if hotel.price_per_night <= max_price]

    def get_activities(self, destination: str) -> list[Activity]:
        return self.activities


def travel_request(destination="Tokyo", budget=2000, style=None) -> TravelRequest:
    return TravelRequest(
        destination=destination,
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        budget=budget,
        travel_style=style or ["culture", "adventure"],
    )


def flight(id_: str, price: float) -> Flight:
    return Flight(
        id=id_,
        destination="Tokyo",
        price=price,
        airline=f"Air {id_}",
        duration_hours=10,
        style_tags=["culture"],
    )


def hotel(id_: str, price: float, tags=None) -> Hotel:
    return Hotel(
        id=id_,
        destination="Tokyo",
        name=f"Hotel {id_}",
        price_per_night=price,
        stars=3,
        style_tags=tags or ["culture"],
    )


def activity(id_: str, price: float, tags=None) -> Activity:
    return Activity(
        id=id_,
        destination="Tokyo",
        name=f"Activity {id_}",
        price=price,
        style_tags=tags or ["culture"],
    )


@given(
    st.lists(
        st.floats(
            min_value=10,
            max_value=5000,
            allow_nan=False,
            allow_infinity=False,
            width=32,
        ),
        min_size=1,
        max_size=6,
        unique=True,
    )
)
def test_planning_loop_selects_lowest_cost_flight_first(prices):
    flights = [flight(f"f{i}", price) for i, price in enumerate(prices)]
    request = travel_request(budget=max(prices) + 100)
    client = FakeClient(flights=flights, hotels=[hotel("h1", 1)])

    itineraries = run_planning_loop(request, client, [])

    assert itineraries
    assert itineraries[0].flight.price == min(prices)


def test_hotel_search_uses_remaining_budget_as_max_price():
    # Planner now passes per-night ceiling: (budget - flight) / nights
    # travel_request uses 2026-06-01 → 2026-06-08 = 7 nights
    # budget=1000, flight=300 → remaining=700, per_night=700/7=100
    client = FakeClient(
        flights=[flight("f1", 300)],
        hotels=[hotel("h1", 100), hotel("h2", 500)],
    )

    itineraries = run_planning_loop(travel_request(budget=1000), client, [])

    assert client.hotel_queries[0] == pytest.approx(100)  # 700 / 7 nights
    assert itineraries[0].hotel.price_per_night <= 100


def test_planning_loop_selects_highest_match_score_hotel():
    client = FakeClient(
        flights=[flight("f1", 100)],
        hotels=[
            hotel("low", 100, ["budget"]),
            hotel("best", 120, ["culture", "adventure"]),
            hotel("middle", 80, ["culture"]),
        ],
    )

    itineraries = run_planning_loop(travel_request(budget=1000), client, [])

    assert itineraries[0].hotel.id == "best"


def test_activity_allocation_stays_within_remaining_budget():
    # 7 nights; budget=1000, flight=300 → per-night ceiling=(1000-300)/7=100
    # hotel h1=$50/night (passes). Total hotel=50*7=350. Remaining for activities=700-350=350.
    client = FakeClient(
        flights=[flight("f1", 300)],
        hotels=[hotel("h1", 50)],
        activities=[
            activity("a1", 150, ["culture", "adventure"]),
            activity("a2", 100, ["culture"]),
            activity("a3", 999, ["culture"]),
        ],
    )

    itineraries = run_planning_loop(travel_request(budget=1000), client, [])
    selected_activity_cost = sum(a.price for a in itineraries[0].activities)

    assert selected_activity_cost <= 350  # remaining after flight + hotel


def test_backtrack_iteration_never_exceeds_one_and_creates_partial_fallback():
    reasoning_log: list[str] = []
    client = FakeClient(
        flights=[flight("f1", 400), flight("f2", 550)],
        hotels=[hotel("fallback", 1600)],
    )
    request = travel_request(destination="Paris", budget=1900, style=["romance"])

    itineraries = run_planning_loop(request, client, reasoning_log)

    assert len([entry for entry in reasoning_log if "Backtracking" in entry]) == 1
    assert len(itineraries) == 1
    assert itineraries[0].is_partial_fallback is True


def test_planning_output_cardinality_is_bounded_to_three():
    client = FakeClient(
        flights=[flight(f"f{i}", 100 + i) for i in range(6)],
        hotels=[hotel("h1", 10)],
    )

    itineraries = run_planning_loop(travel_request(budget=1000), client, [])

    assert 1 <= len(itineraries) <= 3
