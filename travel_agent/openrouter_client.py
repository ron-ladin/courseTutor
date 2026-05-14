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


# Human-readable labels for each collected field (used in prompts)
_FIELD_LABELS: dict[str, str] = {
    "full_name":       "passenger's full legal name",
    "passport_number": "passport number",
    "date_of_birth":   "date of birth (YYYY-MM-DD)",
    "email":           "contact email address",
    "phone":           "phone number including country code",
    "address":         "billing address",
    "card_last4":      "last 4 digits of payment card",
    "cardholder_name": "name exactly as shown on card",
    "card_expiry":     "card expiry date in MM/YY format",
}


def generate_conversational_prompt(
    missing_fields: list[str],
    chat_history: list[dict],
) -> str | None:
    """
    Generate a short, natural question asking the user for the missing
    passenger/payment fields.

    Returns the question string, or None when OpenRouter is disabled or the
    call fails — the caller must fall back to sequential rule-based prompts.
    """
    if not openrouter_enabled() or not missing_fields:
        return None

    labels = [_FIELD_LABELS.get(f, f.replace("_", " ")) for f in missing_fields]
    fields_str = " and ".join(labels)

    system = (
        "You are SkySwift AI, a friendly travel booking assistant. "
        "Your job is to collect missing passenger and payment details to complete a booking. "
        "Ask only for the fields listed — never invent or confirm data the user has not provided. "
        "Be warm, concise, and natural. One sentence only."
    )

    # Include up to the last 6 turns for context without bloating the prompt
    history_slice = chat_history[-6:]
    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(history_slice)
    messages.append({
        "role": "user",
        "content": (
            f"Still missing: {fields_str}. "
            "Ask the customer for these in one friendly sentence."
        ),
    })

    try:
        payload: dict[str, Any] = {
            "model":       os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
            "messages":    messages,
            "temperature": 0.5,
            "max_tokens":  120,
        }
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "http://localhost:8501",
                "X-Title":       "SkySwift Travel Planning Agent",
            },
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def extract_passenger_fields(user_message: str) -> dict[str, Any]:
    """
    Extract passenger, contact, and payment fields from a natural-language message.

    Returns a dict with any recognised fields, or {} when OpenRouter is disabled
    or extraction fails — the caller stores the raw answer for the pending field.

    Field names mirror _COLLECT_FIELDS keys:
        full_name, passport_number, date_of_birth,
        email, phone, address,
        card_last4, cardholder_name, card_expiry
    """
    if not openrouter_enabled() or not user_message.strip():
        return {}

    prompt = (
        "Extract booking details from this customer message. "
        "Return only valid JSON using keys from this exact set: "
        "full_name, passport_number, date_of_birth, email, phone, address, "
        "card_last4, cardholder_name, card_expiry. "
        "Rules: date_of_birth must be YYYY-MM-DD. "
        "card_last4 must be exactly 4 digits (no spaces). "
        "card_expiry must be MM/YY. "
        "Omit any field not clearly stated by the customer.\n\n"
        f"Customer message: {user_message}"
    )

    try:
        payload: dict[str, Any] = {
            "model":       os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
            "messages": [
                {
                    "role":    "system",
                    "content": "You extract structured booking JSON. Return JSON only, no prose.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens":  180,
        }
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "http://localhost:8501",
                "X-Title":       "SkySwift Travel Planning Agent",
            },
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.strip("`").removeprefix("json").strip()
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


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
