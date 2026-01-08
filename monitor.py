import time
import random
import requests
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import config

# STOP AFTER 5.5 HOURS (GitHub Limit)
start_timestamp = time.time()
MAX_RUNTIME = 5.5 * 3600 

def send_alert(message):
    try:
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", 
                      data={"chat_id": config.CHAT_ID, "text": message})
    except: pass

def check_times(text):
    matches = re.findall(r"\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)", text)
    for t_str in matches:
        try:
            t_obj = datetime.strptime(t_str.strip().upper(), "%I:%M %p")
            val = t_obj.hour + (t_obj.minute / 60.0)
            if config.START_TIME <= val <= config.END_TIME:
                return f"{t_str}"
        except: pass
    return None

def run_check():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = context.new_page()

        for site in config.SITES_TO_WATCH:
            try:
                print(f"Checking {site['url']}...")
                page.goto(site['url'], timeout=60000)
                page.wait_for_timeout(5000)
                
                # BMS Click
                if "bookmyshow" in site['url'] and site['date_trigger']:
                    try: page.locator(f"text={site['date_trigger']}").first.click(timeout=3000)
                    except: pass
                    page.wait_for_timeout(2000)

                # Scan
                content = page.locator("body").inner_text()
                for theater in config.PREFERRED_THEATERS:
                    if theater.lower() in content.lower():
                        found_time = check_times(content)
                        if found_time:
                            # === 🚨 PANIC ALARM MODE ===
                            msg = f"🚨 WAKE UP! {theater} @ {found_time}\n{site['url']}"
                            for _ in range(15): # SEND 15 ALERTS
                                send_alert(msg)
                                time.sleep(1)
                                send_alert("🚨 WAKE UP! TICKETS OPEN!")
                                time.sleep(1)
                            return True
            except Exception as e:
                print(f"Error: {e}")
        
        browser.close()
    return False

print("Starting Cloud Monitor...")
send_alert("🟢 GitHub Cloud Monitor Started.")

while True:
    if time.time() - start_timestamp > MAX_RUNTIME:
        send_alert("🔴 5.5 Hours Done. Restarting soon...")
        break
        
    if run_check():
        break # Stop script so alerts don't loop forever after finding
    
    time.sleep(random.randint(30, 60))
