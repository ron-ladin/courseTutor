from typing import Any

import httpx

try:
    from .models import Activity, Flight, Hotel
except ImportError:  # Allows importing from inside travel_agent/.
    from models import Activity, Flight, Hotel


DEFAULT_BASE_URL = "http://localhost:8000"
SERVER_START_HINT = "Run: uvicorn travel_agent.mock_server:app --reload --port 8000"


class DataClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_flights(self, destination: str, date: str) -> list[Flight]:
        data = self._get_json(
            "/flights/search",
            {"destination": destination, "date": date},
        )
        return [Flight(**flight) for flight in data]

    def get_hotels(
        self,
        destination: str,
        checkin: str,
        checkout: str,
        max_price: float = 99999,
    ) -> list[Hotel]:
        data = self._get_json(
            "/hotels/search",
            {
                "destination": destination,
                "checkin": checkin,
                "checkout": checkout,
                "max_price": max_price,
            },
        )
        return [Hotel(**hotel) for hotel in data]

    def get_activities(self, destination: str) -> list[Activity]:
        data = self._get_json("/activities/search", {"destination": destination})
        return [Activity(**activity) for activity in data]

    def destinations(self) -> list[str]:
        data = self._get_json("/destinations", {})
        return data["destinations"]

    def _get_json(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Cannot reach the travel data server at {self.base_url}. "
                f"{SERVER_START_HINT}"
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectionError(
                f"Travel data server request failed at {self.base_url}. "
                f"{SERVER_START_HINT}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Travel data service error: HTTP {exc.response.status_code} "
                f"for {exc.request.url}"
            ) from exc
