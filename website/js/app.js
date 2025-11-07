// js/app.js - Sukh Guard Dashboard Functions
const app = {
    currentDeviceId: null,
    currentDeviceModel: 'Samsung Device',
    
    // Camera control functions
    activateCamera: function(cameraType) {
        if (!this.currentDeviceId) {
            this.showToast('Please select a device first', 'error');
            return;
        }
        
        console.log(`Activating ${cameraType} camera for device: ${this.currentDeviceId}, model: ${this.currentDeviceModel}`);
        
        fetch('/api/camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_id: this.currentDeviceId,
                device_model: this.currentDeviceModel,
                action: 'activate',
                camera_type: cameraType
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                this.showToast(data.message);
                console.log('Camera command response:', data);
                
                // Add to logs
                this.addToLogs(`📷 ${data.message}`, 'info');
            } else {
                this.showToast('Camera activation failed', 'error');
                this.addToLogs('❌ Camera activation failed', 'danger');
            }
        })
        .catch(error => {
            console.error('Camera error:', error);
            this.showToast('Camera command failed: ' + error.message, 'error');
            this.addToLogs('❌ Camera command failed', 'danger');
        });
    },

    capturePhoto: function() {
        if (!this.currentDeviceId) {
            this.showToast('Please select a device first', 'error');
            return;
        }
        
        const activeCamera = document.querySelector('.camera-btn.active')?.classList.contains('front-camera') ? 'front' : 'back';
        
        fetch('/api/camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_id: this.currentDeviceId,
                device_model: this.currentDeviceModel,
                action: 'capture',
                camera_type: activeCamera
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showToast(data.message);
                this.addToLogs(`📸 ${data.message}`, 'success');
            } else {
                this.showToast('Photo capture failed', 'error');
                this.addToLogs('❌ Photo capture failed', 'danger');
            }
        })
        .catch(error => {
            console.error('Capture error:', error);
            this.showToast('Photo capture failed', 'error');
            this.addToLogs('❌ Photo capture failed', 'danger');
        });
    },

    recordVideo: function() {
        if (!this.currentDeviceId) {
            this.showToast('Please select a device first', 'error');
            return;
        }
        
        const activeCamera = document.querySelector('.camera-btn.active')?.classList.contains('front-camera') ? 'front' : 'back';
        
        fetch('/api/camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_id: this.currentDeviceId,
                device_model: this.currentDeviceModel,
                action: 'record', 
                camera_type: activeCamera
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showToast(data.message);
                this.addToLogs(`🎥 ${data.message}`, 'success');
            } else {
                this.showToast('Video recording failed', 'error');
                this.addToLogs('❌ Video recording failed', 'danger');
            }
        })
        .catch(error => {
            console.error('Record error:', error);
            this.showToast('Video recording failed', 'error');
            this.addToLogs('❌ Video recording failed', 'danger');
        });
    },

    // Utility functions
    showToast: function(message, type = 'success') {
        // Simple toast notification
        alert(`${type.toUpperCase()}: ${message}`);
    },

    addToLogs: function(message, type = 'info') {
        const logsList = document.getElementById('logsList');
        if (logsList) {
            const logItem = document.createElement('div');
            logItem.className = 'log-item';
            logItem.innerHTML = `
                <i class="fas fa-info-circle text-${type}"></i>
                <span class="log-message">${message}</span>
                <span class="log-time">${new Date().toLocaleTimeString()}</span>
            `;
            logsList.appendChild(logItem);
            logsList.scrollTop = logsList.scrollHeight;
        }
    },

    loadAllDevices: function() {
        console.log('Loading devices...');
        this.showToast('Refreshing devices...', 'info');
    },

    toggleView: function() {
        console.log('Toggling view...');
        const btn = document.getElementById('viewToggleBtn');
        if (btn.innerHTML.includes('Grid')) {
            btn.innerHTML = '<i class="fas fa-list"></i> List View';
        } else {
            btn.innerHTML = '<i class="fas fa-th"></i> Grid View';
        }
    },

    toggleAutoRefresh: function() {
        console.log('Toggling auto refresh...');
        const btn = document.getElementById('autoRefreshBtn');
        if (btn.innerHTML.includes('ON')) {
            btn.innerHTML = '<i class="fas fa-clock"></i> Auto Refresh: OFF';
        } else {
            btn.innerHTML = '<i class="fas fa-clock"></i> Auto Refresh: ON';
        }
    },

    // Data tab functions
    loadDeviceData: function() {
        console.log('Loading device data...');
        this.addToLogs('Loading device data...', 'info');
        
        // Simulate data loading
        document.getElementById('cpuUsage').textContent = '45%';
        document.getElementById('memoryUsage').textContent = '2.1/4 GB';
        document.getElementById('storageUsage').textContent = '64/128 GB';
        document.getElementById('networkStatus').textContent = 'WiFi Connected';
        
        const rawData = {
            device_id: this.currentDeviceId,
            device_model: this.currentDeviceModel,
            battery_level: 85,
            android_version: '13',
            last_update: new Date().toISOString(),
            camera_commands: ['front_camera_activated', 'photo_captured']
        };
        
        document.getElementById('rawDataOutput').textContent = JSON.stringify(rawData, null, 2);
    },

    exportDeviceData: function() {
        console.log('Exporting data...');
        this.showToast('Data exported successfully!', 'success');
        this.addToLogs('Device data exported', 'success');
    },

    clearDeviceData: function() {
        console.log('Clearing data...');
        document.getElementById('rawDataOutput').textContent = 'No data available';
        this.showToast('Data cleared successfully!', 'info');
        this.addToLogs('Device data cleared', 'warning');
    },

    loadHistoryData: function(period) {
        console.log('Loading history data for:', period);
        this.addToLogs(`Loading ${period} history data`, 'info');
    }
};

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sukh Guard Dashboard initialized');
    
    // Set current device ID (temporary - aap actual logic add kar sakte hain)
    app.currentDeviceId = 'sukh-device-' + Date.now();
    app.currentDeviceModel = 'Samsung Galaxy S23 Ultra';
    
    // Add initial log
    app.addToLogs('Dashboard initialized successfully', 'success');
});
