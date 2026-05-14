import streamlit as st

from agent import AgentState, build_graph
from models import Itinerary

st.set_page_config(page_title="Travel Planning Agent", layout="centered")
st.title("Travel Planning Agent")

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
        "passenger_info":     {},
        "contact_info":       {},
        "payment_info":       {},
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


# ── Reasoning panel ───────────────────────────────────────────────────────────
with st.expander("Agent Reasoning", expanded=False):
    if state["reasoning_log"]:
        for entry in state["reasoning_log"]:
            st.write(f"• {entry}")
    else:
        st.caption("No reasoning steps yet.")
    if state["phase"] == "plan":
        st.write("Planning in progress...")


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
                    state["phase"] = "collect"
                    # Invoke graph immediately so collect_passenger_node asks the first question
                    new_state = graph.invoke(state)
                    st.session_state.state = new_state
                    st.rerun()


# ── Confirm panel (after passenger collection) ────────────────────────────────
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

    p = state.get("passenger_info", {})
    c = state.get("contact_info",   {})
    pay = state.get("payment_info", {})
    with st.container(border=True):
        st.write(f"**Passenger:** {p.get('full_name')} | Passport: {p.get('passport_number')}")
        st.write(f"**Contact:** {c.get('email')} | {c.get('phone')}")
        st.write(f"**Card:** **** {pay.get('card_last4')} (exp {pay.get('card_expiry')})")

    if st.button("Confirm & Book"):
        # confirm_node calls the server and records all booking IDs
        new_state = graph.invoke(state)
        st.session_state.state = new_state
        st.rerun()


# ── Done: booking confirmation ────────────────────────────────────────────────
if state["phase"] == "done" and state["booking"]:
    st.divider()
    booking = state["booking"]
    st.success(f"Booking Confirmed — Flight ID: `{booking.booking_id}`")
    if booking.hotel_booking_id:
        st.info(f"Hotel ID: `{booking.hotel_booking_id}`")
    for bid in booking.activity_booking_ids:
        st.info(f"Activity ID: `{bid}`")


# ── Chat input ────────────────────────────────────────────────────────────────
# Only show during phases that expect text input
if state["phase"] in ("onboard", "collect"):
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
