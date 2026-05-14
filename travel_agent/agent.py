from __future__ import annotations

import uuid
from datetime import date
from typing import Optional, TypedDict

try:
    from .models import BookingConfirmation, Itinerary, TravelRequest
    from .data_client import DataClient
    from .planner import aggregate_itinerary_tags, compute_raw_score, normalize_scores, run_planning_loop
except ImportError:
    from models import BookingConfirmation, Itinerary, TravelRequest
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
    phase:              str   # "onboard" | "plan" | "rank" | "confirm" | "done"


# ── Onboarding ────────────────────────────────────────────────────────────────

_FIELD_ORDER = ["destination", "departure_date", "return_date", "budget", "travel_style"]

_QUESTIONS = {
    "destination":    "What is your destination? (Tokyo, Paris, Bali, New York)",
    "departure_date": "What is your departure date? (YYYY-MM-DD)",
    "return_date":    "What is your return date? (YYYY-MM-DD)",
    "budget":         "What is your total budget in USD?",
    "travel_style":   "What travel styles do you prefer? (e.g. adventure, culture, luxury)",
}


def _validate_and_store(field: str, value: str, tr: dict) -> Optional[str]:
    """Store validated value in tr. Returns an error message string, or None on success."""
    if field == "budget":
        try:
            budget = float(value.replace("$", "").replace(",", ""))
            if budget <= 0:
                return "Please enter a positive number for your budget."
            tr["budget"] = budget
        except ValueError:
            return "Please enter a valid number for your budget."
    elif field == "departure_date":
        try:
            date.fromisoformat(value)
            tr["departure_date"] = value
        except ValueError:
            return "Please enter a valid date (YYYY-MM-DD)."
    elif field == "return_date":
        try:
            ret = date.fromisoformat(value)
            dep = date.fromisoformat(tr["departure_date"])
            if ret <= dep:
                return "Return date must be after departure date."
            tr["return_date"] = value
        except ValueError:
            return "Please enter a valid date (YYYY-MM-DD)."
    else:
        tr[field] = value
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
            error = _validate_and_store(next_field, last_user, tr)
            if error:
                messages.append({"role": "assistant", "content": error})
                state["messages"] = messages
                state["travel_request"] = tr
                return state
            next_field = next((f for f in _FIELD_ORDER if f not in tr), None)
        else:
            # All fields filled — this message is the yes/no confirmation
            if last_user.lower() in ("yes", "y", "confirm", "ok"):
                return _build_confirmed_request(state, messages, tr)
            elif last_user.lower() in ("no", "n"):
                tr = {}
                messages.append({"role": "assistant", "content": "No problem! Where would you like to travel? (Tokyo, Paris, Bali, New York)"})
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
        # On the very first invocation (no messages yet), prepend a greeting
        if not messages and next_field == "destination":
            messages.append({
                "role": "assistant",
                "content": (
                    "Hello! I'm your travel planning assistant. "
                    "I'll help you build the perfect itinerary.\n\n"
                    + _QUESTIONS["destination"]
                ),
            })
        else:
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


# ── Confirm & book ────────────────────────────────────────────────────────────

def confirm_node(state: AgentState) -> AgentState:
    """
    Displays an order summary, generates a UUID v4 as the BookingID,
    stores a BookingConfirmation in state, and sets phase='done'.

    Requirements: 6.3, 6.4, 6.5, 6.6
    """
    messages      = list(state.get("messages", []))
    selected      = state.get("selected_itinerary")
    reasoning_log = list(state.get("reasoning_log", []))

    if not selected:
        messages.append({"role": "assistant", "content": "No itinerary selected."})
        state["messages"] = messages
        state["phase"] = "done"
        return state

    # Req 6.4: generate UUID v4 locally as the BookingID
    booking_id = str(uuid.uuid4())
    reasoning_log.append(f"Generated BookingID: {booking_id}")

    # Req 6.5: store BookingConfirmation in state
    booking = BookingConfirmation(
        booking_id=booking_id,
        itinerary=selected,
    )
    state["booking"] = booking

    # Req 6.6: set phase to "done"
    state["phase"] = "done"

    # Req 6.3: display order summary with BookingID
    activities_text = (
        "\n".join(f"    • {a.name} (${a.price:.2f})" for a in selected.activities)
        if selected.activities else "    • None"
    )
    messages.append({
        "role": "assistant",
        "content": (
            "✅ Your trip is confirmed!\n\n"
            "**Booking Summary**\n"
            f"  ✈️  Flight:  {selected.flight.airline} — ${selected.flight.price:.2f}\n"
            f"  🏨  Hotel:   {selected.hotel.name} ({selected.hotel.stars}★) — ${selected.hotel.price_per_night:.2f}/night\n"
            f"  🎯  Activities:\n{activities_text}\n"
            f"  💰  Total:   ${selected.total_cost:.2f}\n\n"
            f"**Booking ID: {booking_id}**\n\n"
            "Safe travels!"
        ),
    })
    reasoning_log.append(f"Booking confirmed. BookingID: {booking_id}.")

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
      confirm  → END               (booking complete)
    """
    g = StateGraph(AgentState)

    g.add_node("router",  lambda s: s)  # pass-through dispatcher
    g.add_node("onboard", onboard_node)
    g.add_node("plan",    plan_node)
    g.add_node("rank",    rank_node)
    g.add_node("confirm", confirm_node)

    g.set_entry_point("router")

    # Route to the correct node based on current phase
    def _dispatch(s: AgentState) -> str:
        phase = s.get("phase", "onboard")
        if phase == "confirm":
            return "confirm"
        return "onboard"

    g.add_conditional_edges(
        "router",
        _dispatch,
        {"confirm": "confirm", "onboard": "onboard"},
    )

    # After onboard: proceed to plan only when user confirmed the request
    g.add_conditional_edges(
        "onboard",
        lambda s: "plan" if s.get("confirmed_request") else END,
        {"plan": "plan", END: END},
    )

    g.add_edge("plan",    "rank")
    g.add_edge("rank",    END)
    g.add_edge("confirm", END)

    return g.compile()
