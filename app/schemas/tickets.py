from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateTicketRequest(BaseModel):
    """Данные для регистрации посетителя на событие."""

    event_id: UUID = Field(description="UUID опубликованного события.")
    first_name: str = Field(min_length=1, max_length=255, description="Имя посетителя.")
    last_name: str = Field(min_length=1, max_length=255, description="Фамилия посетителя.")
    email: EmailStr = Field(description="Электронная почта посетителя.")
    seat: str = Field(min_length=1, max_length=50, description="Выбранное свободное место, например A15.")


class CreateTicketResponse(BaseModel):
    """Ответ после успешной регистрации на событие."""

    ticket_id: UUID


class DeleteTicketResponse(BaseModel):
    """Ответ после успешной отмены регистрации."""

    success: bool
