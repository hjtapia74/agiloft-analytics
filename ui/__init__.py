"""
UI package for Agiloft CLM Analytics Dashboard
"""

# Import base page classes
from .base_page import BasePage, FilteredPage, ChartHelper

# Import enhanced components
try:
    from .components import (
        DataChartContainer,
        EnhancedFilterContainer,
        enhanced_date_range_picker,
        enhanced_multiselect,
        render_metrics_grid,
        create_enhanced_chart
    )
except ImportError as e:
    # Fallback if components module is not available
    print(f"Warning: Could not import enhanced components: {e}")
    DataChartContainer = None
    EnhancedFilterContainer = None
    enhanced_date_range_picker = None
    enhanced_multiselect = None
    render_metrics_grid = None
    create_enhanced_chart = None

__all__ = [
    'BasePage',
    'FilteredPage', 
    'ChartHelper',
    'DataChartContainer',
    'EnhancedFilterContainer',
    'enhanced_date_range_picker',
    'enhanced_multiselect',
    'render_metrics_grid',
    'create_enhanced_chart'
]
