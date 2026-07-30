import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.user import User


class ShelfStatus(enum.StrEnum):
    WANT_TO_PLAY = "want_to_play"
    PLAYING = "playing"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"


class ShelfEntry(Base, TimestampMixin):
    """One game on one user's shelf, with how far along they are."""

    __tablename__ = "shelf_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_shelf_entries_user_game"),
        CheckConstraint("hours_played >= 0", name="ck_shelf_entries_hours_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[ShelfStatus] = mapped_column(
        Enum(ShelfStatus, name="shelf_status", values_callable=lambda e: [m.value for m in e]),
        default=ShelfStatus.WANT_TO_PLAY,
        index=True,
        nullable=False,
    )
    hours_played: Mapped[float | None] = mapped_column(Numeric(6, 1))
    platform: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    started_on: Mapped[date | None] = mapped_column()
    finished_on: Mapped[date | None] = mapped_column()
    replay_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="shelf_entries")
    game: Mapped["Game"] = relationship(back_populates="shelf_entries")

    def __repr__(self) -> str:
        return (
            f"<ShelfEntry user_id={self.user_id} game_id={self.game_id} status={self.status.value}>"
        )
