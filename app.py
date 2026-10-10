"""
Habit Buddy — main Flask application.

- Reads PORT and DATA_DIR from environment variables
- Opens one SQLite connection per request (stored on g)
- Creates tables at startup if they don't exist
- Session-based login using Flask's built-in signed cookies
- Pages are Jinja templates in templates/ (escaped automatically)
"""

import os
from datetime import date
from functools import wraps

from flask import (
    Flask, g, redirect, render_template, request, session, url_for, flash,
)

from db import connect, init_schema
from auth.service import register_user, authenticate_user, get_user_by_id
from habits.service import (
    create_group, list_groups, delete_group,
    create_habit, archive_habit, list_habits, get_owned_habit,
    log_checkin, undo_checkin, checkins_by_date,
)
from streaks.service import (
    is_scheduled, current_streak, longest_streak, completion_rate,
    check_and_award_milestones, milestones_for_user,
)

DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
os.makedirs(DATA_DIR, exist_ok=True)   # SQLite can't create missing folders
DB_PATH = os.path.join(DATA_DIR, "habits.db")

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")


def get_db():
    """Returns the database connection for this request, creating it if needed."""
    if "db" not in g:
        g.db = connect(DB_PATH)
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Closes the database connection when the request ends."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Create the tables once at startup (skipped if they already exist)
startup_conn = connect(DB_PATH)
init_schema(startup_conn)
startup_conn.close()


def login_required(f):
    """Only lets logged-in users through, and puts their row in g.user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")
        g.user = get_user_by_id(get_db(), user_id) if user_id else None
        if g.user is None:
            # Not logged in, or the account no longer exists (e.g. database reset)
            session.clear()
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    try:
        user_id = register_user(
            get_db(),
            request.form.get("first_name"),
            request.form.get("last_name"),
            request.form.get("username"),
            request.form.get("password"),
        )
        session["user_id"] = user_id
        return redirect(url_for("dashboard"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("register"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    user = authenticate_user(
        get_db(),
        request.form.get("username"),
        request.form.get("password"),
    )
    if user is None:
        flash("Bad username or password", "error")
        return redirect(url_for("login"))

    session["user_id"] = user["id"]
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def habit_stats(db, habit, today):
    """Everything the dashboard shows for one habit.

    This is where the two domains meet: the habits service gives us the
    check-ins as a {date: count} dict, and the streaks service does the maths.
    """
    checkins = checkins_by_date(db, habit["id"])
    target = habit["target_count_per_day"]
    frequency = habit["frequency"]
    mask = habit["weekdays_mask"]
    today_count = checkins.get(today.isoformat(), 0)

    if frequency == "custom":
        days = ", ".join(d for i, d in enumerate(WEEKDAYS) if mask & (1 << i))
    else:
        days = "Every day"

    return {
        "id": habit["id"],
        "name": habit["name"],
        "group_id": habit["group_id"],
        "days": days,
        "target": target,
        "today_count": today_count,
        "done": today_count >= target,
        "due_today": is_scheduled(today, frequency, mask),
        "streak": current_streak(checkins, target, frequency, mask, as_of=today),
        "best": longest_streak(checkins, target, frequency, mask),
        "rate": round(completion_rate(checkins, target, frequency, mask, as_of=today,
                                      created_on=habit["created_at"]) * 100),
    }


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user = g.user
    today = date.today()

    habit_data = [habit_stats(db, h, today) for h in list_habits(db, user["id"])]
    groups = list_groups(db, user["id"])
    group_names = {grp["id"]: grp["name"] for grp in groups}
    for h in habit_data:
        h["group_name"] = group_names.get(h["group_id"])

    # Today's progress only counts habits that are due today
    due = [h for h in habit_data if h["due_today"]]
    done_count = sum(1 for h in due if h["done"])

    # Milestones with the habit's name, newest first
    habit_names = {h["id"]: h["name"] for h in habit_data}
    milestones = [
        {"habit": habit_names.get(m["habit_id"], "Archived habit"),
         "days": m["streak_length"], "date": m["achieved_on"]}
        for m in milestones_for_user(db, user["id"])
    ]

    return render_template(
        "dashboard.html",
        user=user,
        habits=habit_data,
        groups=groups,
        milestones=milestones,
        done_count=done_count,
        total_count=len(due),
        today=today,
        weekdays=list(enumerate(WEEKDAYS)),
    )


@app.route("/habits/create", methods=["POST"])
@login_required
def habit_create():
    db = get_db()
    name = request.form.get("name", "").strip()
    if not name:
        flash("Habit name is required", "error")
        return redirect(url_for("dashboard"))

    group_id = request.form.get("group_id", "")
    group_id = int(group_id) if group_id.isdigit() else None

    target = request.form.get("target", "1")
    target = int(target) if target.isdigit() else 0   # 0 is rejected by create_habit

    # Checked weekday boxes (0 = Mon … 6 = Sun) become one bitmask, e.g. Mon+Wed+Fri = 21
    frequency = request.form.get("frequency", "daily")
    mask = None
    if frequency == "custom":
        days = {int(d) for d in request.form.getlist("weekdays") if d in "0123456"}
        mask = sum(1 << d for d in days)

    try:
        create_habit(db, g.user["id"], name, frequency=frequency, weekdays_mask=mask,
                     target_count_per_day=target, group_id=group_id)
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("dashboard"))


@app.route("/habits/<int:habit_id>/checkin", methods=["POST"])
@login_required
def habit_checkin(habit_id):
    db = get_db()
    try:
        log_checkin(db, g.user["id"], habit_id)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("dashboard"))

    # A check-in can push the streak over a milestone, so check right after logging
    habit = get_owned_habit(db, g.user["id"], habit_id)
    stats = habit_stats(db, habit, date.today())
    # Only on the log that completes the day, and not on rest days (they don't count for streaks)
    if stats["due_today"] and stats["today_count"] == stats["target"]:
        flash(f"{habit['name']} done for today! Streak: {stats['streak']}", "success")
    for days in check_and_award_milestones(db, habit_id, stats["streak"]):
        flash(f"Milestone! {days}-day streak on {habit['name']}", "success")
    return redirect(url_for("dashboard"))


@app.route("/habits/<int:habit_id>/undo", methods=["POST"])
@login_required
def habit_undo(habit_id):
    db = get_db()
    try:
        undo_checkin(db, g.user["id"], habit_id)
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("dashboard"))


@app.route("/habits/<int:habit_id>/archive", methods=["POST"])
@login_required
def habit_archive(habit_id):
    db = get_db()
    archive_habit(db, g.user["id"], habit_id)
    return redirect(url_for("dashboard"))


@app.route("/groups/create", methods=["POST"])
@login_required
def group_create():
    db = get_db()
    try:
        create_group(db, g.user["id"], request.form.get("name", ""))
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("dashboard"))


@app.route("/groups/<int:group_id>/delete", methods=["POST"])
@login_required
def group_delete(group_id):
    db = get_db()
    delete_group(db, g.user["id"], group_id)
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
