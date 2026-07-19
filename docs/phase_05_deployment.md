# Phase 05 — Deployment

## Context
Phases 00–04 produced a working backend (FastAPI + async SQLAlchemy +
Postgres + NVIDIA streaming) and a working static frontend (vanilla
HTML/CSS/JS), both running and tested locally. This phase deploys the
backend to Render and the frontend to GitHub Pages, and wires them together.

## Task

### Backend → Render

1. **`backend/Dockerfile`**:
   - Base on `python:3.12-slim`.
   - Copy `requirements.txt`, install deps.
   - Copy the rest of `backend/`.
   - Run Alembic migrations then start uvicorn on container start — use a
     small entrypoint script (`backend/entrypoint.sh`) that runs `alembic
     upgrade head` before `exec uvicorn app.main:app --host 0.0.0.0 --port
     $PORT` (Render injects `$PORT`).
   - Ensure the entrypoint script is executable and set as the container
     `CMD`.

2. **Render setup instructions** (write as clear README steps, since actual
   dashboard clicks can't be scripted):
   - Create a new Web Service on Render, connect the GitHub repo, set root
     directory to `backend/`, runtime Docker.
   - Add environment variables matching `.env.example`
     (`NVIDIA_API_KEY`, `NVIDIA_API_BASE_URL`, `NVIDIA_MODEL`,
     `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, etc.) — note `DATABASE_URL`
     should point to the Neon (or other) Postgres instance, and
     `CORS_ALLOWED_ORIGINS` must include the eventual GitHub Pages URL
     (`https://<username>.github.io`).
   - Set health check path to `/health`.
   - Note the free-tier cold-start behavior (spins down after 15 min
     idle, ~30s wake time) and where to mention this in the frontend UI
     (e.g. a small note near the input box, added as a nice-to-have).

### Frontend → GitHub Pages

3. **`.github/workflows/deploy.yml`**:
   - Trigger on push to `main` affecting `frontend/**`.
   - Use `actions/upload-pages-artifact` + `actions/deploy-pages` to deploy
     the contents of `frontend/` directly (no build step needed since it's
     plain HTML/JS).
   - Include the standard `permissions: pages: write, id-token: write` and
     `environment: github-pages` blocks required by the official GitHub
     Pages deploy action.

4. **Wire frontend to backend**:
   - Update `frontend/app.js`'s `API_BASE_URL` constant to the real Render
     service URL (e.g. `https://llm-chat-interface.onrender.com`).
   - Confirm CORS on the backend allows the exact GitHub Pages origin
     (scheme + host, no trailing slash).

5. **`README.md` update**: replace the placeholder "Setup" section from
   Phase 00 with real, complete instructions: local dev setup (backend +
   frontend), environment variables needed, how to deploy changes to each
   (push to `main` → Pages auto-deploys via Actions; Render auto-deploys
   on push if configured, or manual deploy steps if not).

## Constraints
- Do not commit real secrets anywhere — `.env` stays gitignored,
  Render/GitHub environment variables are the only place real values live.
- Ask before proceeding if you'd rather use a different Postgres provider
  than Neon, or if GitHub Pages should serve from a `docs/` folder instead
  of a separate `frontend/` directory + Action (both are valid; the Action
  approach was chosen here for a cleaner repo root).

## Deliverable
A live, working chat interface: frontend on GitHub Pages, backend on
Render, both talking to each other over HTTPS, with conversations
persisting correctly across page reloads.
