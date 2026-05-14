from typing import TypedDict, Optional, Any
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
    """State TypedDict for the travel planning agent."""
    messages: list[dict]
    travel_request: dict
    confirmed_request: Optional[TravelRequest]
    itineraries: list[Itinerary]
    selected_itinerary: Optional[Itinerary]
    booking: Optional[BookingConfirmation]
    reasoning_log: list[str]
    backtrack_count: int
    phase: str  # "onboard" | "plan" | "rank" | "confirm" | "done"


# ============================================================================
# Onboarding Node (Task 7.2)
# ============================================================================

def onboard_node(state: AgentState) -> AgentState:
    """
    Sequential onboarding with one question at a time.
    Order: destination → departure_date → return_date → budget → travel_style
    
    Handles user input from the latest message if present.
    """
    messages = state.get("messages", [])
    travel_request = state.get("travel_request", {})
    
    # Extract user input from the latest message if it's from user
    if messages and messages[-1].get("role") == "user":
        latest_input = messages[-1].get("content", "").strip()
        
        # Determine which field to populate based on what's already answered
        questions = [
            "destination",
            "departure_date",
            "return_date",
            "budget",
            "travel_style",
        ]
        
        answered_count = sum(1 for q in questions if q in travel_request)
        if answered_count < len(questions):
            field = questions[answered_count]
            
            # Validate input
            if field == "budget":
                try:
                    travel_request["budget"] = float(latest_input)
                except ValueError:
                    messages.append({"role": "assistant", "content": "Please enter a valid number for budget."})
                    state["messages"] = messages
                    state["phase"] = "onboard"
                    return state
            elif field in ("departure_date", "return_date"):
                try:
                    date.fromisoformat(latest_input)
                    travel_request[field] = latest_input
                except ValueError:
                    messages.append({"role": "assistant", "content": f"Please enter a valid date (YYYY-MM-DD)."})
                    state["messages"] = messages
                    state["phase"] = "onboard"
                    return state
            else:
                travel_request[field] = latest_input
    
    # Determine which question to ask based on what's been answered
    questions = [
        ("destination", "What's your travel destination?"),
        ("departure_date", "When do you want to depart? (YYYY-MM-DD)"),
        ("return_date", "When do you want to return? (YYYY-MM-DD)"),
        ("budget", "What's your budget in USD?"),
        ("travel_style", "What's your travel style? (comma-separated tags, e.g., 'luxury, adventure')"),
    ]
    
    # Find the first unanswered question
    for field, question in questions:
        if field not in travel_request:
            messages.append({"role": "assistant", "content": question})
            state["messages"] = messages
            state["phase"] = "onboard"
            return state
    
    # All questions answered — validate and build TravelRequest
    try:
        # Handle confirmation (check if last user message is "yes")
        if messages and messages[-1].get("role") == "user":
            user_confirmation = messages[-1].get("content", "").strip().lower()
            if user_confirmation not in ("yes", "y", "confirm", "ok"):
                messages.append({"role": "assistant", "content": "Please confirm with 'yes' to proceed."})
                state["messages"] = messages
                state["phase"] = "onboard"
                return state
        
        # Parse travel_style if it's a string
        travel_style = travel_request.get("travel_style", [])
        if isinstance(travel_style, str):
            travel_style = [tag.strip() for tag in travel_style.split(",") if tag.strip()]
        
        # Parse dates if they're strings
        departure_date = travel_request.get("departure_date")
        return_date = travel_request.get("return_date")
        
        if isinstance(departure_date, str):
            departure_date = date.fromisoformat(departure_date)
        if isinstance(return_date, str):
            return_date = date.fromisoformat(return_date)
        
        confirmed = TravelRequest(
            destination=travel_request.get("destination", ""),
            departure_date=departure_date,
            return_date=return_date,
            budget=float(travel_request.get("budget", 0)),
            travel_style=travel_style,
        )
        
        state["confirmed_request"] = confirmed
        summary = (
            f"✅ **Confirmed Travel Request**\n\n"
            f"**Destination:** {confirmed.destination}\n"
            f"**Departure:** {confirmed.departure_date}\n"
            f"**Return:** {confirmed.return_date}\n"
            f"**Budget:** ${confirmed.budget:.2f}\n"
            f"**Travel Style:** {', '.join(confirmed.travel_style)}\n\n"
            f"Finding the perfect itinerary..."
        )
        messages.append({"role": "assistant", "content": summary})
        state["phase"] = "plan"  # Auto-transition to planning
        
    except ValueError as e:
        messages.append({"role": "assistant", "content": f"❌ Validation error: {e}. Please try again."})
    
    state["messages"] = messages
    state["travel_request"] = travel_request
    return state


def _update_travel_request(state: AgentState, user_input: str, field: str) -> AgentState:
    """Helper to update travel_request with user input."""
    state["travel_request"][field] = user_input
    return state


# ============================================================================
# Plan Node (Task 7.4)
# ============================================================================

def plan_node(state: AgentState) -> AgentState:
    """
    Call run_planning_loop to generate itinerary options.
    """
    messages = state.get("messages", [])
    confirmed_request = state.get("confirmed_request")
    reasoning_log = state.get("reasoning_log", [])
    
    if not confirmed_request:
        messages.append({"role": "assistant", "content": "No confirmed request. Please complete onboarding first."})
        state["messages"] = messages
        return state
    
    # Instantiate DataClient and run planning loop
    try:
        client = DataClient()
        itineraries = run_planning_loop(confirmed_request, client, reasoning_log)
        
        state["itineraries"] = itineraries
        state["reasoning_log"] = reasoning_log
        state["phase"] = "rank"
        
        if itineraries:
            messages.append({"role": "assistant", "content": f"Found {len(itineraries)} itinerary options. Analyzing..."})
        else:
            messages.append({"role": "assistant", "content": "No itineraries found. Please adjust your criteria."})
        
    except Exception as e:
        messages.append({"role": "assistant", "content": f"Error during planning: {str(e)}"})
        state["phase"] = "done"
    
    state["messages"] = messages
    return state


# ============================================================================
# Rank Node (Task 7.4)
# ============================================================================

def rank_node(state: AgentState) -> AgentState:
    """
    Normalize scores across itineraries and sort by match_score descending.
    Handles user selection through state updates from the UI.
    """
    messages = state.get("messages", [])
    itineraries = state.get("itineraries", [])
    confirmed_request = state.get("confirmed_request")
    reasoning_log = state.get("reasoning_log", [])
    
    # If no itineraries, stay in rank phase waiting for user input
    if not itineraries or not confirmed_request:
        state["phase"] = "rank"
        return state
    
    # Check if itineraries have been scored already (avoid re-scoring)
    if all(it.match_score > 0 for it in itineraries):
        # Already scored, check if user selected an itinerary
        if state.get("selected_itinerary"):
            state["phase"] = "confirm"
            return state
        
        # Show options and wait for selection
        state["phase"] = "rank"
        return state
    
    # Compute raw scores and normalize
    raw_scores = [
        compute_raw_score(aggregate_itinerary_tags(it), confirmed_request.travel_style)
        for it in itineraries
    ]
    normalized = normalize_scores(raw_scores)
    
    for itinerary, score in zip(itineraries, normalized):
        itinerary.match_score = score
    
    # Sort by match_score descending and trim to top 3
    itineraries.sort(key=lambda it: it.match_score, reverse=True)
    itineraries = itineraries[:3]
    
    reasoning_log.append("=" * 60)
    reasoning_log.append("Trade-off Analysis:")
    for i, it in enumerate(itineraries):
        reasoning_log.append(
            f"  Option {i+1}: {it.flight.airline} + {it.hotel.name} "
            f"(Match: {it.match_score:.2f}, Cost: ${it.total_cost:.2f})"
        )
    reasoning_log.append("=" * 60)
    
    state["itineraries"] = itineraries
    state["reasoning_log"] = reasoning_log
    state["phase"] = "rank"
    
    # Display options for user selection (UI handles the button clicks)
    options_text = "🎯 **Here are your top options:**\n\n"
    for i, it in enumerate(itineraries):
        activity_names = ", ".join(a.name for a in it.activities) if it.activities else "None"
        fallback_note = " ⚠️ *Exceeds Budget*" if it.is_partial_fallback else ""
        options_text += (
            f"**Option {i+1}** (Match: {it.match_score:.1%}){fallback_note}\n"
            f"> Flight: {it.flight.airline} → ${it.flight.price:.2f}\n"
            f"> Hotel: {it.hotel.name} ({it.hotel.stars}★) → ${it.hotel.price_per_night:.2f}/night\n"
            f"> Activities: {activity_names}\n"
            f"> **Total: ${it.total_cost:.2f}**\n\n"
        )
    
    messages.append({"role": "assistant", "content": options_text})
    state["messages"] = messages
    return state


# ============================================================================
# Confirm Node (Task 7.6)
# ============================================================================

def confirm_node(state: AgentState) -> AgentState:
    """
    Display order summary and generate BookingConfirmation with UUID.
    """
    messages = state.get("messages", [])
    selected_itinerary = state.get("selected_itinerary")
    
    if not selected_itinerary:
        messages.append({"role": "assistant", "content": "No itinerary selected."})
        state["messages"] = messages
        state["phase"] = "done"
        return state
    
    # Generate booking ID
    booking_id = str(uuid.uuid4())
    confirmation = BookingConfirmation(
        booking_id=booking_id,
        itinerary=selected_itinerary,
    )
    
    state["booking"] = confirmation
    state["phase"] = "done"
    
    # Display confirmation
    summary = (
        f"✅ Booking Confirmed!\n"
        f"Booking ID: {booking_id}\n"
        f"\n"
        f"Flight: {selected_itinerary.flight.airline} → ${selected_itinerary.flight.price:.2f}\n"
        f"Hotel: {selected_itinerary.hotel.name} ({selected_itinerary.hotel.stars}★) → ${selected_itinerary.hotel.price_per_night:.2f}/night\n"
        f"Activities: {len(selected_itinerary.activities)} selected\n"
        f"Total Cost: ${selected_itinerary.total_cost:.2f}"
    )
    messages.append({"role": "assistant", "content": summary})
    state["messages"] = messages
    return state


# ============================================================================
# Graph Construction (Task 7.9)
# ============================================================================

def build_graph():
    """
    Build and return the LangGraph state machine.
    Edges:
      START → onboard → (conditional: continue | proceed to plan) → plan → rank → (wait | confirm) → confirm → END
    """
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("onboard", onboard_node)
    graph.add_node("plan", plan_node)
    graph.add_node("rank", rank_node)
    graph.add_node("confirm", confirm_node)
    
    # Add edges
    graph.set_entry_point("onboard")
    
    # Onboard → Plan (conditional: when user confirms)
    def onboard_to_plan(state: AgentState) -> str:
        """Transition from onboard to plan when user confirms."""
        if state.get("confirmed_request"):
            return "plan"
        return "onboard"
    
    graph.add_conditional_edges("onboard", onboard_to_plan, {"plan": "plan", "onboard": "onboard"})
    
    # Plan → Rank (direct)
    graph.add_edge("plan", "rank")
    
    # Rank → Confirm (conditional: when user selects an itinerary)
    def rank_to_confirm(state: AgentState) -> str:
        """Transition from rank to confirm when user selects an option."""
        if state.get("selected_itinerary"):
            return "confirm"
        return "rank"
    
    graph.add_conditional_edges("rank", rank_to_confirm, {"confirm": "confirm", "rank": "rank"})
    
    # Confirm → End (direct)
    graph.add_edge("confirm", END)
    
    return graph.compile()
