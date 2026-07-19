# Phase 01 — Database Layer

## Context
Phase 00 created the repo scaffold with `backend/app/config.py` exposing a
`settings` object (including `settings.database_url`, an async Postgres
URL). This phase builds the persistence layer: SQLAlchemy models, async
session management, Alembic migrations, and CRUD helper functions. No API
routes yet — this is a self-contained data layer other phases will import.

## Task

1. **`backend/app/database.py`**
   - Create an async SQLAlchemy engine from `settings.database_url` using
     `create_async_engine`.
   - Create an async session factory (`async_sessionmaker`).
   - Provide an async generator `get_db()` suitable for FastAPI dependency
     injection (`yield`s a session, ensures close/rollback on error).
   - Provide a `Base` (via `DeclarativeBase`) for models to inherit from.

2. **`backend/app/models.py`** — SQLAlchemy models:
   - `Conversation`:
     - `id: UUID` (primary key, server-generated default)
     - `title: str` (nullable — filled in later phase by auto-titling)
     - `created_at: datetime` (server default now, timezone-aware)
     - `updated_at: datetime` (server default now, updated on message add)
     - relationship to `messages`, ordered by `created_at`, with
       `cascade="all, delete-orphan"` so deleting a conversation deletes its
       messages.
   - `Message`:
     - `id: UUID` (primary key, server-generated default)
     - `conversation_id: UUID` (foreign key to `Conversation.id`)
     - `role: str` (constrained to `"user"` or `"assistant"` — use a
       `CheckConstraint` or `Enum`)
     - `content: str` (`Text`, not `String`, since responses can be long)
     - `created_at: datetime` (server default now, timezone-aware)
     - `token_count: int | None` (nullable — populated later from NVIDIA
       usage data)

3. **Alembic setup**:
   - Initialize Alembic in `backend/alembic/` with an async-compatible
     `env.py` (using `run_sync` pattern for autogenerate against the async
     engine).
   - Configure `alembic.ini` / `env.py` to read `database_url` from
     `settings` rather than a hardcoded value.
   - Generate the initial migration creating both tables with correct
     types, constraints, and indexes (index on
     `Message.conversation_id`, index on `Conversation.updated_at` for
     sidebar sorting).

4. **`backend/app/crud.py`** — async CRUD functions, each taking an
   `AsyncSession` as first arg:
   - `create_conversation(db, title: str | None = None) -> Conversation`
   - `get_conversation(db, conversation_id: UUID) -> Conversation | None`
     (with messages eagerly loaded via `selectinload`)
   - `list_conversations(db) -> list[Conversation]` (ordered by
     `updated_at` desc, messages NOT eagerly loaded — sidebar only needs
     id/title/updated_at)
   - `delete_conversation(db, conversation_id: UUID) -> bool` (returns
     whether a row was deleted)
   - `add_message(db, conversation_id: UUID, role: str, content: str,
     token_count: int | None = None) -> Message` (also bumps the parent
     conversation's `updated_at`)
   - `update_conversation_title(db, conversation_id: UUID, title: str) ->
     Conversation | None`

   All functions must commit their own transaction and handle the
   not-found case by returning `None` (not raising), so calling routers can
   decide how to respond.

## Constraints
- Use UUID primary keys (`uuid.uuid4`), not auto-increment ints.
- All datetimes timezone-aware (`DateTime(timezone=True)`).
- No raw SQL strings — use SQLAlchemy Core/ORM constructs throughout.
- Ask before proceeding if you want soft-delete instead of hard-delete for
  conversations, or any other schema deviation from the above.

## Deliverable
`database.py`, `models.py`, `crud.py`, a working Alembic setup with one
migration, and confirmation that `alembic upgrade head` runs cleanly against
a fresh Postgres database defined by `settings.database_url`.
