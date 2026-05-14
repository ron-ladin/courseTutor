from datetime import date as date_type

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st

try:
    from travel_agent.agent import AgentState, build_graph
    from travel_agent.models import Itinerary, TravelRequest
except ImportError:
    from agent import AgentState, build_graph
    from models import Itinerary, TravelRequest

_VALID_STYLES = ["adventure", "culture", "luxury", "romance", "nature", "food", "budget"]

st.set_page_config(page_title="Travel Planning Agent", layout="centered", page_icon="✈️")
st.title("✈️ Travel Planning Agent")

# ── sidebar: demo guide ───────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none;
    }
    section.main > div {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    st.caption(
        "**Live data:** set `AMADEUS_CLIENT_ID` + `AMADEUS_CLIENT_SECRET`\n\n"
        "App runs standalone with embedded data when no credentials are set."
    )

# ── Session state init ────────────────────────────────────────────────────────
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
    st.session_state.state: AgentState = {
        "messages":           [],
        "travel_request":     {},
        "confirmed_request":  None,
        "itineraries":        [],
        "selected_itinerary": None,
        "booking":            None,
        "reasoning_log":      [],
        "backtrack_count":    0,
        "phase":              "onboard",
    }

state: AgentState = st.session_state.state
graph = st.session_state.graph

# First-load: let the graph ask the opening question
if not state["messages"]:
    new_state = graph.invoke(state)
    st.session_state.state = new_state
    st.rerun()


# ── Chat history ──────────────────────────────────────────────────────────────
for msg in state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# ── reasoning panel ───────────────────────────────────────────────────────────
with st.expander("Agent Reasoning", expanded=False):
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


# ── Itinerary cards (rank phase) ──────────────────────────────────────────────
if state["phase"] == "rank":
    if not state["itineraries"]:
        st.error("Unable to find a matching itinerary. Please restart with a higher budget.")
    else:
        st.divider()
        st.subheader("Your Itinerary Options")
        for i, itin in enumerate(state["itineraries"]):
            with st.container(border=True):
                fallback = "  ⚠️ Exceeds Budget" if itin.is_partial_fallback else ""
                st.subheader(f"Option {i + 1}  —  Score: {itin.match_score:.2f}{fallback}")
                st.write(f"**Flight:** {itin.flight.airline} ({itin.flight.id})  —  ${itin.flight.price:.2f}  ({itin.flight.duration_hours}h)")
                st.write(f"**Hotel:** {itin.hotel.name}  —  ${itin.hotel.price_per_night:.2f}/night  ({itin.hotel.stars}★)")
                st.write(f"**Activities:** {', '.join(a.name for a in itin.activities) or 'None'}")
                st.write(f"**Total Cost:** ${itin.total_cost:.2f}")

                if st.button(f"Select Option {i + 1}", key=f"select_{i}"):
                    state["selected_itinerary"] = itin
                    state["phase"] = "confirm"
                    # Invoke graph so confirm_node generates the booking
                    new_state = graph.invoke(state)
                    st.session_state.state = new_state
                    st.rerun()


# ── Confirm panel (after itinerary selection) ─────────────────────────────────
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
        st.write(f"**Activities:** {', '.join(a.name for a in itin.activities) or 'None'}")
        st.write(f"**Total Cost:** ${itin.total_cost:.2f}")
        st.write(f"**Match Score:** {itin.match_score:.2f}")

    if st.button("Confirm & Book"):
        new_state = graph.invoke(state)
        st.session_state.state = new_state
        st.rerun()


# ── Done: booking confirmation ────────────────────────────────────────────────
if state["phase"] == "done" and state["booking"]:
    st.divider()
    st.success(f"Booking Confirmed — ID: `{state['booking'].booking_id}`")
    if st.button("Plan Another Trip", type="primary"):
        st.session_state.state = {
            "messages": [], "travel_request": {}, "confirmed_request": None,
            "itineraries": [], "selected_itinerary": None, "booking": None,
            "reasoning_log": [], "backtrack_count": 0, "phase": "onboard",
            "passenger_info": {}, "contact_info": {}, "payment_info": {},
        }
        st.rerun()


# ── stub-mode helpers ─────────────────────────────────────────────────────────

def _run_planning(state: AgentState) -> None:
    """Call the real planner directly (used when build_graph() is still a stub)."""
    try:
        from travel_agent.data.client import LiveDataClient as DataClient
        from travel_agent.planner import run_planning_loop
    except ImportError:
        from data.client import LiveDataClient as DataClient
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
        try:
            new_state = graph.invoke(state)
            st.session_state.state = new_state
        except ConnectionError:
            state["messages"].append({
                "role": "assistant",
                "content": "Cannot reach the travel data server. Run: `uvicorn mock_server:app --port 8000`",
            })
            st.session_state.state = state
        except Exception as e:
            state["messages"].append({"role": "assistant", "content": f"Unexpected error: {e}"})
            st.session_state.state = state
        st.rerun()
