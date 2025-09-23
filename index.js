import express from "express";
import bodyParser from "body-parser";
import cors from "cors";

const app = express();
app.use(cors());
app.use(bodyParser.json());

let devices = {}; // device info storage
let cameraImages = {}; // store latest camera image (base64)

// ✅ Update device battery/location/status
app.post("/api/device/update", (req, res) => {
  const { deviceId, battery, location, status } = req.body;
  devices[deviceId] = { battery, location, status, lastUpdate: new Date(), cameraImage: cameraImages[deviceId] || null };
  res.json({ success: true, device: devices[deviceId] });
});

// ✅ Get device data
app.get("/api/device/:id", (req, res) => {
  const device = devices[req.params.id];
  if (!device) return res.status(404).json({ error: "Device not found" });
  res.json(device);
});

// ✅ Camera upload endpoint
app.post("/api/frontcamera/upload", (req, res) => {
  const { deviceId, imageBase64 } = req.body;
  cameraImages[deviceId] = imageBase64;
  if (devices[deviceId]) devices[deviceId].cameraImage = imageBase64;
  console.log("Camera image received for device", deviceId);
  res.json({ success: true });
});

// ✅ Camera trigger from web panel
app.post("/api/device/camera-trigger", (req, res) => {
  const { deviceId } = req.body;
  // Mark a flag or push a notification to the child app (simple polling can check this)
  if (!devices[deviceId]) devices[deviceId] = {};
  devices[deviceId].cameraTrigger = true;
  console.log("Camera trigger requested for device", deviceId);
  res.json({ success: true });
});

// ✅ Child app polling endpoint to check camera trigger
app.get("/api/device/:id/camera-trigger", (req, res) => {
  const deviceId = req.params.id;
  const trigger = devices[deviceId]?.cameraTrigger || false;
  if (trigger) devices[deviceId].cameraTrigger = false; // reset after polling
  res.json({ trigger });
});

// ✅ Home route
app.get("/", (req, res) => {
  res.send("Child Monitoring Server Running 🚀");
});

app.listen(3000, () => console.log("Server running on port 3000"));
