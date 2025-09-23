const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json({ limit: "10mb" })); // large base64 image
app.use(cors());

// In-memory "database"
let devices = {}; 
/*
devices = {
  "12345": {
      battery: "90%",
      location: "28.7,77.1",
      status: "online",
      lastUpdate: Date.now(),
      cameraImage: "base64string",
      captureFrontCamera: false
  }
}
*/

// Update device data (battery, location, status)
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

// Trigger front camera capture
app.post("/api/device/camera-trigger", (req, res) => {
    const { deviceId } = req.body;
    const device = devices[deviceId];
    if (!device) return res.status(404).json({ error: "Device not found" });

    device.captureFrontCamera = true; // app will detect and send pic
    res.json({ success: true, message: "Camera trigger sent" });
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
