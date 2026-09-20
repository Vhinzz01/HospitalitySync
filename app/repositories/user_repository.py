from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(func.lower(User.email) == email.lower())
        return self._session.scalar(statement)

    def get_by_id(self, user_id: int) -> User | None:
        return self._session.get(User, user_id)
