const app = {
    SERVER_URL: 'https://sukh-3qtl.onrender.com/api/website/app-data',
    autoRefreshInterval: null,
    isAutoRefresh: true,
    currentView: 'grid',

    init: function() {
        document.addEventListener('DOMContentLoaded', function() {
            app.loadAllDevices();
            app.startAutoRefresh();
        });
        
        window.addEventListener('online', app.loadAllDevices);
        window.addEventListener('offline', app.handleOffline);
    },

    loadAllDevices: async function() {
        try {
            console.log('🔄 Loading devices from:', app.SERVER_URL);
            app.showLoading();
            
            const response = await fetch(app.SERVER_URL);
            console.log('📡 Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('📱 Data received:', result);
            
            if (result && result.data) {
                app.updateStats(result.data);
                app.displayDeviceGrid(result.data);
                app.hideLoading();
            } else {
                throw new Error('Invalid data format from server');
            }
            
        } catch (error) {
            console.error('❌ Error loading data:', error);
            app.showError('Server connection failed. Error: ' + error.message);
        }
    },

    updateStats: function(data) {
        const totalDevicesElement = document.getElementById('totalDevices');
        const totalUsersElement = document.getElementById('totalUsers');
        const avgBatteryElement = document.getElementById('avgBattery');
        
        if (!data || data.length === 0) {
            totalDevicesElement.textContent = '0';
            totalUsersElement.textContent = '0';
            avgBatteryElement.textContent = '0%';
            return;
        }
        
        try {
            const uniqueDevices = new Set();
            const userSet = new Set();
            let totalBattery = 0;
            let validBatteryCount = 0;

            data.forEach(item => {
                try {
                    const deviceData = app.parseDeviceData(item);
                    const deviceKey = deviceData.device_id || deviceData.device_model;
                    
                    if (deviceKey) uniqueDevices.add(deviceKey);
                    if (deviceData.user_id) userSet.add(deviceData.user_id);
                    if (deviceData.battery_percent) {
                        totalBattery += deviceData.battery_percent;
                        validBatteryCount++;
                    }
                } catch (e) {
                    console.warn('Skipping invalid data item:', e);
                }
            });

            totalDevicesElement.textContent = uniqueDevices.size;
            totalUsersElement.textContent = userSet.size;
            avgBatteryElement.textContent = validBatteryCount > 0 ? 
                Math.round(totalBattery / validBatteryCount) + '%' : '0%';
                
        } catch (error) {
            console.error('Error updating stats:', error);
            totalDevicesElement.textContent = '0';
            totalUsersElement.textContent = '0';
            avgBatteryElement.textContent = '0%';
        }
    },

    displayDeviceGrid: function(data) {
        const devicesGrid = document.getElementById('devicesGrid');
        const deviceCount = document.getElementById('deviceCount');
        
        if (!data || data.length === 0) {
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
        
        try {
            const deviceMap = new Map();
            
            data.forEach(item => {
                try {
                    const deviceData = app.parseDeviceData(item);
                    const deviceKey = deviceData.device_id || deviceData.device_model;
                    
                    if (deviceKey) {
                        if (!deviceMap.has(deviceKey) || new Date(item.created_at) > new Date(deviceMap.get(deviceKey).created_at)) {
                            deviceMap.set(deviceKey, {
                                ...deviceData,
                                created_at: item.created_at,
                                rawData: item
                            });
                        }
                    }
                } catch (e) {
                    console.warn('Skipping invalid device data:', e);
                }
            });
            
            const latestDevices = Array.from(deviceMap.values());
            deviceCount.textContent = `${latestDevices.length} device${latestDevices.length !== 1 ? 's' : ''} connected`;
            devicesGrid.innerHTML = latestDevices.map(device => app.createDeviceCard(device)).join('');
            
            // Add click events
            document.querySelectorAll('.device-card').forEach(card => {
                card.addEventListener('click', function() {
                    const deviceId = this.getAttribute('data-device-id');
                    app.openDeviceDetails(deviceId);
                });
            });
            
        } catch (error) {
            console.error('Error displaying device grid:', error);
            devicesGrid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--secondary);">
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; margin-bottom: 15px; display: block;"></i>
                    <h3>Error Displaying Devices</h3>
                    <p>${error.message}</p>
                </div>
            `;
        }
    },

    createDeviceCard: function(device) {
        try {
            const batteryPercent = device.battery_percent || 0;
            const batteryClass = app.getBatteryLevelClass(batteryPercent);
            const timeAgo = app.getTimeAgo(device.created_at);
            const deviceId = device.device_id || device.device_model || 'unknown';
            const deviceModel = device.device_model || 'Unknown Device';
            const userId = device.user_id || 1;
            const temperature = device.temperature || 0;
            const androidVersion = device.android_version || 'Unknown';
            const isCharging = device.is_charging || false;
            
            return `
                <div class="device-card" data-device-id="${deviceId}">
                    <div class="device-header">
                        <div class="device-name">${deviceModel}</div>
                        <div class="device-user">User ${userId}</div>
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
                                <span class="${isCharging ? 'status-charging' : 'status-online'}">
                                    <i class="fas ${isCharging ? 'fa-bolt' : 'fa-check'}"></i>
                                    ${isCharging ? 'Charging' : 'Online'}
                                </span>
                            </span>
                        </div>
                        
                        <div class="detail-item">
                            <span class="detail-label">Temperature</span>
                            <span class="detail-value">
                                <i class="fas fa-thermometer-half"></i>
                                ${temperature}°C
                            </span>
                        </div>
                        
                        <div class="detail-item">
                            <span class="detail-label">Android</span>
                            <span class="detail-value">
                                <i class="fab fa-android"></i>
                                ${androidVersion}
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
        } catch (error) {
            console.error('Error creating device card:', error);
            return `
                <div class="device-card" style="border-color: var(--secondary);">
                    <div style="text-align: center; color: var(--secondary); padding: 20px;">
                        <i class="fas fa-exclamation-triangle"></i>
                        <div>Invalid Device Data</div>
                    </div>
                </div>
            `;
        }
    },

    parseDeviceData: function(item) {
        try {
            if (!item.data) {
                return {
                    battery_percent: 0,
                    is_charging: false,
                    temperature: 0,
                    device_model: 'Unknown',
                    android_version: 'Unknown',
                    device_id: 'unknown',
                    user_id: 1
                };
            }
            
            const deviceData = JSON.parse(item.data);
            
            // Check different data formats
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
                user_id: 1
            };
        }
    },

    getBatteryLevelClass: function(percent) {
        if (percent <= 20) return 'low';
        if (percent <= 50) return 'medium';
        return 'high';
    },

    getTimeAgo: function(timestamp) {
        if (!timestamp) return 'Unknown';
        
        try {
            const now = new Date();
            const time = new Date(timestamp);
            const diffInSeconds = Math.floor((now - time) / 1000);
            
            if (diffInSeconds < 60) return 'Just now';
            if (diffInSeconds < 3600) return Math.floor(diffInSeconds / 60) + ' min ago';
            if (diffInSeconds < 86400) return Math.floor(diffInSeconds / 3600) + ' hours ago';
            return Math.floor(diffInSeconds / 86400) + ' days ago';
        } catch (e) {
            return 'Unknown';
        }
    },

    openDeviceDetails: function(deviceId) {
        alert(`Opening details for device: ${deviceId}\n\nFeature coming soon!`);
    },

    toggleView: function() {
        alert('Table view coming soon! Currently in Grid View.');
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

    startAutoRefresh: function() {
        if (this.isAutoRefresh) {
            this.autoRefreshInterval = setInterval(() => {
                this.loadAllDevices();
            }, 10000);
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

    handleOffline: function() {
        this.showError('No internet connection. Please check your network.');
    }
};

// App initialize karo
app.init();
