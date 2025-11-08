// js/app.js - Sukh Guard Dashboard Functions - REAL-TIME COMMAND SYSTEM
const app = {
    SERVER_URL: 'https://sukh-3qtl.onrender.com/api/website/app-data',
    COMMANDS_URL: 'https://sukh-3qtl.onrender.com/api',
    autoRefreshInterval: null,
    isAutoRefresh: true,
    currentView: 'grid',
    lastDataHash: '',
    currentDevice: null,
    currentCamera: 'front',
    currentCommandId: null,
    commandPollInterval: null,

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
            app.stopCommandPolling();
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

        // 📸 ENHANCED CAMERA BUTTONS - REAL-TIME COMMAND SYSTEM
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
                console.log('📷 Front camera button clicked - REAL-TIME COMMAND');
                app.activateCamera('front');
            });
        }

        if (backCameraBtn) {
            backCameraBtn.addEventListener('click', function() {
                console.log('📷 Back camera button clicked - REAL-TIME COMMAND');
                app.activateCamera('back');
            });
        }

        if (capturePhotoBtn) {
            capturePhotoBtn.addEventListener('click', function() {
                console.log('📷 Capture photo button clicked - REAL-TIME COMMAND');
                app.capturePhoto();
            });
        }

        if (recordVideoBtn) {
            recordVideoBtn.addEventListener('click', function() {
                console.log('📷 Record video button clicked - REAL-TIME COMMAND');
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

    // 📸 ENHANCED CAMERA FUNCTIONS - REAL-TIME COMMAND SYSTEM
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
            app.showToast('Front camera selected - Ready to capture', 'info');
        } else if (cameraType === 'back' && backCameraBtn) {
            backCameraBtn.classList.add('active');
            app.currentCamera = 'back';
            app.showToast('Back camera selected - Ready to capture', 'info');
        }
        
        console.log('📷 Camera activated:', cameraType);
    },

    resetCameraSelection: function() {
        const frontCameraBtn = document.getElementById('frontCameraBtn');
        const backCameraBtn = document.getElementById('backCameraBtn');
        
        if (frontCameraBtn) frontCameraBtn.classList.remove('active');
        if (backCameraBtn) backCameraBtn.classList.remove('active');
        
        app.currentCamera = 'front';
    },

    capturePhoto: function() {
        console.log('📷 capturePhoto called - REAL-TIME COMMAND');
        
        if (!app.currentDevice) {
            app.showToast('Please select a device first', 'warning');
            return;
        }
        
        if (!app.currentCamera) {
            app.showToast('Please select a camera first', 'warning');
            return;
        }
        
        console.log('📷 Sending capture command for:', app.currentCamera);
        
        // Show command status
        app.showCommandStatus(`Sending capture command to ${app.currentDevice.device_model}...`, 'sending');
        
        // Send REAL-TIME command
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

    // 🎯 ENHANCED: REAL-TIME CAMERA COMMAND SYSTEM
    sendCameraCommand: async function(action, cameraType) {
        console.log('📷 sendCameraCommand called:', { action, cameraType });
        
        if (!app.currentDevice) {
            console.error('❌ No current device selected');
            app.showToast('No device selected', 'error');
            return;
        }
        
        try {
            const deviceId = app.currentDevice.device_id;
            const deviceModel = app.currentDevice.device_model || 'Unknown Device';
            
            const payload = {
                device_id: deviceId,
                device_model: deviceModel,
                action: action,
                camera_type: cameraType
            };
            
            console.log('📷 Sending REAL-TIME camera command payload:', payload);
            
            // Show sending status
            app.showCommandStatus(`Sending ${action} command to ${deviceModel}...`, 'sending');
            
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
                app.showToast(`Command sent: ${result.message}`, 'success');
                app.showCommandStatus(`Command sent - Waiting for device...`, 'sent');
                
                // ✅ START REAL-TIME POLLING FOR COMMAND RESULT
                app.currentCommandId = result.command_id;
                app.startCommandPolling(result.command_id, deviceId);
                
            } else {
                app.showToast('Camera command failed: ' + result.message, 'error');
                app.showCommandStatus(`Command failed: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('❌ Camera command error:', error);
            app.showToast('Network error - camera command not sent', 'error');
            app.showCommandStatus('Network error - command not sent', 'error');
        }
    },

    // 🎯 NEW: REAL-TIME COMMAND POLLING SYSTEM
    startCommandPolling: function(commandId, deviceId) {
        console.log(`🔄 Starting command polling: ${commandId} for device: ${deviceId}`);
        
        let pollCount = 0;
        const maxPolls = 60; // 60 seconds timeout
        
        // Clear any existing polling
        app.stopCommandPolling();
        
        app.commandPollInterval = setInterval(async () => {
            pollCount++;
            
            if (pollCount > maxPolls) {
                app.stopCommandPolling();
                app.showCommandStatus('Timeout - No response from device', 'timeout');
                app.showToast('Device response timeout', 'warning');
                return;
            }

            try {
                const response = await fetch(`${app.COMMANDS_URL}/command-status/${commandId}`);
                const result = await response.json();
                
                if (result.success) {
                    const command = result.command;
                    
                    console.log(`📊 Command status: ${command.status}`, command);
                    
                    if (command.status === 'delivered') {
                        app.showCommandStatus('Command delivered to device - Executing...', 'delivered');
                    } else if (command.status === 'completed') {
                        app.stopCommandPolling();
                        app.showCommandStatus('Command executed successfully!', 'completed');
                        app.showToast('Photo captured successfully!', 'success');
                        
                        // ✅ PHOTO DATA HANDLING - Agar photo data hai to show karo
                        if (command.photo_data) {
                            console.log('📸 Photo data received:', command.photo_data);
                            app.showPhotoPreview(command.photo_data);
                        }
                        
                    } else if (command.status === 'failed') {
                        app.stopCommandPolling();
                        app.showCommandStatus(`Failed: ${command.error_message || 'Unknown error'}`, 'error');
                        app.showToast('Command execution failed', 'error');
                    }
                }
            } catch (error) {
                console.error('Polling error:', error);
                // Continue polling on error
            }
        }, 1000); // Poll every second
        
        console.log(`✅ Command polling started for command: ${commandId}`);
    },

    stopCommandPolling: function() {
        if (app.commandPollInterval) {
            clearInterval(app.commandPollInterval);
            app.commandPollInterval = null;
            console.log('🛑 Command polling stopped');
        }
    },

    // 🎯 NEW: COMMAND STATUS DISPLAY
    showCommandStatus: function(message, status) {
        // Create or update command status display
        let statusElement = document.getElementById('commandStatusDisplay');
        
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.id = 'commandStatusDisplay';
            statusElement.className = 'command-status-display';
            
            // Insert after camera controls
            const cameraControls = document.querySelector('.camera-controls');
            if (cameraControls) {
                cameraControls.parentNode.insertBefore(statusElement, cameraControls.nextSibling);
            } else {
                document.querySelector('.modal-body').appendChild(statusElement);
            }
        }
        
        const statusClass = `status-${status}`;
        statusElement.innerHTML = `
            <div class="command-status ${statusClass}">
                <i class="fas ${app.getStatusIcon(status)}"></i>
                <span class="status-message">${message}</span>
                ${status === 'sending' || status === 'sent' || status === 'delivered' ? 
                    '<div class="status-spinner"><i class="fas fa-spinner fa-spin"></i></div>' : ''}
            </div>
        `;
        
        statusElement.style.display = 'block';
    },

    getStatusIcon: function(status) {
        switch(status) {
            case 'sending': return 'fa-paper-plane';
            case 'sent': return 'fa-check-circle';
            case 'delivered': return 'fa-mobile-alt';
            case 'completed': return 'fa-check-circle';
            case 'error': return 'fa-exclamation-circle';
            case 'timeout': return 'fa-clock';
            default: return 'fa-info-circle';
        }
    },

    // 🎯 NEW: PHOTO PREVIEW FUNCTION
    showPhotoPreview: function(photoData) {
        // Create photo preview modal
        let photoModal = document.getElementById('photoPreviewModal');
        
        if (!photoModal) {
            photoModal = document.createElement('div');
            photoModal.id = 'photoPreviewModal';
            photoModal.className = 'modal';
            photoModal.innerHTML = `
                <div class="modal-content photo-preview">
                    <div class="modal-header">
                        <h2><i class="fas fa-camera"></i> Photo Preview</h2>
                        <span class="close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="photo-container">
                            <img id="previewImage" src="" alt="Captured Photo">
                        </div>
                        <div class="photo-info">
                            <p>Photo captured from ${app.currentDevice.device_model}</p>
                            <small>${new Date().toLocaleString()}</small>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(photoModal);
            
            // Close event
            photoModal.querySelector('.close').onclick = function() {
                photoModal.style.display = 'none';
            };
            
            // Close on outside click
            window.onclick = function(event) {
                if (event.target === photoModal) {
                    photoModal.style.display = 'none';
                }
            };
        }
        
        // Set image source (agar base64 data hai)
        const previewImage = photoModal.querySelector('#previewImage');
        if (photoData.startsWith('data:image')) {
            previewImage.src = photoData;
        } else {
            previewImage.src = 'data:image/jpeg;base64,' + photoData;
        }
        
        photoModal.style.display = 'block';
    },

    // REST OF THE FUNCTIONS (SAME AS BEFORE WITH MINOR ENHANCEMENTS)
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
        
        // Stop any previous command polling
        app.stopCommandPolling();
        
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
                
                /* 🎯 NEW: Command Status Styles */
                .command-status-display {
                    margin: 15px 0;
                    padding: 0;
                }
                .command-status {
                    padding: 12px 15px;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-size: 14px;
                    border-left: 4px solid var(--info);
                }
                .status-sending { border-left-color: var(--warning); background: rgba(255,193,7,0.1); }
                .status-sent { border-left-color: var(--info); background: rgba(23,162,184,0.1); }
                .status-delivered { border-left-color: var(--primary); background: rgba(0,123,255,0.1); }
                .status-completed { border-left-color: var(--success); background: rgba(40,167,69,0.1); }
                .status-error { border-left-color: var(--danger); background: rgba(220,53,69,0.1); }
                .status-timeout { border-left-color: var(--secondary); background: rgba(108,117,125,0.1); }
                .status-spinner { margin-left: auto; }
                
                /* Photo Preview Styles */
                .photo-preview .modal-content {
                    max-width: 90%;
                    max-height: 90%;
                }
                .photo-container {
                    text-align: center;
                    margin: 20px 0;
                }
                .photo-container img {
                    max-width: 100%;
                    max-height: 400px;
                    border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
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
    },
    
    // Placeholder functions for other buttons
    refreshDevice: function() {
        app.showToast('Refreshing device data...', 'info');
    },
    
    pingDevice: function() {
        app.showToast('Pinging device...', 'info');
    },
    
    emergencyAction: function() {
        app.showToast('Emergency action triggered!', 'warning');
    },
    
    loadDeviceData: function() {
        console.log('Loading device data...');
    }
};

// App initialize karo
app.init();
