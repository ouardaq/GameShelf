"""Builders for test rows.

Every field a test does not care about gets a plausible unique default, so a
test about shelf statuses does not have to invent an email address, and two
users created in the same test cannot collide on the unique indexes.

Defaults are merged rather than passed as keywords, so a test is free to
override any of them.
"""

from itertools import count
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import Base
from app.models import Game, Review, ShelfEntry, User

_counter = count(1)


def _persist[ModelT: Base](
    db: Session, model: type[ModelT], defaults: dict[str, Any], overrides: dict[str, Any]
) -> ModelT:
    instance = model(**(defaults | overrides))
    db.add(instance)
    db.commit()
    return instance


def make_user(db: Session, **overrides: Any) -> User:
    n = next(_counter)
    return _persist(
        db,
        User,
        {
            "email": f"user{n}@example.com",
            "username": f"user{n}",
            "hashed_password": "not-a-real-hash",
        },
        overrides,
    )


def make_game(db: Session, **overrides: Any) -> Game:
    n = next(_counter)
    return _persist(
        db,
        Game,
        {
            "rawg_id": n,
            "slug": f"game-{n}",
            "name": f"Game {n}",
        },
        overrides,
    )


def make_shelf_entry(db: Session, **overrides: Any) -> ShelfEntry:
    defaults = {
        "user_id": overrides.get("user_id") or make_user(db).id,
        "game_id": overrides.get("game_id") or make_game(db).id,
    }
    return _persist(db, ShelfEntry, defaults, overrides)


def make_review(db: Session, **overrides: Any) -> Review:
    defaults = {
        "user_id": overrides.get("user_id") or make_user(db).id,
        "game_id": overrides.get("game_id") or make_game(db).id,
        "rating": 8,
    }
    return _persist(db, Review, defaults, overrides)
