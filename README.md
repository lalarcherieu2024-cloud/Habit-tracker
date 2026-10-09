# Habit Buddy

A habit tracker with streak analytics. Individual Assignment 1.

You create habits (daily, or only on some weekdays, with a target like
"read twice a day"), log them each day, and see your current streak,
longest streak, 30-day completion rate and streak milestones.

## Setup

Tested with Python 3.13.

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5001` and register an account. The database
and its tables are created automatically on first start, so there is no
setup step.

## Configuration

Everything is set with environment variables. All of them are optional.

| Variable | Default | What it does |
| --- | --- | --- |
| `PORT` | `5001` | Port the app listens on (always on `0.0.0.0`) |
| `DATA_DIR` | the project folder | Folder for the SQLite file. Created if it doesn't exist |
| `SECRET_KEY` | a fixed development key | Signs the login cookie. Set your own outside development |

The database is always stored at **`$DATA_DIR/habits.db`**.

Example:

```bash
PORT=8080 DATA_DIR=./data SECRET_KEY=change-me python app.py
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest --cov=auth --cov=db --cov=habits --cov=streaks --cov-report=term-missing
```

Result (2026-10-09): **66 passed, 100% coverage**.

```
Name                  Stmts   Miss  Cover
-----------------------------------------
auth/service.py          30      0   100%
db/__init__.py           12      0   100%
habits/service.py        67      0   100%
streaks/service.py       82      0   100%
-----------------------------------------
TOTAL                   191      0   100%
```

## Project structure

| Path | What's in it |
| --- | --- |
| `app.py` | Starts Flask, opens the database, login/register/dashboard routes |
| `db/` | `schema.sql` (the tables) and `connect` / `init_schema` |
| `habits/` | Domain A, Habits & Check-ins: groups, habits, daily check-ins |
| `streaks/` | Domain B, Streaks & Insights: streaks, completion rate, milestones |
| `auth/` | Register and log in, with hashed passwords |
| `templates/` | The HTML pages (Jinja2) |
| `tests/` | pytest tests for each domain |

## Status

- Step 1: bare Flask app, satisfies the §7 deployment contract (binds
  `0.0.0.0`, reads `PORT` from env, no interactive setup).
- Step 2: database schema (`db/schema.sql`) and the habits service
  (`habits/service.py`): create, list and archive habits, and log or undo
  check-ins with a per-day target (e.g. "read twice a day").
- Step 3: streaks service (`streaks/service.py`): current and longest
  streak, completion rate, milestones. Rest days of custom habits don't
  break a streak, and today counts only once it's done.
- Step 4: accounts (`auth/service.py`) and the app wiring: `DATA_DIR`,
  one database connection per request, tables created at startup, and
  register / log in / log out pages.

Next: pages for habits, check-ins and streaks on the dashboard.
