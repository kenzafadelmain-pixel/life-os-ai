@echo off
REM LIFE OS AI — convenience runner for Windows.
REM Usage:  run.bat

IF NOT EXIST .venv (
  echo Creating virtualenv (.venv)...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

IF NOT EXIST instance\life_os.db (
  echo First run detected - seeding demo data...
  python seed_data.py
)

echo Starting LIFE OS AI at http://127.0.0.1:5000
python run.py
