# server.py
import os
import datetime
from flask import (
    Flask, request, jsonify, redirect, url_for,
    session, send_from_directory, render_template_string
)
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder=None)  # static served via routes below
app.secret_key = os.getenv("SECRET_KEY", "changeme_local_secret")

# Config (prefer setting these as environment variables on Render)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "guard123")
API_KEY = os.getenv("API_KEY", "")  # if empty -> upload accepts without API key

# Upload folder (ephemeral on Render; use S3 for persistence)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- Templates (embedded) ----------------
LOGIN_HTML = """
<!doctype html>
<title>Login - Guard</title>
<style>body{font-family:Arial;padding:24px;background:#f4f6fb}form{max-width:360px;margin:80px auto;padding:20px;background:#fff;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.06)}</style>
<form method="post">
  <h2 style="margin:0 0 12px">Guard Panel — Login</h2>
  {% if error %}<p style="color:red">{{error}}</p>{% endif %}
  <input name="username" placeholder="Username" style="width:100%;padding:10px;margin:6px 0" required autofocus>
  <input type="password" name="password" placeholder="Password" style="width:100%;padding:10px;margin:6px 0" required>
  <button style="width:100%;padding:10px;margin-top:8px;background:#0b74ff;color:#fff;border:none;border-radius:6px">Login</button>
</form>
"""

DASHBOARD_HTML = """
<!doctype html>
<title>Guard Recordings</title>
<style>
body{font-family:Inter,Arial;padding:20px;background:#f6f8fb;color:#111}
.container{max-width:1100px;margin:0 auto}
header{display:flex;justify-content:space-between;align-items:center}
h1{color:#0b74ff;margin:0}
a.logout{background:#dc3545;color:#fff;padding:8px 12px;border-radius:6px;text-decoration:none}
table{width:100%;border-collapse:collapse;margin-top:18px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 6px 18px rgba(16,24,40,.06)}
th,td{padding:12px 14px;border-bottom:1px solid #f1f5f9;text-align:left}
th{background:#0b74ff;color:#fff}
audio{width:240px}
.btn{padding:8px 10px;border-radius:6px;border:none;cursor:pointer}
.btn-download{background:#eef6ff;color:#0b74ff;border:1px solid #d7ecff;text-decoration:none}
.btn-delete{background:#dc3545;color:#fff;border:1px solid rgba(0,0,0,.06)}
.small{font-size:13px;color:#666}
</style>
<div class="container">
  <header>
    <h1>🎧 Guard Recordings</h1>
    <div>
      <a class="small" href="/logout" style="margin-right:12px">Logout</a>
      <a href="/recorder" class="small">Recorder</a>
    </div>
  </header>
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
        <td><a class="btn btn-download" href="{{ url_for('serve_file', filename=f.name) }}" download>⬇️ Download</a></td>
        <td>
          <form method="post" action="{{ url_for('delete_file', filename=f.name) }}" onsubmit="return confirm('Delete file\\n\\n' + '{{f.name}}' + '\\n\\nThis cannot be undone. Continue?')">
            <button class="btn btn-delete" type="submit">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    {% if files|length == 0 %}
      <tr><td colspan="5" class="small">No recordings yet.</td></tr>
    {% endif %}
    </tbody>
  </table>
  <p class="small" style="margin-top:12px">Use <code>/recorder</code> to record & upload from a browser or set your app's upload URL to <code>/upload</code>.</p>
</div>
"""

RECORDER_HTML = """
<!doctype html>
<title>Recorder — Guard</title>
<style>body{font-family:Arial;padding:20px;background:#f4f6fb}button{padding:12px 18px;font-size:16px}#status{margin-top:12px}</style>
<h2>Record 15s & Upload</h2>
<p>Allows browser recording (mobile supported). You will be prompted for API key before upload.</p>
<button id="rec">Record 15s</button>
<p id="status"></p>
<script>
const btn=document.getElementById('rec'), status=document.getElementById('status');
btn.onclick = async function(){
  status.innerText = 'Requesting microphone...';
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.start();
    status.innerText = 'Recording 15s...';
    setTimeout(()=> recorder.stop(), 15000);
    recorder.onstop = async () => {
      status.innerText = 'Uploading...';
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const fd = new FormData(); fd.append('file', blob, 'rec.webm');
      const key = prompt('Enter upload API key: (required)');
      if(!key){ status.innerText='Upload cancelled'; return; }
      try {
        const res = await fetch('/upload', { method:'POST', body: fd, headers: { 'X-API-KEY': key } });
        const j = await res.json();
        if(j.ok) status.innerText = 'Uploaded: ' + j.path;
        else status.innerText = 'Upload failed: ' + (j.error || JSON.stringify(j));
      } catch(err) { status.innerText = 'Upload error: ' + err.message; }
    };
  } catch(err) {
    status.innerText = 'Microphone error: ' + err.message;
  }
};
</script>
"""

# ---------------- Utility ----------------
def get_uploads():
    files = []
    for fname in sorted(os.listdir(UPLOAD_FOLDER), reverse=True):
        path = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isfile(path):
            files.append({'name': fname, 'size': os.path.getsize(path)})
    return files

# ---------------- Routes ----------------
@app.route('/')
def index():
    if session.get('logged_in'):
        return render_template_string(DASHBOARD_HTML, files=get_uploads())
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    err = None
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        err = "Invalid credentials"
    return render_template_string(LOGIN_HTML, error=err)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/recorder')
def recorder():
    # serve embedded recorder page
    return render_template_string(RECORDER_HTML)

@app.route('/upload', methods=['POST'])
def upload():
    # API key check if configured
    if API_KEY:
        if request.headers.get('X-API-KEY') != API_KEY:
            return jsonify({'ok': False, 'error': 'unauthorized (bad API key)'}), 401

    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'no file part'}), 400

    f = request.files['file']
    if not f or f.filename == '':
        return jsonify({'ok': False, 'error': 'empty filename'}), 400

    original = secure_filename(f.filename)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name = f"{ts}_{original}"
    path = os.path.join(UPLOAD_FOLDER, name)
    f.save(path)
    print("Saved:", path)
    return jsonify({'ok': True, 'path': f"/file/{name}"}), 200

@app.route('/file/<path:filename>')
def serve_file(filename):
    safe = secure_filename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe, as_attachment=False)

@app.route('/delete/<path:filename>', methods=['POST'])
def delete_file(filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    safe = secure_filename(filename)
    path = os.path.join(UPLOAD_FOLDER, safe)
    if os.path.exists(path):
        try:
            os.remove(path)
            print("Deleted:", path)
        except Exception as e:
            print("Delete error:", e)
    return redirect(url_for('index'))


# ---------------- Run ----------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
