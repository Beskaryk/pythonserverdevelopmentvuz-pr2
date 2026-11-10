"""Схемы входных данных Pydantic."""

from pydantic import BaseModel, ConfigDict


class BodyModel(BaseModel):
    """Строгая проверка JSON-тела."""

    model_config = ConfigDict(extra="forbid", strict=True)


class QueryModel(BaseModel):
    """Проверка параметров строки запроса."""

    model_config = ConfigDict(extra="forbid")


class ParticipantCreate(BodyModel):
    timestamp: int
    locale: str
    platform: str


class CommandCreate(BodyModel):
    timestamp: int
    content: str
    participant: int
    state: str
    enqueued: int
    video: str | None = None


class ParticipantFilters(QueryModel):
    identifier: int | None = None
    timestamp: int | None = None
    locale: str | None = None
    platform: str | None = None


class CommandFilters(QueryModel):
    identifier: int | None = None
    timestamp: int | None = None
    content: str | None = None
    participant: int | None = None
    state: str | None = None
    enqueued: int | None = None


class OutputFilters(QueryModel):
    identifier: int | None = None
    timestamp: int | None = None
    result: str | None = None
    state: str | None = None
    exception: str | None = None
    command: int | None = None


class IdentifierQuery(QueryModel):
    identifier: int
