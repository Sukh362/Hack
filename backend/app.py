from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)

# CORS setup for all origins and methods
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])

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
            device_model TEXT,
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
    
    # Insert default parent if not exists
    cursor.execute("SELECT * FROM parents WHERE email = ?", (FIXED_USERNAME,))
    if not cursor.fetchone():
        parent_id = "parent-" + str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO parents (id, email, password, created_at) VALUES (?, ?, ?, ?)",
            (parent_id, FIXED_USERNAME, FIXED_PASSWORD, datetime.now().isoformat())
        )
        print(f"Created default parent: {parent_id}")
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('parental.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/parent/register', methods=['POST', 'OPTIONS'])
def register_parent():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({"message": "Use fixed credentials: Username=Sukh, Password=Sukh hacker"})

@app.route('/parent/login', methods=['POST', 'OPTIONS'])
def login_parent():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    
    # Check fixed credentials
    if data.get('email') == FIXED_USERNAME and data.get('password') == FIXED_PASSWORD:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM parents WHERE email = ?", (FIXED_USERNAME,))
        parent = cursor.fetchone()
        conn.close()
        
        if parent:
            return jsonify({
                "message": "Login successful", 
                "parent_id": parent['id'],
                "username": FIXED_USERNAME
            })
    
    return jsonify({"error": "Invalid credentials"}), 401

# AUTO-REGISTER CHILD DEVICE
@app.route('/child/auto_register', methods=['POST', 'OPTIONS'])
def auto_register_child():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    print(f"Auto-register request: {data}")
    
    # Get device info from mobile app
    device_id = data.get('device_id')
    device_model = data.get('device_model', 'Unknown Device')
    child_name = data.get('child_name', 'Unknown Child')
    
    if not device_id:
        return jsonify({"error": "Device ID required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the fixed parent
    cursor.execute("SELECT id FROM parents WHERE email = ?", (FIXED_USERNAME,))
    parent = cursor.fetchone()
    
    if not parent:
        return jsonify({"error": "Parent not found"}), 404
    
    parent_id = parent['id']
    
    # Check if device already registered
    cursor.execute("SELECT * FROM children WHERE device_id = ?", (device_id,))
    existing_child = cursor.fetchone()
    
    if existing_child:
        print(f"Device already registered: {device_id}")
        return jsonify({
            "message": "Device already registered",
            "child_id": existing_child['id'],
            "is_blocked": bool(existing_child['is_blocked'])
        })
    
    # Generate proper child name if not provided
    if child_name == 'Unknown Child' or not child_name:
        child_name = f"Child - {device_model}"
    
    # Register new device
    child_id = "child-" + str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO children (id, parent_id, name, device_id, device_model, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (child_id, parent_id, child_name, device_id, device_model, datetime.now().isoformat())
    )
    
    conn.commit()
    conn.close()
    
    print(f"New device registered: {child_name} - {device_model} - {device_id}")
    
    return jsonify({
        "message": "Child device auto-registered successfully", 
        "child_id": child_id,
        "parent_id": parent_id,
        "device_id": device_id,
        "device_model": device_model,
        "child_name": child_name
    })

@app.route('/child/register', methods=['POST', 'OPTIONS'])
def register_child():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    child_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO children (id, parent_id, name, device_id, device_model, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (child_id, data['parent_id'], data['name'], data['device_id'], 'Manual Entry', datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Child registered successfully", "child_id": child_id})

@app.route('/usage/log', methods=['POST', 'OPTIONS'])
def log_usage():
    if request.method == 'OPTIONS':
        return '', 200
        
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

@app.route('/child/block', methods=['POST', 'OPTIONS'])
def block_child():
    if request.method == 'OPTIONS':
        return '', 200
        
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

@app.route('/parent/children/<parent_id>', methods=['GET', 'OPTIONS'])
def get_children(parent_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM children WHERE parent_id = ? ORDER BY created_at DESC", (parent_id,))
    children = cursor.fetchall()
    conn.close()
    
    children_list = []
    for child in children:
        children_list.append({
            "id": child['id'],
            "name": child['name'],
            "device_id": child['device_id'],
            "device_model": child['device_model'],
            "is_blocked": bool(child['is_blocked']),
            "created_at": child['created_at']
        })
    
    return jsonify({"children": children_list})

@app.route('/parent/usage/<child_id>', methods=['GET', 'OPTIONS'])
def get_usage(child_id):
    if request.method == 'OPTIONS':
        return '', 200
        
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

@app.route('/child/status/<device_id>', methods=['GET', 'OPTIONS'])
def get_child_status(device_id):
    if request.method == 'OPTIONS':
        return '', 200
        
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

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "Backend is working!", "timestamp": datetime.now().isoformat()})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def root():
    return jsonify({
        "message": "Parental Control API is running!",
        "login_credentials": {
            "username": "Sukh",
            "password": "Sukh hacker"
        },
        "endpoints": {
            "auto_register": "/child/auto_register",
            "parent_login": "/parent/login",
            "get_children": "/parent/children/{parent_id}",
            "block_child": "/child/block",
            "log_usage": "/usage/log",
            "check_status": "/child/status/{device_id}"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
