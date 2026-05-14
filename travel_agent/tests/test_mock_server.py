import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from travel_agent.data.mock_server import app


client = TestClient(app)


def test_tokyo_flights_have_required_offer_fields():
    response = client.get(
        "/flights/search",
        params={"destination": "Tokyo", "date": "2026-06-01"},
    )

    assert response.status_code == 200
    flights = response.json()
    assert len(flights) >= 2
    assert all(flight["price"] > 0 for flight in flights)
    assert all(flight["style_tags"] for flight in flights)
    assert all(flight["airline"] for flight in flights)
    assert all(flight["duration_hours"] > 0 for flight in flights)


def test_paris_budget_filter_exercises_backtracking_data_shape():
    response = client.get(
        "/hotels/search",
        params={
            "destination": "Paris",
            "checkin": "2026-06-01",
            "checkout": "2026-06-08",
            "max_price": 500,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_tokyo_hotel_search_respects_max_price():
    response = client.get(
        "/hotels/search",
        params={
            "destination": "Tokyo",
            "checkin": "2026-06-01",
            "checkout": "2026-06-08",
            "max_price": 200,
        },
    )

    assert response.status_code == 200
    hotels = response.json()
    assert hotels
    assert all(hotel["price_per_night"] <= 200 for hotel in hotels)


def test_destinations_include_demo_cities_and_country_options():
    response = client.get("/destinations")

    assert response.status_code == 200
    destinations = set(response.json()["destinations"])
    assert {"Tokyo", "Paris", "Bali", "New York"}.issubset(destinations)
    assert {"Japan", "France", "Italy", "Greece", "Thailand", "Spain", "United Kingdom", "Mexico", "Israel"}.issubset(destinations)
