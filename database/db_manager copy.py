"""
Database manager for SingleStore implementation - FIXED VERSION
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import singlestoredb as s2
from contextlib import contextmanager

from .db_interface import DatabaseInterface, ContractDataQueries, DataTransformer
from config.settings import app_config, db_config
from utils.exceptions import DatabaseConnectionError, QueryExecutionError

logger = logging.getLogger(__name__)

class DatabaseManager(DatabaseInterface):
    """SingleStore database manager implementation"""
    
    def __init__(self):
        self.connection = None
        self.connection_string = app_config.database_url
        self.queries = ContractDataQueries()
        self.transformer = DataTransformer()
        
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = s2.connect(
                self.connection_string,
                connect_timeout=db_config.CONNECTION_TIMEOUT
            )
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise DatabaseConnectionError(f"Failed to connect to database: {str(e)}")
    
    def disconnect(self) -> bool:
        """Close database connection"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
            logger.info("Database connection closed")
            return True
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute(self.queries.CONNECTION_TEST_QUERY)
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursors"""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    @contextmanager 
    def get_connection(self):
        """Context manager for database connections"""
        if not self.connection:
            self.connect()
        try:
            yield self.connection
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        max_retries = db_config.MAX_RETRIES
        retry_delay = db_config.RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                with self.get_cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    # Get column names
                    columns = [desc[0] for desc in cursor.description]
                    
                    # Fetch results
                    results = cursor.fetchall()
                    
                    # Create DataFrame
                    df = pd.DataFrame(results, columns=columns)
                    
                    logger.info(f"Query executed successfully, returned {len(df)} rows")
                    return df
                    
            except Exception as e:
                logger.error(f"Query execution failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise QueryExecutionError(f"Query execution failed after {max_retries} attempts: {str(e)}")
    
    def get_contract_status_data(self, 
                               contract_managers: List[str],
                               status_filter: Optional[List[str]] = None) -> pd.DataFrame:
        """Get individual contract records (NOT pre-aggregated) for proper amount filtering"""
        try:
            if not contract_managers:
                logger.warning("No contract managers provided")
                return pd.DataFrame()
            
            # FIXED: Use IN clause for specific managers and return individual records
            manager_placeholders = ','.join(['%s'] * len(contract_managers))
            
            # CRITICAL FIX: Return individual contract records, NOT aggregated sums
            query = f"""
                SELECT 
                    co_contractmanager,
                    co_status,
                    co_amount
                FROM contract 
                WHERE co_contractmanager IN ({manager_placeholders})
                    AND co_amount IS NOT NULL
                    AND co_amount > 0
                ORDER BY co_contractmanager, co_status, co_amount DESC
            """
            
            params = tuple(contract_managers)
            
            logger.info(f"Executing individual records query for {len(contract_managers)} managers")
            logger.info(f"Query: {query}")
            logger.info(f"Sample managers: {contract_managers[:3]}...")
            
            df = self.execute_query(query, params)
            
            if not df.empty:
                logger.info(f"Retrieved {len(df)} individual contract records")
                logger.info(f"Amount range in data: ${df['co_amount'].min():,.0f} - ${df['co_amount'].max():,.0f}")
                logger.info(f"Unique managers: {df['co_contractmanager'].nunique()}")
                logger.info(f"Unique statuses: {df['co_status'].nunique()}")
                logger.info(f"Sample amounts: {df['co_amount'].head(10).tolist()}")
                
                # Test the amount filtering that will happen in the UI
                test_filter = df[(df['co_amount'] >= 0) & (df['co_amount'] <= 150000)]
                logger.info(f"Records in $0-$150K range: {len(test_filter)} out of {len(df)} total")
                
                if len(test_filter) > 0:
                    logger.info(f"Sample records in $0-$150K range:")
                    logger.info(test_filter.head())
                
            else:
                logger.warning("No contract records found for the selected managers")
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting contract status data: {str(e)}")
            raise QueryExecutionError(f"Failed to get contract status data: {str(e)}")
    
    def get_customer_contract_data(self, 
                                 customer_range: Tuple[str, str] = ("Customer#000000001", "Customer#000000070"),
                                 year_range: Optional[Tuple[int, int]] = None) -> pd.DataFrame:
        """Get contract data grouped by customer"""
        try:
            # Default to last 10 years if no year range specified
            years_back = 10
            if year_range:
                years_back = year_range[1] - year_range[0] + 1
            
            params = (years_back, customer_range[0], customer_range[1])
            
            df = self.execute_query(self.queries.CUSTOMER_CONTRACT_QUERY, params)
            
            # Filter by year range if specified
            if year_range:
                df = df[
                    (df['contract_year'] >= year_range[0]) & 
                    (df['contract_year'] <= year_range[1])
                ]
            
            logger.info(f"Retrieved customer contract data: {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error getting customer contract data: {str(e)}")
            raise QueryExecutionError(f"Failed to get customer contract data: {str(e)}")
    
    def get_country_contract_data(self, 
                                customer_range: Tuple[str, str] = ("Customer#000000001", "Customer#000000070"),
                                year_range: Optional[Tuple[int, int]] = None) -> pd.DataFrame:
        """Get contract data grouped by country"""
        try:
            # Default to last 10 years if no year range specified
            years_back = 10
            if year_range:
                years_back = year_range[1] - year_range[0] + 1
            
            params = (years_back, customer_range[0], customer_range[1])
            
            df = self.execute_query(self.queries.COUNTRY_CONTRACT_QUERY, params)
            
            # Filter by year range if specified
            if year_range:
                df = df[
                    (df['contract_year'] >= year_range[0]) & 
                    (df['contract_year'] <= year_range[1])
                ]
            
            logger.info(f"Retrieved country contract data: {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error getting country contract data: {str(e)}")
            raise QueryExecutionError(f"Failed to get country contract data: {str(e)}")
    
    def get_contract_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for contracts"""
        try:
            summary_query = """
                SELECT 
                    COUNT(*) as total_contracts,
                    SUM(co_amount) as total_value,
                    AVG(co_amount) as avg_value,
                    MIN(co_amount) as min_value,
                    MAX(co_amount) as max_value,
                    COUNT(DISTINCT co_contractmanager) as total_managers,
                    COUNT(DISTINCT co_status) as total_statuses
                FROM contract
                WHERE co_amount IS NOT NULL AND co_amount > 0
            """
            
            df = self.execute_query(summary_query)
            
            if not df.empty:
                stats = df.iloc[0].to_dict()
                logger.info(f"Contract summary stats: {stats}")
                return stats
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting contract summary stats: {str(e)}")
            raise QueryExecutionError(f"Failed to get contract summary stats: {str(e)}")
    
    def get_available_contract_managers(self) -> List[str]:
        """Get list of available contract managers"""
        try:
            query = """
                SELECT DISTINCT co_contractmanager 
                FROM contract 
                WHERE co_contractmanager IS NOT NULL
                    AND co_contractmanager != ''
                ORDER BY co_contractmanager
                LIMIT 1000
            """
            
            df = self.execute_query(query)
            managers = df['co_contractmanager'].tolist()
            logger.info(f"Retrieved {len(managers)} contract managers")
            return managers
            
        except Exception as e:
            logger.error(f"Error getting contract managers: {str(e)}")
            raise QueryExecutionError(f"Failed to get contract managers: {str(e)}")
    
    def get_available_statuses(self) -> List[str]:
        """Get list of available contract statuses"""
        try:
            query = """
                SELECT DISTINCT co_status 
                FROM contract 
                WHERE co_status IS NOT NULL
                    AND co_status != ''
                ORDER BY co_status
            """
            
            df = self.execute_query(query)
            statuses = df['co_status'].tolist()
            logger.info(f"Retrieved {len(statuses)} contract statuses")
            return statuses
            
        except Exception as e:
            logger.error(f"Error getting contract statuses: {str(e)}")
            raise QueryExecutionError(f"Failed to get contract statuses: {str(e)}")
    
    def get_manager_statistics(self, managers_list: List[str] = None) -> pd.DataFrame:
        """Get comprehensive statistics for contract managers"""
        try:
            # Build WHERE clause for specific managers if provided
            where_clause = ""
            params = []
            
            if managers_list:
                manager_placeholders = ','.join(['%s'] * len(managers_list))
                where_clause = f"WHERE co_contractmanager IN ({manager_placeholders})"
                params = managers_list
            
            query = f"""
            SELECT 
                co_contractmanager as manager_name,
                COUNT(*) as total_contracts,
                SUM(co_amount) as total_value,
                AVG(co_amount) as avg_value,
                MAX(co_datesigned) as last_contract_date,
                CASE 
                    WHEN MAX(co_datesigned) >= DATE_SUB(NOW(), INTERVAL 12 MONTH) 
                    THEN 1 
                    ELSE 0 
                END as recent_activity
            FROM contract 
            {where_clause}
            AND co_amount IS NOT NULL AND co_amount > 0
            GROUP BY co_contractmanager
            ORDER BY total_value DESC
            """
            
            logger.info(f"Getting manager statistics{' for specific managers' if managers_list else ' for all managers'}")
            
            df = self.execute_query(query, tuple(params) if params else None)
            
            if not df.empty:
                # Convert data types
                df['total_contracts'] = df['total_contracts'].astype(int)
                df['total_value'] = pd.to_numeric(df['total_value'], errors='coerce').fillna(0)
                df['avg_value'] = pd.to_numeric(df['avg_value'], errors='coerce').fillna(0)
                df['recent_activity'] = df['recent_activity'].astype(bool)
                df['last_contract_date'] = pd.to_datetime(df['last_contract_date'], errors='coerce')
                
                logger.info(f"Retrieved statistics for {len(df)} managers")
            
            return df
                
        except Exception as e:
            logger.error(f"Error getting manager statistics: {str(e)}")
            # Return empty DataFrame with expected columns on error
            return pd.DataFrame(columns=[
                'manager_name', 'total_contracts', 'total_value', 
                'avg_value', 'recent_activity', 'last_contract_date'
            ])
    
    def get_top_managers_by_activity(self, limit: int = 20) -> List[str]:
        """Get list of top managers by contract activity"""
        try:
            query = f"""
            SELECT 
                co_contractmanager,
                COUNT(*) as contract_count,
                SUM(co_amount) as total_value,
                (COUNT(*) * 0.3 + (SUM(co_amount) / 1000000) * 0.7) as activity_score
            FROM contract 
            WHERE co_contractmanager IS NOT NULL 
                AND co_contractmanager != ''
                AND co_amount > 0
            GROUP BY co_contractmanager
            HAVING contract_count > 0
            ORDER BY activity_score DESC
            LIMIT {limit}
            """
            
            df = self.execute_query(query)
            managers = df['co_contractmanager'].tolist()
            logger.info(f"Retrieved top {len(managers)} managers by activity")
            return managers
                
        except Exception as e:
            logger.error(f"Error getting top managers: {str(e)}")
            # Fallback to basic manager list
            managers = self.get_available_contract_managers()
            return managers[:limit] if managers else []
    
    def get_manager_quick_stats(self, manager_name: str) -> Dict[str, Any]:
        """Get quick statistics for a single manager"""
        try:
            query = """
            SELECT 
                COUNT(*) as contract_count,
                SUM(co_amount) as total_value,
                COUNT(DISTINCT co_status) as status_count,
                MAX(co_datesigned) as last_contract
            FROM contract 
            WHERE co_contractmanager = %s
                AND co_amount IS NOT NULL 
                AND co_amount > 0
            """
            
            df = self.execute_query(query, (manager_name,))
            
            if not df.empty:
                result = df.iloc[0]
                return {
                    'contract_count': int(result['contract_count'] or 0),
                    'total_value': float(result['total_value'] or 0),
                    'status_count': int(result['status_count'] or 0),
                    'last_contract': result['last_contract']
                }
            else:
                return {
                    'contract_count': 0,
                    'total_value': 0,
                    'status_count': 0,
                    'last_contract': None
                }
                
        except Exception as e:
            logger.error(f"Error getting quick stats for manager {manager_name}: {str(e)}")
            return {
                'contract_count': 0,
                'total_value': 0,
                'status_count': 0,
                'last_contract': None
            }
    
    def debug_amount_ranges(self) -> Dict[str, Any]:
        """Debug method to understand amount distribution"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_records,
                MIN(co_amount) as min_amount,
                MAX(co_amount) as max_amount,
                AVG(co_amount) as avg_amount,
                SUM(CASE WHEN co_amount <= 150000 THEN 1 ELSE 0 END) as under_150k,
                SUM(CASE WHEN co_amount BETWEEN 0 AND 50000 THEN 1 ELSE 0 END) as under_50k,
                SUM(CASE WHEN co_amount BETWEEN 50001 AND 150000 THEN 1 ELSE 0 END) as between_50k_150k,
                SUM(CASE WHEN co_amount > 150000 THEN 1 ELSE 0 END) as over_150k
            FROM contract 
            WHERE co_amount IS NOT NULL AND co_amount > 0
            """
            
            df = self.execute_query(query)
            
            if not df.empty:
                result = df.iloc[0].to_dict()
                logger.info(f"Amount distribution analysis: {result}")
                return result
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error in amount range debug: {str(e)}")
            return {}
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()