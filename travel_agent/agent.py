from typing import TypedDict, Optional
from datetime import date
import uuid

try:
    from .models import TravelRequest, Itinerary, BookingConfirmation
    from .data_client import DataClient
    from .planner import run_planning_loop, normalize_scores, aggregate_itinerary_tags, compute_raw_score
except ImportError:
    from models import TravelRequest, Itinerary, BookingConfirmation
    from data_client import DataClient
    from planner import run_planning_loop, normalize_scores, aggregate_itinerary_tags, compute_raw_score

from langgraph.graph import StateGraph, END


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


# ── onboarding helpers ────────────────────────────────────────────────────────

_FIELD_ORDER = ["destination", "departure_date", "return_date", "budget", "travel_style"]

_QUESTIONS = {
    "destination":    "What is your destination? (Tokyo, Paris, Bali, New York)",
    "departure_date": "What is your departure date? (YYYY-MM-DD)",
    "return_date":    "What is your return date? (YYYY-MM-DD)",
    "budget":         "What is your total budget in USD?",
    "travel_style":   "What travel styles do you prefer? (comma-separated, e.g. adventure, culture, luxury)",
}


def _validate_and_store(field: str, value: str, travel_request: dict) -> Optional[str]:
    """Store value in travel_request. Returns an error string or None on success."""
    if field == "budget":
        try:
            budget = float(value.replace("$", "").replace(",", ""))
            if budget <= 0:
                return "Please enter a positive number for your budget."
            travel_request["budget"] = budget
        except ValueError:
            return "Please enter a valid number for your budget."

    elif field == "departure_date":
        try:
            date.fromisoformat(value)
            travel_request["departure_date"] = value
        except ValueError:
            return "Please enter a valid date (YYYY-MM-DD)."

    elif field == "return_date":
        try:
            ret = date.fromisoformat(value)
            dep = date.fromisoformat(travel_request["departure_date"])
            if ret <= dep:
                return "Return date must be after departure date. Please re-enter."
            travel_request["return_date"] = value
        except ValueError:
            return "Please enter a valid date (YYYY-MM-DD)."

    else:  # destination, travel_style
        travel_request[field] = value

    return None


def _build_confirmed_request(state: AgentState, messages: list, travel_request: dict) -> AgentState:
    """Parse travel_request into a TravelRequest and advance to plan phase."""
    try:
        style_raw = travel_request.get("travel_style", "")
        travel_style = (
            [t.strip() for t in style_raw.split(",") if t.strip()]
            if isinstance(style_raw, str) else style_raw
        )
        confirmed = TravelRequest(
            destination=travel_request["destination"],
            departure_date=date.fromisoformat(travel_request["departure_date"]),
            return_date=date.fromisoformat(travel_request["return_date"]),
            budget=float(travel_request["budget"]),
            travel_style=travel_style,
        )
        state["confirmed_request"] = confirmed
        state["phase"] = "plan"
        messages.append({
            "role": "assistant",
            "content": (
                f"Planning your trip to {confirmed.destination}...\n"
                f"Dates: {confirmed.departure_date} to {confirmed.return_date} | "
                f"Budget: ${confirmed.budget:.0f} | Style: {', '.join(confirmed.travel_style)}"
            ),
        })
    except Exception as e:
        messages.append({"role": "assistant", "content": f"Validation error: {e}. Please check your inputs."})

    state["messages"] = messages
    state["travel_request"] = travel_request
    return state


def _summary_text(tr: dict) -> str:
    return (
        f"Here is your trip summary:\n"
        f"- Destination: {tr['destination']}\n"
        f"- Dates: {tr['departure_date']} to {tr['return_date']}\n"
        f"- Budget: ${float(tr['budget']):.0f}\n"
        f"- Style: {tr['travel_style']}\n\n"
        f"Shall I proceed with planning? (yes / no)"
    )


# ── nodes ─────────────────────────────────────────────────────────────────────

def onboard_node(state: AgentState) -> AgentState:
    """
    Sequential onboarding: destination → departure_date → return_date → budget → travel_style → confirm.

    Called once per graph.invoke(). Reads the latest user message (if any),
    stores the answer for the current field, then asks the next question or
    shows the confirmation prompt. Routing to END after each call means the
    graph stops and waits for the next user message — no infinite loop.
    """
    messages = list(state.get("messages", []))
    travel_request = dict(state.get("travel_request", {}))

    last_user_msg: Optional[str] = None
    if messages and messages[-1].get("role") == "user":
        last_user_msg = messages[-1]["content"].strip()

    next_field = next((f for f in _FIELD_ORDER if f not in travel_request), None)

    if last_user_msg is not None:
        if next_field is not None:
            # Store the answer for the current field
            error = _validate_and_store(next_field, last_user_msg, travel_request)
            if error:
                messages.append({"role": "assistant", "content": error})
                state["messages"] = messages
                state["travel_request"] = travel_request
                return state
            # Recalculate after storage
            next_field = next((f for f in _FIELD_ORDER if f not in travel_request), None)

        else:
            # All fields already filled — this message is the confirmation response
            if last_user_msg.lower() in ("yes", "y", "confirm", "ok"):
                return _build_confirmed_request(state, messages, travel_request)
            elif last_user_msg.lower() in ("no", "n"):
                travel_request = {}
                messages.append({
                    "role": "assistant",
                    "content": "No problem! Let's start over. Where would you like to travel? (Tokyo, Paris, Bali, New York)",
                })
                state["messages"] = messages
                state["travel_request"] = travel_request
                state["phase"] = "onboard"
                return state
            else:
                messages.append({"role": "assistant", "content": "Please type 'yes' to confirm or 'no' to start over."})
                state["messages"] = messages
                state["travel_request"] = travel_request
                state["phase"] = "onboard"
                return state

    # ── decide what to say next ───────────────────────────────────────────────
    if next_field is not None:
        messages.append({"role": "assistant", "content": _QUESTIONS[next_field]})
    else:
        # All fields filled
        if last_user_msg is not None:
            # We just stored the last field → show summary and ask for confirmation
            messages.append({"role": "assistant", "content": _summary_text(travel_request)})
        else:
            # No user message and all fields already set (e.g. test isolation) → auto-confirm
            return _build_confirmed_request(state, messages, travel_request)

    state["messages"] = messages
    state["travel_request"] = travel_request
    state["phase"] = "onboard"
    return state


def plan_node(state: AgentState) -> AgentState:
    messages = list(state.get("messages", []))
    confirmed_request = state.get("confirmed_request")
    reasoning_log = list(state.get("reasoning_log", []))

    if not confirmed_request:
        messages.append({"role": "assistant", "content": "No confirmed request. Please complete onboarding first."})
        state["messages"] = messages
        return state

    try:
        itineraries = run_planning_loop(confirmed_request, DataClient(), reasoning_log)
        state["itineraries"] = itineraries
        state["reasoning_log"] = reasoning_log
        state["phase"] = "rank"
        if itineraries:
            messages.append({"role": "assistant", "content": f"Found {len(itineraries)} itinerary option(s). Analyzing..."})
        else:
            messages.append({"role": "assistant", "content": "No itineraries found. Please try a higher budget."})
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
    confirmed_request = state.get("confirmed_request")
    reasoning_log = list(state.get("reasoning_log", []))

    if not itineraries or not confirmed_request:
        state["phase"] = "rank"
        return state

    # Always (re-)score — idempotent and cheap
    raw_scores = [
        compute_raw_score(aggregate_itinerary_tags(it), confirmed_request.travel_style)
        for it in itineraries
    ]
    normalized = normalize_scores(raw_scores)
    for it, score in zip(itineraries, normalized):
        it.match_score = score

    itineraries.sort(key=lambda it: it.match_score, reverse=True)
    itineraries = itineraries[:3]

    # Append trade-off analysis only once
    if not any("Trade-off Analysis" in e for e in reasoning_log):
        reasoning_log.append("Trade-off Analysis:")
        for i, it in enumerate(itineraries):
            reasoning_log.append(
                f"  Option {i+1}: {it.flight.airline} + {it.hotel.name} "
                f"(Match: {it.match_score:.2f}, Cost: ${it.total_cost:.2f})"
            )

    state["itineraries"] = itineraries
    state["reasoning_log"] = reasoning_log
    state["phase"] = "rank"

    options_text = "Here are your top options:\n\n"
    for i, it in enumerate(itineraries):
        activity_names = ", ".join(a.name for a in it.activities) or "None"
        fallback = " [Exceeds Budget]" if it.is_partial_fallback else ""
        options_text += (
            f"Option {i+1} (Match: {it.match_score:.0%}){fallback}\n"
            f"  Flight: {it.flight.airline} — ${it.flight.price:.2f}\n"
            f"  Hotel:  {it.hotel.name} ({it.hotel.stars} stars) — ${it.hotel.price_per_night:.2f}/night\n"
            f"  Activities: {activity_names}\n"
            f"  Total: ${it.total_cost:.2f}\n\n"
        )
    messages.append({"role": "assistant", "content": options_text})
    state["messages"] = messages
    return state


def confirm_node(state: AgentState) -> AgentState:
    messages = list(state.get("messages", []))
    selected = state.get("selected_itinerary")

    if not selected:
        messages.append({"role": "assistant", "content": "No itinerary selected."})
        state["messages"] = messages
        state["phase"] = "done"
        return state

    booking_id = str(uuid.uuid4())
    state["booking"] = BookingConfirmation(booking_id=booking_id, itinerary=selected)
    state["phase"] = "done"
    messages.append({
        "role": "assistant",
        "content": (
            f"Booking confirmed! Your Booking ID is: {booking_id}\n"
            f"Flight: {selected.flight.airline} — ${selected.flight.price:.2f}\n"
            f"Hotel:  {selected.hotel.name} — ${selected.hotel.price_per_night:.2f}/night\n"
            f"Total:  ${selected.total_cost:.2f}"
        ),
    })
    state["messages"] = messages
    return state


# ── graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    """
    Build the travel planning state machine.

    Each node runs once per graph.invoke() call and routes to END when it
    needs more user input — no self-loops, no recursion errors.

    Flow:
      onboard → END  (waiting for next user message)
      onboard → plan → rank → END  (after confirmation, until itinerary selected)
      onboard → plan → rank → confirm → END  (full booking flow)
    """
    g = StateGraph(AgentState)
    g.add_node("onboard", onboard_node)
    g.add_node("plan",    plan_node)
    g.add_node("rank",    rank_node)
    g.add_node("confirm", confirm_node)

    g.set_entry_point("onboard")

    # After onboard: go to plan only when confirmed_request is set; otherwise stop
    g.add_conditional_edges(
        "onboard",
        lambda s: "plan" if s.get("confirmed_request") else END,
        {"plan": "plan", END: END},
    )

    # plan always proceeds to rank
    g.add_edge("plan", "rank")

    # After rank: go to confirm only when itinerary selected; otherwise stop
    g.add_conditional_edges(
        "rank",
        lambda s: "confirm" if s.get("selected_itinerary") else END,
        {"confirm": "confirm", END: END},
    )

    g.add_edge("confirm", END)

    return g.compile()
