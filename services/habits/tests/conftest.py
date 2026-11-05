import pytest

import db as database


@pytest.fixture
def db():
    conn = database.connect(":memory:")
    database.init_schema(conn)
    for username in ("alice", "bob"):
        conn.execute(
            """INSERT INTO users (first_name, last_name, username, password_hash)
               VALUES ('Test', 'User', ?, 'x')""",
            (username,),
        )
    conn.commit()
    yield conn
    conn.close()


ALICE, BOB = 1, 2
