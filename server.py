# Add this after your existing routes
import threading
import time

# Global variable to track recording signal
recording_signal = False
signal_listeners = []

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

# Update DASHBOARD_HTML template to include the button
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
    <!-- Your existing table content -->
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
          <form method="post" action="{{ url_for('delete_file', filename=f.name) }}" onsubmit="return confirm('Delete file\\n\\n' + '{{f.name}}' + '\\n\\nThis cannot be undone. Continue?')">
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
