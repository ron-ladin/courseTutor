"""Mock FastAPI server for travel data (stub - Dev 2 will implement)."""

from fastapi import FastAPI

app = FastAPI(title="Travel Planning Mock Server")


@app.get("/flights/search")
def search_flights(destination: str, date: str):
    """Search flights by destination and date."""
    return []


@app.get("/hotels/search")
def search_hotels(destination: str, checkin: str, checkout: str, max_price: float = 99999):
    """Search hotels by destination, dates, and budget."""
    return []


@app.get("/activities/search")
def search_activities(destination: str):
    """Search activities by destination."""
    return []


@app.get("/destinations")
def get_destinations():
    """Get list of available destinations."""
    return []
