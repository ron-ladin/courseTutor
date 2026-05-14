# Travel Planning Agent

Streamlit demo app for a travel-planning agent. The customer chats naturally,
the agent extracts trip details, the planner searches local travel data, and
the UI shows ranked itinerary options.

## Project Structure

```text
travel_agent/
  app.py                 Streamlit chat UI
  agent.py               Conversation state and LangGraph flow
  planner.py             Itinerary planning, scoring, and backtracking
  models.py              Pydantic models
  openrouter_client.py   Optional OpenRouter extraction/explanation layer
  data/
    static.py            Embedded demo travel catalog
    client.py            Data client with static fallback and optional live-style paths
    mock_server.py       FastAPI mock API over the static catalog

tests/                   System-level tests
travel_agent/tests/      Package-level tests
```

`data_client.py` and `mock_server.py` at the repo root are compatibility
wrappers for older imports and commands.

## Data Flow

```text
User message
-> OpenRouter extraction, if enabled
-> local parser fallback
-> planner
-> static travel catalog
-> OpenRouter explanation, if enabled
-> Streamlit response
```

The actual flights, hotels, and activities shown in the app come from
`travel_agent/data/static.py`. The mock server exposes that same data as a fake
API for tests and demos.

## Supported Demo Destinations

The embedded catalog uses city destinations only:

```text
Tokyo, Paris, Bali, New York,
Kyoto, Nice, Rome, Athens, Bangkok,
Barcelona, London, Mexico City, Tel Aviv
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## OpenRouter

Create a local `.env` file. Do not commit it.

```text
OPENROUTER_API_KEY=your_key_here
OPENROUTER_ENABLED=true
OPENROUTER_MODEL=openai/gpt-4o-mini
```

If OpenRouter is disabled or unavailable, the app still works with the local
parser and static catalog.

## Run The App

```powershell
.venv\Scripts\streamlit.exe run travel_agent\app.py
```

Then open:

```text
http://localhost:8501
```

## Optional Mock API Server

The Streamlit app can run without this server, but it is useful for API-style
testing.

```powershell
.venv\Scripts\python.exe -m uvicorn travel_agent.data.mock_server:app --host 127.0.0.1 --port 8000
```

## Tests

```powershell
.venv\Scripts\python.exe -m pytest
```
