const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Middleware
app.use(cors());
app.use(express.json());
app.use('/uploads', express.static('uploads'));
app.use(express.static('public'));

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads', { recursive: true });
}

// Multer configuration for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const deviceId = req.body.deviceId || 'unknown';
    const devicePath = path.join('uploads', deviceId);
    
    if (!fs.existsSync(devicePath)) {
      fs.mkdirSync(devicePath, { recursive: true });
    }
    
    cb(null, devicePath);
  },
  filename: (req, file, cb) => {
    const timestamp = Date.now();
    const fileExtension = path.extname(file.originalname);
    cb(null, `${file.fieldname}-${timestamp}${fileExtension}`);
  }
});

const upload = multer({ 
  storage: storage,
  limits: {
    fileSize: 50 * 1024 * 1024 // 50MB limit
  }
});

// In-memory storage for devices and commands
const connectedDevices = new Map();
const deviceCommands = new Map();

// Routes

// Serve web panel
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Get all connected devices
app.get('/api/devices', (req, res) => {
  const devices = Array.from(connectedDevices.values());
  res.json({ success: true, devices });
});

// Send command to device
app.post('/api/command', (req, res) => {
  const { deviceId, command, parameters } = req.body;
  
  if (!deviceId || !command) {
    return res.status(400).json({ 
      success: false, 
      message: 'Device ID and command are required' 
    });
  }

  if (!connectedDevices.has(deviceId)) {
    return res.status(404).json({ 
      success: false, 
      message: 'Device not connected' 
    });
  }

  // Store command for device
  if (!deviceCommands.has(deviceId)) {
    deviceCommands.set(deviceId, []);
  }

  const commandData = {
    id: Date.now().toString(),
    command,
    parameters,
    timestamp: new Date().toISOString(),
    status: 'pending'
  };

  deviceCommands.get(deviceId).push(commandData);

  // Send command via socket
  io.to(deviceId).emit('command', commandData);

  res.json({ 
    success: true, 
    message: 'Command sent successfully',
    command: commandData
  });
});

// File upload endpoint
app.post('/api/upload', upload.single('media'), (req, res) => {
  try {
    const { deviceId, fileType, commandId } = req.body;
    const file = req.file;

    if (!file) {
      return res.status(400).json({ 
        success: false, 
        message: 'No file uploaded' 
      });
    }

    // Update command status if commandId provided
    if (commandId && deviceId && deviceCommands.has(deviceId)) {
      const commands = deviceCommands.get(deviceId);
      const command = commands.find(cmd => cmd.id === commandId);
      if (command) {
        command.status = 'completed';
        command.result = {
          fileUrl: `/uploads/${deviceId}/${file.filename}`,
          fileName: file.filename,
          fileType: fileType
        };
      }
    }

    res.json({
      success: true,
      message: 'File uploaded successfully',
      file: {
        filename: file.filename,
        originalname: file.originalname,
        size: file.size,
        url: `/uploads/${deviceId}/${file.filename}`
      }
    });

  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Upload failed' 
    });
  }
});

// Get device files
app.get('/api/files/:deviceId', (req, res) => {
  const { deviceId } = req.params;
  const devicePath = path.join('uploads', deviceId);
  
  if (!fs.existsSync(devicePath)) {
    return res.json({ success: true, files: [] });
  }

  try {
    const files = fs.readdirSync(devicePath).map(filename => {
      const filePath = path.join(devicePath, filename);
      const stats = fs.statSync(filePath);
      
      return {
        filename,
        url: `/uploads/${deviceId}/${filename}`,
        size: stats.size,
        created: stats.birthtime,
        type: path.extname(filename)
      };
    });

    res.json({ success: true, files });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      message: 'Error reading files' 
    });
  }
});

// Socket.io for real-time communication
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  // Device registration
  socket.on('register-device', (deviceData) => {
    const deviceId = deviceData.deviceId || socket.id;
    
    connectedDevices.set(deviceId, {
      ...deviceData,
      socketId: socket.id,
      deviceId: deviceId,
      connectedAt: new Date().toISOString(),
      lastSeen: new Date().toISOString()
    });

    socket.join(deviceId);
    console.log(`Device registered: ${deviceId}`);

    // Notify all clients about new device
    io.emit('devices-updated', Array.from(connectedDevices.values()));
  });

  // Command response from device
  socket.on('command-response', (response) => {
    const { deviceId, commandId, success, message, data } = response;
    
    // Broadcast to all web panel clients
    io.emit('command-response', {
      deviceId,
      commandId,
      success,
      message,
      data,
      timestamp: new Date().toISOString()
    });
  });

  // Device status update
  socket.on('device-status', (status) => {
    const { deviceId, battery, storage, ...otherStatus } = status;
    
    if (connectedDevices.has(deviceId)) {
      const device = connectedDevices.get(deviceId);
      device.lastSeen = new Date().toISOString();
      device.status = { battery, storage, ...otherStatus };
    }

    io.emit('device-status-update', { deviceId, status });
  });

  socket.on('disconnect', () => {
    // Find and remove disconnected device
    for (let [deviceId, device] of connectedDevices.entries()) {
      if (device.socketId === socket.id) {
        connectedDevices.delete(deviceId);
        console.log(`Device disconnected: ${deviceId}`);
        
        // Notify all clients
        io.emit('devices-updated', Array.from(connectedDevices.values()));
        break;
      }
    }
  });
});

// Cleanup function
function cleanupOldFiles() {
  // This function can be implemented to clean up old files
  console.log('Cleanup function called');
}

// Schedule cleanup every hour
setInterval(cleanupOldFiles, 60 * 60 * 1000);

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📱 Web Panel: http://localhost:${PORT}`);
});
