from models import Itinerary, TravelRequest
from data_client import DataClient


def compute_raw_score(item_tags: list[str], user_style: list[str]) -> float:
    return 0.0


def normalize_scores(scores: list[float]) -> list[float]:
    return scores


def run_planning_loop(request: TravelRequest, client: DataClient, reasoning_log: list[str]) -> list[Itinerary]:
    return []
