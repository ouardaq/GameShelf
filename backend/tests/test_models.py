"""Tests for invariants the database enforces.

These deliberately go through the database rather than asserting on Python
objects: the point of a CHECK constraint or an ON DELETE CASCADE is that it
holds even when application code forgets, so the test has to make the database
be the one to refuse.
"""

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Game, Review, ShelfEntry, ShelfStatus, User
from tests.factories import make_game, make_review, make_shelf_entry, make_user


def _count(db: Session, model: type) -> int:
    return db.execute(sa.select(sa.func.count()).select_from(model)).scalar_one()


class TestUser:
    def test_email_is_unique(self, db: Session) -> None:
        make_user(db, email="taken@example.com")

        db.add(User(email="taken@example.com", username="somebody", hashed_password="x"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_username_is_unique(self, db: Session) -> None:
        make_user(db, username="taken")

        db.add(User(email="other@example.com", username="taken", hashed_password="x"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_is_active_defaults_to_true(self, db: Session) -> None:
        user = make_user(db)

        assert user.is_active is True

    def test_timestamps_are_set_by_the_database(self, db: Session) -> None:
        # Not asserting that updated_at later advances: in Postgres now() is
        # the transaction's start time, and every test runs in one transaction,
        # so within a test the two are equal by construction.
        user = make_user(db)

        assert user.created_at is not None
        assert user.updated_at is not None


class TestGame:
    def test_rawg_id_is_unique(self, db: Session) -> None:
        make_game(db, rawg_id=4200)

        db.add(Game(rawg_id=4200, slug="different-slug", name="Different"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_slug_is_unique(self, db: Session) -> None:
        make_game(db, slug="half-life")

        db.add(Game(rawg_id=999_001, slug="half-life", name="Half-Life Again"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_facets_default_to_empty_lists(self, db: Session) -> None:
        game = make_game(db)

        assert game.genres == []
        assert game.platforms == []
        assert game.developers == []

    def test_jsonb_facets_round_trip(self, db: Session) -> None:
        genres = [{"id": 4, "name": "Action"}, {"id": 51, "name": "Indie"}]
        game = make_game(db, genres=genres)

        db.expire(game)
        assert game.genres == genres


class TestShelfEntry:
    def test_status_defaults_to_want_to_play(self, db: Session) -> None:
        entry = make_shelf_entry(db)

        assert entry.status is ShelfStatus.WANT_TO_PLAY

    def test_a_user_can_shelve_a_game_only_once(self, db: Session) -> None:
        user = make_user(db)
        game = make_game(db)
        make_shelf_entry(db, user_id=user.id, game_id=game.id)

        db.add(ShelfEntry(user_id=user.id, game_id=game.id, status=ShelfStatus.PLAYING))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_the_same_game_can_be_on_two_shelves(self, db: Session) -> None:
        game = make_game(db)
        make_shelf_entry(db, user_id=make_user(db).id, game_id=game.id)
        make_shelf_entry(db, user_id=make_user(db).id, game_id=game.id)

        assert _count(db, ShelfEntry) == 2

    def test_hours_played_cannot_be_negative(self, db: Session) -> None:
        db.add(
            ShelfEntry(
                user_id=make_user(db).id,
                game_id=make_game(db).id,
                hours_played=-1,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_deleting_a_user_removes_their_shelf(self, db: Session) -> None:
        user = make_user(db)
        make_shelf_entry(db, user_id=user.id)

        db.delete(user)
        db.commit()

        assert _count(db, ShelfEntry) == 0

    def test_deleting_a_game_removes_it_from_shelves(self, db: Session) -> None:
        game = make_game(db)
        make_shelf_entry(db, game_id=game.id)

        db.delete(game)
        db.commit()

        assert _count(db, ShelfEntry) == 0


class TestReview:
    def test_a_user_can_review_a_game_only_once(self, db: Session) -> None:
        user = make_user(db)
        game = make_game(db)
        make_review(db, user_id=user.id, game_id=game.id)

        db.add(Review(user_id=user.id, game_id=game.id, rating=3))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    @pytest.mark.parametrize("rating", [0, 11, -1])
    def test_rating_outside_one_to_ten_is_rejected(self, db: Session, rating: int) -> None:
        db.add(
            Review(
                user_id=make_user(db).id,
                game_id=make_game(db).id,
                rating=rating,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    @pytest.mark.parametrize("rating", [1, 5, 10])
    def test_rating_at_the_bounds_is_accepted(self, db: Session, rating: int) -> None:
        review = make_review(db, rating=rating)

        assert review.rating == rating

    def test_contains_spoilers_defaults_to_false(self, db: Session) -> None:
        review = make_review(db)

        assert review.contains_spoilers is False

    def test_deleting_a_user_removes_their_reviews(self, db: Session) -> None:
        user = make_user(db)
        make_review(db, user_id=user.id)

        db.delete(user)
        db.commit()

        assert _count(db, Review) == 0
