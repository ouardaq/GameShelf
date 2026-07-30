"""Shared test fixtures.

These tests run against a real PostgreSQL database rather than SQLite. The
models use JSONB and a native enum type, and every constraint worth testing --
the partial cascades, the CHECK bounds -- is enforced by Postgres. Substituting
SQLite would mean testing a schema the application never actually runs on.

The schema is built with `Base.metadata.create_all`, which is fast but says
nothing about whether the Alembic migrations produce the same thing. CI checks
that separately by running the migrations and asserting autogenerate finds no
drift.
"""

import os
from collections.abc import Generator

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

import app.models  # noqa: F401  -- registers every model on Base.metadata
from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app as fastapi_app


def _test_database_url() -> URL:
    """Where tests may create and drop tables.

    Defaults to the development database name with a `_test` suffix, which
    keeps local setup to zero steps. Set TEST_DATABASE_URL to override.
    """
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return make_url(explicit)
    url = make_url(settings.DATABASE_URL)
    return url.set(database=f"{url.database}_test")


def _ensure_database_exists(url: URL) -> None:
    """Create the test database if it is not there yet.

    CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT, and an
    identifier cannot be a bind parameter. The name comes from our own
    configuration rather than from any request, so interpolating it is safe.
    """
    maintenance = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with maintenance.connect() as connection:
            exists = connection.execute(
                sa.text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            ).scalar()
            if not exists:
                connection.execute(sa.text(f'CREATE DATABASE "{url.database}"'))
    finally:
        maintenance.dispose()


@pytest.fixture(scope="session")
def engine() -> Generator[Engine]:
    url = _test_database_url()

    # This fixture drops tables. Refuse to touch the database the application
    # is configured to use, however the URLs were arrived at.
    if url.database == make_url(settings.DATABASE_URL).database:
        pytest.fail(
            "TEST_DATABASE_URL points at the application database "
            f"({url.database!r}); refusing to run destructive tests against it."
        )

    _ensure_database_exists(url)
    engine = create_engine(url, pool_pre_ping=True)

    # A previous run that crashed mid-test can leave tables behind.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Generator[Session]:
    """A session whose writes never outlive the test.

    The session runs inside an outer transaction that is rolled back at the
    end. `join_transaction_mode="create_savepoint"` means code under test can
    call commit() for real -- constraints fire, triggers run -- while the
    outer rollback still discards everything.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient]:
    """An API client that shares the test's session, and so its rollback."""

    def override_get_db() -> Generator[Session]:
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.clear()
