from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.game import GameSummary
from app.schemas.user import UserPublic


class ReviewBase(BaseModel):
    rating: int = Field(ge=1, le=10)
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=10000)
    contains_spoilers: bool = False


class ReviewCreate(ReviewBase):
    rawg_id: int


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=10)
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=10000)
    contains_spoilers: bool | None = None


class ReviewRead(ReviewBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user: UserPublic
    game: GameSummary
    created_at: datetime
    updated_at: datetime
