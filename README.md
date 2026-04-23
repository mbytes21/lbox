# lbox

Minimal Playwright browser scaffold with environment-based configuration.

## What is included

- `main.py`: opens a browser session and optionally submits a login form if credentials are provided through environment variables
- `requirements.txt`: Python dependency list
- `.env.example`: example configuration values
- `install.bat`: Windows setup helper

## Quick start

1. Install Python 3.11 or newer.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

3. Copy `.env.example` to `.env` and fill in values if you want to test a login flow.
4. Run:

```powershell
python main.py
```

## Notes

- This project does not store credentials in source control.
- The script is intentionally generic and does not contain any automated submission or brute-force workflow.
