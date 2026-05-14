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

        .stat-block {
            background: var(--soft);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 14px 16px;
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
    activities = ", ".join(a.name for a in itin.activities) or "None selected"
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

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f"""<div class="stat-block">
                  <div class="stat-label">✈️ Flight</div>
                  <div class="stat-val">{itin.flight.airline}</div>
                  <div class="stat-sub">${itin.flight.price:,.0f} &nbsp;·&nbsp; {itin.flight.duration_hours}h</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""<div class="stat-block">
                  <div class="stat-label">🏨 Hotel</div>
                  <div class="stat-val">{itin.hotel.name}</div>
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

        st.markdown(f"<div style='margin:10px 0 4px;font-size:0.82rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.06em'>🎯 Activities</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.92rem;color:#334155'>{activities}</div>", unsafe_allow_html=True)
        st.write("")

        if st.button(
            f"Select Option {index + 1} →",
            key=f"select_{index}",
            type="primary" if index == 0 else "secondary",
            use_container_width=True,
        ):
            state["selected_itinerary"] = itin
            state["phase"] = "collect"
            new_state = graph.invoke(state)
            st.session_state.state = new_state
            st.rerun()


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
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    for msg in state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    st.markdown("</div>", unsafe_allow_html=True)


# ── Reasoning panel ───────────────────────────────────────────────────────────
if state["reasoning_log"]:
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
                    st.session_state.state = new_state
                except Exception as e:
                    state["messages"].append({"role": "assistant", "content": f"Error: {e}"})
                    st.session_state.state = state
        st.rerun()
