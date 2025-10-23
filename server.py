from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory, render_template_string
import os
import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecret"

# Hardcoded admin (quick). You can switch to env vars later.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "guard123"

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Use the template file from templates/dashboard.html
@app.route('/')
def index():
    if 'logged_in' in session:
        # prepare list of files with sizes
        files = []
        for fname in sorted(os.listdir(UPLOAD_FOLDER), reverse=True):
            fpath = os.path.join(UPLOAD_FOLDER, fname)
            if os.path.isfile(fpath):
                files.append({'name': fname, 'size': os.path.getsize(fpath)})
        # render a template that expects 'files' as list of dicts
        # we'll use a small helper template loader calling render_template directly
        # but our provided dashboard.html expects plain filenames; adjust to pass names only
        return render_template('dashboard.html', files=[f['name'] for f in files], os=os)
    else:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

# serve file for playback and download
@app.route('/file/<path:filename>')
def serve_file(filename):
    # If you want to require login to play, uncomment the next lines:
    # if 'logged_in' not in session:
    #     return redirect(url_for('login'))
    # sanitize filename
    safe = secure_filename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe, as_attachment=False)

# delete route (POST)
@app.route('/delete/<path:filename>', methods=['POST'])
def delete_file(filename):
    if 'logged_in' not in session:
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

# upload endpoint (expects header X-API-KEY or you can keep it open)
@app.route('/upload', methods=['POST'])
def upload():
    # optional API key check (if you set API_KEY env)
    api_key = os.getenv("API_KEY")
    if api_key:
        if request.headers.get("X-API-KEY") != api_key:
            return {"ok": False, "error": "unauthorized"}, 401

    f = request.files.get('file')
    if not f:
        return {"ok": False, "error": "no file"}, 400

    filename = secure_filename(f.filename) or "recording.m4a"
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name = f"{ts}_{filename}"
    save_path = os.path.join(UPLOAD_FOLDER, name)
    f.save(save_path)
    print("Saved:", save_path)
    return {"ok": True, "path": save_path}, 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
