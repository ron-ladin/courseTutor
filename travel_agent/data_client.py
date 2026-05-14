from models import Flight, Hotel, Activity


class DataClient:
    def get_flights(self, destination: str, date: str) -> list[Flight]:
        return []

    def get_hotels(self, destination: str, checkin: str, checkout: str, max_price: float = 99999) -> list[Hotel]:
        return []

    def get_activities(self, destination: str) -> list[Activity]:
        return []

    def destinations(self) -> list[str]:
        return []
