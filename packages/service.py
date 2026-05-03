"""Package service with comprehensive edge-case validation."""

from datetime import datetime, date
from typing import Optional, Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Package, Sender, Traveler, Trip
from packages.schemas import PackageCreate, PackageUpdate
from errors.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
)

VALID_STATUSES = {"pending", "accepted", "in_transit", "delivered", "cancelled"}
VALID_SIZES = {"small", "medium", "large"}

# Status transition rules
ALLOWED_TRANSITIONS = {
    "pending": {"accepted", "cancelled"},
    "accepted": {"in_transit", "cancelled"},
    "in_transit": {"delivered"},
    "delivered": set(),  # terminal
    "cancelled": set(),  # terminal
}


async def list_packages(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    status_filter: Optional[str] = None,
    pickup_city: Optional[str] = None,
    delivery_city: Optional[str] = None,
    sender_id: Optional[int] = None,
    traveler_id: Optional[int] = None,
    max_weight: Optional[float] = None,
    sort_by: str = "id",
    order: str = "desc",
) -> Sequence[Package]:
    stmt = select(Package)
    if status_filter:
        if status_filter not in VALID_STATUSES:
            raise BadRequestException(
                detail=f"Invalid status '{status_filter}'. Must be one of: {', '.join(VALID_STATUSES)}"
            )
        stmt = stmt.where(Package.status == status_filter)
    if pickup_city:
        stmt = stmt.where(Package.pickup_city.ilike(f"%{pickup_city}%"))  # type: ignore[attr-defined]
    if delivery_city:
        stmt = stmt.where(Package.delivery_city.ilike(f"%{delivery_city}%"))  # type: ignore[attr-defined]
    if sender_id:
        stmt = stmt.where(Package.sender_id == sender_id)
    if traveler_id:
        stmt = stmt.where(Package.accepted_traveler_id == traveler_id)
    if max_weight:
        stmt = stmt.where(Package.weight_kg <= max_weight)

    sort_column = getattr(Package, sort_by, Package.id)
    if order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    stmt = stmt.offset(skip).limit(limit)
    result = await session.exec(stmt)
    return result.all()


async def get_package(session: AsyncSession, package_id: int) -> Package:
    package = await session.get(Package, package_id)
    if not package:
        raise NotFoundException(detail=f"Package with id {package_id} not found")
    return package


async def _validate_foreign_keys(
    session: AsyncSession,
    sender_id: Optional[int],
    traveler_id: Optional[int],
) -> None:
    if sender_id is not None:
        sender = await session.get(Sender, sender_id)
        if not sender:
            raise NotFoundException(detail=f"Sender with id {sender_id} not found")
    if traveler_id is not None:
        traveler = await session.get(Traveler, traveler_id)
        if not traveler:
            raise NotFoundException(detail=f"Traveler with id {traveler_id} not found")


def _validate_package_data(payload_dict: dict) -> None:
    """Validate business rules on package data."""
    size = payload_dict.get("size")
    if size and size not in VALID_SIZES:
        raise BadRequestException(
            detail=f"Invalid size '{size}'. Must be one of: {', '.join(VALID_SIZES)}"
        )

    status_val = payload_dict.get("status")
    if status_val and status_val not in VALID_STATUSES:
        raise BadRequestException(
            detail=f"Invalid status '{status_val}'. Must be one of: {', '.join(VALID_STATUSES)}"
        )

    deadline = payload_dict.get("deadline")
    if deadline and isinstance(deadline, date) and deadline < date.today():
        raise BadRequestException(detail="Deadline cannot be in the past")

    pickup = payload_dict.get("pickup_city")
    delivery = payload_dict.get("delivery_city")
    if pickup and delivery and pickup.lower() == delivery.lower():
        raise BadRequestException(detail="Pickup and delivery cities cannot be the same")


async def create_package(
    session: AsyncSession, payload: PackageCreate, current_user_id: int | None = None
) -> Package:
    await _validate_foreign_keys(
        session, sender_id=payload.sender_id, traveler_id=payload.accepted_traveler_id
    )

    payload_dict = payload.model_dump()
    _validate_package_data(payload_dict)

    # Edge case: if status is not pending on creation
    if payload.status != "pending":
        raise BadRequestException(detail="New packages must start with status 'pending'")

    # Ownership check: sender must belong to current user
    if current_user_id:
        sender = await session.get(Sender, payload.sender_id)
        if sender and sender.user_id and sender.user_id != current_user_id:
            raise ForbiddenException(detail="You can only create packages for your own sender profile")

    # Edge case: if accepted_traveler_id is set on creation, validate traveler has capacity
    if payload.accepted_traveler_id:
        raise BadRequestException(
            detail="Cannot assign a traveler on creation. Create the package first, then accept it."
        )

    package = Package(**payload_dict)
    session.add(package)
    await session.commit()
    await session.refresh(package)
    return package


async def accept_package(
    session: AsyncSession, package_id: int, traveler_id: int, current_user_id: int | None = None
) -> Package:
    """Traveler accepts a pending package."""
    package = await get_package(session, package_id)

    if package.status != "pending":
        raise BadRequestException(
            detail=f"Package cannot be accepted in '{package.status}' status. Must be 'pending'."
        )

    # Validate traveler exists
    traveler = await session.get(Traveler, traveler_id)
    if not traveler:
        raise NotFoundException(detail=f"Traveler with id {traveler_id} not found")

    # Ownership check
    if current_user_id and traveler.user_id and traveler.user_id != current_user_id:
        raise ForbiddenException(detail="You can only accept packages with your own traveler profile")

    # Edge case: check if traveler has an open trip matching the package route
    has_matching_trip = False
    for trip in traveler.trips:
        if (
            trip.status == "open"
            and trip.from_city.lower() == package.pickup_city.lower()
            and trip.to_city.lower() == package.delivery_city.lower()
            and trip.available_weight_kg >= package.weight_kg
            and trip.departure_date >= date.today()
        ):
            has_matching_trip = True
            # Reduce available weight on the trip
            trip.available_weight_kg -= package.weight_kg
            if trip.available_weight_kg <= 0:
                trip.status = "full"
            break

    if not has_matching_trip:
        raise BadRequestException(
            detail="Traveler has no open trip matching this package's route with sufficient weight capacity"
        )

    package.accepted_traveler_id = traveler_id
    package.status = "accepted"
    package.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(package)
    return package


async def update_package_status(
    session: AsyncSession, package_id: int, new_status: str, current_user_id: int | None = None
) -> Package:
    """Update package status with transition validation."""
    package = await get_package(session, package_id)

    if new_status not in VALID_STATUSES:
        raise BadRequestException(
            detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(VALID_STATUSES)}"
        )

    allowed = ALLOWED_TRANSITIONS.get(package.status, set())
    if new_status not in allowed:
        raise BadRequestException(
            detail=f"Cannot transition from '{package.status}' to '{new_status}'. Allowed: {', '.join(allowed) or 'none (terminal state)'}"
        )

    # For cancellation, restore trip weight if there was an accepted traveler
    if new_status == "cancelled" and package.accepted_traveler_id:
        traveler = await session.get(Traveler, package.accepted_traveler_id)
        if traveler:
            for trip in traveler.trips:
                if (
                    trip.from_city.lower() == package.pickup_city.lower()
                    and trip.to_city.lower() == package.delivery_city.lower()
                ):
                    trip.available_weight_kg += package.weight_kg
                    if trip.status == "full":
                        trip.status = "open"
                    break

    package.status = new_status
    package.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(package)
    return package


async def update_package_full(
    session: AsyncSession, package_id: int, payload: PackageCreate, current_user_id: int | None = None
) -> Package:
    package = await get_package(session, package_id)

    # Edge case: cannot update delivered or cancelled packages
    if package.status in ("delivered", "cancelled"):
        raise BadRequestException(
            detail=f"Cannot update package in '{package.status}' status"
        )

    if current_user_id:
        sender = await session.get(Sender, package.sender_id)
        if sender and sender.user_id and sender.user_id != current_user_id:
            raise ForbiddenException(detail="You can only update your own packages")

    await _validate_foreign_keys(
        session, sender_id=payload.sender_id, traveler_id=payload.accepted_traveler_id
    )

    payload_dict = payload.model_dump()
    _validate_package_data(payload_dict)

    for field, value in payload_dict.items():
        setattr(package, field, value)
    package.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(package)
    return package


async def update_package_partial(
    session: AsyncSession, package_id: int, payload: PackageUpdate, current_user_id: int | None = None
) -> Package:
    package = await get_package(session, package_id)

    if package.status in ("delivered", "cancelled"):
        raise BadRequestException(
            detail=f"Cannot update package in '{package.status}' status"
        )

    if current_user_id:
        sender = await session.get(Sender, package.sender_id)
        if sender and sender.user_id and sender.user_id != current_user_id:
            raise ForbiddenException(detail="You can only update your own packages")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException(detail="At least one field must be provided")

    await _validate_foreign_keys(
        session,
        sender_id=data.get("sender_id"),
        traveler_id=data.get("accepted_traveler_id"),
    )

    _validate_package_data(data)

    for field, value in data.items():
        setattr(package, field, value)
    package.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(package)
    return package


async def delete_package(
    session: AsyncSession, package_id: int, current_user_id: int | None = None, is_admin: bool = False
) -> None:
    package = await get_package(session, package_id)

    # Edge case: cannot delete in_transit packages
    if package.status == "in_transit":
        raise BadRequestException(detail="Cannot delete a package that is in transit")

    if not is_admin and current_user_id:
        sender = await session.get(Sender, package.sender_id)
        if sender and sender.user_id and sender.user_id != current_user_id:
            raise ForbiddenException(detail="You can only delete your own packages")

    await session.delete(package)
    await session.commit()
