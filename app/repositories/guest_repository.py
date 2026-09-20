from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Guest


class GuestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, active: bool | None = None, search: str | None = None) -> list[Guest]:
        statement = select(Guest)
        if active is not None:
            statement = statement.where(Guest.active.is_(active))
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Guest.full_name.ilike(pattern),
                    Guest.document.ilike(pattern),
                )
            )
        statement = statement.order_by(Guest.full_name, Guest.id)
        return list(self._session.scalars(statement))

    def get(self, guest_id: int) -> Guest | None:
        return self._session.get(Guest, guest_id)

    def document_exists(self, document: str, exclude_guest_id: int | None = None) -> bool:
        statement = select(Guest.id).where(func.upper(Guest.document) == document.upper())
        if exclude_guest_id is not None:
            statement = statement.where(Guest.id != exclude_guest_id)
        return self._session.scalar(statement.limit(1)) is not None

    def add(self, guest: Guest) -> None:
        self._session.add(guest)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
