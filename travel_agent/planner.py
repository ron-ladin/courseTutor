try:
    from .data_client import DataClient
    from .models import Activity, Hotel, Itinerary, TravelRequest
except ImportError:  # Allows importing from inside travel_agent/.
    from data_client import DataClient
    from models import Activity, Hotel, Itinerary, TravelRequest


MAX_ITINERARIES = 3
UNFILTERED_MAX_PRICE = 99999


def compute_raw_score(item_tags: list[str], user_style: list[str]) -> float:
    """Count overlapping style tags, preserving repeated tags in the item list."""
    preferred_tags = set(user_style)
    return float(sum(1 for tag in item_tags if tag in preferred_tags))


def aggregate_itinerary_tags(itinerary: Itinerary) -> list[str]:
    tags = itinerary.flight.style_tags + itinerary.hotel.style_tags
    for activity in itinerary.activities:
        tags.extend(activity.style_tags)
    return tags


def normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        return [1.0] * len(scores)

    return [(score - min_score) / (max_score - min_score) for score in scores]


def run_planning_loop(
    request: TravelRequest,
    client: DataClient,
    reasoning_log: list[str],
) -> list[Itinerary]:
    departure = request.departure_date.isoformat()
    return_date = request.return_date.isoformat()
    flights = sorted(
        client.get_flights(request.destination, departure),
        key=lambda flight: (flight.price, flight.duration_hours, flight.airline),
    )

    if not flights:
        reasoning_log.append(f"No flights found for {request.destination}.")
        return []

    itineraries: list[Itinerary] = []
    backtrack_count = 0
    flight_index = 0

    while flight_index < len(flights) and len(itineraries) < MAX_ITINERARIES:
        flight = flights[flight_index]
        remaining_after_flight = request.budget - flight.price
        reasoning_log.append(
            f"Selected flight {flight.id} on {flight.airline} "
            f"(${flight.price:.2f}). Remaining budget: ${remaining_after_flight:.2f}."
        )
        reasoning_log.append(
            f"GET /hotels/search?destination={request.destination}"
            f"&max_price={remaining_after_flight:.2f}"
        )

        hotels = client.get_hotels(
            request.destination,
            checkin=departure,
            checkout=return_date,
            max_price=remaining_after_flight,
        )

        if not hotels:
            if backtrack_count == 0 and flight_index + 1 < len(flights):
                rejected = flight.id
                alternative = flights[flight_index + 1].id
                backtrack_count += 1
                reasoning_log.append(
                    f"No hotel fits remaining budget after flight {rejected}. "
                    f"Backtracking to alternative flight {alternative}."
                )
                flight_index += 1
                continue

            fallback = _lowest_cost_hotel(
                client,
                request.destination,
                departure,
                return_date,
            )
            if fallback is None:
                reasoning_log.append(
                    f"No hotels found for {request.destination}; no itinerary produced."
                )
                break

            total_cost = flight.price + fallback.price_per_night
            reasoning_log.append(
                "Backtrack limit reached. Assembling partial fallback with "
                f"{fallback.name} (${fallback.price_per_night:.2f}/night)."
            )
            itineraries.append(
                Itinerary(
                    flight=flight,
                    hotel=fallback,
                    activities=[],
                    total_cost=total_cost,
                    is_partial_fallback=True,
                )
            )
            break

        hotel = _best_matching_hotel(hotels, request.travel_style)
        hotel_score = compute_raw_score(hotel.style_tags, request.travel_style)
        remaining_after_hotel = remaining_after_flight - hotel.price_per_night
        reasoning_log.append(
            f"Selected hotel {hotel.name} (score={hotel_score:.0f}, "
            f"${hotel.price_per_night:.2f}/night). "
            f"Remaining budget: ${remaining_after_hotel:.2f}."
        )

        activities = client.get_activities(request.destination)
        selected_activities = _allocate_activities(
            activities,
            request.travel_style,
            remaining_after_hotel,
            reasoning_log,
        )
        total_cost = (
            flight.price
            + hotel.price_per_night
            + sum(activity.price for activity in selected_activities)
        )
        itineraries.append(
            Itinerary(
                flight=flight,
                hotel=hotel,
                activities=selected_activities,
                total_cost=total_cost,
            )
        )
        flight_index += 1

    _assign_normalized_scores(itineraries, request.travel_style)
    itineraries.sort(key=lambda itinerary: itinerary.match_score, reverse=True)
    return itineraries[:MAX_ITINERARIES]


def _lowest_cost_hotel(
    client: DataClient,
    destination: str,
    checkin: str,
    checkout: str,
) -> Hotel | None:
    hotels = client.get_hotels(
        destination,
        checkin=checkin,
        checkout=checkout,
        max_price=UNFILTERED_MAX_PRICE,
    )
    if not hotels:
        return None
    return min(hotels, key=lambda hotel: (hotel.price_per_night, -hotel.stars, hotel.name))


def _best_matching_hotel(hotels: list[Hotel], travel_style: list[str]) -> Hotel:
    return sorted(
        hotels,
        key=lambda hotel: (
            -compute_raw_score(hotel.style_tags, travel_style),
            hotel.price_per_night,
            -hotel.stars,
            hotel.name,
        ),
    )[0]


def _allocate_activities(
    activities: list[Activity],
    travel_style: list[str],
    budget: float,
    reasoning_log: list[str],
) -> list[Activity]:
    selected: list[Activity] = []
    remaining = budget
    activities_by_fit = sorted(
        activities,
        key=lambda activity: (
            -compute_raw_score(activity.style_tags, travel_style),
            activity.price,
            activity.name,
        ),
    )

    for activity in activities_by_fit:
        if activity.price <= remaining:
            selected.append(activity)
            remaining -= activity.price
            reasoning_log.append(
                f"Added activity {activity.name} (${activity.price:.2f}). "
                f"Activity budget left: ${remaining:.2f}."
            )
        else:
            reasoning_log.append(
                f"Skipped activity {activity.name} (${activity.price:.2f}); "
                f"only ${remaining:.2f} left."
            )

    if not selected:
        reasoning_log.append("No activities fit the remaining budget.")
    return selected


def _assign_normalized_scores(
    itineraries: list[Itinerary],
    travel_style: list[str],
) -> None:
    raw_scores = [
        compute_raw_score(aggregate_itinerary_tags(itinerary), travel_style)
        for itinerary in itineraries
    ]
    normalized_scores = normalize_scores(raw_scores)
    for itinerary, score in zip(itineraries, normalized_scores):
        itinerary.match_score = score
