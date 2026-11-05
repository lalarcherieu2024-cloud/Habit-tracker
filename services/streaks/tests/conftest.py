import pytest

import db as database


@pytest.fixture
def db():
    conn = database.connect(":memory:")
    database.init_schema(conn)
    yield conn
    conn.close()
