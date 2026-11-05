import db as database


def test_init_schema_is_safe_to_run_twice(db):
    database.init_schema(db)  # tables already exist: must not fail or wipe data
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2


def test_foreign_keys_are_enforced(db):
    db.execute("INSERT INTO habits (user_id, name) VALUES (1, 'Read')")
    db.execute("DELETE FROM users WHERE id = 1")
    assert db.execute("SELECT COUNT(*) FROM habits").fetchone()[0] == 0
