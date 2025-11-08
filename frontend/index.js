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
    }

    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            if (this.currentParentId) {
                this.loadChildren();
            }
        }, 5000);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    async registerParent() {
        alert("Use fixed credentials:\n\nUsername: Sukh\nPassword: Sukh hacker\n\nNew devices will automatically appear when they install the mobile app!");
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
                            <button class="btn-usage" onclick="app.viewUsage('${this.escapeHtml(child.id)}', '${this.escapeHtml(child.name)}')">
                                📊 Usage
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
                // Wait a bit then refresh
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

    async viewUsage(childId, childName) {
        try {
            const response = await fetch(`${API_BASE_URL}/parent/usage/${childId}`);
            
            if (response.ok) {
                const data = await response.json();
                
                let usageContent;
                if (data.usage_logs && data.usage_logs.length > 0) {
                    usageContent = data.usage_logs.map(log => `
                        <div class="usage-item">
                            <div class="app-name"><strong>${this.escapeHtml(log.app_name)}</strong></div>
                            <div class="usage-details">
                                <span class="duration">${this.formatDuration(log.duration)}</span>
                                <small class="timestamp">${new Date(log.timestamp).toLocaleString()}</small>
                            </div>
                        </div>
                    `).join('');
                } else {
                    usageContent = '<div class="no-usage"><p>No usage data available yet.</p></div>';
                }

                document.getElementById('usageTitle').textContent = `Usage for ${this.escapeHtml(childName)}`;
                document.getElementById('usageList').innerHTML = usageContent;
                document.getElementById('usageModal').style.display = 'block';
            } else {
                throw new Error('Server error: ' + response.status);
            }
        } catch (error) {
            console.error('Error loading usage:', error);
            document.getElementById('usageTitle').textContent = `Usage for ${this.escapeHtml(childName)}`;
            document.getElementById('usageList').innerHTML = `
                <div class="error-message">
                    <p>Unable to load usage data.</p>
                    <p>Check your internet connection.</p>
                </div>
            `;
            document.getElementById('usageModal').style.display = 'block';
        }
    }

    formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds} sec`;
        } else if (seconds < 3600) {
            return `${Math.floor(seconds / 60)} min`;
        } else {
            return `${Math.floor(seconds / 3600)} hr ${Math.floor((seconds % 3600) / 60)} min`;
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
        const parentId = localStorage.getItem('parentId');
        if (parentId) {
            this.currentParentId = parentId;
            this.showDashboard();
            this.loadChildren();
            this.startAutoRefresh();
        } else {
            this.showLogin();
        }
    }

    logout() {
        this.currentParentId = null;
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

// Add CSS for notifications and styles
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
    
    .btn-usage {
        background: #17a2b8;
        color: white;
    }
    
    .usage-item {
        border-bottom: 1px solid #eee;
        padding: 10px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .usage-item:last-child {
        border-bottom: none;
    }
    
    .app-name {
        font-weight: bold;
        color: #333;
    }
    
    .usage-details {
        text-align: right;
    }
    
    .duration {
        color: #007bff;
        font-weight: bold;
    }
    
    .timestamp {
        color: #666;
        display: block;
        font-size: 11px;
    }
    
    .no-children, .error-message, .no-usage {
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
        border-radius: 10px;
        max-width: 600px;
        max-height: 80vh;
        overflow-y: auto;
        position: relative;
    }
    
    .debug-info {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        font-size: 12px;
    }
`;
document.head.appendChild(style);

// Initialize app
const app = new ParentalControlApp();

// Close modal when clicking outside
window.addEventListener('click', (event) => {
    const modal = document.getElementById('usageModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
});

// Export for global access
window.app = app;
