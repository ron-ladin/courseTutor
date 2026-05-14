from typing import TypedDict, Optional
from models import TravelRequest, Itinerary, BookingConfirmation


class AgentState(TypedDict):
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
    return None
