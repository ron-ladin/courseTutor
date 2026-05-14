import uuid
from datetime import date as date_type

import streamlit as st

from agent import AgentState, build_graph
from models import BookingConfirmation, Itinerary, TravelRequest

st.set_page_config(page_title="Travel Planning Agent", layout="centered", page_icon="✈️")
st.title("✈️ Travel Planning Agent")

# ── sidebar: demo guide ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("Demo Scenarios")
    st.markdown(
        "**Tokyo (happy path)**\n"
        "- Budget: $2,000+\n"
        "- Style: adventure, culture\n\n"
        "**Paris (backtracking demo)**\n"
        "- Budget: $1,500 ← triggers backtrack!\n"
        "- Style: romance\n"
        "- All Paris hotels > $1,500/night\n"
        "- Watch the Reasoning panel fill up\n\n"
        "**Bali / New York** — standard paths"
    )
    st.divider()
    st.caption("Start the mock server before using:\n`uvicorn mock_server:app --port 8000`")

_VALID_STYLES = ["adventure", "culture", "luxury", "romance", "nature", "food", "budget"]

# ── session state init ────────────────────────────────────────────────────────
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
    st.session_state.state: AgentState = {
        "messages": [],
        "travel_request": {},
        "confirmed_request": None,
        "itineraries": [],
        "selected_itinerary": None,
        "booking": None,
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "onboard",
    }

state: AgentState = st.session_state.state

# First-load greeting
if not state["messages"]:
    if st.session_state.graph is not None:
        # Let the graph ask the first question
        new_state = st.session_state.graph.invoke(state)
        st.session_state.state = new_state
    else:
        state["messages"].append({
            "role": "assistant",
            "content": "Hello! I'm your travel planning assistant. Where would you like to travel? (Tokyo, Paris, Bali, New York)",
        })
        st.session_state.state = state
    st.rerun()


# ── chat history ──────────────────────────────────────────────────────────────
for msg in state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# ── reasoning panel ───────────────────────────────────────────────────────────
with st.expander("Agent Reasoning", expanded=bool(state["reasoning_log"])):
    if state["phase"] == "plan":
        st.info("Planning in progress...")
    if state["reasoning_log"]:
        for entry in state["reasoning_log"]:
            if "backtrack" in entry.lower() or "fallback" in entry.lower():
                st.warning(f"⚠ {entry}")
            elif entry.startswith("GET "):
                st.code(entry, language=None)
            else:
                st.write(f"• {entry}")
    else:
        st.caption("No reasoning steps yet.")


# ── itinerary cards ───────────────────────────────────────────────────────────
if state["phase"] == "rank" and not state["itineraries"]:
    st.error("Unable to find a matching itinerary. Please restart with a higher budget.")

if state["phase"] == "rank" and state["itineraries"]:
    st.divider()
    st.subheader("Your Itinerary Options")
    for i, itin in enumerate(state["itineraries"]):
        with st.container(border=True):
            fallback_label = "  Warning: Exceeds Budget" if itin.is_partial_fallback else ""
            st.subheader(f"Option {i + 1}  —  Score: {itin.match_score:.2f}{fallback_label}")
            st.write(f"**Flight:** {itin.flight.airline} ({itin.flight.id})  —  ${itin.flight.price:.2f}  ({itin.flight.duration_hours}h)")
            st.write(f"**Hotel:** {itin.hotel.name}  —  ${itin.hotel.price_per_night:.2f}/night  ({itin.hotel.stars} stars)")
            if itin.activities:
                st.write(f"**Activities:** {', '.join(a.name for a in itin.activities)}")
            else:
                st.write("**Activities:** None")
            st.write(f"**Total Cost:** ${itin.total_cost:.2f}")
            if st.button(f"Select Option {i + 1}", key=f"select_{i}"):
                state["selected_itinerary"] = itin
                state["phase"] = "confirm"
                st.session_state.state = state
                st.rerun()


# ── confirm: order summary ────────────────────────────────────────────────────
if state["phase"] == "confirm" and state["selected_itinerary"]:
    itin: Itinerary = state["selected_itinerary"]
    st.divider()
    st.subheader("Order Summary")
    with st.container(border=True):
        if itin.is_partial_fallback:
            st.warning("This package exceeds your stated budget.")
        st.write(f"**Destination:** {itin.flight.destination}")
        st.write(f"**Flight:** {itin.flight.airline} ({itin.flight.id})  —  ${itin.flight.price:.2f}")
        st.write(f"**Hotel:** {itin.hotel.name}  —  ${itin.hotel.price_per_night:.2f}/night")
        if itin.activities:
            st.write(f"**Activities:** {', '.join(a.name for a in itin.activities)}")
        st.write(f"**Total Cost:** ${itin.total_cost:.2f}")
        st.write(f"**Match Score:** {itin.match_score:.2f}")

    if st.button("Confirm Booking"):
        booking_id = str(uuid.uuid4())
        state["booking"] = BookingConfirmation(booking_id=booking_id, itinerary=itin)
        state["phase"] = "done"
        state["messages"].append({
            "role": "assistant",
            "content": f"Booking confirmed! Your Booking ID is: **{booking_id}**",
        })
        st.session_state.state = state
        st.rerun()


# ── done: booking confirmation ────────────────────────────────────────────────
if state["phase"] == "done" and state["booking"]:
    st.divider()
    st.success(f"Booking Confirmed — ID: `{state['booking'].booking_id}`")
    if st.button("Plan Another Trip", type="primary"):
        st.session_state.state = {
            "messages": [],
            "travel_request": {},
            "confirmed_request": None,
            "itineraries": [],
            "selected_itinerary": None,
            "booking": None,
            "reasoning_log": [],
            "backtrack_count": 0,
            "phase": "onboard",
        }
        st.rerun()


# ── stub-mode helpers ─────────────────────────────────────────────────────────

def _run_planning(state: AgentState) -> None:
    """Call the real planner directly (used when build_graph() is still a stub)."""
    from data_client import DataClient
    from planner import run_planning_loop

    tr = state["travel_request"]
    try:
        request = TravelRequest(
            destination=tr["destination"],
            departure_date=date_type.fromisoformat(tr["departure_date"]),
            return_date=date_type.fromisoformat(tr["return_date"]),
            budget=float(tr["budget"]),
            travel_style=tr.get("travel_style", []),
        )
        state["confirmed_request"] = request
        log: list[str] = state["reasoning_log"]
        itineraries = run_planning_loop(request, DataClient(), log)
        state["reasoning_log"] = log

        if not itineraries:
            state["messages"].append({
                "role": "assistant",
                "content": "Unable to find a matching itinerary. Please restart with a higher budget.",
            })
            state["phase"] = "onboard"
            state["travel_request"] = {}
        else:
            state["itineraries"] = itineraries
            state["phase"] = "rank"
            state["messages"].append({
                "role": "assistant",
                "content": f"Found {len(itineraries)} itinerary option(s). Review and select one below.",
            })
    except ConnectionError as e:
        state["messages"].append({"role": "assistant", "content": str(e)})
        state["phase"] = "onboard"
    except Exception as e:
        state["messages"].append({"role": "assistant", "content": f"Planning error: {e}"})
        state["phase"] = "onboard"


def _process_stub(state: AgentState, prompt: str) -> None:
    """Sequential onboarding flow used while build_graph() returns None."""
    tr = state["travel_request"]
    reply: str

    if "destination" not in tr:
        valid = ["Tokyo", "Paris", "Bali", "New York"]
        dest = next((v for v in valid if v.lower() == prompt.strip().lower()), None)
        if dest:
            tr["destination"] = dest
            reply = "What is your departure date? (YYYY-MM-DD)"
        else:
            reply = f"Please choose from: {', '.join(valid)}."

    elif "departure_date" not in tr:
        try:
            date_type.fromisoformat(prompt.strip())
            tr["departure_date"] = prompt.strip()
            reply = "What is your return date? (YYYY-MM-DD)"
        except ValueError:
            reply = "Please enter a valid date in YYYY-MM-DD format."

    elif "return_date" not in tr:
        try:
            ret = date_type.fromisoformat(prompt.strip())
            dep = date_type.fromisoformat(tr["departure_date"])
            if ret <= dep:
                reply = "Return date must be after departure date. Please re-enter."
            else:
                tr["return_date"] = prompt.strip()
                reply = "What is your total budget in USD?"
        except ValueError:
            reply = "Please enter a valid date in YYYY-MM-DD format."

    elif "budget" not in tr:
        try:
            budget = float(prompt.strip().replace("$", "").replace(",", ""))
            if budget <= 0:
                reply = "Please enter a positive number for your budget."
            else:
                tr["budget"] = budget
                reply = (
                    f"What travel styles do you prefer? "
                    f"(comma-separated from: {', '.join(_VALID_STYLES)})"
                )
        except ValueError:
            reply = "Please enter a positive number for your budget."

    elif "travel_style" not in tr:
        styles = [s.strip().lower() for s in prompt.split(",") if s.strip().lower() in _VALID_STYLES]
        if not styles:
            reply = f"Please choose at least one from: {', '.join(_VALID_STYLES)}."
        else:
            tr["travel_style"] = styles
            reply = (
                f"Here's your trip summary:\n"
                f"- Destination: {tr['destination']}\n"
                f"- Dates: {tr['departure_date']} → {tr['return_date']}\n"
                f"- Budget: ${tr['budget']:.0f}\n"
                f"- Style: {', '.join(styles)}\n\n"
                f"Shall I proceed with planning? (yes / no)"
            )

    elif prompt.strip().lower() in ("yes", "y"):
        state["travel_request"] = tr
        state["messages"].append({"role": "assistant", "content": "On it! Planning your trip..."})
        _run_planning(state)
        return

    elif prompt.strip().lower() in ("no", "n"):
        state["travel_request"] = {}
        reply = "No problem! Where would you like to travel? (Tokyo, Paris, Bali, New York)"

    else:
        reply = "Please reply with 'yes' to proceed or 'no' to start over."

    state["travel_request"] = tr
    state["messages"].append({"role": "assistant", "content": reply})


# ── chat input ────────────────────────────────────────────────────────────────
if state["phase"] != "done":
    if prompt := st.chat_input("Type your response..."):
        state["messages"].append({"role": "user", "content": prompt})

        graph = st.session_state.graph
        if graph is not None:
            try:
                new_state = graph.invoke(state)
                st.session_state.state = new_state
            except ConnectionError:
                state["messages"].append({
                    "role": "assistant",
                    "content": "Cannot reach the travel data server. Run: `uvicorn mock_server:app --port 8000`",
                })
                st.session_state.state = state
            except ValueError as e:
                msg = str(e).lower()
                if "destination" in msg or "not found" in msg:
                    try:
                        from data_client import DataClient
                        dest_list = ", ".join(DataClient().destinations())
                    except Exception:
                        dest_list = "Tokyo, Paris, Bali, New York"
                    state["messages"].append({
                        "role": "assistant",
                        "content": f"That destination isn't available. Please choose from: {dest_list}.",
                    })
                elif "itinerar" in msg or "no match" in msg:
                    state["messages"].append({
                        "role": "assistant",
                        "content": "Unable to find a matching itinerary. Please restart with a higher budget.",
                    })
                else:
                    state["messages"].append({"role": "assistant", "content": f"Error: {e}"})
                st.session_state.state = state
            except Exception as e:
                state["messages"].append({"role": "assistant", "content": f"Unexpected error: {e}"})
                st.session_state.state = state
        else:
            _process_stub(state, prompt)
            st.session_state.state = state

        st.rerun()
