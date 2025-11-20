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

## API Endpoints & CURL Examples

All endpoints (except `/health`) require authentication via Supabase JWT token in the Authorization header.

### Authentication Header
```bash
# Set your JWT token as an environment variable for convenience
export JWT_TOKEN="your_supabase_jwt_token_here"
```

---

### Task Management

#### Create a Task
```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Complete the quarterly report presentation"
  }'
```

**Response (201 Created):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_description": "Complete the quarterly report presentation",
  "created_at": "2024-01-15T10:30:00Z",
  "last_worked_on": null,
  "status": "active"
}
```

#### List Tasks
```bash
# Get all active tasks (default)
curl -X GET "http://localhost:8000/api/tasks" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Get tasks with specific status
curl -X GET "http://localhost:8000/api/tasks?status=active&limit=10" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Available status values: active, completed, abandoned
```

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_description": "Complete the quarterly report presentation",
      "created_at": "2024-01-15T10:30:00Z",
      "last_worked_on": "2024-01-15T14:20:00Z",
      "status": "active"
    }
  ]
}
```

---

### Interventions

#### Create an Intervention Session
```bash
curl -X POST "http://localhost:8000/api/interventions" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "physical_sensation": "Tension in shoulders and jaw",
    "internal_narrative": "I feel overwhelmed and worried about meeting the deadline",
    "emotion_label": "anxiety"
  }'
```

**Response (201 Created):**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "ai_identified_pattern": "performance_anxiety_with_physical_tension",
  "technique_id": "breathing_and_grounding",
  "personalized_message": "I notice you're experiencing tension in your shoulders and worry about deadlines. Let's try a breathing technique to help you feel more grounded.",
  "intervention_duration_seconds": 180
}
```

#### Start an Intervention Session
```bash
curl -X POST "http://localhost:8000/api/interventions/123e4567-e89b-12d3-a456-426614174000/start" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "started_at": "2024-01-15T15:00:00Z"
  }'

# Or start immediately (started_at is optional)
curl -X POST "http://localhost:8000/api/interventions/123e4567-e89b-12d3-a456-426614174000/start" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response (200 OK):**
```json
{
  "success": true,
  "scheduled_checkin_at": "2024-01-15T15:15:00Z"
}
```

#### Update Check-in Time
```bash
curl -X PATCH "http://localhost:8000/api/interventions/123e4567-e89b-12d3-a456-426614174000/checkin-time" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "checkin_minutes": 30
  }'
```

**Response (200 OK):**
```json
{
  "scheduled_checkin_at": "2024-01-15T15:30:00Z"
}
```
*Note: `checkin_minutes` must be between 15 and 120.*

#### Get Intervention Details
```bash
curl -X GET "http://localhost:8000/api/interventions/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response (200 OK):**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "task": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_description": "Complete the quarterly report presentation"
  },
  "physical_sensation": "Tension in shoulders and jaw",
  "internal_narrative": "I feel overwhelmed and worried about meeting the deadline",
  "emotion_label": "anxiety",
  "technique_id": "breathing_and_grounding",
  "personalized_message": "I notice you're experiencing tension in your shoulders and worry about deadlines. Let's try a breathing technique to help you feel more grounded.",
  "created_at": "2024-01-15T14:30:00Z",
  "scheduled_checkin_at": "2024-01-15T15:00:00Z",
  "checkin": null
}
```

---

### Check-ins

#### Create a Check-in
```bash
curl -X POST "http://localhost:8000/api/checkins" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "outcome": "started_kept_going",
    "optional_notes": "The breathing exercise really helped calm my nerves",
    "emotion_after": "calm"
  }'
```

**Valid outcome values:**
- `started_kept_going` - Started the intervention and continued
- `started_stopped` - Started but stopped partway through
- `did_not_start` - Never started the intervention
- `still_working` - Still working on the intervention

**Response (201 Created):**
```json
{
  "checkin_id": "987fcdeb-51a2-43d1-9f4e-123456789abc",
  "created_at": "2024-01-15T15:30:00Z",
  "suggestion": "Great work completing the breathing exercise! Consider using this technique again when you notice similar physical tension."
}
```

---

### User Dashboard

#### Get Dashboard Data
```bash
curl -X GET "http://localhost:8000/api/user/dashboard" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response (200 OK):**
```json
{
  "active_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_description": "Complete the quarterly report presentation",
      "created_at": "2024-01-15T10:30:00Z",
      "status": "active",
      "last_worked_on": "2024-01-15T14:20:00Z"
    }
  ],
  "recent_sessions": [
    {
      "session_id": "123e4567-e89b-12d3-a456-426614174000",
      "task_description": "Complete the quarterly report presentation",
      "created_at": "2024-01-15T14:30:00Z",
      "technique_id": "breathing_and_grounding"
    }
  ],
  "pending_checkin": {
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "task_description": "Complete the quarterly report presentation",
    "scheduled_at": "2024-01-15T15:00:00Z"
  }
}
```

---

### AI Services

#### Get Emotion Label Suggestions
```bash
curl -X POST "http://localhost:8000/api/ai/emotion-labels" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Complete the quarterly report presentation",
    "physical_sensation": "Tension in shoulders and jaw",
    "internal_narrative": "I feel overwhelmed and worried about meeting the deadline"
  }'
```

**Response (200 OK):**
```json
{
  "emotion_options": [
    "anxiety",
    "overwhelm",
    "stress",
    "worry",
    "pressure"
  ]
}
```

---

### Health Check (No Authentication Required)
```bash
curl -X GET "http://localhost:8000/health"
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T15:30:00Z",
  "message": "API is running",
  "service": "nkt-easeme-api"
}
```

## Notes

- AI technique selection follows the 4 defined techniques and patterns with structured JSON, with safe fallbacks.
- Check-in default is 15 minutes; bounds 15–120 mins.
- Supabase RLS policies should be enabled to enforce user isolation.