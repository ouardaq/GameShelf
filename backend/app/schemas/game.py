from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GameSummary(BaseModel):
    """Card-sized game, for search results and shelf listings."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    rawg_id: int
    slug: str
    name: str
    background_image: str | None = None
    released: date | None = None
    metacritic: int | None = None


class GameRead(GameSummary):
    """Full game detail page payload."""

    description: str | None = None
    rawg_rating: float | None = None
    playtime_hours: int | None = None
    genres: list[dict[str, Any]] = Field(default_factory=list)
    platforms: list[dict[str, Any]] = Field(default_factory=list)
    developers: list[dict[str, Any]] = Field(default_factory=list)
    synced_at: datetime


class GameCreate(BaseModel):
    """Internal shape used when mirroring a RAWG payload into our games table."""

    rawg_id: int
    slug: str
    name: str
    description: str | None = None
    background_image: str | None = None
    released: date | None = None
    metacritic: int | None = None
    rawg_rating: float | None = None
    playtime_hours: int | None = None
    genres: list[dict[str, Any]] = Field(default_factory=list)
    platforms: list[dict[str, Any]] = Field(default_factory=list)
    developers: list[dict[str, Any]] = Field(default_factory=list)
