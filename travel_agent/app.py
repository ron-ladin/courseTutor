from __future__ import annotations

from datetime import date as date_type
from html import escape
import time
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
_STREAM_DELAY_SECONDS = 0.025


st.set_page_config(
    page_title="SkySwift AI",
    layout="centered",
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        :root {
            --ink: #0f172a;
            --ink-2: #334155;
            --muted: #64748b;
            --line: #e2e8f0;
            --soft: #f8fafc;
            --teal: #0d9488;
            --teal-light: #14b8a6;
            --teal-bg: #f0fdfa;
            --teal-border: #99f6e4;
            --amber: #f59e0b;
            --red: #ef4444;
            --user-bg: #eff6ff;
            --user-border: #bfdbfe;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background: #f8fafc;
            color: var(--ink);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] { display: none !important; }

        .block-container {
            max-width: 860px;
            padding: 0 20px 130px;
        }

        /* ── Top bar ── */
        .topbar {
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(248,250,252,0.92);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--line);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            margin-bottom: 24px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-mark {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            display: grid;
            place-items: center;
            font-size: 1.1rem;
        }

        .brand-name {
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.02em;
        }

        .brand-badge {
            font-size: 0.65rem;
            font-weight: 700;
            color: var(--teal);
            background: var(--teal-bg);
            border: 1px solid var(--teal-border);
            border-radius: 999px;
            padding: 2px 7px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .reset-wrap .stButton > button {
            min-height: 32px;
            padding: 0 14px;
            border-radius: 8px;
            border: 1px solid var(--line);
            background: white;
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 600;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .reset-wrap .stButton > button:hover {
            border-color: #cbd5e1;
            color: var(--ink-2);
        }

        /* ── Landing hero ── */
        .hero {
            padding: 72px 0 52px;
            text-align: center;
        }

        .hero-icon {
            font-size: 3rem;
            margin-bottom: 18px;
            display: block;
        }

        .hero-title {
            margin: 0 0 14px;
            font-size: clamp(2.6rem, 8vw, 5rem);
            font-weight: 900;
            letter-spacing: -0.04em;
            line-height: 1;
            color: var(--ink);
        }

        .hero-title span {
            background: linear-gradient(135deg, var(--teal) 0%, #06b6d4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-sub {
            margin: 0 0 36px;
            font-size: clamp(1rem, 2.5vw, 1.25rem);
            color: var(--muted);
            font-weight: 400;
        }

        .hero-pills {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 8px;
            margin-bottom: 40px;
        }

        .pill {
            background: white;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 6px 14px;
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--ink-2);
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }

        /* ── Chat messages ── */
        .chat-wrap {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        div[data-testid="stChatMessage"] {
            background: transparent;
            border: none;
            box-shadow: none;
            padding: 4px 0;
        }

        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: var(--user-bg);
            border: 1px solid var(--user-border);
            border-radius: 12px;
            padding: 8px 12px;
        }

        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            line-height: 1.7;
            font-size: 0.95rem;
        }

        /* ── Chat input ── */
        [data-testid="stChatInput"] {
            max-width: 820px;
            margin: 0 auto;
        }

        [data-testid="stChatInput"] textarea {
            border-radius: 12px;
            border: 1px solid var(--line);
            background: white;
            box-shadow: 0 4px 24px rgba(15,23,42,0.08), 0 1px 4px rgba(15,23,42,0.04);
            font-size: 0.95rem;
            min-height: 56px;
        }

        [data-testid="stChatInput"] textarea:focus {
            border-color: var(--teal-light);
            box-shadow: 0 0 0 3px rgba(20,184,166,0.12), 0 4px 24px rgba(15,23,42,0.08);
        }

        [data-testid="stChatInput"] button {
            border-radius: 10px;
            background: var(--teal);
            color: white;
        }

        /* ── Cards ── */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--line) !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 3px rgba(15,23,42,0.06) !important;
            background: white;
        }

        .itin-header-good {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            margin-bottom: 4px;
            font-size: 0.85rem;
            font-weight: 600;
            color: #15803d;
        }

        .itin-header-warn {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: #fffbeb;
            border: 1px solid #fde68a;
            border-radius: 8px;
            margin-bottom: 4px;
            font-size: 0.85rem;
            font-weight: 600;
            color: #92400e;
        }

        .option-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--ink);
            margin: 12px 0 10px;
        }

        .stat-block {
            background: var(--soft);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 14px 16px;
            min-height: 104px;
        }

        .stat-label {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--muted);
            margin-bottom: 4px;
        }

        .stat-val {
            font-size: 1rem;
            font-weight: 700;
            color: var(--ink);
        }

        .stat-sub {
            font-size: 0.78rem;
            color: var(--muted);
            margin-top: 2px;
        }

        .activity-area {
            margin-top: 14px;
        }

        .activity-label {
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--muted);
            margin-bottom: 8px;
        }

        .activity-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .activity-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border: 1px solid var(--line);
            background: #ffffff;
            border-radius: 999px;
            padding: 7px 10px;
            font-size: 0.84rem;
            font-weight: 600;
            color: var(--ink-2);
        }

        .activity-chip small {
            color: var(--teal);
            font-weight: 800;
        }

        /* ── Buttons ── */
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.15s;
        }

        .stButton > button[kind="primary"] {
            background: var(--teal);
            border: 1px solid var(--teal);
            color: white;
            box-shadow: 0 2px 8px rgba(13,148,136,0.3);
        }

        .stButton > button[kind="primary"]:hover {
            background: #0f766e;
            border-color: #0f766e;
            box-shadow: 0 4px 16px rgba(13,148,136,0.35);
            transform: translateY(-1px);
        }

        .stButton > button[kind="secondary"] {
            background: white;
            border: 1px solid var(--line);
            color: var(--ink-2);
        }

        .stButton > button[kind="secondary"]:hover {
            border-color: #cbd5e1;
            background: var(--soft);
        }

        /* ── Divider ── */
        hr { border-color: var(--line); }

        /* ── Booking confirmed ── */
        .booking-card {
            background: linear-gradient(135deg, #f0fdfa 0%, #ecfdf5 100%);
            border: 1px solid var(--teal-border);
            border-radius: 16px;
            padding: 32px;
            text-align: center;
            margin: 16px 0;
        }

        .booking-icon { font-size: 3rem; margin-bottom: 12px; }
        .booking-title { font-size: 1.6rem; font-weight: 800; color: var(--ink); margin-bottom: 6px; }
        .booking-id {
            display: inline-block;
            font-family: monospace;
            font-size: 0.82rem;
            background: white;
            border: 1px solid var(--teal-border);
            border-radius: 8px;
            padding: 6px 14px;
            color: var(--teal);
            font-weight: 600;
            margin: 10px 0 20px;
        }

        .booking-detail {
            font-size: 0.95rem;
            color: var(--ink-2);
            font-weight: 500;
        }

        @media (max-width: 640px) {
            .hero { padding: 48px 0 36px; }
            .hero-title { font-size: 2.4rem; }
            .block-container { padding: 0 14px 120px; }
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
                <div class="brand-mark">✈️</div>
                <span class="brand-name">SkySwift</span>
                <span class="brand-badge">AI</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if show_reset:
            st.markdown('<div class="reset-wrap">', unsafe_allow_html=True)
            if st.button("↺ Reset", use_container_width=True):
                _reset_trip()
            st.markdown("</div>", unsafe_allow_html=True)


def _render_landing() -> None:
    st.markdown(
        """
        <div class="hero">
          <span class="hero-icon">✈️</span>
          <h1 class="hero-title">Travel smarter<br>with <span>SkySwift AI</span></h1>
          <p class="hero-sub">Tell me where you want to go — I'll handle the rest.</p>
          <div class="hero-pills">
            <span class="pill">🗺 Any destination</span>
            <span class="pill">💸 Any budget</span>
            <span class="pill">🏨 Hotels included</span>
            <span class="pill">🎯 Activities matched</span>
            <span class="pill">⚡ Real-time prices</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_trip_card(index: int, itin: Itinerary, confirmed) -> None:
    activities = itin.activities[:4]
    activity_chips = "".join(
        f'<span class="activity-chip">{escape(a.name)} <small>${a.price:,.0f}</small></span>'
        for a in activities
    ) or '<span class="activity-chip">No paid activities selected</span>'
    is_over = itin.is_partial_fallback and confirmed
    gap = (itin.total_cost - confirmed.budget) if is_over and confirmed else 0

    with st.container(border=True):
        if is_over:
            st.markdown(
                f'<div class="itin-header-warn">⚠️ Option {index + 1} — Over budget by ${gap:,.0f} &nbsp;|&nbsp; Match: {itin.match_score:.0%}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="itin-header-good">✅ Option {index + 1} — Within budget &nbsp;|&nbsp; Match: {itin.match_score:.0%}</div>',
                unsafe_allow_html=True,
            )

        option_titles = ["Best value", "Balanced pick", "Comfort upgrade"]
        title = option_titles[index] if index < len(option_titles) else "Trip package"
        st.markdown(
            f'<div class="option-title">Option {index + 1}: {title}</div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f"""<div class="stat-block">
                  <div class="stat-label">✈️ Flight</div>
                  <div class="stat-val">{escape(itin.flight.airline)}</div>
                  <div class="stat-sub">${itin.flight.price:,.0f} &nbsp;·&nbsp; {itin.flight.duration_hours}h</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""<div class="stat-block">
                  <div class="stat-label">🏨 Hotel</div>
                  <div class="stat-val">{escape(itin.hotel.name)}</div>
                  <div class="stat-sub">${itin.hotel.price_per_night:,.0f}/night &nbsp;·&nbsp; {"⭐" * itin.hotel.stars}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""<div class="stat-block">
                  <div class="stat-label">💰 Total</div>
                  <div class="stat-val">${itin.total_cost:,.0f}</div>
                  <div class="stat-sub">Full package</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="activity-area">
              <div class="activity-label">Activities included</div>
              <div class="activity-list">{activity_chips}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

        if st.button(
            f"Select Option {index + 1} →",
            key=f"select_{index}",
            type="primary" if index == 0 else "secondary",
            use_container_width=True,
        ):
            state["selected_itinerary"] = itin
            state["phase"] = "collect"
            st.session_state.state = state
            st.session_state.show_payment_modal = True
            st.rerun()


def _reset_trip() -> None:
    st.session_state.graph = build_graph()
    st.session_state.state = _empty_state()
    st.rerun()


def _has_user_message(state: AgentState) -> bool:
    return any(message.get("role") == "user" for message in state.get("messages", []))


def _message_key(index: int, message: dict) -> str:
    return f"{index}:{message.get('role', '')}:{message.get('content', '')}"


def _stream_markdown(text: str) -> None:
    placeholder = st.empty()
    rendered = ""
    chunks = text.split(" ")

    for index, chunk in enumerate(chunks):
        rendered += chunk
        if index < len(chunks) - 1:
            rendered += " "
        placeholder.markdown(rendered)
        time.sleep(_STREAM_DELAY_SECONDS)


def _render_chat_history(messages: list[dict]) -> None:
    animated_key = st.session_state.get("pending_stream_message_key")

    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    for index, msg in enumerate(messages):
        role = msg.get("role", "assistant")
        content = str(msg.get("content", ""))
        key = _message_key(index, msg)

        with st.chat_message(role):
            if role == "assistant" and key == animated_key:
                _stream_markdown(content)
                st.session_state.pending_stream_message_key = None
            else:
                st.write(content)
    st.markdown("</div>", unsafe_allow_html=True)


_inject_theme()

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "state" not in st.session_state:
    st.session_state.state = _empty_state()
if "pending_stream_message_key" not in st.session_state:
    st.session_state.pending_stream_message_key = None

state: AgentState = st.session_state.state
graph = st.session_state.graph

if not state["messages"]:
    new_state = graph.invoke(state)
    st.session_state.state = new_state
    st.rerun()

# Show payment confirmation modal
if st.session_state.get("show_payment_modal") and state.get("selected_itinerary"):
    itin = state["selected_itinerary"]
    st.markdown(
        f"""
        <style>
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(15, 23, 42, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999;
        }}
        .modal-content {{
            background: white;
            border-radius: 16px;
            padding: 32px;
            max-width: 480px;
            box-shadow: 0 20px 60px rgba(15, 23, 42, 0.3);
            text-align: center;
        }}
        .modal-title {{
            font-size: 1.5rem;
            font-weight: 900;
            color: #0f172a;
            margin-bottom: 16px;
        }}
        .modal-price {{
            font-size: 2.2rem;
            font-weight: 900;
            color: #0d9488;
            margin: 16px 0;
        }}
        .modal-text {{
            font-size: 1rem;
            color: #64748b;
            margin-bottom: 24px;
            line-height: 1.6;
        }}
        .modal-buttons {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 480px;
            display: flex;
            gap: 12px;
            z-index: 1000;
        }}
        </style>
        <div class="modal-overlay">
          <div class="modal-content">
            <div style="font-size:2.5rem;margin-bottom:16px">✈️</div>
            <div class="modal-title">Trip Selected!</div>
            <div class="modal-price">${itin.total_cost:,.0f}</div>
            <div class="modal-text">
              You've selected <b>{itin.flight.airline}</b> + <b>{itin.hotel.name}</b>
            </div>
            <div class="modal-text" style="color: #334155; font-weight: 600;">
              Proceed to payment to complete your booking
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Options", use_container_width=True, key="modal_back"):
            state["selected_itinerary"] = None
            state["phase"] = "rank"
            st.session_state.state = state
            st.session_state.show_payment_modal = False
            st.rerun()
    with col2:
        if st.button("💳 Go to Payment →", type="primary", use_container_width=True, key="modal_payment"):
            st.session_state.show_payment_modal = False
            st.rerun()

conversation_started = _has_user_message(state)
_render_topbar(show_reset=conversation_started or state["phase"] != "onboard")

# Early exit if modal is showing - don't render other phase content
if st.session_state.get("show_payment_modal") and state.get("selected_itinerary"):
    st.stop()

if not state["messages"]:
    _render_landing()
else:
    _render_chat_history(state["messages"])


# ── Reasoning panel ───────────────────────────────────────────────────────────
if state["reasoning_log"] and st.session_state.get("show_debug_reasoning", False):
    with st.expander("🧠 Agent Reasoning", expanded=False):
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
        st.markdown(
            f"<div style='font-size:0.9rem;color:#64748b;margin-bottom:16px'>"
            f"🗺 <b>{confirmed.destination}</b> &nbsp;·&nbsp; "
            f"{confirmed.departure_date} → {confirmed.return_date} ({nights} nights) &nbsp;·&nbsp; "
            f"Budget <b>${confirmed.budget:,.0f}</b> &nbsp;·&nbsp; "
            f"Style: {', '.join(confirmed.travel_style)}"
            f"</div>",
            unsafe_allow_html=True,
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
                f"All options slightly exceed your budget. "
                f"The closest option needs **${min_gap:,.0f} more**. You can still book it."
            )

        st.markdown(
            "<h3 style='font-size:1.3rem;font-weight:800;margin:8px 0 18px;color:#0f172a'>Your Itinerary Options</h3>",
            unsafe_allow_html=True,
        )
        for i, itin in enumerate(itins):
            _render_trip_card(i, itin, confirmed)

        st.write("")
        if st.button("← Change Trip Details", type="secondary"):
            st.session_state.state = _empty_state()
            st.rerun()


# ── Collect phase: Tabs for Order + Payment ────────────────────────────────
if state["phase"] == "collect" and state["selected_itinerary"]:
    itin: Itinerary = state["selected_itinerary"]
    st.divider()

    # Create tabs
    tab_order, tab_payment, tab_confirm = st.tabs(["📋 Order Review", "💳 Payment", "✅ Confirmation"])

    # TAB 1: Order Review
    with tab_order:
        st.markdown(
            "<h3 style='font-size:1.3rem;font-weight:800;margin-bottom:20px'>Your Trip</h3>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("<div style='font-size:0.85rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.06em'>📍 Destination</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.2rem;font-weight:800;color:#0f172a;margin:8px 0'>{itin.flight.destination}</div>", unsafe_allow_html=True)
            from datetime import date as _date
            confirmed = state.get("confirmed_request")
            if confirmed:
                nights = (_date.fromisoformat(str(confirmed.return_date)) - _date.fromisoformat(str(confirmed.departure_date))).days
                st.write(f"{confirmed.departure_date} → {confirmed.return_date} ({nights} nights)")

        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown("<div style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.06em'>✈️ Flight</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.1rem;font-weight:800'>{escape(itin.flight.airline)}</div>", unsafe_allow_html=True)
                st.write(f"${itin.flight.price:,.0f}")
                st.write(f"{itin.flight.duration_hours}h flight")
        with c2:
            with st.container(border=True):
                st.markdown("<div style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.06em'>🏨 Hotel</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.1rem;font-weight:800'>{escape(itin.hotel.name)}</div>", unsafe_allow_html=True)
                st.write(f"${itin.hotel.price_per_night:,.0f}/night")
                st.write(f"{'⭐' * itin.hotel.stars}")
        with c3:
            with st.container(border=True):
                st.markdown("<div style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.06em'>💰 Total</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.4rem;font-weight:900;color:#0d9488'>${itin.total_cost:,.0f}</div>", unsafe_allow_html=True)
                st.write("Total package price")

        st.write("")
        st.markdown("<div style='font-size:0.9rem;font-weight:700;margin-bottom:10px'>🎯 Included Activities</div>", unsafe_allow_html=True)
        activities = ", ".join(a.name for a in itin.activities) or "None"
        st.write(activities)

        st.write("")
        if st.button("← Go Back to Options", type="secondary", use_container_width=True):
            state["phase"] = "rank"
            st.session_state.state = state
            st.rerun()

    # TAB 2: Payment
    with tab_payment:
        st.markdown(
            "<h3 style='font-size:1.3rem;font-weight:800;margin-bottom:20px'>Payment Details</h3>",
            unsafe_allow_html=True,
        )

        st.info("🎯 Demo Mode — Enter any valid card details (no real charge)")

        st.markdown("<div style='font-size:0.9rem;font-weight:700;margin-bottom:14px'>Card Information</div>", unsafe_allow_html=True)

        pay = state.get("payment_info", {})
        card_num = st.text_input(
            "Card Number *",
            value=pay.get("card_number", ""),
            placeholder="4532 1234 5678 9010",
            key="payment_card",
        )

        c1, c2 = st.columns(2)
        with c1:
            card_exp = st.text_input(
                "Expiry (MM/YY) *",
                value=pay.get("card_expiry", ""),
                placeholder="12/26",
                key="payment_expiry",
            )
        with c2:
            card_cvc = st.text_input(
                "CVC *",
                value=pay.get("card_cvc", ""),
                placeholder="123",
                key="payment_cvc",
                type="password",
            )

        card_name = st.text_input(
            "Cardholder Name *",
            value=pay.get("cardholder_name", ""),
            placeholder="JOHN DOE",
            key="payment_name",
        )

        st.write("")
        st.markdown("<div style='font-size:0.9rem;font-weight:700;margin-bottom:14px'>Billing Address</div>", unsafe_allow_html=True)

        c = state.get("contact_info", {})
        email = st.text_input(
            "Email *",
            value=c.get("email", ""),
            placeholder="you@example.com",
            key="billing_email",
        )
        phone = st.text_input(
            "Phone *",
            value=c.get("phone", ""),
            placeholder="+1 (555) 123-4567",
            key="billing_phone",
        )

        # Update payment state
        last4 = card_num.replace(" ", "")[-4:] if card_num else "0000"
        state["payment_info"] = {
            "card_number": card_num,
            "card_expiry": card_exp,
            "cardholder_name": card_name,
            "card_cvc": card_cvc,
            "card_last4": last4,
        }
        state["contact_info"] = {"email": email, "phone": phone}

    # TAB 3: Confirmation
    with tab_confirm:
        st.markdown(
            "<h3 style='font-size:1.3rem;font-weight:800;margin-bottom:20px'>Passenger Information</h3>",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='font-size:0.9rem;font-weight:700;margin-bottom:14px'>Passenger Details</div>", unsafe_allow_html=True)

        p = state.get("passenger_info", {})
        c1, c2 = st.columns(2)
        with c1:
            full_name = st.text_input(
                "Full Name *",
                value=p.get("full_name", ""),
                placeholder="John Doe",
                key="passenger_name",
            )
        with c2:
            passport = st.text_input(
                "Passport Number *",
                value=p.get("passport_number", ""),
                placeholder="AB123456789",
                key="passenger_passport",
            )

        # Update state
        state["passenger_info"] = {"full_name": full_name, "passport_number": passport}

        st.write("")
        st.markdown("<div style='font-size:1rem;font-weight:800;margin-bottom:16px;margin-top:16px'>📋 Review & Book</div>", unsafe_allow_html=True)

        # Summary
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("🎫 Passenger", full_name or "—")
            with c2:
                st.metric("💳 Payment Method", "Card" if state["payment_info"].get("card_last4") else "—")
            with c3:
                st.metric("💰 Total Cost", f"${itin.total_cost:,.0f}")

        st.write("")
        col_book, col_back = st.columns([2, 1])
        with col_book:
            if st.button("✅ Complete Booking", type="primary", use_container_width=True):
                if full_name and passport and state["payment_info"].get("card_number") and state["contact_info"].get("email"):
                    state["phase"] = "confirm"
                    st.session_state.state = state
                    st.rerun()
                else:
                    st.error("❌ Please fill all required fields (* marked)")
        with col_back:
            if st.button("← Back", use_container_width=True):
                state["phase"] = "rank"
                st.session_state.state = state
                st.rerun()


# ── Confirm phase ─────────────────────────────────────────────────────────────
if state["phase"] == "confirm" and state["selected_itinerary"]:
    itin: Itinerary = state["selected_itinerary"]
    st.divider()
    st.markdown(
        "<h3 style='font-size:1.2rem;font-weight:800;margin-bottom:14px'>Order Summary</h3>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        if itin.is_partial_fallback:
            st.warning("⚠️ This package exceeds your stated budget.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Destination** &nbsp; {itin.flight.destination}")
            st.markdown(f"**Flight** &nbsp; {itin.flight.airline} — ${itin.flight.price:,.0f}")
            st.markdown(f"**Hotel** &nbsp; {itin.hotel.name} — ${itin.hotel.price_per_night:,.0f}/night")
        with c2:
            st.markdown(f"**Activities** &nbsp; {', '.join(a.name for a in itin.activities) or 'None'}")
            st.markdown(f"**Total Cost** &nbsp; **${itin.total_cost:,.0f}**")
            st.markdown(f"**Match Score** &nbsp; {itin.match_score:.0%}")

    p   = state.get("passenger_info", {})
    c   = state.get("contact_info",   {})
    pay = state.get("payment_info",   {})
    with st.container(border=True):
        st.markdown(f"👤 **{p.get('full_name', '—')}** &nbsp;·&nbsp; Passport: `{p.get('passport_number', '—')}`")
        st.markdown(f"📧 {c.get('email', '—')} &nbsp;·&nbsp; 📱 {c.get('phone', '—')}")
        st.markdown(f"💳 **** {pay.get('card_last4', '—')} &nbsp;(exp {pay.get('card_expiry', '—')})")

    st.write("")
    col_book, col_back = st.columns([3, 1])
    with col_book:
        if st.button("✅ Confirm & Book Now", type="primary", use_container_width=True):
            new_state = graph.invoke(state)
            st.session_state.state = new_state
            st.rerun()
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.state = _empty_state()
            st.rerun()


# ── Done ──────────────────────────────────────────────────────────────────────
if state["phase"] == "done" and state["booking"]:
    st.divider()
    itin = state.get("selected_itinerary")
    dest = itin.flight.destination if itin else "your destination"
    airline = itin.flight.airline if itin else ""
    hotel = itin.hotel.name if itin else ""
    total = f"${itin.total_cost:,.0f}" if itin else ""

    st.markdown(
        f"""
        <div class="booking-card">
          <div class="booking-icon">🎉</div>
          <div class="booking-title">You're going to {dest}!</div>
          <div class="booking-id">Booking ID: {state['booking'].booking_id}</div>
          <div class="booking-detail">{airline} &nbsp;·&nbsp; {hotel} &nbsp;·&nbsp; {total}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    if st.button("✈️ Plan Another Trip", type="primary", use_container_width=False):
        st.session_state.state = _empty_state()
        st.rerun()


# ── Chat input (onboard + collect phases only) ────────────────────────────────
if state["phase"] in ("onboard", "collect"):
    if prompt := st.chat_input("Where would you like to go?"):
        state["messages"].append({"role": "user", "content": prompt})
        st.session_state.state = state
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    new_state = graph.invoke(state)
                    for index in range(len(new_state["messages"]) - 1, -1, -1):
                        if new_state["messages"][index].get("role") == "assistant":
                            st.session_state.pending_stream_message_key = _message_key(
                                index,
                                new_state["messages"][index],
                            )
                            break
                    st.session_state.state = new_state
                except Exception as e:
                    state["messages"].append({"role": "assistant", "content": f"Error: {e}"})
                    st.session_state.pending_stream_message_key = _message_key(
                        len(state["messages"]) - 1,
                        state["messages"][-1],
                    )
                    st.session_state.state = state
        st.rerun()
