"""
Utility helper functions for Agiloft CLM Analytics application
"""

import pandas as pd
import streamlit as st
import io
import base64
import json
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Data validation helpers
class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_columns: List[str] = None) -> bool:
        """Validate DataFrame structure and content"""
        from utils.exceptions import ValidationError
        
        if df is None or df.empty:
            raise ValidationError("DataFrame is empty or None")
        
        if required_columns:
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise ValidationError(f"Missing required columns: {missing_columns}")
        
        return True
    
    @staticmethod
    def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
        """Validate date range"""
        from utils.exceptions import ValidationError
        
        if start_date > end_date:
            raise ValidationError("Start date cannot be after end date")
        
        if end_date > datetime.now():
            raise ValidationError("End date cannot be in the future")
        
        return True
    
    @staticmethod
    def validate_numeric_range(min_val: float, max_val: float) -> bool:
        """Validate numeric range"""
        from utils.exceptions import ValidationError
        
        if min_val < 0:
            raise ValidationError("Minimum value cannot be negative")
        
        if min_val >= max_val:
            raise ValidationError("Minimum value must be less than maximum value")
        
        return True
    
    @staticmethod
    def validate_contract_manager_id(manager_id: str) -> bool:
        """Validate contract manager ID format"""
        from utils.exceptions import ValidationError
        
        if not manager_id.startswith("Contract_Manager#"):
            raise ValidationError("Invalid contract manager ID format")
        
        return True

# Data export helpers
class DataExporter:
    """Data export utilities"""
    
    @staticmethod
    def to_csv(df: pd.DataFrame, filename: str = None) -> str:
        """Convert DataFrame to CSV string"""
        from utils.exceptions import ExportError
        
        try:
            return df.to_csv(index=False)
        except Exception as e:
            logger.error(f"CSV export failed: {str(e)}")
            raise ExportError(f"Failed to export CSV: {str(e)}")
    
    @staticmethod
    def to_excel(df: pd.DataFrame, filename: str = None) -> bytes:
        """Convert DataFrame to Excel bytes"""
        from utils.exceptions import ExportError
        
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            return output.getvalue()
        except Exception as e:
            logger.error(f"Excel export failed: {str(e)}")
            raise ExportError(f"Failed to export Excel: {str(e)}")
    
    @staticmethod
    def to_json(data: Dict[str, Any], filename: str = None) -> str:
        """Convert data to JSON string"""
        from utils.exceptions import ExportError
        
        try:
            return json.dumps(data, indent=2, default=str)
        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            raise ExportError(f"Failed to export JSON: {str(e)}")
    
    @staticmethod
    def create_download_link(data: Union[str, bytes], filename: str, mime_type: str) -> str:
        """Create download link for data"""
        from utils.exceptions import ExportError
        
        try:
            if isinstance(data, str):
                data = data.encode()
            
            b64 = base64.b64encode(data).decode()
            return f'<a href="data:{mime_type};base64,{b64}" download="{filename}">Download {filename}</a>'
        except Exception as e:
            logger.error(f"Download link creation failed: {str(e)}")
            raise ExportError(f"Failed to create download link: {str(e)}")

# Streamlit UI helpers
class StreamlitHelper:
    """Streamlit UI utilities"""
    
    @staticmethod
    def show_dataframe_info(df: pd.DataFrame, title: str = "DataFrame Info"):
        """Display DataFrame information"""
        with st.expander(f"{title}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Rows", f"{len(df):,}")
            
            with col2:
                st.metric("Columns", f"{len(df.columns):,}")
            
            with col3:
                st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
            
            # Data types
            st.subheader("Column Information")
            info_df = pd.DataFrame({
                'Column': df.columns,
                'Type': df.dtypes.astype(str),
                'Non-Null Count': df.count(),
                'Null Count': df.isnull().sum()
            })
            st.dataframe(info_df, use_container_width=True)
    
    @staticmethod
    def create_metric_card(title: str, value: str, delta: str = None, help_text: str = None):
        """Create a styled metric card"""
        st.metric(
            label=title,
            value=value,
            delta=delta,
            help=help_text
        )
    
    @staticmethod
    def create_progress_bar(current: int, total: int, text: str = "Progress"):
        """Create progress bar with text"""
        progress = current / total if total > 0 else 0
        st.progress(progress, text=f"{text}: {current}/{total} ({progress:.1%})")
    
    @staticmethod
    def show_loading_message(message: str = "Loading..."):
        """Show loading message with spinner"""
        return st.spinner(message)
    
    @staticmethod
    def create_alert(message: str, alert_type: str = "info"):
        """Create styled alert message"""
        if alert_type == "success":
            st.success(f"{message}")
        elif alert_type == "warning":
            st.warning(f"{message}")
        elif alert_type == "error":
            st.error(f"{message}")
        else:
            st.info(f"{message}")
    
    @staticmethod
    def create_sidebar_section(title: str, content_func):
        """Create sidebar section with title"""
        with st.sidebar:
            st.subheader(title)
            content_func()

# Date and time helpers
class DateTimeHelper:
    """Date and time utilities"""
    
    @staticmethod
    def get_current_timestamp() -> str:
        """Get current timestamp as string"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def get_date_range_options() -> Dict[str, Tuple[datetime, datetime]]:
        """Get common date range options"""
        now = datetime.now()
        return {
            "Last 7 days": (now - timedelta(days=7), now),
            "Last 30 days": (now - timedelta(days=30), now),
            "Last 90 days": (now - timedelta(days=90), now),
            "Last 6 months": (now - timedelta(days=180), now),
            "Last year": (now - timedelta(days=365), now),
            "Year to date": (datetime(now.year, 1, 1), now),
            "Previous year": (datetime(now.year - 1, 1, 1), datetime(now.year - 1, 12, 31))
        }
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    @staticmethod
    def get_business_days(start_date: datetime, end_date: datetime) -> int:
        """Calculate business days between dates"""
        return pd.bdate_range(start_date, end_date).size

# Number formatting helpers
class NumberFormatter:
    """Number formatting utilities"""
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD") -> str:
        """Format number as currency"""
        if currency == "USD":
            return f"${amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """Format number as percentage"""
        return f"{value:.{decimals}f}%"
    
    @staticmethod
    def format_large_number(value: float, decimals: int = 1) -> str:
        """Format large numbers with K, M, B suffixes"""
        if value >= 1e9:
            return f"{value/1e9:.{decimals}f}B"
        elif value >= 1e6:
            return f"{value/1e6:.{decimals}f}M"
        elif value >= 1e3:
            return f"{value/1e3:.{decimals}f}K"
        else:
            return f"{value:.{decimals}f}"
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safe division with default value for zero denominator"""
        return numerator / denominator if denominator != 0 else default

# Cache helpers
class CacheHelper:
    """Caching utilities for Streamlit"""
    
    @staticmethod
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def cached_dataframe_operation(df: pd.DataFrame, operation: str, **kwargs) -> pd.DataFrame:
        """Cache expensive DataFrame operations"""
        if operation == "groupby":
            return df.groupby(kwargs.get("by", [])).sum()
        elif operation == "pivot":
            return df.pivot_table(**kwargs)
        elif operation == "sort":
            return df.sort_values(kwargs.get("by", []))
        else:
            return df
    
    @staticmethod
    @st.cache_data(ttl=1800)  # Cache for 30 minutes
    def cached_calculation(data: List[float], operation: str) -> float:
        """Cache expensive calculations"""
        if operation == "sum":
            return sum(data)
        elif operation == "mean":
            return sum(data) / len(data) if data else 0
        elif operation == "max":
            return max(data) if data else 0
        elif operation == "min":
            return min(data) if data else 0
        else:
            return 0

# File handling helpers
class FileHelper:
    """File handling utilities"""
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """Ensure directory exists"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """Get file size in bytes"""
        return Path(file_path).stat().st_size
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension"""
        return Path(filename).suffix.lower()
    
    @staticmethod
    def is_valid_file_type(filename: str, allowed_types: List[str]) -> bool:
        """Check if file type is allowed"""
        extension = FileHelper.get_file_extension(filename)
        return extension in allowed_types
    
    @staticmethod
    def read_config_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Read configuration file (JSON or YAML)"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() == '.json':
                return json.load(f)
            elif file_path.suffix.lower() in ['.yml', '.yaml']:
                import yaml
                return yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config file format: {file_path.suffix}")

# Performance monitoring helpers
class PerformanceMonitor:
    """Performance monitoring utilities"""
    
    def __init__(self):
        self.start_time = None
        self.checkpoints = {}
    
    def start(self):
        """Start performance monitoring"""
        self.start_time = datetime.now()
        logger.debug("Performance monitoring started")
    
    def checkpoint(self, name: str):
        """Add a checkpoint"""
        if self.start_time is None:
            self.start()
        
        checkpoint_time = datetime.now()
        elapsed = (checkpoint_time - self.start_time).total_seconds()
        self.checkpoints[name] = elapsed
        logger.debug(f"Checkpoint '{name}': {elapsed:.3f}s")
    
    def get_elapsed_time(self) -> float:
        """Get total elapsed time"""
        if self.start_time is None:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_report(self) -> Dict[str, float]:
        """Get performance report"""
        report = {
            "total_time": self.get_elapsed_time(),
            "checkpoints": self.checkpoints.copy()
        }
        return report
    
    def reset(self):
        """Reset performance monitor"""
        self.start_time = None
        self.checkpoints.clear()

# Data quality helpers
class DataQualityChecker:
    """Data quality checking utilities"""
    
    @staticmethod
    def check_missing_values(df: pd.DataFrame) -> Dict[str, float]:
        """Check for missing values in DataFrame"""
        missing_percentages = {}
        for column in df.columns:
            missing_count = df[column].isnull().sum()
            missing_percentage = (missing_count / len(df)) * 100
            missing_percentages[column] = missing_percentage
        return missing_percentages
    
    @staticmethod
    def check_duplicates(df: pd.DataFrame, subset: List[str] = None) -> Dict[str, int]:
        """Check for duplicate rows"""
        total_duplicates = df.duplicated(subset=subset).sum()
        unique_rows = len(df) - total_duplicates
        
        return {
            "total_rows": len(df),
            "unique_rows": unique_rows,
            "duplicate_rows": total_duplicates,
            "duplicate_percentage": (total_duplicates / len(df)) * 100 if len(df) > 0 else 0
        }
    
    @staticmethod
    def check_data_types(df: pd.DataFrame) -> Dict[str, str]:
        """Check data types of columns"""
        return {col: str(dtype) for col, dtype in df.dtypes.items()}
    
    @staticmethod
    def check_outliers(df: pd.DataFrame, column: str, method: str = "iqr") -> Dict[str, Any]:
        """Check for outliers in a numeric column"""
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        series = df[column].dropna()
        
        if method == "iqr":
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = series[(series < lower_bound) | (series > upper_bound)]
        elif method == "zscore":
            z_scores = (series - series.mean()) / series.std()
            outliers = series[abs(z_scores) > 3]
        else:
            raise ValueError("Method must be 'iqr' or 'zscore'")
        
        return {
            "total_values": len(series),
            "outlier_count": len(outliers),
            "outlier_percentage": (len(outliers) / len(series)) * 100 if len(series) > 0 else 0,
            "outlier_values": outliers.tolist()
        }
    
    @staticmethod
    def generate_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive data quality report"""
        import numpy as np
        
        report = {
            "overview": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024**2
            },
            "missing_values": DataQualityChecker.check_missing_values(df),
            "duplicates": DataQualityChecker.check_duplicates(df),
            "data_types": DataQualityChecker.check_data_types(df)
        }
        
        # Check outliers for numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        report["outliers"] = {}
        for col in numeric_columns:
            try:
                report["outliers"][col] = DataQualityChecker.check_outliers(df, col)
            except Exception as e:
                logger.warning(f"Could not check outliers for column {col}: {str(e)}")
        
        return report

# Security helpers
class SecurityHelper:
    """Security utilities"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file operations"""
        import re
        # Remove or replace dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')
        # Limit length
        if len(sanitized) > 255:
            name, ext = Path(sanitized).stem, Path(sanitized).suffix
            sanitized = name[:255-len(ext)] + ext
        return sanitized
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """Mask sensitive data like passwords or API keys"""
        if len(data) <= visible_chars * 2:
            return mask_char * len(data)
        
        start = data[:visible_chars]
        end = data[-visible_chars:]
        middle = mask_char * (len(data) - visible_chars * 2)
        return start + middle + end
    
    @staticmethod
    def validate_sql_input(sql_input: str) -> bool:
        """Basic SQL injection prevention"""
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
            'EXEC', 'EXECUTE', 'UNION', 'SCRIPT', '--', ';'
        ]
        
        sql_upper = sql_input.upper()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        return True

# Configuration helpers
class ConfigHelper:
    """Configuration management utilities"""
    
    @staticmethod
    def load_environment_config() -> Dict[str, str]:
        """Load configuration from environment variables"""
        import os
        from config.settings import app_config
        
        config = {}
        
        # Database configuration
        config['DB_HOST'] = os.getenv('DB_HOST', app_config.DB_HOST)
        config['DB_PORT'] = os.getenv('DB_PORT', str(app_config.DB_PORT))
        config['DB_NAME'] = os.getenv('DB_NAME', app_config.DB_NAME)
        config['DB_USER'] = os.getenv('DB_USER', app_config.DB_USER)
        config['DB_PASSWORD'] = os.getenv('DB_PASSWORD', app_config.DB_PASSWORD)
        
        # Application configuration
        config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', app_config.LOG_LEVEL)
        config['APP_TITLE'] = os.getenv('APP_TITLE', app_config.APP_TITLE)
        
        return config
    
    @staticmethod
    def validate_config(config: Dict[str, Any], required_keys: List[str]) -> bool:
        """Validate configuration dictionary"""
        from utils.exceptions import ValidationError
        
        missing_keys = set(required_keys) - set(config.keys())
        if missing_keys:
            raise ValidationError(f"Missing required configuration keys: {missing_keys}")
        return True
    
    @staticmethod
    def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries"""
        merged = {}
        for config in configs:
            merged.update(config)
        return merged

# Testing helpers
class TestHelper:
    """Testing utilities"""
    
    @staticmethod
    def create_sample_dataframe(rows: int = 100, columns: List[str] = None) -> pd.DataFrame:
        """Create sample DataFrame for testing"""
        import random
        
        if columns is None:
            columns = ['id', 'name', 'value', 'category', 'date']
        
        data = {}
        for col in columns:
            if col == 'id':
                data[col] = range(1, rows + 1)
            elif col == 'name':
                data[col] = [f"Item_{i}" for i in range(1, rows + 1)]
            elif col == 'value':
                data[col] = [random.uniform(100, 1000) for _ in range(rows)]
            elif col == 'category':
                categories = ['A', 'B', 'C', 'D']
                data[col] = [random.choice(categories) for _ in range(rows)]
            elif col == 'date':
                start_date = datetime.now() - timedelta(days=365)
                data[col] = [start_date + timedelta(days=random.randint(0, 365)) for _ in range(rows)]
            else:
                data[col] = [f"Value_{i}" for i in range(1, rows + 1)]
        
        return pd.DataFrame(data)
    
    @staticmethod
    def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, Any]:
        """Compare two DataFrames and return differences"""
        comparison = {
            "shape_match": df1.shape == df2.shape,
            "columns_match": list(df1.columns) == list(df2.columns),
            "data_equal": df1.equals(df2)
        }
        
        if not comparison["data_equal"]:
            try:
                diff = df1.compare(df2)
                comparison["differences"] = diff
            except Exception as e:
                comparison["comparison_error"] = str(e)
        
        return comparison

# Global utility instances
performance_monitor = PerformanceMonitor()
data_validator = DataValidator()
data_exporter = DataExporter()
streamlit_helper = StreamlitHelper()
date_helper = DateTimeHelper()
number_formatter = NumberFormatter()
cache_helper = CacheHelper()
file_helper = FileHelper()
data_quality_checker = DataQualityChecker()
security_helper = SecurityHelper()
config_helper = ConfigHelper()
test_helper = TestHelper()
