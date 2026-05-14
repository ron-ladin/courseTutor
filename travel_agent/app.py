import uuid

import streamlit as st

from agent import AgentState, build_graph
from models import BookingConfirmation, Itinerary

st.set_page_config(page_title="Travel Planning Agent", layout="centered")
st.title("Travel Planning Agent")

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


# ── chat history ──────────────────────────────────────────────────────────────
for msg in state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# ── reasoning panel ───────────────────────────────────────────────────────────
with st.expander("Agent Reasoning", expanded=False):
    if state["reasoning_log"]:
        for entry in state["reasoning_log"]:
            st.write(f"• {entry}")
    else:
        st.caption("No reasoning steps yet.")
    if state["phase"] == "plan":
        st.write("Planning in progress...")


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
                        destinations = DataClient().destinations()
                        dest_list = ", ".join(destinations)
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
            # stub mode: echo back so the UI is testable before the graph is wired
            state["messages"].append({"role": "assistant", "content": f"[stub] Received: {prompt}"})
            st.session_state.state = state

        st.rerun()
