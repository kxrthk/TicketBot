import time
import random
import requests
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import config

# STOP AFTER 5.5 HOURS (GitHub Limit is 6 Hours)
start_timestamp = time.time()
MAX_RUNTIME = 5.5 * 3600 

def send_alert(message):
    try:
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", 
                      data={"chat_id": config.CHAT_ID, "text": message})
    except: pass

def check_times(text):
    # Logic to find 08:30 AM - 04:00 PM
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

                # Scan for Theaters
                content = page.locator("body").inner_text()
                for theater in config.PREFERRED_THEATERS:
                    if theater.lower() in content.lower():
                        # Simple proximity check or full text scan
                        found_time = check_times(content) # simplified for cloud stability
                        if found_time:
                            send_alert(f"🚨 FOUND! {theater} @ {found_time}\n{site['url']}")
                            return True
            except Exception as e:
                print(f"Error: {e}")
        
        browser.close()
    return False

print("Starting Cloud Monitor...")
send_alert("🟢 GitHub Cloud Monitor Started.")

while True:
    if time.time() - start_timestamp > MAX_RUNTIME:
        send_alert("🔴 5.5 Hours Done. Stopping to save GitHub limit.")
        break
        
    if run_check():
        send_alert("🚨 TICKETS FOUND! Check Now!")
        break
    
    time.sleep(random.randint(30, 60))
