"""
API routes for the admin dashboard.
Provides RESTful endpoints for accessing admin data.
"""

import sys
import os

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime, timedelta, date, time
from decimal import Decimal
import json
import cx_Oracle
from db_connection import get_camera_registry, get_employee_daily_summary, get_employee_daily_summary_aggregated, get_db_connection, close_db_connection, authenticate_user_hris_api, add_camera, update_camera_status, check_user_access, create_registration_request, get_pending_registration_requests, approve_registration_request, reject_registration_request, get_access_granted_users, revoke_user_access, allow_user_access, grant_direct_access, execute_query, get_employee_downtime_summary, get_employee_movement_data, get_daily_inout_summary_data, get_employee_movement_transitions, get_registered_users, get_employee_unique_visit_summary, get_location_coverage_details, get_top_floor_visitors
# Import configuration
from config import BACKEND_HOST, BACKEND_PORT, ALLOWED_ORIGINS, FACE_RECOGNITION_URL

def json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return str(obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app, origins=ALLOWED_ORIGINS)  # Enable CORS with configuration from config.py

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user with two-step verification process."""
    try:
        # Get credentials from request
        data = request.get_json()
        employee_id = data.get('employee_id')
        password = data.get('password')
        
        if not employee_id or not password:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': 'Employee ID and password are required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Check for hardcoded admin credentials
        if employee_id == 'Admin' and password == 'mis123':
            # Grant admin access without checking database or HRIS
            user_data = {
                'employee_id': 'Admin',
                'name': 'Administrator',
                'role': 'Administrator'
            }
            
            response_data = {
                'success': True,
                'message': 'Authentication successful',
                'user': user_data
            }
            
            return app.response_class(
                response=json.dumps(response_data, default=json_serializer),
                status=200,
                mimetype='application/json'
            )
        
        # Step 1: Check if user has access in local database
        has_access = check_user_access(employee_id)
        
        if not has_access:
            response_data = {
                'success': False,
                'message': 'Access not granted. Please request access from administrator.'
            }
            return app.response_class(
                response=json.dumps(response_data, default=json_serializer),
                status=403,
                mimetype='application/json'
            )
        
        # Step 2: Authenticate user against HRIS system
        is_valid = authenticate_user_hris_api(employee_id, password)
        
        if is_valid:
            # Get user details (simulated)
            user_data = {
                'employee_id': employee_id,
                'name': f'User {employee_id}',
                'role': 'Administrator'
            }
            
            response_data = {
                'success': True,
                'message': 'Authentication successful',
                'user': user_data
            }
        else:
            response_data = {
                'success': False,
                'message': 'Invalid employee ID or password'
            }
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200 if response_data['success'] else 401,
            mimetype='application/json'
        )
            
    except cx_Oracle.Error as e:
        logger.error(f"Database error during login: {e}")
        error_response = {
            'success': False,
            'message': 'Authentication service unavailable'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error during login: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred during authentication'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    """Retrieve all registered cameras."""
    try:
        cameras = get_camera_registry()
        response_data = {
            'success': True,
            'data': cameras,
            'count': len(cameras)
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving cameras: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/employee-summary', methods=['GET'])
def get_employee_summary():
    """Retrieve employee daily summary data."""
    try:
        # Get date range from query parameters or use defaults
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # If no dates provided, use last 7 days
        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        summary_data = get_employee_daily_summary(from_date, to_date)
        aggregated_data = get_employee_daily_summary_aggregated(from_date, to_date)
        
        response_data = {
            'success': True,
            'data': summary_data,
            'kpi_data': aggregated_data['kpi_data'],
            'chart_data': {
                'department_data': aggregated_data['department_data'],
                'entry_time_data': aggregated_data['entry_time_data']
            },
            'count': len(summary_data),
            'from_date': from_date,
            'to_date': to_date
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving employee summary: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/employee-summary-aggregated', methods=['GET'])
def get_employee_summary_aggregated():
    """Retrieve aggregated employee daily summary data for KPI cards and charts."""
    try:
        # Get date range from query parameters or use defaults
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # If no dates provided, use last 7 days
        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        aggregated_data = get_employee_daily_summary_aggregated(from_date, to_date)
        
        response_data = {
            'success': True,
            'kpi_data': aggregated_data['kpi_data'],
            'chart_data': {
                'department_data': aggregated_data['department_data'],
                'entry_time_data': aggregated_data['entry_time_data']
            },
            'from_date': from_date,
            'to_date': to_date
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving aggregated employee summary: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Retrieve dashboard statistics."""
    try:
        # Get camera count
        cameras = get_camera_registry()
        camera_count = len(cameras)
        
        # Get active cameras (assuming IS_ACTIVE = 'Y' means active)
        active_cameras = [cam for cam in cameras if cam.get('IS_ACTIVE') == 'Y']
        active_camera_count = len(active_cameras)
        
        # For demonstration, we'll use a fixed date range for employee summary
        from_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        employee_data = get_employee_daily_summary(from_date, to_date)
        
        total_employees = len(set(emp['EMPLOYEE_ID'] for emp in employee_data))
        total_recognitions = sum(emp['TOTAL_HITS'] for emp in employee_data)
        
        stats = {
            'total_cameras': camera_count,
            'active_cameras': active_camera_count,
            'total_employees': total_employees,
            'total_recognitions': total_recognitions,
            'date_range': {
                'from': from_date,
                'to': to_date
            }
        }
        
        response_data = {
            'success': True,
            'data': stats
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving dashboard stats: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/cameras', methods=['POST'])
def add_camera_endpoint():
    """Add a new camera to the registry."""
    try:
        # Get camera data from request
        camera_data = request.get_json()
        
        if not camera_data:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': 'No camera data provided'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Add camera to database
        camera_id = add_camera(camera_data)
        
        if camera_id:
            response_data = {
                'success': True,
                'message': 'Camera registered successfully',
                'camera_id': camera_id
            }
            status_code = 201
        else:
            response_data = {
                'success': False,
                'message': 'Failed to register camera'
            }
            status_code = 500
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error adding camera: {e}")
        error_response = {
            'success': False,
            'message': f'Error adding camera: {str(e)}'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/cameras/<camera_id>/status', methods=['PUT'])
def update_camera_status_endpoint(camera_id):
    """Update camera active status."""
    try:
        # Get status data from request
        data = request.get_json()
        
        if not data:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': 'No status data provided'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        is_active = data.get('is_active')
        
        if is_active not in ['Y', 'N']:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': 'Invalid status value. Must be Y or N.'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Update camera status in database
        result = update_camera_status(camera_id, is_active)
        
        if result:
            response_data = {
                'success': True,
                'message': f'Camera {camera_id} status updated successfully'
            }
            status_code = 200
        else:
            response_data = {
                'success': False,
                'message': f'Failed to update camera {camera_id} status'
            }
            status_code = 500
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error updating camera status: {e}")
        error_response = {
            'success': False,
            'message': f'Error updating camera status: {str(e)}'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/face-recognition-url', methods=['GET'])
def get_face_recognition_url():
    """Return the URL for the face recognition system."""
    try:
        # Return the URL for the face recognition system
        response_data = {
            'success': True,
            'url': FACE_RECOGNITION_URL
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error getting face recognition URL: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/user-registration', methods=['POST'])
def user_registration():
    """Create a new user registration request."""
    try:
        # Get registration data from request
        request_data = request.get_json()
        
        # Validate required fields (making designation and email optional)
        required_fields = ['full_name', 'employee_id', 'department']
        for field in required_fields:
            if not request_data.get(field):
                return app.response_class(
                    response=json.dumps({
                        'success': False,
                        'message': f'{field} is required'
                    }, default=json_serializer),
                    status=400,
                    mimetype='application/json'
                )
        
        # Check if employee ID already exists in registration requests
        check_query = "SELECT COUNT(*) as count FROM ADMIN_REGISTRATION_REQUESTS WHERE EMPLOYEE_ID = :employee_id"
        existing_requests = execute_query(check_query, {'employee_id': request_data['employee_id']})
        if existing_requests and existing_requests[0]['COUNT'] > 0:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': 'Registration request already exists for this employee ID'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Check if employee ID already has access
        if check_user_access(request_data['employee_id']):
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': 'User already has access to the system'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Create registration request
        request_id = create_registration_request(request_data)
        
        if request_id:
            response_data = {
                'success': True,
                'message': 'Registration request submitted successfully',
                'request_id': request_id
            }
            status_code = 201
        else:
            response_data = {
                'success': False,
                'message': 'Failed to submit registration request'
            }
            status_code = 500
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error creating registration request: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred while processing your request'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/registration-requests', methods=['GET'])
def get_registration_requests():
    """Get all pending registration requests."""
    try:
        requests = get_pending_registration_requests()
        response_data = {
            'success': True,
            'data': requests,
            'count': len(requests)
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving registration requests: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/registered-users', methods=['GET'])
def get_registered_users_endpoint():
    """Retrieve all registered users from the REGISTERED_USERS table."""
    try:
        users = get_registered_users()
        response_data = {
            'success': True,
            'data': users,
            'count': len(users)
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving registered users: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/registration-requests/<int:request_id>/approve', methods=['POST'])
def approve_request(request_id):
    """Approve a registration request."""
    try:
        # Get approver info from request (in real app, this would come from authenticated user)
        data = request.get_json()
        approved_by = data.get('approved_by', 'System')
        
        # Approve the request
        result = approve_registration_request(request_id, approved_by)
        
        if result:
            response_data = {
                'success': True,
                'message': f'Registration request {request_id} approved successfully'
            }
            status_code = 200
        else:
            response_data = {
                'success': False,
                'message': f'Failed to approve registration request {request_id}'
            }
            status_code = 500
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error approving registration request: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred while processing your request'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/registration-requests/<int:request_id>/reject', methods=['POST'])
def reject_request(request_id):
    """Reject a registration request."""
    try:
        # Get rejector info from request (in real app, this would come from authenticated user)
        data = request.get_json()
        rejected_by = data.get('rejected_by', 'System')
        
        # Reject the request
        result = reject_registration_request(request_id, rejected_by)
        
        if result:
            response_data = {
                'success': True,
                'message': f'Registration request {request_id} rejected successfully'
            }
            status_code = 200
        else:
            response_data = {
                'success': False,
                'message': f'Failed to reject registration request {request_id}'
            }
            status_code = 500
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error rejecting registration request: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred while processing your request'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/access-granted-users', methods=['GET'])
def get_granted_users():
    """Get all users who have been granted access."""
    try:
        from db_connection import get_access_granted_users_with_admin
        users = get_access_granted_users_with_admin()
        response_data = {
            'success': True,
            'data': users,
            'count': len(users)
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving granted users: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/access-granted-users/direct-grant', methods=['POST'])
def direct_grant_access():
    """Directly grant access to a user without requiring registration request."""
    try:
        # Get user data from request
        user_data = request.get_json()
        
        # Validate required fields
        required_fields = ['employee_id', 'full_name', 'department']
        for field in required_fields:
            if not user_data.get(field):
                return app.response_class(
                    response=json.dumps({
                        'success': False,
                        'message': f'{field} is required'
                    }, default=json_serializer),
                    status=400,
                    mimetype='application/json'
                )
        
        # Get granter info from request (in real app, this would come from authenticated user)
        granted_by = user_data.get('granted_by', 'System')
        
        # Grant direct access
        result = grant_direct_access(user_data, granted_by)
        
        if result:
            response_data = {
                'success': True,
                'message': 'User access granted successfully'
            }
            status_code = 201
        else:
            response_data = {
                'success': False,
                'message': 'Employee ID already exists or failed to grant access'
            }
            status_code = 400
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error granting direct access: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred while processing your request'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/access-granted-users/<int:user_id>/revoke', methods=['POST'])
def revoke_user(user_id):
    """Revoke user access."""
    try:
        # Get revoker info from request (in real app, this would come from authenticated user)
        data = request.get_json()
        revoked_by = data.get('revoked_by', 'System')
        
        # Revoke user access
        result = revoke_user_access(user_id, revoked_by)
        
        if result:
            response_data = {
                'success': True,
                'message': f'User access {user_id} revoked successfully'
            }
            status_code = 200
        else:
            response_data = {
                'success': False,
                'message': f'Failed to revoke user access {user_id}'
            }
            status_code = 500
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error revoking user access: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred while processing your request'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/access-granted-users/<int:user_id>/allow', methods=['POST'])
def allow_user(user_id):
    """Allow user access."""
    try:
        # Get allow info from request (in real app, this would come from authenticated user)
        data = request.get_json()
        allowed_by = data.get('allowed_by', 'System')
        
        # Allow user access
        result = allow_user_access(user_id, allowed_by)
        
        if result:
            response_data = {
                'success': True,
                'message': f'User access {user_id} allowed successfully'
            }
            status_code = 200
        else:
            response_data = {
                'success': False,
                'message': f'Failed to allow user access {user_id}'
            }
            status_code = 500
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error allowing user access: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred while processing your request'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/admin-access-users', methods=['GET'])
def get_admin_access_users():
    """Get all users who have admin access (ADMIN_ACCESS = 'Y')."""
    try:
        from db_connection import get_access_granted_users_with_admin
        all_users = get_access_granted_users_with_admin()
        
        # Filter only users with admin access
        admin_users = [user for user in all_users if user.get('ADMIN_ACCESS') == 'Y']
        
        response_data = {
            'success': True,
            'data': admin_users,
            'count': len(admin_users)
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving admin access users: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/admin-access-users/<int:user_id>/revoke', methods=['POST'])
def revoke_admin_access(user_id):
    """Revoke admin access by setting ADMIN_ACCESS to 'N'."""
    try:
        # Get revoker info from request (in real app, this would come from authenticated user)
        data = request.get_json()
        revoked_by = data.get('revoked_by', 'System')
        
        from db_connection import revoke_admin_access as revoke_admin_func
        result = revoke_admin_func(user_id, revoked_by)
        
        if result:
            response_data = {
                'success': True,
                'message': f'Admin access for user {user_id} revoked successfully'
            }
            status_code = 200
        else:
            response_data = {
                'success': False,
                'message': f'Failed to revoke admin access for user {user_id}'
            }
            status_code = 500
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error revoking admin access: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred while processing your request'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/grant-admin-access', methods=['POST'])
def grant_admin_access():
    """Grant admin access to a user by employee ID."""
    try:
        # Get user data from request
        user_data = request.get_json()
        employee_id = user_data.get('employee_id')
        
        if not employee_id:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': 'Employee ID is required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        from db_connection import grant_admin_access as grant_admin_func
        granted_by = user_data.get('granted_by', 'System')
        result = grant_admin_func(employee_id, granted_by)
        
        if result:
            response_data = {
                'success': True,
                'message': f'Admin access granted to {employee_id} successfully',
                'user': result
            }
            status_code = 200
        else:
            response_data = {
                'success': False,
                'message': f'User with employee ID {employee_id} does not have access to the system'
            }
            status_code = 404
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=status_code,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error granting admin access: {e}")
        error_response = {
            'success': False,
            'message': 'An error occurred while processing your request'
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/downtime-summary', methods=['GET'])
def get_downtime_summary():
    """Retrieve employee downtime summary data."""
    try:
        # Get date range from query parameters or use defaults
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # If no dates provided, use last 7 days
        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        downtime_data = get_employee_downtime_summary(from_date, to_date)
        
        response_data = {
            'success': True,
            'data': downtime_data,
            'count': len(downtime_data),
            'from_date': from_date,
            'to_date': to_date
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving downtime summary: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )



@app.route('/api/employee-movement', methods=['GET'])
def get_employee_movement():
    """Retrieve employee movement data based on provided parameters."""
    try:
        # Get parameters from query string
        employee_id = request.args.get('employee_id')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        gap_min = request.args.get('gap_min', '15')  # Default to 15 minutes
        
        # Validate required parameters
        if not from_date:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'error': 'From Date is required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # If to_date is not provided, use current date
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Validate and convert gap_min to integer
        try:
            gap_min = int(gap_min)
        except ValueError:
            gap_min = 15  # Default to 15 minutes if invalid
        
        # Get movement data
        movement_data = get_employee_movement_data(employee_id, from_date, to_date, gap_min)
        
        response_data = {
            'success': True,
            'data': movement_data,
            'count': len(movement_data),
            'employee_id': employee_id,
            'from_date': from_date,
            'to_date': to_date
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving employee movement: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

@app.route('/api/daily-inout-summary', methods=['GET'])
def get_daily_inout_summary():
    """Retrieve daily IN/OUT summary data based on provided parameters."""
    try:
        # Get parameters from query string
        employee_id = request.args.get('employee_id')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # Validate required parameters
        if not from_date:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'error': 'From Date is required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # If to_date is not provided, use current date
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get IN/OUT summary data
        inout_data = get_daily_inout_summary_data(employee_id, from_date, to_date)
        
        response_data = {
            'success': True,
            'data': inout_data,
            'count': len(inout_data),
            'employee_id': employee_id,
            'from_date': from_date,
            'to_date': to_date
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving daily IN/OUT summary: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/employee-inout-details', methods=['GET'])
def get_employee_inout_details():
    """Retrieve detailed employee IN/OUT movement data for explainable analytics."""
    try:
        # Get parameters from query string
        employee_id = request.args.get('employee_id')
        rec_date = request.args.get('rec_date')  # Single date for detailed view
        
        # Validate required parameters
        if not employee_id:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'error': 'Employee ID is required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        if not rec_date:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'error': 'Record Date is required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Get summary data (from existing Step 6 function)
        summary_data = get_daily_inout_summary_data(employee_id, rec_date, rec_date)
        
        # Get movement transitions (from new Step 4 function)
        transitions_data = get_employee_movement_transitions(employee_id, rec_date, rec_date)
        
        # Get raw movement data (from existing function)
        raw_movement_data = get_employee_movement_data(employee_id, rec_date, rec_date, 0)  # gap_min not relevant here
        
        response_data = {
            'success': True,
            'summary_data': summary_data,
            'transitions_data': transitions_data,
            'raw_movement_data': raw_movement_data,
            'employee_id': employee_id,
            'rec_date': rec_date
        }
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving employee IN/OUT details: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/daily-presence-distribution', methods=['GET'])
def get_daily_presence_distribution():
    """Retrieve daily presence distribution (total inside vs outside time across all employees for a given date)."""
    try:
        # Get date from query string
        date = request.args.get('date')
        
        # Validate required parameters
        if not date:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'error': 'Date is required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Get IN/OUT summary data for the specified date
        inout_data = get_daily_inout_summary_data(None, date, date)  # None for employee_id to get all
        
        # Calculate total inside and outside minutes
        total_inside_minutes = sum(record.get('TOTAL_INSIDE_MINUTES', 0) for record in inout_data)
        total_outside_minutes = sum(record.get('TOTAL_OUTSIDE_MINUTES', 0) for record in inout_data)
        total_minutes = total_inside_minutes + total_outside_minutes
        
        # Calculate percentages
        inside_percentage = (total_inside_minutes / total_minutes * 100) if total_minutes > 0 else 0
        outside_percentage = (total_outside_minutes / total_minutes * 100) if total_minutes > 0 else 0
        
        response_data = {
            'success': True,
            'data': {
                'date': date,
                'inside_minutes': total_inside_minutes,
                'outside_minutes': total_outside_minutes,
                'total_minutes': total_minutes,
                'inside_percentage': round(inside_percentage, 2),
                'outside_percentage': round(outside_percentage, 2)
            }
        }
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving daily presence distribution: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/top-employee-movement', methods=['GET'])
def get_top_employee_movement_rankings():
    """Retrieve top employee movement rankings based on selected metric (inside/outside time)."""
    try:
        # Get parameters from query string
        date = request.args.get('date')
        metric = request.args.get('metric', 'outside')  # Default to 'outside'
        limit = request.args.get('limit', '5')  # Default to top 5
        
        # Validate required parameters
        if not date:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'error': 'Date is required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Validate metric parameter
        if metric not in ['inside', 'outside']:
            metric = 'outside'
        
        # Validate and convert limit to integer
        try:
            limit = int(limit)
            if limit <= 0 or limit > 50:  # Set reasonable limit
                limit = 5
        except ValueError:
            limit = 5  # Default to 5 if invalid
        
        # Get IN/OUT summary data for the specified date
        inout_data = get_daily_inout_summary_data(None, date, date)  # None for employee_id to get all
        
        # Filter out records with no movement data
        valid_records = []
        for record in inout_data:
            if metric == 'outside':
                if record.get('TOTAL_OUTSIDE_MINUTES', 0) > 0:
                    valid_records.append(record)
            else:  # inside
                if record.get('TOTAL_INSIDE_MINUTES', 0) > 0:
                    valid_records.append(record)
        
        # Sort by the appropriate metric
        if metric == 'outside':
            sorted_records = sorted(valid_records, key=lambda x: x.get('TOTAL_OUTSIDE_MINUTES', 0), reverse=True)
        else:
            sorted_records = sorted(valid_records, key=lambda x: x.get('TOTAL_INSIDE_MINUTES', 0), reverse=True)
        
        # Limit the results
        top_records = sorted_records[:limit]
        
        response_data = {
            'success': True,
            'data': top_records,
            'count': len(top_records),
            'date': date,
            'metric': metric,
            'limit': limit
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving top employee movement rankings: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/top-floor-visitors', methods=['GET'])
def get_top_floor_visitors_endpoint():
    """Retrieve top floor visitors based on unique floors visited for a given date."""
    try:
        # Get parameters from query string
        date = request.args.get('date')
        limit = request.args.get('limit', '5')  # Default to top 5
        
        # Validate required parameters
        if not date:
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'error': 'Date is required'
                }, default=json_serializer),
                status=400,
                mimetype='application/json'
            )
        
        # Validate and convert limit to integer
        try:
            limit = int(limit)
            if limit <= 0 or limit > 50:  # Set reasonable limit
                limit = 5
        except ValueError:
            limit = 5  # Default to 5 if invalid
        
        # Get top floor visitors data for the specified date
        floor_visitor_data = get_top_floor_visitors(date, limit)
        
        response_data = {
            'success': True,
            'data': floor_visitor_data,
            'count': len(floor_visitor_data),
            'date': date,
            'limit': limit
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving top floor visitors: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/location-coverage-report', methods=['GET'])
def get_location_coverage_report():
    """Retrieve employee unique visit summary data (Location Coverage Report)."""
    try:
        # Get parameters from query string
        employee_id = request.args.get('employee_id')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # Call the function from db_connection with the proper parameters
        coverage_data = get_employee_unique_visit_summary(
            employee_id=employee_id, 
            from_date=from_date, 
            to_date=to_date
        )
        
        response_data = {
            'success': True,
            'data': coverage_data,
            'count': len(coverage_data),
            'employee_id': employee_id,
            'from_date': from_date,
            'to_date': to_date
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving location coverage report: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )

# Calculate new KPIs based on existing functions
def calculate_new_kpis(from_date, to_date):
    """Calculate the new KPIs based on existing data functions."""
    # Get downtime summary data
    downtime_data = get_employee_downtime_summary(from_date, to_date)
    
    # Get IN/OUT summary data
    inout_data = get_daily_inout_summary_data(None, from_date, to_date)  # None for employee_id to get all
    
    # Get location coverage data
    location_coverage_data = get_employee_unique_visit_summary(None, from_date, to_date)
    
    # KPI 1: Employees with Outside Time
    total_employees_with_downtime = len([emp for emp in downtime_data if emp.get('DOWNTIME_MINUTES', 0) > 0])
    total_employees = len(set(emp['EMPLOYEE_ID'] for emp in downtime_data))
    employees_with_outside_time_percentage = (total_employees_with_downtime / total_employees * 100) if total_employees > 0 else 0
    
    # KPI 2: Average Outside Time per Employee
    total_downtime_minutes = sum(emp.get('DOWNTIME_MINUTES', 0) for emp in downtime_data)
    avg_outside_time = (total_downtime_minutes / total_employees) if total_employees > 0 else 0
    
    # Get yesterday's data for comparison
    yesterday = (datetime.strptime(from_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_downtime_data = get_employee_downtime_summary(yesterday, yesterday)
    if yesterday_downtime_data:
        yesterday_total_downtime_minutes = sum(emp.get('DOWNTIME_MINUTES', 0) for emp in yesterday_downtime_data)
        yesterday_total_employees = len(set(emp['EMPLOYEE_ID'] for emp in yesterday_downtime_data))
        yesterday_avg_outside_time = (yesterday_total_downtime_minutes / yesterday_total_employees) if yesterday_total_employees > 0 else 0
        avg_comparison = avg_outside_time - yesterday_avg_outside_time
    else:
        avg_comparison = 0
    
    # KPI 3: Highest Outside Time (Worst Case)
    if downtime_data:
        highest_downtime_record = max(downtime_data, key=lambda x: x.get('DOWNTIME_MINUTES', 0))
        highest_outside_time = highest_downtime_record.get('DOWNTIME_MINUTES', 0)
        worst_case_employee = highest_downtime_record.get('EMPLOYEE_ID', 'N/A')
    else:
        highest_outside_time = 0
        worst_case_employee = 'N/A'
    
    # KPI 4: Inside vs Outside Ratio
    total_inside_minutes = sum(record.get('TOTAL_INSIDE_MINUTES', 0) for record in inout_data)
    total_outside_minutes = sum(record.get('TOTAL_OUTSIDE_MINUTES', 0) for record in inout_data)
    total_time = total_inside_minutes + total_outside_minutes
    inside_percentage = (total_inside_minutes / total_time * 100) if total_time > 0 else 0
    outside_percentage = (total_outside_minutes / total_time * 100) if total_time > 0 else 0
    
    # KPI 5: High Location Coverage Employees (visited > 3 floors)
    high_coverage_threshold = 3
    high_coverage_employees = [emp for emp in location_coverage_data if emp.get('UNIQUE_FLOORS_VISITED', 0) >= high_coverage_threshold]
    high_coverage_count = len(high_coverage_employees)
    
    # KPI 6: Employees with high outside time (> average)
    high_outside_threshold = avg_outside_time if avg_outside_time > 0 else 30  # Default to 30 min if avg is 0
    high_outside_employees = [emp for emp in downtime_data if emp.get('DOWNTIME_MINUTES', 0) > high_outside_threshold]
    high_outside_count = len(high_outside_employees)
    
    return {
        'employees_with_outside_time': {
            'count_with_outside': total_employees_with_downtime,
            'total_employees': total_employees,
            'percentage': round(employees_with_outside_time_percentage, 1)
        },
        'avg_outside_time': {
            'minutes': round(avg_outside_time, 1),
            'comparison_to_yesterday': round(avg_comparison, 1),
            'is_higher_than_yesterday': avg_comparison > 0
        },
        'highest_outside_time': {
            'minutes': highest_outside_time,
            'hours_formatted': f"{int(highest_outside_time // 60)}h {int(highest_outside_time % 60)}m",
            'employee_id': worst_case_employee
        },
        'inside_vs_outside_ratio': {
            'inside_percentage': round(inside_percentage, 1),
            'outside_percentage': round(outside_percentage, 1),
            'inside_minutes': round(total_inside_minutes),
            'outside_minutes': round(total_outside_minutes)
        },
        'high_location_coverage_employees': {
            'count': high_coverage_count,
            'threshold': high_coverage_threshold,
            'employees': high_coverage_employees[:10]  # Top 10 for detail if needed
        },
        'high_outside_employees': {
            'count': high_outside_count,
            'threshold': round(high_outside_threshold, 1),
            'percentage': round((high_outside_count / total_employees * 100) if total_employees > 0 else 0, 1)
        }
    }


@app.route('/api/new-dashboard-kpis', methods=['GET'])
def get_new_dashboard_kpis():
    """Retrieve the new KPIs for the dashboard."""
    try:
        # Get date range from query parameters or use defaults
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # If no dates provided, use today
        if not from_date:
            from_date = datetime.now().strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        kpis = calculate_new_kpis(from_date, to_date)
        
        response_data = {
            'success': True,
            'kpis': kpis,
            'from_date': from_date,
            'to_date': to_date
        }
        
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving new dashboard KPIs: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


@app.route('/api/location-coverage/details', methods=['GET'])
def get_location_coverage_details_endpoint():
    """Retrieve detailed location coverage data for a specific employee on a specific date."""
    try:
        # Get parameters from query string
        employee_id = request.args.get('employee_id')
        date = request.args.get('date')
        
        if not employee_id or not date:
            return app.response_class(
                response=json.dumps({'success': False, 'error': 'employee_id and date are required'}),
                status=400,
                mimetype='application/json'
            )
        
        # Call the function from db_connection with the proper parameters
        details_data = get_location_coverage_details(
            employee_id=employee_id, 
            date=date
        )
        
        # Get employee info for the summary
        employee_summary = {}
        if details_data:
            first_record = details_data[0]
            employee_summary = {
                'employee_id': first_record['EMPLOYEE_ID'],
                'name': first_record['NAME'],
                'department': first_record['DEPARTMENT']
            }
        else:
            # If no data found, still return employee info based on parameters
            employee_summary = {
                'employee_id': employee_id,
                'name': 'Unknown',
                'department': 'Unknown'
            }
        
        # Calculate summary statistics
        unique_buildings = 0
        unique_floors = 0
        total_segments = 0
        
        if details_data:
            total_segments = len(details_data)
            unique_buildings = len(set(str(record['BUILDING_NAME']) for record in details_data if record['BUILDING_NAME'] is not None and str(record['BUILDING_NAME']).strip() != ''))
            unique_floors = len(set(str(record['FLOOR_NAME']) for record in details_data if record['FLOOR_NAME'] is not None and str(record['FLOOR_NAME']).strip() != ''))
        
        response_data = {
            'success': True,
            'data': details_data,
            'employee_summary': employee_summary,
            'summary_stats': {
                'unique_buildings_visited': unique_buildings,
                'unique_floors_visited': unique_floors,
                'total_location_segments': total_segments
            },
            'employee_id': employee_id,
            'date': date
        }
        return app.response_class(
            response=json.dumps(response_data, default=json_serializer),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error retrieving location coverage details: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        return app.response_class(
            response=json.dumps(error_response, default=json_serializer),
            status=500,
            mimetype='application/json'
        )


if __name__ == '__main__':
    app.run(host=BACKEND_HOST, port=BACKEND_PORT, debug=True)
