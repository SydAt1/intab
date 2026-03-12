# FYP Project: Audio Tablature Studio

A FastAPI backend with a lightweight frontend for transcribing guitar audio into tablature and visualizing results. The project exposes a REST API and serves a small static UI.

## Quick Start

- Prerequisites
  - Python 3.13 or newer
- Install (choose one):
  - Using Poetry (recommended):
    - Install Poetry if you don’t have it
    - poetry install
  - Without Poetry (manual):
    - Create a virtual environment
      - python -m venv .venv
      - source .venv/bin/activate (or .venv\Scripts\activate on Windows)
    - Install dependencies from the pyproject.toml (or manually via pip if you prefer tightly pinned versions)

- Run the app
  - Uvicorn (development):
    - uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
  - The app also mounts static frontend assets from the frontend/web directory, so the UI will be available at the root URL.

- Access
  - API health: http://localhost:8000/api/health
  - Frontend UI: http://localhost:8000/

- Configuration
  - The app reads configuration from a .env file. See the repository for an example. Populate DB credentials and MinIO settings (MINIO_ENDPOINT, MINIO_BUCKET, etc.).
  - If you already have a running Postgres and MinIO instance, ensure the connection details match your environment.

- Tests
  - Run: pytest


## Project Structure
- frontend/
  - web/ contains the static HTML/CSS/JS assets for the UI
- src/
  - app.py: FastAPI app and API routers
  - main.py: small bootstrap (demo/test code)
  - api/: API route implementations (auth, upload, transcription, etc.)
  - fretboard/: visualization and utilities for guitar fretboard rendering
- test/ or test_*.py
- pyproject.toml: project metadata and dependencies (Python 3.13+)
- README.md: this file

Note: The app uses MinIO for object storage and a PostgreSQL database. See src/core/config.py for environment variable keys and defaults.

## Deployment notes
- For production, run behind a reverse proxy (e.g., Nginx) and consider using a process manager like Gunicorn with Uvicorn workers.
- Secure sensitive configuration; avoid committing .env files to version control.

## How to contribute
- Open issues for feature requests or bugs.
- Submit a pull request with a clear description of changes and rationale.

## License
- This project is a student project and license information should be added by the maintainers.
