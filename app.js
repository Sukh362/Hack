// Firebase Configuration
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "parentguard-app.firebaseapp.com",
    projectId: "parentguard-app",
    storageBucket: "parentguard-app.appspot.com",
    messagingSenderId: "123456789",
    appId: "YOUR_APP_ID"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

// Initialize Map
let map = L.map('map').setView([28.6139, 77.2090], 13); // Default to Delhi
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

let marker = L.marker([28.6139, 77.2090]).addTo(map)
    .bindPopup('Device Location')
    .openPopup();

// Charts
let appUsageChart, timeAnalysisChart;

function initCharts() {
    // App Usage Chart
    const appCtx = document.getElementById('appUsageChart').getContext('2d');
    appUsageChart = new Chart(appCtx, {
        type: 'doughnut',
        data: {
            labels: ['YouTube', 'Games', 'Browser', 'Social Media'],
            datasets: [{
                data: [45, 30, 15, 10],
                backgroundColor: ['#4361ee', '#f72585', '#4cc9f0', '#f8961e']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: 'white' }
                }
            }
        }
    });

    // Time Analysis Chart
    const timeCtx = document.getElementById('timeAnalysisChart').getContext('2d');
    timeAnalysisChart = new Chart(timeCtx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Screen Time (hours)',
                data: [3, 4, 2, 5, 3, 6, 4],
                borderColor: '#4361ee',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                x: {
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }
            }
        }
    });
}

// Fetch Data from Firestore
function fetchDashboardData() {
    db.collection("usageData").doc("current").get()
        .then((doc) => {
            if (doc.exists) {
                const data = doc.data();
                updateDashboard(data);
                updateCharts(data);
                updateMap(data.location);
            }
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
        });
}

function updateDashboard(data) {
    document.getElementById("screenTime").textContent = data.screenTime || "0h 0m";
    document.getElementById("totalApps").textContent = data.totalApps || "0";
    document.getElementById("blockedAttempts").textContent = data.blockedAttempts || "0";
    document.getElementById("alerts").textContent = data.alerts || "0";
    
    // Update app list
    if (data.apps && data.apps.length > 0) {
        let appListHTML = "";
        data.apps.forEach((app, index) => {
            appListHTML += `
                <div class="app-usage-item">
                    <div>
                        <h6 class="mb-0 text-white">${app.name}</h6>
                        <small class="text-white-50">${app.category || 'App'}</small>
                    </div>
                    <div class="text-end">
                        <span class="text-white">${app.time}</span>
                        <br>
                        <small class="text-white-50">${app.usage || '0%'} usage</small>
                    </div>
                </div>
            `;
        });
        document.getElementById("appList").innerHTML = appListHTML;
    }
    
    // Update refresh time
    document.getElementById("refreshTime").textContent = `Updated: ${new Date().toLocaleTimeString()}`;
}

function updateCharts(data) {
    // Update charts with real data
    if (data.chartData) {
        appUsageChart.data.datasets[0].data = data.chartData.appUsage;
        timeAnalysisChart.data.datasets[0].data = data.chartData.timeAnalysis;
        appUsageChart.update();
        timeAnalysisChart.update();
    }
}

function updateMap(location) {
    if (location && location.lat && location.lng) {
        map.setView([location.lat, location.lng], 13);
        marker.setLatLng([location.lat, location.lng]);
        document.getElementById("locationTime").textContent = new Date().toLocaleTimeString();
    }
}

// Event Listeners
document.getElementById("btnLockDevice").addEventListener("click", () => {
    if (confirm("Are you sure you want to lock the device?")) {
        // Send lock command to Firebase
        db.collection("commands").add({
            type: "lock_device",
            timestamp: new Date(),
            executed: false
        });
        showNotification("Device lock command sent!", "success");
    }
});

document.getElementById("btnSetLimit").addEventListener("click", () => {
    const limit = prompt("Enter daily time limit (hours):");
    if (limit && !isNaN(limit)) {
        db.collection("settings").doc("timeLimit").set({
            hours: parseInt(limit),
            lastUpdated: new Date()
        });
        showNotification(`Time limit set to ${limit} hours`, "info");
    }
});

// Initialize
initCharts();
fetchDashboardData();

// Real-time listener
db.collection("usageData").doc("current")
    .onSnapshot((doc) => {
        if (doc.exists) {
            const data = doc.data();
            updateDashboard(data);
            updateCharts(data);
            updateMap(data.location);
        }
    });

// Refresh every 30 seconds
setInterval(fetchDashboardData, 30000);

function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement("div");
    notification.className = `alert alert-${type} position-fixed`;
    notification.style.cssText = "top: 20px; right: 20px; z-index: 9999;";
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
        }
