
CREATE TABLE users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Groups/tabs to organize the habits
CREATE TABLE habit_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0,   
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE habits (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id              INTEGER REFERENCES habit_groups(id) ON DELETE SET NULL,
    name                  TEXT NOT NULL,
    frequency             TEXT NOT NULL DEFAULT 'daily',   
    weekdays_mask         INTEGER,                         
    target_count_per_day  INTEGER NOT NULL DEFAULT 1,      
    archived              INTEGER NOT NULL DEFAULT 0,
    created_at            TEXT NOT NULL DEFAULT (date('now'))
);

-- One row per habit per day. "count" accumulates how many times the
-- habit was logged that day; the day counts as done once
-- count >= habits.target_count_per_day. This replaces a plain boolean
-- so habits like "read twice a day" are representable without a second
-- table or a variable number of rows per day.
CREATE TABLE checkins (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id    INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    date        TEXT NOT NULL,          -- YYYY-MM-DD
    count       INTEGER NOT NULL DEFAULT 0,
    note        TEXT,
    UNIQUE(habit_id, date)
);

CREATE TABLE milestones (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id       INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    streak_length  INTEGER NOT NULL,
    item_unlocked  TEXT,
    achieved_on    TEXT NOT NULL,
    UNIQUE(habit_id, streak_length)
);

CREATE INDEX idx_habits_user       ON habits(user_id);
CREATE INDEX idx_habits_group      ON habits(group_id);
CREATE INDEX idx_habit_groups_user ON habit_groups(user_id);
CREATE INDEX idx_checkins_habit    ON checkins(habit_id);
