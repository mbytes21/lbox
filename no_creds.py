import time
import secrets
import threading
import sys
import subprocess
import json
import os
import signal

# ==========================================================
# CONFIGURATION & GLOBAL STATE
# ==========================================================
USERNAME = ""
PASSWORD = ""
PREFIX = "LBOX-"
CODE_DELAY = 0.06 
CODES_PER_SECTOR = 100
SAVE_FILE = "progress.json"

ZONE_QUEUE = [
    "D0", "C4", "01", "87", "2B", "28", "19", "AE", "5D", "06", 
    "AD", "24", "FE", "C5", "9E", "89", "E3", "29", "36", "07", 
    "EE", "E6", "5E", "94", "61", "B1", "F6", "A7", "D5", "E0", 
    "D4", "4A", "B0", "92", "3A", "3E", "CA", "A6", "45", "BA", 
    "D8", "5F", "58", "37", "57", "26", "7F", "8F", "25", "60", 
    "66", "67", "9C", "8E", "86", "11", "98", "34", "2F", "B5", "C1"
]

# Shared state to track progress in memory without disk hits
state = {
    "zone_index": 0,
    "codes_sent": 0,
    "total_session_attempts": 0
}
state_lock = threading.Lock()

def load_progress():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                state["zone_index"] = data.get("zone_index", 0)
                state["codes_sent"] = data.get("codes_sent", 0)
                print(f"[System] Resuming from Zone {ZONE_QUEUE[state['zone_index']]}...")
        except:
            print("[System] Progress file corrupted, starting fresh.")

def save_to_disk():
    """The only function that actually touches the hard drive"""
    with state_lock:
        with open(SAVE_FILE, "w") as f:
            json.dump({
                "zone_index": state["zone_index"], 
                "codes_sent": state["codes_sent"]
            }, f)
    print(f"\n[System] Progress saved to {SAVE_FILE}.")

def signal_handler(sig, frame):
    """Triggered on Ctrl+C"""
    print("\n[System] Shutdown detected...")
    save_to_disk()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ==========================================================
# BROWSER LOGIC
# ==========================================================
def sync_playwright_env():
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    except:
        pass

sync_playwright_env()
from playwright.sync_api import sync_playwright

def run_vault_window(wid):
    """Stable worker that updates memory-only state"""
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage"
                    ]
                )
                context = browser.new_context(user_agent="Mozilla/5.0...")
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                page.goto("https://lucidtrading.com/my-account/", timeout=60000)
                if not page.locator('text="Log out"').is_visible(timeout=5000):
                    page.locator('#log').fill(USERNAME)
                    page.locator('#pwd').fill(PASSWORD)
                    page.locator('#lucidLoginBtn').click()
                    time.sleep(5)

                page.goto("https://dash.lucidtrading.com/#/promo")
                page.wait_for_selector('input.secret-redeem__input')
                
                while True:
                    with state_lock:
                        current_zone = ZONE_QUEUE[state["zone_index"]]
                        code = f"{PREFIX}{current_zone}{secrets.token_hex(3).upper()[:5]}"
                        
                        # Increment memory counters
                        state["codes_sent"] += 1
                        state["total_session_attempts"] += 1
                        
                        # Sector switch logic (In-Memory Only)
                        if state["codes_sent"] >= CODES_PER_SECTOR:
                            state["zone_index"] = (state["zone_index"] + 1) % len(ZONE_QUEUE)
                            state["codes_sent"] = 0
                            print(f"[W{wid}] Next Sector: {ZONE_QUEUE[state['zone_index']]}")

                    page.evaluate(f"""() => {{
                        const input = document.querySelector('input.secret-redeem__input');
                        const btn = document.querySelector('button.secret-redeem__btn');
                        if (input && btn) {{
                            input.value = "{code}";
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            btn.click();
                        }}
                    }}""")
                    
                    time.sleep(CODE_DELAY)
                    
        except Exception as e:
            time.sleep(5)

def main():
    load_progress()
    ans = input("How many windows? ")
    num = int(ans) if ans.strip() else 1

    for i in range(num):
        t = threading.Thread(target=run_vault_window, args=(i+1,), daemon=True)
        t.start()
        time.sleep(8) 

    while True:
        time.sleep(10)
        print(f" >> [SYSTEM] Session Attempts: {state['total_session_attempts']} | Current: {ZONE_QUEUE[state['zone_index']]}")

if __name__ == "__main__":
    main()
