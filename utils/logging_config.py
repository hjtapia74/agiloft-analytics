"""
Logging configuration for Agiloft CLM Analytics application
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

from config.settings import app_config

def setup_logging(log_level: str = None, log_file: str = None):
    """
    Setup logging configuration for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
    """
    
    # Use config values if not provided
    if log_level is None:
        log_level = app_config.LOG_LEVEL
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Default log file name with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"agiloft_analytics_{timestamp}.log"
    
    # Configure logging format
    formatter = logging.Formatter(
        fmt=app_config.LOG_FORMAT,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Log file: {log_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

def log_function_call(func):
    """
    Decorator to log function calls
    
    Usage:
        @log_function_call
        def my_function():
            pass
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling function: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Function {func.__name__} failed: {str(e)}")
            raise
    return wrapper

def log_performance(func):
    """
    Decorator to log function performance
    
    Usage:
        @log_performance
        def my_function():
            pass
    """
    import time
    
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        logger.debug(f"Starting performance measurement for: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.3f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f} seconds: {str(e)}")
            raise
    return wrapper

class ContextualLogger:
    """
    Logger with contextual information
    """
    
    def __init__(self, name: str, context: dict = None):
        self.logger = logging.getLogger(name)
        self.context = context or {}
    
    def _format_message(self, message: str) -> str:
        """Add context to log message"""
        if self.context:
            context_str = " | ".join([f"{k}={v}" for k, v in self.context.items()])
            return f"[{context_str}] {message}"
        return message
    
    def debug(self, message: str):
        self.logger.debug(self._format_message(message))
    
    def info(self, message: str):
        self.logger.info(self._format_message(message))
    
    def warning(self, message: str):
        self.logger.warning(self._format_message(message))
    
    def error(self, message: str):
        self.logger.error(self._format_message(message))
    
    def critical(self, message: str):
        self.logger.critical(self._format_message(message))
    
    def add_context(self, **kwargs):
        """Add context variables"""
        self.context.update(kwargs)
    
    def remove_context(self, *keys):
        """Remove context variables"""
        for key in keys:
            self.context.pop(key, None)

class DatabaseLogger(ContextualLogger):
    """
    Specialized logger for database operations
    """
    
    def __init__(self, connection_string: str = None):
        super().__init__("database")
        if connection_string:
            # Don't log the full connection string for security
            masked_conn = connection_string.replace(app_config.DB_PASSWORD, "***")
            self.add_context(connection=masked_conn)
    
    def log_query(self, query: str, params: tuple = None, execution_time: float = None):
        """Log database query execution"""
        message = f"Query: {query[:100]}..."  # Truncate long queries
        if params:
            message += f" | Params: {params}"
        if execution_time:
            message += f" | Time: {execution_time:.3f}s"
        self.info(message)
    
    def log_connection_event(self, event: str, success: bool = True):
        """Log database connection events"""
        level = self.info if success else self.error
        level(f"Database connection {event}")

class PageLogger(ContextualLogger):
    """
    Specialized logger for page operations
    """
    
    def __init__(self, page_name: str, user_id: str = None):
        super().__init__("pages")
        self.add_context(page=page_name)
        if user_id:
            self.add_context(user=user_id)
    
    def log_page_render(self, success: bool = True, error: str = None):
        """Log page rendering events"""
        if success:
            self.info("Page rendered successfully")
        else:
            self.error(f"Page rendering failed: {error}")
    
    def log_user_action(self, action: str, details: dict = None):
        """Log user actions on the page"""
        message = f"User action: {action}"
        if details:
            detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
            message += f" | {detail_str}"
        self.info(message)

# Error tracking utilities
class ErrorTracker:
    """
    Track and aggregate errors for monitoring
    """
    
    def __init__(self):
        self.error_counts = {}
        self.logger = logging.getLogger("error_tracker")
    
    def track_error(self, error_type: str, error_message: str, context: dict = None):
        """Track an error occurrence"""
        key = f"{error_type}:{error_message[:50]}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        log_context = {"error_count": self.error_counts[key]}
        if context:
            log_context.update(context)
        
        contextual_logger = ContextualLogger("error_tracker", log_context)
        contextual_logger.error(f"{error_type}: {error_message}")
    
    def get_error_summary(self) -> dict:
        """Get summary of tracked errors"""
        return dict(self.error_counts)
    
    def reset_counts(self):
        """Reset error counts"""
        self.error_counts.clear()
        self.logger.info("Error counts reset")

# Global error tracker instance
error_tracker = ErrorTracker()
