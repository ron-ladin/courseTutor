"""Tests for LiveDataClient — static-data path (no Amadeus credentials needed)."""

import pytest

try:
    from travel_agent.data.client import LiveDataClient
    from travel_agent.models import Activity, Flight, Hotel
except ImportError:
    from data.client import LiveDataClient
    from models import Activity, Flight, Hotel


def _client() -> LiveDataClient:
    """Return a client without Amadeus credentials — always uses static data."""
    import os
    os.environ.pop("AMADEUS_CLIENT_ID",     None)
    os.environ.pop("AMADEUS_CLIENT_SECRET", None)
    return LiveDataClient()


def test_live_client_returns_typed_flight_models():
    flights = _client().get_flights("Tokyo", "2026-06-01")
    assert len(flights) > 0
    assert all(isinstance(f, Flight) for f in flights)


def test_live_client_returns_empty_list_for_unknown_destination():
    assert _client().get_flights("Atlantis", "2026-06-01") == []
    assert _client().get_hotels("Atlantis", "2026-06-01", "2026-06-08") == []
    assert _client().get_activities("Atlantis") == []


def test_live_client_hotel_max_price_filter():
    client = _client()
    all_hotels = client.get_hotels("Tokyo", "2026-06-01", "2026-06-08")
    cheap = client.get_hotels("Tokyo", "2026-06-01", "2026-06-08", max_price=150)
    assert all(h.price_per_night <= 150 for h in cheap)
    assert len(cheap) <= len(all_hotels)


def test_live_client_booking_returns_valid_uuid():
    import uuid as _uuid
    from datetime import date
    from models import PassengerInfo, ContactInfo, PaymentInfo

    passenger = PassengerInfo(full_name="Test User", passport_number="AB123", date_of_birth=date(1990, 1, 1))
    contact   = ContactInfo(email="t@t.com", phone="+1", address="123 St")
    payment   = PaymentInfo(card_last4="1234", cardholder_name="TEST", card_expiry="06/28")

    client = _client()
    for bid in [
        client.book_flight("f1", passenger, contact, payment),
        client.book_hotel("h1", passenger, contact, payment),
        client.book_activity("a1", passenger, contact, payment),
    ]:
        _uuid.UUID(bid)  # raises ValueError if not a valid UUID
