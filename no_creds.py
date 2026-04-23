import time
import secrets
import threading
import sys
import subprocess
import json
import os
import signal
from playwright.sync_api import sync_playwright

# ==========================================================
# CONFIGURATION
# ==========================================================
USERNAME = ""
PASSWORD = ""
PREFIX = "LBOX-"
CODE_DELAY = 0.1  # Slightly increased for VM stability
CODES_PER_SECTOR = 100
SAVE_FILE = "progress.json"

ZONE_QUEUE = [
    "D0", "C4", "01", "87", "2B", "28", "19", "AE", "5D", "06", 
    "AD", "24", "FE", "C5", "9E", "89", "E3", "29", "36", "07", 
    "EE", "E6", "5E", "94", "61", "B1", "F6", "A7", "D5", "E0"
]

state = {"zone_index": 0, "codes_sent": 0, "total_session_attempts": 0}
state_lock = threading.Lock()

# ==========================================================
# SYSTEM UTILITIES
# ==========================================================
def load_progress():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                state["zone_index"] = data.get("zone_index", 0)
                state["codes_sent"] = data.get("codes_sent", 0)
                print(f"[*] Resuming from Zone {ZONE_QUEUE[state['zone_index']]}")
        except Exception:
            print("[!] Progress file error, starting fresh.")

def save_to_disk():
    with state_lock:
        with open(SAVE_FILE, "w") as f:
            json.dump({"zone_index": state["zone_index"], "codes_sent": state["codes_sent"]}, f)
    print(f"\n[!] Progress saved to {SAVE_FILE}")

def signal_handler(sig, frame):
    save_to_disk()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ==========================================================
# CORE BROWSER ENGINE
# ==========================================================
def run_vault_worker(wid):
    while True:
        try:
            with sync_playwright() as p:
                # Optimized for Proxmox/VM environments
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-gpu",
                        "--disable-dev-shm-usage",
                        "--disable-software-rasterizer",
                        "--window-size=1280,720"
                    ]
                )
                
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 720}
                )
                
                # Anti-Detection Script
                context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page = context.new_page()
                
                # Login Flow
                print(f"[W{wid}] Accessing Login...")
                page.goto("https://lucidtrading.com/my-account/", timeout=90000)
                
                if not page.get_by_text("Log out").is_visible(timeout=5000):
                    page.locator('#log').fill(USERNAME)
                    page.locator('#pwd').fill(PASSWORD)
                    page.locator('#lucidLoginBtn').click()
                    page.wait_for_load_state("networkidle")

                # Navigate to Promo
                page.goto("https://dash.lucidtrading.com/#/promo", wait_until="networkidle")
                page.wait_for_selector('input.secret-redeem__input')
                
                print(f"[W{wid}] authenticated and ready.")

                while True:
                    with state_lock:
                        current_zone = ZONE_QUEUE[state["zone_index"]]
                        code = f"{PREFIX}{current_zone}{secrets.token_hex(3).upper()[:5]}"
                        
                        state["codes_sent"] += 1
                        state["total_session_attempts"] += 1
                        
                        if state["codes_sent"] >= CODES_PER_SECTOR:
                            state["zone_index"] = (state["zone_index"] + 1) % len(ZONE_QUEUE)
                            state["codes_sent"] = 0
                            save_to_disk() # Auto-save on sector change

                    # Reliable JS Injection for Frameworks (React/Vue)
                    page.evaluate(f"""() => {{
                        const input = document.querySelector('input.secret-redeem__input');
                        const btn = document.querySelector('button.secret-redeem__btn');
                        if (input && btn) {{
                            input.value = '{code}';
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            btn.click();
                        }}
                    }}""")
                    
                    time.sleep(CODE_DELAY)

        except Exception as e:
            print(f"[W{wid}] Error: {e}. Restarting worker...")
            time.sleep(10)

def main():
    load_progress()
    try:
        ans = input("Number of VM windows: ")
        num = int(ans) if ans.strip() else 1
    except ValueError:
        num = 1

    for i in range(num):
        t = threading.Thread(target=run_vault_worker, args=(i+1,), daemon=True)
        t.start()
        time.sleep(10) # Staggered start to prevent CPU spikes

    while True:
        time.sleep(15)
        with state_lock:
            print(f" >> STATS | Total: {state['total_session_attempts']} | Zone: {ZONE_QUEUE[state['zone_index']]} ({state['codes_sent']}/{CODES_PER_SECTOR})")

if __name__ == "__main__":
    main()
