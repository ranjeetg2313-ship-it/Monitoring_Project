import sqlite3
import requests

DB_NAME = "offline_data.db"
SERVER_URL = "http://127.0.0.1:5000/upload" 

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS queue 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     system_id TEXT,
                     app_name TEXT, 
                     duration REAL, 
                     location TEXT, 
                     timestamp TEXT)''')
    conn.commit()
    conn.close()

def save_to_queue(system_id, app_name, duration, location, timestamp_str):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO queue (system_id, app_name, duration, location, timestamp) VALUES (?, ?, ?, ?, ?)", 
                 (system_id, app_name, duration, location, timestamp_str))
    conn.commit()
    conn.close()

def sync_with_server():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, system_id, app_name, duration, location, timestamp FROM queue")
    rows = cursor.fetchall()

    for row in rows:
        data = {
            "system_id": row[1], 
            "app": row[2], 
            "time": row[3], 
            "loc": row[4],
            "timestamp": row[5] 
        }
        try:
            response = requests.post(SERVER_URL, json=data, timeout=5)
            if response.status_code == 200:
                conn.execute("DELETE FROM queue WHERE id = ?", (row[0],))
                conn.commit()
        except requests.ConnectionError:
            break 
    conn.close()