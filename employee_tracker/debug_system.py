import requests
import sqlite3
import os

# --- CONFIGURATION ---
SERVER_URL = "http://127.0.0.1:5000/upload"
DB_PATH = "offline_data.db"

print("--- DIAGNOSTIC TEST STARTED ---")

# TEST 1: Check if Local Database Exists
print("\n[TEST 1] Checking Local Database...")
if os.path.exists(DB_PATH):
    print(f"✅ 'offline_data.db' found. Size: {os.path.getsize(DB_PATH)} bytes")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM queue")
        count = cursor.fetchone()[0]
        print(f"ℹ️  There are {count} unsent records stuck in the local queue.")
        conn.close()
    except Exception as e:
        print(f"❌ Error reading database: {e}")
else:
    print("⚠️ 'offline_data.db' does not exist yet. (This is normal if you just started)")

# TEST 2: Check Server Connection
print("\n[TEST 2] Pinging Server...")
try:
    # We send a fake data packet to see if the server accepts it
    test_data = {
        "system_id": "TEST_PC",
        "app": "Test_App.exe",
        "time": 5.5,
        "loc": "Test_Location",
        "timestamp": "2023-01-01 12:00:00"
    }
    response = requests.post(SERVER_URL, json=test_data, timeout=5)
    
    if response.status_code == 200:
        print("✅ Server Connection SUCCESS! (Data sent successfully)")
    else:
        print(f"❌ Server Error. Status Code: {response.status_code}")
        print(f"Server Message: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ FAILED: Could not connect to the server.")
    print("   -> Is 'server.py' running?")
    print("   -> Are you using the correct URL (http://127.0.0.1:5000)?")
except Exception as e:
    print(f"❌ An error occurred: {e}")

print("\n--- TEST FINISHED ---")