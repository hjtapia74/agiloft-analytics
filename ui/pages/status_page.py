"""
Enhanced Contract Status Page for Agiloft CLM Analytics
Updated with 2x2 grid layout below the existing tabbed container
"""

import streamlit as st
import pandas as pd
import altair as alt
import logging
from typing import Dict, Any, List
from datetime import datetime

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
    logger.info("Enhanced components successfully imported")
except ImportError as e:
    ENHANCED_COMPONENTS_AVAILABLE = False
    logger.warning(f"Enhanced components not available: {e}")
    
    def enhanced_multiselect(label, options, default=None, key="", help_text=None, max_selections=None):
        # Handle session state properly - if default is None, use what's in session state
        if default is None and key and key in st.session_state:
            effective_default = st.session_state[key]
        else:
            effective_default = default
        return st.multiselect(label, options, default=effective_default, key=key, help=help_text, max_selections=max_selections)
    
    def create_enhanced_chart(data, chart_type, x_col, y_col, color_col=None, title=None):
        if chart_type == "line":
            return st.line_chart(data.set_index(x_col)[y_col])
        elif chart_type == "bar":
            return st.bar_chart(data.set_index(x_col)[y_col])
        else:
            return st.dataframe(data)
    
    def render_metrics_grid(metrics, columns=4):
        """Fallback metrics grid without currency formatting"""
        cols = st.columns(columns)
        for i, (name, data) in enumerate(metrics.items()):
            with cols[i % columns]:
                st.metric(name, data.get("value", 0), help=data.get("help"))


def enhanced_manager_selector(available_managers, key="manager_selector", default_count=20):
    """Simple enhanced manager selector with search and quick actions"""
    
    if not available_managers:
        st.warning("No contract managers found in database")
        return []
    
    # Initialize session state
    search_key = f"{key}_search"
    selection_key = f"{key}_selection"
    
    if selection_key not in st.session_state:
        # Smart default: Use top performers instead of alphabetical order
        if 'db_manager' in st.session_state:
            try:
                db_manager = st.session_state.db_manager
                top_performers = db_manager.get_top_managers_by_activity(limit=default_count)
                if top_performers:
                    default_managers = top_performers
                    st.info(f"Showing top {len(default_managers)} managers by contract value")
                else:
                    # Fallback to alphabetical if top performers query fails
                    default_managers = available_managers[:min(default_count, len(available_managers))]
                    st.warning("Using alphabetical order - could not retrieve top performers")
            except Exception as e:
                # Fallback to alphabetical if there's an error
                default_managers = available_managers[:min(default_count, len(available_managers))]
                st.warning(f"Using alphabetical order - error getting top performers: {e}")
        else:
            # Fallback when db_manager not available
            default_managers = available_managers[:min(default_count, len(available_managers))]
        
        st.session_state[selection_key] = default_managers
    
    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    
    # Quick action buttons BEFORE search - arranged in rows (one per row)
    st.markdown("**Quick Selection Actions:**")
    
    # Get access to database manager for top performer queries
    if 'db_manager' in st.session_state:
        db_manager = st.session_state.db_manager
        
        # Row 1: Top 10 by total contract value
        if st.button(
            "Top 10 Managers",
            key=f"{key}_top10",
            help="Select the 10 managers with highest total contract value",
            use_container_width=True
        ):
            try:
                top_10_managers = db_manager.get_top_managers_by_activity(limit=10)
                if top_10_managers:
                    st.session_state[selection_key] = top_10_managers
                    st.success(f"Selected top 10 managers by contract value")
                else:
                    st.warning("Could not retrieve top managers")
            except Exception as e:
                st.error(f"Error getting top 10 managers: {e}")
        
        # Row 2: Top 20 by total contract value  
        if st.button(
            f"Top {default_count} Managers",
            key=f"{key}_top_default",
            help=f"Select the {default_count} managers with highest total contract value",
            use_container_width=True
        ):
            try:
                top_managers = db_manager.get_top_managers_by_activity(limit=default_count)
                if top_managers:
                    st.session_state[selection_key] = top_managers
                    st.success(f"Selected top {default_count} managers by contract value")
                else:
                    st.warning("Could not retrieve top managers")
            except Exception as e:
                st.error(f"Error getting top {default_count} managers: {e}")
    else:
        # Fallback buttons when db_manager not available
        if st.button(
            f"First 10 Managers (Alphabetical)",
            key=f"{key}_top10",
            help="Select first 10 managers alphabetically (fallback mode)",
            use_container_width=True
        ):
            st.session_state[selection_key] = available_managers[:10]
            st.warning("Using alphabetical order - database connection not available for top performers")
        
        if st.button(
            f"First {default_count} Managers (Alphabetical)",
            key=f"{key}_top_default", 
            help=f"Select first {default_count} managers alphabetically (fallback mode)",
            use_container_width=True
        ):
            st.session_state[selection_key] = available_managers[:default_count]
            st.warning("Using alphabetical order - database connection not available for top performers")
    
    # Row 3: Select All
    if st.button(
        "All Contract Managers",
        key=f"{key}_all_managers",
        help="Select all available managers",
        use_container_width=True
    ):
        st.session_state[selection_key] = available_managers.copy()
        # Show confirmation without triggering rerun
        st.success(f"Selected all {len(available_managers)} managers")
    
    # Row 4: Clear All
    if st.button(
        "Clear Selections",
        key=f"{key}_clear",
        help="Clear all current selections",
        use_container_width=True
    ):
        st.session_state[selection_key] = []
        st.info("Cleared all selections")
    
    st.markdown("---")  # Visual separator
    
    # Search box
    search_term = st.text_input(
        "Search Contract Managers",
        value=st.session_state[search_key],
        placeholder="Type to search manager names...",
        key=f"{search_key}_input",
        help="Filter managers by name. Search is case-insensitive."
    )
    
    # Update search state
    if search_term != st.session_state[search_key]:
        st.session_state[search_key] = search_term
    
    # Filter managers based on search
    if search_term:
        filtered_managers = [
            manager for manager in available_managers 
            if search_term.lower() in manager.lower()
        ]
        # Sort by relevance
        filtered_managers.sort(key=lambda x: (
            0 if x.lower() == search_term.lower() else
            1 if x.lower().startswith(search_term.lower()) else
            2
        ))
    else:
        filtered_managers = available_managers
    
    # Additional quick actions for filtered results (if search is active)
    if search_term and filtered_managers:
        st.markdown("**Actions for Search Results:**")
        
        # Row 1: Select all search results
        if st.button(
            f"Select All {len(filtered_managers)} Search Results",
            key=f"{key}_all_filtered",
            help="Select all managers from current search results",
            use_container_width=True
        ):
            st.session_state[selection_key] = filtered_managers.copy()
            st.success(f"Selected {len(filtered_managers)} search results")
        
        # Row 2: Add search results to current selection
        if st.button(
            f"Add Search Results to Selection",
            key=f"{key}_add_filtered",
            help="Add search results to current selection",
            use_container_width=True
        ):
            current_selection = st.session_state.get(selection_key, [])
            # Add filtered managers that aren't already selected
            new_additions = 0
            for manager in filtered_managers:
                if manager not in current_selection:
                    current_selection.append(manager)
                    new_additions += 1
            st.session_state[selection_key] = current_selection
            if new_additions > 0:
                st.success(f"Added {new_additions} new managers to selection")
            else:
                st.info("All search results were already selected")
    
    # Show search results info
    if search_term:
        st.info(f"Found {len(filtered_managers)} managers matching '{search_term}'")
    
    # Selection summary and compact multiselect (no nested expanders)
    current_selection = st.session_state.get(selection_key, [])
    
    if current_selection:
        # Show compact summary without duplicate success message
        if len(current_selection) <= 3:
            # Show individual names if 3 or fewer
            summary_text = f"**Currently selected:** {', '.join(current_selection)}"
        else:
            # Show count and sample if more than 3
            sample_names = ', '.join(current_selection[:2])
            summary_text = f"**{len(current_selection)} managers selected**"
        
        st.markdown(summary_text)  # Use markdown instead of st.success to avoid duplication
        
        # Add a checkbox to show/hide the full selection for editing
        show_full_selection = st.checkbox(
            "Show full selection for editing",
            value=False,
            key=f"{key}_show_selection",
            help="Check this box to view and edit the complete manager selection"
        )
        
        if show_full_selection:
            # Use the filtered list for options, but maintain current selection
            display_options = filtered_managers
            
            # Ensure current selection is included in options
            for selected in current_selection:
                if selected not in display_options and selected in available_managers:
                    display_options.append(selected)
            
            selected_managers = st.multiselect(
                f"Edit Selection ({len(current_selection)} currently selected)",
                options=display_options,
                default=current_selection,
                key=f"{key}_multiselect",
                help="Modify your current manager selection"
            )
        else:
            # Don't show multiselect, just use current selection
            selected_managers = current_selection
    else:
        # No selection yet - show normal multiselect
        st.warning("No managers selected - please choose managers above or use the selection below")
        
        # Use the filtered list for options
        display_options = filtered_managers
        
        selected_managers = st.multiselect(
            "Select Contract Managers",
            options=display_options,
            default=[],
            key=f"{key}_multiselect",
            help="Choose which contract managers to include in your analysis"
        )
    
    # Update session state
    st.session_state[selection_key] = selected_managers
    
    # Single final selection summary (only show once at the end)
    if selected_managers:
        if len(selected_managers) == len(available_managers):
            st.info(f"All {len(available_managers)} managers selected")
        else:
            st.info(f"{len(selected_managers)} of {len(available_managers)} managers selected")
    
    return selected_managers


class StatusPage(FilteredPage):
    """Enhanced page for displaying contract data by status with 2x2 grid layout"""
    
    def __init__(self):
        super().__init__("Contract Value ($) by Status", "")
        self.transformer = DataTransformer()
        self.chart_helper = ChartHelper()
    
    def render_sidebar_filters(self) -> Dict[str, Any]:
        """Render enhanced sidebar filters for status page"""
        try:
            # Get available options from database
            available_managers = self.db_manager.get_available_contract_managers()
            available_statuses = self.db_manager.get_available_statuses()
            
            # Enhanced contract managers filter with search and quick actions
            with st.expander("Contract Managers", expanded=False):
                if available_managers:
                    selected_managers = enhanced_manager_selector(
                        available_managers=available_managers,
                        key="status_managers_enhanced",
                        default_count=20
                    )
                else:
                    st.warning("No contract managers found in database")
                    selected_managers = []
            
            # Contract Status filter (keep existing enhanced multiselect)
            with st.expander("Contract Status", expanded=False):
                if available_statuses:
                    available_status_options = available_statuses
                else:
                    available_status_options = ["Approved", "Pending Approval", "Pending Review", "Draft"]
                    st.warning("No contract statuses found, using defaults")
                
                # Initialize session state for statuses if not set
                status_key = "status_statuses"
                if status_key not in st.session_state:
                    st.session_state[status_key] = available_status_options.copy()  # Start with all selected
                
                selected_statuses = enhanced_multiselect(
                    label="Select Contract Statuses",
                    options=available_status_options,
                    default=None,  # Don't use default parameter to avoid conflict
                    key=status_key,
                    help_text="Choose which contract statuses to analyze"
                )
            
            # Value Range filter with dynamic slider
            with st.expander("Value Range", expanded=False):
                st.subheader("Contract Value Range")
                
                # Get actual min/max values from database for realistic slider bounds
                try:
                    summary_stats = self.db_manager.get_contract_summary_stats()
                    if summary_stats:
                        db_min_value = float(summary_stats.get('min_value', 0))
                        db_max_value = float(summary_stats.get('max_value', 500000000))
                        db_avg_value = float(summary_stats.get('avg_value', 150000))
                        
                        # Round to nice numbers for better UX
                        slider_min = max(0, int(db_min_value))
                        slider_max = int(db_max_value * 1.1)  # Add 10% buffer
                        default_max = int(db_max_value)
                        
                        st.info(f"Database Range: \${db_min_value:,.0f} - \${db_max_value:,.0f} | Avg: \${db_avg_value:,.0f}")
                        
                    else:
                        # Fallback values if stats query fails
                        slider_min = 0
                        slider_max = 500000000
                        default_max = 500000000
                        db_avg_value = 150000
                        st.warning("Could not retrieve database statistics, using default range")
                        
                except Exception as e:
                    # Fallback values if there's an error
                    slider_min = 0
                    slider_max = 500000000
                    default_max = 500000000
                    db_avg_value = 150000
                    st.warning(f"Error getting database range: {e}")
                
                # Handle preset button clicks BEFORE creating the slider
                slider_key = "amount_range_slider_status"
                
                # Initialize session state if it doesn't exist
                if slider_key not in st.session_state:
                    st.session_state[slider_key] = (slider_min, default_max)
                
                # Quick Range Presets BEFORE the slider
                st.markdown("**Quick Range Presets:**")
                
                # Row 1: Low Value
                if st.button("Low Value (Bottom 25% of contracts)", key="preset_low", help="Select contracts in the lower value range", use_container_width=True):
                    preset_max = int(db_avg_value * 0.5)
                    st.session_state[slider_key] = (slider_min, min(preset_max, slider_max))
                
                # Row 2: Medium Value
                if st.button("Medium Value (Around average value)", key="preset_medium", help="Select contracts around the average value range", use_container_width=True):
                    preset_min = int(db_avg_value * 0.5)
                    preset_max = int(db_avg_value * 1.5)
                    st.session_state[slider_key] = (preset_min, min(preset_max, slider_max))
                
                # Row 3: High Value
                if st.button("High Value (Top 25% of contracts)", key="preset_high", help="Select contracts in the higher value range", use_container_width=True):
                    preset_min = int(db_avg_value * 2)
                    st.session_state[slider_key] = (preset_min, slider_max)
                
                # Row 4: All Values
                if st.button("All Values (Include all contract values)", key="preset_all", help="Reset to include the full value range", use_container_width=True):
                    st.session_state[slider_key] = (slider_min, slider_max)
                
                st.markdown("---")  # Visual separator
                
                # Now create the slider - it will automatically use the session state value
                amount_range = st.slider(
                    "Select Contract Value Range",
                    min_value=slider_min,
                    max_value=slider_max,
                    step=1000,  # $1K increments
                    format="$%d",
                    key=slider_key,  # This automatically handles session state
                    help=f"Filter contracts by value range. Database contains values from ${slider_min:,.0f} to ${slider_max:,.0f}"
                )
                
                min_amount, max_amount = amount_range
                
                # Show range summary with better formatting
                range_percentage = ((max_amount - min_amount) / (slider_max - slider_min)) * 100 if slider_max > slider_min else 100
                st.success(f"Selected Range: \${min_amount:,.0f} - \${max_amount:,.0f} ({range_percentage:.1f}% of total range)")
            
            
            return {
                "selected_managers": selected_managers,
                "selected_statuses": selected_statuses,
                "amount_range": (min_amount, max_amount)
            }
            
        except Exception as e:
            logger.error(f"Error rendering status sidebar filters: {str(e)}")
            self.render_error("Error loading filter options")
            return {}
    
    def _render_visualization_settings(self):
        """Override to provide status page specific visualization options"""
        show_summary = st.checkbox(
            "Show Summary Statistics",
            value=True,
            help="Display key metrics at the top of the page",
            key="status_show_summary"
        )
        
        chart_type = st.radio(
            "Chart Type",
            ["Line Chart", "Bar Chart", "Area Chart"],
            index=1,  # Default to Bar Chart
            horizontal=True,
            help="Select your preferred visualization style",
            key="status_chart_type"
        )
        
        # Color scheme selection
        color_scheme = st.selectbox(
            "Color Scheme",
            ["category10", "viridis", "plasma", "blues", "greens"],
            index=1,
            help="Choose color palette for charts",
            key="status_color_scheme"
        )
        
        # Update filters with visualization settings
        if hasattr(self, 'filters'):
            self.filters.update({
                "show_summary": show_summary,
                "chart_type": chart_type,
                "color_scheme": color_scheme
            })
    
    def validate_filters(self, filters: Dict[str, Any]) -> bool:
        """Enhanced filter validation with helpful messages"""
        if not filters:
            return False
        
        if not filters.get("selected_managers"):
            self.render_warning("Please select at least one contract manager")
            st.info("**Tip**: Use the 'Top 20' quick action button to get started")
            return False
        
        if not filters.get("selected_statuses"):
            self.render_warning("Please select at least one contract status")
            return False
        
        amount_range = filters.get("amount_range")
        if amount_range and amount_range[0] >= amount_range[1]:
            self.render_warning("Invalid amount range: minimum must be less than maximum")
            return False
        
        return True
    
    def process_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced data processing with better error handling"""
        try:
            logger.info(f"Processing status data with {len(filters.get('selected_managers', []))} managers")
            
            # Get raw data from database - now returns individual contract records
            raw_data = self.db_manager.get_contract_status_data(
                contract_managers=filters["selected_managers"],
                status_filter=None  # Don't filter in SQL - do it here for flexibility
            )
            
            logger.info(f"Raw data shape: {raw_data.shape if not raw_data.empty else 'Empty'}")
            
            if raw_data.empty:
                logger.warning("No raw data returned from database")
                return {}
            
            # Debug: Show data before filtering
            logger.info(f"Raw data amount range: ${raw_data['co_amount'].min():,.0f} - ${raw_data['co_amount'].max():,.0f}")
            logger.info(f"Total individual contract records: {len(raw_data)}")
            
            # Filter by amount range FIRST (this is now the key fix)
            min_amount, max_amount = filters["amount_range"]
            logger.info(f"Applying amount filter: ${min_amount:,.0f} - ${max_amount:,.0f}")
            
            amount_filtered_data = raw_data[
                (raw_data["co_amount"] >= min_amount) & 
                (raw_data["co_amount"] <= max_amount)
            ]
            logger.info(f"After amount filter: {len(amount_filtered_data)} records (was {len(raw_data)} records)")
            
            if amount_filtered_data.empty:
                logger.warning("No data after amount filtering")
                # Enhanced debug info about what's available
                amount_ranges = {
                    "total_contracts": len(raw_data),
                    "amount_range_requested": f"${min_amount:,.0f} - ${max_amount:,.0f}",
                    "actual_amount_range": f"${raw_data['co_amount'].min():,.0f} - ${raw_data['co_amount'].max():,.0f}",
                    "sample_amounts": raw_data['co_amount'].describe().to_dict(),
                    "amount_distribution": {
                        "under_50k": len(raw_data[raw_data['co_amount'] < 50000]),
                        "50k_to_150k": len(raw_data[(raw_data['co_amount'] >= 50000) & (raw_data['co_amount'] <= 150000)]),
                        "over_150k": len(raw_data[raw_data['co_amount'] > 150000])
                    }
                }
                logger.info(f"Amount filtering debug: {amount_ranges}")
                
                return {
                    "debug_info": {
                        "raw_count": len(raw_data),
                        "available_statuses": sorted(raw_data['co_status'].unique()) if not raw_data.empty else [],
                        "selected_statuses": filters["selected_statuses"],
                        "amount_range_applied": f"${min_amount:,.0f} - ${max_amount:,.0f}",
                        "actual_amount_range": f"${raw_data['co_amount'].min():,.0f} - ${raw_data['co_amount'].max():,.0f}" if not raw_data.empty else "No data",
                        "selected_managers_count": len(filters.get("selected_managers", [])),
                        "manager_sample": filters.get("selected_managers", [])[:5],
                        "amount_debug": amount_ranges
                    }
                }
            
            # Then filter by status
            selected_statuses = filters["selected_statuses"]
            if selected_statuses:
                filtered_data = amount_filtered_data[amount_filtered_data["co_status"].isin(selected_statuses)]
                logger.info(f"After status filter ({len(selected_statuses)} statuses): {len(filtered_data)} records")
            else:
                filtered_data = amount_filtered_data
            
            if filtered_data.empty:
                logger.warning("No data after status filtering")
                return {
                    "debug_info": {
                        "raw_count": len(raw_data),
                        "after_amount_filter": len(amount_filtered_data),
                        "available_statuses": sorted(amount_filtered_data['co_status'].unique()) if not amount_filtered_data.empty else [],
                        "selected_statuses": selected_statuses,
                        "amount_range_applied": f"${min_amount:,.0f} - ${max_amount:,.0f}",
                        "selected_managers_count": len(filters.get("selected_managers", [])),
                        "manager_sample": filters.get("selected_managers", [])[:5]
                    }
                }
            
            # NOW aggregate the filtered individual records for display
            # This is the key change - we aggregate AFTER filtering, not before
            aggregated_data = filtered_data.groupby(['co_contractmanager', 'co_status'])['co_amount'].sum().reset_index()
            logger.info(f"After aggregation: {len(aggregated_data)} manager+status combinations")
            
            # Create pivot table from the aggregated data
            pivot_data = aggregated_data.pivot_table(
                index="co_contractmanager",
                columns="co_status", 
                values="co_amount",
                aggfunc="sum",
                fill_value=0
            )
            
            # Convert all numeric data to float to avoid decimal type issues with Altair
            pivot_data = pivot_data.astype(float)
            
            logger.info(f"Pivot data shape: {pivot_data.shape}")
            logger.info(f"Pivot data total value: ${pivot_data.sum().sum():,.0f}")
            
            # Prepare chart data
            chart_data = pd.melt(
                pivot_data.reset_index(), 
                id_vars="co_contractmanager", 
                var_name="co_status", 
                value_name="amount"
            )
            
            # Ensure amount is float type for charts
            chart_data['amount'] = pd.to_numeric(chart_data['amount'], errors='coerce').fillna(0).astype(float)
            
            # Calculate enhanced summary statistics
            summary_stats = self._calculate_enhanced_summary_stats(filtered_data, filters)
            
            # Create enhanced chart
            enhanced_chart = self._create_status_chart(chart_data, filters)
            
            return {
                "raw_data": raw_data,
                "filtered_data": filtered_data,
                "aggregated_data": aggregated_data,
                "pivot_data": pivot_data,
                "chart_data": chart_data,
                "summary_stats": summary_stats,
                "enhanced_chart": enhanced_chart,
                "sql_query": f"""
                -- Individual contract records query (new approach)
                SELECT co_contractmanager, co_status, co_amount
                FROM contract 
                WHERE co_contractmanager IN ({', '.join([f"'{m}'" for m in filters['selected_managers']])})
                    AND co_amount IS NOT NULL AND co_amount > 0
                -- Then filtered in Python by amount range: ${min_amount:,.0f} - ${max_amount:,.0f}
                -- Then aggregated by manager+status
                """,
                "filter_summary": {
                    "managers_selected": len(filters.get("selected_managers", [])),
                    "statuses_selected": len(filters.get("selected_statuses", [])),
                    "amount_range": filters.get("amount_range", (0, 0)),
                    "total_individual_records": len(raw_data),
                    "records_after_amount_filter": len(amount_filtered_data),
                    "records_after_status_filter": len(filtered_data),
                    "final_aggregated_combinations": len(aggregated_data) if 'aggregated_data' in locals() else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing status data: {str(e)}")
            raise DataProcessingError(f"Failed to process status data: {str(e)}")
    
    def _calculate_enhanced_summary_stats(self, data: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced summary statistics with metrics for the grid"""
        try:
            total_contracts = len(data)
            total_value = data["co_amount"].sum()
            avg_value = data["co_amount"].mean()
            max_value = data["co_amount"].max()
            min_value = data["co_amount"].min()
            
            unique_managers = data["co_contractmanager"].nunique()
            unique_statuses = data["co_status"].nunique()
            
            # Calculate additional insights
            top_manager = data.groupby("co_contractmanager")["co_amount"].sum().idxmax()
            top_manager_value = data.groupby("co_contractmanager")["co_amount"].sum().max()
            
            most_common_status = data["co_status"].mode().iloc[0] if not data["co_status"].mode().empty else "N/A"
            
            return {
                "total_contracts": total_contracts,
                "total_value": total_value,
                "avg_value": avg_value,
                "max_value": max_value,
                "min_value": min_value,
                "unique_managers": unique_managers,
                "unique_statuses": unique_statuses,
                "top_manager": top_manager,
                "top_manager_value": top_manager_value,
                "most_common_status": most_common_status
            }
        except Exception as e:
            logger.error(f"Error calculating summary stats: {str(e)}")
            return {}
    
    def _create_status_chart(self, chart_data: pd.DataFrame, filters: Dict[str, Any]):
        """Create enhanced status chart based on selected type"""
        if chart_data.empty:
            return None
        
        chart_type_map = {
            "Line Chart": "line",
            "Bar Chart": "bar", 
            "Area Chart": "area"
        }
        
        chart_type = chart_type_map.get(filters.get("chart_type", "Bar Chart"), "bar")
        color_scheme = filters.get("color_scheme", "category10")
        
        if ENHANCED_COMPONENTS_AVAILABLE:
            return create_enhanced_chart(
                data=chart_data,
                chart_type=chart_type,
                x_col="co_contractmanager",
                y_col="amount",
                color_col="co_status",
                title=f"Contract Value by Manager and Status ({filters.get('chart_type', 'Bar Chart')})",
                color_scheme=color_scheme
            )
        else:
            return chart_data
    
    def render_metrics(self, data: Dict[str, Any]):
        """Render enhanced metrics using the new grid system"""
        if not self.filters.get("show_summary") or not data.get("summary_stats"):
            return
        
        stats = data["summary_stats"]
        
        st.subheader("Contract Status Overview")
        
        # Create metrics dictionary for the enhanced grid
        metrics = {
            "Total Contracts": {
                "value": stats["total_contracts"],
                "format": "number",
                "help": "Total number of contracts matching your filters"
            },
            "Total Value": {
                "value": stats["total_value"],
                "format": "currency",
                "help": "Sum of all contract values"
            },
            "Selected Managers": {
                "value": stats["unique_managers"], 
                "format": "number",
                "help": "Number of contract managers in your selection"
            },
            "Active Statuses": {
                "value": stats["unique_statuses"],
                "format": "number",
                "help": "Number of different contract statuses found"
            }
        }
        
        # Render metrics grid - with explicit formatting
        logger.info(f"Rendering metrics with ENHANCED_COMPONENTS_AVAILABLE: {ENHANCED_COMPONENTS_AVAILABLE}")
        logger.info(f"Total value before formatting: {stats['total_value']}")
        
        if ENHANCED_COMPONENTS_AVAILABLE:
            # Use the imported enhanced function
            from ui.components import render_metrics_grid
            logger.info("Using enhanced render_metrics_grid from components")
            render_metrics_grid(metrics, columns=4)
        else:
            # Use fallback with manual formatting
            logger.info("Using fallback metrics rendering")
            cols = st.columns(4)
            
            with cols[0]:
                st.metric("Total Contracts", f"{stats['total_contracts']:,}", help="Total number of contracts matching your filters")
            with cols[1]: 
                # Manual currency formatting
                value = stats["total_value"]
                if value >= 1_000_000_000:
                    formatted_value = f"${value/1_000_000_000:.1f}B"
                elif value >= 1_000_000:
                    millions = value / 1_000_000
                    if millions >= 1000:
                        formatted_value = f"${millions:,.0f}M"
                    else:
                        formatted_value = f"${millions:.1f}M"
                else:
                    formatted_value = f"${value:,.0f}"
                st.metric("Total Value", formatted_value, help="Sum of all contract values")
            with cols[2]:
                st.metric("Selected Managers", f"{stats['unique_managers']:,}", help="Number of contract managers in your selection")
            with cols[3]:
                st.metric("Active Statuses", f"{stats['unique_statuses']:,}", help="Number of different contract statuses found")
        
        # Additional insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **Top Performing Manager**  
            **{stats['top_manager']}**  
            Total Value: {self.chart_helper.format_number(stats['top_manager_value'])}
            """)
        
        with col2:
            st.info(f"""
            **Most Common Status**  
            **{stats['most_common_status']}**  
            Found across {stats['unique_statuses']} status types
            """)
    
    def _render_main_analysis(self):
        """Override main analysis rendering with tabbed container + 2x2 grid"""
        if ENHANCED_COMPONENTS_AVAILABLE:
            # Create the main analysis container using our tabbed system (KEEP THIS)
            container = self.create_data_container("status_analysis")
            
            # Show filter summary in description
            filter_summary = self.data.get("filter_summary", {})
            managers_count = filter_summary.get("managers_selected", 0)
            statuses_count = filter_summary.get("statuses_selected", 0)
            amount_range = filter_summary.get("amount_range", (0, 0))
            
            # Prepare description for this analysis
            description = f"""
            ## Contract Status Analysis
            
            This analysis shows contract values broken down by **contract manager** and **status**. 
            
            **Key Insights:**
            - Compare performance across different contract managers
            - Identify bottlenecks in contract approval processes  
            - Track contract values by status categories
            - Monitor manager workload distribution
            
            **Current Analysis Scope:**
            - **Contract Managers**: {managers_count} selected (with enhanced search & quick actions)
            - **Contract Statuses**: {statuses_count} selected
            - **Value Range**: \${amount_range[0]:,.0f} - \${amount_range[1]:,.0f}
            
            **Enhanced Manager Selection Features:**
            - **Smart Search**: Find managers instantly by typing
            - **Quick Actions**: Top 10, Top 20, All Filtered, Clear All
            - **Visual Feedback**: Clear selection summary
            - **No Page Refresh**: Smooth selection experience
            """
            
            # Render the enhanced container with all tabs (KEEP THIS)
            container.render(
                dataframe=self.data.get("pivot_data", pd.DataFrame()),
                chart_data=self.data.get("enhanced_chart"),
                sql_query=self.data.get("sql_query"),
                description=description,
                export_filename="contract_status_analysis"
            )
        else:
            # Fallback to basic display
            st.subheader("Status Analysis")
            if "pivot_data" in self.data:
                st.dataframe(self.data["pivot_data"], use_container_width=True)
        
        # ADD NEW 2x2 GRID SECTION BELOW THE TABBED CONTAINER
        if not self.data.get("pivot_data", pd.DataFrame()).empty:
            st.markdown("---")
            st.subheader("Additional Analysis")
            
            # Add custom CSS for consistent cell heights
            st.markdown("""
            <style>
            .grid-cell-status {
                height: 400px;
                overflow-y: auto;
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # ROW 1: Manager Performance Summary | Status Distribution (Table)
            col1, col2 = st.columns([1, 1])
            
            with col1:
                self._render_manager_performance_summary()
            
            with col2:
                self._render_status_distribution_table()
            
            # ROW 2: Status Distribution (Bar Chart) | Status Distribution (Pie Chart)
            col1, col2 = st.columns([1, 1])
            
            with col1:
                self._render_status_distribution_bar_chart()
            
            with col2:
                self._render_status_distribution_pie_chart()
    
    def _render_manager_performance_summary(self):
        """Render manager performance summary table"""
        st.markdown("#### Manager Performance Summary")
        
        if "pivot_data" not in self.data or self.data["pivot_data"].empty:
            st.info("No manager performance data available")
            return
        
        pivot_df = self.data["pivot_data"]
        
        # Calculate manager totals and create ranking
        manager_totals = pivot_df.sum(axis=1).sort_values(ascending=False)
        
        # Create a summary dataframe
        summary_data = []
        for manager, total in manager_totals.head(15).items():  # Limit to top 15 for better display
            # Find the top status for this manager
            manager_row = pivot_df.loc[manager]
            top_status = manager_row.idxmax()
            top_status_value = manager_row.max()
            
            summary_data.append({
                "Manager": manager,
                "Total Value": total,
                "Top Status": top_status,
                "Top Status Value": top_status_value,
                "Status Count": (manager_row > 0).sum()
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        st.dataframe(
            summary_df,
            use_container_width=True,
            height=350,
            column_config={
                "Manager": "Contract Manager",
                "Total Value": st.column_config.NumberColumn(
                    "Total Value",
                    format="$%.0f"
                ),
                "Top Status": "Primary Status",
                "Top Status Value": st.column_config.NumberColumn(
                    "Primary Status Value", 
                    format="$%.0f"
                ),
                "Status Count": "Active Statuses"
            },
            hide_index=True
        )
    
    def _render_status_distribution_table(self):
        """Render status distribution table"""
        st.markdown("#### Status Distribution")
        
        if "pivot_data" not in self.data or self.data["pivot_data"].empty:
            st.info("No status distribution data available")
            return
        
        pivot_df = self.data["pivot_data"]
        
        # Calculate status totals and convert to float to avoid decimal type issues
        status_totals = pivot_df.sum().sort_values(ascending=False)
        status_totals = status_totals.astype(float)
        
        if len(status_totals) == 0:
            st.warning("No status data found")
            return
        
        # Create dataframe for status distribution
        status_df = status_totals.reset_index()
        status_df.columns = ["Status", "Total Value"]
        status_df["Total Value"] = status_df["Total Value"].astype(float)
        
        # Calculate percentages
        if status_df["Total Value"].sum() > 0:
            status_df["Percentage"] = (status_df["Total Value"] / status_df["Total Value"].sum()) * 100
        else:
            status_df["Percentage"] = 0
        
        status_df["Percentage"] = status_df["Percentage"].astype(float)
        
        # Add manager count per status
        manager_counts = []
        for status in status_df["Status"]:
            if status in pivot_df.columns:
                count = (pivot_df[status] > 0).sum()
                manager_counts.append(count)
            else:
                manager_counts.append(0)
        
        status_df["Manager Count"] = manager_counts
        
        st.dataframe(
            status_df,
            use_container_width=True,
            height=350,
            column_config={
                "Status": "Contract Status",
                "Total Value": st.column_config.NumberColumn(
                    "Total Value",
                    format="$%.0f"
                ),
                "Percentage": st.column_config.NumberColumn(
                    "Percentage",
                    format="%.1f%%"
                ),
                "Manager Count": "Managers"
            },
            hide_index=True
        )
    
    def _render_status_distribution_bar_chart(self):
        """Render status distribution bar chart with theme colors"""
        st.markdown("#### Status Distribution (Bar Chart)")
        
        if "pivot_data" not in self.data or self.data["pivot_data"].empty:
            st.info("No data available for bar chart")
            return
        
        pivot_df = self.data["pivot_data"]
        
        try:
            # Calculate status totals
            status_totals = pivot_df.sum().sort_values(ascending=False)
            status_totals = status_totals.astype(float)
            
            if len(status_totals) == 0:
                st.warning("No status data for chart")
                return
            
            # Create dataframe for Altair chart to use theme colors
            bar_data = status_totals.reset_index()
            bar_data.columns = ["Status", "Total Value"]
            bar_data["Total Value"] = bar_data["Total Value"].astype(float)
            
            # Get the selected color scheme from filters
            color_scheme = self.filters.get("color_scheme", "category10")
            
            # Create themed bar chart with Altair
            bar_chart = alt.Chart(bar_data).mark_bar().encode(
                x=alt.X("Status:N", title="Contract Status", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("Total Value:Q", title="Total Value", axis=alt.Axis(format="$,.0f")),
                color=alt.Color(
                    "Status:N",
                    scale=alt.Scale(scheme=color_scheme),
                    legend=None  # Hide legend since x-axis already shows status names
                ),
                tooltip=[
                    alt.Tooltip("Status:N", title="Status"),
                    alt.Tooltip("Total Value:Q", title="Total Value", format="$,.0f")
                ]
            ).properties(
                width=350,
                height=350,
                title="Status Distribution by Value"
            )
            
            st.altair_chart(bar_chart, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering themed bar chart: {str(e)}")
            # Fallback to simple streamlit bar chart
            try:
                status_totals = pivot_df.sum().sort_values(ascending=False)
                st.bar_chart(status_totals, height=350)
            except:
                # Final fallback to metric display
                for status, value in status_totals.head(5).items():
                    st.metric(label=status, value=f"${value:,.0f}")
    
    def _render_status_distribution_pie_chart(self):
        """Render status distribution pie chart"""
        st.markdown("#### Status Distribution (Pie Chart)")
        
        if "pivot_data" not in self.data or self.data["pivot_data"].empty:
            st.info("No data available for pie chart")
            return
        
        pivot_df = self.data["pivot_data"]
        
        try:
            # Calculate status totals
            status_totals = pivot_df.sum().sort_values(ascending=False)
            status_totals = status_totals.astype(float)
            
            if len(status_totals) == 0:
                st.warning("No status data for pie chart")
                return
            
            # Create dataframe for pie chart
            pie_data = status_totals.reset_index()
            pie_data.columns = ["Status", "Total Value"]
            pie_data["Total Value"] = pie_data["Total Value"].astype(float)
            
            # Calculate percentages for tooltip
            total_value = pie_data["Total Value"].sum()
            if total_value > 0:
                pie_data["Percentage"] = (pie_data["Total Value"] / total_value) * 100
            else:
                pie_data["Percentage"] = 0
            
            # Get the selected color scheme from filters
            color_scheme = self.filters.get("color_scheme", "category10")
            
            # Create pie chart with Altair
            pie_chart = alt.Chart(pie_data).mark_arc().encode(
                theta=alt.Theta("Total Value:Q"),
                color=alt.Color(
                    "Status:N",
                    scale=alt.Scale(scheme=color_scheme),
                    legend=alt.Legend(title="Contract Status")
                ),
                tooltip=[
                    alt.Tooltip("Status:N", title="Status"),
                    alt.Tooltip("Total Value:Q", title="Total Value", format="$,.0f"),
                    alt.Tooltip("Percentage:Q", title="Percentage", format=".1f")
                ]
            ).properties(
                width=350,
                height=350,
                title="Status Value Distribution"
            )
            
            st.altair_chart(pie_chart, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering pie chart: {str(e)}")
            # Fallback to simple metric display
            status_totals = pivot_df.sum().sort_values(ascending=False)
            for status, value in status_totals.head(5).items():
                percentage = (value / status_totals.sum()) * 100 if status_totals.sum() > 0 else 0
                st.metric(
                    label=status,
                    value=f"${value:,.0f}",
                    delta=f"{percentage:.1f}%"
                )
    
    # Keep existing methods for compatibility but mark as deprecated
    def render_data_tables(self, data: Dict[str, Any]):
        """Deprecated: Now handled by tabbed container and grid layout"""
        pass
    
    def render_visualizations(self, data: Dict[str, Any]):
        """Deprecated: Now handled by tabbed container and grid layout"""  
        pass
    
    def handle_export(self, data: Dict[str, Any]):
        """Deprecated: Now handled by tabbed container"""
        pass