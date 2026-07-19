# Phase 04 — Frontend (Vanilla HTML/CSS/JS)

## Context
Phase 03 exposes a running backend with:
- `POST /chat` — body `{"conversation_id": <uuid|null>, "message":
  <string>}`, response is `text/event-stream` with named events:
  - `event: conversation_id` — data is the UUID (only sent when a new
    conversation was created)
  - `event: token` — data is an incremental text chunk
  - `event: done` — data is `{}`, stream complete
  - `event: error` — data is an error message string (may include a
    truncation signal)
- `GET /conversations` — list of `{id, title, updated_at}`
- `GET /conversations/{id}` — full conversation with messages
- `DELETE /conversations/{id}`

This phase builds the static frontend: no build step, no framework,
deployable as-is to GitHub Pages.

## Task

1. **`frontend/index.html`**
   - Layout: left sidebar (conversation list + "New chat" button), main
     panel (message history + input box at bottom).
   - Link `style.css` and `app.js`.
   - Include `marked.js` via CDN (`<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>`)
     for rendering assistant markdown responses.

2. **`frontend/style.css`**
   - Clean, minimal chat UI: distinct styling for user vs. assistant
     messages (e.g. right/left alignment or background color difference),
     sticky input box, scrollable message area, sidebar with hover/active
     states on conversation items, responsive down to mobile width.

3. **`frontend/app.js`**
   - A `const API_BASE_URL = "http://localhost:8000";` at the top of the
     file, clearly commented as "update this after backend deploy in Phase
     05".
   - State: `currentConversationId` (nullable), in-memory message list for
     the active conversation.
   - `loadConversations()`: `fetch(API_BASE_URL + "/conversations")`,
     render into sidebar, clicking one calls `openConversation(id)`.
   - `openConversation(id)`: fetch full conversation, render its messages,
     set `currentConversationId`.
   - `newChat()`: clears the active view and sets
     `currentConversationId = null` (next sent message creates a new
     conversation server-side).
   - `sendMessage(text)`:
     - Immediately render the user's message in the UI (optimistic).
     - `POST` to `/chat` with `fetch`, using the request body described
       above.
     - Read the response body via `response.body.getReader()` +
       `TextDecoder`, manually parsing the SSE format (split on double
       newlines, parse `event:`/`data:` lines) since `EventSource` does
       not support POST bodies.
     - On `conversation_id` event: store it, refresh the sidebar (new
       conversation now exists).
     - On `token` event: append the chunk to a growing assistant message
       bubble in real time, re-rendering via `marked.parse()` as it grows
       (or append raw text during streaming and do a final markdown
       render on `done`, if that's simpler/less flicker-prone — pick the
       approach and note the tradeoff).
     - On `done` event: finalize the message, re-enable the input box.
     - On `error` event: show an inline error message in the chat (styled
       distinctly, e.g. red-tinted), re-enable the input box, do not lose
       the partial response already rendered.
   - `deleteConversation(id)`: confirm via a simple `confirm()` dialog,
     `DELETE` request, remove from sidebar, if it was the active
     conversation clear the main panel.
   - Disable the input box (and show a typing/streaming indicator) while a
     response is in flight; re-enable on `done` or `error`.

## Constraints
- No frameworks, no bundler, no `node_modules` — must run by opening
  `index.html` directly or via a simple static server.
- Escape/sanitize user input before rendering as HTML to avoid XSS (do not
  use `innerHTML` with raw user text — use `textContent` for user messages;
  for assistant markdown rendering via `marked.js`, note that `marked`
  output should be treated carefully — using it here is acceptable for a
  personal portfolio project, but mention this as a known simplification).
- Ask before proceeding if you want a different markdown renderer, a
  dark/light theme toggle, or any specific visual style direction beyond
  "clean and minimal."

## Deliverable
A fully working static frontend that, when pointed at the local backend
from Phase 03, can create conversations, send messages, see streamed
responses render live, switch between conversations, and delete them.
