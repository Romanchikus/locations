from sqlalchemy import String, Float, DateTime, Text, func, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.database import Base


class Request(Base):
    """Base class for history tracking."""

    __tablename__ = "requests"

    # Primary key with proper type annotation
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Required fields
    method: Mapped[str] = mapped_column(String(10), index=True)
    url: Mapped[str] = mapped_column(String(255))
    headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    body: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    trip: Mapped[Optional["Trip"]] = relationship(
        "Trip",
        back_populates="request",
        foreign_keys="[Trip.request_id]",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Request(id={self.id}, method='{self.method}', url='{self.url}')>"


class Trip(Base):
    """Trip model for storing predict data."""

    __tablename__ = "trips"

    # Primary key with proper type annotation
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Foreign key to request
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    # relationship to itself if request was updated within "exclude" parameter
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("trips.id"), nullable=True
    )

    # Required fields
    response_json: Mapped[Optional[dict | list]] = mapped_column(JSON, nullable=True)
    num_places: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship to locations
    locations: Mapped[list["Location"]] = relationship(back_populates="trip")
    request: Mapped["Request"] = relationship(
        "Request", back_populates="trip", foreign_keys=[request_id]
    )
    trip_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="several_places"
    )


class Location(Base):
    """Location model for storing geographical locations."""

    __tablename__ = "locations"

    # Primary key with proper type annotation
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    trip: Mapped["Trip"] = relationship(back_populates="locations")

    # Required fields
    name: Mapped[str] = mapped_column(String(100), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Optional fields with proper typing
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Location(id={self.id}, name='{self.name}')>"
