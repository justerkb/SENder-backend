"""Trip service with edge-case validation and custom exceptions."""

from datetime import datetime, date
from typing import Optional, Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Trip, Traveler
from trips.schemas import TripCreate, TripUpdate
from errors.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
)

VALID_STATUSES = {"open", "full", "completed", "cancelled"}


async def list_trips(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    from_city: Optional[str] = None,
    to_city: Optional[str] = None,
    status_filter: Optional[str] = None,
    traveler_id: Optional[int] = None,
    min_weight: Optional[float] = None,
    sort_by: str = "id",
    order: str = "desc",
) -> Sequence[Trip]:
    stmt = select(Trip)
    if from_city:
        stmt = stmt.where(Trip.from_city.ilike(f"%{from_city}%"))  # type: ignore[attr-defined]
    if to_city:
        stmt = stmt.where(Trip.to_city.ilike(f"%{to_city}%"))  # type: ignore[attr-defined]
    if status_filter:
        if status_filter not in VALID_STATUSES:
            raise BadRequestException(
                detail=f"Invalid status '{status_filter}'. Must be one of: {', '.join(VALID_STATUSES)}"
            )
        stmt = stmt.where(Trip.status == status_filter)
    if traveler_id:
        stmt = stmt.where(Trip.traveler_id == traveler_id)
    if min_weight:
        stmt = stmt.where(Trip.available_weight_kg >= min_weight)

    sort_column = getattr(Trip, sort_by, Trip.id)
    if order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    stmt = stmt.offset(skip).limit(limit)
    result = await session.exec(stmt)
    return result.all()


async def get_trip(session: AsyncSession, trip_id: int) -> Trip:
    trip = await session.get(Trip, trip_id)
    if not trip:
        raise NotFoundException(detail=f"Trip with id {trip_id} not found")
    return trip


async def _validate_traveler(session: AsyncSession, traveler_id: int) -> Traveler:
    traveler = await session.get(Traveler, traveler_id)
    if not traveler:
        raise NotFoundException(detail=f"Traveler with id {traveler_id} not found")
    return traveler


async def _check_date_overlap(
    session: AsyncSession,
    traveler_id: int,
    departure: date,
    arrival: date,
    exclude_trip_id: Optional[int] = None,
) -> None:
    """Edge case: no overlapping trips for same traveler."""
    stmt = select(Trip).where(
        Trip.traveler_id == traveler_id,
        Trip.status.in_(["open", "full"]),  # type: ignore[attr-defined]
        Trip.departure_date <= arrival,
        Trip.arrival_date >= departure,
    )
    if exclude_trip_id:
        stmt = stmt.where(Trip.id != exclude_trip_id)

    result = await session.exec(stmt)
    existing = result.first()
    if existing:
        raise ConflictException(
            detail=f"Trip dates overlap with existing trip #{existing.id} "
            f"({existing.departure_date} - {existing.arrival_date}). "
            f"A traveler cannot have two active trips at the same time."
        )


def _validate_trip_dates(departure: date, arrival: date) -> None:
    if arrival < departure:
        raise BadRequestException(detail="Arrival date cannot be before departure date")
    if departure < date.today():
        raise BadRequestException(detail="Departure date cannot be in the past")


async def create_trip(
    session: AsyncSession, payload: TripCreate, current_user_id: int | None = None
) -> Trip:
    traveler = await _validate_traveler(session, payload.traveler_id)

    # Ownership check
    if current_user_id and traveler.user_id and traveler.user_id != current_user_id:
        raise ForbiddenException(detail="You can only create trips for your own traveler profile")

    _validate_trip_dates(payload.departure_date, payload.arrival_date)

    # Edge case: same origin and destination
    if payload.from_city.lower() == payload.to_city.lower():
        raise BadRequestException(detail="Origin and destination cities cannot be the same")

    # Edge case: date overlap
    await _check_date_overlap(session, payload.traveler_id, payload.departure_date, payload.arrival_date)

    trip = Trip(**payload.model_dump())
    session.add(trip)
    await session.commit()
    await session.refresh(trip)
    return trip


async def update_trip_full(
    session: AsyncSession, trip_id: int, payload: TripCreate, current_user_id: int | None = None
) -> Trip:
    trip = await get_trip(session, trip_id)

    # Cannot update completed/cancelled trips
    if trip.status in ("completed", "cancelled"):
        raise BadRequestException(detail=f"Cannot update trip in '{trip.status}' status")

    traveler = await _validate_traveler(session, payload.traveler_id)

    if current_user_id and traveler.user_id and traveler.user_id != current_user_id:
        raise ForbiddenException(detail="You can only update your own trips")

    _validate_trip_dates(payload.departure_date, payload.arrival_date)

    if payload.from_city.lower() == payload.to_city.lower():
        raise BadRequestException(detail="Origin and destination cities cannot be the same")

    await _check_date_overlap(
        session, payload.traveler_id, payload.departure_date, payload.arrival_date,
        exclude_trip_id=trip_id,
    )

    for field, value in payload.model_dump().items():
        setattr(trip, field, value)
    trip.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(trip)
    return trip


async def update_trip_partial(
    session: AsyncSession, trip_id: int, payload: TripUpdate, current_user_id: int | None = None
) -> Trip:
    trip = await get_trip(session, trip_id)

    if trip.status in ("completed", "cancelled"):
        raise BadRequestException(detail=f"Cannot update trip in '{trip.status}' status")

    if current_user_id and trip.traveler:
        traveler = trip.traveler
        if traveler.user_id and traveler.user_id != current_user_id:
            raise ForbiddenException(detail="You can only update your own trips")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException(detail="At least one field must be provided")

    # Validate dates
    departure = data.get("departure_date", trip.departure_date)
    arrival = data.get("arrival_date", trip.arrival_date)
    if departure and arrival:
        _validate_trip_dates(departure, arrival)

    from_city = data.get("from_city", trip.from_city)
    to_city = data.get("to_city", trip.to_city)
    if from_city.lower() == to_city.lower():
        raise BadRequestException(detail="Origin and destination cities cannot be the same")

    # Date overlap check
    traveler_id = data.get("traveler_id", trip.traveler_id)
    if traveler_id and "traveler_id" in data:
        await _validate_traveler(session, traveler_id)

    if departure and arrival:
        await _check_date_overlap(session, traveler_id, departure, arrival, exclude_trip_id=trip_id)

    status_val = data.get("status")
    if status_val and status_val not in VALID_STATUSES:
        raise BadRequestException(
            detail=f"Invalid status '{status_val}'. Must be one of: {', '.join(VALID_STATUSES)}"
        )

    for field, value in data.items():
        setattr(trip, field, value)
    trip.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(trip)
    return trip


async def delete_trip(
    session: AsyncSession, trip_id: int, current_user_id: int | None = None, is_admin: bool = False
) -> None:
    trip = await get_trip(session, trip_id)

    # Edge case: cannot delete trip with active packages
    if trip.status in ("open", "full"):
        # Check if traveler has packages linked to this trip route
        if trip.traveler:
            for pkg in trip.traveler.accepted_packages:
                if (
                    pkg.status in ("accepted", "in_transit")
                    and pkg.pickup_city.lower() == trip.from_city.lower()
                    and pkg.delivery_city.lower() == trip.to_city.lower()
                ):
                    raise BadRequestException(
                        detail=f"Cannot delete trip: package #{pkg.id} is still active on this route"
                    )

    if not is_admin and current_user_id:
        if trip.traveler and trip.traveler.user_id and trip.traveler.user_id != current_user_id:
            raise ForbiddenException(detail="You can only delete your own trips")

    await session.delete(trip)
    await session.commit()
