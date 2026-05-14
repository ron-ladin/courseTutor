from __future__ import annotations

from typing import Any

import httpx

try:
    from .models import Activity, BookingRequest, ContactInfo, Flight, Hotel, PassengerInfo, PaymentInfo
except ImportError:
    from models import Activity, BookingRequest, ContactInfo, Flight, Hotel, PassengerInfo, PaymentInfo

DEFAULT_BASE_URL = "http://localhost:8000"
_START_HINT = "Run: uvicorn travel_agent.mock_server:app --reload --port 8000"


class DataClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Search methods ────────────────────────────────────────────────────────

    def get_flights(self, destination: str, date: str) -> list[Flight]:
        data = self._get("/flights/search", {"destination": destination, "date": date})
        return [Flight(**f) for f in data]

    def get_hotels(
        self,
        destination: str,
        checkin: str,
        checkout: str,
        max_price: float = 99999,
    ) -> list[Hotel]:
        data = self._get("/hotels/search", {
            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "max_price": max_price,
        })
        return [Hotel(**h) for h in data]

    def get_activities(self, destination: str) -> list[Activity]:
        data = self._get("/activities/search", {"destination": destination})
        return [Activity(**a) for a in data]

    def destinations(self) -> list[str]:
        return self._get("/destinations", {})["destinations"]

    # ── Booking methods ───────────────────────────────────────────────────────

    def book_flight(
        self,
        flight_id: str,
        passenger: PassengerInfo,
        contact: ContactInfo,
        payment: PaymentInfo,
    ) -> str:
        """POST /flights/book → returns booking_id string."""
        result = self._post("/flights/book", BookingRequest(
            item_id=flight_id, item_type="flight",
            passenger=passenger, contact=contact, payment=payment,
        ))
        return result["booking_id"]

    def book_hotel(
        self,
        hotel_id: str,
        passenger: PassengerInfo,
        contact: ContactInfo,
        payment: PaymentInfo,
    ) -> str:
        """POST /hotels/book → returns booking_id string."""
        result = self._post("/hotels/book", BookingRequest(
            item_id=hotel_id, item_type="hotel",
            passenger=passenger, contact=contact, payment=payment,
        ))
        return result["booking_id"]

    def book_activity(
        self,
        activity_id: str,
        passenger: PassengerInfo,
        contact: ContactInfo,
        payment: PaymentInfo,
    ) -> str:
        """POST /activities/book → returns booking_id string."""
        result = self._post("/activities/book", BookingRequest(
            item_id=activity_id, item_type="activity",
            passenger=passenger, contact=contact, payment=payment,
        ))
        return result["booking_id"]

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            r = httpx.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Cannot reach server at {self.base_url}. {_START_HINT}") from exc
        except httpx.RequestError as exc:
            raise ConnectionError(f"Request failed at {self.base_url}. {_START_HINT}") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"HTTP {exc.response.status_code} for {exc.request.url}") from exc

    def _post(self, path: str, body: BookingRequest) -> Any:
        url = f"{self.base_url}{path}"
        try:
            r = httpx.post(url, json=body.model_dump(mode="json"), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Cannot reach server at {self.base_url}. {_START_HINT}") from exc
        except httpx.RequestError as exc:
            raise ConnectionError(f"Request failed at {self.base_url}. {_START_HINT}") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Booking failed HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
