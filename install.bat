@echo off
SETLOCAL
TITLE lbox setup
COLOR 0A

echo ==========================================
echo            lbox environment setup
echo ==========================================

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Python is not installed or not on PATH.
    pause
    exit /b 1
)

echo [+] Upgrading pip...
python -m pip install --upgrade pip

echo [+] Installing Python dependencies...
python -m pip install -r requirements.txt

echo [+] Installing Chromium for Playwright...
python -m playwright install chromium

echo [OK] Setup complete.
echo [OK] Run with: python main.py
pause
