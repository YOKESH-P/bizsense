# BizSense

BizSense is a full-stack AI Business Intelligence platform.

- **Backend:** FastAPI + SQLAlchemy + JWT auth + LangGraph agents
- **Frontend:** Single-page React app via CDN + Tailwind CSS
- **Database:** SQLite (configurable via `DATABASE_URL`)

## Features

- User signup and login with JWT authentication
- Protected business analysis endpoint
- Multi-agent analysis pipeline:
  - Orchestrator Agent
  - Research Agent (Tavily web search)
  - Analysis Agent (SWOT, competitors, market)
  - Report Agent (final report generation)
- Report history per user
- Fetch single report
- Delete report

## Analysis Report Sections

Every generated report includes:

- Executive Summary
- Market Overview
- Competitor Analysis
- SWOT Analysis
- Growth Opportunities
- Risks and Challenges
- Strategic Recommendations

## Project Structure

```text
bizsense/
  main.py
  database.py
  models.py
  auth.py
  agents.py
  graph.py
  requirements.txt
  .env
  frontend/
    index.html
```

## Prerequisites

- Python 3.10+
- Access to required third-party AI/search services configured via environment variables

## Environment Variables

Create a local `.env` file with the required runtime settings for your environment.
Keep all secrets private and do not commit real credentials to version control.

## Install and Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run backend:

```bash
uvicorn main:app --reload
```

Backend URL: `http://localhost:8000`

Open frontend:

- Open `frontend/index.html` in your browser  
  or
- Serve it from any static file server

## API Overview

### Auth

- `POST /auth/signup`
- `POST /auth/login`

### Protected

- `POST /analyze`
- `GET /reports`
- `GET /reports/{report_id}`
- `DELETE /reports/{report_id}`

Pass JWT in header:

```http
Authorization: Bearer <token>
```

## Example Requests

Signup:

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"founder@bizsense.ai","password":"securepass123","name":"Founder"}'
```

Login:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"founder@bizsense.ai","password":"securepass123"}'
```

Analyze:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"topic":"EV charging business in India"}'
```

Get reports:

```bash
curl http://localhost:8000/reports \
  -H "Authorization: Bearer <token>"
```

## Notes

- SQLite DB file (`bizsense.db`) is created automatically.
- CORS is enabled in FastAPI to allow frontend-backend communication.
- If API keys are missing/invalid, analysis endpoints will fail with an error.
