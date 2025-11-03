const app = {
    SERVER_URL: 'https://sukh-3qtl.onrender.com/api/website/app-data',
    autoRefreshInterval: null,
    isAutoRefresh: true,
    currentView: 'grid', // 'grid' or 'table'

    init: function() {
        // Page load pe data load karo
        document.addEventListener('DOMContentLoaded', function() {
            app.loadAllDevices();
            app.startAutoRefresh();
        });
        
        // Online/offline detection
        window.addEventListener('online', app.loadAllDevices);
        window.addEventListener('offline', app.handleOffline);
    },

    loadAllDevices: async function() {
        try {
            app.showLoading();
            app.updateLastUpdate();
            
            // App data fetch karo
            const response = await fetch(`${app.SERVER_URL}/api/website/app-data`);
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            const result = await response.json();
            
            // Stats update karo
            app.updateStats(result.data);
            
            // Device grid display karo
            app.displayDeviceGrid(result.data);
            
            app.hideLoading();
            
        } catch (error) {
            console.error('Error loading data:', error);
            app.showError('Error loading data. Please check server connection.');
        }
    },

    updateStats: function(data) {
        const totalDevicesElement = document.getElementById('totalDevices');
        const totalUsersElement = document.getElementById('totalUsers');
        const avgBatteryElement = document.getElementById('avgBattery');
        
        if (data.length === 0) {
            totalDevicesElement.textContent = '0';
            totalUsersElement.textContent = '0';
            avgBatteryElement.textContent = '0%';
            return;
        }
        
        // Calculate stats
        const uniqueDevices = new Set(data.map(item => {
            const deviceData = app.parseDeviceData(item);
            return deviceData.device_id || deviceData.device_model;
        })).size;
        
        const uniqueUsers = new Set(data.map(item => {
            const deviceData = app.parseDeviceData(item);
            return deviceData.user_id || 1;
        })).size;
        
        const totalBattery = data.reduce((sum, item) => {
            const deviceData = app.parseDeviceData(item);
            return sum + (deviceData.battery_percent || 0);
        }, 0);
        
        const avgBattery = Math.round(totalBattery / data.length);
        
        // Update stats
        totalDevicesElement.textContent = uniqueDevices;
        totalUsersElement.textContent = uniqueUsers;
        avgBatteryElement.textContent = avgBattery + '%';
    },

    displayDeviceGrid: function(data) {
        const devicesGrid = document.getElementById('devicesGrid');
        const deviceCount = document.getElementById('deviceCount');
        
        if (data.length === 0) {
            devicesGrid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
                    <i class="fas fa-mobile-alt" style="font-size: 3rem; margin-bottom: 15px; display: block;"></i>
                    <h3>No Devices Connected</h3>
                    <p>Waiting for devices to send data...</p>
                </div>
            `;
            deviceCount.textContent = '0 devices found';
            return;
        }
        
        // Group data by device (latest entry for each device)
        const deviceMap = new Map();
        
        data.forEach(item => {
            const deviceData = app.parseDeviceData(item);
            const deviceKey = deviceData.device_id || deviceData.device_model;
            
            if (!deviceMap.has(deviceKey) || new Date(item.created_at) > new Date(deviceMap.get(deviceKey).created_at)) {
                deviceMap.set(deviceKey, {
                    ...deviceData,
                    created_at: item.created_at,
                    rawData: item
                });
            }
        });
        
        const latestDevices = Array.from(deviceMap.values());
        
        // Update device count
        deviceCount.textContent = `${latestDevices.length} device${latestDevices.length !== 1 ? 's' : ''} connected`;
        
        // Create device cards
        devicesGrid.innerHTML = latestDevices.map(device => app.createDeviceCard(device)).join('');
        
        // Add click event listeners
        document.querySelectorAll('.device-card').forEach(card => {
            card.addEventListener('click', function() {
                const deviceId = this.getAttribute('data-device-id');
                app.openDeviceDetails(deviceId);
            });
        });
    },

    createDeviceCard: function(device) {
        const batteryPercent = device.battery_percent || 0;
        const batteryClass = app.getBatteryLevelClass(batteryPercent);
        const timeAgo = app.getTimeAgo(device.created_at);
        const deviceId = device.device_id || device.device_model || 'unknown';
        
        return `
            <div class="device-card" data-device-id="${deviceId}">
                <div class="device-header">
                    <div class="device-name">${device.device_model || 'Unknown Device'}</div>
                    <div class="device-user">User ${device.user_id || 1}</div>
                </div>
                
                <div class="battery-indicator">
                    <div class="battery-level">
                        <div class="battery-fill ${batteryClass}" style="width: ${batteryPercent}%"></div>
                    </div>
                    <div class="battery-percent ${batteryClass}">${batteryPercent}%</div>
                </div>
                
                <div class="device-details">
                    <div class="detail-item">
                        <span class="detail-label">Status</span>
                        <span class="detail-value">
                            <span class="${device.is_charging ? 'status-charging' : 'status-online'}">
                                <i class="fas ${device.is_charging ? 'fa-bolt' : 'fa-check'}"></i>
                                ${device.is_charging ? 'Charging' : 'Online'}
                            </span>
                        </span>
                    </div>
                    
                    <div class="detail-item">
                        <span class="detail-label">Temperature</span>
                        <span class="detail-value">
                            <i class="fas fa-thermometer-half"></i>
                            ${device.temperature || 0}°C
                        </span>
                    </div>
                    
                    <div class="detail-item">
                        <span class="detail-label">Android</span>
                        <span class="detail-value">
                            <i class="fab fa-android"></i>
                            ${device.android_version || 'Unknown'}
                        </span>
                    </div>
                    
                    <div class="detail-item">
                        <span class="detail-label">Last Update</span>
                        <span class="detail-value">
                            <i class="far fa-clock"></i>
                            ${timeAgo}
                        </span>
                    </div>
                </div>
                
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--border);">
                    <small style="color: var(--text-muted);">
                        <i class="fas fa-id-card"></i>
                        ID: ${deviceId.substring(0, 12)}...
                    </small>
                </div>
            </div>
        `;
    },

    openDeviceDetails: function(deviceId) {
        // Yahan device details page open karenge
        // Temporary - alert show karte hain
        alert(`Opening details for device: ${deviceId}\n\nYe feature abhi implement ho raha hai!`);
        
        // Future mein yahan redirect karenge device-details.html?deviceId=${deviceId}
        // window.location.href = `device-details.html?deviceId=${deviceId}`;
    },

    parseDeviceData: function(item) {
        try {
            const deviceData = JSON.parse(item.data);
            
            // Check if it's full device data or just battery
            if (deviceData.battery_data) {
                return {
                    ...deviceData.battery_data,
                    location_data: deviceData.location_data,
                    device_model: deviceData.device_model,
                    android_version: deviceData.android_version,
                    device_id: deviceData.device_id,
                    user_id: deviceData.user_id
                };
            }
            return deviceData;
        } catch (e) {
            console.error('Error parsing device data:', e);
            return {
                battery_percent: 0,
                is_charging: false,
                temperature: 0,
                device_model: 'Unknown',
                android_version: 'Unknown',
                device_id: 'unknown',
                user_id: 1,
                location_data: null
            };
        }
    },

    getBatteryLevelClass: function(percent) {
        if (percent <= 20) return 'low';
        if (percent <= 50) return 'medium';
        return 'high';
    },

    getTimeAgo: function(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);
        
        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return Math.floor(diffInSeconds / 60) + ' min ago';
        if (diffInSeconds < 86400) return Math.floor(diffInSeconds / 3600) + ' hours ago';
        return Math.floor(diffInSeconds / 86400) + ' days ago';
    },

    toggleView: function() {
        const btn = document.getElementById('viewToggleBtn');
        
        if (this.currentView === 'grid') {
            // Switch to table view
            this.currentView = 'table';
            btn.innerHTML = '<i class="fas fa-table"></i> Table View';
            // Yahan table view implement karenge
            alert('Table view coming soon!');
        } else {
            // Switch to grid view
            this.currentView = 'grid';
            btn.innerHTML = '<i class="fas fa-th"></i> Grid View';
            this.loadAllDevices();
        }
    },

    showLoading: function() {
        document.getElementById('loadingDevices').style.display = 'block';
        document.getElementById('devicesGrid').style.display = 'none';
    },

    hideLoading: function() {
        document.getElementById('loadingDevices').style.display = 'none';
        document.getElementById('devicesGrid').style.display = 'grid';
    },

    showError: function(message) {
        const loadingElement = document.getElementById('loadingDevices');
        loadingElement.innerHTML = `
            <i class="fas fa-exclamation-triangle" style="color: var(--secondary);"></i>
            <div>${message}</div>
            <button class="btn" onclick="app.loadAllDevices()" style="margin-top: 15px;">
                <i class="fas fa-sync-alt"></i> Try Again
            </button>
        `;
        loadingElement.style.display = 'block';
    },

    updateLastUpdate: function() {
        const now = new Date();
        document.getElementById('lastUpdate').textContent = 
            `Last update: ${now.toLocaleTimeString()}`;
    },

    startAutoRefresh: function() {
        if (this.isAutoRefresh) {
            this.autoRefreshInterval = setInterval(() => {
                this.loadAllDevices();
            }, 10000); // 10 seconds
        }
    },

    stopAutoRefresh: function() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    },

    toggleAutoRefresh: function() {
        this.isAutoRefresh = !this.isAutoRefresh;
        const btn = document.getElementById('autoRefreshBtn');
        
        if (this.isAutoRefresh) {
            this.startAutoRefresh();
            btn.innerHTML = '<i class="fas fa-clock"></i> Auto Refresh: ON';
            btn.style.background = 'linear-gradient(45deg, var(--primary), #0099cc)';
        } else {
            this.stopAutoRefresh();
            btn.innerHTML = '<i class="fas fa-clock"></i> Auto Refresh: OFF';
            btn.style.background = 'linear-gradient(45deg, #666, #888)';
        }
    },

    exportData: function() {
        // Simple export functionality
        const dataStr = JSON.stringify(this.getCurrentData(), null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'sukh-guard-devices.json';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        // Show success message
        const originalText = document.querySelector('.btn-secondary').innerHTML;
        document.querySelector('.btn-secondary').innerHTML = '<i class="fas fa-check"></i> Exported!';
        setTimeout(() => {
            document.querySelector('.btn-secondary').innerHTML = originalText;
        }, 2000);
    },

    getCurrentData: function() {
        // Current devices data return karega for export
        return {
            exportTime: new Date().toISOString(),
            totalDevices: document.getElementById('totalDevices').textContent,
            totalUsers: document.getElementById('totalUsers').textContent,
            avgBattery: document.getElementById('avgBattery').textContent
        };
    },

    handleOffline: function() {
        this.showError('No internet connection. Please check your network.');
    }
};

// App initialize karo
app.init();
