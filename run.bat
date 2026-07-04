@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
    echo [Dental Librarian] Creating virtual environment...
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py

pause
