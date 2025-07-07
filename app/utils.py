import logging
from typing import Dict
import math
from operator import itemgetter

import pydantic
from app.schemas import LocationCreate, TripResponse
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the Haversine distance between two points on the earth.

    :param lat1: Latitude of first point
    :param lon1: Longitude of first point
    :param lat2: Latitude of second point
    :param lon2: Longitude of second point
    :return: Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    # Convert latitude and longitude to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def order_locations_by_distance(locations: list[Dict]) -> list[Dict]:
    """
    Order locations based on geographical distance from the first location.

    :param locations: List of location dictionaries with latitude and longitude
    :return: Ordered list of locations
    """
    if not locations:
        return locations

    # Keep first location as reference point
    ordered = [locations[0]]
    remaining = locations[1:]

    while remaining:
        # Get the last added location's coordinates
        last = ordered[-1]
        last_lat, last_lon = last["latitude"], last["longitude"]

        # Find the closest remaining location
        distances = [
            (loc, haversine_distance(last_lat, last_lon, loc["latitude"], loc["longitude"]))
            for loc in remaining
        ]
        closest_loc, _ = min(distances, key=itemgetter(1))

        ordered.append(closest_loc)
        remaining.remove(closest_loc)

    return ordered


def validate_prediction_locations(
    prediction_locations_list: list[Dict],
) -> list[LocationCreate]:
    """
    Validate and convert the prediction locations list to a list of LocationCreate objects.
    Orders locations based on geographical distance from the first location.

    :param prediction_locations_list: List of dictionaries containing location data.
    :return: List of LocationCreate objects ordered by geographical proximity.
    :raises HTTPException: If validation fails or no locations are generated.
    """
    # Validate prediction_locations_list
    if not prediction_locations_list:
        raise HTTPException(status_code=400, detail="No locations generated")

    # Order locations based on geographical distance
    ordered_locations = order_locations_by_distance(prediction_locations_list)
    try:
        locations_list = [
            LocationCreate(trip_id=None, **location)
            for location in ordered_locations
        ]
    except pydantic.ValidationError as e:
        logger.error("Validation error in locations: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid location data: {str(prediction_locations_list[0])}",
        ) from e

    return locations_list


def validate_trip_response(trip, request_data, locations) -> TripResponse:
    """
    Validate the trip response data.

    :param trip: The trip object containing trip details.
    :param request_data: The request data object containing request details.
    :param locations: List of validated location objects.
    :return: TripResponse object if validation is successful.
    :raises HTTPException: If validation fails.
    """
    try:
        response = TripResponse(
            id=trip.id,
            request_id=request_data.id,
            parent_id=trip.parent_id,
            num_places=trip.num_places,
            locations=locations,
            created_at=trip.created_at,
            trip_type=trip.trip_type,
        )
        logger.debug("Validated response: %s", response.model_dump())
        return response
    except pydantic.ValidationError as e:
        logger.error(
            "Validation error: %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Validation error: {str(e)}"
        ) from e
