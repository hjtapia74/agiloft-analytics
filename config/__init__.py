# config/__init__.py
"""
Configuration management for Agiloft CLM Analytics
"""

from .settings import app_config, db_config, ui_config

__all__ = ['app_config', 'db_config', 'ui_config']