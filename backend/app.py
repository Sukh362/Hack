from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime
import base64
import os
import json

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
    
    # Camera images table
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

# ========== DATA ROUTE (MAIN MOBILE DATA UPLOAD) ==========

@app.route('/data', methods=['POST', 'OPTIONS'])
def handle_mobile_data():
    """Main data upload endpoint for mobile app - handles all types of data"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        print(f"Mobile data received: {data}")
        
        device_id = data.get('device_id')
        data_type = data.get('type', 'unknown')
        
        if not device_id:
            return jsonify({"error": "Device ID is required"}), 400
        
        # Handle different types of data
        if data_type == 'camera_image':
            return handle_camera_image(data)
        elif data_type == 'battery':
            return handle_battery_data(data)
        elif data_type == 'usage':
            return handle_usage_data(data)
        elif data_type == 'device_info':
            return handle_device_info(data)
        else:
            return jsonify({"error": "Unknown data type"}), 400
            
    except Exception as e:
        print(f"Error in /data route: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def handle_camera_image(data):
    """Handle camera image upload from mobile app"""
    device_id = data.get('device_id')
    image_data = data.get('image_data')
    image_type = data.get('image_type', 'jpg')
    
    if not image_data:
        return jsonify({"error": "Image data is required"}), 400
    
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

def handle_battery_data(data):
    """Handle battery data upload from mobile app"""
    device_id = data.get('device_id')
    battery_level = data.get('battery_level')
    
    if battery_level is None:
        return jsonify({"error": "Battery level is required"}), 400
    
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
    
    # Insert battery data
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

def handle_usage_data(data):
    """Handle usage data upload from mobile app"""
    device_id = data.get('device_id')
    app_name = data.get('app_name')
    duration = data.get('duration')
    
    if not app_name or duration is None:
        return jsonify({"error": "App name and duration are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get child_id from device_id
    cursor.execute("SELECT id FROM children WHERE device_id = ?", (device_id,))
    child = cursor.fetchone()
    
    if not child:
        conn.close()
        return jsonify({"error": "Device not registered"}), 404
    
    # Insert usage log
    log_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO usage_logs (id, child_id, app_name, duration, timestamp) VALUES (?, ?, ?, ?, ?)",
        (log_id, child['id'], app_name, duration, datetime.now().isoformat())
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Usage logged successfully"})

def handle_device_info(data):
    """Handle device information upload from mobile app"""
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
        "message": "Device registered successfully", 
        "child_id": child_id,
        "parent_id": parent_id,
        "device_id": device_id,
        "device_model": device_model,
        "child_name": child_name
    })

# ========== CAMERA ROUTES (FOR PARENT WEB INTERFACE) ==========

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

# ========== EXISTING BATTERY ROUTES (SAME AS BEFORE) ==========

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

# ========== EXISTING OTHER ROUTES (SAME AS BEFORE) ==========

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

# ... (rest of your existing routes remain the same)

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
            "main_data_upload": "/data",
            "parent_login": "/parent/login",
            "get_children": "/parent/children/{parent_id}",
            "block_child": "/child/block",
            "check_status": "/child/status/{device_id}",
            # BATTERY ENDPOINTS
            "battery_all": "/battery",
            "battery_device": "/battery/{device_id}",
            "battery_history": "/battery/history/{device_id}",
            "battery_stats": "/battery/stats",
            # CAMERA ENDPOINTS
            "camera_images": "/camera/images/{device_id}",
            "camera_image": "/camera/image/{image_id}",
            "camera_latest": "/camera/latest/{device_id}",
            "camera_delete": "/camera/delete/{image_id}",
            "camera_devices": "/camera/devices"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
