"""
Domain B — Streaks & Insights.

Computes current streak, longest streak, and completion rate
from check-in history.  Persists milestone events (7/14/30-day)
to the milestones table.

Handles daily habits (every day counts) and custom habits (only certain weekdays count)

Note for self: 
fetchone() -> returns one habit or none 
fetchall() -> returns all habits as a list
"""
from datetime import date, timedelta

MILESTONE_DAYS = (7, 14, 30, 60, 100, 365)

#Mon=0 … Sun=6  
_WEEKDAY_BIT = {i: (1 << i) for i in range(7)}


def _is_scheduled(day, frequency, weekdays_mask):
    """True if this calendar day is one the habit is supposed to be done on."""
    if frequency == "daily" or not weekdays_mask:
        return True
    return bool(weekdays_mask & _WEEKDAY_BIT[day.weekday()])


def _sorted_completed_dates(db, habit_id, target):
    """Returns a sorted list of date objects where the habit met its daily target."""
    rows = db.execute(
        "SELECT date, count FROM checkins WHERE habit_id = ? AND count >= ?",
        (habit_id, target),
    ).fetchall()
    return sorted(date.fromisoformat(r["date"]) for r in rows)


def _get_habit_info(db, habit_id):
    """Fetch frequency, weekdays_mask, and created_at for a habit."""
    row = db.execute(
        "SELECT frequency, weekdays_mask, created_at FROM habits WHERE id = ?",
        (habit_id,),
    ).fetchone()
    return row


def current_streak(db, habit_id, target=1, as_of=None):
    """Consecutive *scheduled* days ending today (or as_of) where count >= target.

    Grace period: if today is scheduled but not yet completed, the streak
    is counted from yesterday so it doesn't drop to 0 every morning.
    """
    as_of = as_of or date.today()
    info = _get_habit_info(db, habit_id)
    frequency = info["frequency"] if info else "daily"
    mask = info["weekdays_mask"] if info else None

    day_set = set(_sorted_completed_dates(db, habit_id, target))
    if not day_set:
        return 0

    # Grace period: if as_of is scheduled but not done, start from yesterday
    check = as_of
    if _is_scheduled(check, frequency, mask) and check not in day_set:
        check -= timedelta(days=1)

    streak = 0
    while True:
        # Skip non-scheduled days (rest days aren't gaps)
        if not _is_scheduled(check, frequency, mask):
            check -= timedelta(days=1)
            continue
        if check in day_set:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


def longest_streak(db, habit_id, target=1):
    """Longest run of consecutive *scheduled* completed days ever recorded."""
    info = _get_habit_info(db, habit_id)
    frequency = info["frequency"] if info else "daily"
    mask = info["weekdays_mask"] if info else None

    days = _sorted_completed_dates(db, habit_id, target)
    if not days:
        return 0

    best = 1
    run = 1
    for i in range(1, len(days)):
        # Count non-scheduled days between the two completed days
        gap_has_scheduled = False
        d = days[i - 1] + timedelta(days=1)
        while d < days[i]:
            if _is_scheduled(d, frequency, mask):
                gap_has_scheduled = True
                break
            d += timedelta(days=1)

        if not gap_has_scheduled:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def completion_rate(db, habit_id, target=1, window_days=30, as_of=None):
    """Fraction of *scheduled* days in the window where count >= target (0.0–1.0).

    The window is clamped so it never extends before the habit's created_at
    date — new habits aren't penalised for days that didn't exist yet.
    """
    as_of = as_of or date.today()
    info = _get_habit_info(db, habit_id)
    frequency = info["frequency"] if info else "daily"
    mask = info["weekdays_mask"] if info else None

    start = as_of - timedelta(days=window_days - 1)

    # Clamp to the habit's creation date
    if info and info["created_at"]:
        created = date.fromisoformat(info["created_at"])
        if created > start:
            start = created

    # Count how many days in the window are actually scheduled
    scheduled = 0
    d = start
    while d <= as_of:
        if _is_scheduled(d, frequency, mask):
            scheduled += 1
        d += timedelta(days=1)

    if scheduled == 0:
        return 0.0

    rows = db.execute(
        """SELECT COUNT(*) AS hit FROM checkins
           WHERE habit_id = ? AND count >= ? AND date BETWEEN ? AND ?""",
        (habit_id, target, start.isoformat(), as_of.isoformat()),
    ).fetchone()
    return rows["hit"] / scheduled


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
