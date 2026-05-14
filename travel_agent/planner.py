from __future__ import annotations

from typing import Any

try:
    from .models import Activity, Itinerary, TravelRequest
except ImportError:
    from models import Activity, Itinerary, TravelRequest


# ── Scoring helpers ───────────────────────────────────────────────────────────

def compute_raw_score(item_tags: list[str], user_style: list[str]) -> float:
    """Dot product: count of overlapping tags between an item and the user's style."""
    return float(len(set(item_tags) & set(user_style)))


def aggregate_itinerary_tags(itinerary: Itinerary) -> list[str]:
    """Collect all style tags across flight, hotel, and every activity."""
    tags: list[str] = list(itinerary.flight.style_tags)
    tags.extend(itinerary.hotel.style_tags)
    for activity in itinerary.activities:
        tags.extend(activity.style_tags)
    return tags


def normalize_scores(scores: list[float]) -> list[float]:
    """
    Min-Max normalization.
    Returns [1.0] * n when all scores are equal — avoids a flat zero-score list
    which would make the ranking panel useless.
    """
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi == lo:
        return [1.0] * len(scores)
    return [(s - lo) / (hi - lo) for s in scores]


# ── Activity allocation ───────────────────────────────────────────────────────

def _greedy_activities(
    client: Any,
    request: TravelRequest,
    budget: float,
    reasoning_log: list[str],
) -> list[Activity]:
    """
    Greedy knapsack: pick activities by match score descending, then price
    ascending for ties. Stops as soon as the next item would exceed budget.
    """
    activities = client.get_activities(request.destination)
    activities.sort(
        key=lambda a: (-compute_raw_score(a.style_tags, request.travel_style), a.price)
    )
    selected: list[Activity] = []
    remaining = budget
    for a in activities:
        if a.price <= remaining:
            selected.append(a)
            remaining -= a.price

    reasoning_log.append(
        f"Activities: selected {len(selected)} item(s) "
        f"(${sum(a.price for a in selected):.0f}) within ${budget:.0f} remaining budget."
    )
    return selected


# ── Planning loop ─────────────────────────────────────────────────────────────

def run_planning_loop(
    request: TravelRequest,
    client: Any,
    reasoning_log: list[str],
) -> list[Itinerary]:
    """
    Core planning loop (Requirement 2).

    1. Fetch flights sorted by price ascending.
    2. For each flight, ask the server for hotels under (remaining / nights).
    3. If no hotels returned, backtrack once (try next-cheapest flight).
    4. On second failure, assemble a partial-fallback itinerary with the
       cheapest available hotel regardless of budget.
    5. Return up to 3 Itinerary objects (match_score left at 0.0;
       rank_node normalises and sorts them).
    """
    nights = (request.return_date - request.departure_date).days
    flights = sorted(
        client.get_flights(request.destination, str(request.departure_date)),
        key=lambda f: f.price,
    )

    if not flights:
        reasoning_log.append(f"No flights found for {request.destination}.")
        return []

    reasoning_log.append(
        f"Found {len(flights)} flight(s) to {request.destination}. "
        f"Evaluating cheapest-first over {nights} night(s), budget ${request.budget:.0f}."
    )

    itineraries: list[Itinerary] = []
    backtrack_count = 0

    for flight in flights:
        remaining_after_flight = request.budget - flight.price
        if remaining_after_flight <= 0:
            reasoning_log.append(
                f"Skipping {flight.airline} (${flight.price:.0f}) — exceeds total budget."
            )
            continue

        # Server handles the price filter; we just tell it the per-night ceiling
        max_hotel_per_night = remaining_after_flight / nights
        reasoning_log.append(
            f"Trying {flight.airline} (${flight.price:.0f}). "
            f"Remaining ${remaining_after_flight:.0f}, max hotel/night ${max_hotel_per_night:.0f}."
        )

        hotels = client.get_hotels(
            request.destination,
            str(request.departure_date),
            str(request.return_date),
            max_price=max_hotel_per_night,
        )
        reasoning_log.append(
            f"GET /hotels/search?destination={request.destination}"
            f"&max_price={max_hotel_per_night:.0f} → {len(hotels)} result(s)."
        )

        if not hotels:
            if backtrack_count < 1:
                # First failure — try the next cheapest flight before giving up
                backtrack_count += 1
                reasoning_log.append(
                    f"No hotels in budget with {flight.airline}. "
                    f"Backtracking (attempt {backtrack_count}) — trying cheaper flight."
                )
                continue
            else:
                # Second failure — partial fallback with the cheapest available hotel
                all_hotels = client.get_hotels(
                    request.destination,
                    str(request.departure_date),
                    str(request.return_date),
                )
                if not all_hotels:
                    reasoning_log.append("No hotels at any price for this destination.")
                    break
                best_hotel = min(all_hotels, key=lambda h: h.price_per_night)
                hotel_cost = best_hotel.price_per_night * nights
                budget_for_activities = max(remaining_after_flight - hotel_cost, 0.0)
                activities = _greedy_activities(client, request, budget_for_activities, reasoning_log)
                total_cost = flight.price + hotel_cost + sum(a.price for a in activities)
                reasoning_log.append(
                    f"Partial fallback: {flight.airline} + {best_hotel.name} "
                    f"exceeds budget by ${total_cost - request.budget:.0f}."
                )
                itineraries.append(Itinerary(
                    flight=flight, hotel=best_hotel, activities=activities,
                    total_cost=total_cost, is_partial_fallback=True,
                ))
                break

        else:
            # Pick best hotel by match score; break ties by lowest price
            best_hotel = max(
                hotels,
                key=lambda h: (compute_raw_score(h.style_tags, request.travel_style), -h.price_per_night),
            )
            hotel_cost = best_hotel.price_per_night * nights
            score = compute_raw_score(best_hotel.style_tags, request.travel_style)

            # Transparency: explain WHY this hotel was chosen (Requirement 4)
            reasoning_log.append(
                f"Selected {best_hotel.name} (${best_hotel.price_per_night:.0f}/night, "
                f"{best_hotel.stars}★, style-match {score:.0f}) "
                f"— best match among {len(hotels)} qualifying hotel(s)."
            )

            activities = _greedy_activities(
                client, request, remaining_after_flight - hotel_cost, reasoning_log
            )
            total_cost = flight.price + hotel_cost + sum(a.price for a in activities)
            itineraries.append(Itinerary(
                flight=flight, hotel=best_hotel, activities=activities,
                total_cost=total_cost, is_partial_fallback=False,
            ))
            if len(itineraries) >= 3:
                break

    return itineraries[:3]
