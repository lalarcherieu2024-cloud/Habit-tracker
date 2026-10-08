# Architecture Decision Records

## 1. Backend Language & Framework Choice
Date: 2026-09-30
Status: Decided
Context: Habit Buddy has to show web pages and save data in SQLite, all in one program. Every request is a quick read or write, so nothing needs to happen in real time or in the background.
Decision: I use Flask with Jinja2 templates, and I write plain SQL with Python's built-in `sqlite3` module instead of using an ORM.
Alternatives considered: **Django**: it comes with a lot built in (ORM, admin panel, migrations), but my app only has five tables and no admin users, so most of it would go unused. **FastAPI**: good for JSON APIs and async code, but my pages are built on the server and each database call is short, so async doesn't help.
Consequences: I write every SQL query myself and set up the connection myself (`PRAGMA foreign_keys = ON`, `row_factory`), but in return I can see exactly what each query does. Flask is my only runtime dependency, so the app stays small and easy to explain.

## 2. Keeping the Two Domains Separate for a Future Service Split
Date: 2026-10-06
Status: Decided
Context: My two domains are Habits & Check-ins (habits, groups, daily check-ins) and Streaks & Insights (streaks, completion rate, milestones). They need to stay separate enough that I could turn them into two services later.
Decision: Each domain has its own folder and `service.py`. The habits service owns the `habit_groups`, `habits` and `checkins` tables, and the streaks service owns only `milestones`. The streak functions don't read the database: they get the check-ins as a `{date: count}` dictionary from `checkins_by_date()`, plus the habit's settings.
Alternatives considered: **One shared service file**: easier at the start, but the streak code would get mixed in with the habit code and be hard to pull apart later. **Letting streaks read the `checkins` table itself**: fewer arguments to pass, but then both domains would depend on the same table, and every streak test would need a database.
Consequences: If I split the app later, only `checkins_by_date()` needs to become an API call; the streak functions stay the same. One link is left: `milestones_for_user` joins `milestones` with `habits` to find a user's habits, and that would also need to change in a split.

## 3. Data Model: Count-Based Check-ins and Per-Habit Milestones
Date: 2026-10-06
Status: Decided
Context: Some habits have to be done more than once a day (like "drink 8 glasses of water"), and each habit can earn milestones for long streaks. The tables need to store both.
Decision: `checkins` keeps one row per habit per day with a `count`, and a day is done when `count >= target_count_per_day`. `milestones` is linked to `habit_id` (not `user_id`), and `UNIQUE(habit_id, streak_length)` makes sure a habit can only earn each milestone once.
Alternatives considered: **A yes/no `completed` column**: simpler, but it can't store "read twice a day" without extra rows or another table. **Putting `user_id` on `milestones`**: makes "show all my milestones" a simpler query, but the owner is already stored on the habit, and two copies could stop matching.
Consequences: `log_checkin` uses `ON CONFLICT ... DO UPDATE SET count = count + 1`, so logging twice adds to the same row, and deleting a habit also deletes its check-ins and milestones (`ON DELETE CASCADE`). The cost is that `milestones_for_user` needs a JOIN through `habits`, which is still fast because `UNIQUE(habit_id, streak_length)` creates an index on `habit_id`.
