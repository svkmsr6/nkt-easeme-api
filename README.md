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

### 2. Database Initialization
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