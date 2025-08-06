"""
Configuration settings for Agiloft CLM Analytics Dashboard
"""

import os
from dataclasses import dataclass
from typing import Optional
import streamlit as st

@dataclass
class AppConfig:
    """Application configuration settings"""
    
    # App settings
    APP_TITLE: str = "Agiloft CLM Analytics"
    APP_ICON: str = ""
    
    # Logo settings
    LOGO_URL_LARGE: str = "https://higherlogicdownload.s3.amazonaws.com/AGILOFT/46412d73-e4f2-4abc-83be-9887a0cf006a/UploadedImages/Agiloft_Signature_Rev_Color_RGB.png"
    
    # Database settings
    DB_HOST: str = "svc-dae6f783-22b7-40ef-9d36-3bcb46e7780a-dml.aws-virginia-8.svc.singlestore.com"
    DB_PORT: int = 3306
    DB_NAME: str = "order_mgt"
    DB_USER: str = "admin"
    DB_PASSWORD: str = "syq,Q_4$pn0F4Qv8=1L4xZlAd~"
    
    # Chart settings
    CHART_HEIGHT: int = 320
    CHART_WIDTH: int = 800
    
    # Data settings
    DEFAULT_CONTRACT_MANAGERS: list = None
    DEFAULT_CONTRACT_STATUSES: list = None
    DEFAULT_AMOUNT_RANGE: tuple = (10000000.0, 35000000.0)
    MAX_AMOUNT: float = 50000000.0
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        """Post-initialization setup"""
        if self.DEFAULT_CONTRACT_MANAGERS is None:
            self.DEFAULT_CONTRACT_MANAGERS = [
                f"Contract_Manager#{i:09d}" for i in range(1, 71)
            ]
        
        if self.DEFAULT_CONTRACT_STATUSES is None:
            self.DEFAULT_CONTRACT_STATUSES = [
                "Approved", "Pending Approval", "Pending Review", "Draft"
            ]
    
    @property
    def database_url(self) -> str:
        """Get database connection URL"""
        return f"{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def get_from_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration value from environment variables"""
        return os.getenv(key, default)
    
    def get_from_secrets(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration value from Streamlit secrets"""
        try:
            return st.secrets[key]
        except KeyError:
            return default

@dataclass
class DatabaseConfig:
    """Database-specific configuration"""
    
    # Query timeouts
    QUERY_TIMEOUT: int = 30
    CONNECTION_TIMEOUT: int = 10
    
    # Connection pool settings
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour
    POOL_PRE_PING: bool = True  # Validate connections before use
    POOL_RESET_ON_RETURN: str = "commit"  # Reset connection state on return
    
    # Cache settings
    CACHE_MAX_SIZE_MB: int = 100
    CACHE_DEFAULT_TTL: int = 3600  # 1 hour
    CACHE_MAX_ENTRIES: int = 1000
    
    # Cache TTL settings for different data types (in seconds)
    CACHE_TTL_STATIC_DATA: int = 14400      # 4 hours - rarely changing data (managers, statuses)
    CACHE_TTL_SUMMARY_STATS: int = 7200     # 2 hours - aggregate statistics
    CACHE_TTL_CONTRACT_DATA: int = 3600     # 1 hour - individual contract records
    CACHE_TTL_DYNAMIC_QUERIES: int = 1800   # 30 minutes - frequently changing data
    
    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    
    # Query limits
    MAX_ROWS: int = 10000
    DEFAULT_LIMIT: int = 1000

@dataclass
class UIConfig:
    """UI-specific configuration"""
    
    # Widget defaults
    MULTISELECT_MAX_SELECTIONS: int = 10
    SLIDER_STEP: float = 1000.0
    
    # Table settings
    TABLE_MAX_ROWS: int = 500
    TABLE_PAGINATION: bool = True
    
    # Chart settings
    CHART_THEME: str = "streamlit"
    CHART_COLORS: list = None
    
    def __post_init__(self):
        """Post-initialization setup"""
        if self.CHART_COLORS is None:
            self.CHART_COLORS = [
                "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", 
                "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"
            ]

# Global configuration instances
app_config = AppConfig()
db_config = DatabaseConfig()
ui_config = UIConfig()
