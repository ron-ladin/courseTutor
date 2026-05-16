# Requirements Document

## Introduction

The Travel Planning Agent is a locally-running, conversational travel itinerary planner built for a 20-hour hackathon. It guides users through a step-by-step chat interface to collect travel preferences, autonomously assembles ranked itinerary packages by querying a local mock HTTP server, and presents the results with transparent, real-time reasoning. The system runs entirely offline using Streamlit, LangGraph, Pydantic, FastAPI, and Python — no external APIs are required.

## Glossary

- **Agent**: The LangGraph-powered planning orchestrator that drives the conversation and itinerary assembly loop.
- **TravelRequest**: A Pydantic model capturing the validated user inputs: destination, travel dates, budget, and travel style preferences.
- **MockServer**: A local FastAPI server (`travel_agent/data/mock_server.py`) running on `localhost:8000` that exposes `/flights/search`, `/hotels/search`, and `/activities/search` endpoints, mimicking the Amadeus and Booking.com API styles.
- **DataClient**: An HTTP client (`travel_agent/data/client.py`) that calls the MockServer and returns typed Pydantic model instances to the PlanningLoop.
- **PlanningLoop**: The LangGraph graph that executes flight selection, hotel search, activity allocation, and optional backtracking.
- **MatchScore**: A normalized numeric score (0.0–1.0) computed for each itinerary package using Min-Max normalization and a dot-product against travel style weights.
- **Itinerary**: A complete travel package consisting of one flight, one hotel, and a set of activities for a given destination.
- **ReasoningPanel**: A collapsible Streamlit sidebar/expander that streams the Agent's step-by-step reasoning in real time.
- **ConfirmationState**: The terminal LangGraph state reached after the user selects an itinerary and triggers a booking confirmation.
- **BookingID**: A UUID generated at confirmation time to uniquely identify a confirmed booking.
- **BacktrackIteration**: A single retry cycle in the PlanningLoop triggered when no hotel fits the remaining budget after flight selection.

---

## Requirements

### Requirement 1: Conversational Onboarding

**User Story:** As a traveler, I want the agent to ask me one question at a time in a chat interface, so that I can provide my travel preferences naturally without filling out a form.

#### Acceptance Criteria

1. WHEN the application starts, THE Agent SHALL display a greeting message and ask the user for their desired destination as the first conversational turn.
2. WHEN the user submits a response to the current question, THE Agent SHALL store the answer in the TravelRequest model and ask the next unanswered question in the sequence: destination → travel dates → budget → travel style preferences.
3. WHEN all four TravelRequest fields have been collected, THE Agent SHALL display a confirmation summary of the collected inputs and ask the user to confirm before proceeding to planning.
4. IF the user provides a budget value that is not a positive number, THEN THE Agent SHALL prompt the user to re-enter a valid budget without advancing to the next question.
5. IF the user provides travel dates where the departure date is not before the return date, THEN THE Agent SHALL prompt the user to re-enter valid dates without advancing to the next question.
6. WHEN the user confirms the TravelRequest, THE Agent SHALL validate the complete TravelRequest against the Pydantic schema and transition to the PlanningLoop.
7. IF Pydantic schema validation fails on the confirmed TravelRequest, THEN THE Agent SHALL display the validation error message and return the user to the affected question.

---

### Requirement 2: Mock Server

**User Story:** As a developer, I want a local HTTP server that mimics real travel APIs, so that the system demonstrates realistic API integration while running fully offline.

#### Acceptance Criteria

1. THE MockServer SHALL be a FastAPI application running on `localhost:8000` with three route groups: `/flights`, `/hotels`, and `/activities`.
2. THE MockServer SHALL expose `GET /flights/search?destination=<str>&date=<YYYY-MM-DD>` and return a JSON array of flight offers, each with `id`, `destination`, `price`, `airline`, `duration_hours`, and `style_tags`.
3. THE MockServer SHALL expose `GET /hotels/search?destination=<str>&checkin=<YYYY-MM-DD>&checkout=<YYYY-MM-DD>&max_price=<float>` and return a JSON array of hotel offers, each with `id`, `destination`, `name`, `price_per_night`, `stars`, and `style_tags`.
4. THE MockServer SHALL expose `GET /activities/search?destination=<str>` and return a JSON array of activities, each with `id`, `destination`, `name`, `price`, and `style_tags`.
5. THE MockServer SHALL supply data for exactly 4 destinations: Tokyo, Paris, Bali, and New York.
6. THE MockServer SHALL provide at least 2 flight options, at least 2 hotel options, and at least 3 activity options per destination.
7. THE MockServer SHALL include Paris as a destination where all hotel options exceed $1,500/night, so that the backtracking scenario is exercised during a planning run.
8. WHEN the PlanningLoop requests data, THE DataClient SHALL call the MockServer over HTTP on localhost and return typed Pydantic model instances; no file I/O or hardcoded data SHALL exist in the client.
9. IF the MockServer is not running when the application starts, THE Agent SHALL display an error message instructing the user to start the server with `uvicorn travel_agent.data.mock_server:app`.

---

### Requirement 3: Holistic Planning Loop with Backtracking

**User Story:** As a traveler, I want the agent to autonomously assemble a complete itinerary within my budget, so that I receive a coherent package without having to manually mix and match options.

#### Acceptance Criteria

1. WHEN the PlanningLoop starts, THE Agent SHALL select the lowest-cost flight to the requested destination by calling the DataClient.
2. WHEN a flight has been selected, THE Agent SHALL compute the remaining budget by subtracting the flight price from the total budget and call the DataClient for hotels filtered by `max_price=remaining`.
3. WHEN at least one hotel is returned, THE Agent SHALL select the hotel with the highest MatchScore among the results.
4. WHEN a hotel has been selected, THE Agent SHALL call the DataClient for activities and allocate those whose combined price does not exceed the remaining budget after hotel cost.
5. IF no hotel option fits the remaining budget after flight selection and the BacktrackIteration count is zero, THEN THE Agent SHALL increment the BacktrackIteration count, select the next lowest-cost flight, and restart hotel search.
6. IF no hotel option fits the remaining budget after the one permitted BacktrackIteration, THEN THE Agent SHALL assemble a partial package containing the selected flight and the lowest-cost hotel regardless of budget fit, and mark the package as a partial fallback.
7. THE PlanningLoop SHALL NOT exceed one BacktrackIteration per planning run.
8. WHEN the PlanningLoop completes, THE Agent SHALL have produced between 1 and 3 complete or partial Itinerary packages.

---

### Requirement 4: Deterministic Match Score Engine

**User Story:** As a traveler, I want itineraries ranked by how well they match my preferences, so that I can quickly identify the best option for my travel style.

#### Acceptance Criteria

1. THE MatchScore engine SHALL compute a score for each Itinerary using a dot product of the itinerary's aggregated travel style tag weights and the user's preference weights derived from the TravelRequest.
2. THE MatchScore engine SHALL apply Min-Max normalization across all candidate Itinerary scores so that the highest score maps to 1.0 and the lowest score maps to 0.0.
3. WHEN scores are equal across all candidates, THE MatchScore engine SHALL assign a score of 1.0 to all candidates.
4. THE Agent SHALL present the top 3 Itineraries ranked in descending order of MatchScore.
5. WHERE fewer than 3 complete Itineraries are available, THE Agent SHALL present all available Itineraries ranked in descending order of MatchScore.
6. THE Agent SHALL display the numeric MatchScore alongside each ranked Itinerary in the Streamlit chat interface.

---

### Requirement 5: Agentic Reasoning Transparency

**User Story:** As a traveler, I want to see the agent's reasoning as it plans my trip, so that I can understand why certain options were chosen or rejected.

#### Acceptance Criteria

1. THE ReasoningPanel SHALL be rendered as a collapsible Streamlit expander or sidebar visible on the planning results page.
2. WHEN the PlanningLoop executes each step, THE Agent SHALL append a human-readable reasoning string describing the step's decision to the ReasoningPanel in real time.
3. WHEN a BacktrackIteration is triggered, THE Agent SHALL append a reasoning string to the ReasoningPanel that identifies the flight that was rejected, the reason (no hotel fits remaining budget), and the alternative flight selected.
4. WHEN the MatchScore engine ranks Itineraries, THE Agent SHALL append a trade-off analysis string to the ReasoningPanel that lists each candidate's score and the dominant travel style tags that influenced the ranking.
5. WHILE the PlanningLoop is executing, THE ReasoningPanel SHALL display a streaming indicator so the user can see that reasoning is in progress.

---

### Requirement 6: Ranked Itinerary Presentation and Booking Confirmation

**User Story:** As a traveler, I want to review ranked itinerary options and confirm my booking, so that I receive a clear summary and a booking reference I can keep.

#### Acceptance Criteria

1. WHEN the PlanningLoop completes, THE Agent SHALL display 2 to 3 ranked Itinerary cards in the Streamlit chat interface, each showing destination, flight details, hotel name, selected activities, total cost, and MatchScore.
2. WHERE a package is marked as a partial fallback, THE Agent SHALL display a visible label on the Itinerary card indicating that the package exceeds the stated budget.
3. WHEN the user selects an Itinerary, THE Agent SHALL transition to ConfirmationState and display an order summary card with the full details of the selected Itinerary.
4. WHEN the user clicks the Confirm Booking button in ConfirmationState, THE Agent SHALL generate a UUID as the BookingID and display it to the user as a booking confirmation message.
5. THE Agent SHALL display the BookingID in the Streamlit chat interface so the user can record it.
6. WHEN ConfirmationState is reached, THE Agent SHALL NOT allow the user to return to itinerary selection without restarting the planning session.
