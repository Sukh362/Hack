cat > main.py << 'EOF'
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import uuid
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect('parental.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parents (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS children (
            id TEXT PRIMARY KEY,
            parent_id TEXT,
            name TEXT,
            device_id TEXT UNIQUE,
            is_blocked BOOLEAN DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id TEXT PRIMARY KEY,
            child_id TEXT,
            app_name TEXT,
            duration INTEGER,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

class ParentRegister(BaseModel):
    email: str
    password: str

class ChildRegister(BaseModel):
    parent_id: str
    name: str
    device_id: str

class UsageLog(BaseModel):
    child_id: str
    app_name: str
    duration: int

class BlockRequest(BaseModel):
    child_id: str
    is_blocked: bool

def get_db_connection():
    conn = sqlite3.connect('parental.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.post("/parent/register")
async def register_parent(parent: ParentRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        parent_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO parents (id, email, password, created_at) VALUES (?, ?, ?, ?)",
            (parent_id, parent.email, parent.password, datetime.now().isoformat())
        )
        conn.commit()
        return {"message": "Parent registered successfully", "parent_id": parent_id}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        conn.close()

@app.post("/parent/login")
async def login_parent(parent: ParentRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM parents WHERE email = ? AND password = ?",
        (parent.email, parent.password)
    )
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"message": "Login successful", "parent_id": user['id']}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/child/register")
async def register_child(child: ChildRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    child_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO children (id, parent_id, name, device_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (child_id, child.parent_id, child.name, child.device_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return {"message": "Child registered successfully", "child_id": child_id}

@app.post("/usage/log")
async def log_usage(usage: UsageLog):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    log_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO usage_logs (id, child_id, app_name, duration, timestamp) VALUES (?, ?, ?, ?, ?)",
        (log_id, usage.child_id, usage.app_name, usage.duration, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return {"message": "Usage logged successfully"}

@app.post("/child/block")
async def block_child(block: BlockRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE children SET is_blocked = ? WHERE id = ?",
        (block.is_blocked, block.child_id)
    )
    conn.commit()
    conn.close()
    
    action = "blocked" if block.is_blocked else "unblocked"
    return {"message": f"Child {action} successfully"}

@app.get("/parent/children/{parent_id}")
async def get_children(parent_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM children WHERE parent_id = ?", (parent_id,))
    children = cursor.fetchall()
    conn.close()
    
    return {
        "children": [
            {
                "id": child['id'],
                "name": child['name'],
                "device_id": child['device_id'],
                "is_blocked": bool(child['is_blocked'])
            }
            for child in children
        ]
    }

@app.get("/parent/usage/{child_id}")
async def get_usage(child_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM usage_logs WHERE child_id = ? ORDER BY timestamp DESC LIMIT 50",
        (child_id,)
    )
    logs = cursor.fetchall()
    conn.close()
    
    return {
        "usage_logs": [
            {
                "app_name": log['app_name'],
                "duration": log['duration'],
                "timestamp": log['timestamp']
            }
            for log in logs
        ]
    }

@app.get("/child/status/{device_id}")
async def get_child_status(device_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM children WHERE device_id = ?", (device_id,))
    child = cursor.fetchone()
    conn.close()
    
    if child:
        return {
            "is_blocked": bool(child['is_blocked']),
            "child_id": child['id'],
            "name": child['name']
        }
    else:
        raise HTTPException(status_code=404, detail="Child device not found")

@app.get("/")
async def root():
    return {"message": "Parental Control API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF
