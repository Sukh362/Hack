// index.js
const express = require("express");
const bodyParser = require("body-parser");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;

// Use JSON parser
app.use(bodyParser.json({ limit: "50mb" }));

// Serve static uploads
app.use("/uploads", express.static(path.join(__dirname, "uploads")));

// In-memory device data
let devices = {};

// Ensure uploads folder exists
const uploadsDir = path.join(__dirname, "uploads");
if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir);

// Route: Update battery/location/status
app.post("/api/device/update", (req, res) => {
    const { deviceId, battery, location, status } = req.body;
    if (!deviceId) return res.status(400).json({ error: "Missing deviceId" });

    devices[deviceId] = {
        battery: battery || "Unknown",
        location: location || "Not fetched",
        status: status || "offline",
        lastUpdate: new Date(),
        cameraImage: devices[deviceId] ? devices[deviceId].cameraImage : null
    };

    console.log(`Updated device ${deviceId}: battery=${battery}, location=${location}, status=${status}`);
    return res.json({ success: true });
});

// Route: Upload front camera image
app.post("/api/frontcamera/upload", (req, res) => {
    const { deviceId, imageBase64 } = req.body;
    if (!deviceId || !imageBase64) return res.status(400).json({ error: "Missing deviceId or imageBase64" });

    // Save image
    const imageBuffer = Buffer.from(imageBase64, "base64");
    const filename = `${deviceId}_${Date.now()}.jpg`;
    const filepath = path.join(uploadsDir, filename);
    fs.writeFileSync(filepath, imageBuffer);

    // Update device info
    if (!devices[deviceId]) devices[deviceId] = {};
    devices[deviceId].cameraImage = imageBase64;
    console.log(`Camera image received from ${deviceId}: ${filename}`);

    return res.json({ success: true, filename });
});

// Route: Get device info
app.get("/api/device/:deviceId", (req, res) => {
    const { deviceId } = req.params;
    if (!devices[deviceId]) return res.status(404).json({ error: "Device not found" });
    return res.json(devices[deviceId]);
});

// Route: Web trigger camera
app.post("/api/device/camera-trigger", (req, res) => {
    const { deviceId } = req.body;
    if (!deviceId) return res.status(400).json({ error: "Missing deviceId" });

    console.log(`Camera trigger requested for device ${deviceId}`);
    // Note: actual camera capture happens on Android app
    return res.json({ success: true });
});

// Start server
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
