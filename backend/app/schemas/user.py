from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)


class UserRead(UserBase):
    """Public shape of a user — never carries the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    bio: str | None = None
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime


class UserPublic(BaseModel):
    """Trimmed user, for embedding in reviews and other users' views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    avatar_url: str | None = None
