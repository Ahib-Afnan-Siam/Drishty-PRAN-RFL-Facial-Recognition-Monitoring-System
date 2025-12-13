# User Management and Access Control System

## Overview

This document describes the implementation of the User Management and Access Control System for the Face Recognition Admin Dashboard. The system introduces a two-step authentication process and a comprehensive user access request workflow.

## System Architecture

### Two-Step Authentication Process

1. **Access Verification**: Check if Employee ID exists in the Access Granted User List (local database)
2. **HRIS Authentication**: Send Employee ID and Password to HRIS API for validation

### Database Schema

The system uses two main tables:

1. **ADMIN_REGISTRATION_REQUESTS**: Stores pending user access requests
2. **ADMIN_ACCESS_GRANTED_USERS**: Stores users approved to access the dashboard

SQL scripts for table creation can be found in `admin/backend/user_management_tables.sql`.

## Features

### User Registration
- New users can request access through the "New User Registration" button on the login page
- Registration form collects Full Name, Employee ID, Department, Designation, and Email
- Passwords are never stored in the system

### Admin User Management
- Admins can view, approve, or reject pending access requests
- Admins can view and revoke access for authorized users
- Dedicated user management interface with separate sections for pending requests and authorized users

### Enhanced Security
- Two-step authentication process ensures only authorized users can access the dashboard
- Local access verification before HRIS authentication
- Passwords are never stored locally

## API Endpoints

### Authentication
- `POST /api/login` - Two-step authentication (local access check + HRIS validation)

### User Management
- `POST /api/register` - Create a new user registration request
- `GET /api/registration-requests` - Get all pending registration requests
- `POST /api/registration-requests/<id>/approve` - Approve a registration request
- `POST /api/registration-requests/<id>/reject` - Reject a registration request
- `GET /api/access-granted-users` - Get all users with granted access
- `POST /api/access-granted-users/<id>/revoke` - Revoke user access

## UI Components

### Login Page
- Added "New User Registration" button
- Enhanced error messaging for access denied scenarios

### User Registration Page
- Dedicated form for new user access requests
- Information section explaining the process

### Admin Dashboard
- Added "User Management" section to the sidebar
- Separate views for pending requests and authorized users
- Action buttons for approving/rejecting requests and revoking access

## Implementation Files

### Backend
- `admin/backend/db_connection.py` - Added user management database functions
- `admin/backend/api.py` - Added user management API endpoints
- `admin/backend/user_management_tables.sql` - Database schema definition
- `admin/backend/test_user_management.py` - Database function tests
- `admin/backend/test_api_endpoints.py` - API endpoint tests

### Frontend
- `admin/frontend/login.html` - Updated with registration button
- `admin/frontend/user_registration.html` - New user registration form
- `admin/frontend/user_management.html` - Admin user management interface
- `admin/frontend/styles.css` - Added styling for new components

## Testing

Two test scripts are provided:
1. `test_user_management.py` - Tests database functions
2. `test_api_endpoints.py` - Tests API endpoints

## Deployment Notes

1. Execute the SQL script in `user_management_tables.sql` to create the required database tables
2. Ensure the backend API is running on port 5001
3. Verify the frontend is served on port 8001
4. Test the complete workflow with sample data

## Security Considerations

- All API endpoints use parameterized queries to prevent SQL injection
- Passwords are never stored in the system
- Access control is enforced at both the database and API levels
- Session management uses localStorage (consider upgrading to JWT for production)

## Future Enhancements

- Implement JWT-based authentication for better session management
- Add email notifications for request status changes
- Include audit logging for all user management actions
- Add pagination for large datasets
- Implement role-based access control (RBAC)