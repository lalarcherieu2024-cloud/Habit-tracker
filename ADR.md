# Architecture Decision Records

## 1. Backend Language & Framework Choice
Date: 2026-09-30
Status: Decided
Context: I needed a web framework that could serve pages, store data in SQLite, and run as one process. My app does two things — managing habits/check-ins and calculating streaks — and neither needs anything fancy like real-time updates.
Decision: I went with Flask, Jinja2 templates, and plain SQL using Python's built-in `sqlite3` module. No ORM.
Alternatives considered: **Django** — it comes with an ORM, admin panel, and migrations, but I only have five tables and no admin page. Most of Django would sit there unused, and the assignment actually penalizes picking it when Flask does the job. **FastAPI** — great for building JSON APIs, but my app serves HTML pages, not data to a JavaScript frontend. The async stuff it offers doesn't help when every request just reads or writes SQLite.
Consequences: I have to write all the SQL myself, turn on foreign keys with `PRAGMA foreign_keys = ON`, and set up `row_factory` by hand. But in return I can see exactly what every query does. Flask keeps things small — few dependencies, few files, easy to walk through and explain.

## 2. Keeping the Two Domains Separate
Date: 2026-10-01
Status: Decided
Context: The app has two domains — Habits & Check-ins (creating, listing, and logging habits) and Streaks & Insights (calculating streaks and awarding milestones). I wanted to keep them loosely connected so they could become separate services later without rewriting everything.
Decision: Each domain has its own folder and its own `service.py`. The habits service does all the creating, listing, archiving, and logging. When the streaks service needs check-in data, it gets it through `checkins_by_date()`, which just returns a dictionary like `{"2026-10-07": 2}`. The streak functions — `current_streak`, `longest_streak`, `completion_rate` — only do math on that dictionary. They never open the database. The only streaks function that touches the database is `check_and_award_milestones`, and it only writes to the `milestones` table, which belongs to the streaks domain.
Alternatives considered: **Putting everything in one service file** — quicker to set up, but then both domains are mixed together and pulling them apart later means rewriting a lot of code. **Having the streaks service query the checkins table directly** — it would work, but then both services depend on the same table layout. Going through `checkins_by_date()` means the streaks service just sees dates and counts, and doesn't care how check-ins are stored underneath.
Consequences: If these ever become microservices, the only thing that changes is `checkins_by_date()` — it turns into an API call instead of a database query, and all the streak math stays exactly the same. The downside is a bit more setup (two folders, two files), but each domain can be tested on its own and is easy to follow.

## 3. Data Model: Count-Based Check-ins and Per-Habit Milestones
Date: 2026-10-01
Status: Decided
Context: Some habits need more than one completion per day (like "drink 8 glasses of water"), and the app needs to track streaks and give out milestone badges. The schema had to handle both of those.
Decision: The `checkins` table has one row per habit per day, with a `count` column instead of a simple yes/no. A day counts as done when `count >= target_count_per_day`. The `milestones` table links to `habit_id` (not directly to `user_id`), and has a `UNIQUE(habit_id, streak_length)` constraint so each habit can only earn each milestone once. To get all milestones for a user, I join through the `habits` table.
Alternatives considered: **A boolean column for check-ins** — simpler, but then "read twice a day" doesn't work unless you add extra rows or another table. One row with a count handles it cleanly — one `SELECT` gives you everything the streak calculator needs. **Putting `user_id` directly on milestones** — would make the "show all milestones" query simpler, but it repeats ownership info that already lives on the habit. With `ON DELETE CASCADE` on the foreign key, deleting a habit automatically cleans up its milestones too.
Consequences: `log_checkin` uses `ON CONFLICT ... DO UPDATE SET count = count + 1`, so you never get duplicate rows for the same habit on the same day. The streaks service can figure out everything just from the check-in counts. The trade-off is that `milestones_for_user` needs a JOIN through habits, but the indexes keep it fast.

## 4. Testing Approach
Date: 2026-10-10
Status: Decided
Context: I needed at least 70% test coverage on the core logic, measured with pytest-cov. I had to decide what to test properly, what to test lightly, and what to skip.
Decision: I test the service functions directly — `habits/service.py`, `streaks/service.py`, and `auth/service.py`. Each test file creates a temporary in-memory SQLite database, loads the real schema, inserts a test user, and then calls the service functions. No HTTP requests, no Flask test client. Helper functions like `_log_n_days` keep the tests short and readable.
Alternatives considered: **Testing through Flask routes** — that would also cover the routing and session handling, but most of the real logic lives in the service functions, not the routes. Route tests are slower, break more easily when you change a template, and don't tell you much about whether the business logic is correct. **Mocking the database** — faster, but then you miss real SQL bugs like a wrong column name or a missing foreign key. Using in-memory SQLite with the real schema catches those because the tests run the exact same SQL the app runs.
Consequences: The three service files have 100% coverage, which is where all the graded logic lives. The routes and templates aren't tested automatically, so I have to check those by hand — but template bugs are easy to spot in the browser. The trade-off works: the assignment grades "core business logic" coverage, and that all lives in the service layer.
