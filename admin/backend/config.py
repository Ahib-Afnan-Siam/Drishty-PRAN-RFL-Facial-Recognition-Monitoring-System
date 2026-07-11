"""
Configuration file for the admin dashboard backend.
Separate configuration for backend services.
"""
import os

# Server configuration
# BACKEND_HOST: The hostname or IP address where the backend API will run
BACKEND_HOST = os.getenv('BACKEND_HOST', 'localhost')

# BACKEND_PORT: The port number for the backend API server
# Port 5001 is used for the Flask API server
BACKEND_PORT = int(os.getenv('BACKEND_PORT', 5001))

# FACE_RECOGNITION_HOST: The hostname or IP address where the face recognition system runs
FACE_RECOGNITION_HOST = os.getenv('FACE_RECOGNITION_HOST', '127.0.0.1')

# FACE_RECOGNITION_PORT: The port number for the face recognition system
FACE_RECOGNITION_PORT = int(os.getenv('FACE_RECOGNITION_PORT', 8000))

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
    f"http://localhost:8001",     # Standard frontend access
    f"http://127.0.0.1:8001",     # Alternative localhost access
    f"http://localhost:{BACKEND_PORT}",       # Backend self-access (if needed)
    f"http://127.0.0.1:{BACKEND_PORT}",      # Alternative backend access (if needed)
    "http://172.17.2.78:8094",    # Production frontend access
    "http://172.17.2.78:8093",    # Production backend access
    f"http://172.17.2.78:{BACKEND_PORT}",    # Production backend access with dynamic port
    "*"  # Allow all origins (for development only - remove in production)
]

# Application settings
# DEBUG_MODE: Enable/disable debug mode for the Flask application
# Should be False in production environments
DEBUG_MODE = os.getenv('DEBUG_MODE', 'True').lower() == 'true'

# SECRET_KEY: Secret key for Flask sessions and other security features
# CHANGE THIS IN PRODUCTION to a secure random value
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Change this in production