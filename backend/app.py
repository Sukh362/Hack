from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime
import base64
import os

app = Flask(__name__)

# CORS setup for all origins and methods
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])

# Fixed parent credentials
FIXED_USERNAME = "Sukh"
FIXED_PASSWORD = "Sukh hacker"

# Create uploads directory for camera images
UPLOAD_FOLDER = 'camera_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
    
    # NEW: Camera images table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS camera_images (
            id TEXT PRIMARY KEY,
            device_id TEXT,
            image_path TEXT,
            image_type TEXT,
            timestamp TEXT,
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

@app.route('/camera', methods=['POST', 'OPTIONS'])
def upload_camera_image():
    """Upload camera image from mobile app"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        print(f"Camera image upload received from device: {data.get('device_id')}")
        
        device_id = data.get('device_id')
        image_data = data.get('image_data')
        image_type = data.get('image_type', 'jpg')
        
        if not device_id or not image_data:
            return jsonify({"error": "Device ID and image data are required"}), 400
        
        # Check if device exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM children WHERE device_id = ?", (device_id,))
        device = cursor.fetchone()
        
        if not device:
            conn.close()
            return jsonify({"error": "Device not registered"}), 404
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"camera_{device_id}_{timestamp}.{image_type}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save image file
        try:
            # Decode base64 image data
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
        except Exception as e:
            print(f"Error saving image: {str(e)}")
            conn.close()
            return jsonify({"error": "Failed to save image"}), 500
        
        # Save to database
        image_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO camera_images (id, device_id, image_path, image_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (image_id, device_id, filepath, image_type, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"Camera image saved successfully for device {device_id}: {filename}")
        
        return jsonify({
            "message": "Camera image uploaded successfully",
            "image_id": image_id,
            "filename": filename,
            "device_id": device_id,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in camera upload: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/camera/images/<device_id>', methods=['GET'])
def get_camera_images(device_id):
    """Get all camera images for a specific device"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM camera_images 
        WHERE device_id = ? 
        ORDER BY timestamp DESC
        LIMIT 50
    ''', (device_id,))
    
    images = cursor.fetchall()
    conn.close()
    
    images_list = []
    for image in images:
        # Check if file exists
        file_exists = os.path.exists(image['image_path'])
        
        images_list.append({
            "id": image['id'],
            "device_id": image['device_id'],
            "image_path": image['image_path'],
            "filename": os.path.basename(image['image_path']),
            "image_type": image['image_type'],
            "timestamp": image['timestamp'],
            "file_exists": file_exists
        })
    
    return jsonify({
        "device_id": device_id,
        "total_images": len(images_list),
        "images": images_list
    })

@app.route('/camera/image/<image_id>', methods=['GET'])
def get_camera_image(image_id):
    """Get specific camera image data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM camera_images WHERE id = ?
    ''', (image_id,))
    
    image = cursor.fetchone()
    conn.close()
    
    if not image:
        return jsonify({"error": "Image not found"}), 404
    
    # Check if file exists
    if not os.path.exists(image['image_path']):
        return jsonify({"error": "Image file not found"}), 404
    
    # Read and encode image
    try:
        with open(image['image_path'], 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        return jsonify({
            "id": image['id'],
            "device_id": image['device_id'],
            "image_data": f"data:image/{image['image_type']};base64,{image_data}",
            "image_type": image['image_type'],
            "timestamp": image['timestamp'],
            "filename": os.path.basename(image['image_path'])
        })
    except Exception as e:
        return jsonify({"error": "Failed to read image file"}), 500

@app.route('/camera/latest/<device_id>', methods=['GET'])
def get_latest_camera_image(device_id):
    """Get latest camera image for a device"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM camera_images 
        WHERE device_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (device_id,))
    
    image = cursor.fetchone()
    conn.close()
    
    if not image:
        return jsonify({"error": "No images found for this device"}), 404
    
    # Check if file exists
    if not os.path.exists(image['image_path']):
        return jsonify({"error": "Image file not found"}), 404
    
    # Read and encode image
    try:
        with open(image['image_path'], 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        return jsonify({
            "id": image['id'],
            "device_id": image['device_id'],
            "image_data": f"data:image/{image['image_type']};base64,{image_data}",
            "image_type": image['image_type'],
            "timestamp": image['timestamp'],
            "filename": os.path.basename(image['image_path'])
        })
    except Exception as e:
        return jsonify({"error": "Failed to read image file"}), 500

@app.route('/camera/delete/<image_id>', methods=['DELETE'])
def delete_camera_image(image_id):
    """Delete a camera image"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM camera_images WHERE id = ?', (image_id,))
    image = cursor.fetchone()
    
    if not image:
        conn.close()
        return jsonify({"error": "Image not found"}), 404
    
    # Delete file
    file_deleted = False
    if os.path.exists(image['image_path']):
        try:
            os.remove(image['image_path'])
            file_deleted = True
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
    
    # Delete database record
    cursor.execute('DELETE FROM camera_images WHERE id = ?', (image_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": "Camera image deleted successfully",
        "image_id": image_id,
        "file_deleted": file_deleted,
        "filename": os.path.basename(image['image_path'])
    })

@app.route('/camera/devices', methods=['GET'])
def get_camera_devices():
    """Get list of all devices that have uploaded camera images"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT c.device_id, c.name, COUNT(ci.id) as image_count,
               MAX(ci.timestamp) as last_upload
        FROM children c
        LEFT JOIN camera_images ci ON c.device_id = ci.device_id
        GROUP BY c.device_id, c.name
        HAVING COUNT(ci.id) > 0
        ORDER BY last_upload DESC
    ''')
    
    devices = cursor.fetchall()
    conn.close()
    
    devices_list = []
    for device in devices:
        devices_list.append({
            "device_id": device['device_id'],
            "device_name": device['name'],
            "image_count": device['image_count'],
            "last_upload": device['last_upload']
        })
    
    return jsonify({
        "total_devices": len(devices_list),
        "devices": devices_list
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
    
    # Get camera images count
    cursor.execute("SELECT device_id, COUNT(*) as image_count FROM camera_images GROUP BY device_id")
    camera_counts = cursor.fetchall()
    
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
    
    camera_info = {}
    for count in camera_counts:
        camera_info[count['device_id']] = count['image_count']
    
    return jsonify({
        "parents": parents_list,
        "children": children_list,
        "camera_images": camera_info,
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
            # NEW CAMERA ENDPOINTS
            "camera_upload": "/camera",
            "camera_images": "/camera/images/{device_id}",
            "camera_image": "/camera/image/{image_id}",
            "camera_latest": "/camera/latest/{device_id}",
            "camera_delete": "/camera/delete/{image_id}",
            "camera_devices": "/camera/devices"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
