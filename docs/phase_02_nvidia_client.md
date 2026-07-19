# Phase 02 — NVIDIA API Streaming Client

## Context
Phases 00–01 set up config (`backend/app/config.py`, with
`settings.nvidia_api_key`, `settings.nvidia_api_base_url`,
`settings.nvidia_model`, `settings.nvidia_temperature`,
`settings.nvidia_max_tokens`, `settings.nvidia_request_timeout_seconds`)
and the database layer. This phase builds a standalone async client for
calling NVIDIA's OpenAI-compatible `/chat/completions` endpoint with
streaming, isolated from any FastAPI/route code so it can be unit-tested
independently.

## Task

1. **`backend/app/nvidia_client.py`**
   - Define a custom exception `NvidiaAPIError(Exception)` carrying a
     status code and message, and a `NvidiaTimeoutError(NvidiaAPIError)`
     subclass for timeouts.
   - `async def stream_chat_completion(messages: list[dict[str, str]]) ->
     AsyncGenerator[str, None]`:
     - `messages` is a list of `{"role": ..., "content": ...}` dicts in
       OpenAI chat format.
     - Uses `httpx.AsyncClient` with `settings.nvidia_request_timeout_seconds`
       as timeout, posts to
       `f"{settings.nvidia_api_base_url}/chat/completions"` with
       `Authorization: Bearer {settings.nvidia_api_key}`, body including
       `model`, `messages`, `temperature`, `max_tokens`, `stream: true`.
     - Parses the SSE stream line-by-line (`data: {...}` chunks, terminated
       by `data: [DONE]`), yields only the incremental text content
       (`choices[0].delta.content`) as it arrives — skip empty deltas,
       skip non-content chunks (e.g. role-only first chunk) silently.
     - Malformed JSON in a chunk: log and skip that chunk, don't crash the
       whole stream.
   - `async def get_full_completion(messages: list[dict[str, str]]) -> str`:
     non-streaming convenience wrapper that consumes
     `stream_chat_completion` internally and returns the concatenated
     result (used later for auto-title generation, where streaming isn't
     needed).
   - Retry logic: wrap the initial connection (not mid-stream) in a retry
     with exponential backoff (e.g. 3 attempts, base delay 1s) for
     connection errors and 5xx responses. Do NOT retry on 4xx (bad
     request, auth failure) — raise `NvidiaAPIError` immediately with the
     response body included in the message.
   - On `httpx.TimeoutException`, raise `NvidiaTimeoutError` with a clear
     message.

2. **Token usage** (best-effort): if the final SSE chunk before `[DONE]`
   includes a `usage` field (NVIDIA/OpenAI-compatible APIs sometimes send
   this with `stream_options: {"include_usage": true}` — add that to the
   request body), capture and expose it. Add a way for
   `stream_chat_completion` callers to retrieve the last-seen usage after
   the generator is exhausted (e.g. an optional mutable dict passed in, or
   a small wrapper class holding `.usage` after streaming completes — pick
   one and note the choice).

3. A small standalone script `backend/scripts/test_nvidia_client.py` that
   sends one hardcoded test message and prints streamed chunks to stdout as
   they arrive, for manual verification against the real API before wiring
   it into FastAPI.

## Constraints
- No FastAPI imports in this file — this must be usable standalone.
- Never log or print the API key.
- Ask before proceeding if you want a specific retry count/backoff curve
  different from the above, or if you want usage tracking dropped entirely
  for now.

## Deliverable
`nvidia_client.py` with both functions working end-to-end against the real
NVIDIA API (verified via the test script), correct error handling for
auth failures, timeouts, and malformed responses.
