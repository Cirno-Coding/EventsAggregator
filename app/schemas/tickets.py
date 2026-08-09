from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class CreateTicketRequest(BaseModel):
    """Данные для регистрации посетителя на событие."""

    event_id: UUID = Field(description="UUID опубликованного события.")
    first_name: str = Field(min_length=1, max_length=255, description="Имя посетителя.")
    last_name: str = Field(min_length=1, max_length=255, description="Фамилия посетителя.")
    email: EmailStr = Field(description="Электронная почта посетителя.")
    seat: str = Field(min_length=1, max_length=50, description="Выбранное свободное место, например A15.")
    idempotency_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Необязательный ключ идемпотентности. Повтор одного и того же "
            "запроса с тем же ключом вернёт исходный ticket_id без создания "
            "нового билета."
        ),
    )

    @field_validator("idempotency_key")
    @classmethod
    def normalize_idempotency_key(cls, value: str | None) -> str | None:
        """Удалить пробелы по краям ключа и запретить ключ из одних пробелов."""
        if value is None:
            return None

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Ключ идемпотентности не должен состоять только из пробелов.")

        return normalized_value


class CreateTicketResponse(BaseModel):
    """Ответ после успешной регистрации на событие."""

    ticket_id: UUID


class DeleteTicketResponse(BaseModel):
    """Ответ после успешной отмены регистрации."""

    success: bool
