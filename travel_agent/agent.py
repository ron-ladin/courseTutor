from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional, TypedDict

try:
    from .models import BookingConfirmation, ContactInfo, Itinerary, PassengerInfo, PaymentInfo, TravelRequest
    from .data.client import LiveDataClient as DataClient
    from .openrouter_client import (
        build_trip_explanation,
        extract_passenger_fields,
        generate_autonomous_response,
        generate_conversational_prompt,
    )
    from .planner import aggregate_itinerary_tags, compute_raw_score, normalize_scores, run_planning_loop
except ImportError:
    from models import BookingConfirmation, ContactInfo, Itinerary, PassengerInfo, PaymentInfo, TravelRequest
    from data.client import LiveDataClient as DataClient
    from openrouter_client import (
        build_trip_explanation,
        extract_passenger_fields,
        generate_autonomous_response,
        generate_conversational_prompt,
    )
    from planner import aggregate_itinerary_tags, compute_raw_score, normalize_scores, run_planning_loop

from langgraph.graph import END, StateGraph

LiveDataClient = DataClient


# ── State definition ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages:           list[dict]
    travel_request:     dict
    confirmed_request:  Optional[TravelRequest]
    itineraries:        list[Itinerary]
    selected_itinerary: Optional[Itinerary]
    booking:            Optional[BookingConfirmation]
    reasoning_log:      list[str]
    backtrack_count:    int
    phase:              str   # "onboard" | "plan" | "rank" | "collect" | "confirm" | "done"
    agent_status:       str   # "COLLECTING" | "READY_TO_PROPOSE" | "APPROVED"
    passenger_info:     dict  # full_name, passport_number, date_of_birth
    contact_info:       dict  # email, phone, address
    payment_info:       dict  # card_last4, cardholder_name, card_expiry


# ── Onboarding ────────────────────────────────────────────────────────────────

_TRAVEL_FIELDS = {"destination", "departure_date", "return_date", "budget", "travel_style"}
_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _coerce_year(year: str | int | None, fallback_year: int | None = None) -> int:
    if year is None:
        return fallback_year or date.today().year
    year_int = int(year)
    if year_int < 100:
        return 2000 + year_int
    return year_int


def _format_date(year: int, month: int, day: int) -> str:
    return date(year, month, day).isoformat()


def _normalise_date_value(value: Any, fallback_year: int | None = None) -> str:
    """
    Convert common customer date formats to YYYY-MM-DD.

    Supported examples:
      2026-8-15, 15/8/26, 25.6.2026, April 26, Apr 26 2026, 26 April 2026.
    """
    raw = str(value).strip()
    if not raw:
        raise ValueError("empty date")

    iso_match = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", raw)
    if iso_match:
        year, month, day = iso_match.groups()
        return _format_date(int(year), int(month), int(day))

    numeric_match = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?", raw)
    if numeric_match:
        day, month, year = numeric_match.groups()
        return _format_date(_coerce_year(year, fallback_year), int(month), int(day))

    lowered = raw.lower().replace(",", " ")
    lowered = re.sub(r"\s+", " ", lowered).strip()

    month_first = re.fullmatch(r"([a-z]+)\s+(\d{1,2})(?:\s+(\d{2,4}))?", lowered)
    if month_first and month_first.group(1) in _MONTHS:
        month_name, day, year = month_first.groups()
        return _format_date(_coerce_year(year, fallback_year), _MONTHS[month_name], int(day))

    day_first = re.fullmatch(r"(\d{1,2})\s+([a-z]+)(?:\s+(\d{2,4}))?", lowered)
    if day_first and day_first.group(2) in _MONTHS:
        day, month_name, year = day_first.groups()
        return _format_date(_coerce_year(year, fallback_year), _MONTHS[month_name], int(day))

    raise ValueError(f"unsupported date format: {raw}")


def _normalise_trip_dates(tr: dict) -> dict:
    normalised = dict(tr)
    departure_year: int | None = None

    if "departure_date" in normalised:
        departure = _normalise_date_value(normalised["departure_date"])
        normalised["departure_date"] = departure
        departure_year = date.fromisoformat(departure).year

    if "return_date" in normalised:
        normalised["return_date"] = _normalise_date_value(normalised["return_date"], departure_year)

    return normalised


def _merge_extracted_preferences(current: dict, extracted: dict[str, Any]) -> dict:
    """Merge model-extracted travel fields into the persisted request state."""
    merged = dict(current or {})
    for key, value in (extracted or {}).items():
        if key not in _TRAVEL_FIELDS or value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        merged[key] = value
    try:
        merged = _normalise_trip_dates(merged)
    except ValueError:
        pass
    return merged


def _normalise_travel_style(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()] if str(value).strip() else []


def _coerce_budget(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = (
            value.lower()
            .replace("$", "")
            .replace(",", "")
            .replace("usd", "")
            .replace("dollars", "")
            .strip()
        )
        return float(cleaned)
    return float(value)


def _build_confirmed_request_from_preferences(
    state: AgentState,
    tr: dict,
) -> tuple[Optional[TravelRequest], Optional[str]]:
    """Validate the LLM-extracted preferences and build the final TravelRequest."""
    missing = [
        field
        for field in ("destination", "departure_date", "return_date", "budget")
        if field not in tr
    ]
    if missing:
        return None, "Missing trip details: " + ", ".join(missing)

    try:
        tr = _normalise_trip_dates(tr)
        confirmed = TravelRequest(
            destination=str(tr["destination"]),
            departure_date=date.fromisoformat(str(tr["departure_date"]).strip()),
            return_date=date.fromisoformat(str(tr["return_date"]).strip()),
            budget=_coerce_budget(tr["budget"]),
            travel_style=_normalise_travel_style(tr.get("travel_style")),
        )
        return confirmed, None
    except Exception as exc:
        return None, f"Validation error: {exc}"


def onboard_node(state: AgentState) -> AgentState:
    """
    Autonomous onboarding node.

    The LLM owns the conversation strategy and returns structured JSON with:
      extracted_data, agent_status, response_to_user.

    This node only persists the extracted state and routes the graph forward
    when the user explicitly approves planning.
    """
    messages = list(state.get("messages", []))
    travel_request = dict(state.get("travel_request", {}))

    llm_response = generate_autonomous_response(messages, travel_request)

    extracted = llm_response.get("extracted_data", {})
    if not isinstance(extracted, dict):
        extracted = {}

    travel_request = _merge_extracted_preferences(travel_request, extracted)

    agent_status = str(llm_response.get("agent_status", "COLLECTING")).strip().upper()
    if agent_status not in {"COLLECTING", "READY_TO_PROPOSE", "APPROVED"}:
        agent_status = "COLLECTING"

    response_to_user = str(llm_response.get("response_to_user", "")).strip()
    if response_to_user:
        messages.append({"role": "assistant", "content": response_to_user})

    if agent_status == "APPROVED":
        confirmed, error = _build_confirmed_request_from_preferences(state, travel_request)
        if confirmed is not None:
            state["confirmed_request"] = confirmed
            state["phase"] = "plan"
        else:
            agent_status = "COLLECTING"
            state["confirmed_request"] = None
            state["phase"] = "onboard"
            messages.append({
                "role": "assistant",
                "content": (
                    "I am almost ready, but I still need valid trip details before planning. "
                    f"{error}."
                ),
            })
    else:
        state["phase"] = "onboard"

    state["messages"] = messages
    state["travel_request"] = travel_request
    state["agent_status"] = agent_status
    return state


# ── Plan & Rank ───────────────────────────────────────────────────────────────

def plan_node(state: AgentState) -> AgentState:
    messages = list(state.get("messages", []))
    confirmed = state.get("confirmed_request")
    reasoning_log = list(state.get("reasoning_log", []))

    if not confirmed:
        messages.append({
            "role": "assistant",
            "content": "No confirmed request. Please complete onboarding first.",
        })
        state["messages"] = messages
        return state

    try:
        itineraries = run_planning_loop(confirmed, DataClient(), reasoning_log)
        state["itineraries"] = itineraries
        state["reasoning_log"] = reasoning_log
        state["phase"] = "rank"

        msg = (
            f"I found {len(itineraries)} itinerary option(s). Here are the best matches."
            if itineraries
            else "No itineraries found. Please try a higher budget."
        )
        messages.append({"role": "assistant", "content": msg})

    except ConnectionError as e:
        messages.append({"role": "assistant", "content": str(e)})
        state["phase"] = "onboard"
    except Exception as e:
        messages.append({"role": "assistant", "content": f"Planning error: {e}"})
        state["phase"] = "onboard"

    state["messages"] = messages
    return state


def rank_node(state: AgentState) -> AgentState:
    messages = list(state.get("messages", []))
    itineraries = list(state.get("itineraries", []))
    confirmed = state.get("confirmed_request")
    reasoning_log = list(state.get("reasoning_log", []))

    if not itineraries or not confirmed:
        state["phase"] = "rank"
        return state

    raw_scores = [
        compute_raw_score(aggregate_itinerary_tags(it), confirmed.travel_style)
        for it in itineraries
    ]
    normalized = normalize_scores(raw_scores)

    for it, score in zip(itineraries, normalized):
        it.match_score = score

    itineraries.sort(key=lambda it: it.match_score, reverse=True)
    itineraries = itineraries[:3]

    if not any("Trade-off Analysis" in e for e in reasoning_log):
        reasoning_log.append("Trade-off Analysis:")
        for i, it in enumerate(itineraries):
            reasoning_log.append(
                f"  Option {i+1}: {it.flight.airline} + {it.hotel.name} "
                f"(Match: {it.match_score:.0%}, Cost: ${it.total_cost:.2f})"
            )

    state["itineraries"] = itineraries
    state["reasoning_log"] = reasoning_log
    state["phase"] = "rank"

    ai_explanation = build_trip_explanation(confirmed, itineraries)
    if ai_explanation:
        messages.append({"role": "assistant", "content": ai_explanation})
        reasoning_log.append(
            "OpenRouter generated a grounded customer-facing answer from mock itinerary data."
        )
    else:
        messages.append({
            "role": "assistant",
            "content": (
                "I ranked the best itinerary options below. "
                "Pick the one that feels right, and I will continue the booking flow."
            ),
        })

    state["messages"] = messages
    state["reasoning_log"] = reasoning_log
    return state

    options_text = ""
    if ai_explanation:
        options_text += f"{ai_explanation}\n\n"
        reasoning_log.append("OpenRouter generated a grounded customer-facing answer.")

    data_label = "live" if DataClient().using_live_data else "available"
    options_text += f"Here are the {data_label} options I found:\n\n"

    for i, it in enumerate(itineraries):
        activities = ", ".join(a.name for a in it.activities) or "None"
        fallback = " [Exceeds Budget]" if it.is_partial_fallback else ""
        options_text += (
            f"Option {i+1} (Match: {it.match_score:.0%}){fallback}\n"
            f"  Flight: {it.flight.airline} — ${it.flight.price:.2f}\n"
            f"  Hotel:  {it.hotel.name} ({it.hotel.stars}★) — "
            f"${it.hotel.price_per_night:.2f}/night\n"
            f"  Activities: {activities}\n"
            f"  Total: ${it.total_cost:.2f}\n\n"
        )

    messages.append({"role": "assistant", "content": options_text})

    state["messages"] = messages
    state["reasoning_log"] = reasoning_log
    return state


# ── Passenger / payment collection ───────────────────────────────────────────

_COLLECT_FIELDS: list[tuple[str, str, str]] = [
    ("full_name",       "passenger_info", "Passenger's full legal name:"),
    ("passport_number", "passenger_info", "Passport number:"),
    ("date_of_birth",   "passenger_info", "Date of birth (YYYY-MM-DD):"),
    ("email",           "contact_info",   "Contact email address:"),
    ("phone",           "contact_info",   "Phone number (include country code):"),
    ("address",         "contact_info",   "Billing address:"),
    ("card_last4",      "payment_info",   "Last 4 digits of payment card (digits only):"),
    ("cardholder_name", "payment_info",   "Name exactly as shown on card:"),
    ("card_expiry",     "payment_info",   "Card expiry date (MM/YY):"),
]


def _validate_collect_field(field: str, value: str) -> Optional[str]:
    """Returns an error string or None if the value is valid."""
    if field == "date_of_birth":
        try:
            date.fromisoformat(value)
        except ValueError:
            return "Please enter a valid date (YYYY-MM-DD)."

    elif field == "card_last4":
        if not value.isdigit() or len(value) != 4:
            return "Please enter exactly 4 digits."

    elif field == "card_expiry":
        if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", value):
            return "Please enter expiry as MM/YY (e.g. 06/28)."

    return None


def _next_collect_field(
    passenger_info: dict,
    contact_info: dict,
    payment_info: dict,
) -> Optional[tuple[str, str, str]]:
    stores = {
        "passenger_info": passenger_info,
        "contact_info": contact_info,
        "payment_info": payment_info,
    }

    for field, key, prompt in _COLLECT_FIELDS:
        if field not in stores[key]:
            return field, key, prompt

    return None


def collect_passenger_node(state: AgentState) -> AgentState:
    """
    Dynamic collection of passenger, contact, and payment details.

    When OpenRouter is enabled: calls extract_passenger_fields on the user's
    last message. Any fields mentioned naturally are extracted and stored in
    one turn. Then calls generate_conversational_prompt to ask for whatever
    is still missing in a single friendly sentence.

    When OpenRouter is disabled: falls back to the sequential one-field-per-turn
    behaviour with rule-based prompts.

    Advances to phase 'confirm' when all fields are filled.
    """
    messages       = list(state.get("messages", []))
    passenger_info = dict(state.get("passenger_info", {}))
    contact_info   = dict(state.get("contact_info", {}))
    payment_info   = dict(state.get("payment_info", {}))
    reasoning_log  = list(state.get("reasoning_log", []))

    stores = {
        "passenger_info": passenger_info,
        "contact_info": contact_info,
        "payment_info": payment_info,
    }

    last_user: Optional[str] = None
    if messages and messages[-1].get("role") == "user":
        last_user = messages[-1]["content"].strip()

    if last_user:
        extracted = extract_passenger_fields(last_user)

        if extracted:
            stored: list[str] = []

            for field, key, _ in _COLLECT_FIELDS:
                if field not in extracted or field in stores[key]:
                    continue

                value = str(extracted[field]).strip()

                if not _validate_collect_field(field, value):
                    stores[key][field] = value
                    stored.append(field)

            if stored:
                reasoning_log.append(
                    f"LLM extracted passenger fields: {', '.join(stored)}"
                )

        else:
            pending = _next_collect_field(passenger_info, contact_info, payment_info)

            if pending is not None:
                field, key, _ = pending
                error = _validate_collect_field(field, last_user)

                if error:
                    messages.append({"role": "assistant", "content": error})
                    state.update({
                        "messages": messages,
                        "passenger_info": passenger_info,
                        "contact_info": contact_info,
                        "payment_info": payment_info,
                    })
                    return state

                stores[key][field] = last_user

    next_pending = _next_collect_field(passenger_info, contact_info, payment_info)

    if next_pending is None:
        reasoning_log.append("All passenger and payment details collected.")
        state["phase"] = "confirm"

        messages.append({
            "role": "assistant",
            "content": (
                "All details collected. Here's your booking summary:\n\n"
                f"**Passenger:** {passenger_info.get('full_name')} | "
                f"Passport: {passenger_info.get('passport_number')}\n"
                f"**DOB:** {passenger_info.get('date_of_birth')}\n"
                f"**Contact:** {contact_info.get('email')} | {contact_info.get('phone')}\n"
                f"**Address:** {contact_info.get('address')}\n"
                f"**Payment:** **** {payment_info.get('card_last4')} "
                f"(exp {payment_info.get('card_expiry')}) — "
                f"{payment_info.get('cardholder_name')}\n\n"
                "Click **Confirm & Book** to finalize."
            ),
        })

    else:
        missing_names = [
            f for f, k, _ in _COLLECT_FIELDS
            if f not in stores[k]
        ]

        question = generate_conversational_prompt(missing_names, messages)

        if question is None:
            _, _, question = next_pending

        messages.append({"role": "assistant", "content": question})

    state.update({
        "messages": messages,
        "passenger_info": passenger_info,
        "contact_info": contact_info,
        "payment_info": payment_info,
        "reasoning_log": reasoning_log,
    })
    return state


# ── Critic validator ─────────────────────────────────────────────────────────

def critic_validation_node(state: AgentState) -> AgentState:
    """
    Re-validates all collected fields after collection is complete.

    Any field that fails validation is removed and phase is reset to 'collect'
    so the user is asked only for the failing fields again.
    """
    messages       = list(state.get("messages", []))
    passenger_info = dict(state.get("passenger_info", {}))
    contact_info   = dict(state.get("contact_info", {}))
    payment_info   = dict(state.get("payment_info", {}))
    reasoning_log  = list(state.get("reasoning_log", []))

    stores = {
        "passenger_info": passenger_info,
        "contact_info": contact_info,
        "payment_info": payment_info,
    }

    failures: list[tuple[str, str]] = []

    for field, key, _ in _COLLECT_FIELDS:
        value = stores[key].get(field, "")
        error = _validate_collect_field(field, str(value))

        if error:
            failures.append((field, error))
            stores[key].pop(field, None)

    if failures:
        detail = "; ".join(f"{f}: {e}" for f, e in failures)
        reasoning_log.append(f"Critic rejected fields: {detail}")

        messages.append({
            "role": "assistant",
            "content": (
                "Some details didn't pass validation and need to be re-entered:\n"
                + "\n".join(f"- **{f}**: {e}" for f, e in failures)
            ),
        })

        state["phase"] = "collect"

    else:
        reasoning_log.append(
            "Critic validation passed — all passenger/payment fields valid."
        )

    state.update({
        "messages": messages,
        "passenger_info": passenger_info,
        "contact_info": contact_info,
        "payment_info": payment_info,
        "reasoning_log": reasoning_log,
    })
    return state


# ── Confirm & book ────────────────────────────────────────────────────────────

def confirm_node(state: AgentState) -> AgentState:
    """
    Calls the mock server to POST-book each component, assembles a
    BookingConfirmation with the server-issued IDs, and sets phase='done'.
    """
    messages       = list(state.get("messages", []))
    selected       = state.get("selected_itinerary")
    passenger_info = state.get("passenger_info", {})
    contact_info   = state.get("contact_info", {})
    payment_info   = state.get("payment_info", {})
    reasoning_log  = list(state.get("reasoning_log", []))

    if not selected:
        messages.append({"role": "assistant", "content": "No itinerary selected."})
        state["messages"] = messages
        state["phase"] = "done"
        return state

    try:
        passenger = PassengerInfo(
            full_name=passenger_info["full_name"],
            passport_number=passenger_info["passport_number"],
            date_of_birth=date.fromisoformat(passenger_info["date_of_birth"]),
        )

        contact = ContactInfo(**contact_info)
        payment = PaymentInfo(**payment_info)
        client = DataClient()

        reasoning_log.append(
            f"Booking {selected.flight.airline} flight ({selected.flight.id})..."
        )
        flight_bid = client.book_flight(
            selected.flight.id,
            passenger,
            contact,
            payment,
        )
        reasoning_log.append(f"Flight confirmed → {flight_bid}")

        reasoning_log.append(
            f"Booking {selected.hotel.name} ({selected.hotel.id})..."
        )
        hotel_bid = client.book_hotel(
            selected.hotel.id,
            passenger,
            contact,
            payment,
        )
        reasoning_log.append(f"Hotel confirmed → {hotel_bid}")

        activity_bids: list[str] = []

        for activity in selected.activities:
            reasoning_log.append(f"Booking activity: {activity.name}...")
            bid = client.book_activity(
                activity.id,
                passenger,
                contact,
                payment,
            )
            activity_bids.append(bid)
            reasoning_log.append(f"Activity confirmed → {bid}")

        booking = BookingConfirmation(
            booking_id=flight_bid,
            hotel_booking_id=hotel_bid,
            activity_booking_ids=activity_bids,
            itinerary=selected,
            passenger=passenger,
            contact=contact,
        )

        state["booking"] = booking
        state["phase"] = "done"

        activity_lines = "\n".join(
            f"  - Activity: {bid}" for bid in activity_bids
        )

        messages.append({
            "role": "assistant",
            "content": (
                "Your trip is confirmed!\n\n"
                f"  - Flight: {flight_bid}\n"
                f"  - Hotel:  {hotel_bid}\n"
                f"{activity_lines}\n\n"
                f"Total charged: ${selected.total_cost:.2f} "
                f"to card ending in {payment_info.get('card_last4', '????')}. "
                f"Safe travels, {passenger_info.get('full_name', 'traveller')}!"
            ),
        })

        reasoning_log.append(
            f"All bookings confirmed. Master reference: {flight_bid}."
        )

    except ConnectionError as e:
        messages.append({"role": "assistant", "content": str(e)})

    except Exception as e:
        messages.append({"role": "assistant", "content": f"Booking error: {e}"})

    state["messages"] = messages
    state["reasoning_log"] = reasoning_log
    return state


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    """
    Graph entry point is a router node that dispatches by phase.

    Flow:
      onboard → plan → rank → END
      collect → critic → END
      confirm → END
    """
    g = StateGraph(AgentState)

    g.add_node("router", lambda s: s)
    g.add_node("onboard", onboard_node)
    g.add_node("plan", plan_node)
    g.add_node("rank", rank_node)
    g.add_node("collect_passenger", collect_passenger_node)
    g.add_node("critic", critic_validation_node)
    g.add_node("confirm", confirm_node)

    g.set_entry_point("router")

    def _dispatch(s: AgentState) -> str:
        phase = s.get("phase", "onboard")

        if phase == "collect":
            return "collect"

        if phase == "confirm":
            return "confirm"

        if phase == "plan":
            return "plan"

        if phase in {"rank", "done"}:
            return END

        return "onboard"

    g.add_conditional_edges(
        "router",
        _dispatch,
        {
            "collect": "collect_passenger",
            "confirm": "confirm",
            "plan": "plan",
            "onboard": "onboard",
            END: END,
        },
    )

    g.add_conditional_edges(
        "onboard",
        lambda s: "plan" if s.get("agent_status") == "APPROVED" else END,
        {
            "plan": "plan",
            END: END,
        },
    )

    g.add_edge("plan", "rank")
    g.add_edge("rank", END)

    g.add_conditional_edges(
        "collect_passenger",
        lambda s: "critic" if s.get("phase") == "confirm" else END,
        {
            "critic": "critic",
            END: END,
        },
    )

    g.add_edge("critic", END)
    g.add_edge("confirm", END)

    return g.compile()
