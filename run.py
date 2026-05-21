"""
LIFE OS AI — Application Entry Point
====================================

Run the development server with:
    python run.py

In production, prefer a WSGI server (gunicorn, waitress) — for example:
    gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
"""
from app import create_app

# Build the application using the factory pattern. The factory itself takes
# care of creating runtime directories and initialising the SQLite schema, so
# a fresh clone "just works".
app = create_app()


if __name__ == "__main__":
    # 127.0.0.1 by default so the dev server isn't accidentally exposed.
    app.run(host="127.0.0.1", port=5000, debug=True)
