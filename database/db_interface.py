"""
Database interface for Agiloft CLM Analytics

Provides database-agnostic interface for data operations
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import datetime

class DatabaseInterface(ABC):
    """Abstract base class for database operations"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish database connection"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Close database connection"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test database connection"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        pass
    
    @abstractmethod
    def get_contract_status_data(self, 
                               contract_managers: List[str],
                               status_filter: Optional[List[str]] = None) -> pd.DataFrame:
        """Get contract data grouped by status"""
        pass
    
    @abstractmethod
    def get_customer_contract_data(self, 
                                 customer_range: Tuple[str, str],
                                 year_range: Optional[Tuple[int, int]] = None) -> pd.DataFrame:
        """Get contract data grouped by customer"""
        pass
    
    @abstractmethod
    def get_country_contract_data(self, 
                                customer_range: Tuple[str, str],
                                year_range: Optional[Tuple[int, int]] = None) -> pd.DataFrame:
        """Get contract data grouped by country"""
        pass

class ContractDataQueries:
    """SQL queries for contract data operations - Fixed for proper schema"""
    
    # Status analysis query - matches your original working query
    CONTRACT_STATUS_QUERY = """
        SELECT 
            co_contractmanager, 
            co_status, 
            SUM(co_amount) AS co_amount 
        FROM contract 
        WHERE co_contractmanager BETWEEN %s AND %s
        GROUP BY co_contractmanager, co_status
        ORDER BY co_contractmanager, co_status
    """
    
    # Customer analysis query - UUID-compatible join
    # Note: Both c_custkey and co_custkey are now UUID strings (varchar(36))
    CUSTOMER_CONTRACT_QUERY = """
        SELECT
            c.c_name,
            YEAR(co.co_datesigned) AS contract_year,
            SUM(co.co_amount) AS total_contract_value
        FROM customer c
        JOIN contract co ON c.c_custkey = co.co_custkey
        WHERE co.co_datesigned IS NOT NULL
        AND co.co_datesigned >= DATE_SUB(CURDATE(), INTERVAL %s YEAR)
        AND c.c_name IN ({customer_placeholders})
        GROUP BY c.c_name, contract_year
        ORDER BY c.c_name, contract_year DESC, total_contract_value DESC
    """
    
    # Country analysis - UUID-compatible join with customer and nation tables
    COUNTRY_CONTRACT_QUERY = """
        SELECT
            n.n_name AS country_name,
            YEAR(co.co_datesigned) AS contract_year,
            SUM(co.co_amount) AS total_contract_value
        FROM contract co
        JOIN customer c ON c.c_custkey = co.co_custkey
        JOIN nation n ON c.c_nationkey = n.n_nationkey
        WHERE co.co_datesigned IS NOT NULL
        AND co.co_datesigned >= DATE_SUB(CURDATE(), INTERVAL %s YEAR)
        AND c.c_name IN ({customer_placeholders})
        GROUP BY country_name, contract_year
        ORDER BY country_name, contract_year DESC
    """
    
    CONNECTION_TEST_QUERY = "SELECT 1 as test"
    
    @staticmethod
    def get_filtered_status_query(status_filter: Optional[List[str]] = None) -> str:
        """Get contract status query with optional status filter"""
        base_query = ContractDataQueries.CONTRACT_STATUS_QUERY
        
        if status_filter and len(status_filter) > 0:
            # Create placeholders for each status
            status_placeholders = ','.join(['%s'] * len(status_filter))
            base_query += f" AND co_status IN ({status_placeholders})"
            print(f"DEBUG: Status filter query: {base_query}")
            print(f"DEBUG: Status filter values: {status_filter}")
        else:
            print("DEBUG: No status filter applied to query")
        
        return base_query
    
    @staticmethod
    def get_date_filtered_query(base_query: str, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> str:
        """Add date filtering to a query"""
        if start_date and end_date:
            base_query += " AND co.co_datesigned BETWEEN %s AND %s"
        elif start_date:
            base_query += " AND co.co_datesigned >= %s"
        elif end_date:
            base_query += " AND co.co_datesigned <= %s"
        
        return base_query

class DataTransformer:
    """Utility class for data transformation operations"""
    
    @staticmethod
    def pivot_contract_status_data(df: pd.DataFrame) -> pd.DataFrame:
        """Transform contract status data for display"""
        if df.empty:
            return pd.DataFrame()
        
        # Debug: Log before pivot
        print(f"DEBUG: Before pivot - shape: {df.shape}")
        print(f"DEBUG: Unique managers: {df['co_contractmanager'].nunique()}")
        print(f"DEBUG: Unique statuses: {df['co_status'].nunique()}")
        print(f"DEBUG: Sample data:\n{df.head()}")
        
        # Create pivot table
        pivot_df = df.pivot_table(
            index="co_contractmanager",
            columns="co_status",
            values="co_amount",
            aggfunc="sum",  # This should sum if there are multiple rows with same manager+status
            fill_value=0
        )
        
        # Debug: Log after pivot
        print(f"DEBUG: After pivot - shape: {pivot_df.shape}")
        print(f"DEBUG: Columns: {list(pivot_df.columns)}")
        print(f"DEBUG: Index: {list(pivot_df.index)}")
        print(f"DEBUG: Pivot sample:\n{pivot_df.head()}")
        
        return pivot_df
    
    @staticmethod
    def pivot_customer_data(df: pd.DataFrame) -> pd.DataFrame:
        """Transform customer contract data for display"""
        df['total_contract_value'] = pd.to_numeric(df['total_contract_value'], errors='coerce')
        
        return df.pivot_table(
            index="c_name",
            columns="contract_year",
            values="total_contract_value",
            aggfunc="sum",
            fill_value=0
        )
    
    @staticmethod
    def pivot_country_data(df: pd.DataFrame) -> pd.DataFrame:
        """Transform country contract data for display"""
        df['total_contract_value'] = df['total_contract_value'].astype(float)
        
        return df.pivot_table(
            index="contract_year",
            columns="country_name",
            values="total_contract_value",
            fill_value=0
        )
    
    @staticmethod
    def prepare_chart_data(df: pd.DataFrame, 
                          id_col: str, 
                          value_col: str, 
                          category_col: str) -> pd.DataFrame:
        """Prepare data for Altair charts"""
        return pd.melt(
            df.reset_index(),
            id_vars=id_col,
            var_name=category_col,
            value_name=value_col
        )
    
    @staticmethod
    def clean_numeric_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Clean and convert numeric columns"""
        df = df.copy()
        if column in df.columns:
            df[column] = (df[column]
                         .astype(str)
                         .str.replace(r'[$,]', '', regex=True)
                         .astype(float))
        return df
    
    @staticmethod
    def filter_by_amount_range(df: pd.DataFrame, 
                              amount_col: str, 
                              min_amount: float, 
                              max_amount: float) -> pd.DataFrame:
        """Filter dataframe by amount range"""
        return df[(df[amount_col] >= min_amount) & (df[amount_col] <= max_amount)]
    
    @staticmethod
    def format_currency(value: float) -> str:
        """Format value as currency"""
        return f"${value:,.2f}"
    
    @staticmethod
    def aggregate_by_group(df: pd.DataFrame, 
                          group_cols: List[str], 
                          agg_col: str, 
                          agg_func: str = 'sum') -> pd.DataFrame:
        """Aggregate dataframe by group columns"""
        return df.groupby(group_cols)[agg_col].agg(agg_func).reset_index()
