"""
Database configuration template for the admin dashboard.
Copy this file to db_config.py and update with your actual database credentials.
"""

# DRISHTI Database Configuration
DB_CONFIG = {
    'host': 'your_database_host',
    'port': 1521,
    'service_name': 'your_service_name',
    'user': 'your_username',
    'password': 'your_password'
}

# Connection string for cx_Oracle or similar Oracle connectors
CONNECTION_STRING = f"{DB_CONFIG['user']}/{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['service_name']}"

def get_db_config():
    """
    Returns the database configuration dictionary.
    """
    return DB_CONFIG.copy()

def get_connection_string():
    """
    Returns the database connection string.
    """
    return CONNECTION_STRING