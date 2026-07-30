from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.shelf import ShelfStatus
from app.schemas.game import GameSummary


class ShelfEntryBase(BaseModel):
    status: ShelfStatus = ShelfStatus.WANT_TO_PLAY
    hours_played: float | None = Field(default=None, ge=0, le=99999)
    platform: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    started_on: date | None = None
    finished_on: date | None = None
    replay_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_dates_ordered(self) -> "ShelfEntryBase":
        if self.started_on and self.finished_on and self.finished_on < self.started_on:
            raise ValueError("finished_on cannot be earlier than started_on")
        return self


class ShelfEntryCreate(ShelfEntryBase):
    """Add a game to the shelf by its RAWG id — we mirror the game if we lack it."""

    rawg_id: int


class ShelfEntryUpdate(BaseModel):
    status: ShelfStatus | None = None
    hours_played: float | None = Field(default=None, ge=0, le=99999)
    platform: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    started_on: date | None = None
    finished_on: date | None = None
    replay_count: int | None = Field(default=None, ge=0)


class ShelfEntryRead(ShelfEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    game: GameSummary
    created_at: datetime
    updated_at: datetime


class ShelfStats(BaseModel):
    """Counts per status, for the shelf dashboard."""

    total: int
    by_status: dict[ShelfStatus, int]
    total_hours: float
