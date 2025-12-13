# logger_config.py

import sys
from loguru import logger

# Define a professional log format
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Remove the default logger
logger.remove()

# System Logger
logger.add(
    "logs/system.txt",
    level="DEBUG",
    format=log_format,
    rotation="10 MB",
    retention="10 days",
    enqueue=True,
    backtrace=True,
    diagnose=True,
    filter=lambda record: "system" in record["extra"]
)

# Registration Logger
logger.add(
    "logs/registration.txt",
    level="INFO",
    format=log_format,
    rotation="10 MB",
    retention="10 days",
    enqueue=True,
    backtrace=True,
    diagnose=True,
    filter=lambda record: "registration" in record["extra"]
)

# Detection Logger
logger.add(
    "logs/detection.txt",
    level="INFO",
    format=log_format,
    rotation="10 MB",
    retention="10 days",
    enqueue=True,
    filter=lambda record: "detection" in record["extra"]
)

# Recognition Logger
logger.add(
    "logs/recognition.txt",
    level="DEBUG",
    format=log_format,
    rotation="10 MB",
    retention="10 days",
    enqueue=True,
    filter=lambda record: "recognition" in record["extra"]
)

# Add a console logger for immediate feedback during development
logger.add(sys.stderr, level="DEBUG", format=log_format)

# Create specialized loggers
system_logger = logger.bind(system=True)
registration_logger = logger.bind(registration=True)
detection_logger = logger.bind(detection=True)
recognition_logger = logger.bind(recognition=True)