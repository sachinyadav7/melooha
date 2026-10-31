# Melooha: Show Your Work

Free interactive birth chart in the app, plus answers that link to the chart facts they use.
Backend: FastAPI (Python). Frontend: Next.js. Database: Postgres.

## Run everything with one command

1. Install Docker Desktop.
2. Copy the env file: `cp .env.example .env` (add your Gemini and Groq keys later).
3. Start the project:

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (API docs at /docs)

## Run the tests

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

Tests also run on every push through GitHub Actions (`.github/workflows/ci.yml`).

## Project layout

- `backend/`: FastAPI app and tests
- `frontend/`: Next.js app
- `docker-compose.yml`: starts Postgres, backend and frontend

## Notes

- Reused code from earlier projects: none yet (update this if that changes).
