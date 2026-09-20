from pydantic import BaseModel, Field, field_validator


class GuestWriteRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    document: str = Field(min_length=2, max_length=50)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("full_name", "document")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("email", "phone")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class GuestView(BaseModel):
    id: int
    full_name: str
    document: str
    email: str | None
    phone: str | None
    active: bool
    status_label: str
    status_style: str
