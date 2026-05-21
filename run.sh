#!/usr/bin/env bash
# LIFE OS AI — convenience runner for macOS / Linux.
# Usage:  ./run.sh
set -e

if [ ! -d ".venv" ]; then
  echo "▸ Creating virtualenv (.venv)…"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "▸ Installing dependencies…"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if [ ! -f "instance/life_os.db" ]; then
  echo "▸ First run detected — seeding demo data…"
  python seed_data.py
fi

echo "▸ Starting LIFE OS AI…  http://127.0.0.1:5000"
python run.py
