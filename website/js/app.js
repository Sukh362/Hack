const app = {
    SERVER_URL: 'http://192.168.31.123:3000',
    autoRefreshInterval: null,
    isAutoRefresh: true,

    init: function() {
        // Page load pe data load karo
        document.addEventListener('DOMContentLoaded', function() {
            app.loadData();
            app.startAutoRefresh();
        });
        
        // Online/offline detection
        window.addEventListener('online', app.loadData);
        window.addEventListener('offline', app.handleOffline);
    },

    loadData: async function() {
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
            
            // Table data display karo
            app.displayTableData(result.data);
            
            app.hideLoading();
            
        } catch (error) {
            console.error('Error loading data:', error);
            app.showError('Error loading data. Please check server connection.');
        }
    },

    updateStats: function(data) {
        const statsContainer = document.getElementById('statsCards');
        
        if (data.length === 0) {
            statsContainer.innerHTML = `
                <div class="card">
                    <div class="card-icon"><i class="fas fa-exclamation-circle"></i></div>
                    <h3>No Data</h3>
                    <div class="value">--</div>
                    <div class="subtext">Waiting for device connection</div>
                </div>
            `;
            return;
        }
        
        const latest = this.parseDeviceData(data[0]);
        const totalDevices = new Set(data.map(item => item.user_id)).size;
        const totalRecords = data.length;
        
        // Battery status text
        let batteryStatus = 'Optimal';
        let batteryIcon = 'fa-battery-full';
        if (latest.battery_percent <= 20) {
            batteryStatus = 'Critical';
            batteryIcon = 'fa-battery-quarter';
        } else if (latest.battery_percent <= 50) {
            batteryStatus = 'Low';
            batteryIcon = 'fa-battery-half';
        }
        
        // Location status
        let locationStatus = 'Not Available';
        let locationIcon = 'fa-map-marker-alt';
        let locationColor = 'var(--text-muted)';
        
        if (latest.location_data) {
            if (latest.location_data.latitude && latest.location_data.longitude) {
                locationStatus = 'Available';
                locationIcon = 'fa-map-marker-alt';
                locationColor = 'var(--primary)';
            } else if (latest.location_data.error) {
                locationStatus = 'Error';
                locationIcon = 'fa-exclamation-triangle';
                locationColor = 'var(--secondary)';
            }
        }

        statsContainer.innerHTML = `
            <div class="card">
                <div class="card-icon"><i class="fas ${batteryIcon}"></i></div>
                <h3>Battery Level</h3>
                <div class="value ${this.getBatteryColor(latest.battery_percent)}">
                    ${latest.battery_percent}%
                </div>
                <div class="subtext">${batteryStatus}</div>
            </div>
            
            <div class="card">
                <div class="card-icon"><i class="fas ${latest.is_charging ? 'fa-bolt' : 'fa-plug'}"></i></div>
                <h3>Charging Status</h3>
                <div class="value ${latest.is_charging ? 'status-on' : 'status-off'}">
                    ${latest.is_charging ? 'Charging' : 'Not Charging'}
                </div>
                <div class="subtext">Power connected: ${latest.is_charging ? 'Yes' : 'No'}</div>
            </div>
            
            <div class="card">
                <div class="card-icon"><i class="fas fa-thermometer-half"></i></div>
                <h3>Temperature</h3>
                <div class="value">${latest.temperature}°C</div>
                <div class="subtext">${this.getTemperatureStatus(latest.temperature)}</div>
            </div>
            
            <div class="card">
                <div class="card-icon"><i class="fas ${locationIcon}" style="color: ${locationColor}"></i></div>
                <h3>Location</h3>
                <div class="value" style="color: ${locationColor}">${locationStatus}</div>
                <div class="subtext">${totalDevices} device(s) connected</div>
            </div>
        `;
    },

    displayTableData: function(data) {
        const tableBody = document.getElementById('tableBody');
        tableBody.innerHTML = '';
        
        if (data.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted);">
                    <i class="fas fa-inbox" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>
                    No device data available
                </td>
            `;
            tableBody.appendChild(row);
            return;
        }
        
        data.forEach(item => {
            try {
                const deviceData = this.parseDeviceData(item);
                const time = new Date(item.created_at).toLocaleString();
                
                // Location display logic improve karo
                let locationDisplay = '';
                if (deviceData.location_data) {
                    if (deviceData.location_data.latitude && deviceData.location_data.longitude) {
                        locationDisplay = `
                            <div style="text-align: left;">
                                <i class="fas fa-map-marker-alt" style="color: var(--primary);"></i>
                                <strong>${deviceData.location_data.latitude.toFixed(4)}, ${deviceData.location_data.longitude.toFixed(4)}</strong>
                                <br>
                                <small style="color: var(--text-muted); font-size: 0.8rem;">
                                    📍 Accuracy: ${deviceData.location_data.accuracy ? deviceData.location_data.accuracy.toFixed(1) + 'm' : 'N/A'}
                                    ${deviceData.location_data.provider ? ' | 📡 ' + deviceData.location_data.provider : ''}
                                </small>
                            </div>
                        `;
                    } else if (deviceData.location_data.error) {
                        locationDisplay = `
                            <div style="text-align: left;">
                                <i class="fas fa-map-marker-alt" style="color: var(--secondary);"></i>
                                <span style="color: var(--secondary);">${this.getLocationErrorText(deviceData.location_data.error)}</span>
                            </div>
                        `;
                    } else {
                        locationDisplay = `
                            <div style="text-align: left;">
                                <i class="fas fa-map-marker-alt" style="color: var(--text-muted);"></i>
                                <span style="color: var(--text-muted);">Not available</span>
                            </div>
                        `;
                    }
                } else {
                    locationDisplay = `
                        <div style="text-align: left;">
                            <i class="fas fa-map-marker-alt" style="color: var(--text-muted);"></i>
                            <span style="color: var(--text-muted);">No location data</span>
                        </div>
                    `;
                }
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <i class="fas fa-mobile-alt" style="color: var(--primary); margin-right: 8px;"></i>
                        ${deviceData.device_model || android.os.Build.MODEL || 'Unknown Device'}
                        ${deviceData.android_version ? `<br><small style="color: var(--text-muted);">Android ${deviceData.android_version}</small>` : ''}
                    </td>
                    <td class="${this.getBatteryColor(deviceData.battery_percent)}">
                        <i class="fas fa-battery-${this.getBatteryIcon(deviceData.battery_percent)}"></i>
                        ${deviceData.battery_percent}%
                        ${deviceData.health ? `<br><small style="color: var(--text-muted);">${deviceData.health}</small>` : ''}
                    </td>
                    <td class="${deviceData.is_charging ? 'status-on' : 'status-off'}">
                        <i class="fas ${deviceData.is_charging ? 'fa-bolt' : 'fa-plug'}"></i>
                        ${deviceData.is_charging ? 'Charging' : 'Not Charging'}
                        ${deviceData.voltage ? `<br><small style="color: var(--text-muted);">${deviceData.voltage}mV</small>` : ''}
                    </td>
                    <td>
                        <i class="fas fa-thermometer-half" style="color: var(--accent);"></i>
                        ${deviceData.temperature}°C
                        ${deviceData.technology ? `<br><small style="color: var(--text-muted);">${deviceData.technology}</small>` : ''}
                    </td>
                    <td>
                        ${locationDisplay}
                    </td>
                    <td>
                        <i class="far fa-clock" style="color: var(--text-muted);"></i>
                        ${time}
                    </td>
                `;
                tableBody.appendChild(row);
            } catch (e) {
                console.error('Error parsing data:', e);
                // Fallback row for invalid data
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td colspan="6" style="text-align: center; color: var(--secondary);">
                        <i class="fas fa-exclamation-triangle"></i> Invalid data format
                    </td>
                `;
                tableBody.appendChild(row);
            }
        });
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
                    android_version: deviceData.android_version
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
                location_data: null,
                health: 'Unknown',
                voltage: 0,
                technology: 'Unknown'
            };
        }
    },

    getBatteryColor: function(percent) {
        if (percent <= 15) return 'battery-critical';
        if (percent <= 30) return 'battery-low';
        if (percent <= 70) return 'battery-medium';
        return 'battery-high';
    },

    getBatteryIcon: function(percent) {
        if (percent <= 15) return 'quarter';
        if (percent <= 30) return 'half';
        if (percent <= 70) return 'three-quarters';
        return 'full';
    },

    getTemperatureStatus: function(temp) {
        if (temp <= 30) return 'Cool';
        if (temp <= 40) return 'Normal';
        if (temp <= 50) return 'Warm';
        return 'Hot';
    },

    getLocationErrorText: function(error) {
        if (!error) return 'Location unavailable';
        
        const errorStr = error.toString().toLowerCase();
        
        if (errorStr.includes('permission')) {
            return 'Permission denied';
        } else if (errorStr.includes('disabled')) {
            return 'Location disabled';
        } else if (errorStr.includes('security')) {
            return 'Security error';
        } else if (errorStr.includes('not available')) {
            return 'No location data';
        } else {
            return 'Location error';
        }
    },

    showLoading: function() {
        document.getElementById('loading').style.display = 'block';
        document.getElementById('dataTable').style.display = 'none';
    },

    hideLoading: function() {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dataTable').style.display = 'table';
    },

    showError: function(message) {
        const loadingElement = document.getElementById('loading');
        loadingElement.innerHTML = `
            <i class="fas fa-exclamation-triangle" style="color: var(--secondary);"></i>
            <div>${message}</div>
            <button class="btn" onclick="app.loadData()" style="margin-top: 15px;">
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
                this.loadData();
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
        link.download = 'sukh-guard-data.json';
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
        // Current page data return karega for export
        const table = document.getElementById('dataTable');
        const rows = table.querySelectorAll('tbody tr');
        const data = [];
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 6) {
                data.push({
                    device: cells[0].textContent.trim(),
                    battery: cells[1].textContent.trim(),
                    status: cells[2].textContent.trim(),
                    temperature: cells[3].textContent.trim(),
                    location: cells[4].textContent.trim(),
                    lastUpdated: cells[5].textContent.trim()
                });
            }
        });
        
        return {
            exportTime: new Date().toISOString(),
            totalRecords: data.length,
            data: data
        };
    },

    handleOffline: function() {
        this.showError('No internet connection. Please check your network.');
    }
};

// App initialize karo
app.init();
