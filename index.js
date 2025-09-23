import express from "express";
import bodyParser from "body-parser";

const app = express();
app.use(bodyParser.json());

let devices = {}; // temporary memory (later DB add karenge)

// ✅ Update device data
app.post("/api/device/update", (req, res) => {
  const { deviceId, battery, location, status } = req.body;
  devices[deviceId] = { battery, location, status, lastUpdate: new Date() };
  res.json({ success: true, device: devices[deviceId] });
});

// ✅ Get device data
app.get("/api/device/:id", (req, res) => {
  const device = devices[req.params.id];
  if (!device) return res.status(404).json({ error: "Device not found" });
  res.json(device);
});

// ✅ Home Route
app.get("/", (req, res) => {
  res.send("Child Monitoring Server Running 🚀");
});

app.listen(3000, () => {
  console.log("Server running on port 3000");
});
