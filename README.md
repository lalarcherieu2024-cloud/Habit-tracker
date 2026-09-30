# Habit Buddy

A habit tracker with streak analytics. Individual Assignment 1.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Runs on `http://0.0.0.0:5001` by default. Override the port with the `PORT`
environment variable:

```bash
PORT=8080 python app.py
```

## Status

Step 1: bare Flask app, satisfies the §7 deployment contract (binds
`0.0.0.0`, reads `PORT` from env, no interactive setup). Accounts, habits,
and streaks land in the next steps — this README will grow with them,
including the coverage command once tests exist.
