"""
Habit Buddy — main Flask application.

- Reads PORT and DATA_DIR from environment variables
- Opens one SQLite connection per request
- Pages are Jinja templates in templates/ (escaped automatically)
- Creates tables at startup if they don't exist
- Session-based login using Flask's built-in signed cookies
"""

import os
from functools import wraps

from flask import Flask, g, redirect, render_template, request, session, url_for

from db import connect, init_schema
from auth.service import register_user, authenticate_user, get_user_by_id


DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
os.makedirs(DATA_DIR, exist_ok=True)   # SQLite can't create missing folders
DB_PATH = os.path.join(DATA_DIR, "habits.db")

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
        return render_template("register.html", error=str(e))


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
        return render_template("login.html", error="Bad username or password")

    session["user_id"] = user["id"]
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    # Jinja escapes {{ user.first_name }}, so a name like <script> shows as text
    return render_template("dashboard.html", user=g.user)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
