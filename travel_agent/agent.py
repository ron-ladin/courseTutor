from __future__ import annotations

import re
from datetime import date
from typing import Optional, TypedDict

try:
    from .models import BookingConfirmation, ContactInfo, Itinerary, PassengerInfo, PaymentInfo, TravelRequest
    from .data_client import DataClient
    from .planner import aggregate_itinerary_tags, compute_raw_score, normalize_scores, run_planning_loop
except ImportError:
    from models import BookingConfirmation, ContactInfo, Itinerary, PassengerInfo, PaymentInfo, TravelRequest
    from data_client import DataClient
    from planner import aggregate_itinerary_tags, compute_raw_score, normalize_scores, run_planning_loop

from langgraph.graph import END, StateGraph


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
    passenger_info:     dict  # full_name, passport_number, date_of_birth
    contact_info:       dict  # email, phone, address
    payment_info:       dict  # card_last4, cardholder_name, card_expiry


# ── Onboarding ────────────────────────────────────────────────────────────────

_FIELD_ORDER = ["destination", "departure_date", "return_date", "budget", "travel_style"]

_VALID_DESTINATIONS = ["Tokyo", "Paris", "Bali", "New York"]
_VALID_STYLES = ["adventure", "culture", "luxury", "romance", "nature", "food", "budget"]

_QUESTIONS = {
    "destination":    f"What is your destination? Available: {', '.join(_VALID_DESTINATIONS)}",
    "departure_date": "What is your departure date? (YYYY-MM-DD)",
    "return_date":    "What is your return date? (YYYY-MM-DD)",
    "budget":         "What is your total budget in USD?",
    "travel_style":   f"What travel styles do you prefer? Choose from: {', '.join(_VALID_STYLES)} (comma-separated)",
}

_ACK = {
    "destination":    lambda tr: f"Great, {tr['destination']}! ",
    "departure_date": lambda tr: f"Departing on {tr['departure_date']}. ",
    "return_date":    lambda tr: f"Returning on {tr['return_date']}. ",
    "budget":         lambda tr: f"Budget: ${float(tr['budget']):.0f}. ",
    "travel_style":   lambda tr: f"Style: {tr['travel_style']}. ",
}


def _validate_and_store(field: str, value: str, tr: dict) -> Optional[str]:
    """Validate and store value in tr. Returns an error message string, or None on success."""
    if field == "destination":
        match = next((d for d in _VALID_DESTINATIONS if d.lower() == value.strip().lower()), None)
        if not match:
            return (
                f"'{value.strip()}' isn't available. "
                f"Please choose from: {', '.join(_VALID_DESTINATIONS)}."
            )
        tr["destination"] = match

    elif field == "travel_style":
        styles = [s.strip().lower() for s in value.split(",") if s.strip()]
        if not styles:
            return f"Please enter at least one style from: {', '.join(_VALID_STYLES)}."
        unknown = [s for s in styles if s not in _VALID_STYLES]
        if unknown:
            return (
                f"Unknown style(s): {', '.join(unknown)}. "
                f"Please choose from: {', '.join(_VALID_STYLES)}."
            )
        tr["travel_style"] = ", ".join(styles)

    elif field == "budget":
        try:
            budget = float(value.replace("$", "").replace(",", ""))
            if budget <= 0:
                return "Please enter a positive number for your budget."
            tr["budget"] = budget
        except ValueError:
            return "Please enter a valid number for your budget (e.g. 2000)."

    elif field == "departure_date":
        try:
            date.fromisoformat(value.strip())
            tr["departure_date"] = value.strip()
        except ValueError:
            return "Please enter a valid date in YYYY-MM-DD format (e.g. 2025-06-01)."

    elif field == "return_date":
        try:
            ret = date.fromisoformat(value.strip())
            dep = date.fromisoformat(tr["departure_date"])
            if ret <= dep:
                return f"Return date must be after {tr['departure_date']}. Please re-enter."
            tr["return_date"] = value.strip()
        except ValueError:
            return "Please enter a valid date in YYYY-MM-DD format (e.g. 2025-06-08)."

    return None


def _summary_text(tr: dict) -> str:
    return (
        f"Here is your trip summary:\n"
        f"- Destination: {tr['destination']}\n"
        f"- Dates: {tr['departure_date']} → {tr['return_date']}\n"
        f"- Budget: ${float(tr['budget']):.0f}\n"
        f"- Style: {tr['travel_style']}\n\n"
        "Shall I proceed with planning? (yes / no)"
    )


def _build_confirmed_request(state: AgentState, messages: list, tr: dict) -> AgentState:
    try:
        style_raw = tr.get("travel_style", "")
        travel_style = (
            [t.strip() for t in style_raw.split(",") if t.strip()]
            if isinstance(style_raw, str) else style_raw
        )
        confirmed = TravelRequest(
            destination=tr["destination"],
            departure_date=date.fromisoformat(tr["departure_date"]),
            return_date=date.fromisoformat(tr["return_date"]),
            budget=float(tr["budget"]),
            travel_style=travel_style,
        )
        state["confirmed_request"] = confirmed
        state["phase"] = "plan"
        messages.append({
            "role": "assistant",
            "content": (
                f"Planning your trip to {confirmed.destination}...\n"
                f"Dates: {confirmed.departure_date} → {confirmed.return_date} | "
                f"Budget: ${confirmed.budget:.0f} | Style: {', '.join(confirmed.travel_style)}"
            ),
        })
    except Exception as e:
        messages.append({"role": "assistant", "content": f"Validation error: {e}. Please check your inputs."})
    state["messages"] = messages
    state["travel_request"] = tr
    return state


def onboard_node(state: AgentState) -> AgentState:
    """
    Sequential onboarding: one field per graph.invoke() call.
    Reads the latest user message, validates + stores the answer, then asks
    the next question or shows the confirmation prompt.
    """
    messages = list(state.get("messages", []))
    tr = dict(state.get("travel_request", {}))

    last_user: Optional[str] = None
    if messages and messages[-1].get("role") == "user":
        last_user = messages[-1]["content"].strip()

    next_field = next((f for f in _FIELD_ORDER if f not in tr), None)

    if last_user is not None:
        if next_field is not None:
            stored_field = next_field
            error = _validate_and_store(next_field, last_user, tr)
            if error:
                messages.append({"role": "assistant", "content": error})
                state["messages"] = messages
                state["travel_request"] = tr
                return state
            next_field = next((f for f in _FIELD_ORDER if f not in tr), None)
            # Acknowledge the stored answer, then ask next question or show summary
            ack = _ACK[stored_field](tr)
            if next_field is not None:
                messages.append({"role": "assistant", "content": ack + _QUESTIONS[next_field]})
            else:
                messages.append({"role": "assistant", "content": ack + "\n\n" + _summary_text(tr)})
            state["messages"] = messages
            state["travel_request"] = tr
            state["phase"] = "onboard"
            return state
        else:
            # All fields filled — this message is the yes/no confirmation
            if last_user.lower() in ("yes", "y", "confirm", "ok"):
                return _build_confirmed_request(state, messages, tr)
            elif last_user.lower() in ("no", "n"):
                tr = {}
                messages.append({"role": "assistant", "content": "No problem! Let's start over.\n\n" + _QUESTIONS["destination"]})
                state["messages"] = messages
                state["travel_request"] = tr
                state["phase"] = "onboard"
                return state
            else:
                messages.append({"role": "assistant", "content": "Please type 'yes' to confirm or 'no' to start over."})
                state["messages"] = messages
                state["travel_request"] = tr
                state["phase"] = "onboard"
                return state

    if next_field is not None:
        messages.append({"role": "assistant", "content": _QUESTIONS[next_field]})
    else:
        if last_user is not None:
            messages.append({"role": "assistant", "content": _summary_text(tr)})
        else:
            return _build_confirmed_request(state, messages, tr)

    state["messages"] = messages
    state["travel_request"] = tr
    state["phase"] = "onboard"
    return state


# ── Plan & Rank ───────────────────────────────────────────────────────────────

def plan_node(state: AgentState) -> AgentState:
    messages = list(state.get("messages", []))
    confirmed = state.get("confirmed_request")
    reasoning_log = list(state.get("reasoning_log", []))

    if not confirmed:
        messages.append({"role": "assistant", "content": "No confirmed request. Please complete onboarding first."})
        state["messages"] = messages
        return state

    try:
        itineraries = run_planning_loop(confirmed, DataClient(), reasoning_log)
        state["itineraries"] = itineraries
        state["reasoning_log"] = reasoning_log
        state["phase"] = "rank"
        msg = (
            f"Found {len(itineraries)} itinerary option(s). Analyzing..."
            if itineraries else
            "No itineraries found. Please try a higher budget."
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

    options_text = "Here are your top options:\n\n"
    for i, it in enumerate(itineraries):
        activities = ", ".join(a.name for a in it.activities) or "None"
        fallback = " [Exceeds Budget]" if it.is_partial_fallback else ""
        options_text += (
            f"Option {i+1} (Match: {it.match_score:.0%}){fallback}\n"
            f"  Flight: {it.flight.airline} — ${it.flight.price:.2f}\n"
            f"  Hotel:  {it.hotel.name} ({it.hotel.stars}★) — ${it.hotel.price_per_night:.2f}/night\n"
            f"  Activities: {activities}\n"
            f"  Total: ${it.total_cost:.2f}\n\n"
        )
    messages.append({"role": "assistant", "content": options_text})
    state["messages"] = messages
    return state


# ── Passenger / payment collection ───────────────────────────────────────────

# Each tuple: (field_name, state_dict_key, question_prompt)
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
    stores = {"passenger_info": passenger_info, "contact_info": contact_info, "payment_info": payment_info}
    for field, key, prompt in _COLLECT_FIELDS:
        if field not in stores[key]:
            return field, key, prompt
    return None


def collect_passenger_node(state: AgentState) -> AgentState:
    """
    Sequential collection of passenger, contact, and payment details.
    One field per graph.invoke() call, with inline validation.
    Advances to phase 'confirm' when all 9 fields are collected.
    """
    messages      = list(state.get("messages", []))
    passenger_info = dict(state.get("passenger_info", {}))
    contact_info   = dict(state.get("contact_info",   {}))
    payment_info   = dict(state.get("payment_info",   {}))
    reasoning_log  = list(state.get("reasoning_log",  []))

    stores = {
        "passenger_info": passenger_info,
        "contact_info":   contact_info,
        "payment_info":   payment_info,
    }

    last_user: Optional[str] = None
    if messages and messages[-1].get("role") == "user":
        last_user = messages[-1]["content"].strip()

    if last_user is not None:
        pending = _next_collect_field(passenger_info, contact_info, payment_info)
        if pending is not None:
            field, key, _ = pending
            error = _validate_collect_field(field, last_user)
            if error:
                messages.append({"role": "assistant", "content": error})
                state.update({"messages": messages, "passenger_info": passenger_info,
                               "contact_info": contact_info, "payment_info": payment_info})
                return state
            stores[key][field] = last_user

    next_field = _next_collect_field(passenger_info, contact_info, payment_info)

    if next_field is not None:
        _, _, prompt = next_field
        messages.append({"role": "assistant", "content": prompt})
    else:
        # All collected — show summary and advance to confirm
        reasoning_log.append("All passenger and payment details collected.")
        state["phase"] = "confirm"
        messages.append({
            "role": "assistant",
            "content": (
                "All details collected. Here's your booking summary:\n\n"
                f"**Passenger:** {passenger_info.get('full_name')} | Passport: {passenger_info.get('passport_number')}\n"
                f"**DOB:** {passenger_info.get('date_of_birth')}\n"
                f"**Contact:** {contact_info.get('email')} | {contact_info.get('phone')}\n"
                f"**Address:** {contact_info.get('address')}\n"
                f"**Payment:** **** {payment_info.get('card_last4')} (exp {payment_info.get('card_expiry')}) — {payment_info.get('cardholder_name')}\n\n"
                "Click **Confirm & Book** to finalize."
            ),
        })

    state.update({
        "messages":      messages,
        "passenger_info": passenger_info,
        "contact_info":   contact_info,
        "payment_info":   payment_info,
        "reasoning_log":  reasoning_log,
    })
    return state


# ── Confirm & book ────────────────────────────────────────────────────────────

def confirm_node(state: AgentState) -> AgentState:
    """
    Calls the mock server to POST-book each component (flight, hotel, activities),
    assembles a BookingConfirmation with the server-issued IDs, and sets phase='done'.
    """
    messages       = list(state.get("messages", []))
    selected       = state.get("selected_itinerary")
    passenger_info = state.get("passenger_info", {})
    contact_info   = state.get("contact_info",   {})
    payment_info   = state.get("payment_info",   {})
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
        client  = DataClient()

        reasoning_log.append(f"Booking {selected.flight.airline} flight ({selected.flight.id})...")
        flight_bid = client.book_flight(selected.flight.id, passenger, contact, payment)
        reasoning_log.append(f"Flight confirmed → {flight_bid}")

        reasoning_log.append(f"Booking {selected.hotel.name} ({selected.hotel.id})...")
        hotel_bid = client.book_hotel(selected.hotel.id, passenger, contact, payment)
        reasoning_log.append(f"Hotel confirmed → {hotel_bid}")

        activity_bids: list[str] = []
        for activity in selected.activities:
            reasoning_log.append(f"Booking activity: {activity.name}...")
            bid = client.book_activity(activity.id, passenger, contact, payment)
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
        state["phase"]   = "done"

        activity_lines = "\n".join(f"  - Activity: {bid}" for bid in activity_bids)
        messages.append({
            "role": "assistant",
            "content": (
                f"Your trip is confirmed!\n\n"
                f"  - Flight: {flight_bid}\n"
                f"  - Hotel:  {hotel_bid}\n"
                f"{activity_lines}\n\n"
                f"Total charged: ${selected.total_cost:.2f} to card ending in {payment_info.get('card_last4', '????')}. "
                f"Safe travels, {passenger_info.get('full_name', 'traveller')}!"
            ),
        })
        reasoning_log.append(f"All bookings confirmed. Master reference: {flight_bid}.")

    except ConnectionError as e:
        messages.append({"role": "assistant", "content": str(e)})
    except Exception as e:
        messages.append({"role": "assistant", "content": f"Booking error: {e}"})

    state["messages"]      = messages
    state["reasoning_log"] = reasoning_log
    return state


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    """
    Graph entry point is a router node that dispatches by phase so that
    every graph.invoke() resumes at exactly the right node rather than
    always re-entering onboarding.

    Flow:
      onboard  → plan → rank → END  (wait for user to select option)
      collect  → END               (wait for next passenger-detail answer)
      confirm  → END               (booking complete)
    """
    g = StateGraph(AgentState)

    g.add_node("router",            lambda s: s)  # pass-through dispatcher
    g.add_node("onboard",           onboard_node)
    g.add_node("plan",              plan_node)
    g.add_node("rank",              rank_node)
    g.add_node("collect_passenger", collect_passenger_node)
    g.add_node("confirm",           confirm_node)

    g.set_entry_point("router")

    # Route to the correct node based on current phase
    def _dispatch(s: AgentState) -> str:
        phase = s.get("phase", "onboard")
        if phase == "collect":
            return "collect"
        if phase == "confirm":
            return "confirm"
        return "onboard"

    g.add_conditional_edges(
        "router",
        _dispatch,
        {"collect": "collect_passenger", "confirm": "confirm", "onboard": "onboard"},
    )

    # After onboard: proceed to plan only when user confirmed the request
    g.add_conditional_edges(
        "onboard",
        lambda s: "plan" if s.get("confirmed_request") else END,
        {"plan": "plan", END: END},
    )

    g.add_edge("plan", "rank")
    g.add_edge("rank",              END)
    g.add_edge("collect_passenger", END)
    g.add_edge("confirm",           END)

    return g.compile()
