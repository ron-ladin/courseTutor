from __future__ import annotations

import os
import json
from typing import Any

import httpx

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional at runtime.
    load_dotenv = None

try:
    from .models import Itinerary, TravelRequest
    from .data.static import STATIC_DATA
except ImportError:
    from models import Itinerary, TravelRequest
    from data.static import STATIC_DATA


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv()


def openrouter_enabled() -> bool:
    _load_env()
    return (
        os.getenv("OPENROUTER_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        and bool(os.getenv("OPENROUTER_API_KEY"))
    )


def build_trip_explanation(
    request: TravelRequest,
    itineraries: list[Itinerary],
) -> str | None:
    """
    Return a short AI-written explanation when OpenRouter is configured.

    The deterministic planner remains the source of truth. This helper only
    improves the wording shown to the user, and quietly returns None on any
    API/configuration failure so the demo can continue on mock data.
    """
    if not openrouter_enabled() or not itineraries:
        return None

    option_lines = []
    for index, itinerary in enumerate(itineraries, start=1):
        activities = ", ".join(activity.name for activity in itinerary.activities) or "no paid activities"
        fallback = " yes" if itinerary.is_partial_fallback else " no"
        option_lines.append(
            f"Option {index}: flight_id={itinerary.flight.id}, airline={itinerary.flight.airline}, "
            f"flight_price=${itinerary.flight.price:.2f}, duration_hours={itinerary.flight.duration_hours}, "
            f"hotel={itinerary.hotel.name}, hotel_price_per_night=${itinerary.hotel.price_per_night:.2f}, "
            f"hotel_stars={itinerary.hotel.stars}, activities={activities}, "
            f"total=${itinerary.total_cost:.2f}, match={itinerary.match_score:.2f}, "
            f"exceeds_budget={fallback}"
        )

    prompt = (
        "Write the main customer-facing answer for a travel planning chat. "
        "Use only the itinerary facts below from the local mock travel database. "
        "Do not invent airlines, prices, hotels, activities, booking links, airport names, or availability. "
        "Sound like a helpful travel agent talking directly to the customer. "
        "Start with a short recommendation, then compare the options briefly. "
        "Keep it under 180 words.\n\n"
        f"Destination: {request.destination}\n"
        f"Dates: {request.departure_date} to {request.return_date}\n"
        f"Budget: ${request.budget:.2f}\n"
        f"Travel style: {', '.join(request.travel_style)}\n"
        + "\n".join(option_lines)
    )

    try:
        payload: dict[str, Any] = {
            "model": os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are SkySwift AI, a travel planning assistant. "
                        "You must stay grounded in the provided mock itinerary facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 160,
        }
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "SkySwift Travel Planning Agent",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def extract_travel_request_fields(user_message: str) -> dict[str, Any]:
    """
    Extract partial TravelRequest fields from a natural-language customer message.

    Returns an empty dict when OpenRouter is disabled or extraction fails. The
    onboarding node can then continue its normal one-question-at-a-time flow.
    """
    if not openrouter_enabled() or not user_message.strip():
        return {}

    prompt = (
        "Extract travel planning fields from this customer message. "
        "Return only valid JSON with keys from this exact set: "
        "destination, departure_date, return_date, budget, travel_style. "
        "Use YYYY-MM-DD dates. destination must be one of these supported places when clear: "
        f"{', '.join(STATIC_DATA.keys())}. "
        "when the customer clearly asks for one of them. travel_style must be an array "
        "using only these values when present: adventure, culture, luxury, romance, nature, food, budget. "
        "Omit any unknown fields. Do not guess dates.\n\n"
        f"Customer message: {user_message}"
    )

    try:
        payload: dict[str, Any] = {
            "model": os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
            "messages": [
                {
                    "role": "system",
                    "content": "You extract structured travel request JSON. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 180,
        }
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "SkySwift Travel Planning Agent",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.strip("`")
            content = content.removeprefix("json").strip()
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}
