import os
import subprocess
import sys
from typing import Optional


DEFAULT_URL = "https://example.com/"
DEFAULT_WAIT_MS = 30000


def sync_playwright_env() -> None:
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    except subprocess.CalledProcessError:
        print("[setup] Unable to install Chromium automatically.")


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"[config] Invalid integer for {name}: {raw!r}. Using {default}.")
        return default


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def maybe_fill(locator, value: Optional[str]) -> None:
    if value:
        locator.fill(value)


def run_browser_session() -> None:
    sync_playwright_env()
    from playwright.sync_api import TimeoutError, sync_playwright

    start_url = os.getenv("LBOX_START_URL", DEFAULT_URL).strip() or DEFAULT_URL
    username = os.getenv("LBOX_USERNAME", "").strip()
    password = os.getenv("LBOX_PASSWORD", "").strip()
    user_selector = os.getenv("LBOX_USERNAME_SELECTOR", "#log").strip()
    pass_selector = os.getenv("LBOX_PASSWORD_SELECTOR", "#pwd").strip()
    submit_selector = os.getenv("LBOX_SUBMIT_SELECTOR", "button[type='submit']").strip()
    wait_ms = env_int("LBOX_WAIT_MS", DEFAULT_WAIT_MS)
    headless = env_bool("LBOX_HEADLESS", False)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context()
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        print(f"[session] Opening {start_url}")
        page.goto(start_url, timeout=wait_ms)

        if username and password:
            print("[session] Credentials detected in environment. Attempting login flow.")
            maybe_fill(page.locator(user_selector), username)
            maybe_fill(page.locator(pass_selector), password)
            page.locator(submit_selector).click()
            try:
                page.wait_for_load_state("networkidle", timeout=wait_ms)
            except TimeoutError:
                print("[session] Login submit completed without reaching network idle.")
        else:
            print("[session] No credentials provided. Browser left open for manual inspection.")

        print("[session] Press Enter to close the browser.")
        input()
        context.close()
        browser.close()


if __name__ == "__main__":
    run_browser_session()
