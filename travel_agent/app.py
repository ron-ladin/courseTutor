from __future__ import annotations

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


st.set_page_config(
    page_title="SkySwift AI",
    layout="centered",
    page_icon="SS",
    initial_sidebar_state="collapsed",
)


def _empty_state() -> AgentState:
    return {
        "messages": [],
        "travel_request": {},
        "confirmed_request": None,
        "itineraries": [],
        "selected_itinerary": None,
        "booking": None,
        "reasoning_log": [],
        "backtrack_count": 0,
        "phase": "onboard",
        "agent_status": "COLLECTING",
        "passenger_info": {},
        "contact_info": {},
        "payment_info": {},
    }


def _inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --sky-ink: #172033;
            --sky-muted: #697386;
            --sky-line: #e4e9ef;
            --sky-soft: #f6f9fb;
            --sky-teal: #0ea5a4;
            --sky-teal-dark: #087d7d;
            --sky-user: #e9f7f6;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background: #fbfcfd;
            color: var(--sky-ink);
            font-family: Inter, Segoe UI, system-ui, -apple-system, sans-serif;
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none;
        }

        .block-container {
            max-width: 880px;
            padding: 22px 18px 120px;
        }

        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 18px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
        }

        .brand-mark {
            width: 34px;
            height: 34px;
            border-radius: 8px;
            display: grid;
            place-items: center;
            background: #172033;
            color: #ffffff;
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0;
        }

        .brand-name {
            font-size: 1rem;
            font-weight: 800;
            color: var(--sky-ink);
            letter-spacing: 0;
        }

        .reset-wrap .stButton > button {
            min-height: 34px;
            padding: 0 12px;
            border-radius: 8px;
            border: 1px solid var(--sky-line);
            background: #ffffff;
            color: var(--sky-muted);
            box-shadow: none;
            font-weight: 650;
        }

        .landing {
            min-height: calc(100vh - 260px);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 42px 0 24px;
        }

        .landing-title {
            margin: 0;
            font-size: clamp(2.4rem, 7vw, 4.8rem);
            line-height: 1;
            letter-spacing: 0;
            font-weight: 850;
            color: var(--sky-ink);
        }

        .landing-line {
            margin: 18px 0 0;
            color: var(--sky-muted);
            font-size: clamp(1.05rem, 2.2vw, 1.35rem);
        }

        .chat-space {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        div[data-testid="stChatMessage"] {
            background: transparent;
            border: 0;
            box-shadow: none;
            padding: 0.25rem 0;
        }

        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            line-height: 1.65;
        }

        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: var(--sky-user);
            border: 1px solid #d5efed;
            border-radius: 8px;
            padding: 0.35rem 0.55rem;
        }

        [data-testid="stChatInput"] {
            max-width: 840px;
            margin: 0 auto;
        }

        [data-testid="stChatInput"] textarea {
            min-height: 58px;
            border-radius: 8px;
            border: 1px solid var(--sky-line);
            background: #ffffff;
            box-shadow: 0 12px 30px rgba(23, 32, 51, 0.08);
        }

        [data-testid="stChatInput"] button {
            border-radius: 8px;
            background: var(--sky-teal);
            color: #ffffff;
        }

        .trip-card {
            border: 1px solid var(--sky-line);
            border-radius: 8px;
            background: #ffffff;
            padding: 18px;
            margin: 14px 0 8px;
            box-shadow: 0 12px 30px rgba(23, 32, 51, 0.05);
        }

        .trip-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
        }

        .trip-title {
            margin: 0;
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--sky-ink);
        }

        .score {
            border-radius: 999px;
            padding: 5px 9px;
            color: var(--sky-teal-dark);
            background: #e8f7f6;
            font-size: 0.82rem;
            font-weight: 800;
            white-space: nowrap;
        }

        .trip-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
        }

        .fact {
            background: var(--sky-soft);
            border-radius: 8px;
            padding: 12px;
            min-height: 88px;
        }

        .label {
            color: var(--sky-muted);
            font-size: 0.76rem;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .value {
            color: var(--sky-ink);
            font-weight: 650;
            overflow-wrap: anywhere;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--sky-line);
            border-radius: 8px;
            box-shadow: 0 12px 30px rgba(23, 32, 51, 0.05);
        }

        .warning {
            display: inline-block;
            margin-top: 8px;
            border-radius: 999px;
            background: #fff4e5;
            color: #8a5b0c;
            padding: 5px 9px;
            font-size: 0.8rem;
            font-weight: 750;
        }

        .stButton > button {
            border-radius: 8px;
            border: 1px solid var(--sky-teal);
            background: var(--sky-teal);
            color: #ffffff;
            font-weight: 750;
        }

        .stButton > button:hover {
            border-color: var(--sky-teal-dark);
            background: var(--sky-teal-dark);
            color: #ffffff;
        }

        @media (max-width: 700px) {
            .block-container {
                padding: 18px 14px 110px;
            }
            .trip-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_topbar(show_reset: bool) -> None:
    left, right = st.columns([5, 1])
    with left:
        st.markdown(
            """
            <div class="topbar">
              <div class="brand">
                <div class="brand-mark">SS</div>
                <div class="brand-name">SkySwift AI</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if show_reset:
            st.markdown('<div class="reset-wrap">', unsafe_allow_html=True)
            if st.button("Start over", use_container_width=True):
                _reset_trip()
            st.markdown("</div>", unsafe_allow_html=True)


def _render_landing() -> None:
    st.markdown(
        """
        <div class="landing">
          <h1 class="landing-title">SkySwift AI</h1>
          <p class="landing-line">Where are we flying today?</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_trip_card(index: int, itin: Itinerary) -> None:
    activities = ", ".join(activity.name for activity in itin.activities) or "None selected"

    with st.container(border=True):
        title_col, score_col = st.columns([4, 1])
        with title_col:
            st.subheader(f"Option {index + 1}: {itin.flight.destination}")
            if itin.is_partial_fallback:
                st.warning("This option exceeds the stated budget.")
        with score_col:
            st.metric("Match", f"{itin.match_score:.0%}")

        flight_col, hotel_col, total_col = st.columns(3)
        with flight_col:
            st.caption("FLIGHT")
            st.markdown(f"**{itin.flight.airline}**")
            st.write(f"${itin.flight.price:.0f} · {itin.flight.duration_hours:g}h")
        with hotel_col:
            st.caption("HOTEL")
            st.markdown(f"**{itin.hotel.name}**")
            st.write(f"${itin.hotel.price_per_night:.0f}/night · {itin.hotel.stars} stars")
        with total_col:
            st.caption("TOTAL")
            st.markdown(f"**${itin.total_cost:.0f}**")
            st.write("Estimated package total")

        st.caption("ACTIVITIES")
        st.write(activities)


def _render_order_summary(itin: Itinerary) -> None:
    activities = ", ".join(activity.name for activity in itin.activities) or "None selected"

    with st.container(border=True):
        st.subheader("Order summary")
        if itin.is_partial_fallback:
            st.warning("This package exceeds your stated budget.")

        dest_col, flight_col, hotel_col, total_col = st.columns(4)
        with dest_col:
            st.caption("DESTINATION")
            st.markdown(f"**{itin.flight.destination}**")
        with flight_col:
            st.caption("FLIGHT")
            st.markdown(f"**{itin.flight.airline}**")
            st.write(f"${itin.flight.price:.0f}")
        with hotel_col:
            st.caption("HOTEL")
            st.markdown(f"**{itin.hotel.name}**")
            st.write(f"${itin.hotel.price_per_night:.0f}/night")
        with total_col:
            st.caption("TOTAL")
            st.markdown(f"**${itin.total_cost:.0f}**")

        st.caption("ACTIVITIES")
        st.write(activities)


def _reset_trip() -> None:
    st.session_state.graph = build_graph()
    st.session_state.state = _empty_state()
    st.rerun()


def _has_user_message(state: AgentState) -> bool:
    return any(message.get("role") == "user" for message in state.get("messages", []))


_inject_theme()

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "state" not in st.session_state:
    st.session_state.state = _empty_state()

state: AgentState = st.session_state.state
graph = st.session_state.graph

if not state["messages"]:
    new_state = graph.invoke(state)
    st.session_state.state = new_state
    st.rerun()

conversation_started = _has_user_message(state)
_render_topbar(show_reset=conversation_started or state["phase"] != "onboard")

if not state["messages"]:
    _render_landing()
else:
    st.markdown('<div class="chat-space">', unsafe_allow_html=True)
    for msg in state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    st.markdown("</div>", unsafe_allow_html=True)


# ── Reasoning panel ───────────────────────────────────────────────────────────
if state["reasoning_log"]:
    with st.expander("Agent Reasoning", expanded=False):
        for entry in state["reasoning_log"]:
            low = entry.lower()
            if "⚠" in entry or "below minimum" in low or "fallback" in low or "backtrack" in low:
                st.warning(entry)
            elif entry.startswith("GET "):
                st.code(entry, language=None)
            else:
                st.write(f"• {entry}")


# ── Rank phase: itinerary cards ───────────────────────────────────────────────
if state["phase"] == "rank":
    st.divider()

    confirmed = state.get("confirmed_request")
    if confirmed:
        from datetime import date as _date
        nights = (_date.fromisoformat(str(confirmed.return_date)) - _date.fromisoformat(str(confirmed.departure_date))).days
        st.caption(
            f"🗺 **{confirmed.destination}** · "
            f"{confirmed.departure_date} → {confirmed.return_date} ({nights} nights) · "
            f"Budget **${confirmed.budget:,.0f}** · "
            f"Style: {', '.join(confirmed.travel_style)}"
        )

    itins = state["itineraries"]

    if not itins:
        st.error("No itinerary found. Try a higher budget or shorter trip.")
        if st.button("✏️ Start Over", type="primary"):
            st.session_state.state = _empty_state()
            st.rerun()
    else:
        all_fallback = all(it.is_partial_fallback for it in itins)
        if all_fallback and confirmed:
            min_gap = min(it.total_cost - confirmed.budget for it in itins)
            st.warning(
                f"All options exceed your budget. "
                f"The closest option needs **${min_gap:,.0f} more**. "
                f"You can still book it or start over with a higher budget."
            )

        st.subheader("Your Itinerary Options")
        for i, itin in enumerate(itins):
            with st.container(border=True):
                if itin.is_partial_fallback and confirmed:
                    gap = itin.total_cost - confirmed.budget
                    st.error(f"Option {i + 1} — ⚠️ Over budget by ${gap:,.0f}  |  Match: {itin.match_score:.0%}")
                else:
                    st.success(f"Option {i + 1} — ✅ Within budget  |  Match: {itin.match_score:.0%}")

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"✈️ **{itin.flight.airline}** — ${itin.flight.price:,.0f} ({itin.flight.duration_hours}h)")
                    st.write(f"🏨 **{itin.hotel.name}** — ${itin.hotel.price_per_night:,.0f}/night ({itin.hotel.stars}★)")
                with col2:
                    acts = ', '.join(a.name for a in itin.activities) or 'None'
                    st.write(f"🎯 **Activities:** {acts}")
                    st.write(f"💰 **Total: ${itin.total_cost:,.0f}**")

                if st.button(f"Select Option {i + 1}", key=f"select_{i}", type="primary" if i == 0 else "secondary"):
                    state["selected_itinerary"] = itin
                    state["phase"] = "collect"
                    new_state = graph.invoke(state)
                    st.session_state.state = new_state
                    st.rerun()

        st.divider()
        if st.button("✏️ Change Trip Details", type="secondary"):
            st.session_state.state = _empty_state()
            st.rerun()


# ── Confirm phase ─────────────────────────────────────────────────────────────
if state["phase"] == "confirm" and state["selected_itinerary"]:
    itin: Itinerary = state["selected_itinerary"]
    st.divider()
    st.subheader("Order Summary")
    with st.container(border=True):
        if itin.is_partial_fallback:
            st.warning("⚠️ This package exceeds your stated budget.")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Destination:** {itin.flight.destination}")
            st.write(f"**Flight:** {itin.flight.airline} — ${itin.flight.price:,.0f}")
            st.write(f"**Hotel:** {itin.hotel.name} — ${itin.hotel.price_per_night:,.0f}/night")
        with col2:
            st.write(f"**Activities:** {', '.join(a.name for a in itin.activities) or 'None'}")
            st.write(f"**Total Cost:** ${itin.total_cost:,.0f}")
            st.write(f"**Match Score:** {itin.match_score:.0%}")

    p   = state.get("passenger_info", {})
    c   = state.get("contact_info",   {})
    pay = state.get("payment_info",   {})
    with st.container(border=True):
        st.write(f"**Passenger:** {p.get('full_name')} | Passport: {p.get('passport_number')}")
        st.write(f"**Contact:** {c.get('email')} | {c.get('phone')}")
        st.write(f"**Card:** **** {pay.get('card_last4')} (exp {pay.get('card_expiry')})")

    col_book, col_back = st.columns([3, 1])
    with col_book:
        if st.button("✅ Confirm & Book", type="primary"):
            new_state = graph.invoke(state)
            st.session_state.state = new_state
            st.rerun()
    with col_back:
        if st.button("← Back"):
            st.session_state.state = _empty_state()
            st.rerun()


# ── Done ──────────────────────────────────────────────────────────────────────
if state["phase"] == "done" and state["booking"]:
    st.divider()
    st.success("🎉 Booking Confirmed!")
    st.code(f"Booking ID: {state['booking'].booking_id}")
    if state["selected_itinerary"]:
        itin = state["selected_itinerary"]
        st.write(f"**{itin.flight.destination}** · {itin.flight.airline} + {itin.hotel.name} · ${itin.total_cost:,.0f}")
    if st.button("✈️ Plan Another Trip", type="primary"):
        st.session_state.state = _empty_state()
        st.rerun()


# ── Chat input (onboard + collect phases only) ────────────────────────────────
if state["phase"] in ("onboard", "collect"):
    if prompt := st.chat_input("Type your message..."):
        state["messages"].append({"role": "user", "content": prompt})
        st.session_state.state = state
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    new_state = graph.invoke(state)
                    st.session_state.state = new_state
                except Exception as e:
                    state["messages"].append({"role": "assistant", "content": f"Error: {e}"})
                    st.session_state.state = state
        st.rerun()
