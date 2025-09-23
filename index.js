const express = require("express");
const app = express();
const bodyParser = require("body-parser");
const path = require("path");

app.use(bodyParser.json());
app.use(express.static("public"));

// Mock database (memory ke andar store karne ke liye)
let devices = {};

// Device status fetch route
app.get("/api/device/:id/status", (req, res) => {
    const deviceId = req.params.id;
    if (devices[deviceId]) {
        res.json(devices[deviceId]);
    } else {
        res.status(404).json({ error: "Device not found" });
    }
});

// Camera trigger route
app.post("/api/device/:id/camera-trigger", (req, res) => {
    const deviceId = req.params.id;
    if (!devices[deviceId]) {
        devices[deviceId] = {};
    }

    // For now, dummy image URL return karte hain
    devices[deviceId].lastImage = "https://via.placeholder.com/300x200.png?text=Captured+Image";

    res.json({
        success: true,
        message: "Camera triggered successfully",
        imageUrl: devices[deviceId].lastImage
    });
});

// Latest image fetch
app.get("/api/device/:id/image", (req, res) => {
    const deviceId = req.params.id;
    if (devices[deviceId] && devices[deviceId].lastImage) {
        res.json({ imageUrl: devices[deviceId].lastImage });
    } else {
        res.status(404).json({ error: "No image found" });
    }
});

// Default route
app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "public", "index.html"));
});

// Start server
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    console.log(`✅ Server running on port ${PORT}`);
});
