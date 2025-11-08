cat > README.md << 'EOF'
# Parental Control App

Complete parental control solution with web panel and backend API.

## Features
- Parent registration & login
- Child device management  
- App usage tracking
- Real-time blocking
- Web dashboard

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
