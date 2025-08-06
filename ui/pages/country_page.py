"""
Enhanced Country Contract Page for Agiloft CLM Analytics
Updated with 2x4 grid layout for Analysis Results section
"""

import streamlit as st
import pandas as pd
import altair as alt
import pydeck as pdk
import logging
from typing import Dict, Any, Tuple
from datetime import datetime

from ui.base_page import FilteredPage, ChartHelper
from database.db_interface import DataTransformer
from config.settings import app_config, ui_config
from utils.exceptions import DataProcessingError

logger = logging.getLogger(__name__)

class CountryPage(FilteredPage):
    """Page for displaying contract data by country with enhanced 2x4 grid layout"""
    
    def __init__(self):
        super().__init__("Contract Value ($) by Country", "")
        self.transformer = DataTransformer()
        self.chart_helper = ChartHelper()
        self.country_coordinates = self._load_country_coordinates()
    
    def _load_country_coordinates(self) -> pd.DataFrame:
        """Load country coordinates for mapping"""
        try:
            # Try to load from CSV file first
            import os
            csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'country_coordinates.csv')
            if os.path.exists(csv_path):
                coords_df = pd.read_csv(csv_path)
                logger.info(f"Loaded {len(coords_df)} country coordinates from CSV")
                return coords_df
        except Exception as e:
            logger.warning(f"Could not load coordinates from CSV: {e}")
        
        # Fallback to default coordinates for common countries
        default_coordinates = {
            'country_name': [
                'ARGENTINA', 'BRAZIL', 'CANADA', 'CHINA', 'EGYPT', 'ETHIOPIA',
                'FRANCE', 'GERMANY', 'INDIA', 'INDONESIA', 'IRAN', 'IRAQ',
                'JAPAN', 'JORDAN', 'KENYA', 'MOROCCO', 'MOZAMBIQUE', 'PERU',
                'ROMANIA', 'RUSSIA', 'SAUDI ARABIA', 'UNITED KINGDOM', 'UNITED STATES', 'VIETNAM'
            ],
            'latitude': [
                -34.6118, -14.2350, 56.1304, 35.8617, 26.0975, 9.1450,
                46.2276, 51.1657, 20.5937, -0.7893, 32.4279, 33.2232,
                36.2048, 30.5852, -0.0236, 31.7917, -18.6657, -9.1900,
                45.9432, 61.5240, 23.8859, 55.3781, 37.0902, 14.0583
            ],
            'longitude': [
                -58.3960, -51.9253, -106.3468, 104.1954, 31.2357, 40.4897,
                2.2137, 10.4515, 78.9629, 113.9213, 53.6880, 43.6793,
                138.2529, 36.2384, 37.9062, -7.0926, 35.5296, -75.0152,
                24.9668, 105.3188, 45.0792, -3.4360, -95.7129, 108.2772
            ]
        }
        
        logger.info("Using default country coordinates")
        return pd.DataFrame(default_coordinates)
    
    def render_sidebar_filters(self) -> Dict[str, Any]:
        """Render sidebar filters for country page with organized expanders"""
        try:
            # Geographic Filters
            with st.expander("Geographic Filters", expanded=False):
                st.subheader("Data Selection")
                
                # Customer range selection - IN ROWS FOR BETTER FIT
                customer_start = st.text_input(
                    "Start Customer ID",
                    value="Customer#000000001",
                    help="Starting customer ID for the range"
                )
                
                customer_end = st.text_input(
                    "End Customer ID",
                    value="Customer#000000070",
                    help="Ending customer ID for the range"
                )
                
                # Show range summary
                try:
                    start_num = int(customer_start.split('#')[1])
                    end_num = int(customer_end.split('#')[1])
                    range_size = end_num - start_num + 1
                    st.info(f"Selected range includes {range_size:,} customer IDs")
                except:
                    st.warning("Invalid customer ID format. Use format: Customer#000000001")
                
                # Year range selection
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
                "customer_range": (customer_start, customer_end),
                "year_range": year_range
            }
            
        except Exception as e:
            logger.error(f"Error rendering country sidebar filters: {str(e)}")
            self.render_error("Error loading filter options")
            return {}
    
    def _render_visualization_settings(self):
        """Override to provide country page specific visualization options"""
        # Map visualization options
        show_map = st.checkbox(
            "Show Geographic Map",
            value=True,
            help="Display contracts on a world map",
            key="country_show_map"
        )
        
        # Chart type and styling
        chart_type = st.selectbox(
            "Chart Type",
            ["Line Chart", "Bar Chart", "Area Chart"],
            index=0,
            help="Select visualization type for time series",
            key="country_chart_type"
        )
        
        # Color scheme selection - SAME AS STATUS PAGE
        color_scheme = st.selectbox(
            "Color Scheme",
            ["category10", "viridis", "plasma", "blues", "greens"],
            index=1,  # Default to viridis like status page
            help="Choose color palette for charts",
            key="country_color_scheme"
        )
        
        top_n_countries = st.slider(
            "Top N Countries to Display",
            min_value=5,
            max_value=25,
            value=15,
            help="Limit the number of countries shown in charts",
            key="country_top_n"
        )
        
        st.markdown("**Analysis Options**")
        
        show_regional_analysis = st.checkbox(
            "Show Regional Analysis",
            value=True,
            help="Group countries by region for analysis",
            key="country_regional_analysis"
        )
        
        include_growth_metrics = st.checkbox(
            "Include Growth Metrics",
            value=True,
            help="Calculate and display growth rates",
            key="country_growth_metrics"
        )
        
        show_summary = st.checkbox(
            "Show Summary Statistics",
            value=True,
            help="Display key metrics at the top of the page",
            key="country_show_summary"
        )
        
        # Update filters with visualization settings
        if hasattr(self, 'filters'):
            self.filters.update({
                "show_map": show_map,
                "chart_type": chart_type,
                "color_scheme": color_scheme,
                "top_n_countries": top_n_countries,
                "show_regional_analysis": show_regional_analysis,
                "include_growth_metrics": include_growth_metrics,
                "show_summary": show_summary
            })
    
    def validate_filters(self, filters: Dict[str, Any]) -> bool:
        """Validate filter inputs"""
        if not filters:
            return False
        
        customer_range = filters.get("customer_range")
        if not customer_range or not customer_range[0] or not customer_range[1]:
            self.render_warning("Please provide valid customer range")
            return False
        
        year_range = filters.get("year_range")
        if year_range and year_range[0] > year_range[1]:
            self.render_warning("Invalid year range selected")
            return False
        
        return True
    
    def process_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Process country contract data based on filters"""
        try:
            # Get raw data from database
            raw_data = self.db_manager.get_country_contract_data(
                customer_range=filters["customer_range"],
                year_range=filters["year_range"]
            )
            
            if raw_data.empty:
                return {}
            
            # Transform data for display
            pivot_data = self.transformer.pivot_country_data(raw_data)
            pivot_data.index = pivot_data.index.astype(str)
            
            # Prepare map data
            map_data = self._prepare_map_data(raw_data, filters)
            
            # Aggregate data by country
            country_totals = raw_data.groupby('country_name')['total_contract_value'].sum().reset_index()
            country_totals = country_totals.sort_values('total_contract_value', ascending=False)
            
            # Limit to top N countries
            if filters["top_n_countries"] < len(country_totals):
                top_countries = country_totals.head(filters["top_n_countries"])['country_name'].tolist()
                pivot_data = pivot_data[pivot_data.columns.intersection(top_countries)]
                country_totals = country_totals.head(filters["top_n_countries"])
            
            # Calculate growth metrics if requested
            growth_data = {}
            if filters["include_growth_metrics"]:
                growth_data = self._calculate_growth_metrics(raw_data, filters)
            
            # Regional analysis if requested
            regional_data = {}
            if filters["show_regional_analysis"]:
                regional_data = self._perform_regional_analysis(raw_data, filters)
            
            # Calculate summary statistics
            summary_stats = self._calculate_summary_stats(raw_data, filters)
            
            return {
                "raw_data": raw_data,
                "pivot_data": pivot_data,
                "map_data": map_data,
                "country_totals": country_totals,
                "growth_data": growth_data,
                "regional_data": regional_data,
                "summary_stats": summary_stats
            }
            
        except Exception as e:
            logger.error(f"Error processing country data: {str(e)}")
            raise DataProcessingError(f"Failed to process country data: {str(e)}")
    
    def _prepare_map_data(self, raw_data: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Prepare data for map visualization"""
        try:
            # Aggregate by country
            country_data = raw_data.groupby('country_name')['total_contract_value'].sum().reset_index()
            
            # Merge with coordinates
            map_data = country_data.merge(
                self.country_coordinates, 
                on='country_name', 
                how='left'
            )
            
            # Remove countries without coordinates
            map_data = map_data.dropna(subset=['latitude', 'longitude'])
            
            if map_data.empty:
                return pd.DataFrame()
            
            # Data is ready for Streamlit's simple map (no custom styling needed)
            
            return map_data
            
        except Exception as e:
            logger.error(f"Error preparing map data: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_growth_metrics(self, raw_data: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate growth metrics for countries"""
        try:
            growth_data = {}
            
            for country in raw_data['country_name'].unique():
                country_data = raw_data[raw_data['country_name'] == country]
                yearly_values = country_data.groupby('contract_year')['total_contract_value'].sum()
                
                if len(yearly_values) > 1:
                    # Calculate year-over-year growth
                    growth_rates = yearly_values.pct_change() * 100
                    avg_growth = growth_rates.mean()
                    
                    growth_data[country] = {
                        'yearly_values': yearly_values,
                        'growth_rates': growth_rates,
                        'avg_growth': avg_growth
                    }
            
            return growth_data
            
        except Exception as e:
            logger.error(f"Error calculating growth metrics: {str(e)}")
            return {}
    
    def _perform_regional_analysis(self, raw_data: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform regional analysis grouping"""
        try:
            # Simple regional grouping (this could be enhanced with a proper mapping)
            region_mapping = {
                'UNITED STATES': 'North America',
                'CANADA': 'North America',
                'BRAZIL': 'South America',
                'ARGENTINA': 'South America',
                'PERU': 'South America',
                'UNITED KINGDOM': 'Europe',
                'FRANCE': 'Europe',
                'GERMANY': 'Europe',
                'ROMANIA': 'Europe',
                'RUSSIA': 'Europe',
                'CHINA': 'Asia',
                'JAPAN': 'Asia',
                'INDIA': 'Asia',
                'INDONESIA': 'Asia',
                'VIETNAM': 'Asia',
                'IRAN': 'Middle East',
                'IRAQ': 'Middle East',
                'JORDAN': 'Middle East',
                'SAUDI ARABIA': 'Middle East',
                'EGYPT': 'Africa',
                'ETHIOPIA': 'Africa',
                'KENYA': 'Africa',
                'MOROCCO': 'Africa',
                'MOZAMBIQUE': 'Africa'
            }
            
            # Add region column
            regional_data = raw_data.copy()
            regional_data['region'] = regional_data['country_name'].map(region_mapping)
            regional_data['region'] = regional_data['region'].fillna('Other')
            
            # Aggregate by region
            regional_totals = regional_data.groupby('region')['total_contract_value'].sum().reset_index()
            regional_totals = regional_totals.sort_values('total_contract_value', ascending=False)
            
            # Regional trends over time
            regional_trends = regional_data.groupby(['region', 'contract_year'])['total_contract_value'].sum().reset_index()
            
            return {
                'regional_totals': regional_totals,
                'regional_trends': regional_trends,
                'region_mapping': region_mapping
            }
            
        except Exception as e:
            logger.error(f"Error performing regional analysis: {str(e)}")
            return {}
    
    def _calculate_summary_stats(self, data: pd.DataFrame, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics"""
        try:
            total_contracts = len(data)
            total_value = data["total_contract_value"].sum()
            avg_value = data["total_contract_value"].mean()
            unique_countries = data["country_name"].nunique()
            unique_years = data["contract_year"].nunique()
            
            # Top country
            top_country_data = data.groupby("country_name")["total_contract_value"].sum()
            top_country = top_country_data.idxmax()
            top_country_value = top_country_data.max()
            
            return {
                "total_contracts": total_contracts,
                "total_value": total_value,
                "avg_value": avg_value,
                "unique_countries": unique_countries,
                "unique_years": unique_years,
                "top_country": top_country,
                "top_country_value": top_country_value
            }
        except Exception as e:
            logger.error(f"Error calculating summary stats: {str(e)}")
            return {}
    
    def render_metrics(self, data: Dict[str, Any]):
        """Render key metrics using enhanced grid system"""
        if not self.filters.get("show_summary") or not data.get("summary_stats"):
            return
        
        stats = data["summary_stats"]
        
        st.subheader("Global Contract Overview")
        
        # Create metrics dictionary for the enhanced grid - SAME AS STATUS PAGE
        metrics = {
            "Countries": {
                "value": stats["unique_countries"],
                "format": "number",
                "help": "Number of countries with contracts"
            },
            "Total Value": {
                "value": stats["total_value"],
                "format": "currency",
                "help": "Sum of all contract values"
            },
            "Years Covered": {
                "value": stats["unique_years"],
                "format": "number",
                "help": "Number of years in the data"
            },
            "Avg Value": {
                "value": stats["avg_value"],
                "format": "currency",
                "help": "Average contract value"
            }
        }
        
        # Use the enhanced render_metrics_grid function
        try:
            from ui.components import render_metrics_grid
            render_metrics_grid(metrics, columns=4)
        except ImportError:
            # Fallback to basic metrics display
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Countries", f"{stats['unique_countries']:,}", help="Number of countries with contracts")
            with col2:
                st.metric("Total Value", self.chart_helper.format_number(stats["total_value"]), help="Sum of all contract values")
            with col3:
                st.metric("Years Covered", f"{stats['unique_years']:,}", help="Number of years in the data")
            with col4:
                st.metric("Avg Value", self.chart_helper.format_number(stats["avg_value"]), help="Average contract value")
        
        # Top country info
        if "top_country" in stats:
            st.info(
                f"Top Country: **{stats['top_country']}** with "
                f"**{self.chart_helper.format_number(stats['top_country_value'])}** in total contracts"
            )
    
    def _render_main_analysis(self):
        """Override main analysis rendering to use 2x4 grid layout"""
        # st.subheader("Analysis Results")
        
        # Add custom CSS for consistent cell heights
        st.markdown("""
        <style>
        .grid-cell {
            height: 400px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # ROW 1: Contract Data by Country | Geographic Distribution
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_country_data_table()
        
        with col2:
            self._render_geographic_map()
        
        # ROW 2: Regional Analysis (table) | Country Trends Over Time
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_regional_analysis_table()
        
        with col2:
            self._render_country_trends_chart()
        
        # ROW 3: Regional Analysis (bar chart) | Regional Analysis (line chart)
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_regional_bar_chart()
        
        with col2:
            self._render_regional_line_chart()
        
        # ROW 4: Growth Analysis - Top Growing | Growth Analysis - Declining
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_top_growing_countries()
        
        with col2:
            self._render_declining_countries()
    
    def _render_country_data_table(self):
        """Render contract data by country table"""
        st.markdown("#### Contract Data by Country")
        
        if "country_totals" not in self.data or self.data["country_totals"].empty:
            st.info("No country data available")
            return
        
        country_data = self.data["country_totals"]
        
        st.dataframe(
            country_data,
            use_container_width=True,
            height=350,
            column_config={
                "country_name": "Country",
                "total_contract_value": st.column_config.NumberColumn(
                    "Total Contract Value",
                    format="$%.0f"
                )
            },
            hide_index=True
        )
    
    def _render_geographic_map(self):
        """Render geographic distribution map"""
        st.markdown("#### Geographic Distribution")
        
        if not self.filters.get("show_map"):
            st.info("Geographic map is disabled in filters")
            return
        
        if "map_data" not in self.data or self.data["map_data"].empty:
            st.info("No geographic data available for mapping")
            return
        
        map_data = self.data["map_data"]
        
        # Ensure data types are correct
        map_data = map_data.copy()
        map_data['latitude'] = pd.to_numeric(map_data['latitude'], errors='coerce')
        map_data['longitude'] = pd.to_numeric(map_data['longitude'], errors='coerce')
        map_data['total_contract_value'] = pd.to_numeric(map_data['total_contract_value'], errors='coerce')
        
        # Remove any rows with NaN coordinates
        map_data = map_data.dropna(subset=['latitude', 'longitude'])
        
        if map_data.empty:
            st.warning("No valid coordinate data available for mapping")
            return
        
        # Use Streamlit's built-in map which is more reliable
        try:
            # st.markdown("**World Map View**")
            
            # Prepare data for Streamlit map
            st_map_data = map_data[['latitude', 'longitude', 'country_name', 'total_contract_value']].copy()
            st_map_data = st_map_data.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
            
            # Show the map with red dots
            st.map(st_map_data[['lat', 'lon']], zoom=1, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering map: {str(e)}")
            logger.error(f"Map rendering error: {str(e)}")
            
            # Final fallback to simple table
            st.markdown("**Country Data (Table View)**")
            display_data = map_data[['country_name', 'total_contract_value', 'latitude', 'longitude']].copy()
            st.dataframe(display_data, use_container_width=True)
    
    def _render_regional_analysis_table(self):
        """Render regional analysis table"""
        st.markdown("#### Regional Analysis")
        
        if not self.filters.get("show_regional_analysis"):
            st.info("Regional analysis is disabled in filters")
            return
        
        if "regional_data" not in self.data or "regional_totals" not in self.data["regional_data"]:
            st.info("No regional data available")
            return
        
        regional_totals = self.data["regional_data"]["regional_totals"]
        
        st.dataframe(
            regional_totals,
            use_container_width=True,
            height=350,
            column_config={
                "region": "Region",
                "total_contract_value": st.column_config.NumberColumn(
                    "Total Contract Value",
                    format="$%.0f"
                )
            },
            hide_index=True
        )
    
    def _render_country_trends_chart(self):
        """Render country trends over time chart with theme support"""
        st.markdown("#### Country Trends Over Time")
        
        if "pivot_data" not in self.data or self.data["pivot_data"].empty:
            st.info("No trend data available")
            return
        
        pivot_data = self.data["pivot_data"]
        chart_type = self.filters.get("chart_type", "Line Chart")
        color_scheme = self.filters.get("color_scheme", "category10")
        
        try:
            # Prepare data for Altair
            chart_data = pivot_data.reset_index()
            chart_data = pd.melt(
                chart_data,
                id_vars="contract_year",
                var_name="country_name",
                value_name="total_contract_value"
            )
            chart_data["total_contract_value"] = chart_data["total_contract_value"].astype(float)
            
            # Create themed Altair chart
            base_chart = alt.Chart(chart_data)
            
            if chart_type == "Line Chart":
                chart = base_chart.mark_line(
                    point=True,
                    strokeWidth=2,
                    opacity=0.8
                ).encode(
                    x=alt.X("contract_year:O", title="Year"),
                    y=alt.Y("total_contract_value:Q", title="Contract Value", axis=alt.Axis(format="$,.0f")),
                    color=alt.Color(
                        "country_name:N",
                        scale=alt.Scale(scheme=color_scheme),
                        legend=alt.Legend(title="Country")
                    ),
                    tooltip=["contract_year:O", "country_name:N", alt.Tooltip("total_contract_value:Q", format="$,.0f")]
                )
            elif chart_type == "Bar Chart":
                chart = base_chart.mark_bar(
                    opacity=0.8
                ).encode(
                    x=alt.X("contract_year:O", title="Year"),
                    y=alt.Y("total_contract_value:Q", title="Contract Value", axis=alt.Axis(format="$,.0f")),
                    color=alt.Color(
                        "country_name:N",
                        scale=alt.Scale(scheme=color_scheme),
                        legend=alt.Legend(title="Country")
                    ),
                    tooltip=["contract_year:O", "country_name:N", alt.Tooltip("total_contract_value:Q", format="$,.0f")]
                )
            else:  # Area Chart
                chart = base_chart.mark_area(
                    opacity=0.7
                ).encode(
                    x=alt.X("contract_year:O", title="Year"),
                    y=alt.Y("total_contract_value:Q", title="Contract Value", axis=alt.Axis(format="$,.0f"), stack="zero"),
                    color=alt.Color(
                        "country_name:N",
                        scale=alt.Scale(scheme=color_scheme),
                        legend=alt.Legend(title="Country")
                    ),
                    tooltip=["contract_year:O", "country_name:N", alt.Tooltip("total_contract_value:Q", format="$,.0f")]
                )
            
            chart = chart.properties(
                width=350,
                height=350,
                # title="Country Performance Over Time"
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering themed chart: {str(e)}")
            # Fallback to basic chart
            if chart_type == "Line Chart":
                st.line_chart(pivot_data, height=350)
            elif chart_type == "Bar Chart":
                st.bar_chart(pivot_data.T, height=350)
            elif chart_type == "Area Chart":
                st.area_chart(pivot_data, height=350)
    
    def _render_regional_bar_chart(self):
        """Render regional analysis bar chart with theme support"""
        st.markdown("#### Regional Contract Distribution")
        
        if not self.filters.get("show_regional_analysis"):
            st.info("Regional analysis is disabled in filters")
            return
        
        if "regional_data" not in self.data or "regional_totals" not in self.data["regional_data"]:
            st.info("No regional data available")
            return
        
        regional_totals = self.data["regional_data"]["regional_totals"]
        color_scheme = self.filters.get("color_scheme", "category10")
        
        try:
            # Create themed Altair bar chart
            chart = alt.Chart(regional_totals).mark_bar(
                opacity=0.8
            ).encode(
                x=alt.X("region:N", title="Region", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("total_contract_value:Q", title="Total Contract Value", axis=alt.Axis(format="$,.0f")),
                color=alt.Color(
                    "region:N",
                    scale=alt.Scale(scheme=color_scheme),
                    legend=None  # Hide legend since x-axis shows region names
                ),
                tooltip=[
                    alt.Tooltip("region:N", title="Region"),
                    alt.Tooltip("total_contract_value:Q", title="Total Value", format="$,.0f")
                ]
            ).properties(
                width=350,
                height=350,
                # title="Regional Contract Distribution"
            )
            
            st.altair_chart(chart, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering themed bar chart: {str(e)}")
            # Fallback to basic chart
            try:
                chart_data = regional_totals.set_index("region")["total_contract_value"]
                st.bar_chart(chart_data, height=350)
            except:
                st.dataframe(regional_totals, use_container_width=True)
    
    def _render_regional_line_chart(self):
        """Render regional analysis line chart with theme support"""
        st.markdown("#### Regional Trends Over Time")
        
        if not self.filters.get("show_regional_analysis"):
            st.info("Regional analysis is disabled in filters")
            return
        
        if "regional_data" not in self.data or "regional_trends" not in self.data["regional_data"]:
            st.info("No regional trend data available")
            return
        
        regional_trends = self.data["regional_data"]["regional_trends"]
        color_scheme = self.filters.get("color_scheme", "category10")
        
        try:
            # Prepare data for Altair (already in the right format)
            chart_data = regional_trends.copy()
            chart_data["total_contract_value"] = chart_data["total_contract_value"].astype(float)
            
            # Create themed Altair line chart
            chart = alt.Chart(chart_data).mark_line(
                point=True,
                strokeWidth=3,
                opacity=0.8
            ).encode(
                x=alt.X("contract_year:O", title="Year"),
                y=alt.Y("total_contract_value:Q", title="Total Contract Value", axis=alt.Axis(format="$,.0f")),
                color=alt.Color(
                    "region:N",
                    scale=alt.Scale(scheme=color_scheme),
                    legend=alt.Legend(title="Region")
                ),
                tooltip=[
                    alt.Tooltip("contract_year:O", title="Year"),
                    alt.Tooltip("region:N", title="Region"),
                    alt.Tooltip("total_contract_value:Q", title="Total Value", format="$,.0f")
                ]
            ).properties(
                width=350,
                height=350,
                # title="Regional Trends Over Time"
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering themed line chart: {str(e)}")
            # Fallback to basic chart
            try:
                pivot_regional = regional_trends.pivot(
                    index="contract_year", 
                    columns="region", 
                    values="total_contract_value"
                ).fillna(0)
                st.line_chart(pivot_regional, height=350)
            except:
                st.dataframe(regional_trends.head(10), use_container_width=True)
    
    def _render_top_growing_countries(self):
        """Render top growing countries table"""
        st.markdown("#### Top Growing Countries")
        
        if not self.filters.get("include_growth_metrics"):
            st.info("Growth metrics are disabled in filters")
            return
        
        if "growth_data" not in self.data or not self.data["growth_data"]:
            st.info("No growth data available")
            return
        
        growth_data = self.data["growth_data"]
        
        # Create growth summary
        growth_summary = []
        for country, data_item in growth_data.items():
            avg_growth = data_item.get('avg_growth', 0)
            if avg_growth > 0:  # Only positive growth
                growth_summary.append({
                    'country': country,
                    'avg_growth_rate': avg_growth
                })
        
        if not growth_summary:
            st.info("No growing countries found in the data")
            return
        
        growth_df = pd.DataFrame(growth_summary).sort_values('avg_growth_rate', ascending=False)
        top_growth = growth_df.head(15)
        
        st.dataframe(
            top_growth,
            use_container_width=True,
            height=350,
            column_config={
                "country": "Country",
                "avg_growth_rate": st.column_config.NumberColumn(
                    "Avg Growth Rate (%)",
                    format="%.1f%%"
                )
            },
            hide_index=True
        )
    
    def _render_declining_countries(self):
        """Render declining countries table"""
        st.markdown("#### Declining Countries")
        
        if not self.filters.get("include_growth_metrics"):
            st.info("Growth metrics are disabled in filters")
            return
        
        if "growth_data" not in self.data or not self.data["growth_data"]:
            st.info("No growth data available")
            return
        
        growth_data = self.data["growth_data"]
        
        # Create decline summary
        decline_summary = []
        for country, data_item in growth_data.items():
            avg_growth = data_item.get('avg_growth', 0)
            if avg_growth < 0:  # Only negative growth (declining)
                decline_summary.append({
                    'country': country,
                    'avg_decline_rate': abs(avg_growth)  # Make positive for display
                })
        
        if not decline_summary:
            st.info("No declining countries found in the data")
            return
        
        decline_df = pd.DataFrame(decline_summary).sort_values('avg_decline_rate', ascending=False)
        top_decline = decline_df.head(15)
        
        st.dataframe(
            top_decline,
            use_container_width=True,
            height=350,
            column_config={
                "country": "Country",
                "avg_decline_rate": st.column_config.NumberColumn(
                    "Avg Decline Rate (%)",
                    format="%.1f%%"
                )
            },
            hide_index=True
        )
    
    # Keep existing methods for compatibility but mark as deprecated
    def render_data_tables(self, data: Dict[str, Any]):
        """Deprecated: Now handled by grid layout"""
        pass
    
    def render_visualizations(self, data: Dict[str, Any]):
        """Deprecated: Now handled by grid layout"""
        pass
    
    def handle_export(self, data: Dict[str, Any]):
        """Handle data export functionality"""
        if not data:
            return
        
        st.subheader("Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Export Country Data"):
                if "country_totals" in data:
                    csv = data["country_totals"].to_csv(index=False)
                    st.download_button(
                        label="Download Country Data CSV",
                        data=csv,
                        file_name="country_contract_data.csv",
                        mime="text/csv"
                    )
        
        with col2:
            if st.button("Export Map Data"):
                if "map_data" in data and not data["map_data"].empty:
                    csv = data["map_data"].to_csv(index=False)
                    st.download_button(
                        label="Download Map Data CSV",
                        data=csv,
                        file_name="country_map_data.csv",
                        mime="text/csv"
                    )
        
        with col3:
            if st.button("Export Analysis Report"):
                if "summary_stats" in data:
                    report = self._generate_summary_report(data)
                    st.download_button(
                        label="Download Analysis Report",
                        data=report,
                        file_name="country_analysis_report.txt",
                        mime="text/plain"
                    )
    
    def _generate_summary_report(self, data: Dict[str, Any]) -> str:
        """Generate text summary report"""
        stats = data.get("summary_stats", {})
        regional_data = data.get("regional_data", {})
        growth_data = data.get("growth_data", {})
        
        report = f"""
Country Contract Analysis Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

EXECUTIVE SUMMARY
================
- Total Countries: {stats.get('unique_countries', 'N/A')}
- Total Contract Value: {self.chart_helper.format_number(stats.get('total_value', 0))}
- Average Contract Value: {self.chart_helper.format_number(stats.get('avg_value', 0))}
- Years Analyzed: {stats.get('unique_years', 'N/A')}
- Top Performing Country: {stats.get('top_country', 'N/A')}
- Top Country Value: {self.chart_helper.format_number(stats.get('top_country_value', 0))}

FILTER SETTINGS
==============
- Customer Range: {self.filters.get('customer_range', ('N/A', 'N/A'))[0]} to {self.filters.get('customer_range', ('N/A', 'N/A'))[1]}
- Year Range: {self.filters.get('year_range', (0, 0))[0]} to {self.filters.get('year_range', (0, 0))[1]}
- Top Countries Displayed: {self.filters.get('top_n_countries', 'N/A')}
- Chart Type: {self.filters.get('chart_type', 'N/A')}
- Map Visualization: {self.filters.get('show_map', False)}
"""
        
        # Add regional analysis if available
        if regional_data and "regional_totals" in regional_data:
            report += "\nREGIONAL BREAKDOWN\n================\n"
            regional_totals = regional_data["regional_totals"]
            for _, row in regional_totals.iterrows():
                region = row['region']
                value = self.chart_helper.format_number(row['total_contract_value'])
                report += f"- {region}: {value}\n"
        
        # Add growth analysis if available
        if growth_data:
            report += "\nGROWTH ANALYSIS\n==============\n"
            growth_summary = []
            for country, data_item in growth_data.items():
                avg_growth = data_item.get('avg_growth', 0)
                growth_summary.append((country, avg_growth))
            
            # Sort by growth rate
            growth_summary.sort(key=lambda x: x[1], reverse=True)
            
            report += "Top Growing Countries:\n"
            for country, growth in growth_summary[:5]:
                report += f"- {country}: {growth:.1f}% avg growth\n"
            
            if len(growth_summary) > 5:
                report += "\nDeclining Countries:\n"
                declining = [item for item in growth_summary if item[1] < 0]
                for country, growth in declining[:5]:
                    report += f"- {country}: {growth:.1f}% avg decline\n"
        
        return report