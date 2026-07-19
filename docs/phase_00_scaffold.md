# Phase 00 — Project Scaffold

## Context
Starting a new project: a web-based chat interface for an LLM, backed by
NVIDIA's hosted inference API. Backend is FastAPI + async SQLAlchemy +
Postgres, deployed to Render. Frontend is plain HTML/CSS/JS, deployed to
GitHub Pages. This phase only sets up structure and configuration — no
business logic yet.

## Task
Create the initial repo scaffold:

1. **Directory structure**:
```
llm-chat-interface/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── frontend/
│   └── .gitkeep
├── .gitignore
└── README.md
```

2. **`backend/app/config.py`** — a `pydantic-settings`-based `Settings` class
   loaded from environment variables (via a `.env` file locally). Include, at
   minimum:
   - `nvidia_api_key: str` (required, no default)
   - `nvidia_api_base_url: str` (default `"https://integrate.api.nvidia.com/v1"`)
   - `nvidia_model: str` (default to a placeholder like
     `"meta/llama-3.1-8b-instruct"` — will be finalized later, but must be a
     single config value, not hardcoded elsewhere)
   - `nvidia_temperature: float` (default `0.7`)
   - `nvidia_max_tokens: int` (default `1024`)
   - `nvidia_request_timeout_seconds: int` (default `60`)
   - `database_url: str` (required — async driver, e.g.
     `postgresql+asyncpg://...`)
   - `cors_allowed_origins: list[str]` (parsed from a comma-separated env
     var, default includes `http://localhost:8000` and
     `http://127.0.0.1:5500` for local dev)
   - `environment: str` (default `"development"`)
   Expose a single module-level `settings = Settings()` instance for import
   elsewhere.

3. **`backend/requirements.txt`** with pinned major versions for: `fastapi`,
   `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`,
   `httpx`, `pydantic`, `pydantic-settings`, `python-dotenv`.

4. **`backend/.env.example`** — documents every env var from `config.py`
   with placeholder values and a one-line comment each.

5. **`.gitignore`** (root) — standard Python + Node + editor ignores,
   plus `.env`, `__pycache__/`, `*.pyc`, `.venv/`.

6. **`README.md`** — project title, one-paragraph description, stack list,
   and a "Setup" section with placeholder instructions to be filled in as
   later phases add real setup steps.

## Constraints
- Do not write any FastAPI routes, DB models, or NVIDIA client code yet —
  that's later phases.
- `config.py` must fail loudly (raise on missing required env var) rather
  than silently defaulting `nvidia_api_key` or `database_url`.
- Ask before proceeding if you want to change the NVIDIA model default or
  any other default value.

## Deliverable
The full directory structure and files listed above, ready to `pip install
-r requirements.txt` and import `Settings` without errors (given a valid
`.env`).
