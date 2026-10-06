"""
Domain B — Streaks & Insights.

Computes current streak, longest streak, and completion rate
from check-in history.  Persists milestone events (7/14/30-day)
to the milestones table.
"""

from datetime import date, timedelta

MILESTONE_DAYS = (7, 14, 30, 60, 100, 365)


def _sorted_completed_dates(db, habit_id, target):
    """Returns a sorted list of date objects where the habit met its daily target."""
    rows = db.execute(
        "SELECT date, count FROM checkins WHERE habit_id = ? AND count >= ?",
        (habit_id, target),
    ).fetchall()
    return sorted(date.fromisoformat(r["date"]) for r in rows)


def current_streak(db, habit_id, target=1, as_of=None):
    """Consecutive days ending today (or as_of) where count >= target."""
    as_of = as_of or date.today()
    days = _sorted_completed_dates(db, habit_id, target)
    if not days:
        return 0

    streak = 0
    check = as_of
    # Walk backwards from as_of; each day must be in the set
    day_set = set(days)
    while check in day_set:
        streak += 1
        check -= timedelta(days=1)
    return streak


def longest_streak(db, habit_id, target=1):
    """Longest run of consecutive completed days ever recorded."""
    days = _sorted_completed_dates(db, habit_id, target)
    if not days:
        return 0

    best = 1
    run = 1
    for i in range(1, len(days)):
        if days[i] - days[i - 1] == timedelta(days=1):
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def completion_rate(db, habit_id, target=1, window_days=30, as_of=None):
    """Fraction of the last `window_days` days where count >= target (0.0–1.0)."""
    as_of = as_of or date.today()
    start = as_of - timedelta(days=window_days - 1)
    rows = db.execute(
        """SELECT COUNT(*) AS hit FROM checkins
           WHERE habit_id = ? AND count >= ? AND date BETWEEN ? AND ?""",
        (habit_id, target, start.isoformat(), as_of.isoformat()),
    ).fetchone()
    return rows["hit"] / window_days


def check_and_award_milestones(db, habit_id, target=1, as_of=None):
    """Awards any new milestones the user just earned.  Returns a list of new day-counts."""
    as_of = as_of or date.today()
    streak = current_streak(db, habit_id, target, as_of)
    awarded = []

    for threshold in MILESTONE_DAYS:
        if streak < threshold:
            break  # sorted ascending, no point checking further

        already = db.execute(
            "SELECT 1 FROM milestones WHERE habit_id = ? AND streak_length = ?",
            (habit_id, threshold),
        ).fetchone()

        if not already:
            db.execute(
                """INSERT INTO milestones (habit_id, streak_length, achieved_on)
                   VALUES (?, ?, ?)""",
                (habit_id, threshold, as_of.isoformat()),
            )
            awarded.append(threshold)

    if awarded:
        db.commit()
    return awarded


def milestones_for_habit(db, habit_id):
    """All milestones earned for one habit, oldest first."""
    return db.execute(
        "SELECT * FROM milestones WHERE habit_id = ? ORDER BY achieved_on",
        (habit_id,),
    ).fetchall()


def milestones_for_user(db, user_id):
    """All milestones across all of a user's habits, newest first."""
    return db.execute(
        """SELECT m.* FROM milestones m
           JOIN habits h ON h.id = m.habit_id
           WHERE h.user_id = ?
           ORDER BY m.achieved_on DESC""",
        (user_id,),
    ).fetchall()
