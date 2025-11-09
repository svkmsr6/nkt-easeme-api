# EaseMe API (FastAPI + Supabase + OpenAI)

## Overview

Implements:
- Onboarding-to-intervention and check-in backend per APP_FLOW (emotion-first techniques)
- API contract per BACKEND_SPECS (auth, tasks, interventions, check-ins, dashboard, AI label suggestions)
- DB schema per Build Product (Supabase/Postgres with RLS)  

## Quick Start Guide

### 1. Environment Setup
```bash
cp .env.example .env
# Fill DATABASE_URL, SUPABASE_JWKS_URL, JWT_ISSUER, OPENAI_API_KEY
```

### Important: DATABASE_URL format for async SQLAlchemy

This project uses SQLAlchemy's asyncio engine. Your `DATABASE_URL` must use an async
Postgres driver (asyncpg) in order for the async engine to initialize correctly.

Example (recommended):

```env
# Use the asyncpg driver for SQLAlchemy asyncio
DATABASE_URL="postgresql+asyncpg://<user>:<password>@<host>:5432/<database>"
SUPABASE_JWKS_URL="https://<your-supabase-project>.supabase.co/auth/v1/.well-known/jwks.json"
JWT_ISSUER="https://<your-supabase-project>.supabase.co"
OPENAI_API_KEY="sk-..."
```

If you set `DATABASE_URL` to a plain `postgresql://...` the app will attempt to
rewrite it to use `+asyncpg` at runtime, but it's best to explicitly provide
the `+asyncpg` scheme so environments and deployment scripts are unambiguous.


### 2. Python Environment Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip for PEP 517 support
python -m pip install --upgrade pip

# Install project dependencies (in editable mode)
python -m pip install -e .

# Optional: If project has dev dependencies
python -m pip install -e ".[dev]"
```

If using Poetry (check pyproject.toml for [tool.poetry]):
```powershell
pip install --user poetry
poetry install
```

### 3. Database Initialization
```bash
psql "$DATABASE_URL" -f migrations/0001_init.sql
# (Optional) python -m app.db.init_db
```

### 3. Run the Application
```bash
uvicorn app.main:app --reload
```

## Authentication

Pass Supabase JWT in `Authorization: Bearer <token>` for all endpoints except `/health`.

## cURL (admin create user + sign-in)

Create a user (admin API) — replace `<PROJECT>` and `<SERVICE_ROLE_KEY>`:
```bash
curl -s -X POST "https://<PROJECT>.supabase.co/auth/v1/admin/users" \
	-H "Authorization: Bearer <SERVICE_ROLE_KEY>" \
	-H "Content-Type: application/json" \
	-d '{"email":"new@user.test","password":"P@ssw0rd!","email_confirm":true}'
```

Sign in to get an access token (JWT) — replace `<PROJECT>` and `<ANON_KEY>`:
```bash
curl -s -X POST "https://<PROJECT>.supabase.co/auth/v1/token" \
	-H "apikey: <ANON_KEY>" \
	-H "Content-Type: application/json" \
	-d '{"grant_type":"password","email":"new@user.test","password":"P@ssw0rd!"}'
```

Response contains `access_token` (the JWT).

## Endpoints

### Health Check
- `GET /health`

### Task Management
- `POST /api/tasks`
- `GET /api/tasks?status=active&limit=20`

### Interventions
- `POST /api/interventions`
- `POST /api/interventions/{session_id}/start`
- `PATCH /api/interventions/{session_id}/checkin-time`
- `GET /api/interventions/{session_id}`

### Check-ins
- `POST /api/checkins`

### User Dashboard
- `GET /api/user/dashboard`

### AI Emotion Labels
- `POST /api/ai/emotion-labels`

## Notes

- AI technique selection follows the 4 defined techniques and patterns with structured JSON, with safe fallbacks.
- Check-in default is 15 minutes; bounds 15–120 mins.
- Supabase RLS policies should be enabled to enforce user isolation.