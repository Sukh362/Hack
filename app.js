// Firebase Config (apna config daalna yahan)
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

// Fetch Data from Firestore
function fetchDashboardData() {
    // Yahan tumhara data structure ke hisab se changes karne honge
    db.collection("usageData").doc("current").get()
        .then((doc) => {
            if (doc.exists) {
                const data = doc.data();
                updateDashboard(data);
            } else {
                console.log("No data found!");
            }
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
        });
}

// Update UI with Data
function updateDashboard(data) {
    // Update stats cards
    document.getElementById("screenTime").textContent = data.screenTime || "0h 0m";
    document.getElementById("totalApps").textContent = data.totalApps || "0";
    document.getElementById("blockedAttempts").textContent = data.blockedAttempts || "0";
    document.getElementById("alerts").textContent = data.alerts || "0";

    // Update app list
    if (data.apps && data.apps.length > 0) {
        let appListHTML = "";
        data.apps.forEach(app => {
            appListHTML += `
                <div class="d-flex justify-content-between border-bottom py-2">
                    <span>${app.name}</span>
                    <span class="text-muted">${app.time}</span>
                </div>
            `;
        });
        document.getElementById("appList").innerHTML = appListHTML;
    }
}

// Remote Control Functions
document.getElementById("btnLockDevice").addEventListener("click", () => {
    alert("Device lock command sent!");
    // Yahan FCM ya HTTP request bhejoge actual device lock ke liye
});

document.getElementById("btnSetLimit").addEventListener("click", () => {
    const limit = prompt("Enter daily time limit (hours):");
    if (limit) {
        alert(`Time limit set to ${limit} hours`);
        // Firebase mein update karo
    }
});

// Refresh data every 30 seconds
setInterval(fetchDashboardData, 30000);

// Initial data fetch
fetchDashboardData();
