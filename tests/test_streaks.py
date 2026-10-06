"""Tests for Domain B — Streaks & Insights."""

import pytest
from datetime import date, timedelta
from db import connect, init_schema
from habits.service import create_habit, log_checkin
from streaks.service import (
    current_streak, longest_streak, completion_rate,
    check_and_award_milestones, milestones_for_habit, milestones_for_user,
)


@pytest.fixture
def db():
    """In-memory database with schema loaded and a test user inserted."""
    conn = connect(":memory:")
    init_schema(conn)
    conn.execute(
        "INSERT INTO users (id, first_name, last_name, username, password_hash) "
        "VALUES (1, 'Luna', 'Larcher', 'luna', 'x')"
    )
    conn.commit()
    return conn


def _log_n_days(db, user_id, habit_id, n, end_date=None):
    """Helper: log one check-in per day for n consecutive days ending on end_date."""
    end_date = end_date or date.today()
    for i in range(n):
        day = end_date - timedelta(days=n - 1 - i)
        log_checkin(db, user_id, habit_id, day.isoformat())


# ── Current streak ──────────────────────────────────────

class TestCurrentStreak:
    def test_no_checkins(self, db):
        hid = create_habit(db, 1, "Read")
        assert current_streak(db, hid, as_of=date(2026, 10, 6)) == 0

    def test_one_day(self, db):
        hid = create_habit(db, 1, "Read")
        log_checkin(db, 1, hid, "2026-10-06")
        assert current_streak(db, hid, as_of=date(2026, 10, 6)) == 1

    def test_consecutive_days(self, db):
        hid = create_habit(db, 1, "Read")
        _log_n_days(db, 1, hid, 5, date(2026, 10, 6))
        assert current_streak(db, hid, as_of=date(2026, 10, 6)) == 5

    def test_gap_breaks_streak(self, db):
        hid = create_habit(db, 1, "Read")
        log_checkin(db, 1, hid, "2026-10-03")
        # skip Oct 4
        log_checkin(db, 1, hid, "2026-10-05")
        log_checkin(db, 1, hid, "2026-10-06")
        assert current_streak(db, hid, as_of=date(2026, 10, 6)) == 2

    def test_target_count(self, db):
        hid = create_habit(db, 1, "Water", target_count_per_day=3)
        # Only log twice on Oct 6 — below target of 3
        log_checkin(db, 1, hid, "2026-10-06")
        log_checkin(db, 1, hid, "2026-10-06")
        assert current_streak(db, hid, target=3, as_of=date(2026, 10, 6)) == 0
        # Third log meets the target
        log_checkin(db, 1, hid, "2026-10-06")
        assert current_streak(db, hid, target=3, as_of=date(2026, 10, 6)) == 1


# ── Longest streak ──────────────────────────────────────

class TestLongestStreak:
    def test_no_checkins(self, db):
        hid = create_habit(db, 1, "Read")
        assert longest_streak(db, hid) == 0

    def test_single_day(self, db):
        hid = create_habit(db, 1, "Read")
        log_checkin(db, 1, hid, "2026-10-01")
        assert longest_streak(db, hid) == 1

    def test_past_streak_longer_than_current(self, db):
        hid = create_habit(db, 1, "Read")
        # 5-day streak in the past
        _log_n_days(db, 1, hid, 5, date(2026, 9, 30))
        # gap, then 2-day current streak
        log_checkin(db, 1, hid, "2026-10-05")
        log_checkin(db, 1, hid, "2026-10-06")
        assert longest_streak(db, hid) == 5
        assert current_streak(db, hid, as_of=date(2026, 10, 6)) == 2


# ── Completion rate ─────────────────────────────────────

class TestCompletionRate:
    def test_empty(self, db):
        hid = create_habit(db, 1, "Read")
        assert completion_rate(db, hid, as_of=date(2026, 10, 6)) == 0.0

    def test_perfect_week(self, db):
        hid = create_habit(db, 1, "Read")
        _log_n_days(db, 1, hid, 7, date(2026, 10, 6))
        rate = completion_rate(db, hid, window_days=7, as_of=date(2026, 10, 6))
        assert rate == pytest.approx(1.0)

    def test_half_window(self, db):
        hid = create_habit(db, 1, "Read")
        _log_n_days(db, 1, hid, 5, date(2026, 10, 6))
        rate = completion_rate(db, hid, window_days=10, as_of=date(2026, 10, 6))
        assert rate == pytest.approx(0.5)


# ── Milestones ──────────────────────────────────────────

class TestMilestones:
    def test_7_day_milestone(self, db):
        hid = create_habit(db, 1, "Read")
        _log_n_days(db, 1, hid, 7, date(2026, 10, 6))
        awarded = check_and_award_milestones(db, hid, as_of=date(2026, 10, 6))
        assert 7 in awarded

    def test_no_duplicate_milestone(self, db):
        hid = create_habit(db, 1, "Read")
        _log_n_days(db, 1, hid, 7, date(2026, 10, 6))
        check_and_award_milestones(db, hid, as_of=date(2026, 10, 6))
        # Calling again should not re-award
        second = check_and_award_milestones(db, hid, as_of=date(2026, 10, 6))
        assert second == []

    def test_multiple_milestones_at_once(self, db):
        hid = create_habit(db, 1, "Read")
        _log_n_days(db, 1, hid, 14, date(2026, 10, 6))
        awarded = check_and_award_milestones(db, hid, as_of=date(2026, 10, 6))
        assert 7 in awarded
        assert 14 in awarded

    def test_milestones_for_habit(self, db):
        hid = create_habit(db, 1, "Read")
        _log_n_days(db, 1, hid, 7, date(2026, 10, 6))
        check_and_award_milestones(db, hid, as_of=date(2026, 10, 6))
        ms = milestones_for_habit(db, hid)
        assert len(ms) == 1
        assert ms[0]["streak_length"] == 7

    def test_milestones_for_user(self, db):
        h1 = create_habit(db, 1, "Read")
        h2 = create_habit(db, 1, "Walk")
        _log_n_days(db, 1, h1, 7, date(2026, 10, 6))
        _log_n_days(db, 1, h2, 14, date(2026, 10, 6))
        check_and_award_milestones(db, h1, as_of=date(2026, 10, 6))
        check_and_award_milestones(db, h2, as_of=date(2026, 10, 6))
        ms = milestones_for_user(db, 1)
        assert len(ms) == 3  # 7 for h1, 7+14 for h2

    def test_streak_too_short_no_milestone(self, db):
        hid = create_habit(db, 1, "Read")
        _log_n_days(db, 1, hid, 5, date(2026, 10, 6))
        awarded = check_and_award_milestones(db, hid, as_of=date(2026, 10, 6))
        assert awarded == []
