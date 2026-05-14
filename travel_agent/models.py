from pydantic import BaseModel, model_validator
from datetime import date


class TravelRequest(BaseModel):
    destination: str
    departure_date: date
    return_date: date
    budget: float
    travel_style: list[str] = []

    @model_validator(mode="after")
    def budget_must_be_positive(self):
        if self.budget <= 0:
            raise ValueError("budget must be positive")
        return self

    @model_validator(mode="after")
    def return_after_departure(self):
        if self.return_date <= self.departure_date:
            raise ValueError("return_date must be after departure_date")
        return self


class Flight(BaseModel):
    id: str
    destination: str
    price: float
    airline: str
    duration_hours: float
    style_tags: list[str] = []


class Hotel(BaseModel):
    id: str
    destination: str
    name: str
    price_per_night: float
    stars: int
    style_tags: list[str] = []


class Activity(BaseModel):
    id: str
    destination: str
    name: str
    price: float
    style_tags: list[str] = []


class Itinerary(BaseModel):
    flight: Flight
    hotel: Hotel
    activities: list[Activity] = []
    total_cost: float = 0.0
    match_score: float = 0.0
    is_partial_fallback: bool = False


class BookingConfirmation(BaseModel):
    booking_id: str
    itinerary: Itinerary
