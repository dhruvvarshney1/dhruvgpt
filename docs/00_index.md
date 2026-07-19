# NVIDIA-API Chat Interface — Project Index

## Overview
A web-based chat interface for an LLM, using NVIDIA's hosted inference API for
responses. Frontend is static (plain HTML/CSS/JS, deployed to GitHub Pages).
Backend is a FastAPI service (deployed to Render) that proxies streaming
requests to the NVIDIA API and persists conversation history to Postgres via
async SQLAlchemy.

## Why a backend is required
GitHub Pages only serves static files. The NVIDIA API key cannot be embedded
in client-side JS (it would be exposed to anyone who opens devtools), and
async SQLAlchemy / Postgres persistence is inherently server-side. The backend
exists specifically to (a) hold the API key, (b) proxy + stream NVIDIA
responses over SSE, and (c) persist conversations.

## Stack
- **Backend**: FastAPI, async SQLAlchemy, Alembic, Postgres (Neon free tier),
  httpx (async streaming client), Pydantic v2
- **Frontend**: Plain HTML/CSS/JS, no build step, `fetch` + `ReadableStream`
  for SSE consumption, marked.js (CDN) for markdown rendering
- **Backend hosting**: Render (Docker-based web service)
- **Frontend hosting**: GitHub Pages, deployed via GitHub Actions

## Repo structure (target end-state)
```
llm-chat-interface/
├── backend/
│   ├── app/
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── nvidia_client.py
│   │   └── routers/
│   │       ├── chat.py
│   │       └── conversations.py
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── .github/workflows/deploy.yml
└── README.md
```

## Phases
| Phase | File | Covers |
|---|---|---|
| 00 | `phase_00_scaffold.md` | Repo structure, `config.py`, env handling, dependencies |
| 01 | `phase_01_database.md` | Async SQLAlchemy models, Alembic, CRUD helpers |
| 02 | `phase_02_nvidia_client.md` | Streaming NVIDIA API wrapper, retries, error handling |
| 03 | `phase_03_backend_api.md` | FastAPI app, `/chat` SSE endpoint, `/conversations` CRUD, CORS |
| 04 | `phase_04_frontend.md` | Vanilla JS chat UI, SSE consumption, sidebar, markdown rendering |
| 05 | `phase_05_deployment.md` | Dockerfile, Render deploy, GitHub Actions Pages deploy, env wiring |
| 06 | `phase_06_polish.md` | Auto-titles, error states, rate-limit handling, empty states |

## How to use these prompts
Feed each phase file to the agentic IDE sequentially, in order. Each phase
assumes all prior phases are complete and working. Each phase file is
self-contained: it restates the relevant context so it can be run as a fresh
prompt without needing the full conversation history.

## Global rules for every phase (apply throughout)
- No placeholder code, no `# TODO: implement this` — every function must be
  complete and runnable.
- All tunables (model name, timeouts, token limits, CORS origins, DB URL,
  etc.) live in `backend/app/config.py`, loaded from environment variables
  with sane defaults. Nothing hardcoded inline elsewhere.
- If any requirement in a phase is ambiguous, ask a clarifying question
  before writing code rather than guessing.
- Use type hints on all functions. Docstrings on all public functions.
- Async throughout the backend — no blocking calls in request handlers.
