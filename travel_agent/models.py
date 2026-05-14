from __future__ import annotations

import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


# ── Trip preference models ────────────────────────────────────────────────────

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


# ── Booking / passenger models ────────────────────────────────────────────────

class PassengerInfo(BaseModel):
    full_name: str
    passport_number: str
    date_of_birth: date


class ContactInfo(BaseModel):
    email: str
    phone: str
    address: str


class PaymentInfo(BaseModel):
    # Never store full card numbers — last 4 digits only
    card_last4: str
    cardholder_name: str
    card_expiry: str  # MM/YY

    @field_validator("card_last4")
    @classmethod
    def validate_card_last4(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 4:
            raise ValueError("card_last4 must be exactly 4 digits")
        return v

    @field_validator("card_expiry")
    @classmethod
    def validate_card_expiry(cls, v: str) -> str:
        # Accepts 01/25 through 12/99
        if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", v):
            raise ValueError("card_expiry must be MM/YY with month 01–12")
        return v


class BookingRequest(BaseModel):
    """Payload sent to the mock server to record a single component booking."""
    item_id: str
    item_type: str  # "flight" | "hotel" | "activity"
    passenger: PassengerInfo
    contact: ContactInfo
    payment: PaymentInfo


class BookingConfirmation(BaseModel):
    """Full booking record returned after all components are confirmed."""
    booking_id: str                       # flight booking ID used as master reference
    hotel_booking_id: str = ""
    activity_booking_ids: list[str] = []
    itinerary: Itinerary
    passenger: Optional[PassengerInfo] = None
    contact: Optional[ContactInfo] = None
