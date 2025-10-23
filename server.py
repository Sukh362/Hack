from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
import os

app = Flask(__name__)
app.secret_key = "supersecret"

# hardcoded login credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "guard123"

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    if 'logged_in' in session:
        files = os.listdir(UPLOAD_FOLDER)
        return render_template('dashboard.html', files=files)
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
