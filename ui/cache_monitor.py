"""
Cache monitoring component for Agiloft Analytics
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def render_cache_monitor_sidebar(db_manager):
    """Render cache monitoring in sidebar"""
    
    with st.sidebar:
        with st.expander("Cache Monitor", expanded=False):
            try:
                # Get cache stats
                cache_stats = db_manager.get_cache_stats()
                
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
                st.markdown("**Actions:**")
                
                if st.button("Warm Cache", help="Pre-load common queries"):
                    with st.spinner("Warming cache..."):
                        db_manager.warm_cache()
                    st.success("Cache warmed!")
                    st.rerun()
                
                if st.button("Clear Cache", help="Clear all cached data"):
                    db_manager.invalidate_cache()
                    st.success("Cache cleared!")
                    st.rerun()
                
                # Show detailed stats if cache is active
                if basic_stats.get('total_entries', 0) > 0:
                    with st.expander("Detailed Stats"):
                        st.json(cache_stats)
                
            except Exception as e:
                st.error(f"Cache monitor error: {e}")
                logger.error(f"Cache monitor error: {e}")

def render_cache_health_indicator(db_manager):
    """Render a simple cache health indicator"""
    try:
        cache_stats = db_manager.get_cache_stats()
        basic_stats = cache_stats.get("basic_stats", {})
        
        hit_rate = basic_stats.get("hit_rate", 0)
        
        if hit_rate >= 70:
            st.success(f"Cache: {hit_rate:.1f}% hit rate")
        elif hit_rate >= 40:
            st.warning(f"Cache: {hit_rate:.1f}% hit rate") 
        elif hit_rate > 0:
            st.info(f"Cache: {hit_rate:.1f}% hit rate")
        else:
            st.info("Cache: Warming up...")
            
    except Exception as e:
        logger.error(f"Cache health indicator error: {e}")

def create_cache_performance_page(db_manager):
    """Create a detailed cache performance page"""
    
    st.header("Cache Performance Dashboard")
    
    try:
        # Get comprehensive stats
        cache_stats = db_manager.get_cache_stats()
        pool_health = db_manager.get_pool_health()
        combined_health = db_manager.get_combined_health()
        
        # Overall health indicator
        status = combined_health.get("overall_status", "unknown")
        if status == "healthy":
            st.success("System Health: Excellent")
        else:
            st.warning("System Health: Needs Attention")
        
        # Main metrics
        st.subheader("Cache Performance")
        
        basic_stats = cache_stats.get("basic_stats", {})
        performance = cache_stats.get("performance", {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Hit Rate", 
                f"{basic_stats.get('hit_rate', 0):.1f}%",
                help="Percentage of requests served from cache"
            )
        
        with col2:
            st.metric(
                "Total Entries",
                f"{basic_stats.get('total_entries', 0):,}",
                help="Number of cached items"
            )
        
        with col3:
            st.metric(
                "Cache Size",
                f"{basic_stats.get('total_size_mb', 0):.1f} MB",
                f"/ {basic_stats.get('max_size_mb', 100)} MB"
            )
        
        with col4:
            st.metric(
                "Evictions",
                f"{basic_stats.get('evictions', 0):,}",
                help="Items removed due to space/time limits"
            )
        
        # Query patterns
        st.subheader("Query Patterns")
        
        query_patterns = cache_stats.get("query_patterns", {})
        if query_patterns:
            # Create DataFrame for visualization
            pattern_df = pd.DataFrame([
                {"Query Type": k, "Count": v} 
                for k, v in query_patterns.items()
            ]).sort_values("Count", ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.bar_chart(pattern_df.set_index("Query Type")["Count"])
            
            with col2:
                st.dataframe(pattern_df, hide_index=True)
        
        # Tag distribution
        st.subheader("Cache Tag Distribution")
        
        tag_distribution = cache_stats.get("tag_distribution", {})
        if tag_distribution:
            tag_df = pd.DataFrame([
                {"Tag": k, "Entries": v}
                for k, v in tag_distribution.items()
            ]).sort_values("Entries", ascending=False)
            
            st.dataframe(tag_df, hide_index=True)
        
        # Recommendations
        recommendations = cache_stats.get("recommendations", [])
        if recommendations:
            st.subheader("Optimization Recommendations")
            for rec in recommendations:
                st.info(f"• {rec}")
        
        # Connection pool health
        st.subheader("Connection Pool Health")
        
        pool_stats = pool_health.get("stats", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Active Connections",
                pool_stats.get("active_connections", 0),
                f"/ {pool_stats.get('max_connections', 0)} max"
            )
        
        with col2:
            st.metric(
                "Total Queries",
                f"{pool_stats.get('total_queries', 0):,}",
                help="Queries executed through pool"
            )
        
        with col3:
            utilization = pool_health.get("utilization_percent", 0)
            st.metric(
                "Pool Utilization",
                f"{utilization:.1f}%",
                help="Percentage of pool capacity in use"
            )
        
        # Pool recommendations
        pool_recommendations = pool_health.get("recommendations", [])
        if pool_recommendations:
            st.subheader("Pool Optimization")
            for rec in pool_recommendations:
                st.info(f"• {rec}")
        
        # Cache management actions
        st.subheader("Cache Management")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Warm Cache", help="Pre-load common data"):
                with st.spinner("Warming cache..."):
                    db_manager.warm_cache()
                st.success("Cache warmed successfully!")
                st.rerun()
        
        with col2:
            if st.button("Clear All Cache", help="Remove all cached data"):
                db_manager.invalidate_cache()
                st.success("Cache cleared!")
                st.rerun()
        
        with col3:
            if st.button("Refresh Stats", help="Update performance metrics"):
                st.rerun()
        
        # Advanced cache controls
        with st.expander("Advanced Cache Controls"):
            
            # Selective cache invalidation
            st.markdown("**Selective Cache Invalidation:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Clear Manager Data"):
                    db_manager.invalidate_cache(["managers"])
                    st.success("Manager cache cleared!")
                
                if st.button("Clear Status Data"):
                    db_manager.invalidate_cache(["statuses"]) 
                    st.success("Status cache cleared!")
            
            with col2:
                if st.button("Clear Customer Data"):
                    db_manager.invalidate_cache(["customers"])
                    st.success("Customer cache cleared!")
                
                if st.button("Clear Amount Data"):
                    db_manager.invalidate_cache(["amounts"])
                    st.success("Amount cache cleared!")
            
            # Raw stats
            st.markdown("**Raw Statistics:**")
            st.json(cache_stats)
        
    except Exception as e:
        st.error(f"Error loading cache performance data: {e}")
        logger.error(f"Cache performance page error: {e}")