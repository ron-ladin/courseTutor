# Design Document: Travel Planning Agent

## Overview

A locally-running conversational travel planner built for a 20-hour hackathon. The system uses a Streamlit chat UI, a LangGraph state machine for conversation and planning orchestration, Pydantic for data validation, and a local FastAPI mock server that mimics the Amadeus and Booking.com APIs — no external network calls.

The design is intentionally minimal: five Python modules, a single FastAPI server, and a single Streamlit entry point. Every component maps directly to a requirement so the team can divide work cleanly.

---

## Architecture

```
uvicorn mock_server:app        streamlit run app.py
        │                               │
        ▼                               ▼
┌─────────────────┐      ┌──────────────────────────────────┐
│  mock_server.py │      │         app.py (Streamlit UI)    │
│  FastAPI app    │      │  - Chat message history          │
│  localhost:8000 │      │  - ReasoningPanel expander       │
│                 │      │  - Itinerary cards + booking     │
│  GET /flights/  │      └──────────────┬───────────────────┘
│  GET /hotels/   │                     │ calls
│  GET /activities│                     ▼
└────────┬────────┘      ┌──────────────────────────────────┐
         │ HTTP          │      agent.py (LangGraph Graph)  │
         │               │  Nodes: onboard→plan→rank→confirm│
         ▼               │  State: AgentState (TypedDict)   │
┌─────────────────┐      └──────┬───────────────────────────┘
│  data_client.py │◄────────────┘
│  HTTP client    │      calls planner.py
│  → typed models │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐      ┌─────────────┐
│      planner.py         │      │  models.py  │
│  PlanningLoop +         │◄─────│  Pydantic   │
│  MatchScore engine      │      │  models     │
└─────────────────────────┘      └─────────────┘
```

### File Layout

```
travel_agent/
├── app.py              # Streamlit entry point
├── agent.py            # LangGraph graph definition
├── models.py           # Pydantic models
├── planner.py          # PlanningLoop + MatchScore engine
├── data_client.py      # HTTP client → calls mock_server
└── mock_server.py      # FastAPI mock server (localhost:8000)
```

---

## Mock Server (`mock_server.py`)

A single FastAPI app with three routers, modeled after Amadeus (flights) and Booking.com (hotels) API conventions. All data is hardcoded in the server — no JSON files.

```python
from fastapi import FastAPI, Query
from models import Flight, Hotel, Activity

app = FastAPI(title="Travel Mock API")

# ── hardcoded data ──────────────────────────────────────────────────────────
_DATA = {
    "Tokyo": {
        "flights": [
            Flight(id="f1", destination="Tokyo", price=650, airline="ANA",    duration_hours=14, style_tags=["adventure","culture"]),
            Flight(id="f2", destination="Tokyo", price=820, airline="JAL",    duration_hours=12, style_tags=["luxury","culture"]),
        ],
        "hotels": [
            Hotel(id="h1", destination="Tokyo", name="Shinjuku Inn",    price_per_night=120, stars=3, style_tags=["budget","culture"]),
            Hotel(id="h2", destination="Tokyo", name="Park Hyatt Tokyo",price_per_night=450, stars=5, style_tags=["luxury"]),
        ],
        "activities": [
            Activity(id="a1", destination="Tokyo", name="Tsukiji Market Tour", price=30,  style_tags=["culture","food"]),
            Activity(id="a2", destination="Tokyo", name="Mt. Fuji Day Trip",   price=80,  style_tags=["adventure","nature"]),
            Activity(id="a3", destination="Tokyo", name="Akihabara Walk",      price=0,   style_tags=["culture"]),
        ],
    },
    "Paris": {
        "flights": [
            Flight(id="f3", destination="Paris", price=400, airline="Air France", duration_hours=8,  style_tags=["romance","culture"]),
            Flight(id="f4", destination="Paris", price=550, airline="Lufthansa",  duration_hours=9,  style_tags=["luxury","romance"]),
        ],
        "hotels": [
            # All Paris hotels > $1,500 — triggers backtracking demo
            Hotel(id="h3", destination="Paris", name="Le Grand Hotel", price_per_night=1800, stars=5, style_tags=["luxury","romance"]),
            Hotel(id="h4", destination="Paris", name="Hotel Lumiere",  price_per_night=1600, stars=4, style_tags=["romance"]),
        ],
        "activities": [
            Activity(id="a4", destination="Paris", name="Eiffel Tower Visit", price=25, style_tags=["romance","culture"]),
            Activity(id="a5", destination="Paris", name="Louvre Museum",      price=17, style_tags=["culture","art"]),
            Activity(id="a6", destination="Paris", name="Seine River Cruise", price=15, style_tags=["romance"]),
        ],
    },
    "Bali": {
        "flights": [
            Flight(id="f5", destination="Bali", price=700, airline="Garuda",   duration_hours=18, style_tags=["adventure","nature"]),
            Flight(id="f6", destination="Bali", price=850, airline="Singapore",duration_hours=16, style_tags=["luxury","nature"]),
        ],
        "hotels": [
            Hotel(id="h5", destination="Bali", name="Ubud Jungle Resort",   price_per_night=90,  stars=3, style_tags=["nature","adventure"]),
            Hotel(id="h6", destination="Bali", name="Seminyak Beach Villa", price_per_night=200, stars=4, style_tags=["luxury","nature"]),
        ],
        "activities": [
            Activity(id="a7", destination="Bali", name="Rice Terrace Trek", price=20, style_tags=["adventure","nature"]),
            Activity(id="a8", destination="Bali", name="Temple Ceremony",   price=10, style_tags=["culture","nature"]),
            Activity(id="a9", destination="Bali", name="Surf Lesson",       price=45, style_tags=["adventure"]),
        ],
    },
    "New York": {
        "flights": [
            Flight(id="f7", destination="New York", price=300, airline="Delta",   duration_hours=6, style_tags=["culture","food"]),
            Flight(id="f8", destination="New York", price=420, airline="JetBlue", duration_hours=6, style_tags=["luxury","culture"]),
        ],
        "hotels": [
            Hotel(id="h7", destination="New York", name="Times Square Hotel", price_per_night=180, stars=3, style_tags=["culture","food"]),
            Hotel(id="h8", destination="New York", name="The Plaza",          price_per_night=600, stars=5, style_tags=["luxury"]),
        ],
        "activities": [
            Activity(id="a10", destination="New York", name="Central Park Walk", price=0,   style_tags=["nature","culture"]),
            Activity(id="a11", destination="New York", name="Broadway Show",     price=120, style_tags=["culture","art"]),
            Activity(id="a12", destination="New York", name="Food Tour",         price=65,  style_tags=["food","culture"]),
        ],
    },
}

# ── routes ──────────────────────────────────────────────────────────────────
@app.get("/flights/search", response_model=list[Flight])
def search_flights(destination: str, date: str = Query(...)):
    return _DATA.get(destination, {}).get("flights", [])

@app.get("/hotels/search", response_model=list[Hotel])
def search_hotels(destination: str, checkin: str, checkout: str,
                  max_price: float = Query(default=99999)):
    hotels = _DATA.get(destination, {}).get("hotels", [])
    return [h for h in hotels if h.price_per_night <= max_price]

@app.get("/activities/search", response_model=list[Activity])
def search_activities(destination: str):
    return _DATA.get(destination, {}).get("activities", [])

@app.get("/destinations")
def list_destinations():
    return {"destinations": list(_DATA.keys())}
```

Start with: `uvicorn mock_server:app --reload --port 8000`

---

## Data Client (`data_client.py`)

Thin HTTP wrapper — the only file that knows the server URL. The PlanningLoop imports this instead of a JSON provider.

```python
import httpx
from models import Flight, Hotel, Activity

BASE = "http://localhost:8000"

class DataClient:
    def get_flights(self, destination: str, date: str) -> list[Flight]:
        r = httpx.get(f"{BASE}/flights/search", params={"destination": destination, "date": date})
        r.raise_for_status()
        return [Flight(**f) for f in r.json()]

    def get_hotels(self, destination: str, checkin: str, checkout: str,
                   max_price: float = 99999) -> list[Hotel]:
        r = httpx.get(f"{BASE}/hotels/search",
                      params={"destination": destination, "checkin": checkin,
                              "checkout": checkout, "max_price": max_price})
        r.raise_for_status()
        return [Hotel(**h) for h in r.json()]

    def get_activities(self, destination: str) -> list[Activity]:
        r = httpx.get(f"{BASE}/activities/search", params={"destination": destination})
        r.raise_for_status()
        return [Activity(**a) for a in r.json()]

    def destinations(self) -> list[str]:
        r = httpx.get(f"{BASE}/destinations")
        r.raise_for_status()
        return r.json()["destinations"]
```

The `PlanningLoop` receives a `DataClient` instance (same interface as the old `MockDataProvider`) so no changes are needed in `planner.py` beyond swapping the import.

---

## Data Models (`models.py`)

```python
from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional
from uuid import UUID

class TravelRequest(BaseModel):
    destination: str
    departure_date: date
    return_date: date
    budget: float
    travel_style: list[str]  # e.g. ["adventure", "budget"]

    @field_validator("budget")
    @classmethod
    def budget_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Budget must be a positive number")
        return v

    @field_validator("return_date")
    @classmethod
    def return_after_departure(cls, v, info):
        if "departure_date" in info.data and v <= info.data["departure_date"]:
            raise ValueError("Return date must be after departure date")
        return v


class Flight(BaseModel):
    id: str
    destination: str
    price: float
    airline: str
    duration_hours: float
    style_tags: list[str]

class Hotel(BaseModel):
    id: str
    destination: str
    name: str
    price_per_night: float
    stars: int
    style_tags: list[str]

class Activity(BaseModel):
    id: str
    destination: str
    name: str
    price: float
    style_tags: list[str]

class Itinerary(BaseModel):
    flight: Flight
    hotel: Hotel
    activities: list[Activity]
    total_cost: float
    match_score: float = 0.0
    is_partial_fallback: bool = False

class BookingConfirmation(BaseModel):
    booking_id: UUID
    itinerary: Itinerary
```

---

## Mock Data Provider (`data/mock_data.json`)

> **Replaced by `mock_server.py` and `data_client.py`.** See the Mock Server section above. No JSON files are used.

---

## Planning Loop and Match Score Engine (`planner.py`)

### MatchScore Engine

```python
def compute_raw_score(item_tags: list[str], user_style: list[str]) -> float:
    """Dot product: count of overlapping tags."""
    return float(sum(1 for tag in item_tags if tag in user_style))

def aggregate_itinerary_tags(itinerary: Itinerary) -> list[str]:
    tags = itinerary.flight.style_tags + itinerary.hotel.style_tags
    for act in itinerary.activities:
        tags += act.style_tags
    return tags

def normalize_scores(scores: list[float]) -> list[float]:
    min_s, max_s = min(scores), max(scores)
    if max_s == min_s:
        return [1.0] * len(scores)
    return [(s - min_s) / (max_s - min_s) for s in scores]
```

### PlanningLoop

```python
def run_planning_loop(
    request: TravelRequest,
    provider: MockDataProvider,
    reasoning_log: list[str],
) -> list[Itinerary]:
    flights = sorted(provider.get_flights(request.destination), key=lambda f: f.price)
    backtrack_count = 0
    flight_index = 0
    itineraries = []

    while flight_index < len(flights):
        flight = flights[flight_index]
        remaining = request.budget - flight.price
        reasoning_log.append(f"Selected flight {flight.id} (${flight.price}). Remaining budget: ${remaining:.2f}")

        hotels = provider.get_hotels(request.destination)
        qualifying = [h for h in hotels if h.price_per_night <= remaining]

        if not qualifying:
            if backtrack_count == 0:
                reasoning_log.append(
                    f"No hotel fits remaining budget after flight {flight.id}. "
                    f"Backtracking to next cheapest flight."
                )
                backtrack_count += 1
                flight_index += 1
                continue
            else:
                # Partial fallback
                fallback_hotel = min(hotels, key=lambda h: h.price_per_night)
                reasoning_log.append(
                    f"Backtrack limit reached. Assembling partial fallback with hotel {fallback_hotel.name}."
                )
                itinerary = Itinerary(
                    flight=flight,
                    hotel=fallback_hotel,
                    activities=[],
                    total_cost=flight.price + fallback_hotel.price_per_night,
                    is_partial_fallback=True,
                )
                itineraries.append(itinerary)
                break

        # Select best hotel by match score
        hotel_scores = [
            compute_raw_score(h.style_tags, request.travel_style) for h in qualifying
        ]
        best_hotel = qualifying[hotel_scores.index(max(hotel_scores))]
        remaining_after_hotel = remaining - best_hotel.price_per_night
        reasoning_log.append(f"Selected hotel {best_hotel.name} (score={max(hotel_scores)}, ${best_hotel.price_per_night}/night)")

        # Greedy activity allocation
        activities = provider.get_activities(request.destination)
        activities_sorted = sorted(
            activities,
            key=lambda a: compute_raw_score(a.style_tags, request.travel_style),
            reverse=True,
        )
        selected_activities = []
        activity_budget = remaining_after_hotel
        for act in activities_sorted:
            if act.price <= activity_budget:
                selected_activities.append(act)
                activity_budget -= act.price

        total = flight.price + best_hotel.price_per_night + sum(a.price for a in selected_activities)
        itineraries.append(Itinerary(
            flight=flight,
            hotel=best_hotel,
            activities=selected_activities,
            total_cost=total,
        ))
        break  # One complete itinerary per planning run; extend for multi-option

    return itineraries
```

> For the hackathon MVP, the loop produces one primary itinerary. To reach 2–3 options, the caller runs the loop for each available flight and collects results, then ranks and trims to top 3.

---

## LangGraph Agent (`agent.py`)

### State

```python
from typing import TypedDict, Optional
from models import TravelRequest, Itinerary, BookingConfirmation

class AgentState(TypedDict):
    messages: list[dict]           # chat history [{role, content}]
    travel_request: Optional[dict] # partial TravelRequest fields
    confirmed_request: Optional[TravelRequest]
    itineraries: list[Itinerary]
    selected_itinerary: Optional[Itinerary]
    booking: Optional[BookingConfirmation]
    reasoning_log: list[str]
    backtrack_count: int
    phase: str  # "onboard" | "plan" | "rank" | "confirm" | "done"
```

### Graph Nodes

| Node | Responsibility |
|---|---|
| `onboard_node` | Asks questions one at a time, validates each answer, builds TravelRequest |
| `plan_node` | Calls `run_planning_loop`, appends to `reasoning_log` |
| `rank_node` | Applies MatchScore + normalization, sorts itineraries, appends trade-off analysis to log |
| `confirm_node` | Displays order summary, generates UUID BookingID on confirmation |

### Graph Edges

```
START → onboard_node
onboard_node → plan_node          (when phase == "plan")
onboard_node → onboard_node       (while collecting inputs)
plan_node → rank_node
rank_node → confirm_node          (when user selects itinerary)
rank_node → rank_node             (waiting for selection)
confirm_node → END
```

### Simplified Graph Definition

```python
from langgraph.graph import StateGraph, END
from agent_state import AgentState

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("onboard", onboard_node)
    g.add_node("plan", plan_node)
    g.add_node("rank", rank_node)
    g.add_node("confirm", confirm_node)

    g.set_entry_point("onboard")
    g.add_conditional_edges("onboard", route_onboard, {
        "continue": "onboard",
        "plan": "plan",
    })
    g.add_edge("plan", "rank")
    g.add_conditional_edges("rank", route_rank, {
        "wait": "rank",
        "confirm": "confirm",
    })
    g.add_edge("confirm", END)
    return g.compile()
```

---

## Streamlit UI (`app.py`)

### Layout

```
┌──────────────────────────────────────────────────────┐
│  🌍 Travel Planning Agent                            │
├──────────────────────────────────────────────────────┤
│  Chat messages (scrollable)                          │
│  ┌────────────────────────────────────────────────┐  │
│  │ 🤖 Hello! Where would you like to travel?      │  │
│  │ 👤 Tokyo                                       │  │
│  │ 🤖 Great! What are your travel dates?          │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ▼ Agent Reasoning  [collapsible expander]           │
│  ┌────────────────────────────────────────────────┐  │
│  │ • Selected flight f1 ($650). Remaining: $350   │  │
│  │ • Selected hotel Shinjuku Inn (score=2, $120)  │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  [Itinerary Card 1]  [Itinerary Card 2]              │
│                                                      │
│  [Text input]  [Send]                                │
└──────────────────────────────────────────────────────┘
```

### Key UI Patterns

```python
import streamlit as st
from agent import build_graph

# Session state initialization
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
    st.session_state.state = {
        "messages": [], "travel_request": {}, "confirmed_request": None,
        "itineraries": [], "selected_itinerary": None, "booking": None,
        "reasoning_log": [], "backtrack_count": 0, "phase": "onboard"
    }

# Render chat history
for msg in st.session_state.state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ReasoningPanel
with st.expander("🧠 Agent Reasoning", expanded=False):
    for entry in st.session_state.state["reasoning_log"]:
        st.write(f"• {entry}")
    if st.session_state.state["phase"] == "plan":
        st.write("⏳ Planning in progress...")

# Itinerary cards (rendered after planning)
if st.session_state.state["phase"] == "rank":
    for i, itin in enumerate(st.session_state.state["itineraries"]):
        with st.container(border=True):
            label = "⚠️ Exceeds Budget" if itin.is_partial_fallback else ""
            st.subheader(f"Option {i+1} — Score: {itin.match_score:.2f} {label}")
            st.write(f"✈️ Flight: {itin.flight.id} (${itin.flight.price})")
            st.write(f"🏨 Hotel: {itin.hotel.name} (${itin.hotel.price_per_night}/night)")
            st.write(f"🎯 Activities: {', '.join(a.name for a in itin.activities)}")
            st.write(f"💰 Total: ${itin.total_cost:.2f}")
            if st.button(f"Select Option {i+1}", key=f"select_{i}"):
                # update state and rerun
                pass

# User input
if prompt := st.chat_input("Type your response..."):
    # invoke graph with new user message
    pass
```

---

## Onboarding Conversation Flow

```
Agent: "Hello! I'm your travel planning assistant. Where would you like to travel?"
User:  "Tokyo"
Agent: "Great choice! What are your travel dates? (format: YYYY-MM-DD to YYYY-MM-DD)"
User:  "2025-03-10 to 2025-03-17"
Agent: "What is your total budget in USD?"
User:  "1500"
Agent: "What travel styles do you prefer? (e.g. adventure, culture, luxury, romance, nature, food, budget)"
User:  "adventure, culture"
Agent: "Here's a summary of your trip:
        • Destination: Tokyo
        • Dates: 2025-03-10 → 2025-03-17
        • Budget: $1,500
        • Style: adventure, culture
        Shall I proceed with planning? (yes/no)"
User:  "yes"
→ Transitions to PlanningLoop
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Non-positive budget | Re-prompt: "Please enter a positive number for your budget." |
| Return date ≤ departure date | Re-prompt: "Return date must be after departure date." |
| Destination not in server data | Re-prompt with list of available destinations from `GET /destinations` |
| Pydantic validation failure at confirm | Display error message, return to affected question |
| No itineraries produced | Display "Unable to find a matching itinerary. Please restart with a higher budget." |
| MockServer not running | Display "Cannot reach the travel data server. Run: `uvicorn mock_server:app --port 8000`" |
| HTTP error from server | Display "Travel data service error. Please restart the server and try again." |

---

## Team Division of Work

| Member | Module | Est. Hours |
|---|---|---|
| Dev 1 | `models.py` | 2h |
| Dev 2 | `mock_server.py` + `data_client.py` + `planner.py` | 6h |
| Dev 3 | `agent.py` (LangGraph graph + nodes) | 6h |
| Dev 4 | `app.py` (Streamlit UI + ReasoningPanel) | 5h |
| All | Integration + testing | 1h |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Onboarding sequence advances in order

*For any* sequence of four valid answers provided to the onboarding flow, the TravelRequest fields should be populated in the order destination → departure_date → return_date → budget → travel_style, and each question asked should correspond to the next unpopulated field.

**Validates: Requirements 1.2**

---

### Property 2: Budget validation rejects non-positive values

*For any* input value that is zero, negative, or non-numeric when provided as a budget, the agent should reject it and the question sequence should not advance.

**Validates: Requirements 1.4**

---

### Property 3: Date validation rejects invalid ranges

*For any* pair of dates where the departure date is on or after the return date, the agent should reject the input and the question sequence should not advance.

**Validates: Requirements 1.5**

---

### Property 4: MockDataProvider data completeness

*For any* destination in the MockDataProvider, it should supply at least 2 flights, at least 2 hotels, and at least 3 activities, each with a numeric price and a non-empty list of style tags.

**Validates: Requirements 2.2, 2.5**

---

### Property 5: Flight selection is minimum-cost

*For any* list of available flights for a destination, the PlanningLoop should select the flight with the lowest price as its first choice.

**Validates: Requirements 3.1**

---

### Property 6: Hotel search respects remaining budget

*For any* combination of total budget and selected flight price, the set of hotels considered by the PlanningLoop should contain only hotels whose price does not exceed (budget − flight_price).

**Validates: Requirements 3.2**

---

### Property 7: Hotel selection maximizes MatchScore

*For any* set of budget-qualifying hotels with distinct MatchScores, the PlanningLoop should select the hotel with the highest MatchScore.

**Validates: Requirements 3.3**

---

### Property 8: Activity allocation stays within budget

*For any* activity allocation produced by the PlanningLoop, the sum of selected activity prices should not exceed the remaining budget after flight and hotel costs.

**Validates: Requirements 3.4**

---

### Property 9: BacktrackIteration never exceeds one

*For any* planning run regardless of destination and budget, the BacktrackIteration counter should be at most 1 when the PlanningLoop terminates.

**Validates: Requirements 3.7**

---

### Property 10: Planning output cardinality is bounded

*For any* valid TravelRequest, the number of Itinerary packages produced by the PlanningLoop should be between 1 and 3 inclusive.

**Validates: Requirements 3.8**

---

### Property 11: MatchScore dot product correctness

*For any* itinerary tag list and user style preference list, the raw MatchScore should equal the count of tags that appear in both lists (dot product over binary indicator vectors).

**Validates: Requirements 4.1**

---

### Property 12: Min-Max normalization bounds

*For any* list of two or more raw MatchScores, after normalization the maximum value should be 1.0 and the minimum value should be 0.0.

**Validates: Requirements 4.2**

---

### Property 13: Itinerary ranking is non-increasing

*For any* list of itineraries with assigned MatchScores, the order in which they are presented to the user should be non-increasing by MatchScore.

**Validates: Requirements 4.4, 4.5**

---

### Property 14: Reasoning log grows with planning steps

*For any* planning run, the number of entries appended to the reasoning log should be greater than zero and should increase monotonically as each planning step executes.

**Validates: Requirements 5.2**

---

### Property 15: Itinerary card contains all required fields

*For any* Itinerary object, the rendered card should contain the destination, flight identifier and price, hotel name and price, list of activity names, total cost, and numeric MatchScore.

**Validates: Requirements 6.1**

---

### Property 16: BookingID is a valid UUID

*For any* confirmed booking, the generated BookingID should be a valid UUID (version 4) string conforming to the standard 8-4-4-4-12 hexadecimal format.

**Validates: Requirements 6.4**

---

### Property 17: ConfirmationState is terminal

*For any* AgentState in the "confirm" phase, the only valid next phase transition should be "done" (restart); no transition back to "rank" or earlier phases should be possible.

**Validates: Requirements 6.6**
