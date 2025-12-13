# Drishty - Facial Recognition Monitoring System
This is a comprehensive facial recognition-based monitoring system developed by PRAN-RFL Group for internal use. The system uses state-of-the-art computer vision and machine learning technologies to provide real-time face detection, recognition, and attendance tracking.
## System Overview

The system consists of two distinct but interconnected components:

1. **Main Face Recognition System** - Real-time facial recognition engine using YOLOv8 and MobileFaceNet
2. **Admin Dashboard** - Separate administrative interface for system management and reporting

This dual-frontend architecture allows for specialized functionality in each component while maintaining centralized data storage and management.

## Architecture

### Dual Database System
- **PRAN Database** (Main system): Stores registered user face embeddings and recognition logs
- **DRISHTI Database** (Admin system): Manages camera registry, user access control, and reporting data

### Main Face Recognition System
- **Backend**: Python/FastAPI server with real-time camera processing
- **Face Detection**: YOLOv8n-face model for accurate face detection
- **Face Recognition**: MobileFaceNet model for efficient face recognition
- **Tracking**: Embedding-aware centroid tracker to maintain consistent identities
- **Storage**: FAISS vector database for fast face similarity search
- **Database**: Oracle DB for persistent storage of user data and logs

### Admin Dashboard
- **Backend**: Python/Flask REST API for administrative functions
- **Frontend**: HTML/CSS/JavaScript dashboard with Bootstrap UI
- **Authentication**: Two-step verification (local access check + HRIS system validation)
- **User Management**: Request/approval workflow for access control
- **Reporting**: Camera registry and employee attendance analytics

## Key Features

### Face Recognition Engine
- Real-time multi-camera face detection and recognition
- Adaptive frame skipping for optimal performance
- Quality filtering (blur, brightness, pose) for reliable recognition
- Multi-frame averaging for stable embeddings
- Automatic camera reconnection handling

### Admin Dashboard
- Camera registry management
- User access control with approval workflow
- Employee attendance reporting
- Real-time system monitoring
- Secure authentication with HRIS integration

### Security
- Two-step authentication process
- No password storage policy
- Separation of sensitive configuration files
- Parameterized database queries to prevent injection

## Prerequisites

- Python 3.9+
- Oracle Database connectivity
- HRIS system API access (for admin authentication)
- Camera streams (RTSP/IP cameras or webcams)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd drishty
```
### 2. Configuration Files

Due to security concerns, actual configuration files containing sensitive credentials are not included in this repository. Template files are provided instead:

1. **Main Application Configuration**:
   - Copy `config_template.yaml` to `config.yaml`
   - Update with your PRAN database credentials and camera settings

2. **Admin Dashboard Configuration**:
   - Copy `admin/db_config_template.py` to `admin/db_config.py`
   - Update with your DRISHTI database credentials

### 3. Install Dependencies

Install main system dependencies:
```bash
pip install -r requirements.txt
```

Install admin dashboard dependencies:
```bash
cd admin/backend
pip install -r requirements.txt
```

Install system dependencies for OpenCV (Linux/Ubuntu):
```bash
sudo apt-get update
sudo apt-get install libgl1-mesa-glx libglib2.0-0
```

### 4. Download Required Models

The project requires several pre-trained models that are excluded from the repository due to their large size. You need to manually download these models:

#### YOLOv8 Face Detection Model
1. Download `yolov8n-face.pt` from the official YOLOv8 repository or trained models
2. Place it in the `models/` directory

#### Alternative Models (Optional)
- `glint360k_r100.onnx` - For ArcFace recognition (optional)
- `face_detection_yunet_2023mar.onnx` - For YuNet face detection (optional)

If you don't have these models, the system will use the YOLOv8 + MobileFaceNet combination by default.

### 5. Database Setup

The system requires two Oracle databases:

1. **PRAN Database** (configured in `config.yaml`):
   - Tables: `REGISTERED_USERS`, `RECOGNITION_LOGS`

2. **DRISHTI Database** (configured in `admin/db_config.py`):
   - Tables: `CAMERA_REGISTRY`, `ADMIN_REGISTRATION_REQUESTS`, `ADMIN_ACCESS_GRANTED_USERS`
   - Run the SQL script in `admin/backend/user_management_tables.sql` to create the required tables

### 6. Directory Structure Setup

Ensure the following directories exist and have proper permissions:
```bash
mkdir -p models
mkdir -p data/known_faces
mkdir -p output
mkdir -p logs
```

### 7. Running the Application

The system requires three separate servers:

1. **Main Face Recognition Server**:
   ```bash
   python server.py
   ```
   Accessible at `http://localhost:8000`

2. **Admin Backend API**:
   ```bash
   cd admin/backend
   python api.py
   ```
   REST API available at `http://localhost:5001`

3. **Admin Frontend Server**:
   ```bash
   cd admin/frontend
   python server.py
   ```
   Dashboard accessible at `http://localhost:8001`

## Project Structure

```
├── server.py                 # Main face recognition FastAPI server
├── config.yaml              # Main application configuration (not in repo)
├── config_template.yaml     # Template for main configuration
├── database.py             # PRAN database connection and operations
├── requirements.txt        # Main system dependencies
├── html/                   # Main dashboard frontend files
│   ├── index.html          # Main recognition dashboard
│   └── attendance.html     # Attendance kiosk view
├── admin/                  # Administrative dashboard
│   ├── db_config.py        # DRISHTI database configuration (not in repo)
│   ├── db_config_template.py # Template for database configuration
│   ├── backend/            # Admin REST API
│   │   ├── api.py          # Flask API endpoints
│   │   ├── db_connection.py # Database utilities
│   │   ├── user_management_tables.sql # Database schema
│   │   ├── test_user_management.py # Database function tests
│   │   └── test_api_endpoints.py # API endpoint tests
│   └── frontend/           # Admin dashboard UI
│       ├── index.html      # Main admin dashboard
│       ├── login.html      # Admin login page
│       └── user_management.html # User access control
├── models/                 # Pre-trained ML models (not in repo)
├── data/                   # Employee data and images
├── logs/                   # Application logs
└── output/                 # Generated FAISS indexes and metadata
```

## Admin Dashboard Features

### User Management System
We've implemented a comprehensive user management system with the following features:

1. **Two-Step Authentication Process**:
   - Local access verification (check if user exists in ADMIN_ACCESS_GRANTED_USERS)
   - HRIS system validation (authenticate against corporate HRIS API)

2. **User Registration Workflow**:
   - Users can request access through a registration form
   - Requests are stored in ADMIN_REGISTRATION_REQUESTS table
   - Admins can approve or reject pending requests
   - Approved users are moved to ADMIN_ACCESS_GRANTED_USERS table

3. **Direct Access Granting**:
   - Administrators can directly grant access to users without requiring registration
   - Prevents duplicate entries with validation checks

4. **User Access Revocation**:
   - Administrators can revoke user access by setting IS_ACTIVE flag to 'N'
   - Maintains audit trail of access changes

5. **API Endpoints**:
   - `/api/user-registration` - Submit new user registration requests
   - `/api/registration-requests` - View all pending requests
   - `/api/registration-requests/<id>/approve` - Approve registration requests
   - `/api/registration-requests/<id>/reject` - Reject registration requests
   - `/api/access-granted-users` - View all authorized users
   - `/api/access-granted-users/direct-grant` - Directly grant user access
   - `/api/access-granted-users/<id>/revoke` - Revoke user access

### Camera Management
- Add new cameras to the registry with detailed metadata
- Activate/deactivate cameras remotely
- View camera registry with comprehensive information

### Reporting and Analytics
- Employee daily summary reports with first/last seen times
- Dashboard statistics showing total cameras, active cameras, employees, and recognitions
- Real-time system health monitoring

## Security Notes

- Configuration files with credentials are excluded via `.gitignore`
- Never commit actual configuration files with credentials to version control
- Passwords are never stored in the system
- All database queries use parameterized statements
- Hardcoded admin backup credentials for emergency access (Admin/mis123)

## Docker Deployment

A Dockerfile is provided for containerized deployment of the main face recognition system:

```bash
docker build -t face-recognition-system .
docker run -p 8000:8000 face-recognition-system
```

Note: The admin dashboard requires separate containerization or manual setup.

## Testing

We've implemented comprehensive testing for the admin system:

1. **Database Function Tests** (`test_user_management.py`):
   - Creates registration requests
   - Approves/rejects requests
   - Checks user access permissions
   - Revokes user access
   - Verifies all database operations work correctly

2. **API Endpoint Tests** (`test_api_endpoints.py`):
   - Tests all REST API endpoints
   - Validates request/response formats
   - Ensures proper error handling
   - Verifies authentication flows

Run tests with:
```bash
cd admin/backend
python test_user_management.py
python test_api_endpoints.py
```

## Troubleshooting

### Missing Models
If you encounter errors about missing models:
1. Ensure the `models/` directory exists
2. Download the required model files as described in the setup instructions
3. Verify the model paths in `config.yaml` match your downloaded files

### Database Connection Issues
1. Verify database credentials in `config.yaml` and `admin/db_config.py`
2. Ensure Oracle client libraries are installed
3. Check network connectivity to database servers

### Camera Stream Issues
1. Verify camera URLs in `config.yaml` are accessible
2. Check firewall settings for RTSP streams
3. Ensure proper codec support for your camera streams

## Contributing

Please ensure you follow these guidelines:
1. Do not commit sensitive credentials
2. Use the template files as examples for configuration
3. Update the `.gitignore` file if you add new types of files that should be excluded
4. Follow the existing code style and architecture patterns