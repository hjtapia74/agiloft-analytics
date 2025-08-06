"""
Enhanced Contract Manager Filter Component
Implements search-first multiselect with smart defaults and quick actions
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class EnhancedManagerFilter:
    """Enhanced contract manager filter with search and smart defaults"""
    
    def __init__(self, key: str = "manager_filter"):
        self.key = key
        self.search_key = f"{key}_search"
        self.selection_key = f"{key}_selection"
        self.apply_key = f"{key}_apply"
    
    def render(
        self, 
        available_managers: List[str],
        db_manager,
        default_count: int = 20,
        help_text: Optional[str] = None
    ) -> List[str]:
        """
        Render the enhanced manager filter component
        
        Args:
            available_managers: List of all available manager names
            db_manager: Database manager for fetching manager statistics
            default_count: Number of managers to select by default
            help_text: Optional help text for the filter
            
        Returns:
            List of selected manager names
        """
        
        if not available_managers:
            st.warning("No contract managers found in database")
            return []
        
        # Get manager statistics for smart defaults
        manager_stats = self._get_manager_statistics(available_managers, db_manager)
        
        # Initialize session state
        if self.selection_key not in st.session_state:
            # Smart default: top N most active managers
            default_managers = self._get_smart_defaults(manager_stats, default_count)
            st.session_state[self.selection_key] = default_managers
        
        if self.search_key not in st.session_state:
            st.session_state[self.search_key] = ""
        
        # Create the filter UI
        st.markdown("###Contract Managers")
        
        # Search box
        search_term = st.text_input(
            "Search Managers",
            value=st.session_state[self.search_key],
            placeholder="Type to search manager names...",
            key=f"{self.search_key}_input",
            help="Filter managers by name. Search is case-insensitive."
        )
        
        # Update search state
        if search_term != st.session_state[self.search_key]:
            st.session_state[self.search_key] = search_term
        
        # Filter managers based on search
        filtered_managers = self._filter_managers(available_managers, search_term, manager_stats)
        
        # Quick action buttons
        self._render_quick_actions(filtered_managers, manager_stats, default_count)
        
        # Selection interface
        selected_managers = self._render_selection_interface(filtered_managers, manager_stats)
        
        # Selection summary
        self._render_selection_summary(selected_managers, manager_stats)
        
        # Apply button (optional - can be used to batch apply changes)
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button(
                "Refresh Analysis", 
                key=self.apply_key,
                help="Apply current manager selection and refresh the analysis",
                type="primary"
            ):
                st.rerun()
        
        return selected_managers
    
    def _get_manager_statistics(self, managers: List[str], db_manager) -> Dict[str, Dict]:
        """Get statistics for each manager to enable smart defaults"""
        try:
            # Get manager statistics from database
            manager_stats = {}
            
            # This would be a single query to get all manager stats efficiently
            # For now, we'll create a simplified version
            for manager in managers:
                # In a real implementation, this would be a single query for all managers
                # manager_data = db_manager.get_manager_stats(manager)
                
                # Simplified stats - in reality, get from database
                manager_stats[manager] = {
                    'total_contracts': len(manager) * 10,  # Placeholder
                    'total_value': len(manager) * 1000000,  # Placeholder
                    'recent_activity': True,  # Placeholder
                    'last_contract_date': '2024-01-01'  # Placeholder
                }
            
            return manager_stats
            
        except Exception as e:
            logger.error(f"Error getting manager statistics: {e}")
            # Return basic stats if database query fails
            return {manager: {'total_contracts': 1, 'total_value': 100000, 'recent_activity': True} 
                   for manager in managers}
    
    def _get_smart_defaults(self, manager_stats: Dict[str, Dict], count: int) -> List[str]:
        """Get smart default selection based on manager activity"""
        try:
            # Sort managers by total contract value (primary) and contract count (secondary)
            sorted_managers = sorted(
                manager_stats.items(),
                key=lambda x: (
                    x[1].get('total_value', 0),
                    x[1].get('total_contracts', 0),
                    1 if x[1].get('recent_activity', False) else 0  # Recent activity bonus
                ),
                reverse=True
            )
            
            # Return top N managers
            return [manager for manager, _ in sorted_managers[:count]]
            
        except Exception as e:
            logger.error(f"Error creating smart defaults: {e}")
            # Fallback to first N managers
            return list(manager_stats.keys())[:count]
    
    def _filter_managers(self, managers: List[str], search_term: str, manager_stats: Dict) -> List[str]:
        """Filter managers based on search term"""
        if not search_term:
            return managers
        
        search_lower = search_term.lower()
        
        # Filter by name match
        filtered = [
            manager for manager in managers 
            if search_lower in manager.lower()
        ]
        
        # Sort filtered results by relevance (exact match first, then by activity)
        def sort_key(manager):
            name_lower = manager.lower()
            stats = manager_stats.get(manager, {})
            
            # Exact match gets highest priority
            if name_lower == search_lower:
                return (0, -stats.get('total_value', 0))
            # Starts with search term gets second priority
            elif name_lower.startswith(search_lower):
                return (1, -stats.get('total_value', 0))
            # Contains search term, sorted by activity
            else:
                return (2, -stats.get('total_value', 0))
        
        return sorted(filtered, key=sort_key)
    
    def _render_quick_actions(self, filtered_managers: List[str], manager_stats: Dict, default_count: int):
        """Render quick action buttons"""
        st.markdown("#### Quick Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button(
                f"Top {min(10, len(filtered_managers))}",
                key=f"{self.key}_top10",
                help="Select top 10 most active managers from current list",
                use_container_width=True
            ):
                top_managers = self._get_top_managers(filtered_managers, manager_stats, 10)
                st.session_state[self.selection_key] = top_managers
                st.rerun()
        
        with col2:
            if st.button(
                f"Top {min(default_count, len(filtered_managers))}",
                key=f"{self.key}_top_default",
                help=f"Select top {default_count} most active managers",
                use_container_width=True
            ):
                top_managers = self._get_top_managers(filtered_managers, manager_stats, default_count)
                st.session_state[self.selection_key] = top_managers
                st.rerun()
        
        with col3:
            if st.button(
                "All Filtered",
                key=f"{self.key}_all_filtered",
                help="Select all managers from current filtered list",
                use_container_width=True
            ):
                st.session_state[self.selection_key] = filtered_managers.copy()
                st.rerun()
        
        with col4:
            if st.button(
                "Clear All",
                key=f"{self.key}_clear",
                help="Clear all selections",
                use_container_width=True
            ):
                st.session_state[self.selection_key] = []
                st.rerun()
    
    def _get_top_managers(self, managers: List[str], manager_stats: Dict, count: int) -> List[str]:
        """Get top N managers by activity from the provided list"""
        sorted_managers = sorted(
            managers,
            key=lambda x: manager_stats.get(x, {}).get('total_value', 0),
            reverse=True
        )
        return sorted_managers[:count]
    
    def _render_selection_interface(self, filtered_managers: List[str], manager_stats: Dict) -> List[str]:
        """Render the main selection interface"""
        if not filtered_managers:
            st.warning("No managers match your search criteria")
            return st.session_state.get(self.selection_key, [])
        
        current_selection = st.session_state.get(self.selection_key, [])
        
        st.markdown(f"#### Select from {len(filtered_managers)} managers")
        
        # Show managers in a grid with checkboxes
        # Limit display to first 50 for performance
        display_managers = filtered_managers[:50]
        
        if len(filtered_managers) > 50:
            st.info(f"Showing first 50 of {len(filtered_managers)} managers. Use search to narrow down results.")
        
        # Create checkbox grid (3 columns for better layout)
        cols_per_row = 3
        rows = (len(display_managers) + cols_per_row - 1) // cols_per_row
        
        updated_selection = current_selection.copy()
        
        for row in range(rows):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                manager_idx = row * cols_per_row + col_idx
                if manager_idx < len(display_managers):
                    manager = display_managers[manager_idx]
                    stats = manager_stats.get(manager, {})
                    
                    # Create manager display with stats
                    contracts_count = stats.get('total_contracts', 0)
                    value = stats.get('total_value', 0)
                    
                    # Format value for display
                    if value >= 1_000_000:
                        value_str = f"${value/1_000_000:.1f}M"
                    elif value >= 1_000:
                        value_str = f"${value/1_000:.0f}K"
                    else:
                        value_str = f"${value:,.0f}"
                    
                    manager_label = f"{manager}\n{contracts_count} contracts | {value_str}"
                    
                    with cols[col_idx]:
                        is_selected = st.checkbox(
                            manager_label,
                            value=manager in current_selection,
                            key=f"{self.key}_checkbox_{manager}",
                            help=f"Manager: {manager}\nContracts: {contracts_count}\nTotal Value: {value_str}"
                        )
                        
                        # Update selection based on checkbox state
                        if is_selected and manager not in updated_selection:
                            updated_selection.append(manager)
                        elif not is_selected and manager in updated_selection:
                            updated_selection.remove(manager)
        
        # Update session state if selection changed
        if updated_selection != current_selection:
            st.session_state[self.selection_key] = updated_selection
        
        return updated_selection
    
    def _render_selection_summary(self, selected_managers: List[str], manager_stats: Dict):
        """Render selection summary with key metrics"""
        if not selected_managers:
            st.warning("No managers selected - analysis will be empty")
            return
        
        # Calculate summary statistics
        total_contracts = sum(manager_stats.get(m, {}).get('total_contracts', 0) for m in selected_managers)
        total_value = sum(manager_stats.get(m, {}).get('total_value', 0) for m in selected_managers)
        
        # Format total value
        if total_value >= 1_000_000:
            value_str = f"${total_value/1_000_000:.1f}M"
        elif total_value >= 1_000:
            value_str = f"${total_value/1_000:.0f}K"
        else:
            value_str = f"${total_value:,.0f}"
        
        # Display summary
        st.success(f"""
        **Selection Summary:**
        - **{len(selected_managers)}** managers selected
        - **~{total_contracts:,}** contracts estimated
        - **~{value_str}** total value estimated
        """)
        
        # Show selected managers in an expander for review
        if len(selected_managers) > 5:
            with st.expander(f"View all {len(selected_managers)} selected managers"):
                # Display in columns for better readability
                cols = st.columns(3)
                for i, manager in enumerate(sorted(selected_managers)):
                    with cols[i % 3]:
                        stats = manager_stats.get(manager, {})
                        contracts = stats.get('total_contracts', 0)
                        value = stats.get('total_value', 0)
                        
                        if value >= 1_000_000:
                            value_display = f"${value/1_000_000:.1f}M"
                        else:
                            value_display = f"${value/1_000:.0f}K"
                        
                        st.write(f"• **{manager}**")
                        st.caption(f"  {contracts} contracts | {value_display}")
        else:
            # Show all managers if 5 or fewer
            st.write("**Selected Managers:**")
            for manager in sorted(selected_managers):
                stats = manager_stats.get(manager, {})
                contracts = stats.get('total_contracts', 0)
                value = stats.get('total_value', 0)
                
                if value >= 1_000_000:
                    value_display = f"${value/1_000_000:.1f}M"
                else:
                    value_display = f"${value/1_000:.0f}K"
                
                st.write(f"• **{manager}** - {contracts} contracts | {value_display}")


def enhanced_manager_multiselect(
    label: str,
    available_managers: List[str],
    db_manager,
    default_count: int = 20,
    key: str = "manager_filter",
    help_text: Optional[str] = None
) -> List[str]:
    """
    Convenience function to render the enhanced manager filter
    
    Args:
        label: Label for the filter section
        available_managers: List of all available manager names
        db_manager: Database manager for fetching statistics
        default_count: Number of managers to select by default
        key: Unique key for the component
        help_text: Optional help text
        
    Returns:
        List of selected manager names
    """
    filter_component = EnhancedManagerFilter(key=key)
    return filter_component.render(
        available_managers=available_managers,
        db_manager=db_manager,
        default_count=default_count,
        help_text=help_text
    )