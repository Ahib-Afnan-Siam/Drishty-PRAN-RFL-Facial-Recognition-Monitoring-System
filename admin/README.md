# Admin Dashboard

This directory contains the admin dashboard for the face recognition system, separated into backend and frontend components.

## Directory Structure

```
admin/
├── db_config.py           # Database configuration
├── backend/
│   ├── db_connection.py   # Database connection utilities
│   ├── api.py             # Flask API endpoints
│   └── requirements.txt   # Backend dependencies
└── frontend/
   ├── login.html          # Login page
   ├── index.html          # Main dashboard page
   ├── styles.css          # Dashboard styling
   ├── script.js          # Dashboard functionality
   └── server.py          # Simple HTTP server for frontend
```

## Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the API server:
   ```
   python api.py
   ```

   The backend API will be available at `http://localhost:5001`

## Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Run the frontend server:
   ```
   python server.py
   ```

   The frontend dashboard will be available at `http://localhost:8001`

## Usage

1. Make sure both the backend API and frontend servers are running
2. Open your browser and go to `http://localhost:8001`
3. Login with your employee ID and HRIS password
4. The dashboard will automatically connect to the backend API at `http://localhost:5001`

## API Endpoints

- `GET /api/health` - Health check endpoint
- `POST /api/login` - User authentication endpoint
- `GET /api/cameras` - Retrieve all registered cameras
- `GET /api/employee-summary` - Retrieve employee daily summary data
- `GET /api/dashboard-stats` - Retrieve dashboard statistics

## Authentication

The admin dashboard requires authentication using your employee ID and HRIS password. 
The credentials are verified against the HRIS system via REST API.

## Database Configuration

The database connection details are configured in [db_config.py](file:///C:/Users/MIS/Documents/rnd_face_recognition/admin/db_config.py) in the parent admin directory.

# 5001 - 8093 
# 8001 - 8094

# // Configuration constants
# const CONFIG = {
#    FRONTEND_HOST: "172.17.2.78",
#    FRONTEND_PORT: 8094,
#    BACKEND_HOST: "172.17.2.78",
#    BACKEND_PORT: 8093
# };