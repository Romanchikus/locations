from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session
import logging

from app.config import config
from app.database import get_db
from app.map_gen import generate_full_map_html
from app.services import RequestService, TripService, LocationService
from app.schemas import (
    ExcludeLocationsRequest,
    LocationResponse,
    RequestCreate,
    RequestResponse,
    TripCreate,
    TripCreateRequest,
    TripResponse,
    TripTypeEnum,
)
from app.models import Request as App_Request
from app.openai_client import OpenAIChatClientTrip
from app.utils import validate_prediction_locations, validate_trip_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trip", tags=["trips"])
requests_router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("/", response_model=TripResponse, status_code=201)
async def create_trip(
    trip_data: TripCreateRequest,
    request: Request,
    trip_type: TripTypeEnum = Query(..., description="Type of trip to generate"),
    db: Session = Depends(get_db),
):
    """Create a new trip."""
    trip_service = TripService(db)
    locations_service = LocationService(db)
    req_service = RequestService(db)

    logger.info("Creating trip with data: %s", trip_data)
    chat_trip = OpenAIChatClientTrip(
        api_key=config.openai_api_key,
        model=config.openai_model,
        trip_type=trip_type.value,
    )

    prediction_locations_list = await chat_trip.get_trip_prediction(
        trip_data, trip_type
    )

    # Get request data after body parsing
    request_data: App_Request = request.state.request_data
    request_data = req_service.update_request(
        req_service.get_request(request_data.id),
        RequestCreate(
            method=request_data.method,
            url=request_data.url,
            headers=request_data.headers,
            body=trip_data.model_dump(),
        ),
    )

    locations_list = validate_prediction_locations(prediction_locations_list)

    # Create trip and locations
    trip = trip_service.create_trip(
        TripCreate(
            request_id=request_data.id,
            parent_id=None,
            response_json=prediction_locations_list,
            num_places=len(prediction_locations_list),
            trip_type=trip_type.value,
        )
    )

    locations = locations_service.create_locations_for_trip(
        trip_id=trip.id, locations_data=locations_list
    )

    # Refresh both trip and locations
    db.refresh(trip)
    for location in locations:
        db.refresh(location)

    # Explicitly query the trip with locations to ensure relationship is loaded
    trip = trip_service.get_trip(trip.id)
    logger.debug("Trip before validation: %s", trip.__dict__)
    logger.debug(
        "Trip locations: %s",
        [loc.__dict__ for loc in trip.locations],
    )

    return validate_trip_response(
        trip=trip,
        request_data=request_data,
        locations=[LocationResponse.model_validate(loc) for loc in trip.locations],
    )


@router.post("/exclude", response_model=TripResponse, status_code=201)
async def exclude_locations_from_trip(
    trip_data: ExcludeLocationsRequest,
    request_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new trip excluding specific locations."""
    trip_service = TripService(db)
    locations_service = LocationService(db)
    req_service = RequestService(db)

    previous_trip = trip_service.get_trip_by_request_id(request_id)
    if not previous_trip:
        raise HTTPException(
            status_code=404, detail="Trip not found for the given request ID"
        )

    # Get request data from previous trip
    chat_trip = OpenAIChatClientTrip(
        api_key=config.openai_api_key,
        model=config.openai_model,
        trip_type=previous_trip.trip_type,
    )
    prediction_locations_list = await chat_trip.get_exlude_locations_prediction(
        previous_trip,
        trip_data.exclude_text,
    )
    current_request_data: App_Request = request.state.request_data
    current_request_data = req_service.update_request(
        req_service.get_request(current_request_data.id),
        RequestCreate(
            method=current_request_data.method,
            url=current_request_data.url,
            headers=current_request_data.headers,
            body=trip_data.model_dump(),
        ),
    )

    locations_list = validate_prediction_locations(prediction_locations_list)
    # Create trip and locations
    trip = trip_service.create_trip(
        TripCreate(
            request_id=current_request_data.id,
            parent_id=previous_trip.id,
            response_json=prediction_locations_list,
            num_places=len(prediction_locations_list),
            trip_type=previous_trip.trip_type,
        )
    )

    locations = locations_service.create_locations_for_trip(
        trip_id=trip.id, locations_data=locations_list
    )

    # Refresh both trip and locations
    db.refresh(trip)
    for location in locations:
        db.refresh(location)

    # Explicitly query the trip with locations to ensure relationship is loaded
    trip = trip_service.get_trip(trip.id)
    logger.debug(
        "Trip locations: %s",
        [loc.__dict__ for loc in trip.locations],
    )

    return validate_trip_response(
        trip=trip,
        request_data=current_request_data,
        locations=[LocationResponse.model_validate(loc) for loc in trip.locations],
    )


from fastapi.responses import HTMLResponse


@router.get("/{trip_id}/mapHTML", response_class=HTMLResponse)
async def generate_html_from_map(trip_id: int, db: Session = Depends(get_db)):
    """Return standalone HTML map document."""
    trip_service = TripService(db)
    trip = trip_service.get_trip(trip_id)

    if not trip or not trip.locations:
        return HTMLResponse(
            content="<h2>No locations found for this trip</h2>", status_code=404
        )

    locations_data = [
        (loc.latitude, loc.longitude, loc.description) for loc in trip.locations
    ]
    html_content = generate_full_map_html(locations_data)

    return HTMLResponse(content=html_content, status_code=200)


# Requests Routes


@router.get("/", response_model=list[TripResponse])
async def get_trips(db: Session = Depends(get_db), limit: int = 100):
    """Get a list of trips."""
    trip_service = TripService(db)
    trips = trip_service.get_trips(limit=limit)
    return [TripResponse.model_validate(trip) for trip in trips]


@requests_router.get("/", response_model=list[RequestResponse])
async def get_requests(
    only_trips: bool = False,
    db: Session = Depends(get_db),
    limit: int = 100,
    order: str = "desc",
):
    """Get a list of requests (History)."""
    req_service = RequestService(db)
    requests = req_service.get_requests(limit=limit, order=order, only_trips=only_trips)
    return [RequestResponse.model_validate(req) for req in requests]
