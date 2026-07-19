# Phase 03 — FastAPI Backend

## Context
Phase 01 provides `database.py` (`get_db` dependency), `models.py`
(`Conversation`, `Message`), and `crud.py` (async CRUD functions). Phase 02
provides `nvidia_client.py` (`stream_chat_completion`,
`get_full_completion`). This phase wires it all together into a running
FastAPI app with a streaming chat endpoint and conversation management
endpoints.

## Task

1. **`backend/app/schemas.py`** — Pydantic v2 schemas:
   - `MessageOut`: `id`, `role`, `content`, `created_at` (from `Message`
     model, `model_config = ConfigDict(from_attributes=True)`)
   - `ConversationSummary`: `id`, `title`, `updated_at` (for sidebar list)
   - `ConversationDetail`: `ConversationSummary` fields + `messages:
     list[MessageOut]`
   - `ChatRequest`: `conversation_id: UUID | None` (None means create a new
     conversation), `message: str` (the new user message, min length 1)
   - `ConversationCreateResponse`: `id: UUID` (used when a new conversation
     is created as a side effect of the first chat message)

2. **`backend/app/routers/conversations.py`** — `APIRouter`:
   - `GET /conversations` → `list[ConversationSummary]`
   - `GET /conversations/{conversation_id}` → `ConversationDetail`, 404 if
     not found
   - `DELETE /conversations/{conversation_id}` → 204 on success, 404 if not
     found

3. **`backend/app/routers/chat.py`** — `APIRouter`:
   - `POST /chat`, accepting `ChatRequest`, returns a `StreamingResponse`
     with `media_type="text/event-stream"`.
   - Logic:
     1. If `conversation_id` is `None`, create a new conversation
        (`crud.create_conversation`) first. Send the new `conversation_id`
        as the *first* SSE event (e.g. `event: conversation_id\ndata:
        <uuid>\n\n`) so the frontend can pick it up before message
        streaming begins.
     2. Load the conversation's prior messages (if any) to build the
        `messages` list for NVIDIA (system prompt + prior turns + new user
        message). Define a simple default system prompt as a constant (or
        config value) — e.g. "You are a helpful assistant."
     3. Persist the new user message via `crud.add_message`.
     4. Stream from `nvidia_client.stream_chat_completion`, forwarding each
        chunk to the client as an SSE `data:` event immediately
        (`event: token\ndata: <chunk>\n\n`), while accumulating the full
        text.
     5. On stream completion, persist the full assistant response via
        `crud.add_message`, then send a final SSE event (e.g. `event:
        done\ndata: {}\n\n`).
     6. On any `NvidiaAPIError`/`NvidiaTimeoutError` mid-stream, send an
        `event: error\ndata: <message>\n\n` SSE event and close the stream
        gracefully — do not crash the connection, and do not persist a
        partial assistant message as if it were complete (persist what was
        received so far, but the frontend should be able to tell it was
        cut short — include a `truncated: true` marker in the error
        event's data, or a similar signal).

4. **`backend/app/main.py`**:
   - Create the `FastAPI()` app.
   - Add `CORSMiddleware` using `settings.cors_allowed_origins`.
   - Include both routers.
   - Add a `GET /health` endpoint returning `{"status": "ok"}` (used by
     Render health checks in Phase 05).
   - Wire up startup: nothing DB-migration-related here (Alembic handles
     that separately), just app initialization.

## Constraints
- Every DB-touching route must use `Depends(get_db)`, never open sessions
  manually.
- SSE event formatting must be consistent (`event:` + `data:` + blank line)
  so the frontend parser in Phase 04 has one format to handle.
- Do not add authentication in this phase — that's out of scope unless
  requested explicitly.
- Ask before proceeding if you want a different system prompt, a
  configurable one per-conversation, or any deviation from the SSE event
  names above (frontend code in Phase 04 will assume these exact event
  names: `conversation_id`, `token`, `done`, `error`).

## Deliverable
A running FastAPI app (`uvicorn app.main:app --reload`) where `POST /chat`
streams a real NVIDIA response end-to-end and correctly persists both user
and assistant messages, and where `/conversations` endpoints correctly
list, fetch, and delete conversations.
