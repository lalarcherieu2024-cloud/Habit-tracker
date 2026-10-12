# Habit Buddy

A habit tracker built with Flask and SQLite that works on phones and laptops. Users create an account, define habits, and check them off daily. The app tracks streaks, completion rates, and awards milestones at 7/14/30/60/100/365-day streaks.

## Features

- **Habits & Check-ins** — create, group, archive, and log habits daily. Supports multi-count habits (e.g. "drink 8 glasses of water") and custom weekday schedules (e.g. Mon/Wed/Fri).
- **Streaks & Insights** — current streak, longest streak, and 30-day completion rate for each habit. Milestone badges at streak thresholds.
- **Accounts** — session-based login with password hashing (Werkzeug). Each user sees only their own habits.
- **Groups** — organise habits into named groups, filter the dashboard by group, and move a habit between groups.
- **Companion** — Chabal, a pixel-art cat made from a photo of my cat, reacts to today's progress.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/lalarcherieu2024-cloud/Habit-tracker.git
cd Habit-tracker

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Open [http://localhost:5001](http://localhost:5001) in your browser. Register a new account and start adding habits.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5001` (`8000` in the Docker image) | Port the app listens on |
| `DATA_DIR` | project root (`/data` in the Docker image) | Folder where `habits.db` is created (the folder is created if it doesn't exist) |
| `SECRET_KEY` | `dev-secret-change-in-production` | Flask session signing key |

All configuration is through environment variables — no `.env` file required.

```bash
# Example: custom port and data directory
PORT=8080 DATA_DIR=/tmp/habitdata python app.py
```

## Project Structure

```
habit-tracker/
├── app.py                  # Flask app, routes, config
├── db/
│   ├── __init__.py         # connect() and init_schema()
│   └── schema.sql          # SQLite tables and indexes
├── auth/
│   ├── __init__.py
│   └── service.py          # register, login, password hashing
├── habits/
│   ├── __init__.py
│   └── service.py          # CRUD for habits, groups, check-ins
├── streaks/
│   ├── __init__.py
│   └── service.py          # streak calculation, milestones
├── templates/
│   ├── base.html           # shared layout and CSS
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html      # today's progress, habits, the cat
│   └── new_habit.html      # the new-habit form
├── static/
│   ├── buddy-cat.js        # the pixel cat companion (a web component)
│   └── sprites/            # the cat's animation frames (PNG)
├── tests/
│   ├── test_auth.py
│   ├── test_habits.py
│   ├── test_streaks.py
│   ├── test_db.py
│   └── conftest.py         # shared in-memory database fixture
├── requirements.txt        # the one dependency manifest: Flask, plus pytest and pytest-cov for the tests
├── Dockerfile              # the course's container template, with its four TODOs filled in
├── ADR.md                  # architecture decision records
├── AI_USAGE.md             # AI usage log
└── README.md
```

## SQLite Storage

The database file is created at `DATA_DIR/habits.db`. Tables are created automatically on first startup — no migration step needed. The schema is in `db/schema.sql`.

Tables: `users`, `habit_groups`, `habits`, `checkins`, `milestones`.

Foreign keys are enforced via `PRAGMA foreign_keys = ON` on every connection.

## Testing

Tests cover the three service modules (habits, streaks, auth) and call the service functions directly — no Flask test client or HTTP calls. Habits, auth and milestone tests use an in-memory SQLite database with the real schema; the streak calculations are pure functions, so their tests pass plain `{date: count}` dictionaries.

```bash
# Run all tests with coverage
python -m pytest tests/ -v --cov=habits --cov=streaks --cov=auth --cov-report=term-missing
```

Coverage result:

```
Name                  Stmts   Miss  Cover
------------------------------------------
auth/service.py          30      0   100%
habits/service.py        67      0   100%
streaks/service.py       98      0   100%
------------------------------------------
TOTAL                   195      0   100%

71 passed
```

The 70% threshold (§4) is met. Routes and templates are not unit-tested — they are checked manually in the browser.

## Deployment Contract (§7)

- Single process: `python app.py`
- Binds to `0.0.0.0` (not localhost)
- Reads port from `PORT` env var, defaults to `5001`
- No interactive setup — starts cleanly after clone + install + run
- SQLite at `DATA_DIR/habits.db`
- No external database, cache, or queue
- Exactly one dependency manifest at the repo root (`requirements.txt`)
- Configurable entirely via environment variables
- No seed data: the app is useful with an empty database, so nothing is loaded on boot and a restart never changes row counts

### Docker

`Dockerfile` is the course template with its four `TODO`s filled in: `python:3.12-slim`, `pip install -r requirements.txt`, an explicit `COPY` of `app.py`, `db/`, `auth/`, `habits/`, `streaks/`, `templates/` and `static/` (no tests, `.venv` or local database), and `CMD ["python", "app.py"]`.

```bash
docker build -t habit-buddy .
docker run -p 8000:8000 -v habit-buddy-data:/data habit-buddy
```

### Contract check (`container/run.sh`)

Output of the course checker, run on 2026-10-12 with `PORT=8100 ./container/run.sh /path/to/habit-tracker` (port 8000 was busy on my machine with another app):

```
=== SDD Assignment 1 contract check ===
Repository: /Users/lunalarcher/habit-tracker

==> Repository shape
  PASS  one Dockerfile, one manifest (requirements.txt)

==> Build from a clean context, no build args
  PASS  image built
  PASS  image size 50 MB

==> Start on PORT=8100 and reach it from the host
  PASS  HTTP 302 from http://localhost:8100/

==> SQLite file under DATA_DIR
  PASS  found in /data: habits.db 

==> Data persists, and a second boot does not re-seed
  PASS  volume at /data persists
  PASS  row counts unchanged across restart: checkins=0 habit_groups=0 habits=0 milestones=0 users=0 

==> PORT override is honoured (not hardcoded)
  PASS  HTTP 302 from http://localhost:9123/

=== ALL CHECKS PASSED ===
Paste this output into your README as the §7 evidence.
```
