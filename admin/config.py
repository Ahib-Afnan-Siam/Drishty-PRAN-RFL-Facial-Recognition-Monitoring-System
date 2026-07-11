"""
Configuration file for the admin dashboard.
Centralizes all IP addresses, ports, and other configuration values.
"""

# Server configuration
# FRONTEND_HOST: The hostname or IP address where the frontend server will run
# Typically 'localhost' for development, or a specific IP/hostname for production
FRONTEND_HOST = "localhost"

# FRONTEND_PORT: The port number for the frontend server
# Port 8001 is used to avoid conflicts with common development servers
FRONTEND_PORT = 8001

# BACKEND_HOST: The hostname or IP address where the backend API will run
# Should match the frontend host for local development
# For production, this might be a different server or load balancer
BACKEND_HOST = "localhost"

# BACKEND_PORT: The port number for the backend API server
# Port 5001 is used for the Flask API server
BACKEND_PORT = 5001

# FACE_RECOGNITION_HOST: The hostname or IP address where the face recognition system runs
# This is the main server for the face recognition system
FACE_RECOGNITION_HOST = "127.0.0.1"

# FACE_RECOGNITION_PORT: The port number for the face recognition system
# Port 8000 is used for the main face recognition server
FACE_RECOGNITION_PORT = 8000

# API configuration
# API_BASE_URL: The base URL for all API endpoints
# This is constructed from the backend host and port
API_BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api"

# FACE_RECOGNITION_URL: The URL for the face recognition system
# This is constructed from the face recognition host and port
FACE_RECOGNITION_URL = f"http://{FACE_RECOGNITION_HOST}:{FACE_RECOGNITION_PORT}"

# CORS configuration
# ALLOWED_ORIGINS: List of origins that are allowed to make requests to the API
# This includes both localhost and 127.0.0.1 variations for flexibility
# Update this list when deploying to production with your actual domain(s)
ALLOWED_ORIGINS = [
    f"http://{FRONTEND_HOST}:{FRONTEND_PORT}",     # Standard frontend access
    f"http://127.0.0.1:{FRONTEND_PORT}",           # Alternative localhost access
    f"http://{BACKEND_HOST}:{BACKEND_PORT}",       # Backend self-access (if needed)
    f"http://127.0.0.1:{BACKEND_PORT}"             # Alternative backend access (if needed)
]

# Database configuration (if needed in the future)
# DATABASE_HOST = "localhost"
# DATABASE_PORT = 1521
# DATABASE_SERVICE_NAME = "XE"

# Application settings
# DEBUG_MODE: Enable/disable debug mode for the Flask application
# Should be False in production environments
DEBUG_MODE = True

# SECRET_KEY: Secret key for Flask sessions and other security features
# CHANGE THIS IN PRODUCTION to a secure random value
SECRET_KEY = "your-secret-key-here"  # Change this in production