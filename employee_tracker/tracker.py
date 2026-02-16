import time
import psutil
import win32gui
import win32process
import requests
import socket
from datetime import datetime
import pytz 
from database import init_db, save_to_queue, sync_with_server

# --- CONFIGURATION ---
SYSTEM_ID = socket.gethostname() 
SERVER_BASE = "http://127.0.0.1:5000" 
CONFIG_URL = f"{SERVER_BASE}/get_settings/{SYSTEM_ID}"

# LIST OF APPS TO IGNORE (Background / System Noise)
IGNORE_APPS = [
    "explorer.exe", "SearchApp.exe", #"LockApp.exe", 
    "ShellExperienceHost.exe", "SystemSettings.exe", 
    "TextInputHost.exe", "RuntimeBroker.exe", #"Taskmgr.exe"
]

# Default shift values (Overwritten by server)
start_hour = 9
end_hour = 18
last_config_check = 0
CONFIG_CHECK_INTERVAL = 600  # Check server for new hours every 10 minutes (600s)

def fetch_shift_config():
    global start_hour, end_hour, last_config_check
    
    # Only check if enough time has passed
    if time.time() - last_config_check < CONFIG_CHECK_INTERVAL:
        return

    try:
        response = requests.get(CONFIG_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Only update if changed
            if start_hour != data['start'] or end_hour != data['end']:
                start_hour = data['start']
                end_hour = data['end']
                print(f"🔄 Shift Updated: Now tracking {start_hour}:00 to {end_hour}:00")
            
            last_config_check = time.time()
    except:
        # If server is down, keep using old settings. Don't crash.
        pass

def get_ist_time():
    utc_now = datetime.now(pytz.utc)
    return utc_now.astimezone(pytz.timezone('Asia/Kolkata'))

def is_working_hours():
    current_ist = get_ist_time()
    curr = current_ist.hour
    
    # Logic for Standard Shift (e.g., 9 to 18)
    if start_hour < end_hour:
        return start_hour <= curr < end_hour
    
    # Logic for Overnight Shift (e.g., 22 to 06)
    else:
        return curr >= start_hour or curr < end_hour

def get_active_app():
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        app_name = process.name()
        return app_name
    except:
        return None

def get_location():
    try:
        # Added a fail-safe incase IP service is slow
        response = requests.get('https://ipinfo.io/json', timeout=3)
        data = response.json()
        return f"{data.get('city')}, {data.get('region')}"
    except:
        return "Location Unavailable"

def start_tracking():
    init_db()
    
    # Force first fetch
    global last_config_check
    last_config_check = 0 
    fetch_shift_config()
    
    current_app = None
    start_time = time.time()
    location = get_location()

    print(f"Tracking {SYSTEM_ID} started...")
    print(f"Shift: {start_hour}:00 to {end_hour}:00")
    
    try:
        while True:
            # 1. Periodically check if Admin changed hours
            fetch_shift_config()

            # 2. Check if currently in working hours
            if not is_working_hours():
                # Print status every minute so you know it's alive but paused
                print(f"💤 Off-hours ({get_ist_time().strftime('%H:%M')}). Waiting...", end="\r")
                time.sleep(60)
                continue

            # 3. Get Active App
            new_app = get_active_app()
            
            # Filter Ignored Apps
            if new_app in IGNORE_APPS:
                new_app = None

            # 4. Handle App Switching
            if new_app != current_app:
                if current_app:
                    duration = time.time() - start_time
                    
                    if duration > 5:
                        timestamp_str = get_ist_time().strftime('%Y-%m-%d %H:%M:%S')
                        print(f"LOG: {current_app} used for {round(duration)}s") 
                        save_to_queue(SYSTEM_ID, current_app, duration, location, timestamp_str)
                        sync_with_server()
                
                current_app = new_app
                start_time = time.time()
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    start_tracking()