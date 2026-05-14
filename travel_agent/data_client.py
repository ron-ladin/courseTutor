"""HTTP client for mock server (stub - Dev 2 will implement)."""

from models import Flight, Hotel, Activity


class DataClient:
    """Client for fetching travel data from mock server."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize data client with mock server URL."""
        self.base_url = base_url
    
    def get_flights(self, destination: str, date: str) -> list[Flight]:
        """Get flights for destination on given date."""
        return []
    
    def get_hotels(self, destination: str, checkin: str, checkout: str, max_price: float = 99999) -> list[Hotel]:
        """Get hotels for destination within budget."""
        return []
    
    def get_activities(self, destination: str) -> list[Activity]:
        """Get activities for destination."""
        return []
    
    def destinations(self) -> list[str]:
        """Get list of available destinations."""
        return []
