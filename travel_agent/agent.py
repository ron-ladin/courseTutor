"""LangGraph agent orchestration (stub - Dev 3 will implement)."""

from typing import TypedDict, Optional
from models import TravelRequest, Itinerary, BookingConfirmation


class AgentState(TypedDict):
    """State for the travel planning agent."""
    messages: list[dict]
    travel_request: dict
    confirmed_request: Optional[TravelRequest]
    itineraries: list[Itinerary]
    selected_itinerary: Optional[Itinerary]
    booking: Optional[BookingConfirmation]
    reasoning_log: list[str]
    backtrack_count: int
    phase: str  # "onboard" | "plan" | "rank" | "confirm" | "done"


def build_graph():
    """Build and return the LangGraph state machine."""
    return None  # real graph wired later
