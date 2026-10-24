# CivicRoute AI — End-to-End Demo

A reliable, reproducible walkthrough covering resident submission, clarification,
AI triage, duplicate suggestions, staff approval, and resident tracking.

## 0. One-time setup

```bash
# Database
cd infra && docker compose up -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m app.seed                  # Boston + departments
python -m app.ingestion.cli --max 5000   # Boston 311 history (for analytics)
python -m app.demo                  # demo admin + sample complaints
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The demo seed prints tracking codes and creates a demo admin:

- **demo@civicroute.ai** / **demo-password-123**

> Provider note: by default the app uses the offline deterministic `fake` LLM and
> embedding providers, so the full demo runs with no API keys. To use a real
> model, set `LLM_PROVIDER`/`EMBEDDING_PROVIDER` and `LLM_API_KEY` in `backend/.env`
> (never commit keys), then restart the backend and run
> `python -m app.embeddings.reembed` to regenerate embeddings.

## 1. Resident submits a complaint

- Go to **http://localhost:3000/submit**.
- Submit a complaint (e.g. a pothole). You receive a **tracking code**.

## 2. Resident answers a clarification

- The demo includes a deliberately sparse complaint ("Something is wrong").
- As staff (see step 3) open it and click **Run AI triage**, or call the
  clarification generator; the resident then visits **/track**, enters the code,
  and answers the questions ("Where is it?", "More detail?").
- Answers are stored as resident-provided text — no locations are invented.

## 3. Staff sign in and triage

- Go to **/login**, sign in with the demo admin.
- Open **/staff**, pick a complaint, click **Run AI triage**.
- The AI produces a classification, priority (with rationale), and department
  recommendation with confidence scores. Nothing is applied to the complaint yet.

## 4. Duplicate suggestions

- On a pothole complaint, click **Find duplicates**.
- The near-duplicate pothole appears with a similarity score and evidence.
- Confirm or reject. Confirming records the link — complaints are **never merged
  automatically**.

## 5. Staff approve the AI recommendation

- Go to **/review**. The queue separates **high-risk / low-confidence** items
  from **routine** ones awaiting mandatory approval.
- Open a recommendation to inspect evidence and confidence, then **Approve** or
  **Override** (edit category/priority/department). Only now are the values
  applied to the complaint, and its status moves to *triaged*.

## 6. Resident tracks resolution

- Back on **/track**, the resident sees the updated status timeline.

## Evaluation (optional)

```bash
python -m app.eval.run     # labeled accuracy, calibration, latency, cost
```

Reports classification/priority/routing accuracy, confidence calibration (Brier
+ reliability bins), latency, and — with a real provider — token cost. With the
default `fake` provider the output is clearly labeled as NOT real-model accuracy.
