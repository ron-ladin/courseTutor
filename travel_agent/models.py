from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TravelRequest(BaseModel):
    destination: str
    departure_date: date
    return_date: date
    budget: float
    travel_style: list[str] = Field(default_factory=list)

    @field_validator("budget")
    @classmethod
    def budget_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Budget must be a positive number")
        return value

    @field_validator("return_date")
    @classmethod
    def return_after_departure(cls, value: date, info) -> date:
        departure_date = info.data.get("departure_date")
        if departure_date is not None and value <= departure_date:
            raise ValueError("Return date must be after departure date")
        return value


class Flight(BaseModel):
    id: str
    destination: str
    price: float
    airline: str
    duration_hours: float
    style_tags: list[str] = Field(default_factory=list)


class Hotel(BaseModel):
    id: str
    destination: str
    name: str
    price_per_night: float
    stars: int
    style_tags: list[str] = Field(default_factory=list)


class Activity(BaseModel):
    id: str
    destination: str
    name: str
    price: float
    style_tags: list[str] = Field(default_factory=list)


class Itinerary(BaseModel):
    flight: Flight
    hotel: Hotel
    activities: list[Activity] = Field(default_factory=list)
    total_cost: float
    match_score: float = 0.0
    is_partial_fallback: bool = False


class BookingConfirmation(BaseModel):
    booking_id: UUID
    itinerary: Itinerary
