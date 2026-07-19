# NVIDIA-API Chat Interface

A web-based chat interface for an LLM, powered by NVIDIA's hosted inference
API. The backend is a FastAPI service that proxies streaming requests to the
NVIDIA API and persists conversation history to Postgres via async SQLAlchemy.
The frontend is plain HTML/CSS/JS — no build step required.

## Stack

- **Backend**: FastAPI · async SQLAlchemy · Alembic · Postgres (Neon) · httpx · Pydantic v2
- **Frontend**: HTML / CSS / JS · marked.js (CDN) for Markdown rendering
- **Backend hosting**: Render (Docker)
- **Frontend hosting**: GitHub Pages (via GitHub Actions)

---

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL (local or hosted, e.g. [Neon](https://neon.tech) free tier)

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# Copy .env.example → .env and fill in your values
cp .env.example .env
# Required: NVIDIA_API_KEY, DATABASE_URL

# Run database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

### Frontend

Open `frontend/index.html` in your browser, or use a local dev server like
VS Code Live Server (port 5500 is pre-configured in CORS).

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `NVIDIA_API_KEY` | ✅ | — | Your NVIDIA API key |
| `NVIDIA_API_BASE_URL` | | `https://integrate.api.nvidia.com/v1` | NVIDIA API endpoint |
| `NVIDIA_MODEL` | | `meta/llama-3.1-8b-instruct` | Model identifier |
| `NVIDIA_TEMPERATURE` | | `0.7` | Sampling temperature |
| `NVIDIA_MAX_TOKENS` | | `1024` | Max response tokens |
| `NVIDIA_REQUEST_TIMEOUT_SECONDS` | | `60` | Request timeout |
| `DATABASE_URL` | ✅ | — | Async Postgres URL (`postgresql+asyncpg://...`) |
| `CORS_ALLOWED_ORIGINS` | | `http://localhost:8000,http://127.0.0.1:5500` | Comma-separated origins |
| `ENVIRONMENT` | | `development` | `development` / `staging` / `production` |

---

## Deployment

### Backend → Render

1. Push the repo to GitHub.
2. Create a **Web Service** on [Render](https://render.com):
   - Connect your GitHub repo.
   - **Root directory**: `backend/`
   - **Runtime**: Docker
   - **Health check path**: `/health`
3. Add environment variables in Render dashboard:
   - `NVIDIA_API_KEY` — your real NVIDIA API key
   - `DATABASE_URL` — your Postgres connection string (e.g. from Neon).
     Use the `postgresql+asyncpg://` scheme.
   - `CORS_ALLOWED_ORIGINS` — include your GitHub Pages URL, e.g.
     `https://<username>.github.io`
   - `ENVIRONMENT` — set to `production`
   - Any other overrides from the table above.
4. Deploy. The container runs `alembic upgrade head` automatically on
   startup, then starts uvicorn.

> **Note**: On Render's free tier, the service spins down after 15 minutes
> of inactivity. The first request after idle takes ~30 seconds while the
> container wakes up.

### Frontend → GitHub Pages

1. In your GitHub repo settings → **Pages** → Source: **GitHub Actions**.
2. Push to `main` — the workflow at `.github/workflows/deploy.yml` triggers
   automatically when files in `frontend/` change.
3. Before deploying, update `API_BASE_URL` in `frontend/app.js` to your
   Render service URL (e.g. `https://your-service-name.onrender.com`).
4. The frontend will be live at `https://<username>.github.io/<repo-name>/`.

### Wiring them together

- Backend `CORS_ALLOWED_ORIGINS` must include the exact GitHub Pages origin
  (e.g. `https://dhruvgpt.github.io`) — no trailing slash.
- Frontend `API_BASE_URL` must point to the Render service URL — no trailing
  slash.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── config.py          # pydantic-settings configuration
│   │   ├── main.py            # FastAPI app, CORS, routers
│   │   ├── database.py        # Async engine, session factory, Base
│   │   ├── models.py          # Conversation & Message ORM models
│   │   ├── schemas.py         # Pydantic v2 request/response schemas
│   │   ├── crud.py            # Async CRUD helpers
│   │   ├── nvidia_client.py   # Streaming NVIDIA API client
│   │   └── routers/
│   │       ├── chat.py        # POST /chat (SSE streaming)
│   │       └── conversations.py  # Conversation CRUD endpoints
│   ├── alembic/               # Database migrations
│   ├── scripts/               # Manual test scripts
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── .github/workflows/deploy.yml
└── README.md
```

See `docs/00_index.md` for the full phased build plan.
