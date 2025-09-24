"""
Enhanced Customer Contract Page for Agiloft CLM Analytics
Updated with themed 2x2 grid layout for Customer Performance Analysis
"""

import streamlit as st
import pandas as pd
import altair as alt
import logging
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta

from ui.base_page import FilteredPage, ChartHelper
from database.db_interface import DataTransformer
from config.settings import app_config, ui_config
from utils.exceptions import DataProcessingError

logger = logging.getLogger(__name__)

# Try to import enhanced components with fallback
try:
    from ui.components import (
        enhanced_multiselect,
        render_metrics_grid,
        create_enhanced_chart
    )
    ENHANCED_COMPONENTS_AVAILABLE = True
except ImportError:
    ENHANCED_COMPONENTS_AVAILABLE = False
    logger.warning("Enhanced components not available, using fallbacks")
    
    def enhanced_multiselect(label, options, default=None, key="", help_text=None, max_selections=None):
        return st.multiselect(label, options, default=default, key=key, help=help_text, max_selections=max_selections)
    
    def render_metrics_grid(metrics, columns=4):
        cols = st.columns(columns)
        for i, (name, data) in enumerate(metrics.items()):
            with cols[i % columns]:
                st.metric(name, data.get("value", 0), help=data.get("help"))
    
    def create_enhanced_chart(data, chart_type, x_col, y_col, color_col=None, title=None):
        if chart_type == "line":
            return st.line_chart(data.set_index(x_col)[y_col])
        elif chart_type == "bar":
            return st.bar_chart(data.set_index(x_col)[y_col])
        else:
            return st.dataframe(data)

def enhanced_customer_selector(available_customers, key="customer_selector", default_count=20):
    """Enhanced customer selector with search and quick actions"""

    if not available_customers:
        st.warning("No customers found in database")
        return []

    # Initialize session state
    search_key = f"{key}_search"
    selection_key = f"{key}_selection"

    if selection_key not in st.session_state:
        # Smart default: Use first N customers alphabetically
        default_customers = available_customers[:min(default_count, len(available_customers))]
        st.session_state[selection_key] = default_customers
        st.info(f"Showing first {len(default_customers)} customers alphabetically")

    if search_key not in st.session_state:
        st.session_state[search_key] = ""

    # Quick action buttons
    st.markdown("**Quick Selection Actions:**")

    # Row 1: Top 10 customers
    if st.button(
        "First 10 Customers",
        key=f"{key}_top10",
        help="Select the first 10 customers alphabetically",
        use_container_width=True
    ):
        st.session_state[selection_key] = available_customers[:10]
        st.success(f"Selected first 10 customers")

    # Row 2: Top N customers
    if st.button(
        f"First {default_count} Customers",
        key=f"{key}_top_default",
        help=f"Select the first {default_count} customers alphabetically",
        use_container_width=True
    ):
        st.session_state[selection_key] = available_customers[:default_count]
        st.success(f"Selected first {default_count} customers")

    # Row 3: Select All
    if st.button(
        "All Customers",
        key=f"{key}_all_customers",
        help="Select all available customers",
        use_container_width=True
    ):
        st.session_state[selection_key] = available_customers.copy()
        st.success(f"Selected all {len(available_customers)} customers")

    # Row 4: Clear All
    if st.button(
        "Clear Selections",
        key=f"{key}_clear",
        help="Clear all current selections",
        use_container_width=True
    ):
        st.session_state[selection_key] = []
        st.info("Cleared all selections")

    st.markdown("---")

    # Search box
    search_term = st.text_input(
        "Search Customers",
        value=st.session_state[search_key],
        placeholder="Type to search by customer name...",
        key=f"{search_key}_input",
        help="Filter customers by name. Search is case-insensitive."
    )

    # Update search state
    if search_term != st.session_state[search_key]:
        st.session_state[search_key] = search_term

    # Filter customers based on search
    if search_term:
        filtered_customers = []
        search_lower = search_term.lower()

        for customer in available_customers:
            if search_lower in customer.lower():
                filtered_customers.append(customer)

        # Sort by relevance
        filtered_customers.sort(key=lambda x: (
            0 if x.lower() == search_term.lower() else
            1 if x.lower().startswith(search_term.lower()) else
            2
        ))
    else:
        filtered_customers = available_customers

    # Quick actions for filtered results
    if search_term and filtered_customers:
        st.markdown("**Actions for Search Results:**")

        # Select all search results
        if st.button(
            f"Select All {len(filtered_customers)} Search Results",
            key=f"{key}_all_filtered",
            help="Select all customers from current search results",
            use_container_width=True
        ):
            st.session_state[selection_key] = filtered_customers.copy()
            st.success(f"Selected {len(filtered_customers)} search results")

        # Add search results to current selection
        if st.button(
            f"Add Search Results to Selection",
            key=f"{key}_add_filtered",
            help="Add search results to current selection",
            use_container_width=True
        ):
            current_selection = st.session_state.get(selection_key, [])
            new_additions = 0
            for customer in filtered_customers:
                if customer not in current_selection:
                    current_selection.append(customer)
                    new_additions += 1
            st.session_state[selection_key] = current_selection
            if new_additions > 0:
                st.success(f"Added {new_additions} new customers to selection")
            else:
                st.info("All search results were already selected")

    # Show search results info
    if search_term:
        st.info(f"Found {len(filtered_customers)} customers matching '{search_term}'")

    # Selection summary and multiselect
    current_selection = st.session_state.get(selection_key, [])

    if current_selection:
        # Show compact summary
        if len(current_selection) <= 3:
            summary_text = f"**Currently selected:** {', '.join(current_selection)}"
        else:
            summary_text = f"**{len(current_selection)} customers selected**"

        st.markdown(summary_text)

        # Checkbox to show/hide full selection for editing
        show_full_selection = st.checkbox(
            "Show full selection for editing",
            value=False,
            key=f"{key}_show_selection",
            help="Check this box to view and edit the complete customer selection"
        )

        if show_full_selection:
            # Use the filtered list for options, but maintain current selection
            display_options = filtered_customers

            # Ensure current selection is included in options
            for selected in current_selection:
                if selected not in display_options and selected in available_customers:
                    display_options.append(selected)

            selected_customers = st.multiselect(
                f"Edit Selection ({len(current_selection)} currently selected)",
                options=display_options,
                default=current_selection,
                key=f"{key}_multiselect",
                help="Modify your current customer selection"
            )
        else:
            selected_customers = current_selection
    else:
        # No selection yet - show normal multiselect
        st.warning("No customers selected - please choose customers above or use the selection below")

        selected_customers = st.multiselect(
            "Select Customers",
            options=filtered_customers,
            default=[],
            key=f"{key}_multiselect",
            help="Choose which customers to include in your analysis"
        )

    # Update session state
    st.session_state[selection_key] = selected_customers

    # Final selection summary
    if selected_customers:
        if len(selected_customers) == len(available_customers):
            st.info(f"All {len(available_customers)} customers selected")
        else:
            st.info(f"{len(selected_customers)} of {len(available_customers)} customers selected")

    return selected_customers

class CustomerPage(FilteredPage):
    """Enhanced page for displaying contract data by customer with 2x2 grid layout"""
    
    def __init__(self):
        super().__init__("Contract Value ($) by Customer", "")
        self.transformer = DataTransformer()
        self.chart_helper = ChartHelper()
    
    def render_sidebar_filters(self) -> Dict[str, Any]:
        """Render enhanced sidebar filters for customer page"""
        try:
            # Customer Selection Filter (NEW APPROACH)
            with st.expander("Customer Selection", expanded=False):
                # Get available customers from database
                available_customers = self.db_manager.get_available_customers()

                if available_customers:
                    selected_customers = enhanced_customer_selector(
                        available_customers=available_customers,
                        key="customer_customers_enhanced",
                        default_count=20
                    )
                else:
                    st.warning("No customers found in database")
                    selected_customers = []

            # Date Range Filter
            with st.expander("Time Period", expanded=False):
                current_year = datetime.now().year
                start_year = current_year - 10

                year_range = st.slider(
                    "Contract Year Range",
                    min_value=start_year,
                    max_value=current_year,
                    value=(start_year, current_year),
                    help="Select the range of years to include"
                )

            return {
                "selected_customers": selected_customers,
                "year_range": year_range
            }

        except Exception as e:
            logger.error(f"Error rendering customer sidebar filters: {str(e)}")
            self.render_error("Error loading filter options")
            return {}
    
    def _render_visualization_settings(self):
        """Override to provide customer page specific visualization options"""
        chart_style = st.radio(
            "Chart Style",
            ["Bar Chart", "Line Chart", "Stacked Bar", "Area Chart"],
            index=0,
            horizontal=True,
            help="Select how to display the customer data",
            key="customer_chart_style"
        )
        
        show_trend = st.checkbox(
            "Show Trend Analysis",
            value=True,
            help="Display trend lines and growth metrics",
            key="customer_show_trend"
        )
        
        top_n_customers = st.slider(
            "Top N Customers to Display",
            min_value=5,
            max_value=50,
            value=20,
            help="Limit the number of customers shown in main charts",
            key="customer_top_n"
        )
        
        # Color scheme - SAME AS STATUS PAGE
        color_scheme = st.selectbox(
            "Color Scheme",
            ["category10", "viridis", "plasma", "blues", "greens", "oranges"],
            index=1,  # Default to viridis
            help="Choose color palette for visualizations",
            key="customer_color_scheme"
        )
        
        st.markdown("**Data Processing Options**")
        
        aggregate_by = st.selectbox(
            "Primary Analysis View",
            ["Both Year & Customer", "By Year Only", "By Customer Only"],
            index=0,
            help="Choose primary way to aggregate contract data",
            key="customer_aggregate_by"
        )
        
        include_zero_values = st.checkbox(
            "Include Zero Values",
            value=False,
            help="Include customers/years with zero contract value",
            key="customer_include_zero"
        )
        
        # Advanced filters
        min_customer_value = st.number_input(
            "Minimum Customer Total Value ($)",
            min_value=0.0,
            value=0.0,
            step=10000.0,
            help="Filter out customers below this total value",
            key="customer_min_value"
        )
        
        # Update filters with visualization settings
        if hasattr(self, 'filters'):
            self.filters.update({
                "chart_style": chart_style,
                "show_trend": show_trend,
                "top_n_customers": top_n_customers,
                "aggregate_by": aggregate_by,
                "include_zero_values": include_zero_values,
                "color_scheme": color_scheme,
                "min_customer_value": min_customer_value
            })
    
    def validate_filters(self, filters: Dict[str, Any]) -> bool:
        """Enhanced filter validation"""
        if not filters:
            return False

        selected_customers = filters.get("selected_customers")
        if not selected_customers:
            self.render_warning("Please select at least one customer")
            st.info("**Tip**: Use the 'First 20 Customers' quick action button to get started")
            return False

        year_range = filters.get("year_range")
        if year_range and year_range[0] > year_range[1]:
            self.render_warning("Invalid year range: start year must be before end year")
            return False

        return True
    
    def process_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced data processing with additional analytics"""
        try:
            logger.info(f"Processing customer data with {len(filters.get('selected_customers', []))} customers")

            # Get raw data from database - NEW APPROACH
            raw_data = self.db_manager.get_customer_contract_data(
                selected_customers=filters["selected_customers"],
                year_range=filters["year_range"]
            )
            
            if raw_data.empty:
                return {}
            
            # Apply minimum value filter
            min_value = filters.get("min_customer_value", 0)
            if min_value > 0:
                customer_totals = raw_data.groupby("c_name")["total_contract_value"].sum()
                valid_customers = customer_totals[customer_totals >= min_value].index
                raw_data = raw_data[raw_data["c_name"].isin(valid_customers)]
            
            # Transform data for display
            pivot_data = self.transformer.pivot_customer_data(raw_data)
            
            # Filter out zero values if requested
            if not filters["include_zero_values"]:
                pivot_data = pivot_data.loc[(pivot_data != 0).any(axis=1)]
                pivot_data = pivot_data.loc[:, (pivot_data != 0).any(axis=0)]
            
            # Limit to top N customers by total value
            if filters["top_n_customers"] < len(pivot_data):
                customer_totals = pivot_data.sum(axis=1).sort_values(ascending=False)
                top_customers = customer_totals.head(filters["top_n_customers"]).index
                pivot_data = pivot_data.loc[top_customers]
            
            # Prepare data for different aggregations
            aggregated_data = self._prepare_enhanced_aggregated_data(raw_data, filters)
            
            # Calculate trends if requested
            trend_data = {}
            if filters["show_trend"]:
                trend_data = self._calculate_enhanced_trends(raw_data, filters)
            
            # Calculate enhanced summary statistics
            summary_stats = self._calculate_enhanced_summary_stats(raw_data, filters)
            
            # Create enhanced charts
            enhanced_charts = self._create_customer_charts(raw_data, pivot_data, filters)
            
            return {
                "raw_data": raw_data,
                "pivot_data": pivot_data,
                "aggregated_data": aggregated_data,
                "trend_data": trend_data,
                "summary_stats": summary_stats,
                "enhanced_charts": enhanced_charts,
                "sql_query": f"""
                -- Customer contract analysis with UUID-compatible joins
                SELECT
                    c.c_name,
                    YEAR(co.co_datesigned) as contract_year,
                    SUM(co.co_amount) as total_contract_value
                FROM contract co
                JOIN customer c ON c.c_custkey = co.co_custkey
                WHERE c.c_name IN ({', '.join([f"'{c}'" for c in filters['selected_customers']])})
                    AND YEAR(co.co_datesigned) BETWEEN {filters['year_range'][0]} AND {filters['year_range'][1]}
                GROUP BY c.c_name, YEAR(co.co_datesigned)
                ORDER BY c.c_name, contract_year
                -- Note: Direct UUID string join (c.c_custkey = co.co_custkey)
                -- Selected {len(filters['selected_customers'])} customers
                """
            }
            
        except Exception as e:
            logger.error(f"Error processing customer data: {str(e)}")
            raise DataProcessingError(f"Failed to process customer data: {str(e)}")
    
    def _prepare_enhanced_aggregated_data(self, raw_data: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Prepare enhanced aggregated data with additional insights"""
        aggregated_data = {}
        
        aggregate_by = filters["aggregate_by"]
        
        if aggregate_by in ["By Year Only", "Both Year & Customer"]:
            # Aggregate by year with additional metrics
            year_agg = raw_data.groupby("contract_year").agg({
                "total_contract_value": ["sum", "mean", "count"],
                "c_name": "nunique"
            }).round(2)
            
            # Flatten column names
            year_agg.columns = ["Total Value", "Average Value", "Contract Count", "Unique Customers"]
            year_agg = year_agg.reset_index()
            aggregated_data["by_year"] = year_agg
        
        if aggregate_by in ["By Customer Only", "Both Year & Customer"]:
            # Aggregate by customer with additional metrics
            customer_agg = raw_data.groupby("c_name").agg({
                "total_contract_value": ["sum", "mean", "count"],
                "contract_year": ["min", "max"]
            }).round(2)
            
            # Flatten column names
            customer_agg.columns = ["Total Value", "Average Value", "Contract Count", "First Year", "Last Year"]
            customer_agg["Years Active"] = customer_agg["Last Year"] - customer_agg["First Year"] + 1
            customer_agg = customer_agg.sort_values("Total Value", ascending=False).reset_index()
            aggregated_data["by_customer"] = customer_agg
        
        return aggregated_data
    
    def _calculate_enhanced_trends(self, raw_data: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced trend analysis with more insights"""
        try:
            # Overall year-over-year trends
            year_totals = raw_data.groupby("contract_year")["total_contract_value"].sum()
            year_growth = year_totals.pct_change() * 100
            
            # Calculate compound annual growth rate (CAGR)
            if len(year_totals) > 1:
                years = len(year_totals) - 1
                cagr = ((year_totals.iloc[-1] / year_totals.iloc[0]) ** (1/years) - 1) * 100
            else:
                cagr = 0
            
            # Customer lifecycle analysis
            customer_lifecycle = {}
            for customer in raw_data["c_name"].unique():
                customer_data = raw_data[raw_data["c_name"] == customer]
                years_active = customer_data["contract_year"].nunique()
                total_value = customer_data["total_contract_value"].sum()
                avg_annual_value = total_value / years_active if years_active > 0 else 0
                
                customer_lifecycle[customer] = {
                    "years_active": years_active,
                    "total_value": total_value,
                    "avg_annual_value": avg_annual_value,
                    "first_year": customer_data["contract_year"].min(),
                    "last_year": customer_data["contract_year"].max()
                }
            
            # Identify customer segments
            lifecycle_df = pd.DataFrame.from_dict(customer_lifecycle, orient="index")
            
            # Growth vs decline analysis
            growing_customers = []
            declining_customers = []
            
            for customer in raw_data["c_name"].unique():
                customer_data = raw_data[raw_data["c_name"] == customer]
                if len(customer_data) > 1:
                    customer_yearly = customer_data.groupby("contract_year")["total_contract_value"].sum()
                    if len(customer_yearly) > 1:
                        trend = customer_yearly.iloc[-1] - customer_yearly.iloc[0]
                        if trend > 0:
                            growing_customers.append((customer, trend))
                        elif trend < 0:
                            declining_customers.append((customer, abs(trend)))
            
            return {
                "year_totals": year_totals,
                "year_growth": year_growth,
                "cagr": cagr,
                "avg_growth": year_growth.mean(),
                "best_year": year_totals.idxmax(),
                "worst_year": year_totals.idxmin(),
                "customer_lifecycle": lifecycle_df,
                "growing_customers": sorted(growing_customers, key=lambda x: x[1], reverse=True)[:10],
                "declining_customers": sorted(declining_customers, key=lambda x: x[1], reverse=True)[:10]
            }
        except Exception as e:
            logger.error(f"Error calculating trends: {str(e)}")
            return {}
    
    def _calculate_enhanced_summary_stats(self, data: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced summary statistics"""
        try:
            total_contracts = len(data)
            total_value = data["total_contract_value"].sum()
            avg_value = data["total_contract_value"].mean()
            median_value = data["total_contract_value"].median()
            unique_customers = data["c_name"].nunique()
            unique_years = data["contract_year"].nunique()
            
            # Top customer analysis
            top_customer_data = data.groupby("c_name")["total_contract_value"].sum()
            top_customer = top_customer_data.idxmax()
            top_customer_value = top_customer_data.max()
            
            # Value distribution analysis
            q75 = data["total_contract_value"].quantile(0.75)
            q25 = data["total_contract_value"].quantile(0.25)
            
            # Customer retention analysis
            customer_years = data.groupby("c_name")["contract_year"].nunique()
            avg_customer_longevity = customer_years.mean()
            
            return {
                "total_contracts": total_contracts,
                "total_value": total_value,
                "avg_value": avg_value,
                "median_value": median_value,
                "q75": q75,
                "q25": q25,
                "unique_customers": unique_customers,
                "unique_years": unique_years,
                "top_customer": top_customer,
                "top_customer_value": top_customer_value,
                "avg_customer_longevity": avg_customer_longevity
            }
        except Exception as e:
            logger.error(f"Error calculating summary stats: {str(e)}")
            return {}
    
    def _create_customer_charts(self, raw_data: pd.DataFrame, pivot_data: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced charts for customer analysis"""
        charts = {}
        
        try:
            # Main customer trend chart
            if not pivot_data.empty and ENHANCED_COMPONENTS_AVAILABLE:
                # Prepare data for main chart
                chart_data = pivot_data.reset_index()
                chart_data = pd.melt(
                    chart_data,
                    id_vars="c_name",
                    var_name="contract_year", 
                    value_name="total_value"
                )
                
                # Ensure contract_year is string for consistency
                chart_data["contract_year"] = chart_data["contract_year"].astype(str)
                
                chart_type_map = {
                    "Bar Chart": "bar",
                    "Line Chart": "line",
                    "Stacked Bar": "bar",
                    "Area Chart": "area"
                }
                
                chart_type = chart_type_map.get(filters.get("chart_style", "Bar Chart"), "bar")
                
                charts["main_chart"] = create_enhanced_chart(
                    data=chart_data,
                    chart_type=chart_type,
                    x_col="contract_year",
                    y_col="total_value",
                    color_col="c_name",
                    title=f"Customer Contract Trends ({filters.get('chart_style', 'Bar Chart')})",
                    color_scheme=filters.get("color_scheme", "category10")
                )
            
            # Top customers chart
            if not raw_data.empty and ENHANCED_COMPONENTS_AVAILABLE:
                top_customers = raw_data.groupby("c_name")["total_contract_value"].sum().sort_values(ascending=False).head(10)
                top_customers_df = top_customers.reset_index()
                top_customers_df.columns = ["Customer", "Total Value"]
                
                charts["top_customers"] = create_enhanced_chart(
                    data=top_customers_df,
                    chart_type="bar",
                    x_col="Customer",
                    y_col="Total Value",
                    title="Top 10 Customers by Total Contract Value",
                    color_scheme=filters.get("color_scheme", "category10")
                )
            
        except Exception as e:
            logger.error(f"Error creating customer charts: {str(e)}")
        
        return charts
    
    def render_metrics(self, data: Dict[str, Any]):
        """Render enhanced metrics using the new grid system"""
        if not data.get("summary_stats"):
            return
        
        stats = data["summary_stats"]
        
        st.subheader("Customer Contract Overview")
        
        # Create metrics dictionary for the enhanced grid
        metrics = {
            "Total Customers": {
                "value": stats["unique_customers"],
                "format": "number",
                "help": "Number of unique customers in the analysis"
            },
            "Total Value": {
                "value": stats["total_value"],
                "format": "currency",
                "help": "Sum of all contract values"
            },
            "Average Value": {
                "value": stats["avg_value"],
                "format": "currency", 
                "help": "Average contract value per customer"
            },
            "Years Covered": {
                "value": stats["unique_years"],
                "format": "number",
                "help": "Number of years in the analysis period"
            }
        }
        
        # Render primary metrics grid
        render_metrics_grid(metrics, columns=4)
        
        # Additional insights
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"""
            **Top Customer**  
            **{stats.get('top_customer', 'N/A')}**  
            Total Value: {self.chart_helper.format_number(stats.get('top_customer_value', 0))}
            """)
        
        with col2:
            st.info(f"""
            **Value Distribution**  
            Median: \{self.chart_helper.format_number(stats.get('median_value', 0))}  
            75th Percentile: \{self.chart_helper.format_number(stats.get('q75', 0))}
            """)
        
        with col3:
            st.info(f"""
            **Customer Retention**  
            Avg Years Active: {stats.get('avg_customer_longevity', 0):.1f}  
            Long-term Relationships
            """)
    
    def _render_main_analysis(self):
        """Override main analysis rendering with tabbed container + enhanced grid"""
        if ENHANCED_COMPONENTS_AVAILABLE:
            # Main Analysis Container
            main_container = self.create_data_container("customer_main_analysis")
            
            description = f"""
            ## Customer Contract Analysis
            
            This analysis provides comprehensive insights into contract performance by customer over time.
            
            **Key Features:**
            - Track contract values by customer across multiple years
            - Identify top-performing customers and revenue trends
            - Analyze customer lifecycle and retention patterns
            - Compare year-over-year growth and performance
            
            **Current Analysis Scope:**
            - Selected Customers: {len(self.filters.get('selected_customers', []))} customers selected
            - Time Period: {self.filters.get('year_range', (0, 0))[0]} to {self.filters.get('year_range', (0, 0))[1]}
            - Display: Top {self.filters.get('top_n_customers', 20)} customers
            - Minimum Value Filter: ${self.filters.get('min_customer_value', 0):,.0f}

            **Enhanced Customer Selection Features:**
            - **Smart Search**: Find customers instantly by typing
            - **Quick Actions**: First 10, First 20, All Customers, Clear All
            - **Visual Feedback**: Clear selection summary
            - **UUID Support**: Compatible with new database schema
            """
            
            # Render main analysis with tabbed interface
            main_container.render(
                dataframe=self.data.get("pivot_data", pd.DataFrame()),
                chart_data=self.data.get("enhanced_charts", {}).get("main_chart"),
                sql_query=self.data.get("sql_query"),
                description=description,
                export_filename="customer_contract_analysis"
            )
        else:
            # Fallback to basic display
            st.subheader("Customer Analysis")
            if "pivot_data" in self.data:
                st.dataframe(self.data["pivot_data"], use_container_width=True)
        
        # Enhanced Analysis Sections with 2x2 Grid
        if self.data.get("aggregated_data") or self.data.get("trend_data"):
            st.markdown("---")
            
            # Create tabs for different analysis views
            analysis_tabs = st.tabs([
                "Customer Performance", 
                "Trend Analysis", 
                "Customer Lifecycle"
            ])
            
            with analysis_tabs[0]:
                self._render_customer_performance_analysis()
            
            with analysis_tabs[1]:
                if self.filters.get("show_trend"):
                    self._render_trend_analysis()
                else:
                    st.info("Enable 'Show Trend Analysis' in filters to view trend insights")
            
            with analysis_tabs[2]:
                self._render_customer_lifecycle_analysis()
    
    def _render_customer_performance_analysis(self):
        """Render customer performance analysis with 2x2 grid: tables + charts with theme support"""
        st.subheader("Customer Performance Analysis")
        
        if "aggregated_data" not in self.data:
            st.info("No aggregated data available")
            return
        
        aggregated_data = self.data["aggregated_data"]
        color_scheme = self.filters.get("color_scheme", "viridis")  # Get theme from filters
        
        # Add custom CSS for consistent cell heights
        st.markdown("""
        <style>
        .performance-grid-cell {
            height: 400px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # ROW 1: Top Customers by Total Value (table) | Annual Performance (table)
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_top_customers_table(aggregated_data)
        
        with col2:
            self._render_annual_performance_table(aggregated_data)
        
        # ROW 2: Top Customers by Total Value (chart) | Annual Performance (chart)
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_top_customers_chart(aggregated_data, color_scheme)
        
        with col2:
            self._render_annual_performance_chart(aggregated_data, color_scheme)

    
    def _render_top_customers_table(self):
        """Render top customers table"""
        st.markdown("#### Top Customers by Total Value")
        
        if "aggregated_data" not in self.data or "by_customer" not in self.data["aggregated_data"]:
            st.info("No customer data available")
            return
        
        customer_data = self.data["aggregated_data"]["by_customer"].head(15)
        
        st.dataframe(
            customer_data,
            use_container_width=True,
            height=350,
            column_config={
                "c_name": "Customer",
                "Total Value": st.column_config.NumberColumn(
                    "Total Value",
                    format="$%.0f"
                ),
                "Average Value": st.column_config.NumberColumn(
                    "Avg Value",
                    format="$%.0f"
                ),
                "Contract Count": "Contracts",
                "Years Active": "Years",
                "First Year": "Start",
                "Last Year": "End"
            },
            hide_index=True
        )
    
    def _render_annual_performance_table(self):
        """Render annual performance table"""
        st.markdown("#### Annual Performance")
        
        if "aggregated_data" not in self.data or "by_year" not in self.data["aggregated_data"]:
            st.info("No annual data available")
            return
        
        year_data = self.data["aggregated_data"]["by_year"]
        
        st.dataframe(
            year_data,
            use_container_width=True,
            height=350,
            column_config={
                "contract_year": "Year",
                "Total Value": st.column_config.NumberColumn(
                    "Total Value",
                    format="$%.0f"
                ),
                "Average Value": st.column_config.NumberColumn(
                    "Avg Value", 
                    format="$%.0f"
                ),
                "Contract Count": "Contracts",
                "Unique Customers": "Customers"
            },
            hide_index=True
        )
    
    def _render_top_customers_table(self, aggregated_data):
        """Render top customers table"""
        st.markdown("#### Top Customers by Total Value")
        
        if "by_customer" not in aggregated_data:
            st.info("No customer data available")
            return
        
        customer_data = aggregated_data["by_customer"].head(15)
        
        st.dataframe(
            customer_data,
            use_container_width=True,
            height=350,
            column_config={
                "c_name": "Customer",
                "Total Value": st.column_config.NumberColumn(
                    "Total Value",
                    format="$%.0f"
                ),
                "Average Value": st.column_config.NumberColumn(
                    "Avg Value",
                    format="$%.0f"
                ),
                "Contract Count": "Contracts",
                "Years Active": "Years",
                "First Year": "Start",
                "Last Year": "End"
            },
            hide_index=True
        )
    
    def _render_annual_performance_table(self, aggregated_data):
        """Render annual performance table"""
        st.markdown("#### Annual Performance")
        
        if "by_year" not in aggregated_data:
            st.info("No yearly data available")
            return
        
        year_data = aggregated_data["by_year"]
        
        st.dataframe(
            year_data,
            use_container_width=True,
            height=350,
            column_config={
                "contract_year": "Year",
                "Total Value": st.column_config.NumberColumn(
                    "Total Value",
                    format="$%.0f"
                ),
                "Average Value": st.column_config.NumberColumn(
                    "Avg Value", 
                    format="$%.0f"
                ),
                "Contract Count": "Contracts",
                "Unique Customers": "Customers"
            },
            hide_index=True
        )
    
    def _render_top_customers_chart(self, aggregated_data, color_scheme):
        """Render top customers chart with theme support"""
        st.markdown("#### Top Customers (Chart)")
        
        if "by_customer" not in aggregated_data:
            st.info("No customer data for chart")
            return
        
        try:
            # Get top 10 customers for chart
            customer_data = aggregated_data["by_customer"].head(10).copy()
            
            # Create themed Altair chart
            chart = alt.Chart(customer_data).mark_bar(
                opacity=0.8,
                stroke='white',
                strokeWidth=1
            ).encode(
                x=alt.X("Total Value:Q", title="Total Contract Value", axis=alt.Axis(format="$,.0f")),
                y=alt.Y("c_name:N", title="Customer", sort="-x"),
                color=alt.Color(
                    "c_name:N",
                    scale=alt.Scale(scheme=color_scheme),
                    legend=None  # Hide legend since y-axis shows names
                ),
                tooltip=[
                    alt.Tooltip("c_name:N", title="Customer"),
                    alt.Tooltip("Total Value:Q", title="Total Value", format="$,.0f"),
                    alt.Tooltip("Contract Count:Q", title="Contracts"),
                    alt.Tooltip("Years Active:Q", title="Years Active")
                ]
            ).properties(
                width=350,
                height=350,
                title="Top 10 Customers by Value"
            )
            
            st.altair_chart(chart, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering customer chart: {str(e)}")
            # Fallback to simple chart
            try:
                chart_data = customer_data.set_index("c_name")["Total Value"]
                st.bar_chart(chart_data, height=350)
            except:
                st.info("Chart data unavailable")

    def _render_trend_analysis(self):
        """Render enhanced trend analysis"""
        st.subheader("Trend Analysis & Growth Metrics")
        
        if "trend_data" not in self.data:
            st.info("No trend data available")
            return
        
        trend_data = self.data["trend_data"]
        
        # Overall growth metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            cagr = trend_data.get("cagr", 0)
            st.metric(
                "Compound Annual Growth Rate",
                f"{cagr:.1f}%",
                help="Average yearly growth rate across the analysis period"
            )
        
        with col2:
            avg_growth = trend_data.get("avg_growth", 0)
            st.metric(
                "Average YoY Growth",
                f"{avg_growth:.1f}%",
                help="Average year-over-year growth rate"
            )
        
        with col3:
            best_year = trend_data.get("best_year", "N/A")
            st.metric(
                "Best Performance Year",
                str(best_year),
                help="Year with highest total contract value"
            )
        
        # Growth vs Decline Analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Growing Customers")
            growing = trend_data.get("growing_customers", [])
            if growing:
                growing_df = pd.DataFrame(growing, columns=["Customer", "Growth Value"])
                growing_df["Growth Value"] = growing_df["Growth Value"].apply(
                    lambda x: f"${x:,.0f}"
                )
                st.dataframe(growing_df, use_container_width=True, hide_index=True)
            else:
                st.info("No customers with positive growth trends found")
        
        with col2:
            st.markdown("#### Declining Customers")
            declining = trend_data.get("declining_customers", [])
            if declining:
                declining_df = pd.DataFrame(declining, columns=["Customer", "Decline Value"])
                declining_df["Decline Value"] = declining_df["Decline Value"].apply(
                    lambda x: f"${x:,.0f}"
                )
                st.dataframe(declining_df, use_container_width=True, hide_index=True)
            else:
                st.info("No customers with declining trends found")
                
    def _render_customer_lifecycle_analysis(self):
        """Render customer lifecycle analysis"""
        st.subheader("Customer Lifecycle Analysis")
        
        if "trend_data" not in self.data or "customer_lifecycle" not in self.data["trend_data"]:
            st.info("No customer lifecycle data available")
            return
        
        lifecycle_df = self.data["trend_data"]["customer_lifecycle"]
        
        if lifecycle_df.empty:
            st.info("No lifecycle data to display")
            return
        
        # Customer segmentation
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Customer Segments by Activity")
            
            # Segment customers by years active
            lifecycle_df["Segment"] = lifecycle_df["years_active"].apply(
                lambda x: "New (1 year)" if x == 1 
                else "Growing (2-3 years)" if x <= 3
                else "Established (4-6 years)" if x <= 6
                else "Long-term (7+ years)"
            )
            
            segment_summary = lifecycle_df.groupby("Segment").agg({
                "total_value": ["sum", "mean", "count"]
            }).round(0)
            
            segment_summary.columns = ["Total Value", "Avg Value", "Customer Count"]
            segment_summary = segment_summary.reset_index()
            
            st.dataframe(
                segment_summary,
                use_container_width=True,
                column_config={
                    "Segment": "Customer Segment",
                    "Total Value": st.column_config.NumberColumn(
                        "Total Value",
                        format="$%.0f"
                    ),
                    "Avg Value": st.column_config.NumberColumn(
                        "Avg Value",
                        format="$%.0f"
                    ),
                    "Customer Count": "Customers"
                },
                hide_index=True
            )
        
        with col2:
            st.markdown("#### Value vs Years Active")
            
            # Simple scatter plot representation
            if len(lifecycle_df) > 0:
                scatter_data = lifecycle_df.reset_index()[["years_active", "total_value"]].head(20)
                st.scatter_chart(
                    data=scatter_data,
                    x="years_active",
                    y="total_value"
                )
            else:
                st.info("No data available for scatter plot")
        
        # Detailed lifecycle table
        st.markdown("#### Customer Lifecycle Details")
        
        # Format the lifecycle data for display
        display_lifecycle = lifecycle_df.copy().reset_index()
        display_lifecycle = display_lifecycle.head(20)  # Limit to 20 rows for display
        
        st.dataframe(
            display_lifecycle,
            use_container_width=True,
            column_config={
                "c_name": "Customer",
                "years_active": "Years Active",
                "total_value": st.column_config.NumberColumn(
                    "Total Value",
                    format="$%.0f"
                ),
                "avg_annual_value": st.column_config.NumberColumn(
                    "Avg Annual Value",
                    format="$%.0f"
                ),
                "first_year": "First Year",
                "last_year": "Last Year"
            },
            hide_index=True
        )
    
    def _render_annual_performance_chart(self, aggregated_data, color_scheme):
        """Render annual performance chart with theme support"""
        st.markdown("#### Annual Performance (Chart)")
        
        if "by_year" not in aggregated_data:
            st.info("No yearly data for chart")
            return
        
        try:
            year_data = aggregated_data["by_year"].copy()
            
            # Create themed Altair line chart - FIXED COLOR DEFINITION
            chart = alt.Chart(year_data).mark_line(
                point=True,
                strokeWidth=3,
                opacity=0.8,
                color="#1f77b4"  # Simple fallback color
            ).encode(
                x=alt.X("contract_year:O", title="Year"),
                y=alt.Y("Total Value:Q", title="Total Contract Value", axis=alt.Axis(format="$,.0f")),
                # Apply color scheme through encoding instead of mark
                color=alt.value("#1f77b4"),  # Solid color for line chart
                tooltip=[
                    alt.Tooltip("contract_year:O", title="Year"),
                    alt.Tooltip("Total Value:Q", title="Total Value", format="$,.0f"),
                    alt.Tooltip("Contract Count:Q", title="Contracts"),
                    alt.Tooltip("Unique Customers:Q", title="Customers")
                ]
            ).properties(
                width=350,
                height=350,
                title="Annual Contract Performance"
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering annual chart: {str(e)}")
            # Fallback to simple chart
            try:
                chart_data = year_data.set_index("contract_year")["Total Value"]
                st.line_chart(chart_data, height=350)
            except:
                st.info("Chart data unavailable")
