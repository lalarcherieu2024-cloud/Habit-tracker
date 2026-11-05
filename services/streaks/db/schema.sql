-- Streaks owns only milestones. habit_id and user_id come from the Habits
-- service, so there is no foreign key across the seam (ADR 6).
CREATE TABLE milestones (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    habit_id       INTEGER NOT NULL,
    streak_length  INTEGER NOT NULL,
    item_unlocked  TEXT,
    achieved_on    TEXT NOT NULL,
    UNIQUE(habit_id, streak_length)
);

CREATE INDEX idx_milestones_user ON milestones(user_id);
