import time
import secrets
import threading
import sys
import subprocess

# Ensure Playwright is ready for the desktop
def sync_playwright_env():
    print("[System] Finalizing browser links...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    except Exception as e:
        print(f"[Error] Failed to install Playwright: {e}")

sync_playwright_env()
from playwright.sync_api import sync_playwright

# ==========================================================
# CONFIGURATION
# ==========================1================================
USERNAME = ""
PASSWORD = ""
PREFIX = "LBOX-"
CODE_DELAY = 0.1  # Speed of injection

# Updated Zone Queue: Starting at 01 and moving through the next 9 sectors
ZONE_QUEUE = ["01", "D0", "C4", "87", "2B", "AE", "5D", "06", "AD", "24"] 
CODES_PER_SECTOR = 1000

stats = {"total": 0}
stats_lock = threading.Lock()

def run_vault_window(wid):
    """Stable multi-window worker with sequential zone switching"""
    while True:
        try:
            with sync_playwright() as p:
                # Launching with specific flags to prevent crashes
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu" 
                    ]
                )
                
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={'width': 1000, 'height': 720}
                )
                
                page = context.new_page()
                # Stealth: Hide bot identity
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                print(f"[W{wid}] Heading to Lucid...")
                page.goto("https://lucidtrading.com/my-account/", wait_until="load", timeout=60000)
                
                # Login Logic
                if not page.locator('text="Log out"').is_visible(timeout=5000):
                    page.locator('#log').fill(USERNAME)
                    page.locator('#pwd').fill(PASSWORD)
                    page.locator('#lucidLoginBtn').click()
                    time.sleep(5)

                page.goto("https://dash.lucidtrading.com/#/promo", wait_until="load")
                page.wait_for_selector('input.secret-redeem__input', timeout=30000)
                
                print(f"[W{wid}] Injection loop active.")
                
                # Sequential Switch Tracking
                zone_index = 0
                codes_sent_in_current_sector = 0
                
                while True:
                    current_zone = ZONE_QUEUE[zone_index]
                    
                    # Generate code: PREFIX + ZONE + 5 random hex chars
                    code = f"{PREFIX}{current_zone}{secrets.token_hex(3).upper()[:5]}"
                    
                    # Inject via JS for maximum speed
                    page.evaluate("""(code) => {
                        const input = document.querySelector('input.secret-redeem__input');
                        const btn = document.querySelector('button.secret-redeem__btn');
                        if (input && btn) {
                            input.value = code;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            btn.click();
                        }
                    }""", code)
                    
                    # Update stats
                    with stats_lock:
                        stats["total"] += 1
                    
                    codes_sent_in_current_sector += 1
                    
                    # Switch Sector logic
                    if codes_sent_in_current_sector >= CODES_PER_SECTOR:
                        zone_index = (zone_index + 1) % len(ZONE_QUEUE)
                        codes_sent_in_current_sector = 0
                        print(f"[W{wid}] Completed 100 codes. Switching to Zone: {ZONE_QUEUE[zone_index]}")

                    time.sleep(CODE_DELAY)
                    
        except Exception as e:
            # Shortened error message for cleaner console output
            err_msg = str(e).split('\n')[0][:50]
            print(f"[W{wid}] Session Reset ({err_msg}). Restarting...")
            time.sleep(5)

def main():
    print("--- Lucid Sequential Code Generator ---")
    ans = input("How many windows? ")
    num = int(ans) if ans.strip() else 1

    for i in range(num):
        t = threading.Thread(target=run_vault_window, args=(i+1,), daemon=True)
        t.start()
        # Staggered start to prevent CPU spikes and login collisions
        time.sleep(8) 

    try:
        while True:
            time.sleep(10)
            print(f" >> [SYSTEM] Total Attempts: {stats['total']}")
    except KeyboardInterrupt:
        print("\n[System] Shutting down...")
        sys.exit()

if __name__ == "__main__":
    main()
