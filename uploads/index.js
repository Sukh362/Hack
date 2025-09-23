import express from "express";
import bodyParser from "body-parser";
import fs from "fs";
import path from "path";
import cors from "cors";

const app = express();
app.use(cors());
app.use(bodyParser.json({ limit: "10mb" })); // for large image data

// Folder to save images
const UPLOAD_DIR = path.join(".", "uploads");
if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR);

// ✅ Receive front camera image from child app
app.post("/api/upload/frontcamera", (req, res) => {
    const { deviceId, imageBase64 } = req.body;
    if (!deviceId || !imageBase64) return res.status(400).json({ error: "Missing data" });

    const filename = `${deviceId}_front_${Date.now()}.jpg`;
    const filepath = path.join(UPLOAD_DIR, filename);

    // Save base64 as file
    const data = imageBase64.replace(/^data:image\/\w+;base64,/, "");
    const buffer = Buffer.from(data, "base64");
    fs.writeFile(filepath, buffer, (err) => {
        if (err) return res.status(500).json({ error: "Failed to save image" });
        console.log(`Saved front camera image: ${filename}`);
        res.json({ success: true, filename });
    });
});

// ✅ Serve latest uploaded image for a device
app.get("/api/frontcamera/:deviceId/latest", (req, res) => {
    const files = fs.readdirSync(UPLOAD_DIR)
        .filter(f => f.startsWith(req.params.deviceId + "_front_"))
        .sort()
        .reverse(); // latest first

    if (files.length === 0) return res.status(404).json({ error: "No image found" });

    res.sendFile(path.join(UPLOAD_DIR, files[0]));
});

// ✅ Home route
app.get("/", (req, res) => {
    res.send("Front Camera Upload Server Running 🚀");
});

app.listen(4000, () => console.log("Server running on port 4000"));
