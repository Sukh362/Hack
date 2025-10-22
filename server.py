import os
import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string, redirect, url_for, session

app = Flask(__name__)

# Read secrets from env (set these in Render dashboard)
app.secret_key = os.getenv("SECRET_KEY", "changeme_local_secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "guard123")
API_KEY = os.getenv("API_KEY", "myapisecret")

# Upload folder inside instance (ephemeral)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Minimal templates (same as earlier but trimmed)
LOGIN_HTML = """..."""  # paste your previous LOGIN_HTML (or keep short)
DASHBOARD_HTML = """..."""  # paste previous DASHBOARD_HTML

# For brevity: use the full templates you already had earlier.
# -------------------- Authentication --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == ADMIN_USERNAME and pwd == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = "Invalid username or password"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper

@app.route('/')
@login_required
def index():
    files = []
    for fname in sorted(os.listdir(UPLOAD_FOLDER), reverse=True):
        path = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isfile(path):
            files.append({'name': fname, 'size': os.path.getsize(path)})
    return render_template_string(DASHBOARD_HTML, files=files)

@app.route('/file/<path:filename>')
@login_required
def get_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/delete/<path:filename>', methods=['POST'])
@login_required
def delete_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for('index'))

# Upload endpoint (accepts public uploads from app/web). Requires API_KEY header.
@app.route('/upload', methods=['POST'])
def upload():
    # simple API key check
    if request.headers.get("X-API-KEY") != API_KEY:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    f = request.files.get('file')
    if not f:
        return jsonify({'ok': False, 'error': 'no file provided'}), 400

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(f.filename)[-1] or ".m4a"
    safe_name = f"{ts}_recording{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, safe_name)
    f.save(save_path)
    print("Saved:", save_path)
    return jsonify({'ok': True, 'path': save_path}), 200

if __name__ == "__main__":
    # For local testing only
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
