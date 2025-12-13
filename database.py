# database.py 

import oracledb
import numpy as np
from logger_config import system_logger as logger

# --- Professional Enhancement: Ensure Thick mode is initialized only once ---
_is_thick_mode_initialized = False

class Database:
    """Handles all communication with the Oracle Database."""

    def __init__(self, config):
        self.config = config['oracle']
        # --- FIX: Initialize Oracle Client in Thick Mode for compatibility ---
        self._init_thick_mode()
        self.pool = self._create_pool()

    def _init_thick_mode(self):
        """
        Initializes the python-oracledb driver in Thick mode to support
        a wider range of Oracle DB server versions.
        """
        global _is_thick_mode_initialized
        if not _is_thick_mode_initialized:
            try:
                # This function looks for the Oracle Instant Client in your system PATH
                oracledb.init_oracle_client()
                _is_thick_mode_initialized = True
                logger.info("Successfully initialized oracledb in Thick mode.")
            except oracledb.Error as e:
                logger.error(
                    "Failed to initialize Oracle Client in Thick mode. "
                    "Please ensure Oracle Instant Client is installed and configured in your system's PATH. "
                    f"Error: {e}", exc_info=True
                )
                raise

    def _create_pool(self):
        """Creates a database connection pool for efficient multi-threaded access."""
        try:
            pool = oracledb.create_pool(
                user=self.config['username'],
                password=self.config['password'],
                dsn=self.config['dsn'],
                min=self.config['pool_min'],
                max=self.config['pool_max'],
                increment=self.config['pool_increment']
            )
            logger.success("Successfully created Oracle DB connection pool.")
            return pool
        except oracledb.Error as e:
            logger.error(f"Failed to create Oracle DB connection pool: {e}", exc_info=True)
            # In a real production scenario, you might want to retry a few times before giving up.
            raise

    def load_all_users_from_db(self):
        """
        Loads all registered users' metadata and embeddings from Oracle DB.
        This is called once at startup to build the in-memory FAISS index.
        """
        all_embeddings = []
        all_metadata = []
        sql = "SELECT EMPLOYEE_ID, NAME, DEPARTMENT, ROLE, FACE_EMBEDDING FROM REGISTERED_USERS ORDER BY EMPLOYEE_ID"

        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    for row in cursor:
                        employee_id, name, department, role, embedding_blob = row
                        embedding = np.frombuffer(embedding_blob.read(), dtype=np.float32)
                        logger.debug(f"Loaded embedding with shape: {embedding.shape}")
                        all_embeddings.append(embedding)
                        all_metadata.append({'employee_id': employee_id, 'name': name, 'department': department, 'role': role})
            
            logger.info(f"Loaded {len(all_metadata)} users from the Oracle Database.")
            if all_embeddings:
                # Use the actual dimension of the first embedding
                dimension = all_embeddings[0].shape[0] if len(all_embeddings) > 0 else 128
                embeddings_array = np.array(all_embeddings, dtype=np.float32)
                logger.debug(f"Embeddings array shape: {embeddings_array.shape}")
            else:
                embeddings_array = np.empty((0, 128), dtype=np.float32)
            return embeddings_array, all_metadata
        except oracledb.Error as e:
            logger.error(f"Error loading users from Oracle DB: {e}", exc_info=True)
            return np.empty((0, 128), dtype=np.float32), []

    def add_user(self, metadata, embedding):
        """Adds a new user to the REGISTERED_USERS table in Oracle DB."""
        sql = "INSERT INTO REGISTERED_USERS (EMPLOYEE_ID, NAME, DEPARTMENT, ROLE, FACE_EMBEDDING) VALUES (:1, :2, :3, :4, :5)"
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    embedding_bytes = embedding.tobytes()
                    cursor.execute(sql, [metadata['employee_id'], metadata['name'], metadata['department'], metadata['role'], embedding_bytes])
                    connection.commit()
            logger.success(f"Successfully added user {metadata['name']} (ID: {metadata['employee_id']}) to Oracle DB.")
            return True
        except oracledb.Error as e:
            logger.error(f"Failed to add user {metadata['name']} to Oracle DB: {e}", exc_info=True)
            return False

    def log_recognition_event(self, employee_id, confidence, camera_id="CAM-01"):
        """Logs a successful recognition event to the RECOGNITION_LOGS table."""
        sql = "INSERT INTO RECOGNITION_LOGS (EMPLOYEE_ID, CONFIDENCE, CAMERA_ID) VALUES (:1, :2, :3)"
        try:
            # Round confidence to 2 decimal places before inserting in the database by skd
            rounded_confidence = round(float(confidence), 2)
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, [employee_id, rounded_confidence, camera_id])
                    connection.commit()
            return True
        except oracledb.Error as e:
            logger.warning(f"Could not log recognition event to Oracle DB: {e}")
            return False

    def close_pool(self):
        """Closes the connection pool gracefully on application shutdown."""
        if self.pool:
            self.pool.close()
            logger.info("Oracle DB connection pool closed.")