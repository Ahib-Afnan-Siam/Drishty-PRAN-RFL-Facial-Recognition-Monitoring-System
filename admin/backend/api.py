"""
API routes for the admin dashboard.
Provides RESTful endpoints for accessing admin data.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime, timedelta, date, time
from decimal import Decimal
import json
import cx_Oracle
from db_connection import get_camera_registry, get_employee_daily_summary, get_db_connection, close_db_connection, authenticate_user_hris_api, add_camera, update_camera_status, check_user_access, create_registration_request, get_pending_registration_requests, approve_registration_request, reject_registration_request, get_access_granted_users, revoke_user_access, grant_direct_access, execute_query

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
CORS(app, origins=["http://localhost:8001"])  # Enable CORS specifically for the frontend origin

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
        
        response_data = {
            'success': True,
            'data': summary_data,
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
            'url': 'http://127.0.0.1:8000'
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
        users = get_access_granted_users()
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
