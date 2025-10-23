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
    
    # List audio files
    files = []
    upload_dir = app.config['UPLOAD_FOLDER']
    try:
        for filename in os.listdir(upload_dir):
            if filename.endswith(('.m4a', '.mp3', '.wav', '.mp4')):
                filepath = os.path.join(upload_dir, filename)
                files.append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': os.path.getmtime(filepath)
                })
    except FileNotFoundError:
        os.makedirs(upload_dir, exist_ok=True)
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template_string(DASHBOARD_HTML, files=files)

# Recording signal routes
@app.route('/start-recording', methods=['POST'])
def start_recording():
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    
    global recording_signal
    recording_signal = True
    print("Recording signal activated")
    
    # Notify all listeners
    for listener in signal_listeners:
        listener['active'] = False  # Reset old listeners
    
    return jsonify({'ok': True, 'message': 'Recording signal sent to app'})

@app.route('/check-signal')
def check_signal():
    # This endpoint will be polled by Android app
    global recording_signal
    return jsonify({'record': recording_signal})

@app.route('/signal-received', methods=['POST'])
def signal_received():
    global recording_signal
    recording_signal = False  # Reset signal after app acknowledges
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
        # Add timestamp to avoid overwrites
        name, ext = os.path.splitext(filename)
        timestamp = str(int(time.time()))
        filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        return jsonify({'ok': True, 'message': 'Upload successful', 'filename': filename})
    
    return jsonify({'ok': False, 'error': 'Upload failed'}), 500

# MOBILE UPLOAD ROUTE - ANDROID APP KE LIYE
@app.route('/mobile-upload', methods=['POST'])
def mobile_upload():
    try:
        if 'audio' not in request.files:
            return jsonify({'ok': False, 'error': 'No audio file'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'ok': False, 'error': 'No file selected'}), 400
        
        # File save karo
        timestamp = str(int(time.time()))
        filename = f"android_recording_{timestamp}.m4a"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        print(f"✅ Mobile recording uploaded: {filename}")
        return jsonify({'ok': True, 'message': 'Upload successful', 'filename': filename})
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({'ok': False, 'error': 'Upload failed'}), 500

# LOGIN_HTML template
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

# DASHBOARD_HTML template
DASHBOARD_HTML = """
<!doctype html>
<title>Guard Recordings</title>
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
.signal-status{padding:8px 12px;border-radius:6px;margin-left:12px;font-size:14px}
.signal-active{background:#d4edda;color:#155724;border:1px solid #c3e6cb}
.signal-inactive{background:#f8d7da;color:#721c24;border:1px solid #f5c6cb}
a.logout{background:#6c757d;color:#fff;padding:8px 12px;border-radius:6px;text-decoration:none}
table{width:100%;border-collapse:collapse;margin-top:18px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 6px 18px rgba(16,24,40,.06)}
th,td{padding:12px 14px;border-bottom:1px solid #f1f5f9;text-align:left}
th{background:#0b74ff;color:#fff}
audio{width:240px}
.btn-small{padding:8px 10px;border-radius:6px;border:none;cursor:pointer;font-size:13px}
.btn-download{background:#eef6ff;color:#0b74ff;border:1px solid #d7ecff;text-decoration:none}
.btn-delete{background:#dc3545;color:#fff;border:1px solid rgba(0,0,0,.06)}
.small{font-size:13px;color:#666}
</style>
<div class="container">
  <header>
    <h1>🎧 Guard Recordings</h1>
    <div>
      <a class="logout" href="/logout" style="margin-right:12px">Logout</a>
      <a href="/recorder" class="btn-recorder btn-small">Recorder</a>
    </div>
  </header>
  
  <div class="controls">
    <button class="btn btn-start" onclick="startRecording()">📱 Start Recording Signal</button>
    <button class="btn btn-stop" onclick="stopRecording()">⏹️ Stop Signal</button>
    <span id="signalStatus" class="signal-status signal-inactive">Signal: Inactive</span>
  </div>
  
  <p class="small">Total files: <strong>{{ files|length }}</strong></p>

  <table>
    <thead>
      <tr><th>Filename</th><th>Size (KB)</th><th>Play</th><th>Download</th><th>Delete</th></tr>
    </thead>
    <tbody>
    {% for f in files %}
      <tr>
        <td style="max-width:320px;word-break:break-all">{{ f.name }}</td>
        <td class="small">{{ '%.1f'|format(f.size / 1024) }}</td>
        <td><audio controls preload="none"><source src="{{ url_for('serve_file', filename=f.name) }}" type="audio/mp4"></audio></td>
        <td><a class="btn-small btn-download" href="{{ url_for('serve_file', filename=f.name) }}" download>⬇️ Download</a></td>
        <td>
          <form method="post" action="{{ url_for('delete_file', filename=f.name) }}" onsubmit="return confirm('Delete file\\\\n\\\\n' + '{{f.name}}' + '\\\\n\\\\nThis cannot be undone. Continue?')">
            <button class="btn-small btn-delete" type="submit">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    {% if files|length == 0 %}
      <tr><td colspan="5" class="small">No recordings yet.</td></tr>
    {% endif %}
    </tbody>
  </table>
</div>

<script>
let signalCheckInterval;

function startRecording() {
    fetch('/start-recording', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
        if(data.ok) {
            document.getElementById('signalStatus').className = 'signal-status signal-active';
            document.getElementById('signalStatus').textContent = 'Signal: Active';
            
            // Start checking if signal was received by app
            signalCheckInterval = setInterval(checkSignalStatus, 2000);
            
            setTimeout(() => {
                stopRecording();
            }, 30000); // Auto stop after 30 seconds
        }
    })
    .catch(err => console.error('Error:', err));
}

function stopRecording() {
    if(signalCheckInterval) {
        clearInterval(signalCheckInterval);
    }
    document.getElementById('signalStatus').className = 'signal-status signal-inactive';
    document.getElementById('signalStatus').textContent = 'Signal: Inactive';
}

function checkSignalStatus() {
    fetch('/check-signal')
    .then(r => r.json())
    .then(data => {
        if(!data.record) {
            // Signal was received by app, reset UI
            stopRecording();
        }
    });
}
</script>
"""

# RECORDER_HTML template
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
        
        // Setup audio visualization
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
        
        // Stop all tracks
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