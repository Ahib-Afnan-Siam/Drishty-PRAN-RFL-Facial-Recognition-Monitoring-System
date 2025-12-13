"""
Database connection module for the admin dashboard.
Handles connections to the DRISHTI Oracle database.
"""

import cx_Oracle
import logging
import sys
import os
import requests
import json
from datetime import datetime, date, time, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from db_config import get_db_config, get_connection_string

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_datetime(obj):
    """Convert datetime objects to string representation for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        # Convert timedelta to string representation
        return str(obj)
    return obj

def get_db_connection():
    """
    Establishes and returns a connection to the Oracle database.
    
    Returns:
        cx_Oracle.Connection: Database connection object
    """
    try:
        # Get connection string from config
        connection_string = get_connection_string()
        
        # Create connection
        connection = cx_Oracle.connect(connection_string)
        logger.info("Successfully connected to the database")
        return connection
    except cx_Oracle.Error as error:
        logger.error(f"Error connecting to database: {error}")
        raise

def close_db_connection(connection):
    """
    Closes the database connection.
    
    Args:
        connection (cx_Oracle.Connection): Database connection object to close
    """
    try:
        if connection:
            connection.close()
            logger.info("Database connection closed")
    except cx_Oracle.Error as error:
        logger.error(f"Error closing database connection: {error}")

def execute_query(query, params=None):
    """
    Executes a SELECT query and returns the results.
    
    Args:
        query (str): SQL query to execute
        params (dict, optional): Query parameters
        
    Returns:
        list: Query results as list of tuples
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        # Convert to list of dictionaries for easier handling
        result_dicts = []
        for row in results:
            # Process each value to handle datetime objects
            processed_row = []
            for value in row:
                processed_row.append(convert_datetime(value))
            
            result_dicts.append(dict(zip(columns, processed_row)))
            
        return result_dicts
    except cx_Oracle.Error as error:
        logger.error(f"Error executing query: {error}")
        raise
    finally:
        if connection:
            close_db_connection(connection)

def update_camera_status(camera_id, is_active):
    """
    Update camera active status
    
    Args:
        camera_id (str): Camera ID
        is_active (str): 'Y' for active, 'N' for inactive
        
    Returns:
        bool: True if successful, False otherwise
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        sql = """
            UPDATE CAMERA_REGISTRY 
            SET IS_ACTIVE = :1, UPDATED_AT = SYSDATE, UPDATED_BY = :2
            WHERE CAMERA_ID = :3
        """
        
        # Get current user for UPDATED_BY field
        updated_by = 'System'  # Default value
        
        cursor.execute(sql, [is_active, updated_by, camera_id])
        connection.commit()
        
        status = "activated" if is_active == 'Y' else "deactivated"
        logger.info(f"Successfully {status} camera {camera_id}")
        
        return True
    except cx_Oracle.Error as e:
        logger.error(f"Failed to update camera status for {camera_id}: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            close_db_connection(connection)

def authenticate_user_hris_api(username, password):
    """
    Authenticate user against HRIS system using the REST API.
    
    Args:
        username (str): Employee username
        password (str): HRIS password
        
    Returns:
        bool: True if authentication is successful, False otherwise
    """
    try:
        # HRIS API endpoint
        url = 'http://hrisapi.prangroup.com:8083/v1/Login/UserValidationAp'
        
        # Prepare the payload
        payload = {
            "UserName": username,
            "Password": password
        }
        
        # Set headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic YXV0aDoxMlByYW5AMTIzNDU2JA==',
            'S_KEYL': 'RxsJ4LQdkVFTv37rYfW9b6'
        }
        
        # Make the POST request
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Check if request was successful
        if response.status_code == 200:
            # Parse JSON response
            response_data = response.json()
            # Check if isSuccess is true
            return response_data.get('isSuccess', False) == True
        else:
            logger.error(f"HRIS API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to HRIS API: {e}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing HRIS API response: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during HRIS authentication: {e}")
        return False

def get_camera_registry():
    """
    Retrieves all camera registry records.
    
    Returns:
        list: Camera registry records
    """
    query = """
    SELECT 
        CAMERA_ID,
        CAMERA_NAME,
        LOCATION_TYPE,
        SITE_NAME,
        BUILDING_NAME,
        FLOOR_NO,
        FLOOR_NAME,
        LINE_NO,
        LINE_NAME,
        AREA_NAME,
        DIRECTION,
        IP_ADDRESS,
        RTSP_URL,
        IS_ACTIVE,
        USER_NAME,
        PASSWORDS,
        INSTALL_DATE,
        CREATED_BY,
        CREATED_AT,
        UPDATED_BY,
        UPDATED_AT
    FROM CAMERA_REGISTRY
    ORDER BY CAMERA_ID
    """
    return execute_query(query)

def get_employee_daily_summary(from_date, to_date):
    """
    Retrieves employee daily summary data.
    
    Args:
        from_date (str): Start date in YYYY-MM-DD format
        to_date (str): End date in YYYY-MM-DD format
        
    Returns:
        list: Employee daily summary records
    """
    query = """
    SELECT
        TRUNC(v.RECOGNITION_TIMESTAMP) AS REC_DATE,
        v.EMPLOYEE_ID,
        v.NAME,
        v.DEPARTMENT,
        MIN(v.RECOGNITION_TIMESTAMP) AS FIRST_SEEN_TS,
        MAX(v.RECOGNITION_TIMESTAMP) AS LAST_SEEN_TS,
        TO_CHAR(MIN(v.RECOGNITION_TIMESTAMP), 'HH24:MI:SS') AS FIRST_SEEN_TIME,
        TO_CHAR(MAX(v.RECOGNITION_TIMESTAMP), 'HH24:MI:SS') AS LAST_SEEN_TIME,
        MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP) AS TOTAL_SPAN,
        ROUND(
            EXTRACT(DAY    FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) * 1440 +
            EXTRACT(HOUR   FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) * 60 +
            EXTRACT(MINUTE FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) +
            EXTRACT(SECOND FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) / 60,
            2
        ) AS TOTAL_SPAN_MINUTES,
        ROUND(
            EXTRACT(DAY    FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) * 24 +
            EXTRACT(HOUR   FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) +
            EXTRACT(MINUTE FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) / 60 +
            EXTRACT(SECOND FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) / 3600,
            2
        ) AS TOTAL_SPAN_HOURS,
        LPAD(
            FLOOR(
                EXTRACT(DAY    FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) * 24 +
                EXTRACT(HOUR   FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) +
                EXTRACT(MINUTE FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) / 60
            ),
            2, '0'
        ) || ':' ||
        LPAD(
            MOD(
                FLOOR(
                    EXTRACT(DAY    FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) * 1440 +
                    EXTRACT(HOUR   FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP))) * 60 +
                    EXTRACT(MINUTE FROM (MAX(v.RECOGNITION_TIMESTAMP) - MIN(v.RECOGNITION_TIMESTAMP)))
                ),
                60
            ),
            2, '0'
        ) AS TOTAL_SPAN_HHMM,
        COUNT(*) AS TOTAL_HITS,
        COUNT(DISTINCT v.CAMERA_ID) AS TOTAL_FLOOR
    FROM V_RECOGNITION_LOGS_ENRICHED v
    WHERE TRUNC(v.RECOGNITION_TIMESTAMP) BETWEEN TO_DATE(:from_date, 'YYYY-MM-DD') AND TO_DATE(:to_date, 'YYYY-MM-DD')
    GROUP BY
        TRUNC(v.RECOGNITION_TIMESTAMP),
        v.EMPLOYEE_ID,
        v.NAME,
        v.DEPARTMENT
    ORDER BY
        REC_DATE,
        v.EMPLOYEE_ID
    """
    return execute_query(query, {'from_date': from_date, 'to_date': to_date})

def add_camera(camera_data):
    """
    Add a new camera to the CAMERA_REGISTRY table.
    
    Args:
        camera_data (dict): Dictionary containing camera information
        
    Returns:
        str: The generated camera ID if successful, None otherwise
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Get the next camera ID from the sequence
        cursor.execute("SELECT CAMERA_ID_SEQ.NEXTVAL FROM DUAL")
        camera_id = str(cursor.fetchone()[0])
        
        # Insert the camera data
        sql = """
            INSERT INTO CAMERA_REGISTRY (
                CAMERA_ID, CAMERA_NAME, COMPANY_CODE, COMPANY_NAME,
                DEPARTMENT_CODE, DEPARTMENT_NAME, LOCATION_TYPE,
                SITE_CODE, SITE_NAME, BUILDING_CODE, BUILDING_NAME,
                FLOOR_NO, FLOOR_NAME, WING_NAME, ROOM_NO, ROOM_NAME,
                LINE_NO, LINE_NAME, AREA_NAME, DIRECTION,
                CAMERA_CATEGORY, CAMERA_TYPE, CAMERA_BRAND, CAMERA_MODEL,
                SERIAL_NO, CAMERA_MP, CAMERA_RESOLUTION, FIRMWARE_VERSION,
                IP_ADDRESS, RTSP_URL, USER_NAME, PASSWORDS,
                LATITUDE, LONGITUDE, IS_ACTIVE, INSTALL_DATE,
                CREATED_BY
            ) VALUES (
                :1, :2, :3, :4, :5, :6, :7, :8, :9, :10,
                :11, :12, :13, :14, :15, :16, :17, :18, :19, :20,
                :21, :22, :23, :24, :25, :26, :27, :28, :29, :30,
                :31, :32, :33, :34, :35, :36, :37
            )
        """
        
        params = [
            camera_id,
            camera_data.get('camera_name', ''),
            camera_data.get('company_code'),
            camera_data.get('company_name'),
            camera_data.get('department_code'),
            camera_data.get('department_name'),
            camera_data.get('location_type', 'Indoor'),
            camera_data.get('site_code'),
            camera_data.get('site_name'),
            camera_data.get('building_code'),
            camera_data.get('building_name'),
            camera_data.get('floor_no'),
            camera_data.get('floor_name'),
            camera_data.get('wing_name'),
            camera_data.get('room_no'),
            camera_data.get('room_name'),
            camera_data.get('line_no'),
            camera_data.get('line_name'),
            camera_data.get('area_name'),
            camera_data.get('direction'),
            camera_data.get('camera_category'),
            camera_data.get('camera_type'),
            camera_data.get('camera_brand'),
            camera_data.get('camera_model'),
            camera_data.get('serial_no'),
            camera_data.get('camera_mp'),
            camera_data.get('camera_resolution'),
            camera_data.get('firmware_version'),
            camera_data.get('ip_address', ''),
            camera_data.get('rtsp_url', ''),
            camera_data.get('user_name'),
            camera_data.get('passwords'),
            camera_data.get('latitude'),
            camera_data.get('longitude'),
            camera_data.get('is_active', 'Y'),
            camera_data.get('install_date'),
            camera_data.get('created_by', 'System')
        ]
        
        cursor.execute(sql, params)
        connection.commit()
        
        return camera_id
    except cx_Oracle.Error as e:
        logger.error(f"Error adding camera: {e}")
        if connection:
            connection.rollback()
        return None
    finally:
        if connection:
            close_db_connection(connection)

def revoke_user_access(user_id, revoked_by):
    """
    Revoke user access by setting IS_ACTIVE to 'N'
    
    Args:
        user_id (int): User ID to revoke access for
        revoked_by (str): User who revoked the access
        
    Returns:
        bool: True if successful, False otherwise
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        sql = """
            UPDATE ADMIN_ACCESS_GRANTED_USERS
            SET IS_ACTIVE = 'N', UPDATED_AT = SYSDATE
            WHERE USER_ID = :1
        """
        
        cursor.execute(sql, [user_id])
        
        connection.commit()
        logger.info(f"User access {user_id} revoked by {revoked_by}")
        
        return True
    except cx_Oracle.Error as e:
        logger.error(f"Error revoking user access: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            close_db_connection(connection)


def grant_direct_access(user_data, granted_by):
    """
    Directly grant access to a user without requiring registration request
    
    Args:
        user_data (dict): User data including employee_id, full_name, department, etc.
        granted_by (str): User who granted the access (typically admin)
        
    Returns:
        bool: True if successful, False otherwise
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Check if employee_id already exists in ADMIN_ACCESS_GRANTED_USERS
        check_query = """
            SELECT COUNT(*) as count 
            FROM ADMIN_ACCESS_GRANTED_USERS 
            WHERE EMPLOYEE_ID = :employee_id
        """
        check_result = execute_query(check_query, {'employee_id': user_data['employee_id']})
        
        if check_result and check_result[0]['COUNT'] > 0:
            logger.warning(f"Employee ID {user_data['employee_id']} already exists in access granted users")
            return False
        
        # Insert into ADMIN_ACCESS_GRANTED_USERS
        insert_sql = """
            INSERT INTO ADMIN_ACCESS_GRANTED_USERS (
                FULL_NAME, EMPLOYEE_ID, DEPARTMENT, DESIGNATION, EMAIL, CREATED_BY, IS_ACTIVE
            ) VALUES (:1, :2, :3, :4, :5, :6, :7)
        """
        
        cursor.execute(insert_sql, [
            user_data.get('full_name'),
            user_data.get('employee_id'),
            user_data.get('department'),
            user_data.get('designation', ''),
            user_data.get('email', ''),
            granted_by,
            'Y'  # Active by default
        ])
        
        connection.commit()
        logger.info(f"Direct access granted to {user_data.get('employee_id')} by {granted_by}")
        
        return True
    except cx_Oracle.Error as e:
        logger.error(f"Error granting direct access: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            close_db_connection(connection)

def check_user_access(employee_id):
    """
    Check if Employee ID exists in Access Granted User List (local database)
    
    Args:
        employee_id (str): Employee ID to check
        
    Returns:
        bool: True if user has access, False otherwise
    """
    query = """
        SELECT COUNT(*) as count 
        FROM ADMIN_ACCESS_GRANTED_USERS 
        WHERE EMPLOYEE_ID = :employee_id AND IS_ACTIVE = 'Y'
    """
    try:
        results = execute_query(query, {'employee_id': employee_id})
        return results[0]['COUNT'] > 0 if results else False
    except Exception as e:
        logger.error(f"Error checking user access: {e}")
        return False

def create_registration_request(request_data):
    """
    Create a new user registration request
    
    Args:
        request_data (dict): Registration request data
        
    Returns:
        int: Request ID if successful, None otherwise
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Use RETURNING clause to get the inserted ID
        sql = """
            INSERT INTO ADMIN_REGISTRATION_REQUESTS (
                FULL_NAME, EMPLOYEE_ID, DEPARTMENT, DESIGNATION, EMAIL
            ) VALUES (:1, :2, :3, :4, :5)
            RETURNING REQUEST_ID INTO :6
        """
        
        # Create a variable to hold the returned ID
        request_id_var = cursor.var(cx_Oracle.NUMBER)
        
        cursor.execute(sql, [
            request_data.get('full_name'),
            request_data.get('employee_id'),
            request_data.get('department'),
            request_data.get('designation', ''),  # Default to empty string if not provided
            request_data.get('email', ''),        # Default to empty string if not provided
            request_id_var
        ])
        
        # Get the returned ID
        request_id = int(request_id_var.getvalue()[0])
        
        connection.commit()
        logger.info(f"Registration request created for {request_data.get('employee_id')} with ID {request_id}")
        
        return request_id
    except cx_Oracle.Error as e:
        logger.error(f"Error creating registration request: {e}")
        if connection:
            connection.rollback()
        return None
    finally:
        if connection:
            close_db_connection(connection)

def get_pending_registration_requests():
    """
    Get all pending registration requests
    
    Returns:
        list: List of pending registration requests
    """
    query = """
        SELECT REQUEST_ID, FULL_NAME, EMPLOYEE_ID, DEPARTMENT, DESIGNATION, EMAIL, 
               REQUEST_STATUS, REQUESTED_AT
        FROM ADMIN_REGISTRATION_REQUESTS 
        WHERE REQUEST_STATUS = 'PENDING'
        ORDER BY REQUESTED_AT DESC
    """
    return execute_query(query)

def approve_registration_request(request_id, approved_by):
    """
    Approve a registration request and move user to ADMIN_ACCESS_GRANTED_USERS
    
    Args:
        request_id (int): Request ID to approve
        approved_by (str): User who approved the request
        
    Returns:
        bool: True if successful, False otherwise
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # First, get the request details
        request_query = """
            SELECT FULL_NAME, EMPLOYEE_ID, DEPARTMENT, DESIGNATION, EMAIL
            FROM ADMIN_REGISTRATION_REQUESTS
            WHERE REQUEST_ID = :request_id AND REQUEST_STATUS = 'PENDING'
        """
        
        request_results = execute_query(request_query, {'request_id': request_id})
        if not request_results:
            logger.error(f"Registration request {request_id} not found or not pending")
            return False
            
        request_data = request_results[0]
        
        # Insert into ADMIN_ACCESS_GRANTED_USERS
        insert_sql = """
            INSERT INTO ADMIN_ACCESS_GRANTED_USERS (
                FULL_NAME, EMPLOYEE_ID, DEPARTMENT, DESIGNATION, EMAIL, CREATED_BY
            ) VALUES (:1, :2, :3, :4, :5, :6)
        """
        
        cursor.execute(insert_sql, [
            request_data['FULL_NAME'],
            request_data['EMPLOYEE_ID'],
            request_data['DEPARTMENT'],
            request_data['DESIGNATION'],
            request_data['EMAIL'],
            approved_by
        ])
        
        # Update the request status
        update_sql = """
            UPDATE ADMIN_REGISTRATION_REQUESTS
            SET REQUEST_STATUS = 'APPROVED', PROCESSED_AT = SYSDATE, PROCESSED_BY = :1
            WHERE REQUEST_ID = :2
        """
        
        cursor.execute(update_sql, [approved_by, request_id])
        
        connection.commit()
        logger.info(f"Registration request {request_id} approved by {approved_by}")
        
        return True
    except cx_Oracle.Error as e:
        logger.error(f"Error approving registration request: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            close_db_connection(connection)

def reject_registration_request(request_id, rejected_by):
    """
    Reject a registration request
    
    Args:
        request_id (int): Request ID to reject
        rejected_by (str): User who rejected the request
        
    Returns:
        bool: True if successful, False otherwise
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        sql = """
            UPDATE ADMIN_REGISTRATION_REQUESTS
            SET REQUEST_STATUS = 'REJECTED', PROCESSED_AT = SYSDATE, PROCESSED_BY = :1
            WHERE REQUEST_ID = :2
        """
        
        cursor.execute(sql, [rejected_by, request_id])
        
        connection.commit()
        logger.info(f"Registration request {request_id} rejected by {rejected_by}")
        
        return True
    except cx_Oracle.Error as e:
        logger.error(f"Error rejecting registration request: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            close_db_connection(connection)

def get_access_granted_users():
    """
    Get all users who have been granted access
    
    Returns:
        list: List of access granted users
    """
    query = """
        SELECT USER_ID, FULL_NAME, EMPLOYEE_ID, DEPARTMENT, DESIGNATION, EMAIL, 
               IS_ACTIVE, ACCESS_GRANTED_AT
        FROM ADMIN_ACCESS_GRANTED_USERS
        ORDER BY ACCESS_GRANTED_AT DESC
    """
    return execute_query(query)
