"""
UI Components Module for Agiloft CLM Analytics
Create this file at: ui/components.py
"""

import streamlit as st
import pandas as pd
import altair as alt
try:
    import sqlparse
except ImportError:
    sqlparse = None
from typing import Dict, Any, Optional, Union, Tuple
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

class DataChartContainer:
    """Enhanced data presentation component with tabbed interface"""
    
    def __init__(self, key: str):
        self.key = key
    
    def render(
        self,
        dataframe: pd.DataFrame,
        chart_data: Optional[Union[alt.Chart, pd.DataFrame]] = None,
        sql_query: Optional[str] = None,
        description: Optional[str] = None,
        chart_config: Optional[Dict[str, Any]] = None,
        export_filename: Optional[str] = None
    ) -> None:
        """
        Render tabbed container with Chart, Data, SQL, Description, and Export tabs
        """
        if dataframe.empty:
            st.warning("No data available for the selected filters")
            return
        
        # Create tabs with icons
        tab_chart, tab_data, tab_description, tab_export = st.tabs([
            "Chart", 
            "Data Preview", 
            "Description", 
            "Export"
        ])
        
        # Chart Tab
        with tab_chart:
            self._render_chart_tab(dataframe, chart_data, chart_config)
        
        # Data Preview Tab
        with tab_data:
            self._render_data_tab(dataframe)
        
        # Description Tab
        with tab_description:
            self._render_description_tab(description)
        
        # Export Tab
        with tab_export:
            self._render_export_tab(dataframe, export_filename)
    
    def _render_chart_tab(
        self, 
        dataframe: pd.DataFrame, 
        chart_data: Optional[Union[alt.Chart, pd.DataFrame]], 
        chart_config: Optional[Dict[str, Any]]
    ):
        """Render the chart visualization"""
        try:
            if chart_data is None:
                # Default chart based on data structure
                if len(dataframe.columns) == 2:
                    st.bar_chart(dataframe.set_index(dataframe.columns[0]))
                else:
                    st.dataframe(dataframe, use_container_width=True)
            elif isinstance(chart_data, alt.Chart):
                st.altair_chart(chart_data, use_container_width=True)
            elif isinstance(chart_data, pd.DataFrame):
                if chart_config and chart_config.get("chart_type"):
                    chart_type = chart_config["chart_type"]
                    if chart_type == "line":
                        st.line_chart(chart_data)
                    elif chart_type == "bar":
                        st.bar_chart(chart_data)
                    elif chart_type == "area":
                        st.area_chart(chart_data)
                    else:
                        st.dataframe(chart_data, use_container_width=True)
                else:
                    st.dataframe(chart_data, use_container_width=True)
            else:
                st.dataframe(dataframe, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error rendering chart: {str(e)}")
            st.dataframe(dataframe, use_container_width=True)
    
    def _render_data_tab(self, dataframe: pd.DataFrame):
        """Render data preview with enhanced formatting"""
        st.subheader("Data Overview")
        
        # Data info metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", f"{len(dataframe):,}")
        with col2:
            st.metric("Columns", f"{len(dataframe.columns):,}")
        with col3:
            # Calculate data size
            memory_usage = dataframe.memory_usage(deep=True).sum()
            size_mb = memory_usage / (1024 * 1024)
            st.metric("Size", f"{size_mb:.2f} MB")
        with col4:
            # Show completeness
            total_cells = len(dataframe) * len(dataframe.columns)
            if total_cells > 0:
                null_cells = dataframe.isnull().sum().sum()
                completeness = (1 - null_cells / total_cells) * 100
                st.metric("Completeness", f"{completeness:.1f}%")
            else:
                st.metric("Completeness", "100%")
        
        
        # Display data with pagination for large datasets
        if len(dataframe) > 1000:
            st.info("Showing first 1,000 rows. Use export tab to download complete dataset.")
            display_df = dataframe.head(1000)
        else:
            display_df = dataframe
        
        # Enhanced dataframe display
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config=self._get_enhanced_column_config(display_df)
        )
    
    def _render_sql_tab(self, sql_query: Optional[str]):
        """Render SQL query with formatting"""
        st.subheader("SQL Query")
        
        if sql_query:
            # Format SQL for better readability if sqlparse is available
            if sqlparse:
                try:
                    formatted_sql = sqlparse.format(
                        sql_query, 
                        reindent=True, 
                        keyword_case='upper'
                    )
                    st.code(formatted_sql, language="sql")
                except Exception as e:
                    logger.warning(f"SQL formatting failed: {e}")
                    st.code(sql_query, language="sql")
            else:
                st.code(sql_query, language="sql")
                st.info("Install sqlparse for better SQL formatting: `pip install sqlparse`")
        else:
            st.info("SQL query not available for this analysis")
            st.markdown("""
            **Note**: Some analyses are performed using Python transformations 
            rather than direct SQL queries.
            """)
    
    def _render_description_tab(self, description: Optional[str]):
        """Render analysis description"""
        st.subheader("Analysis Description")
        
        if description:
            st.markdown(description)
        else:
            st.info("No specific description available for this analysis")
        
        # Add standard help content
        with st.expander("How to interpret this analysis"):
            st.markdown("""
            **Tips for using this data:**
            
            **Understanding the Data**
            - Use filters to narrow down your analysis scope
            - Check the Data Preview tab to understand data structure
            - Review column types and completeness metrics
            
            **Working with Charts**
            - Hover over chart elements for detailed tooltips
            - Use chart controls for zooming and panning where available
            - Switch between different visualization types if options are provided
            
            **Exporting Results**
            - Use the Export tab to download data in CSV or Excel format
            - Exported files include all filtered data, not just what's displayed
            - Consider the data size before exporting large datasets
            
            **Advanced Usage**
            - Check the SQL tab to understand data sources and transformations
            - Use multiple filter combinations to identify trends and patterns
            - Export data for further analysis in external tools like Excel or Tableau
            """)
    
    def _render_export_tab(self, dataframe: pd.DataFrame, export_filename: Optional[str]):
        """Render export options"""
        st.subheader("Export Data")
        
        filename = export_filename or f"agiloft_clm_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Download Options")
            
            # CSV Export
            csv_data = dataframe.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv_data,
                file_name=f"{filename}.csv",
                mime="text/csv",
                key=f"{self.key}_csv",
                help="Download data in CSV format for Excel, Google Sheets, etc."
            )
            
            # Excel Export (if openpyxl is available)
            try:
                import io
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    dataframe.to_excel(writer, sheet_name='Data', index=False)
                    
                    # Add a summary sheet if dataframe is not empty
                    if not dataframe.empty:
                        summary_data = {
                            'Metric': ['Total Rows', 'Total Columns', 'Export Date'],
                            'Value': [len(dataframe), len(dataframe.columns), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                        }
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                st.download_button(
                    label="Download as Excel",
                    data=excel_buffer.getvalue(),
                    file_name=f"{filename}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"{self.key}_excel",
                    help="Download as Excel file with multiple sheets"
                )
            except ImportError:
                st.info("Install openpyxl for Excel export functionality: `pip install openpyxl`")
        
        with col2:
            st.markdown("### Export Summary")
            
            # Show export summary in a nice info box
            st.info(f"""
            **Export Details:**
            
            **Filename**: `{filename}`  
            **Rows**: {len(dataframe):,}  
            **Columns**: {len(dataframe.columns):,}  
            **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
            **Estimated Size**: {len(csv_data) / 1024:.1f} KB
            """)
            
            # Show column list
            with st.expander("Columns included in export"):
                for i, col in enumerate(dataframe.columns, 1):
                    st.write(f"{i}. {col}")
    
    def _get_enhanced_column_config(self, dataframe: pd.DataFrame) -> Dict[str, Any]:
        """Generate enhanced column configuration for better display"""
        config = {}
        
        for col in dataframe.columns:
            # Convert column name to string to handle both string and numeric column names
            col_str = str(col).lower()
            
            # Monetary columns
            if any(keyword in col_str for keyword in ['amount', 'value', 'price', 'cost', 'revenue', 'co_amount']):
                config[col] = st.column_config.NumberColumn(
                    str(col),
                    format="$%.2f",
                    help=f"Monetary value in {col}"
                )
            # Percentage columns
            elif any(keyword in col_str for keyword in ['percent', 'rate', '%', 'pct']):
                config[col] = st.column_config.NumberColumn(
                    str(col),
                    format="%.2f%%",
                    help=f"Percentage value for {col}"
                )
            # Date columns
            elif any(keyword in col_str for keyword in ['date', 'time', 'created', 'updated']) or dataframe[col].dtype in ['datetime64[ns]']:
                config[col] = st.column_config.DatetimeColumn(
                    str(col),
                    help=f"Date/time value for {col}"
                )
            # Status columns (for better visual representation)
            elif 'status' in col_str:
                config[col] = st.column_config.TextColumn(
                    str(col),
                    help=f"Status indicator for {col}"
                )
            # Year columns (likely numeric years)
            elif col_str.isdigit() or 'year' in col_str:
                config[col] = st.column_config.NumberColumn(
                    str(col),
                    format="%.0f",
                    help=f"Year value for {col}"
                )
        
        return config


class EnhancedFilterContainer:
    """Enhanced filter container with better UX"""
    
    def __init__(self, title: str, expanded: bool = True):
        self.title = title
        self.expanded = expanded
    
    def __enter__(self):
        self.container = st.expander(self.title, expanded=self.expanded)
        return self.container.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.container.__exit__(exc_type, exc_val, exc_tb)


def enhanced_date_range_picker(
    title: str,
    default_start: Optional[date] = None,
    default_end: Optional[date] = None,
    min_date: Optional[date] = None,
    max_date: Optional[date] = None,
    key: str = "",
    help_text: Optional[str] = None
) -> Tuple[date, date]:
    """Enhanced date range picker with better UX"""
    
    st.subheader(title)
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=default_start,
            min_value=min_date,
            max_value=max_date,
            key=f"{key}_start",
            help=help_text or "Select the start date for your analysis"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=default_end,
            min_value=min_date,
            max_value=max_date,
            key=f"{key}_end",
            help=help_text or "Select the end date for your analysis"
        )
    
    # Validation with helpful feedback
    if start_date > end_date:
        st.error("Start date must be before end date")
        st.stop()
    
    # Show selected range summary
    delta = end_date - start_date
    st.info(f"Selected range: {delta.days} days")
    
    return start_date, end_date


def enhanced_multiselect(
    label: str,
    options: list,
    default: Optional[list] = None,
    key: str = "",
    help_text: Optional[str] = None,
    max_selections: Optional[int] = None
) -> list:
    """Enhanced multiselect with better UX"""
    
    # Add custom CSS for white buttons and sidebar text styling
    st.markdown("""
    <style>
    /* Button styling */
    .stButton button {
        background-color: white !important;
        color: #253A5B !important;
        border: 2px solid #253A5B !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton button:hover {
        background-color: #253A5B !important;
        color: white !important;
        border-color: #253A5B !important;
        box-shadow: 0 2px 4px rgba(37, 58, 91, 0.3) !important;
    }
    
    .stButton button:active {
        background-color: #1a2a42 !important;
        transform: translateY(1px) !important;
    }
    
    /* Sidebar text styling for better contrast */
    div[data-testid="stSidebar"] {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stMarkdown {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stMarkdown h1,
    div[data-testid="stSidebar"] .stMarkdown h2,
    div[data-testid="stSidebar"] .stMarkdown h3,
    div[data-testid="stSidebar"] .stMarkdown h4,
    div[data-testid="stSidebar"] .stMarkdown h5,
    div[data-testid="stSidebar"] .stMarkdown h6 {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stMarkdown p {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stMarkdown strong {
        color: white !important;
    }
    
    /* Sidebar form labels and text */
    div[data-testid="stSidebar"] label {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stSelectbox label,
    div[data-testid="stSidebar"] .stMultiSelect label,
    div[data-testid="stSidebar"] .stSlider label,
    div[data-testid="stSidebar"] .stTextInput label,
    div[data-testid="stSidebar"] .stNumberInput label,
    div[data-testid="stSidebar"] .stCheckbox label,
    div[data-testid="stSidebar"] .stRadio label {
        color: white !important;
    }
    
    /* Sidebar expander headers */
    div[data-testid="stSidebar"] .streamlit-expanderHeader {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .streamlit-expanderHeader p {
        color: white !important;
    }
    
    /* Sidebar info/success/warning/error messages */
    div[data-testid="stSidebar"] .stAlert {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stInfo {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stSuccess {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stWarning {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stError {
        color: white !important;
    }
    
    /* Buttons in sidebar */
    div[data-testid="stSidebar"] .stButton button {
        background-color: white !important;
        color: #253A5B !important;
        border: 2px solid #253A5B !important;
    }
    
    div[data-testid="stSidebar"] .stButton button:hover {
        background-color: #253A5B !important;
        color: white !important;
    }
    
    /* Radio button and checkbox text */
    div[data-testid="stSidebar"] .stRadio > div {
        color: white !important;
    }
    
    div[data-testid="stSidebar"] .stCheckbox > div {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Add "Select All" / "Clear All" buttons with better column layout
    col1, col2 = st.columns(2)
    
    current_selection = st.session_state.get(key, default or [])
    
    with col1:
        if st.button("Select All", key=f"{key}_select_all", help="Select all available options", use_container_width=True):
            current_selection = options[:max_selections] if max_selections else options
            st.session_state[key] = current_selection
            st.rerun()
    
    with col2:
        if st.button("Clear All", key=f"{key}_clear_all", help="Clear all selections", use_container_width=True):
            current_selection = []
            st.session_state[key] = current_selection
            st.rerun()
    
    # The actual multiselect
    selected = st.multiselect(
        label,
        options,
        key=key,
        help=help_text,
        max_selections=max_selections
    )
    
    # Show selection summary with better styling
    if selected:
        if len(selected) == len(options):
            st.success(f"All {len(options)} items selected")
        else:
            st.info(f"Selected {len(selected)} of {len(options)} items")
    else:
        st.warning("No items selected - results may be empty")
    
    return selected


def render_metrics_grid(metrics: Dict[str, Dict[str, Any]], columns: int = 4):
    """Render a grid of metrics with enhanced styling and IMPROVED currency formatting"""
    
    if not metrics:
        return
    
    # Create columns
    cols = st.columns(columns)
    
    for i, (metric_name, metric_data) in enumerate(metrics.items()):
        with cols[i % columns]:
            value = metric_data.get("value", 0)
            delta = metric_data.get("delta", None)
            help_text = metric_data.get("help", None)
            format_type = metric_data.get("format", "number")
            
            # Debug logging
            logger.info(f"Processing metric: {metric_name}, value: {value}, format_type: {format_type}")
            
            # Format value based on type with IMPROVED currency formatting
            if format_type == "currency":
                logger.info(f"Formatting currency value: {value}, type: {type(value)}")
                # Import decimal for type checking
                from decimal import Decimal
                if isinstance(value, (int, float, Decimal)):
                    # Convert to float for calculations
                    value_float = float(value)
                    if value_float >= 1_000_000_000:
                        # Billions
                        formatted_value = f"${value_float/1_000_000_000:.1f}B"
                        logger.info(f"Billions case: {formatted_value}")
                    elif value_float >= 1_000_000:
                        # Millions - check if it's clean thousands of millions
                        millions = value_float / 1_000_000
                        logger.info(f"Millions case: millions = {millions}")
                        if millions >= 1000:
                            # Show as comma-separated millions (e.g., 5,017M)
                            formatted_value = f"${millions:,.0f}M"
                            logger.info(f"Large millions case: {formatted_value}")
                        else:
                            # Show as decimal millions (e.g., 123.5M)
                            formatted_value = f"${millions:.1f}M"
                            logger.info(f"Small millions case: {formatted_value}")
                    elif value_float >= 1_000:
                        # Thousands
                        formatted_value = f"${value_float/1_000:.0f}K"
                        logger.info(f"Thousands case: {formatted_value}")
                    else:
                        # Less than 1000
                        formatted_value = f"${value_float:,.0f}"
                        logger.info(f"Small value case: {formatted_value}")
                else:
                    formatted_value = str(value)
                    logger.info(f"Non-numeric case: {formatted_value}")
            elif format_type == "percentage":
                formatted_value = f"{value:.1f}%" if isinstance(value, (int, float)) else str(value)
            elif format_type == "number":
                if isinstance(value, (int, float)):
                    if value >= 1_000_000:
                        formatted_value = f"{value/1_000_000:.1f}M"
                    elif value >= 1_000:
                        formatted_value = f"{value/1_000:.1f}K"
                    else:
                        formatted_value = f"{value:,}"
                else:
                    formatted_value = str(value)
            else:
                formatted_value = str(value)
            
            # Debug the final formatted value
            logger.info(f"Formatted value for {metric_name}: {formatted_value}")
            
            st.metric(
                label=metric_name,
                value=formatted_value,
                delta=delta,
                help=help_text
            )


def create_enhanced_chart(
    data: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    title: Optional[str] = None,
    color_scheme: str = "category10"
) -> alt.Chart:
    """Create enhanced Altair charts with better styling"""
    
    if data.empty:
        return alt.Chart(pd.DataFrame()).mark_text().encode(
            text=alt.value("No data available")
        )
    
    # Base chart
    base_chart = alt.Chart(data)
    
    # Use the color scheme from parameters
    color_scheme = color_scheme
    
    # Clean column names for display (handle both string and numeric)
    x_title = str(x_col).replace('_', ' ').title()
    y_title = str(y_col).replace('_', ' ').title()
    color_title = str(color_col).replace('_', ' ').title() if color_col else None
    
    # Determine appropriate data type for x column
    x_type = ":O"  # Ordinal by default
    if pd.api.types.is_numeric_dtype(data[x_col]):
        if data[x_col].dtype in ['int64', 'int32'] and data[x_col].nunique() < 50:
            x_type = ":O"  # Treat small numeric ranges as ordinal (like years)
        else:
            x_type = ":Q"  # Quantitative for continuous numeric data
    
    # Create chart based on type
    try:
        if chart_type == "line":
            chart = base_chart.mark_line(
                point=True,
                strokeWidth=3,
                opacity=0.8
            ).encode(
                x=alt.X(f"{x_col}{x_type}", 
                       title=x_title,
                       axis=alt.Axis(labelAngle=-45)),
                y=alt.Y(f"{y_col}:Q", 
                       title=y_title,
                       axis=alt.Axis(format='$,.0f' if 'amount' in str(y_col).lower() else ',.0f')),
                color=alt.Color(f"{color_col}:N", 
                               scale=alt.Scale(scheme=color_scheme),
                               legend=alt.Legend(title=color_title)) if color_col else alt.value("#1f77b4"),
                tooltip=list(data.columns)
            )
        elif chart_type == "bar":
            chart = base_chart.mark_bar(
                opacity=0.8,
                stroke='white',
                strokeWidth=1
            ).encode(
                x=alt.X(f"{x_col}{x_type}", 
                       title=x_title,
                       axis=alt.Axis(labelAngle=-45)),
                y=alt.Y(f"{y_col}:Q", 
                       title=y_title,
                       axis=alt.Axis(format='$,.0f' if 'amount' in str(y_col).lower() else ',.0f')),
                color=alt.Color(f"{color_col}:N", 
                               scale=alt.Scale(scheme=color_scheme),
                               legend=alt.Legend(title=color_title)) if color_col else alt.value("#1f77b4"),
                tooltip=list(data.columns)
            )
        elif chart_type == "area":
            chart = base_chart.mark_area(
                opacity=0.7,
                stroke='white',
                strokeWidth=2
            ).encode(
                x=alt.X(f"{x_col}{x_type}", 
                       title=x_title,
                       axis=alt.Axis(labelAngle=-45)),
                y=alt.Y(f"{y_col}:Q", 
                       title=y_title,
                       axis=alt.Axis(format='$,.0f' if 'amount' in str(y_col).lower() else ',.0f'),
                       stack='zero'),
                color=alt.Color(f"{color_col}:N", 
                               scale=alt.Scale(scheme=color_scheme),
                               legend=alt.Legend(title=color_title)) if color_col else alt.value("#1f77b4"),
                tooltip=list(data.columns)
            )
        else:
            # Default to scatter
            chart = base_chart.mark_circle(
                size=100,
                opacity=0.8
            ).encode(
                x=alt.X(f"{x_col}:Q", title=x_title),
                y=alt.Y(f"{y_col}:Q", title=y_title),
                color=alt.Color(f"{color_col}:N", 
                               scale=alt.Scale(scheme=color_scheme),
                               legend=alt.Legend(title=color_title)) if color_col else alt.value("#1f77b4"),
                tooltip=list(data.columns)
            )
        
        # Add title if provided
        if title:
            chart = chart.properties(
                title=alt.TitleParams(
                    text=title,
                    fontSize=16,
                    fontWeight='bold',
                    anchor='start'
                )
            )
        
        # Enhanced styling and interactivity
        chart = chart.resolve_scale(
            color='independent'
        ).properties(
            width=600,
            height=400
        ).interactive()
        
        return chart
    
    except Exception as e:
        logger.error(f"Error creating enhanced chart: {e}")
        # Return a simple fallback chart
        return alt.Chart(data).mark_bar().encode(
            x=f"{x_col}:O",
            y=f"{y_col}:Q"
        )
