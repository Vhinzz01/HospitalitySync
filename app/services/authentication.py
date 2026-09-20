from app.core.security import PasswordHasher, password_hasher
from app.models import User
from app.repositories import UserRepository


class AuthenticationService:
    def __init__(
        self,
        user_repository: UserRepository,
        hasher: PasswordHasher = password_hasher,
    ) -> None:
        self._user_repository = user_repository
        self._hasher = hasher

    def authenticate_receptionist(self, email: str, password: str) -> User | None:
        user = self._user_repository.get_by_email(email.strip())
        if user is None:
            self._hasher.verify_dummy(password)
            return None

        password_is_valid = self._hasher.verify(password, user.password_hash)
        if not password_is_valid or not user.active or user.role != "RECEPTION":
            return None

        return user

    def get_authenticated_receptionist(self, user_id: int) -> User | None:
        user = self._user_repository.get_by_id(user_id)
        if user is None or not user.active or user.role != "RECEPTION":
            return None
        return user

    def authenticate_kitchen_user(self, email: str, password: str) -> User | None:
        user = self._user_repository.get_by_email(email.strip())
        if user is None:
            self._hasher.verify_dummy(password)
            return None
        password_is_valid = self._hasher.verify(password, user.password_hash)
        if not password_is_valid or not user.active or user.role != "KITCHEN":
            return None
        return user

    def get_authenticated_kitchen_user(self, user_id: int) -> User | None:
        user = self._user_repository.get_by_id(user_id)
        if user is None or not user.active or user.role != "KITCHEN":
            return None
        return user
