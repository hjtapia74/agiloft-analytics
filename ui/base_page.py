"""
Enhanced Base page class for Agiloft CLM Analytics pages
Now with improved UX components and tabbed interface
"""

from abc import ABC, abstractmethod
import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any, Optional

from config.settings import app_config, ui_config
from database.db_manager import DatabaseManager
from utils.exceptions import PageRenderError

logger = logging.getLogger(__name__)

# Try to import enhanced components, fallback to basic functionality if not available
try:
    from .components import (
        DataChartContainer, 
        EnhancedFilterContainer,
        enhanced_date_range_picker,
        enhanced_multiselect,
        render_metrics_grid,
        create_enhanced_chart
    )
    ENHANCED_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Enhanced components not available: {e}")
    ENHANCED_COMPONENTS_AVAILABLE = False
    
    # Create fallback classes
    class DataChartContainer:
        def __init__(self, key: str):
            self.key = key
        
        def render(self, dataframe, **kwargs):
            st.dataframe(dataframe, use_container_width=True)
    
    class EnhancedFilterContainer:
        def __init__(self, title: str, expanded: bool = True):
            self.title = title
            self.expanded = expanded
        
        def __enter__(self):
            self.container = st.expander(self.title, expanded=self.expanded)
            return self.container.__enter__()
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            return self.container.__exit__(exc_type, exc_val, exc_tb)
    
    def enhanced_multiselect(label, options, default=None, key="", help_text=None, max_selections=None):
        return st.multiselect(label, options, default=default, key=key, help=help_text, max_selections=max_selections)
    
    def render_metrics_grid(metrics, columns=4):
        cols = st.columns(columns)
        for i, (name, data) in enumerate(metrics.items()):
            with cols[i % columns]:
                st.metric(name, data.get("value", 0), help=data.get("help"))

class BasePage(ABC):
    """Abstract base class for dashboard pages with enhanced UX"""
    
    def __init__(self, title: str, icon: str = ""):
        self.title = title
        self.icon = icon
        self.db_manager: Optional[DatabaseManager] = None
        
    def setup_page(self):
        """Common page setup - NO set_page_config() here since it's done in main app"""
        # Get database manager from session state
        if 'db_manager' in st.session_state:
            self.db_manager = st.session_state.db_manager
        else:
            st.error("Database connection not available")
            st.stop()
    
    def render_header(self):
        """Render enhanced page header with better styling"""
        # Create a more prominent header
        st.markdown(f"""
        <div>
            <h1 style="margin: 0; font-size: 2.5rem;">
                {self.icon} {self.title}
            </h1>
        </div>
        """, unsafe_allow_html=True)
    
    def render_error(self, error_message: str):
        """Render error message with enhanced styling"""
        st.error(f"{error_message}")
        logger.error(f"Page error in {self.title}: {error_message}")
    
    def render_success(self, message: str):
        """Render success message"""
        st.success(f"{message}")
    
    def render_info(self, message: str):
        """Render info message"""
        st.info(f"{message}")
    
    def render_warning(self, message: str):
        """Render warning message"""
        st.warning(f"{message}")
    
    def show_loading(self, message: str = "Loading..."):
        """Show loading spinner with custom message"""
        return st.spinner(f"{message}")
    
    def create_columns(self, specs: list, vertical_alignment: str = "top"):
        """Create columns with specified widths"""
        return st.columns(specs, vertical_alignment=vertical_alignment)
    
    def create_data_container(self, key: str) -> DataChartContainer:
        """Create a new enhanced data container"""
        return DataChartContainer(key=f"{self.title.lower().replace(' ', '_')}_{key}")
    
    def create_filter_container(self, title: str, expanded: bool = True) -> EnhancedFilterContainer:
        """Create an enhanced filter container"""
        return EnhancedFilterContainer(title, expanded)
    
    def render_sidebar_filters(self) -> Dict[str, Any]:
        """Render sidebar filters (to be implemented by subclasses)"""
        return {}
    
    def validate_filters(self, filters: Dict[str, Any]) -> bool:
        """Validate filter inputs"""
        return True
    
    def process_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Process data based on filters (to be implemented by subclasses)"""
        return {}
    
    def render_visualizations(self, data: Dict[str, Any]):
        """Render visualizations (to be implemented by subclasses)"""
        pass
    
    def render_data_tables(self, data: Dict[str, Any]):
        """Render data tables (to be implemented by subclasses)"""
        pass
    
    def render_metrics(self, data: Dict[str, Any]):
        """Render key metrics using enhanced grid"""
        pass
    
    def handle_export(self, data: Dict[str, Any]):
        """Handle data export functionality (now integrated into containers)"""
        pass
    
    @abstractmethod
    def render_content(self):
        """Render main page content (must be implemented by subclasses)"""
        pass
    
    def render(self):
        """Main render method with enhanced error handling"""
        try:
            # Setup page (no set_page_config here)
            self.setup_page()
            
            # Render enhanced header
            self.render_header()
            
            # Add a subtle separator
            st.markdown("---")
            
            # Render main content
            self.render_content()
            
        except Exception as e:
            error_msg = f"Error rendering page {self.title}: {str(e)}"
            logger.error(error_msg)
            self.render_error(error_msg)
            raise PageRenderError(error_msg)


class FilteredPage(BasePage):
    """Enhanced base class for pages with filter functionality"""
    
    def __init__(self, title: str, icon: str = ""):
        super().__init__(title, icon)
        self.filters = {}
        self.data = {}
    
    def render_content(self):
        """Enhanced filtered page content rendering with improved UX"""
        try:
            # Enhanced sidebar filters with better organization
            with st.sidebar:
                st.markdown("""
                <div>
                    <h2 style="margin: 0;"> Filters</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Render filters in an organized way
                self.filters = self.render_sidebar_filters()
                
                # Add Settings section with technical items
                st.markdown("""
                <div>
                    <h2 style="margin: 0;"> Settings</h2>
                </div>
                """, unsafe_allow_html=True)
                
                self._render_settings_section()
            
            # Main content area
            if not self.validate_filters(self.filters):
                self.render_warning("Please check your filter selections")
                return
            
            # Process data with enhanced loading
            with self.show_loading("Processing data and generating insights..."):
                self.data = self.process_data(self.filters)
            
            # Check if data is available
            if not self.data:
                self._render_no_data_state()
                return
            
            # Check if any meaningful data exists
            has_data = self._check_data_availability()
            
            if not has_data:
                self._render_no_data_state()
                return
            
            # Render metrics using enhanced grid
            self.render_metrics(self.data)
            
            # Add separator
            st.markdown("---")
            
            # Main analysis section
            st.subheader("Analysis Results")
            
            # Create main content sections with enhanced containers
            self._render_main_analysis()
            
        except Exception as e:
            error_msg = f"Error in filtered page content: {str(e)}"
            logger.error(error_msg)
            self.render_error(error_msg)
    
    def _check_data_availability(self) -> bool:
        """Check if meaningful data exists"""
        has_data = False
        for key, value in self.data.items():
            if key == "debug_info":
                continue
            if isinstance(value, pd.DataFrame) and not value.empty:
                has_data = True
                break
            elif value is not None and not (isinstance(value, (list, dict)) and len(value) == 0):
                has_data = True
                break
        return has_data
    
    def _render_no_data_state(self):
        """Render enhanced no-data state"""
        st.markdown("""
        <div style="
            text-align: center;
            padding: 3rem;
            background: #f8f9fa;
            border-radius: 10px;
            margin: 2rem 0;
        ">
            <h2>No Data Available</h2>
            <p>Try adjusting your filters to see results:</p>
            <ul style="text-align: left; display: inline-block;">
                <li>Expand date ranges</li>
                <li>Select more filter options</li>
                <li>Check if data exists for the selected period</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_settings_section(self):
        """Render Settings section with individual expandable subsections"""
        # Cache Monitor
        with st.expander("Cache Monitor", expanded=False):
            self._render_cache_monitor()
        
        # Visualization Options (to be populated by subclasses)
        with st.expander("Visualization Options", expanded=False):
            self._render_visualization_settings()
    
    def _render_cache_monitor(self):
        """Render cache monitoring section"""
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                try:
                    # Get cache stats
                    cache_stats = self.db_manager.get_cache_stats()
                    
                    if not cache_stats:
                        st.warning("Cache not available")
                        return
                    
                    basic_stats = cache_stats.get("basic_stats", {})
                    
                    # Quick stats
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Hit Rate", f"{basic_stats.get('hit_rate', 0):.1f}%")
                        st.metric("Entries", f"{basic_stats.get('total_entries', 0)}")
                    
                    with col2:
                        st.metric("Size", f"{basic_stats.get('total_size_mb', 0):.1f}MB")
                        st.metric("Hits", f"{basic_stats.get('hits', 0)}")
                    
                    # Cache actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Warm Cache", help="Pre-load common queries", key="warm_cache_settings"):
                            with st.spinner("Warming cache..."):
                                self.db_manager.warm_cache()
                            st.success("Cache warmed!")
                            st.rerun()
                    
                    with col2:
                        if st.button("Clear Cache", help="Clear all cached data", key="clear_cache_settings"):
                            self.db_manager.invalidate_cache()
                            st.success("Cache cleared!")
                            st.rerun()
                    
                    # Show detailed stats if cache is active
                    if basic_stats.get('total_entries', 0) > 0:
                        with st.expander("Detailed Cache Stats"):
                            st.json(cache_stats)
                
                except Exception as e:
                    st.error(f"Cache monitor error: {e}")
                    logger.error(f"Cache monitor error: {e}")
            else:
                st.info("Database manager not available")
                
        except ImportError:
            st.info("Cache monitoring not available")
        except Exception as e:
            st.error(f"Error loading cache monitor: {e}")
    
    def _render_visualization_settings(self):
        """Render visualization settings - to be overridden by subclasses"""
        # This method should be overridden by subclasses to provide
        # page-specific visualization options
        pass
    

    def _render_main_analysis(self):
        """Render main analysis with enhanced containers"""
        # This method should be overridden by subclasses to provide
        # specific analysis rendering using the new DataChartContainer
        
        # Default implementation shows data and visualizations side by side
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self.render_data_tables(self.data)
        
        with col2:
            self.render_visualizations(self.data)


class ChartHelper:
    """Enhanced helper class for chart creation with modern styling"""
    
    @staticmethod
    def format_number(value: float, format_type: str = "currency") -> str:
        """Enhanced number formatting with consistent logic"""
        if pd.isna(value):
            return "N/A"
        
        # Import decimal for type checking
        from decimal import Decimal
        
        # Convert to float if it's a Decimal (same fix as render_metrics_grid)
        if isinstance(value, Decimal):
            value = float(value)
            
        if format_type == "currency":
            if isinstance(value, (int, float)):
                if value >= 1_000_000_000:
                    # Billions - NEW: This was missing!
                    return f"${value/1_000_000_000:.1f}B"
                elif value >= 1_000_000:
                    # Millions - check if it's clean thousands of millions
                    millions = value / 1_000_000
                    if millions >= 1000:
                        # Show as comma-separated millions (e.g., 5,017M)
                        return f"${millions:,.0f}M"
                    else:
                        # Show as decimal millions (e.g., 123.5M)
                        return f"${millions:.1f}M"
                elif value >= 1_000:
                    # Thousands
                    return f"${value/1_000:.0f}K"
                else:
                    # Less than 1000
                    return f"${value:,.0f}"
            else:
                return str(value)
        elif format_type == "percentage":
            return f"{value:.1%}" if isinstance(value, (int, float)) else str(value)
        elif format_type == "number":
            if isinstance(value, (int, float)):
                if value >= 1_000_000:
                    return f"{value/1_000_000:.1f}M"
                elif value >= 1_000:
                    return f"{value/1_000:.1f}K"
                else:
                    return f"{value:,}"
            else:
                return str(value)
        else:
            return str(value)
    
    @staticmethod
    def get_color_palette(n_colors: int, scheme: str = "viridis") -> list:
        """Get enhanced color palette"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.colors as mcolors
            
            cmap = plt.get_cmap(scheme)
            colors = [mcolors.to_hex(cmap(i / n_colors)) for i in range(n_colors)]
            return colors
        except:
            # Fallback to default colors
            default_colors = [
                "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
            ]
            return (default_colors * ((n_colors // len(default_colors)) + 1))[:n_colors]
    
    @staticmethod
    def create_gradient_background(color1: str = "#667eea", color2: str = "#764ba2") -> str:
        """Create CSS gradient background"""
        return f"background: linear-gradient(135deg, {color1} 0%, {color2} 100%);"
    
    @staticmethod
    def get_status_color(status: str) -> str:
        """Get color based on contract status"""
        status_colors = {
            "approved": "#28a745",
            "pending": "#ffc107", 
            "draft": "#6c757d",
            "rejected": "#dc3545",
            "active": "#17a2b8",
            "expired": "#6f42c1"
        }
        return status_colors.get(status.lower(), "#007bff")