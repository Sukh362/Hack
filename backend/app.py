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
    
    # Battery data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS battery_data (
            id TEXT PRIMARY KEY,
            device_id TEXT,
            battery_level INTEGER,
            is_charging BOOLEAN,
            battery_health INTEGER,
            temperature REAL,
            voltage REAL,
            timestamp TEXT,
            FOREIGN KEY (device_id) REFERENCES children (device_id)
        )
    ''')
    
    # NEW: Camera commands table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS camera_commands (
            id TEXT PRIMARY KEY,
            device_id TEXT,
            command TEXT,
            status TEXT,
            timestamp TEXT,
            executed_at TEXT,
            FOREIGN KEY (device_id) REFERENCES children (device_id)
        )
    ''')
    
    # Insert default parent if not exists
    cursor.execute("SELECT * FROM parents WHERE email = ?", (FIXED_USERNAME,))
    if not cursor.fetchone():
        parent_id = "parent-main-123"
        cursor.execute(
            "INSERT INTO parents (id, email, password, created_at) VALUES (?, ?, ?, ?)",
            (parent_id, FIXED_USERNAME, FIXED_PASSWORD, datetime.now().isoformat())
        )
        print(f"Created default parent: {parent_id}")
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

def get_db_connection():
    conn = sqlite3.connect('parental.db')
    conn.row_factory = sqlite3.Row
    return conn

# ========== CAMERA ROUTES ==========

@app.route('/camera', methods=['GET', 'POST', 'OPTIONS'])
def camera_capture():
    """Camera capture endpoint for mobile app"""
    if request.method == 'OPTIONS':
        return '', 200
    elif request.method == 'GET':
        # GET request ke liye response
        return jsonify({
            "message": "Camera endpoint is working!",
            "endpoint": "/camera",
            "supported_methods": ["GET", "POST", "OPTIONS"],
            "usage": "Send POST request with device_id and image_data",
            "timestamp": datetime.now().isoformat()
        })
        
    # POST request handling
    data = request.json
    print(f"Camera data received: {data}")
    
    # Basic validation
    if not data or 'device_id' not in data:
        return jsonify({"error": "Device ID is required"}), 400
    
    device_id = data.get('device_id')
    image_data = data.get('image_data', '')  # Base64 encoded image data
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    # Here you can process the image data as needed
    # For now, just log the receipt of camera data
    
    print(f"Camera capture from device: {device_id}")
    print(f"Image data length: {len(image_data) if image_data else 0}")
    print(f"Timestamp: {timestamp}")
    
    # You can save the image to disk or database here
    # Example: save to filesystem
    if image_data:
        try:
            # Create camera directory if not exists
            import os
            if not os.path.exists('camera_captures'):
                os.makedirs('camera_captures')
            
            # Save image with device_id and timestamp
            filename = f"camera_captures/{device_id}_{timestamp.replace(':', '-')}.txt"
            with open(filename, 'w') as f:
                f.write(f"Device: {device_id}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Image Data: {image_data[:100]}...\n")  # Save first 100 chars only
            
            print(f"Camera data saved to: {filename}")
            
        except Exception as e:
            print(f"Error saving camera data: {e}")
    
    return jsonify({
        "message": "Camera data received successfully",
        "device_id": device_id,
        "timestamp": timestamp,
        "image_received": bool(image_data),
        "status": "success"
    })

@app.route('/camera/control', methods=['POST', 'OPTIONS'])
def camera_control():
    """Camera control endpoint for mobile app"""
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    print(f"Camera control received: {data}")
    
    # Basic validation
    if not data or 'device_id' not in data or 'command' not in data:
        return jsonify({"error": "Device ID and command are required"}), 400
    
    device_id = data.get('device_id')
    command = data.get('command')
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    # Validate command
    valid_commands = ['front', 'back', 'stop', 'capture']
    if command not in valid_commands:
        return jsonify({"error": f"Invalid command. Use: {valid_commands}"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if device exists
    cursor.execute("SELECT * FROM children WHERE device_id = ?", (device_id,))
    device = cursor.fetchone()
    
    if not device:
        conn.close()
        return jsonify({"error": "Device not registered"}), 404
    
    # Save command to database
    command_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO camera_commands (id, device_id, command, status, timestamp, executed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        command_id,
        device_id,
        command,
        'sent',
        timestamp,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    # Log the camera command
    print(f"Camera {command} command received for device: {device_id}")
    print(f"Timestamp: {timestamp}")
    print(f"Command ID: {command_id}")
    
    return jsonify({
        "message": f"Camera {command} command executed successfully",
        "device_id": device_id,
        "command": command,
        "command_id": command_id,
        "timestamp": timestamp,
        "status": "success"
    })

@app.route('/camera/status/<device_id>', methods=['GET'])
def get_camera_status(device_id):
    """Get camera status for specific device"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get latest camera command
    cursor.execute('''
        SELECT * FROM camera_commands 
        WHERE device_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (device_id,))
    
    latest_command = cursor.fetchone()
    conn.close()
    
    if latest_command:
        return jsonify({
            "device_id": device_id,
            "last_command": latest_command['command'],
            "last_command_time": latest_command['timestamp'],
            "status": latest_command['status'],
            "camera_available": True
        })
    else:
        return jsonify({
            "device_id": device_id,
            "camera_available": True,
            "status": "no_commands_yet",
            "message": "Camera is available but no commands sent yet"
        })

@app.route('/camera/commands/<device_id>', methods=['GET'])
def get_camera_commands(device_id):
    """Get camera command history for device"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM camera_commands 
        WHERE device_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 20
    ''', (device_id,))
    
    commands = cursor.fetchall()
    conn.close()
    
    commands_list = []
    for cmd in commands:
        commands_list.append({
            "id": cmd['id'],
            "command": cmd['command'],
            "status": cmd['status'],
            "timestamp": cmd['timestamp'],
            "executed_at": cmd['executed_at']
        })
    
    return jsonify({
        "device_id": device_id,
        "total_commands": len(commands_list),
        "commands": commands_list
    })

@app.route('/camera/status', methods=['GET'])
def camera_service_status():
    """Check camera service status"""
    return jsonify({
        "message": "Camera service is active",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "camera_capture": "/camera",
            "camera_control": "/camera/control",
            "camera_status": "/camera/status/<device_id>",
            "camera_commands": "/camera/commands/<device_id>"
        }
    })

# ========== BATTERY ROUTES ==========

@app.route('/battery', methods=['GET'])
def get_all_battery_data():
    """Get battery data for all devices"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.name, c.device_id, b.battery_level, b.is_charging, 
               b.battery_health, b.temperature, b.voltage, b.timestamp
        FROM battery_data b
        JOIN children c ON b.device_id = c.device_id
        ORDER BY b.timestamp DESC
    ''')
    
    battery_data = cursor.fetchall()
    conn.close()
    
    result = []
    for row in battery_data:
        result.append({
            "device_name": row['name'],
            "device_id": row['device_id'],
            "battery_level": row['battery_level'],
            "is_charging": bool(row['is_charging']),
            "battery_health": row['battery_health'],
            "temperature": row['temperature'],
            "voltage": row['voltage'],
            "last_updated": row['timestamp']
        })
    
    return jsonify({
        "message": "Battery data retrieved successfully",
        "total_devices": len(result),
        "battery_data": result
    })

@app.route('/battery/<device_id>', methods=['GET'])
def get_battery_status(device_id):
    """Get battery status for specific device"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT b.*, c.name as device_name 
        FROM battery_data b
        JOIN children c ON b.device_id = c.device_id
        WHERE b.device_id = ?
        ORDER BY b.timestamp DESC
        LIMIT 1
    ''', (device_id,))
    
    battery_data = cursor.fetchone()
    conn.close()
    
    if battery_data:
        return jsonify({
            "device_id": battery_data['device_id'],
            "device_name": battery_data['device_name'],
            "battery_level": battery_data['battery_level'],
            "is_charging": bool(battery_data['is_charging']),
            "battery_health": battery_data['battery_health'],
            "temperature": battery_data['temperature'],
            "voltage": battery_data['voltage'],
            "last_updated": battery_data['timestamp'],
            "status": "success"
        })
    else:
        return jsonify({
            "error": "No battery data found for this device",
            "device_id": device_id,
            "status": "not_found"
        }), 404

@app.route('/battery/update', methods=['POST', 'OPTIONS'])
def update_battery_data():
    """Update battery data from mobile app"""
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    print(f"Battery update received: {data}")
    
    device_id = data.get('device_id')
    battery_level = data.get('battery_level')
    
    if not device_id or battery_level is None:
        return jsonify({"error": "Device ID and battery level are required"}), 400
    
    # Validate battery level
    if not (0 <= battery_level <= 100):
        return jsonify({"error": "Battery level must be between 0 and 100"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if device exists
    cursor.execute("SELECT * FROM children WHERE device_id = ?", (device_id,))
    device = cursor.fetchone()
    
    if not device:
        return jsonify({"error": "Device not registered"}), 404
    
    # Insert or update battery data
    battery_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO battery_data (id, device_id, battery_level, is_charging, 
                                battery_health, temperature, voltage, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        battery_id,
        device_id,
        battery_level,
        data.get('is_charging', False),
        data.get('battery_health', 100),
        data.get('temperature', 25.0),
        data.get('voltage', 3.8),
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    print(f"Battery data updated for device {device_id}: {battery_level}%")
    
    return jsonify({
        "message": "Battery data updated successfully",
        "device_id": device_id,
        "battery_level": battery_level,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/battery/history/<device_id>', methods=['GET'])
def get_battery_history(device_id):
    """Get battery history for a device"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT battery_level, is_charging, timestamp
        FROM battery_data 
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT 50
    ''', (device_id,))
    
    history = cursor.fetchall()
    conn.close()
    
    history_list = []
    for row in history:
        history_list.append({
            "battery_level": row['battery_level'],
            "is_charging": bool(row['is_charging']),
            "timestamp": row['timestamp']
        })
    
    return jsonify({
        "device_id": device_id,
        "history": history_list,
        "total_records": len(history_list)
    })

@app.route('/battery/stats', methods=['GET'])
def get_battery_stats():
    """Get battery statistics for all devices"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get latest battery data for each device
    cursor.execute('''
        SELECT c.name, c.device_id, b.battery_level, b.is_charging, b.timestamp
        FROM battery_data b
        JOIN children c ON b.device_id = c.device_id
        WHERE b.timestamp = (
            SELECT MAX(timestamp) FROM battery_data WHERE device_id = b.device_id
        )
    ''')
    
    latest_data = cursor.fetchall()
    conn.close()
    
    if not latest_data:
        return jsonify({
            "message": "No battery data available",
            "stats": {
                "total_devices": 0,
                "average_battery": 0,
                "charging_count": 0,
                "low_battery_count": 0
            }
        })
    
    total_battery = sum(row['battery_level'] for row in latest_data)
    charging_count = sum(1 for row in latest_data if row['is_charging'])
    low_battery_count = sum(1 for row in latest_data if row['battery_level'] <= 20)
    
    return jsonify({
        "message": "Battery statistics retrieved successfully",
        "stats": {
            "total_devices": len(latest_data),
            "average_battery": round(total_battery / len(latest_data), 1),
            "charging_count": charging_count,
            "low_battery_count": low_battery_count,
            "last_updated": datetime.now().isoformat()
        },
        "devices": [
            {
                "name": row['name'],
                "device_id": row['device_id'],
                "battery_level": row['battery_level'],
                "is_charging": bool(row['is_charging']),
                "last_updated": row['timestamp']
            } for row in latest_data
        ]
    })

# ========== EXISTING ROUTES ==========

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
        else:
            # Create parent if not exists
            parent_id = "parent-main-123"
            conn = get_db_connection()
            cursor = conn.cursor()
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
        # Create parent if not exists
        parent_id = "parent-main-123"
        cursor.execute(
            "INSERT INTO parents (id, email, password, created_at) VALUES (?, ?, ?, ?)",
            (parent_id, FIXED_USERNAME, FIXED_PASSWORD, datetime.now().isoformat())
        )
        conn.commit()
    else:
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
    
    print(f"New device registered: {child_name} - {device_model} - {device_id} for parent: {parent_id}")
    
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
    
    child_id = "child-" + str(uuid.uuid4())
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

# DEBUG ENDPOINTS
@app.route('/debug/children', methods=['GET'])
def debug_children():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all children
    cursor.execute("SELECT * FROM children")
    children = cursor.fetchall()
    
    # Get all parents
    cursor.execute("SELECT * FROM parents")
    parents = cursor.fetchall()
    
    conn.close()
    
    children_list = []
    for child in children:
        children_list.append({
            "id": child['id'],
            "name": child['name'],
            "device_id": child['device_id'],
            "device_model": child['device_model'],
            "parent_id": child['parent_id'],
            "is_blocked": bool(child['is_blocked']),
            "created_at": child['created_at']
        })
    
    parents_list = []
    for parent in parents:
        parents_list.append({
            "id": parent['id'],
            "email": parent['email'],
            "created_at": parent['created_at']
        })
    
    return jsonify({
        "parents": parents_list,
        "children": children_list,
        "total_children": len(children_list),
        "total_parents": len(parents_list)
    })

@app.route('/debug/add_test_device', methods=['POST'])
def add_test_device():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get or create parent
    cursor.execute("SELECT id FROM parents WHERE email = ?", (FIXED_USERNAME,))
    parent = cursor.fetchone()
    
    if not parent:
        parent_id = "parent-main-123"
        cursor.execute(
            "INSERT INTO parents (id, email, password, created_at) VALUES (?, ?, ?, ?)",
            (parent_id, FIXED_USERNAME, FIXED_PASSWORD, datetime.now().isoformat())
        )
    else:
        parent_id = parent['id']
    
    # Add test device
    device_id = "test-device-" + str(uuid.uuid4())
    child_id = "child-" + str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO children (id, parent_id, name, device_id, device_model, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (child_id, parent_id, "Test Device", device_id, "Test Phone", datetime.now().isoformat())
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": "Test device added successfully",
        "child_id": child_id,
        "device_id": device_id,
        "parent_id": parent_id
    })

@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        "status": "Backend is working!", 
        "timestamp": datetime.now().isoformat(),
        "parent_username": FIXED_USERNAME,
        "parent_password": FIXED_PASSWORD
    })

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
            "username": FIXED_USERNAME,
            "password": FIXED_PASSWORD
        },
        "endpoints": {
            "auto_register": "/child/auto_register",
            "parent_login": "/parent/login",
            "get_children": "/parent/children/{parent_id}",
            "block_child": "/child/block",
            "log_usage": "/usage/log",
            "check_status": "/child/status/{device_id}",
            "debug_info": "/debug/children",
            "add_test": "/debug/add_test_device",
            # BATTERY ENDPOINTS
            "battery_all": "/battery",
            "battery_device": "/battery/{device_id}",
            "battery_update": "/battery/update",
            "battery_history": "/battery/history/{device_id}",
            "battery_stats": "/battery/stats",
            # CAMERA ENDPOINTS
            "camera_main": "/camera",
            "camera_control": "/camera/control",
            "camera_status": "/camera/status/{device_id}",
            "camera_commands": "/camera/commands/{device_id}",
            "camera_service": "/camera/status"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
