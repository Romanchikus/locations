from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.models import Location, Request, Trip
from app.schemas import (
    LocationCreate,
    RequestCreate,
    TripCreate,
)
from typing import List, Optional
import logging


logger = logging.getLogger(__name__)


class RequestService:
    """Service class for request operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_request(self, request_data: RequestCreate) -> Request:
        """Create a new request."""
        db_request = Request(**request_data.model_dump())
        self.db.add(db_request)
        self.db.commit()
        self.db.refresh(db_request)
        return db_request

    def get_request(self, request_id: int) -> Optional[Request]:
        """Get a request by ID."""
        stmt = select(Request).where(Request.id == request_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_requests(
        self, limit: int = 100, order: str = "desc", only_trips=False
    ) -> List[Request]:
        """Get a list of requests with an optional limit.

        Args:
            limit: Maximum number of requests to return
            order: Sort order ('asc' or 'desc') by created_at
            only_trips: If True, return only requests that have associated trips
        """
        stmt = select(Request)

        if only_trips:
            stmt = stmt.join(Trip, Request.id == Trip.request_id)
            stmt = stmt.options(selectinload(Request.trip).selectinload(Trip.locations))
            stmt = stmt.distinct()

        # Apply ordering
        stmt = stmt.order_by(
            Request.created_at.desc()
            if order == "desc"
            else Request.created_at.asc()
        )

        # Apply limit
        stmt = stmt.limit(limit)

        # Execute the statement and return the results as a list
        return list(self.db.execute(stmt).scalars().all())

    def update_request(self, request: Request, response_data: RequestCreate) -> Request:
        for field, value in response_data.model_dump().items():
            setattr(request, field, value)
        self.db.commit()
        self.db.refresh(request)
        return request


class TripService:
    """Service class for trip operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_trip(self, trip_data: TripCreate) -> Trip:
        """Create a new trip."""
        db_trip = Trip(**trip_data.model_dump())
        self.db.add(db_trip)
        self.db.commit()
        self.db.refresh(db_trip)
        return db_trip

    def get_trip(self, trip_id: int) -> Optional[Trip]:
        """Get a trip by ID."""
        stmt = (
            select(Trip)
            .where(Trip.id == trip_id)
            .options(selectinload(Trip.locations))  # Ensure locations are loaded
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update_trip(self, trip_id: int, response_json: dict) -> Optional[Trip]:
        """Update a trip with response data."""
        db_trip = self.get_trip(trip_id)
        if not db_trip:
            return None

        db_trip.response_json = response_json
        self.db.commit()
        self.db.refresh(db_trip)
        return db_trip

    def get_trips(self, limit: int = 100) -> List[Trip]:
        """Get a list of trips with an optional limit."""
        stmt = select(Trip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def get_trip_by_request_id(self, request_id: int) -> Optional[Trip]:
        """Get a trip by request ID."""
        stmt = (
            select(Trip)
            .where(Trip.request_id == request_id)
            .options(selectinload(Trip.locations), selectinload(Trip.request))
        )
        return self.db.execute(stmt).scalar_one_or_none()


class LocationService:
    """Service class for location operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_location(self, location_data: LocationCreate) -> Location:
        """Create a new location."""
        db_location = Location(**location_data.model_dump())
        self.db.add(db_location)
        self.db.commit()
        self.db.refresh(db_location)
        return db_location

    def bulk_create_locations(
        self, locations_data: List[LocationCreate]
    ) -> List[Location]:
        """Bulk create locations."""
        try:
            # Create all location instances first
            db_locations = []
            for data in locations_data:
                location_dict = data.model_dump(exclude_none=True)
                logger.debug("Creating location with data: %s", location_dict)
                location = Location(**location_dict)
                self.db.add(location)
                db_locations.append(location)

            # Flush to get IDs but don't commit yet
            self.db.flush()
            logger.debug("Successfully flushed %d locations", len(db_locations))
            return db_locations
        except Exception as e:
            logger.error("Error in bulk_create_locations: %s", str(e), exc_info=True)
            self.db.rollback()
            raise

    def get_location(self, location_id: int) -> Optional[Location]:
        """Get a location by ID."""
        stmt = select(Location).where(Location.id == location_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_locations_by_trip(self, trip_id: int) -> List[Location]:
        """Get locations for a specific trip."""
        stmt = (
            select(Location)
            .where(Location.trip_id == trip_id)
            .order_by(Location.order.asc().nulls_last())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_locations_for_trip(
        self, trip_id: int, locations_data: List[LocationCreate]
    ) -> List[Location]:
        """Create multiple locations for a trip."""
        try:
            if not trip_id:
                raise ValueError("trip_id must be provided")

            # Set trip_id and order for each location
            for i, location_data in enumerate(locations_data):
                location_data.trip_id = trip_id
                location_data.order = i + 1

            logger.debug(
                "Creating %d locations for trip %d", len(locations_data), trip_id
            )
            locations = self.bulk_create_locations(locations_data)
            self.db.commit()
            return locations
        except Exception as e:
            logger.error(
                "Error in create_locations_for_trip: %s", str(e), exc_info=True
            )
            self.db.rollback()
            raise
