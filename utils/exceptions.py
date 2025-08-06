"""
Custom exceptions for Agiloft CLM Analytics application
"""

class AgiloftAnalyticsError(Exception):
    """Base exception for Agiloft Analytics application"""
    pass

class DatabaseConnectionError(AgiloftAnalyticsError):
    """Raised when database connection fails"""
    pass

class QueryExecutionError(AgiloftAnalyticsError):
    """Raised when database query execution fails"""
    pass

class DataProcessingError(AgiloftAnalyticsError):
    """Raised when data processing fails"""
    pass

class PageRenderError(AgiloftAnalyticsError):
    """Raised when page rendering fails"""
    pass

class ConfigurationError(AgiloftAnalyticsError):
    """Raised when configuration is invalid"""
    pass

class ValidationError(AgiloftAnalyticsError):
    """Raised when data validation fails"""
    pass

class ExportError(AgiloftAnalyticsError):
    """Raised when data export fails"""
    pass

class AuthenticationError(AgiloftAnalyticsError):
    """Raised when authentication fails"""
    pass

class PermissionError(AgiloftAnalyticsError):
    """Raised when user lacks required permissions"""
    pass
