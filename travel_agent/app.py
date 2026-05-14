from __future__ import annotations

from datetime import date as date_type
from html import escape

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
            padding: 16px;
            margin: 10px 0;
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
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .fact {
            background: var(--sky-soft);
            border-radius: 8px;
            padding: 10px;
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
    activities = ", ".join(escape(activity.name) for activity in itin.activities) or "None selected"
    warning = '<span class="warning">Exceeds budget</span>' if itin.is_partial_fallback else ""
    st.markdown(
        f"""
        <div class="trip-card">
          <div class="trip-top">
            <div>
              <h3 class="trip-title">Option {index + 1}: {escape(itin.flight.destination)}</h3>
              {warning}
            </div>
            <div class="score">Match {itin.match_score:.2f}</div>
          </div>
          <div class="trip-grid">
            <div class="fact">
              <div class="label">Flight</div>
              <div class="value">{escape(itin.flight.airline)} | ${itin.flight.price:.0f} | {itin.flight.duration_hours:g}h</div>
            </div>
            <div class="fact">
              <div class="label">Hotel</div>
              <div class="value">{escape(itin.hotel.name)} | ${itin.hotel.price_per_night:.0f}/night</div>
            </div>
            <div class="fact">
              <div class="label">Activities</div>
              <div class="value">{activities}</div>
            </div>
            <div class="fact">
              <div class="label">Total</div>
              <div class="value">${itin.total_cost:.0f}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_order_summary(itin: Itinerary) -> None:
    activities = ", ".join(escape(activity.name) for activity in itin.activities) or "None selected"
    warning = '<span class="warning">This package exceeds your stated budget</span>' if itin.is_partial_fallback else ""
    st.markdown(
        f"""
        <div class="trip-card">
          <div class="trip-top">
            <div>
              <h3 class="trip-title">Order summary</h3>
              {warning}
            </div>
            <div class="score">Match {itin.match_score:.2f}</div>
          </div>
          <div class="trip-grid">
            <div class="fact"><div class="label">Destination</div><div class="value">{escape(itin.flight.destination)}</div></div>
            <div class="fact"><div class="label">Flight</div><div class="value">{escape(itin.flight.airline)} | ${itin.flight.price:.0f}</div></div>
            <div class="fact"><div class="label">Hotel</div><div class="value">{escape(itin.hotel.name)} | ${itin.hotel.price_per_night:.0f}/night</div></div>
            <div class="fact"><div class="label">Total</div><div class="value">${itin.total_cost:.0f}</div></div>
          </div>
          <p style="color:#697386;margin:12px 0 0;">Activities: {activities}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

if not conversation_started and state["phase"] == "onboard":
    _render_landing()
else:
    st.markdown('<div class="chat-space">', unsafe_allow_html=True)
    for msg in state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    st.markdown("</div>", unsafe_allow_html=True)

if state["phase"] == "rank":
    if not state["itineraries"]:
        st.error("Unable to find a matching itinerary. Please restart with a higher budget.")
    else:
        for i, itin in enumerate(state["itineraries"]):
            _render_trip_card(i, itin)
            if st.button(f"Select option {i + 1}", key=f"select_{i}", use_container_width=True):
                state["selected_itinerary"] = itin
                state["phase"] = "confirm"
                new_state = graph.invoke(state)
                st.session_state.state = new_state
                st.rerun()

if state["phase"] == "confirm" and state["selected_itinerary"]:
    selected: Itinerary = state["selected_itinerary"]
    _render_order_summary(selected)
    if st.button("Confirm and book", type="primary", use_container_width=True):
        new_state = graph.invoke(state)
        st.session_state.state = new_state
        st.rerun()

if state["phase"] == "done" and state["booking"]:
    st.success(f"Booking confirmed. Confirmation ID: {state['booking'].booking_id}")
    if st.button("Plan another trip", type="primary", use_container_width=True):
        _reset_trip()


def _run_planning(state: AgentState) -> None:
    """Call the real planner directly, used only if the graph is swapped for a stub."""
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
        valid = ["Tokyo", "Paris", "Bali", "New York", "Japan", "Greece", "Thailand", "Mexico", "Israel"]
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
                    "What travel styles do you prefer? "
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
                "Here is your trip summary:\n"
                f"- Destination: {tr['destination']}\n"
                f"- Dates: {tr['departure_date']} -> {tr['return_date']}\n"
                f"- Budget: ${tr['budget']:.0f}\n"
                f"- Style: {', '.join(styles)}\n\n"
                "Shall I proceed with planning? (yes / no)"
            )

    elif prompt.strip().lower() in ("yes", "y"):
        state["travel_request"] = tr
        state["messages"].append({"role": "assistant", "content": "On it. Planning your trip..."})
        _run_planning(state)
        return

    elif prompt.strip().lower() in ("no", "n"):
        state["travel_request"] = {}
        reply = "No problem. Where would you like to travel?"

    else:
        reply = "Please reply with yes to proceed or no to start over."

    state["travel_request"] = tr
    state["messages"].append({"role": "assistant", "content": reply})


if state["phase"] != "done":
    if prompt := st.chat_input("Message SkySwift AI..."):
        state["messages"].append({"role": "user", "content": prompt})
        try:
            new_state = graph.invoke(state)
            st.session_state.state = new_state
        except ConnectionError:
            state["messages"].append({
                "role": "assistant",
                "content": "Cannot reach the travel data server. Run: uvicorn mock_server:app --port 8000",
            })
            st.session_state.state = state
        except Exception as e:
            state["messages"].append({"role": "assistant", "content": f"Unexpected error: {e}"})
            st.session_state.state = state
        st.rerun()
