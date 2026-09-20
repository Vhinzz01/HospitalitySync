from sqlalchemy.exc import IntegrityError

from app.models import Guest
from app.repositories import GuestRepository
from app.schemas import GuestView, GuestWriteRequest


class GuestError(Exception):
    pass


class GuestNotFoundError(GuestError):
    pass


class GuestConflictError(GuestError):
    pass


class GuestValidationError(GuestError):
    pass


class GuestService:
    def __init__(self, repository: GuestRepository) -> None:
        self._repository = repository

    def list_guests(
        self,
        state: str = "active",
        search: str | None = None,
    ) -> list[GuestView]:
        states = {"active": True, "inactive": False, "all": None}
        if state not in states:
            raise GuestValidationError("Filtro de situação inválido.")
        return [
            self._to_view(guest)
            for guest in self._repository.list(active=states[state], search=search)
        ]

    def get(self, guest_id: int) -> GuestView:
        guest = self._repository.get(guest_id)
        if guest is None:
            raise GuestNotFoundError("Hóspede não encontrado.")
        return self._to_view(guest)

    def create(self, data: GuestWriteRequest) -> GuestView:
        normalized = self._normalize(data)
        if self._repository.document_exists(normalized.document):
            raise GuestConflictError("Já existe um hóspede com este documento.")

        guest = Guest(
            full_name=normalized.full_name,
            document=normalized.document,
            email=normalized.email,
            phone=normalized.phone,
            active=True,
        )
        self._repository.add(guest)
        self._commit_with_conflict_handling()
        return self._to_view(guest)

    def update(self, guest_id: int, data: GuestWriteRequest) -> GuestView:
        guest = self._repository.get(guest_id)
        if guest is None:
            raise GuestNotFoundError("Hóspede não encontrado.")

        normalized = self._normalize(data)
        if self._repository.document_exists(normalized.document, guest_id):
            raise GuestConflictError("Já existe um hóspede com este documento.")

        guest.full_name = normalized.full_name
        guest.document = normalized.document
        guest.email = normalized.email
        guest.phone = normalized.phone
        self._commit_with_conflict_handling()
        return self._to_view(guest)

    def deactivate(self, guest_id: int) -> GuestView:
        guest = self._repository.get(guest_id)
        if guest is None:
            raise GuestNotFoundError("Hóspede não encontrado.")
        if guest.active:
            guest.active = False
            self._repository.commit()
        return self._to_view(guest)

    def _normalize(self, data: GuestWriteRequest) -> GuestWriteRequest:
        email = data.email.lower() if data.email else None
        if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
            raise GuestValidationError("E-mail inválido.")
        return GuestWriteRequest(
            full_name=" ".join(data.full_name.split()),
            document=data.document.upper(),
            email=email,
            phone=data.phone,
        )

    def _commit_with_conflict_handling(self) -> None:
        try:
            self._repository.commit()
        except IntegrityError as error:
            self._repository.rollback()
            if getattr(error.orig, "sqlstate", None) == "23505":
                raise GuestConflictError(
                    "Já existe um hóspede com este documento."
                ) from error
            raise

    @staticmethod
    def _to_view(guest: Guest) -> GuestView:
        return GuestView(
            id=guest.id,
            full_name=guest.full_name,
            document=guest.document,
            email=guest.email,
            phone=guest.phone,
            active=guest.active,
            status_label="Ativo" if guest.active else "Inativo",
            status_style="available" if guest.active else "checked-out",
        )
