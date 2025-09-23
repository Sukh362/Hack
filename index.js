const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json({ limit: "10mb" })); 
app.use(cors());

// In-memory DB
let devices = {};

// Update device data
app.post("/api/device/update", (req, res) => {
    const { deviceId, battery, location, status } = req.body;
    if (!deviceId) return res.status(400).json({ error: "Device ID required" });

    devices[deviceId] = devices[deviceId] || {};
    devices[deviceId].battery = battery;
    devices[deviceId].location = location;
    devices[deviceId].status = status;
    devices[deviceId].lastUpdate = Date.now();

    res.json({ success: true, device: devices[deviceId] });
});

// Fetch device data
app.get("/api/device/:deviceId", (req, res) => {
    const deviceId = req.params.deviceId;
    const device = devices[deviceId];
    if (!device) return res.status(404).json({ error: "Device not found" });

    res.json(device);
});

// Trigger front camera capture (set flag true)
app.post("/api/device/camera-trigger", (req, res) => {
    const { deviceId } = req.body;
    const device = devices[deviceId];
    if (!device) return res.status(404).json({ error: "Device not found" });

    device.captureFrontCamera = true;
    res.json({ success: true, message: "Camera trigger sent" });
});

// ✅ NEW: Get camera trigger status (for polling)
app.get("/api/device/:deviceId/camera-status", (req, res) => {
    const deviceId = req.params.deviceId;
    const device = devices[deviceId];
    if (!device) return res.status(404).json({ error: "Device not found" });

    res.json({ captureFrontCamera: device.captureFrontCamera || false });
});

// Upload front camera image
app.post("/api/frontcamera/upload", (req, res) => {
    const { deviceId, imageBase64 } = req.body;
    const device = devices[deviceId];
    if (!device) return res.status(404).json({ error: "Device not found" });

    device.cameraImage = imageBase64;
    device.captureFrontCamera = false;
    res.json({ success: true, message: "Camera image uploaded" });
});

// Start server
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
