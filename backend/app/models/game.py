from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.review import Review
    from app.models.shelf import ShelfEntry


class Game(Base, TimestampMixin):
    """A game, mirrored locally from RAWG so the app is not tied to their uptime."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    rawg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    background_image: Mapped[str | None] = mapped_column(String(500))
    released: Mapped[date | None] = mapped_column()
    metacritic: Mapped[int | None] = mapped_column(Integer)
    rawg_rating: Mapped[float | None] = mapped_column(Float)
    playtime_hours: Mapped[int | None] = mapped_column(Integer)

    # Denormalised RAWG facets — read far more often than they are queried on.
    genres: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    platforms: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    developers: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)

    # When we last refreshed this row from RAWG.
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    shelf_entries: Mapped[list["ShelfEntry"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Game id={self.id} name={self.name!r}>"
