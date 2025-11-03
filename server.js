const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();

// Render ke liye environment port use karo, nahi toh 3000
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json({ limit: '10mb' }));

// Website folder serve karega
app.use(express.static('website'));

// Data storage file
const DATA_FILE = './app_data.json';

// Initialize data file if not exists
const initializeDataFile = () => {
    if (!fs.existsSync(DATA_FILE)) {
        const initialData = {
            users: [],
            app_data: [],
            stats: {
                total_users: 0,
                total_data: 0
            }
        };
        fs.writeFileSync(DATA_FILE, JSON.stringify(initialData, null, 2));
        console.log('✅ Data file created successfully');
    }
};

// Read data from file
const readData = () => {
    try {
        const data = fs.readFileSync(DATA_FILE, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error('Error reading data file:', error);
        return { users: [], app_data: [], stats: { total_users: 0, total_data: 0 } };
    }
};

// Write data to file
const writeData = (data) => {
    try {
        fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
        return true;
    } catch (error) {
        console.error('Error writing data file:', error);
        return false;
    }
};

// Initialize data file on server start
initializeDataFile();

// 📱 MOBILE APP ROUTES

// Health check route - Render ke liye important
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK', 
        message: 'Sukh Guard Backend is running',
        timestamp: new Date().toISOString(),
        environment: process.env.NODE_ENV || 'development'
    });
});

// New user register (App se)
app.post('/api/register', (req, res) => {
    const { name, email, phone } = req.body;
    
    const data = readData();
    const newUser = {
        id: Date.now(), // Unique ID
        name,
        email,
        phone,
        created_at: new Date().toISOString()
    };
    
    data.users.push(newUser);
    data.stats.total_users = data.users.length;
    
    if (writeData(data)) {
        res.json({
            message: 'User registered successfully!',
            user_id: newUser.id
        });
    } else {
        res.status(500).json({ error: 'Failed to save user' });
    }
});

// App se data save karega - MAIN ENDPOINT
app.post('/api/website/app-data', (req, res) => {
    try {
        const { user_id, data, type } = req.body;
        
        console.log('📱 Received app data:', { user_id, type });
        
        const allData = readData();
        const newData = {
            id: Date.now(),
            user_id: user_id || 1, // Default user ID
            data: data,
            type: type || 'full_device_info',
            created_at: new Date().toISOString()
        };
        
        allData.app_data.push(newData);
        allData.stats.total_data = allData.app_data.length;
        
        if (writeData(allData)) {
            console.log('✅ Data saved successfully');
            res.json({
                success: true,
                message: 'Data saved successfully!',
                data_id: newData.id
            });
        } else {
            console.error('❌ Failed to save data');
            res.status(500).json({ 
                success: false,
                error: 'Failed to save data' 
            });
        }
    } catch (error) {
        console.error('💥 Error in app-data endpoint:', error);
        res.status(500).json({ 
            success: false,
            error: 'Internal server error' 
        });
    }
});

// App ke liye user data
app.get('/api/user/:id', (req, res) => {
    const userId = parseInt(req.params.id);
    const data = readData();
    
    const user = data.users.find(u => u.id === userId);
    if (user) {
        res.json(user);
    } else {
        res.status(404).json({ error: 'User not found' });
    }
});

// 🌐 WEBSITE ROUTES

// Website ke liye all users
app.get('/api/website/users', (req, res) => {
    const data = readData();
    res.json({
        users: data.users.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
        total: data.users.length
    });
});

// Website ke liye all app data - GET endpoint
app.get('/api/website/app-data', (req, res) => {
    try {
        const data = readData();
        
        const appDataWithUsers = data.app_data.map(item => {
            const user = data.users.find(u => u.id === item.user_id);
            return {
                ...item,
                user_name: user ? user.name : 'Unknown'
            };
        }).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        console.log('📊 Sending app data to website:', appDataWithUsers.length, 'items');
        
        res.json({
            data: appDataWithUsers,
            total: appDataWithUsers.length
        });
    } catch (error) {
        console.error('Error in GET app-data:', error);
        res.status(500).json({ error: 'Failed to fetch data' });
    }
});

// 📊 STATS ROUTES
app.get('/api/stats', (req, res) => {
    const data = readData();
    res.json(data.stats);
});

// 🎯 WEBSITE PAGES

// Main website dashboard
app.get('/web', (req, res) => {
    res.sendFile(path.join(__dirname, 'website', 'index.html'));
});

// Alternative dashboard route
app.get('/dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, 'website', 'index.html'));
});

// Admin panel
app.get('/admin', (req, res) => {
    res.sendFile(path.join(__dirname, 'website', 'index.html'));
});

// 📄 API DOCUMENTATION
app.get('/api/docs', (req, res) => {
    res.json({
        message: 'Sukh Guard API Documentation',
        version: '1.0',
        environment: process.env.NODE_ENV || 'development',
        endpoints: {
            mobile: {
                'POST /api/register': 'Register new user',
                'POST /api/website/app-data': 'Save app data',
                'GET /api/user/:id': 'Get user data'
            },
            website: {
                'GET /api/website/users': 'Get all users',
                'GET /api/website/app-data': 'Get all app data',
                'GET /api/stats': 'Get statistics'
            },
            pages: {
                'GET /web': 'Website Dashboard',
                'GET /dashboard': 'Dashboard',
                'GET /admin': 'Admin Panel'
            },
            health: {
                'GET /health': 'Server health check'
            }
        }
    });
});

// Root route - Server status
app.get('/', (req, res) => {
    res.json({
        message: '🚀 Sukh Guard Backend Server Running!',
        version: '1.0',
        environment: process.env.NODE_ENV || 'development',
        port: PORT,
        storage: 'JSON File',
        website: {
            dashboard: 'https://' + req.get('host') + '/web',
            admin: 'https://' + req.get('host') + '/admin'
        },
        endpoints: {
            mobile: ['/api/register', '/api/website/app-data', '/api/user/:id'],
            website: ['/api/website/users', '/api/website/app-data'],
            stats: ['/api/stats'],
            pages: ['/web', '/dashboard', '/admin', '/health']
        }
    });
});

// 404 Error handler
app.use((req, res) => {
    res.status(404).json({
        error: 'Endpoint not found',
        available_endpoints: {
            api: ['/api/register', '/api/website/app-data', '/api/stats', '/health'],
            pages: ['/web', '/dashboard', '/admin', '/api/docs']
        }
    });
});

// Server start karein - Render compatible (0.0.0.0)
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 Sukh Guard Server running on port ${PORT}`);
    console.log(`🌐 Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log(`📱 Mobile App API: http://localhost:${PORT}/api`);
    console.log(`🌐 Website Dashboard: http://localhost:${PORT}/web`);
    console.log(`📊 Admin Panel: http://localhost:${PORT}/admin`);
    console.log(`❤️  Health Check: http://localhost:${PORT}/health`);
    console.log(`📚 API Docs: http://localhost:${PORT}/api/docs`);
    console.log(`💾 Data Storage: ${DATA_FILE}`);
    console.log(`\n✅ Server ready for production!`);
});
