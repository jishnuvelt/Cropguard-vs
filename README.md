# CropGuard MVP (S0008)

CropGuard is an app-based solution for plant disease detection and expert support.
Farmers can upload crop photos and symptoms, receive AI triage instantly, and get
recommendations from agronomy experts when a case needs human review.

## Features

- Farmer case submission with image upload
- AI disease triage (disease, confidence, severity, next-step recommendation)
- Automatic escalation to experts when confidence is low or severity is high
- Expert dashboard for pending cases and treatment recommendations
- Follow-up updates for case progress tracking
- JSON APIs plus simple web UI

## Tech Stack

- FastAPI
- SQLite (SQLAlchemy ORM)
- Jinja2 templates (web UI)

## Project Structure

```text
app/
  ai_engine.py
  database.py
  main.py
  models.py
  schemas.py
  services.py
static/
  styles.css
templates/
  index.html
  farmer_dashboard.html
  expert_dashboard.html
uploads/
tests/
requirements.txt
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set OPENWEATHER_API_KEY=your_openweather_api_key
uvicorn app.main:app --reload
```

Open:

- App UI: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

## Default Demo Users

Created automatically on first run:

- Farmers: `Ramesh`, `Lakshmi`
- Experts: `Dr. Sharma`, `Dr. Iyer`

## Key API Endpoints

- `POST /api/farmers`
- `POST /api/experts`
- `POST /api/cases` (multipart form with image)
- `GET /api/farmers/{farmer_id}/cases`
- `GET /api/experts/{expert_id}/queue`
- `POST /api/cases/{case_id}/recommendations`
- `POST /api/cases/{case_id}/followups`
- `GET /api/weather/current?city=Chennai&units=metric`

## Real-Time Weather API (Step 2)

Use OpenWeatherMap current weather data through:

- `GET /api/weather/current?city=<city>&units=metric`

Example response includes:

- City and country
- Current temperature and feels-like temperature
- Humidity
- Weather condition summary

If `OPENWEATHER_API_KEY` is missing or invalid, the endpoint returns HTTP 400 with details.

## Notes

- The AI module is a deterministic heuristic engine for MVP demonstration.
- Replace `app/ai_engine.py` with a trained model endpoint for production.
