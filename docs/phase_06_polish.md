# Phase 06 — Polish

## Context
The app is fully deployed and functional after Phase 05: streaming chat,
persisted conversations, frontend on GitHub Pages, backend on Render. This
phase adds the finishing touches that make it feel like a complete product
rather than a working prototype.

## Task

1. **Auto-generated conversation titles**
   - In `backend/app/routers/chat.py`, after the *first* assistant message
     in a conversation completes (i.e. the conversation had exactly one
     user + one assistant message after this turn), trigger a
     fire-and-forget title generation: call
     `nvidia_client.get_full_completion` with a short prompt built from the
     first user message (e.g. "Summarize the following message in 4 words
     or fewer, as a conversation title, no punctuation: {message}"), then
     `crud.update_conversation_title`.
   - This must not block or delay the SSE response to the user — run it
     after the main stream has finished and been persisted (e.g. as a
     background task via FastAPI's `BackgroundTasks`, not blocking the
     request/response cycle).
   - Frontend: after receiving the `done` event, if this was a new
     conversation, poll or re-fetch the conversation list once
     (short delay, e.g. 1–2s) to pick up the generated title; fall back to
     showing "New conversation" until then.

2. **Error states (frontend)**
   - Network failure (backend unreachable, e.g. cold-start timeout or
     Render down): show a clear inline message distinct from an NVIDIA API
     error, with a "Retry" affordance that resends the last message.
   - Empty backend response / malformed SSE: fail gracefully with a
     generic "Something went wrong, please try again" message rather than
     leaving the UI stuck in a loading state.

3. **Rate-limit handling (backend)**
   - If NVIDIA returns a 429, `nvidia_client.py` should raise a specific
     `NvidiaRateLimitError(NvidiaAPIError)` (subclass, carries `retry_after`
     if the header is present).
   - `chat.py`'s SSE error event should distinguish this case so the
     frontend can show "You're sending messages too quickly — try again in
     a moment" instead of a generic error.

4. **Empty states (frontend)**
   - No conversations yet: sidebar shows a friendly empty state instead of
     a blank list.
   - New/empty conversation selected: main panel shows a light prompt
     (e.g. "Ask me anything") instead of a blank area.

5. **Small UX details**
   - Auto-scroll the message panel to the bottom as new tokens stream in,
     but stop auto-scrolling if the user has manually scrolled up (don't
     yank their view while they're reading history).
   - Disable the send button (not just the input) while a response is
     streaming, to prevent duplicate submissions.
   - `Enter` sends the message, `Shift+Enter` inserts a newline in the
     input box.

## Constraints
- None of this should require schema changes beyond what Phase 01 already
  has (title generation just fills the existing nullable `title` column).
- Ask before proceeding if you want title generation to use a cheaper/
  different NVIDIA model than the main chat model (configurable separately
  in `config.py` as `nvidia_title_model`, defaulting to the same value as
  `nvidia_model` if not set).

## Deliverable
A polished, portfolio-ready chat app: sensible titles appear automatically,
errors are legible and recoverable, empty states don't look broken, and the
UI behaves the way people expect a chat app to behave.
