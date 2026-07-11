# Face Recognition Admin Dashboard - Overview

## Project Summary

The Face Recognition Admin Dashboard is a comprehensive web application designed to monitor, manage, and analyze a face recognition-based attendance and security system. Built with a Python Flask backend and HTML/CSS/JavaScript frontend, it provides administrators with tools to manage cameras, employees, and generate detailed reports on system activity.

## Technology Stack

- **Backend**: Python Flask API
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Database**: Oracle Database
- **Frameworks**: Bootstrap 5 for responsive UI
- **Charting**: Chart.js for data visualization
- **Icons**: Font Awesome
- **File Processing**: xlsx.js for Excel exports

## Core Features

### 1. Authentication & User Management
- **Secure Login**: Two-step authentication using employee ID and HRIS password
- **Role-based Access**: Admin and user access levels with different permissions
- **User Registration**: Self-service registration with approval workflow
- **Access Control**: Centralized management of user permissions

### 2. Camera Management
- **Camera Registry**: View all registered cameras with status, location, and configuration
- **Add Cameras**: Register new cameras with detailed location information (site, building, floor, area, direction)
- **Status Control**: Activate/deactivate cameras remotely
- **Real-time Monitoring**: Track camera status and connectivity

### 3. Employee Monitoring
- **Daily Summaries**: Detailed records of employee presence, including first/last seen times, total duration, and hit counts
- **Movement Tracking**: Monitor employee movements across different floors and buildings
- **Downtime Analysis**: Identify periods of employee inactivity or absence
- **IN/OUT Reports**: Comprehensive reports on employee entry and exit patterns

### 4. Reporting & Analytics
- **Dashboard KPIs**: Key metrics including total cameras, active employees, and recognition events
- **Department-wise Analysis**: Breakdown of employee activity by department
- **Time-based Insights**: Entry time distribution and presence patterns
- **Export Capabilities**: Download reports in Excel and PDF formats

### 5. Advanced Features
- **Location Coverage**: Track which floors and areas employees visit
- **Floor Visitor Analytics**: Identify top floor visitors and movement patterns
- **Presence Distribution**: Analyze inside vs outside time ratios
- **Ranking Reports**: Top performers based on various metrics

## System Architecture

### Backend Components
- **API Layer**: Flask-based REST API with endpoints for all major functions
- **Database Layer**: Oracle DB integration with secure connection handling
- **Authentication Module**: Integration with HRIS system for credential validation
- **User Management**: Two-table system for registration requests and granted access

### Frontend Components
- **Responsive Dashboard**: Mobile-friendly interface built with Bootstrap
- **Dynamic Views**: Single-page application with multiple views and navigation
- **Real-time Updates**: AJAX-powered data refresh without page reloads
- **Interactive Charts**: Visual representation of employee data and trends

## Key API Endpoints

### Authentication
- `POST /api/login` - User authentication with two-step verification
- `POST /api/register` - Submit user registration request

### Camera Management
- `GET /api/cameras` - Retrieve all registered cameras
- `POST /api/cameras` - Add a new camera
- `PUT /api/cameras/{id}/status` - Update camera status

### Employee Data
- `GET /api/employee-summary` - Get employee daily summary
- `GET /api/employee-summary-aggregated` - Get aggregated employee data
- `GET /api/downtime-summary` - Get employee downtime information
- `GET /api/employee-movement` - Track employee movements
- `GET /api/daily-inout-summary` - Get IN/OUT summary
- `GET /api/location-coverage` - Get location coverage reports

### User Management
- `GET /api/registration-requests` - Get pending registration requests
- `POST /api/registration-requests/{id}/approve` - Approve registration
- `POST /api/registration-requests/{id}/reject` - Reject registration
- `GET /api/access-granted-users` - Get authorized users
- `POST /api/access-granted-users/{id}/revoke` - Revoke access
- `GET /api/admin-access-users` - Get users with admin access

## Security Features

- **Two-Step Authentication**: Local access verification + HRIS validation
- **Password Security**: Passwords never stored locally
- **Session Management**: Secure local storage of authentication status
- **SQL Injection Prevention**: Parameterized queries throughout
- **Access Control**: Role-based permissions for different system areas

## User Interface Components

### Navigation
- **Sidebar Menu**: Collapsible menu with intuitive icons
- **Breadcrumb Trail**: Clear navigation path indicator
- **Responsive Design**: Works on desktop, tablet, and mobile devices

### Dashboard Elements
- **KPI Cards**: Real-time statistics display
- **Interactive Charts**: Visual data representation
- **Data Tables**: Sortable, searchable employee records
- **Filter Controls**: Date range and search filters

### Forms & Inputs
- **Camera Registration**: Multi-field form for adding cameras
- **Status Updates**: Toggle switches for camera activation
- **Search Interfaces**: Real-time filtering capabilities
- **Export Options**: Multiple format support (Excel, PDF)

## Installation & Setup

### Backend Setup
1. Navigate to the `backend` directory
2. Install dependencies: `pip install -r requirements.txt`
3. Configure database connection in `db_config.py`
4. Run the API server: `python api.py` (available at http://localhost:5001)

### Frontend Setup
1. Navigate to the `frontend` directory
2. Run the frontend server: `python server.py`
3. Access the dashboard at http://localhost:8001

### Database Configuration
- Execute SQL scripts in `user_management_tables.sql` to create required tables
- Ensure Oracle client libraries are installed
- Configure connection parameters in `db_config.py`

## Administrative Capabilities

### For Super Administrators
- Manage user access requests
- Grant/revoke system access
- Assign admin privileges
- Monitor system-wide activity

### For Department Managers
- View employee activity in their departments
- Generate department-specific reports
- Track attendance patterns
- Monitor compliance

### For Security Personnel
- Monitor camera feeds and statuses
- Track unauthorized access attempts
- Review movement logs
- Generate security reports

## Data Model

### Key Database Tables
- **CAMERA_REGISTRY**: Camera configuration and status
- **EMPLOYEE_RECORDS**: Daily employee recognition logs
- **ADMIN_REGISTRATION_REQUESTS**: Pending user access requests
- **ADMIN_ACCESS_GRANTED_USERS**: Authorized system users
- **MOVEMENT_LOGS**: Detailed employee movement history

## Integration Points

- **HRIS System**: External authentication and employee data validation
- **Face Recognition Engine**: Real-time recognition data feed
- **Oracle Database**: Persistent storage of all system data
- **External APIs**: Third-party services as needed

## Performance Considerations

- **Caching**: Aggregated data caching for improved performance
- **Pagination**: Efficient handling of large datasets
- **Asynchronous Loading**: Non-blocking data retrieval
- **Optimized Queries**: Indexes and query optimization for large datasets

## Maintenance & Monitoring

- **Health Checks**: API endpoint for system health monitoring
- **Logging**: Comprehensive event logging for troubleshooting
- **Audit Trails**: Track administrative actions and changes
- **Backup Procedures**: Regular data backup recommendations

## Customization Options

- **UI Themes**: Configurable color schemes and layouts
- **Report Templates**: Customizable report formats
- **Notification Settings**: Configurable alert thresholds
- **Permission Levels**: Flexible role-based access control

## Future Enhancements

- **Mobile Application**: Native mobile app for on-the-go access
- **Advanced Analytics**: Machine learning-based insights
- **Integration Hub**: Connect with more enterprise systems
- **Enhanced Security**: Multi-factor authentication and biometric verification