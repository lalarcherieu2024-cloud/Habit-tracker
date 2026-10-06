# Habit Buddy

A habit tracker with streak analytics. Individual Assignment 1.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Runs on `http://0.0.0.0:5001` by default. Override the port with the `PORT`
environment variable:

```bash
PORT=8080 python app.py
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest --cov=db --cov=habits --cov-report=term-missing
```

## Status

- Step 1: bare Flask app, satisfies the §7 deployment contract (binds
  `0.0.0.0`, reads `PORT` from env, no interactive setup).
- Step 2: database schema (`db/schema.sql`) and the habits service
  (`habits/service.py`): create, list and archive habits, and log or undo
  check-ins with a per-day target (e.g. "read twice a day"). Not wired to
  any page yet.

Streaks, accounts and the dashboard land in the next steps.
