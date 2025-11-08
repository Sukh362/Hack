const API_BASE_URL = window.location.origin.includes('localhost') ? 'http://localhost:8000' : window.location.origin;

class ParentalControlApp {
    constructor() {
        this.currentParentId = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkAuth();
    }

    bindEvents() {
        document.getElementById('registerBtn')?.addEventListener('click', () => this.registerParent());
        document.getElementById('loginBtn')?.addEventListener('click', () => this.loginParent());
        document.getElementById('logoutBtn')?.addEventListener('click', () => this.logout());
        document.getElementById('addChildBtn')?.addEventListener('click', () => this.addChild());
        document.getElementById('refreshChildrenBtn')?.addEventListener('click', () => this.loadChildren());
        document.getElementById('closeUsage')?.addEventListener('click', () => {
            document.getElementById('usageModal').style.display = 'none';
        });
    }

    async registerParent() {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch(`${API_BASE_URL}/parent/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            
            if (response.ok) {
                alert('Registration successful! Please login.');
                this.showLogin();
            } else {
                alert('Error: ' + data.detail);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async loginParent() {
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const response = await fetch(`${API_BASE_URL}/parent/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            
            if (response.ok) {
                this.currentParentId = data.parent_id;
                localStorage.setItem('parentId', this.currentParentId);
                this.showDashboard();
                this.loadChildren();
            } else {
                alert('Error: ' + data.detail);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async addChild() {
        const name = document.getElementById('childName').value;
        const deviceId = document.getElementById('deviceId').value;

        if (!name || !deviceId) {
            alert('Please fill all fields');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/child/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    parent_id: this.currentParentId,
                    name: name,
                    device_id: deviceId
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                alert('Child added successfully!');
                document.getElementById('childName').value = '';
                document.getElementById('deviceId').value = '';
                this.loadChildren();
            } else {
                alert('Error: ' + data.detail);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async loadChildren() {
        try {
            const response = await fetch(`${API_BASE_URL}/parent/children/${this.currentParentId}`);
            const data = await response.json();
            
            const childrenList = document.getElementById('childrenList');
            childrenList.innerHTML = '';

            data.children.forEach(child => {
                const childElement = document.createElement('div');
                childElement.className = 'child-item';
                childElement.innerHTML = `
                    <div class="child-info">
                        <h4>${child.name}</h4>
                        <p>Device ID: ${child.device_id}</p>
                        <p>Status: ${child.is_blocked ? 'Blocked' : 'Active'}</p>
                    </div>
                    <div class="child-actions">
                        <button onclick="app.toggleBlock('${child.id}', ${!child.is_blocked})">
                            ${child.is_blocked ? 'Unblock' : 'Block'}
                        </button>
                        <button onclick="app.viewUsage('${child.id}', '${child.name}')">
                            View Usage
                        </button>
                    </div>
                `;
                childrenList.appendChild(childElement);
            });
        } catch (error) {
            console.error('Error loading children:', error);
        }
    }

    async toggleBlock(childId, shouldBlock) {
        try {
            const response = await fetch(`${API_BASE_URL}/child/block`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    child_id: childId,
                    is_blocked: shouldBlock
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                alert(data.message);
                this.loadChildren();
            } else {
                alert('Error: ' + data.detail);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async viewUsage(childId, childName) {
        try {
            const response = await fetch(`${API_BASE_URL}/parent/usage/${childId}`);
            const data = await response.json();
            
            const usageContent = data.usage_logs.map(log => `
                <div class="usage-item">
                    <strong>${log.app_name}</strong>
                    <span>${log.duration} seconds</span>
                    <small>${new Date(log.timestamp).toLocaleString()}</small>
                </div>
            `).join('');

            document.getElementById('usageTitle').textContent = `Usage for ${childName}`;
            document.getElementById('usageList').innerHTML = usageContent;
            document.getElementById('usageModal').style.display = 'block';
        } catch (error) {
            console.error('Error loading usage:', error);
        }
    }

    checkAuth() {
        const parentId = localStorage.getItem('parentId');
        if (parentId) {
            this.currentParentId = parentId;
            this.showDashboard();
            this.loadChildren();
        } else {
            this.showLogin();
        }
    }

    logout() {
        localStorage.removeItem('parentId');
        this.currentParentId = null;
        this.showLogin();
    }

    showLogin() {
        document.getElementById('authSection').style.display = 'block';
        document.getElementById('dashboardSection').style.display = 'none';
    }

    showDashboard() {
        document.getElementById('authSection').style.display = 'none';
        document.getElementById('dashboardSection').style.display = 'block';
    }
}

const app = new ParentalControlApp();
