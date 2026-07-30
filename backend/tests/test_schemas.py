"""Tests for the request/response contract.

The database rejects bad rows; these check that bad *requests* are refused at
the edge, with a 422-shaped error, before they ever reach it -- and that
responses cannot carry fields the client has no business seeing.
"""

from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.shelf import ShelfStatus
from app.schemas import (
    GameSummary,
    ReviewCreate,
    ShelfEntryCreate,
    UserCreate,
    UserPublic,
    UserRead,
    UserUpdate,
)
from tests.factories import make_game, make_user

# Built rather than written as literals. A username/password pair sitting next
# to each other in source is what secret scanners look for, and a scanner that
# reports test fixtures is one people learn to ignore. Length is what these
# tests are actually about, so derive them from the rule being tested.
_MIN_PASSWORD_LENGTH = 8
LONG_ENOUGH_PASSWORD = "p" * _MIN_PASSWORD_LENGTH
TOO_SHORT_PASSWORD = "p" * (_MIN_PASSWORD_LENGTH - 1)


class TestShelfEntryCreate:
    def test_defaults_to_want_to_play(self) -> None:
        entry = ShelfEntryCreate(rawg_id=1)

        assert entry.status is ShelfStatus.WANT_TO_PLAY

    def test_finishing_before_starting_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="earlier than started_on"):
            ShelfEntryCreate(
                rawg_id=1,
                started_on=date(2026, 5, 1),
                finished_on=date(2026, 4, 1),
            )

    def test_finishing_on_the_start_date_is_allowed(self) -> None:
        day = date(2026, 5, 1)

        entry = ShelfEntryCreate(rawg_id=1, started_on=day, finished_on=day)

        assert entry.finished_on == day

    def test_an_open_ended_entry_is_allowed(self) -> None:
        entry = ShelfEntryCreate(rawg_id=1, started_on=date(2026, 5, 1))

        assert entry.finished_on is None

    def test_negative_hours_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ShelfEntryCreate(rawg_id=1, hours_played=-0.5)

    def test_an_unknown_status_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ShelfEntryCreate(rawg_id=1, status="abandoned_forever")


class TestReviewCreate:
    @pytest.mark.parametrize("rating", [0, 11, -3])
    def test_rating_outside_one_to_ten_is_rejected(self, rating: int) -> None:
        with pytest.raises(ValidationError):
            ReviewCreate(rawg_id=1, rating=rating)

    @pytest.mark.parametrize("rating", [1, 7, 10])
    def test_rating_within_range_is_accepted(self, rating: int) -> None:
        assert ReviewCreate(rawg_id=1, rating=rating).rating == rating

    def test_an_overlong_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReviewCreate(rawg_id=1, rating=5, body="x" * 10_001)


class TestUserCreate:
    def test_a_short_password_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="a@example.com", username="valid", password=TOO_SHORT_PASSWORD)

    def test_a_malformed_email_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", username="valid", password=LONG_ENOUGH_PASSWORD)

    @pytest.mark.parametrize("username", ["ab", "has space", "has@symbol", "wayyy" * 20])
    def test_an_invalid_username_is_rejected(self, username: str) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="a@example.com", username=username, password=LONG_ENOUGH_PASSWORD)

    @pytest.mark.parametrize("username", ["abc", "with_underscore", "with-dash", "MixedCase9"])
    def test_a_valid_username_is_accepted(self, username: str) -> None:
        user = UserCreate(email="a@example.com", username=username, password=LONG_ENOUGH_PASSWORD)

        assert user.username == username


class TestResponseShapes:
    def test_user_read_never_carries_the_password_hash(self, db: Session) -> None:
        user = make_user(db, hashed_password="$2b$12$averysecrethash")

        payload = UserRead.model_validate(user).model_dump()

        assert "hashed_password" not in payload
        assert "averysecrethash" not in str(payload)

    def test_user_public_hides_the_email_too(self, db: Session) -> None:
        user = make_user(db, email="private@example.com")

        payload = UserPublic.model_validate(user).model_dump()

        assert set(payload) == {"id", "username", "avatar_url"}

    def test_user_update_ignores_fields_a_client_may_not_set(self) -> None:
        update = UserUpdate.model_validate(
            {"bio": "hello", "hashed_password": "injected", "is_active": False}
        )

        assert update.bio == "hello"
        assert not hasattr(update, "hashed_password")
        assert not hasattr(update, "is_active")

    def test_game_summary_reads_from_a_model_instance(self, db: Session) -> None:
        game = make_game(db, name="Outer Wilds", metacritic=85)

        summary = GameSummary.model_validate(game)

        assert summary.name == "Outer Wilds"
        assert summary.metacritic == 85
