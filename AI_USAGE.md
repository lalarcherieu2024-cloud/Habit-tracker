# AI Usage

| Date/commit | Tool | Prompt | Disposition (Accepted/Modified/Rejected) | What changed & why (if modified) | In my own words, how this works |
|---|---|---|---|---|---|
| 2026-09-30 / a1190b1 | Claude Code | Help me create the project structure for a Flask habit tracker with streak counting, organised into separate folders for habits, streaks, and auth so each domain can become its own service later. | Accepted | n/a | `app.py` starts the Flask app. Each domain has its own folder (`habits`, `streaks`, `auth`), and `db` holds the SQLite code. `templates` and `static` hold the pages, and `tests` holds the pytest tests. |
| 2026-10-01 / uncommitted | Claude Code | Help me create the SQLite schema for a habit tracker with users, habit groups, habits, daily check-ins with a count column, milestones, and indexes on the main foreign keys (`habits.user_id`, `habits.group_id`, `habit_groups.user_id`, `checkins.habit_id`). | Accepted | n/a | `db/schema.sql` defines `users`, `habit_groups`, `habits`, `checkins` and `milestones`. `checkins` has one row per habit per day, with a `count` that goes up each time you log the habit. Four indexes (`idx_habits_user`, `idx_habits_group`, `idx_habit_groups_user`, `idx_checkins_habit`) speed up the lookups that the streak and habit queries hit most. `db.connect` turns on foreign keys, and `db.init_schema` runs the file only if the tables don't exist yet. |

## What I learned

**Project structure matters for future separation.**
Organising each feature domain into its own folder (`habits/`, `streaks/`, `auth/`) means the boundaries between them are visible in the file tree, not just in my head. When Assignment 2 asks me to split the monolith into services, each folder already maps roughly to one service. Flask blueprints make this work: each domain registers its own routes, and `app.py` just wires the blueprints together.

**SQLite needs explicit foreign-key enforcement.**
SQLite has foreign keys turned off by default for backwards-compatibility. My `db.connect` function runs `PRAGMA foreign_keys = ON` on every new connection so that, for example, a `checkin` can't reference a `habit_id` that doesn't exist. Without that pragma, the column is just a regular integer and the database won't stop bad data.

**Indexes on foreign keys aren't automatic in SQLite.**
Unlike some databases, SQLite doesn't create indexes on foreign-key columns by default. The four `CREATE INDEX` statements target the columns used most in `WHERE` and `JOIN` clauses — e.g. `idx_checkins_habit` on `checkins(habit_id)` so that looking up all check-ins for a single habit doesn't scan the whole table. Without them the app still works, but queries slow down as data grows.

**Schema initialisation should be idempotent.**
`db.init_schema` uses `CREATE TABLE IF NOT EXISTS` so running it twice doesn't crash or wipe data. This matters for the §7 deployment contract: the app has to start cleanly after clone → install → start with no manual migration step.

**Separating production and dev dependencies keeps the deployment lean.**
`requirements.txt` lists only what the app needs to run (Flask, etc.). `requirements-dev.txt` pulls that in with `-r requirements.txt` and adds `pytest` and `pytest-cov`. In production or a container, only the base file is installed — no test tooling, smaller image, fewer things that can break.
