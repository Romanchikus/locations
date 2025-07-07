from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any, List


class TripTypeEnum(str, Enum):
    """Enumeration for different trip types."""

    several_places = "several_places"
    by_place = "by_place"


# Request schemas
class RequestCreate(BaseModel):
    """Schema for creating a new request."""

    method: str = Field(..., max_length=10)
    url: str = Field(..., max_length=255)
    headers: Optional[Dict[str, Any]] = Field(None)
    body: Optional[Dict[str, Any]] = Field(None)

    # validate body to have the "text" key
    def validate_body(self):
        if self.body and not isinstance(self.body, dict):
            raise ValueError("Body must be a dictionary.")
        if self.body and "text" not in self.body:
            raise ValueError("Body must contain a 'text' key.")

    model_config = ConfigDict(from_attributes=True)


class TripCreateRequest(BaseModel):
    """Schema for creating a new trip request."""

    request_text: str = Field(
        str,
        min_length=1,
        max_length=1000,
        examples=[
            "I want to visit Eiffel Tower, Independence monument Kyiv, and Statue of Liberty in New York.",
            "Plan a trip to Golden Gate Bridge, Yosemite National Park, and Alcatraz Island.",
        ],
    )
    start_location: str = Field(
        None,
        min_length=1,
        max_length=100,
        examples=[
            "Start from Paris",
            "Begin in San Francisco",
            "Starting point: New York City",
        ],
    )
    num_places: Optional[int] = Field(
        None,
        ge=3,
        le=10,
        description="Number of places to include in the trip. If not specified, all relevant places will be included.",
        examples=[5, 10],
    )


class ExcludeLocationsRequest(BaseModel):
    """Schema for excluding specific locations from a trip."""

    exclude_text: str = Field(
        str,
        min_length=1,
        max_length=1000,
        examples=[
            "Exclude Eiffel Tower",
            "Do not include Independence monument Kyiv in the trip.",
            "Remove Statue of Liberty from the trip plan.",
        ],
    )


# Trip schemas
class TripCreate(BaseModel):
    """Schema for creating a new trip."""

    request_id: Optional[int] = None
    parent_id: Optional[int] = Field(None)
    response_json: Optional[Dict[str, Any] | List[Dict[str, Any]]] = Field(None)
    num_places: Optional[int] = Field(None)
    trip_type: TripTypeEnum = Field(
        TripTypeEnum.several_places, description="Type of the trip."
    )


# Location schemas
class LocationCreate(BaseModel):
    """Schema for creating a new location."""

    trip_id: Optional[int] = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    order: Optional[int] = Field(None)

    class Config:
        from_attributes = True  # Enable compatibility with SQLAlchemy models


class LocationResponse(BaseModel):
    """Schema for location response."""

    id: int
    trip_id: Optional[int] = Field(..., ge=1)
    name: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    order: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TripResponse(BaseModel):
    """Schema for trip response."""

    id: int
    request_id: Optional[int] = None
    parent_id: Optional[int] = None
    num_places: Optional[int] = None
    created_at: datetime
    locations: Optional[List[LocationResponse]] = None
    trip_type: TripTypeEnum = Field(
        TripTypeEnum.several_places, description="Type of the trip."
    )

    class Config:
        """Configuration for TripResponse model."""

        from_attributes = True  # use with SQLAlchemy models


class RequestResponse(BaseModel):
    """Schema for request response."""

    id: int
    method: str
    url: str
    headers: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    created_at: datetime
    trip: Optional[TripResponse] = None

    model_config = ConfigDict(from_attributes=True)
