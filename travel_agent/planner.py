"""Planning loop and MatchScore engine (stub - Dev 2 will implement)."""

from models import Itinerary, TravelRequest
from data_client import DataClient


def compute_raw_score(item_tags: list[str], user_style: list[str]) -> float:
    """Compute raw match score as dot product of tags."""
    return 0.0


def aggregate_itinerary_tags(flight_tags: list[str], hotel_tags: list[str], activity_tags: list[str]) -> list[str]:
    """Aggregate all tags from flight, hotel, and activities."""
    return []


def normalize_scores(scores: list[float]) -> list[float]:
    """Normalize scores using Min-Max normalization."""
    if not scores or all(s == scores[0] for s in scores):
        return [1.0] * len(scores)
    return scores


def run_planning_loop(request: TravelRequest, client: DataClient, reasoning_log: list[str]) -> list[Itinerary]:
    """Run planning loop to generate itinerary options."""
    return []
