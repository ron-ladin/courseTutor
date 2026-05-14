import httpx
import pytest

from travel_agent.data_client import DataClient
from travel_agent.models import Flight


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", "http://test/flights/search")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "HTTP error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        return self.payload


def test_data_client_returns_typed_flight_models(monkeypatch):
    def fake_get(url, params, timeout):
        assert url == "http://test/flights/search"
        assert params == {"destination": "Tokyo", "date": "2026-06-01"}
        assert timeout == 5.0
        return DummyResponse(
            [
                {
                    "id": "f1",
                    "destination": "Tokyo",
                    "price": 650,
                    "airline": "ANA",
                    "duration_hours": 14,
                    "style_tags": ["culture"],
                }
            ]
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    flights = DataClient(base_url="http://test").get_flights("Tokyo", "2026-06-01")

    assert flights == [
        Flight(
            id="f1",
            destination="Tokyo",
            price=650,
            airline="ANA",
            duration_hours=14,
            style_tags=["culture"],
        )
    ]


def test_data_client_connection_error_mentions_start_command(monkeypatch):
    def fake_get(url, params, timeout):
        request = httpx.Request("GET", url)
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(ConnectionError, match="uvicorn travel_agent.mock_server:app"):
        DataClient(base_url="http://test").destinations()
