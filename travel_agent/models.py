"""Data models for travel planning agent (stubs - Dev 1 will implement validators)."""

from pydantic import BaseModel, field_validator
from datetime import date


class TravelRequest(BaseModel):
    """User's travel request."""
    destination: str = ""
    departure_date: date = date.today()
    return_date: date = date.today()
    budget: float = 0.0
    travel_style: list[str] = []

    @field_validator("budget")
    def budget_must_be_positive(cls, v):
        """Validate budget is positive."""
        if v <= 0:
            raise ValueError("Budget must be positive")
        return v

    @field_validator("return_date")
    def return_after_departure(cls, v, info):
        """Validate return date is after departure date."""
        if "departure_date" in info.data and v <= info.data["departure_date"]:
            raise ValueError("Return date must be after departure date")
        return v


class Flight(BaseModel):
    """Flight option."""
    id: str = ""
    destination: str = ""
    price: float = 0.0
    airline: str = ""
    duration_hours: float = 0.0
    style_tags: list[str] = []


class Hotel(BaseModel):
    """Hotel option."""
    id: str = ""
    destination: str = ""
    name: str = ""
    price_per_night: float = 0.0
    stars: int = 0
    style_tags: list[str] = []


class Activity(BaseModel):
    """Activity option."""
    id: str = ""
    destination: str = ""
    name: str = ""
    price: float = 0.0
    style_tags: list[str] = []


class Itinerary(BaseModel):
    """Complete itinerary combining flight, hotel, and activities."""
    flight: Flight = Flight()
    hotel: Hotel = Hotel()
    activities: list[Activity] = []
    total_cost: float = 0.0
    match_score: float = 0.0
    is_partial_fallback: bool = False


class BookingConfirmation(BaseModel):
    """Booking confirmation with ID and itinerary."""
    booking_id: str = ""
    itinerary: Itinerary = Itinerary()
