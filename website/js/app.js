// js/app.js - Sukh Guard Dashboard Functions
const app = {
    SERVER_URL: 'https://sukh-3qtl.onrender.com/api/website/app-data',
    COMMANDS_URL: 'https://sukh-3qtl.onrender.com/api',
    autoRefreshInterval: null,
    isAutoRefresh: true,
    currentView: 'grid',
    lastDataHash: '',
    currentDevice: null,
    currentCamera: 'front',

    init: function() {
        console.log('🚀 App initializing...');
        document.addEventListener('DOMContentLoaded', function() {
            console.log('📄 DOM loaded');
            app.loadAllDevices();
            app.startAutoRefresh();
            app.initModalEvents();
        });
        
        window.addEventListener('online', app.loadAllDevices);
        window.addEventListener('offline', app.handleOffline);
    },

    initModalEvents: function() {
        console.log('🔧 Initializing modal events...');
        
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
                
                tabBtns.forEach(tb => tb.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
                
                this.classList.add('active');
                document.getElementById(tabId + 'Tab').classList.add('active');

                if (tabId === 'data' && app.currentDevice) {
                    app.loadDeviceData();
                }
            });
        });

        // 📸 CAMERA BUTTONS - FIXED EVENT LISTENERS
        const frontCameraBtn = document.getElementById('frontCameraBtn');
        const backCameraBtn = document.getElementById('backCameraBtn');
        const capturePhotoBtn = document.getElementById('capturePhotoBtn');
        const recordVideoBtn = document.getElementById('recordVideoBtn');

        console.log('📷 Camera buttons found:', {
            front: !!frontCameraBtn,
            back: !!backCameraBtn,
            capture: !!capturePhotoBtn,
            record: !!recordVideoBtn
        });

        if (frontCameraBtn) {
            frontCameraBtn.addEventListener('click', function() {
                console.log('📷 Front camera button clicked');
                app.activateCamera('front');
            });
        }

        if (backCameraBtn) {
            backCameraBtn.addEventListener('click', function() {
                console.log('📷 Back camera button clicked');
                app.activateCamera('back');
            });
        }

        if (capturePhotoBtn) {
            capturePhotoBtn.addEventListener('click', function() {
                console.log('📷 Capture photo button clicked');
                app.capturePhoto();
            });
        }

        if (recordVideoBtn) {
            recordVideoBtn.addEventListener('click', function() {
                console.log('📷 Record video button clicked');
                app.recordVideo();
            });
        }

        // Other event listeners...
        const refreshBtn = document.getElementById('refreshDeviceBtn');
        const pingBtn = document.getElementById('pingDeviceBtn');
        const emergencyBtn = document.getElementById('emergencyBtn');
        
        if (refreshBtn) refreshBtn.addEventListener('click', app.refreshDevice);
        if (pingBtn) pingBtn.addEventListener('click', app.pingDevice);
        if (emergencyBtn) emergencyBtn.addEventListener('click', app.emergencyAction);
    },

    // 📸 CAMERA FUNCTIONS - FIXED
    activateCamera: function(cameraType) {
        console.log('📷 activateCamera called:', cameraType);
        
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
        console.log('📷 Sending activate command for:', cameraType);
        app.sendCameraCommand('activate', cameraType);
    },

    resetCameraSelection: function() {
        const frontCameraBtn = document.getElementById('frontCameraBtn');
        const backCameraBtn = document.getElementById('backCameraBtn');
        
        if (frontCameraBtn) frontCameraBtn.classList.remove('active');
        if (backCameraBtn) backCameraBtn.classList.remove('active');
        
        app.currentCamera = 'front';
    },

    capturePhoto: function() {
        console.log('📷 capturePhoto called');
        
        if (!app.currentDevice) {
            app.showToast('Please select a device first', 'warning');
            return;
        }
        
        if (!app.currentCamera) {
            app.showToast('Please select a camera first', 'warning');
            return;
        }
        
        console.log('📷 Sending capture command for:', app.currentCamera);
        app.sendCameraCommand('capture', app.currentCamera);
    },

    recordVideo: function() {
        console.log('📷 recordVideo called');
        
        if (!app.currentDevice) {
            app.showToast('Please select a device first', 'warning');
            return;
        }
        
        if (!app.currentCamera) {
            app.showToast('Please select a camera first', 'warning');
            return;
        }
        
        const recordVideoBtn = document.getElementById('recordVideoBtn');
        const isRecording = recordVideoBtn.classList.contains('recording');
        
        if (isRecording) {
            recordVideoBtn.classList.remove('recording');
            recordVideoBtn.innerHTML = '<i class="fas fa-video"></i> Record Video';
            console.log('📷 Sending stop_record command');
            app.sendCameraCommand('stop_record', app.currentCamera);
        } else {
            recordVideoBtn.classList.add('recording');
            recordVideoBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Recording';
            console.log('📷 Sending record command');
            app.sendCameraCommand('record', app.currentCamera);
        }
    },

    sendCameraCommand: async function(action, cameraType) {
        console.log('📷 sendCameraCommand called:', { action, cameraType });
        
        if (!app.currentDevice) {
            console.error('❌ No current device selected');
            app.showToast('No device selected', 'error');
            return;
        }
        
        try {
            const payload = {
                device_id: app.currentDevice.device_id,
                device_model: app.currentDevice.device_model || 'Samsung Device',
                action: action,
                camera_type: cameraType
            };
            
            console.log('📷 Sending camera command payload:', payload);
            
            const response = await fetch(`${app.COMMANDS_URL}/camera`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });
            
            console.log('📷 Response status:', response.status);
            
            const result = await response.json();
            console.log('📷 Camera command result:', result);
            
            if (result.success) {
                app.showToast(result.message, 'success');
            } else {
                app.showToast('Camera command failed: ' + result.message, 'error');
            }
        } catch (error) {
            console.error('❌ Camera command error:', error);
            app.showToast('Network error - camera command not sent', 'error');
        }
    },

    // REST OF THE FUNCTIONS SAME AS BEFORE...
    loadAllDevices: async function() {
        try {
            console.log('🔄 Loading devices from:', app.SERVER_URL);
            app.showLoading();
            
            const response = await fetch(`${app.SERVER_URL}?_=${Math.random()}`);
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result && result.data) {
                const currentHash = app.generateDataHash(result.data);
                if (currentHash !== app.lastDataHash) {
                    app.lastDataHash = currentHash;
                    app.updateStats(result.data);
                    app.displayDeviceGrid(result.data);
                    app.hideLoading();
                } else {
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

    openDeviceDetails: function(deviceData) {
        console.log('📱 Opening device details:', deviceData);
        app.currentDevice = deviceData;
        
        document.getElementById('modalDeviceName').textContent = deviceData.device_model || 'Unknown Device';
        document.getElementById('modalDeviceId').textContent = 'ID: ' + (deviceData.device_id || 'Unknown');
        document.getElementById('modalBatteryPercent').textContent = (deviceData.battery_percent || 0) + '%';
        
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
        
        document.getElementById('infoAndroid').textContent = deviceData.android_version || 'Unknown';
        document.getElementById('infoTemp').textContent = (deviceData.temperature || 0).toFixed(1) + '°C';
        document.getElementById('infoLastUpdate').textContent = new Date(deviceData.created_at).toLocaleString();
        document.getElementById('infoCharging').textContent = deviceData.is_charging ? 'Charging' : 'Not Charging';
        
        const modal = document.getElementById('deviceModal');
        modal.style.display = 'block';
        
        app.showToast(`Opened controls for: ${deviceData.device_model}`);
    },

    showToast: function(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast-message ${type}`;
        toast.innerHTML = `
            <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : type === 'warning' ? 'fa-exclamation-triangle' : type === 'info' ? 'fa-info-circle' : 'fa-check-circle'}"></i>
            <span>${message}</span>
        `;
        
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
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3000);
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

    // ... (other functions remain same)
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

    handleOffline: function() {
        this.showError('No internet connection. Please check your network.');
    }
};

// App initialize karo
app.init();
