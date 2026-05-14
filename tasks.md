# Implementation Plan: Travel Planning Agent

## Team

| Developer | Role | Primary Files | Est. Hours |
|-----------|------|---------------|------------|
| **Dev 1 — Yehonatan** | Data & Models | `models.py` | ~2h |
| **Dev 2 — [Name]** | Mock Server + Planning Engine | `mock_server.py`, `data_client.py`, `planner.py` | ~6h |
| **Dev 3 — [Name]** | Agent Orchestration | `agent.py` (LangGraph nodes + graph) | ~6h |
| **Dev 4 — [Name]** | UI & Experience | `app.py` (Streamlit chat + cards) | ~5h |
| **All** | Scaffolding + Integration + Demo | — | ~1h |

> Replace `[Name]` with your actual team members' names.

## Overview

Four Python modules built in parallel. Each developer owns one module end-to-end and can start immediately after the shared scaffolding (Task 1) is done. Integration wires everything together in the final stretch.

## Parallel Execution Strategy

The architecture has a natural import chain: `models.py → planner.py → agent.py → app.py`. Without stubs, Dev 3 and Dev 4 would be blocked waiting for upstream modules. The solution is to write typed stubs in Task 1 so all four developers are unblocked from hour 0.

**Dependency map:**
```
Dev 1 (models.py)        ← no dependencies, start immediately
Dev 2 (planner.py)       ← imports models.py stubs, start immediately
Dev 3 (agent.py)         ← imports planner.py stubs, start immediately
Dev 4 (app.py)           ← imports agent.py stubs, start immediately
```

**What "stub" means:** a file with the correct function signatures and return type hints, but returning empty/dummy values. Dev 3 and Dev 4 code against these stubs and swap in the real implementations at integration time (Task 11).

**Parallel timeline:**
```
Hour 0–1:   ALL  — scaffolding + write stubs (Task 1)
Hour 1–3:   Dev 1 — real models + validators (Task 2)
Hour 1–7:   Dev 2 — mock server + data client + MatchScore + PlanningLoop (Tasks 3–5)
Hour 1–7:   Dev 3 — real LangGraph nodes + graph (Task 7)
Hour 1–6:   Dev 4 — real Streamlit UI against stubs (Task 9)
Hour 14–18: ALL  — swap stubs for real impls, integration (Task 11)
Hour 18–20: ALL  — demo prep + final run (Task 12)
```

---

## Tasks

- [ ] 1. Set up project structure and shared scaffolding — **All Developers**
  - Create the `travel_agent/` directory with `__init__.py` files and `data/` subdirectory
  - Create `requirements.txt` pinning `streamlit`, `langgraph`, `pydantic`, `fastapi`, `uvicorn`, `httpx`, `hypothesis`, `pytest`
  - **Dev 1** writes typed stubs in `models.py` so everyone can import immediately:
    ```python
    # models.py — stubs (validators added later by Dev 1)
    from pydantic import BaseModel
    from datetime import date

    class TravelRequest(BaseModel):
        destination: str = ""
        departure_date: date = date.today()
        return_date: date = date.today()
        budget: float = 0.0
        travel_style: list[str] = []

    class Flight(BaseModel):
        id: str = ""; destination: str = ""; price: float = 0.0
        airline: str = ""; duration_hours: float = 0.0; style_tags: list[str] = []

    class Hotel(BaseModel):
        id: str = ""; destination: str = ""; name: str = ""
        price_per_night: float = 0.0; stars: int = 0; style_tags: list[str] = []

    class Activity(BaseModel):
        id: str = ""; destination: str = ""; name: str = ""; price: float = 0.0; style_tags: list[str] = []

    class Itinerary(BaseModel):
        flight: Flight = Flight(); hotel: Hotel = Hotel()
        activities: list[Activity] = []; total_cost: float = 0.0
        match_score: float = 0.0; is_partial_fallback: bool = False

    class BookingConfirmation(BaseModel):
        booking_id: str = ""; itinerary: Itinerary = Itinerary()
    ```
  - **Dev 2** writes typed stubs in `data_client.py` and `planner.py` so Dev 3 can import immediately:
    ```python
    # data_client.py — stub
    from models import Flight, Hotel, Activity

    class DataClient:
        def get_flights(self, destination: str, date: str) -> list[Flight]: return []
        def get_hotels(self, destination: str, checkin: str, checkout: str, max_price: float = 99999) -> list[Hotel]: return []
        def get_activities(self, destination: str) -> list[Activity]: return []
        def destinations(self) -> list[str]: return []

    # planner.py — stub
    from models import Itinerary, TravelRequest
    from data_client import DataClient

    def compute_raw_score(item_tags: list[str], user_style: list[str]) -> float: return 0.0
    def normalize_scores(scores: list[float]) -> list[float]: return scores
    def run_planning_loop(request: TravelRequest, client: DataClient, reasoning_log: list[str]) -> list[Itinerary]: return []
    ```
  - **Dev 3** writes a typed stub in `agent.py` so Dev 4 can import immediately:
    ```python
    # agent.py — stub (real graph added later by Dev 3)
    from typing import TypedDict, Optional
    from models import TravelRequest, Itinerary, BookingConfirmation

    class AgentState(TypedDict):
        messages: list[dict]
        travel_request: dict
        confirmed_request: Optional[TravelRequest]
        itineraries: list[Itinerary]
        selected_itinerary: Optional[Itinerary]
        booking: Optional[BookingConfirmation]
        reasoning_log: list[str]
        backtrack_count: int
        phase: str  # "onboard" | "plan" | "rank" | "confirm" | "done"

    def build_graph():
        return None  # real graph wired later
    ```
  - _Requirements: all modules_

---

- [ ] 2. Implement data models (`models.py`) — **Dev 1**
  - [ ] 2.1 Implement `TravelRequest`, `Flight`, `Hotel`, `Activity`, `Itinerary`, `BookingConfirmation` Pydantic models
    - Include `budget_must_be_positive` and `return_after_departure` field validators on `TravelRequest`
    - _Requirements: 1.4, 1.5, 1.6, 1.7_

  - [ ]* 2.2 Write property test for budget validation (Property 2)
    - **Property 2: Budget validation rejects non-positive values**
    - **Validates: Requirements 1.4**
    - Use `hypothesis` to generate zero, negative, and non-numeric-equivalent inputs and assert `ValidationError` is raised

  - [ ]* 2.3 Write property test for date validation (Property 3)
    - **Property 3: Date validation rejects invalid date ranges**
    - **Validates: Requirements 1.5**
    - Use `hypothesis` to generate date pairs where `departure_date >= return_date` and assert `ValidationError` is raised

---

- [ ] 3. Build mock server and data client — **Dev 2**
  - [ ] 3.1 Implement `mock_server.py` as a FastAPI app on `localhost:8000`
    - Three route groups: `GET /flights/search`, `GET /hotels/search`, `GET /activities/search`, `GET /destinations`
    - `/flights/search?destination=<str>&date=<YYYY-MM-DD>` → returns list of `Flight` objects
    - `/hotels/search?destination=<str>&checkin=<str>&checkout=<str>&max_price=<float>` → returns filtered list of `Hotel` objects
    - `/activities/search?destination=<str>` → returns list of `Activity` objects
    - Hardcode data for 4 destinations: Tokyo, Paris, Bali, New York — all inside the server file, no JSON files
    - Paris hotels must all exceed $1,500/night to exercise the backtracking path
    - Each destination: ≥2 flights (with `airline`, `duration_hours`), ≥2 hotels (with `stars`), ≥3 activities
    - _Requirements: 2.1–2.9_

  - [ ] 3.2 Implement `data_client.py` as an `httpx` HTTP client
    - `DataClient` class with `get_flights()`, `get_hotels()`, `get_activities()`, `destinations()` methods
    - Each method calls the corresponding MockServer endpoint and returns typed Pydantic model instances
    - Raise a clear `ConnectionError` with instructions if the server is unreachable
    - _Requirements: 2.8, 2.9_

  - [ ]* 3.3 Write a smoke test for the MockServer endpoints
    - Start the server in-process using `TestClient` from `fastapi.testclient`
    - Assert `/flights/search?destination=Tokyo` returns ≥2 results with `price > 0` and non-empty `style_tags`
    - Assert `/hotels/search?destination=Paris&max_price=500` returns an empty list (all Paris hotels > $1,500)
    - Assert `/hotels/search?destination=Tokyo&max_price=200` returns only hotels with `price_per_night ≤ 200`
    - _Requirements: 2.6, 2.7_

---

- [ ] 4. Implement MatchScore engine (`planner.py`) — **Dev 2**
  - [ ] 4.1 Implement `compute_raw_score`, `aggregate_itinerary_tags`, and `normalize_scores` functions
    - `compute_raw_score`: dot product (count of overlapping tags)
    - `normalize_scores`: Min-Max; return `[1.0] * n` when all scores are equal
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 4.2 Write property test for MatchScore dot product correctness (Property 11)
    - **Property 11: MatchScore dot product correctness**
    - **Validates: Requirements 4.1**
    - Use `hypothesis` to generate arbitrary tag lists and assert raw score equals intersection count

  - [ ]* 4.3 Write property test for Min-Max normalization bounds (Property 12)
    - **Property 12: Min-Max normalization bounds**
    - **Validates: Requirements 4.2**
    - Use `hypothesis` to generate lists of ≥2 distinct floats and assert max normalized = 1.0, min = 0.0

---

- [ ] 5. Implement PlanningLoop (`planner.py`) — **Dev 2**
  - [ ] 5.1 Implement `run_planning_loop(request, client, reasoning_log)` function
    - Sort flights by price ascending; iterate with `flight_index`
    - Call `client.get_flights()` and `client.get_hotels(max_price=remaining)` — server handles budget filtering
    - Select best hotel by `compute_raw_score`; greedy activity allocation by score descending
    - Backtrack once if no hotel is returned; assemble partial fallback after second failure
    - Append human-readable strings to `reasoning_log` at each decision point
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 5.2_

  - [ ]* 5.2 Write property test for minimum-cost flight selection (Property 5)
    - **Property 5: Flight selection is minimum-cost**
    - **Validates: Requirements 3.1**
    - Use `hypothesis` to generate flight lists and assert the first selected flight has the minimum price

  - [ ]* 5.3 Write property test for hotel budget constraint (Property 6)
    - **Property 6: Hotel search respects remaining budget**
    - **Validates: Requirements 3.2**
    - Assert every hotel considered has `price_per_night <= budget - flight.price`

  - [ ]* 5.4 Write property test for hotel MatchScore maximization (Property 7)
    - **Property 7: Hotel selection maximizes MatchScore**
    - **Validates: Requirements 3.3**
    - Assert selected hotel has the highest raw score among qualifying hotels

  - [ ]* 5.5 Write property test for activity budget constraint (Property 8)
    - **Property 8: Activity allocation stays within budget**
    - **Validates: Requirements 3.4**
    - Assert `sum(a.price for a in selected_activities) <= remaining_after_hotel`

  - [ ]* 5.6 Write property test for backtrack limit (Property 9)
    - **Property 9: BacktrackIteration never exceeds one**
    - **Validates: Requirements 3.7**
    - Assert `backtrack_count <= 1` for any planning run

  - [ ]* 5.7 Write property test for output cardinality (Property 10)
    - **Property 10: Planning output cardinality is bounded**
    - **Validates: Requirements 3.8**
    - Assert `1 <= len(itineraries) <= 3` for any valid `TravelRequest`

- [ ] 6. Checkpoint — server + planner layer — **Dev 2 signals ready**
  - MockServer running on `localhost:8000`; all smoke tests pass; share `data_client.py` and `planner.py` with Dev 3 and Dev 4.

---

- [ ] 7. Implement LangGraph agent (`agent.py`) — **Dev 3**
  - [ ] 7.1 Define `AgentState` TypedDict with all fields from the design
    - Fields: `messages`, `travel_request`, `confirmed_request`, `itineraries`, `selected_itinerary`, `booking`, `reasoning_log`, `backtrack_count`, `phase`
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ] 7.2 Implement `onboard_node` with sequential question flow
    - Ask one question at a time in order: destination → departure_date → return_date → budget → travel_style
    - Validate budget (positive number) and dates (departure < return) inline; re-prompt on failure
    - Display confirmation summary and await "yes" before transitioning phase to "plan"
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]* 7.3 Write property test for onboarding sequence order (Property 1)
    - **Property 1: Onboarding sequence advances in order**
    - **Validates: Requirements 1.2**
    - Use `hypothesis` to generate four valid answer sequences and assert fields are populated in the correct order

  - [ ] 7.4 Implement `plan_node` and `rank_node`
    - `plan_node`: instantiate `DataClient`, call `run_planning_loop`, store results in state, set phase to "rank"
    - `rank_node`: apply `normalize_scores` across itineraries, sort descending by `match_score`, append trade-off analysis to `reasoning_log`, trim to top 3
    - _Requirements: 3.1–3.8, 4.1–4.6, 5.2, 5.4_

  - [ ]* 7.5 Write property test for itinerary ranking order (Property 13)
    - **Property 13: Itinerary ranking is non-increasing**
    - **Validates: Requirements 4.4, 4.5**
    - Assert `itineraries[i].match_score >= itineraries[i+1].match_score` for all adjacent pairs

  - [ ] 7.6 Implement `confirm_node`
    - Display order summary; on user confirmation generate `uuid.uuid4()` as `BookingID`
    - Store `BookingConfirmation` in state; set phase to "done"
    - _Requirements: 6.3, 6.4, 6.5, 6.6_

  - [ ]* 7.7 Write property test for BookingID UUID validity (Property 16)
    - **Property 16: BookingID is a valid UUID**
    - **Validates: Requirements 6.4**
    - Assert generated `booking_id` matches UUID v4 format regex `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`

  - [ ]* 7.8 Write property test for ConfirmationState terminal transition (Property 17)
    - **Property 17: ConfirmationState is terminal**
    - **Validates: Requirements 6.6**
    - Assert that invoking the graph from phase "confirm" only transitions to "done", never back to "rank" or earlier

  - [ ] 7.9 Wire graph with `build_graph()` using `StateGraph`, conditional edges, and `compile()`
    - Edges: START → onboard → (continue | plan) → plan → rank → (wait | confirm) → confirm → END
    - _Requirements: 1.1–1.7, 3.1–3.8, 6.3–6.6_

- [ ] 8. Checkpoint — agent layer — **Dev 3 signals ready**
  - Ensure all tests pass; share `agent.py` with Dev 4.

---

- [ ] 9. Implement Streamlit UI (`app.py`) — **Dev 4**
  - [ ] 9.1 Initialize session state and render chat message history
    - Bootstrap `st.session_state.graph` and `st.session_state.state` on first load
    - Render all messages from `state["messages"]` using `st.chat_message`
    - _Requirements: 1.1_

  - [ ] 9.2 Implement ReasoningPanel expander
    - Render `st.expander("🧠 Agent Reasoning")` with all `reasoning_log` entries as bullet points
    - Show `"⏳ Planning in progress..."` spinner while `phase == "plan"`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 9.3 Implement itinerary card rendering
    - For each itinerary in `state["itineraries"]` render a bordered container with: destination, flight id + price, hotel name + price/night, activity names, total cost, MatchScore
    - Show `"⚠️ Exceeds Budget"` label when `is_partial_fallback == True`
    - Render a `st.button(f"Select Option {i+1}")` per card; on click update state and rerun
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 9.4 Write property test for itinerary card field completeness (Property 15)
    - **Property 15: Itinerary card contains all required fields**
    - **Validates: Requirements 6.1**
    - Use `hypothesis` to generate `Itinerary` objects and assert all required fields are present and non-empty in the rendered output

  - [ ] 9.5 Implement booking confirmation display
    - After `confirm_node` sets phase to "done", render the `BookingID` UUID in the chat as a confirmation message
    - _Requirements: 6.4, 6.5_

  - [ ] 9.6 Wire chat input to graph invocation
    - On `st.chat_input` submission, append user message to `state["messages"]`, invoke `graph.invoke(state)`, update `st.session_state.state`, call `st.rerun()`
    - Handle destination-not-in-mock-data and no-itineraries-produced error states with user-facing messages
    - _Requirements: 1.1–1.7, 6.6_

  - [ ]* 9.7 Write property test for reasoning log growth (Property 14)
    - **Property 14: Reasoning log grows with planning steps**
    - **Validates: Requirements 5.2**
    - Assert `len(reasoning_log) > 0` after any planning run and that it grows monotonically across steps

- [ ] 10. Checkpoint — UI layer — **Dev 4 signals ready**
  - Ensure all tests pass; all four modules ready for integration.

---

- [ ] 11. Integration and wiring — **All Developers**
  - [ ] 11.1 Start MockServer (`uvicorn mock_server:app --port 8000`) and connect all four modules end-to-end
    - Import `build_graph` in `app.py`; verify session state flows through onboard → plan → rank → confirm
    - Fix any import errors, missing fields, or type mismatches between modules
    - _Requirements: 1.1–1.7, 3.1–3.8, 4.1–4.6, 5.1–5.5, 6.1–6.6_

  - [ ] 11.2 Verify backtracking path with Paris destination
    - Run a planning session with destination=Paris and a budget below $2,000 to trigger the backtrack and partial fallback path
    - Assert `is_partial_fallback == True` on the returned itinerary and that the ReasoningPanel shows the backtrack message
    - Confirm the ReasoningPanel shows the exact HTTP call: `GET /hotels/search?destination=Paris&max_price=...`
    - _Requirements: 2.7, 3.5, 3.6, 5.3_

- [ ] 12. Final checkpoint — full demo run — **All Developers**
  - Full end-to-end run-through; polish UI; prepare the Paris backtracking scenario as the live demo highlight.

---

## Notes

- Tasks marked with `*` are optional tests — skip them if time is tight
- **Dev 1 and Dev 2** can start immediately in parallel; **Dev 3 and Dev 4** can start on stubs right away and swap in real logic as Dev 1/2 deliver
- Dev 4 should use stub imports for `build_graph` and `run_planning_loop` until Dev 2 and Dev 3 are done
- **Before integration (Task 11), the MockServer must be running**: `uvicorn mock_server:app --reload --port 8000`
- All property tests use `hypothesis`; run with `pytest travel_agent/`
- The Paris backtracking smoke test (11.2) is the single most important integration check before the demo
- No JSON files — all data lives in `mock_server.py`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1", "7.1", "9.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.2", "4.2", "4.3", "7.2", "9.2"] },
    { "id": 3, "tasks": ["3.3", "5.1", "7.3", "9.3"] },
    { "id": 4, "tasks": ["5.2", "5.3", "5.4", "5.5", "5.6", "5.7", "7.4", "9.4", "9.5"] },
    { "id": 5, "tasks": ["7.5", "7.6", "9.6"] },
    { "id": 6, "tasks": ["7.7", "7.8", "9.7"] },
    { "id": 7, "tasks": ["7.9"] },
    { "id": 8, "tasks": ["11.1"] },
    { "id": 9, "tasks": ["11.2"] }
  ]
}
```
