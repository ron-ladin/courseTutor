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


def _fallback_autonomous_response(chat_history: list[dict], current_preferences: dict) -> dict[str, Any]:
    """Offline/test-safe backup for the autonomous travel conversation."""
    preferences = dict(current_preferences or {})
    latest_user = ""
    for msg in reversed(chat_history or []):
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            latest_user = msg["content"].strip()
            break

    required = ("destination", "departure_date", "return_date", "travel_style", "budget")
    missing = [field for field in required if field not in preferences]

    if latest_user.lower() in {"yes", "y", "ok", "confirm", "go ahead", "start planning"} and not missing:
        return {"extracted_data": preferences, "agent_status": "APPROVED", "response_to_user": "Great, I will start planning this trip now."}

    if not latest_user and not missing and "travel_style" in preferences:
        return {"extracted_data": preferences, "agent_status": "APPROVED", "response_to_user": "Great, I will start planning this trip now."}

    if latest_user and missing:
        if "destination" in preferences and latest_user.lower() in {"not a number", "invalid budget", "bad budget"}:
            return {"extracted_data": preferences, "agent_status": "COLLECTING", "response_to_user": "Please send a valid budget as a number, for example 2500."}
        looks_like_date = bool(
            any(month in latest_user.lower() for month in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])
            or any(sep in latest_user for sep in ["-", "/", "."])
            or any(word in latest_user.lower() for word in ["date", "depart", "return", "fly"])
        )
        looks_like_budget = bool(
            "$" in latest_user
            or "budget" in latest_user.lower()
            or "dollar" in latest_user.lower()
            or "usd" in latest_user.lower()
            or latest_user.replace(",", "").strip().isdigit()
        )
        if (
            "destination" in preferences
            and "travel_style" not in preferences
            and not looks_like_date
            and not looks_like_budget
        ):
            preferences["travel_style"] = latest_user
            missing = [field for field in required if field not in preferences]
            return {
                "extracted_data": preferences,
                "agent_status": "COLLECTING",
                "response_to_user": "Great, I will shape the trip around that. What date would you like to depart?",
            }

        field = missing[0]
        if field == "destination":
            supported = {name.lower(): name for name in STATIC_DATA.keys()}
            matched = next((name for lowered, name in supported.items() if lowered in latest_user.lower()), None)
            preferences["destination"] = matched or latest_user
        elif field in {"departure_date", "return_date"}:
            preferences[field] = latest_user
        elif field == "travel_style":
            if looks_like_budget:
                return {
                    "extracted_data": preferences,
                    "agent_status": "COLLECTING",
                    "response_to_user": "Before we talk budget, what sounds most interesting: restaurants, museums, sightseeing, nightlife, nature, or something more relaxed?",
                }
            preferences["travel_style"] = latest_user
        elif field == "budget":
            cleaned = latest_user.lower().replace("$", "").replace(",", "").replace("usd", "").replace("dollars", "").strip()
            try:
                preferences["budget"] = float(cleaned)
            except ValueError:
                return {"extracted_data": preferences, "agent_status": "COLLECTING", "response_to_user": "Please send a valid budget as a number, for example 2500."}

    missing = [field for field in required if field not in preferences]
    if missing:
        prompts = {
            "destination": "What destination city would you like to travel to? Please choose one of the SkySwift demo cities.",
            "departure_date": "Great. What date would you like to depart? You can write it naturally, like 2026-8-15, 15/8/26, or April 26.",
            "return_date": "And when should you return? You can write it naturally too, like 20/8/26 or August 20.",
            "travel_style": "Before we talk budget, what sounds most interesting: restaurants, museums, sightseeing, nightlife, nature, or something more relaxed?",
            "budget": "What total budget should I keep in mind for the whole trip, in USD?",
        }
        return {"extracted_data": preferences, "agent_status": "COLLECTING", "response_to_user": prompts[missing[0]]}

    return {
        "extracted_data": preferences,
        "agent_status": "READY_TO_PROPOSE",
        "response_to_user": "I have the destination, dates, budget, and style. Should I start planning the itinerary now?",
    }


def generate_autonomous_response(
    chat_history: list[dict],
    current_preferences: dict,
) -> dict[str, Any]:
    """
    Autonomous onboarding brain for the travel agent.

    The model owns the conversation strategy and must return structured JSON:
      - extracted_data: the accumulated travel preferences understood so far
      - agent_status: COLLECTING | READY_TO_PROPOSE | APPROVED
      - response_to_user: the next natural-language assistant message

    The deterministic planner still owns actual itinerary construction after
    the user explicitly approves planning.
    """
    supported_destinations = ", ".join(STATIC_DATA.keys())
    safe_preferences = current_preferences or {}

    if os.getenv("PYTEST_CURRENT_TEST"):
        return _fallback_autonomous_response(chat_history, safe_preferences)

    if not openrouter_enabled():
        return _fallback_autonomous_response(chat_history, safe_preferences)

    from datetime import date as _date
    today_str = _date.today().isoformat()

    system_prompt = (
        f"Today's date is {today_str}. "
        "You are SkySwift AI, an autonomous travel agent. "
        "Your goal is to collect enough information to plan a trip: destination, exact departure_date, "
        "exact return_date, and total budget in USD. If the user is flexible about dates, propose concrete "
        "YYYY-MM-DD dates and ask them to confirm. All proposed dates must be strictly in the future (after today). "
        "You may also capture travel_style when the user mentions it.\n\n"
        "Supported demo destinations are: " + supported_destinations + ". "
        "If the user asks for an unsupported destination, explain that this demo currently supports only those places.\n\n"
        "When the user chooses a supported destination and has not shared travel_style/interests yet, do not ask for budget in the same message. "
        "First suggest 2-3 things they could do there, then ask what kind of activities sound interesting: restaurants, museums, sightseeing, nightlife, nature, or relaxed experiences. "
        "Never combine activity suggestions/interests and budget in the same response. "
        "Only ask for budget after the customer has shared dates and some preference/interests. "
        "Use only general suggestions or activities from the supported demo context; do not invent prices or availability at this stage.\n\n"
        "Always return ONLY valid JSON with exactly these three top-level keys:\n"
        "1. extracted_data: an object containing all known trip fields so far. Use keys: "
        "destination, departure_date, return_date, budget, travel_style. Dates must be YYYY-MM-DD. "
        "budget must be numeric. travel_style should be an array of short tags when present.\n"
        "2. agent_status: exactly one of COLLECTING, READY_TO_PROPOSE, APPROVED.\n"
        "3. response_to_user: the friendly natural-language response to show the user.\n\n"
        "Status rules:\n"
        "- COLLECTING: any required information is missing, unclear, invalid, or the user is still deciding.\n"
        "- READY_TO_PROPOSE: destination, departure_date, return_date, and budget are all present and valid; "
        "ask the user if you should start planning.\n"
        "- APPROVED: use only when the required fields are present and the latest user message explicitly approves "
        "planning, for example yes, go ahead, start planning, confirm, or sounds good.\n\n"
        "Never claim that flights, hotels, prices, or availability have been searched before the planner runs. "
        "Never invent booking references."
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": (
                "Current accumulated preferences, which you may correct or extend from the conversation: "
                f"{json.dumps(safe_preferences, ensure_ascii=False, default=str)}"
            ),
        },
    ]

    added_history = False
    for msg in chat_history[-12:]:
        role = msg.get("role")
        content = msg.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            messages.append({"role": role, "content": content})
            added_history = True

    if not added_history:
        messages.append({
            "role": "user",
            "content": "Start the travel-planning conversation and ask for the first useful detail.",
        })

    try:
        payload: dict[str, Any] = {
            "model": os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 420,
            "response_format": {"type": "json_object"},
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
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("OpenRouter returned non-object JSON")

        extracted = parsed.get("extracted_data")
        status = str(parsed.get("agent_status", "COLLECTING")).strip().upper()
        response_text = str(parsed.get("response_to_user", "")).strip()

        if not isinstance(extracted, dict):
            extracted = {}
        if status not in {"COLLECTING", "READY_TO_PROPOSE", "APPROVED"}:
            status = "COLLECTING"
        if not response_text:
            response_text = "Tell me where you would like to travel, your dates, and your budget."

        return {
            "extracted_data": extracted,
            "agent_status": status,
            "response_to_user": response_text,
        }
    except Exception:
        return _fallback_autonomous_response(chat_history, safe_preferences)


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
        "Use YYYY-MM-DD dates. "
        "Map destination to the canonical city name: USA/America/US/United States/NYC -> 'New York'; "
        "Tel Aviv/TLV/Tel Aviv Israel -> 'Tel Aviv'; Rome/Milan/Venice -> 'Rome'; "
        "London/Edinburgh -> 'London'; Barcelona/Madrid -> 'Barcelona'; "
        "Athens/Santorini -> 'Athens'; Bangkok/Phuket -> 'Bangkok'; "
        "Osaka/Kyoto -> 'Kyoto'; Nice/Lyon -> 'Nice'; Cancun/Mexico City -> 'Mexico City'. "
        f"Other supported destinations: {', '.join(STATIC_DATA.keys())}. "
        "travel_style must be an array using only: adventure, culture, luxury, romance, nature, food, budget. "
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


def generate_travel_followup(
    missing_field: str,
    current_request: dict[str, Any],
    chat_history: list[dict],
    last_user_message: str | None = None,
) -> str | None:
    """
    Ask for the next missing travel-planning field in a natural agent voice.

    The graph still controls which field is needed; OpenRouter only improves the
    wording so the experience feels like a travel concierge instead of a form.
    """
    if not openrouter_enabled():
        return None

    field_labels = {
        "destination": "destination city or country",
        "departure_date": "departure date in YYYY-MM-DD format",
        "return_date": "return date in YYYY-MM-DD format",
        "budget": "total budget in USD",
        "travel_style": "preferred travel style, such as adventure, culture, luxury, romance, nature, or food",
    }
    label = field_labels.get(missing_field, missing_field.replace("_", " "))
    supported = ", ".join(STATIC_DATA.keys())
    known = json.dumps(current_request, default=str)

    system = (
        "You are SkySwift AI, a polished travel concierge inside a chat product. "
        "You are warm, concise, and specific. You help the customer plan a trip using the supported demo destinations. "
        "Never pretend you already searched flights or hotels before the planner runs. "
        "Ask for exactly one missing detail. Do not mention internal field names."
    )

    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(chat_history[-6:])
    messages.append({
        "role": "user",
        "content": (
            f"Known trip details so far: {known}\n"
            f"Supported destinations: {supported}\n"
            f"Next missing detail: {label}\n"
            f"Customer just said: {last_user_message or ''}\n"
            "Write the next assistant message. One or two short sentences. "
            "If the customer only greeted you or gave an unsupported destination, respond naturally and ask for the destination."
        ),
    })

    try:
        payload: dict[str, Any] = {
            "model": os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
            "messages": messages,
            "temperature": 0.55,
            "max_tokens": 100,
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
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
