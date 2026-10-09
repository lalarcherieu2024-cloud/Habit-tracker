"""
Domain — Authentication.

Handles user registration and login using Werkzeug's
password hashing (comes free with Flask, no extra dependency).
"""

from werkzeug.security import generate_password_hash, check_password_hash


def register_user(db, first_name, last_name, username, password):
    """Creates a new user and returns their id.

    Raises ValueError if any field is blank or the username is taken.
    """
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    username = (username or "").strip()

    if not first_name:
        raise ValueError("first name is required")
    if not last_name:
        raise ValueError("last name is required")
    if not username:
        raise ValueError("username is required")
    if not password or len(password) < 4:
        raise ValueError("password must be at least 4 characters")

    # Check if username already exists
    existing = db.execute(
        "SELECT 1 FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing:
        raise ValueError("username already taken")

    hashed = generate_password_hash(password)
    cur = db.execute(
        """INSERT INTO users (first_name, last_name, username, password_hash)
           VALUES (?, ?, ?, ?)""",
        (first_name, last_name, username, hashed),
    )
    db.commit()
    return cur.lastrowid


def authenticate_user(db, username, password):
    #Returns the user row if credentials are valid, otherwise None.
    username = (username or "").strip()   # same trimming as register_user
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if user is None:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def get_user_by_id(db, user_id):
    #Returns the user row or None.
    return db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
