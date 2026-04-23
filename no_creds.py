import time
import secrets
import threading
import sys
from cloakbrowser import launch

# ==========================================================
# USER CONFIGURATION
# ==========================================================
USERNAME = ""
PASSWORD = ""
PREFIX = "LBOX-"
CODE_DELAY = 0.1 
STATS_INTERVAL = 10 

# High-priority sectors identified from reverse engineering
ZONE_QUEUE = [
    "D0", "C4", "01", "87", "2B", "28", "19", "AE", "5D", "06", 
    "AD", "24", "FE", "C5", "9E", "89", "E3", "29", "36", "07", 
    "EE", "E6", "5E", "94", "61", "B1", "F6", "A7", "D5", "E0", 
    "D4", "4A", "B0", "92", "3A", "3E", "CA", "A6", "45", "BA", 
    "D8", "5F", "58", "37", "57", "26", "7F", "8F", "25", "60", 
    "66", "67", "9C", "8E", "86", "11", "98", "34", "2F", "B5", "C1"
] 
ZONE_THRESHOLD = 1048576 # 2^20 combinations per sector
# ==========================================================

window_stats = {}
current_zone_index = 0
codes_in_current_zone = 0
stats_lock = threading.Lock()
stop_event = threading.Event()
start_time = time.time()

def get_next_code():
    """Manages global sector cycling across all threads"""
    global current_zone_index, codes_in_current_zone
    with stats_lock:
        if codes_in_current_zone >= ZONE_THRESHOLD:
            current_zone_index = (current_zone_index + 1) % len(ZONE_QUEUE)
            codes_in_current_zone = 0
            print(f"\n[System] Sector Complete. Moving to Zone: {ZONE_QUEUE[current_zone_index]}")
        
        active_zone = ZONE_QUEUE[current_zone_index]
        codes_in_current_zone += 1
        
        # Suffix is 5 hex chars to complete the 7-char code
        suffix = secrets.token_hex(3).upper()[:5]
        return f"{PREFIX}{active_zone}{suffix}"

def handle_login(page):
    """Handles fresh login and existing session detection"""
    try:
        page.goto("https://lucidtrading.com/my-account/", wait_until="domcontentloaded", timeout=45000)
        time.sleep(2)
        
        # Check if already logged in (based on page source provided)
        if page.locator('text="Log out"').is_visible() or page.locator('.woocommerce-MyAccount-content').is_visible():
            print("[System] Session valid. Skipping login fields.")
        
        # Fresh login required
        elif page.locator('#log').is_visible():
            page.locator('#log').fill(USERNAME)
            page.locator('#pwd').fill(PASSWORD)
            page.locator('#lucidLoginBtn').click(force=True)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        # Move to the promo dashboard
        page.goto("https://dash.lucidtrading.com/#/promo", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector('input.secret-redeem__input', timeout=30000)
        return True
    except Exception as e:
        print(f"[System] Navigation Error: {str(e)[:60]}...")
        return False

def fast_vault_loop(page, window_index):
    """The main injection loop"""
    injection_js = """
    (code) => {
        const input = document.querySelector('input.secret-redeem__input');
        const btn = document.querySelector('button.secret-redeem__btn');
        if (input && btn) {
            input.value = code;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            btn.disabled = false;
            btn.click();
            return true;
        }
        return false;
    }
    """
    check_counter = 0
    while not stop_event.is_set():
        # Periodically check if we are still on the promo page
        check_counter += 1
        if check_counter >= 200:
            if not page.locator('input.secret-redeem__input').is_visible():
                if not handle_login(page): 
                    return # Exit to trigger self-healing respawn
            check_counter = 0

        code = get_next_code()
        try:
            if page.evaluate(injection_js, code):
                with stats_lock:
                    window_stats[window_index] = window_stats.get(window_index, 0) + 1
            time.sleep(CODE_DELAY)
        except:
            return # Trigger respawn on communication failure

def self_healing_wrapper(window_index):
    """Keeps the window running even if it crashes or times out"""
    while not stop_event.is_set():
        browser = None
        try:
            browser = launch(headless=False, humanize=False)
            context = browser.new_context(viewport={'width': 1000, 'height': 700})
            page = context.new_page()
            
            if handle_login(page):
                print(f"[Window {window_index}] Success. Starting loop...")
                fast_vault_loop(page, window_index)
            else:
                print(f"[Window {window_index}] Failed to reach promo page. Retrying...")
                
        except Exception:
            pass # Error handled by the restart loop
        finally:
            if browser:
                try: browser.close()
                except: pass
            if not stop_event.is_set():
                time.sleep(5) # Cooldown before respawning

def stats_reporter():
    """Background thread for performance tracking"""
    while not stop_event.is_set():
        time.sleep(STATS_INTERVAL)
        with stats_lock:
            if window_stats:
                elapsed = time.time() - start_time
                time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
                total = sum(window_stats.values())
                cpm = round(total / (elapsed / 60), 2) if elapsed > 0 else 0
                current_zone = ZONE_QUEUE[current_zone_index]
                
                print(f"\n--- [STATS] {time_str} | Zone: {current_zone} ---")
                print(f"Total Codes: {total} | Overall CPM: {cpm}")
                print("-" * 40)

def main():
    try:
        num_windows_input = input("How many windows would you like to open? ")
        num_windows = int(num_windows_input) if num_windows_input.strip() else 1
    except ValueError:
        num_windows = 1

    # Start the stats thread
    threading.Thread(target=stats_reporter, daemon=True).start()

    # Launch the self-healing threads
    threads = []
    for i in range(num_windows):
        if stop_event.is_set(): break
        t = threading.Thread(target=self_healing_wrapper, args=(i + 1,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(2) # Staggered starts to prevent site lag

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Shutdown signal received. Closing all windows...")
        stop_event.set()

if __name__ == "__main__":
    main()
