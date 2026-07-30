# GameShelf

![CI](https://github.com/ouardaq/GameShelf/actions/workflows/ci.yml/badge.svg)

Track the games you have played, are playing, and keep meaning to get around to.
Shelve a game, log hours and platform, and write a rating and review. Game data
comes from [RAWG](https://rawg.io/apidocs) and is mirrored locally, so browsing
your shelf does not depend on their API being up.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · Next.js · TypeScript · Tailwind

## Status

Early. Honest picture of what exists:

| Area | State |
| --- | --- |
| Data model, migrations | Done — users, games, shelf entries, reviews |
| Request/response schemas | Done |
| Health endpoints | Done |
| Test suite, CI | Done — 52 tests against real Postgres |
| Auth (register/login/JWT) | Not started — `app/core/security.py` is empty |
| Shelf, review, search endpoints | Not started — `app/api/` has no routers |
| RAWG client | Not started — `app/services/rawg.py` is empty |
| Frontend | Untouched `create-next-app` scaffold |

## Getting started

Requires Docker, Python 3.13+, and Node 20+.

```bash
git clone https://github.com/ouardaq/GameShelf.git
cd GameShelf
make install          # venv + dependencies + npm packages + backend/.env
make hooks            # ruff runs on staged files before each commit
make up               # Postgres and Redis in Docker
```

Then fill in `backend/.env`. It is created from `.env.example` with
placeholders, and the app deliberately refuses to start without a real
`SECRET_KEY` and `RAWG_API_KEY` rather than falling back to insecure defaults.
`DATABASE_URL` and `REDIS_URL` take the credentials from `docker-compose.yml`,
on host ports **5434** and **6380** — remapped so they cannot collide with a
Postgres or Redis installed directly on your machine.

```bash
make migrate          # create the schema
```

```bash
make dev              # API on http://localhost:8000  (docs at /docs)
make dev-web          # web on http://localhost:3000
```

Verify it is wired up:

```bash
curl localhost:8000/health/db
```

`/health` says the process is up; `/health/db` issues a real query, so a deploy
that cannot reach Postgres fails its check instead of looking healthy.

## Commands

`make help` lists everything. The ones you will use:

| Command | Does |
| --- | --- |
| `make check` | Everything CI runs — run this before pushing |
| `make hooks` | Install the pre-commit hooks |
| `make test` | Backend test suite |
| `make cov` | Tests with a coverage report |
| `make fmt` | Fix formatting and auto-fixable lint |
| `make migration m="..."` | Generate a migration from model changes |
| `make rollback` | Undo the last migration |

## Layout

```
backend/
  app/
    core/       settings, security primitives
    db/         engine, session, declarative base
    models/     SQLAlchemy models — the schema
    schemas/    Pydantic models — the API contract
    services/   business logic and outbound calls
    api/        routers
  alembic/      migrations
  tests/
frontend/       Next.js app router
```

Models and schemas are kept separate on purpose. Models describe what is stored;
schemas describe what crosses the wire. Because they are distinct types, a
request cannot set a server-owned field and a response cannot leak a private one
— `UserRead` and `UserPublic` have no `hashed_password` to expose, rather than
relying on someone remembering to strip it.

## Notable decisions

**Invariants live in the database.** A user can shelve or review a given game at
most once (unique constraints), ratings are 1–10 and hours played is
non-negative (CHECK constraints), and rows disappear with their user or game (ON
DELETE CASCADE). Application code validates too, for good error messages — but
the database is what makes the rules true. `passive_deletes=True` lets Postgres
perform the cascade in one statement instead of SQLAlchemy loading every child
row first.

**Tests run on PostgreSQL, not SQLite.** The models use JSONB and a native enum,
and every constraint above is enforced by Postgres. Testing against SQLite would
exercise a schema the application never actually runs on. Each test gets a
session inside a transaction that is rolled back afterwards, using
`join_transaction_mode="create_savepoint"` so code under test can commit for
real — constraints fire, defaults are applied by the database — without leaking
rows into the next test.

**Configuration comes from the environment.** `DATABASE_URL`, `SECRET_KEY` and
`RAWG_API_KEY` have no defaults, so a missing one is a startup failure rather
than a silent fallback. CI runs with no `.env` file at all, which keeps that
honest. Alembic reads the URL from settings rather than `alembic.ini`, so no
credentials are committed.

**Games are mirrored from RAWG.** Shelves reference local rows, so a RAWG outage
or rate limit does not take the app down with it. Genre, platform and developer
facets are stored as JSONB because they are read as opaque blobs and never
queried on.

**CI checks migrations three ways** — they apply, `alembic check` finds no drift
against the models, and they reverse cleanly. The drift check matters most:
editing a model without generating a migration works fine locally and breaks on
deploy, and nothing else catches it.

## Contributing

`make check` must pass. Work on a branch, keep commits scoped to one change, and
open a pull request — CI runs lint, the test suite, and the migration checks on
both backend and frontend.
