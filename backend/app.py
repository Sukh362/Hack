from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Fixed parent credentials
FIXED_USERNAME = "Sukh"
FIXED_PASSWORD = "Sukh hacker"

def init_db():
    conn = sqlite3.connect('parental.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parents (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS children (
            id TEXT PRIMARY KEY,
            parent_id TEXT,
            name TEXT,
            device_id TEXT UNIQUE,
            is_blocked BOOLEAN DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id TEXT PRIMARY KEY,
            child_id TEXT,
            app_name TEXT,
            duration INTEGER,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('parental.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/parent/register', methods=['POST'])
def register_parent():
    return jsonify({"message": "Use fixed credentials: Username=Sukh, Password=Sukh hacker"})

@app.route('/parent/login', methods=['POST'])
def login_parent():
    data = request.json
    
    # Check fixed credentials
    if data.get('email') == FIXED_USERNAME and data.get('password') == FIXED_PASSWORD:
        # Create or get parent ID
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM parents WHERE email = ?", (FIXED_USERNAME,))
        existing_parent = cursor.fetchone()
        
        if existing_parent:
            parent_id = existing_parent['id']
        else:
            parent_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO parents (id, email, password, created_at) VALUES (?, ?, ?, ?)",
                (parent_id, FIXED_USERNAME, FIXED_PASSWORD, datetime.now().isoformat())
            )
            conn.commit()
        
        conn.close()
        return jsonify({
            "message": "Login successful", 
            "parent_id": parent_id,
            "username": FIXED_USERNAME
        })
    else:
        return jsonify({"error": "Invalid credentials. Use: Username=Sukh, Password=Sukh hacker"}), 401

@app.route('/child/register', methods=['POST'])
def register_child():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    child_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO children (id, parent_id, name, device_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (child_id, data['parent_id'], data['name'], data['device_id'], datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Child registered successfully", "child_id": child_id})

@app.route('/usage/log', methods=['POST'])
def log_usage():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    log_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO usage_logs (id, child_id, app_name, duration, timestamp) VALUES (?, ?, ?, ?, ?)",
        (log_id, data['child_id'], data['app_name'], data['duration'], datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Usage logged successfully"})

@app.route('/child/block', methods=['POST'])
def block_child():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE children SET is_blocked = ? WHERE id = ?",
        (data['is_blocked'], data['child_id'])
    )
    conn.commit()
    conn.close()
    
    action = "blocked" if data['is_blocked'] else "unblocked"
    return jsonify({"message": f"Child {action} successfully"})

@app.route('/parent/children/<parent_id>', methods=['GET'])
def get_children(parent_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM children WHERE parent_id = ?", (parent_id,))
    children = cursor.fetchall()
    conn.close()
    
    children_list = []
    for child in children:
        children_list.append({
            "id": child['id'],
            "name": child['name'],
            "device_id": child['device_id'],
            "is_blocked": bool(child['is_blocked'])
        })
    
    return jsonify({"children": children_list})

@app.route('/parent/usage/<child_id>', methods=['GET'])
def get_usage(child_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM usage_logs WHERE child_id = ? ORDER BY timestamp DESC LIMIT 50",
        (child_id,)
    )
    logs = cursor.fetchall()
    conn.close()
    
    usage_logs = []
    for log in logs:
        usage_logs.append({
            "app_name": log['app_name'],
            "duration": log['duration'],
            "timestamp": log['timestamp']
        })
    
    return jsonify({"usage_logs": usage_logs})

@app.route('/child/status/<device_id>', methods=['GET'])
def get_child_status(device_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM children WHERE device_id = ?", (device_id,))
    child = cursor.fetchone()
    conn.close()
    
    if child:
        return jsonify({
            "is_blocked": bool(child['is_blocked']),
            "child_id": child['id'],
            "name": child['name']
        })
    else:
        return jsonify({"error": "Child device not found"}), 404

@app.route('/')
def root():
    return jsonify({
        "message": "Parental Control API is running!",
        "login_credentials": {
            "username": "Sukh",
            "password": "Sukh hacker"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
