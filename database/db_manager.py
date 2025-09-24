"""
Database manager for SingleStore implementation with connection pooling
"""

import logging
import time
import threading
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import singlestoredb as s2
from contextlib import contextmanager
from queue import Queue, Empty
from dataclasses import dataclass

from .db_interface import DatabaseInterface, ContractDataQueries, DataTransformer
from config.settings import app_config, db_config
from utils.exceptions import DatabaseConnectionError, QueryExecutionError
from utils.cache_manager import get_cache_manager, cached_query

logger = logging.getLogger(__name__)

@dataclass
class PoolStats:
    """Statistics for connection pool monitoring"""
    created_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    
class ConnectionPool:
    """Thread-safe connection pool for SingleStore database"""
    
    def __init__(self, connection_string: str, pool_size: int = 5, max_overflow: int = 10):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.max_connections = pool_size + max_overflow
        
        # Thread-safe queue for available connections
        self._pool = Queue(maxsize=self.max_connections)
        self._lock = threading.RLock()
        self._created_connections = 0
        self._stats = PoolStats()
        
        # Pre-populate pool with initial connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the pool with core connections"""
        try:
            for _ in range(self.pool_size):
                conn = self._create_connection()
                if conn:
                    self._pool.put(conn, block=False)
        except Exception as e:
            logger.error(f"Error initializing connection pool: {e}")
    
    def _create_connection(self):
        """Create a new database connection"""
        try:
            conn = s2.connect(
                self.connection_string,
                connect_timeout=db_config.CONNECTION_TIMEOUT,
                charset='utf8mb4',
                autocommit=True
            )
            
            with self._lock:
                self._created_connections += 1
                self._stats.created_connections += 1
            
            logger.debug(f"Created new connection (total: {self._created_connections})")
            return conn
            
        except Exception as e:
            with self._lock:
                self._stats.failed_connections += 1
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def _validate_connection(self, conn) -> bool:
        """Validate that a connection is still usable"""
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception as e:
            logger.debug(f"Connection validation failed: {e}")
            return False
    
    def get_connection(self, timeout: float = 5.0):
        """Get a connection from the pool"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to get an existing connection
                conn = self._pool.get(block=False)
                
                # Validate the connection if pre-ping is enabled
                if db_config.POOL_PRE_PING:
                    if self._validate_connection(conn):
                        with self._lock:
                            self._stats.active_connections += 1
                        return conn
                    else:
                        # Connection is invalid, close it and try again
                        try:
                            conn.close()
                        except:
                            pass
                        with self._lock:
                            self._created_connections -= 1
                        continue
                else:
                    with self._lock:
                        self._stats.active_connections += 1
                    return conn
                    
            except Empty:
                # No connections available, try to create a new one
                with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = self._create_connection()
                        if conn:
                            self._stats.active_connections += 1
                            return conn
                
                # Wait a bit before retrying
                time.sleep(0.1)
        
        raise DatabaseConnectionError(f"Could not get connection within {timeout} seconds")
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        try:
            # Reset connection state if configured
            if db_config.POOL_RESET_ON_RETURN == "commit":
                conn.commit()
            elif db_config.POOL_RESET_ON_RETURN == "rollback":
                conn.rollback()
            
            # Return to pool if there's space
            try:
                self._pool.put(conn, block=False)
                with self._lock:
                    self._stats.active_connections -= 1
                    self._stats.idle_connections += 1
            except:
                # Pool is full, close the connection
                conn.close()
                with self._lock:
                    self._created_connections -= 1
                    self._stats.active_connections -= 1
                    
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            try:
                conn.close()
            except:
                pass
            with self._lock:
                self._created_connections -= 1
                self._stats.active_connections -= 1
    
    def close_all(self):
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                conn.close()
            except:
                pass
        
        with self._lock:
            self._created_connections = 0
            self._stats = PoolStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                "pool_size": self.pool_size,
                "max_connections": self.max_connections,
                "created_connections": self._created_connections,
                "active_connections": self._stats.active_connections,
                "idle_connections": self._pool.qsize(),
                "failed_connections": self._stats.failed_connections,
                "total_queries": self._stats.total_queries
            }

class DatabaseManager(DatabaseInterface):
    """SingleStore database manager implementation with connection pooling"""
    
    _pool = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.connection_string = app_config.database_url
        self.queries = ContractDataQueries()
        self.transformer = DataTransformer()
        
        # Initialize connection pool (singleton pattern)
        with DatabaseManager._lock:
            if DatabaseManager._pool is None:
                DatabaseManager._pool = ConnectionPool(
                    connection_string=self.connection_string,
                    pool_size=db_config.POOL_SIZE,
                    max_overflow=db_config.MAX_OVERFLOW
                )
                logger.info(f"Initialized connection pool with {db_config.POOL_SIZE} connections")
    
    @property
    def pool(self) -> ConnectionPool:
        """Get the connection pool instance"""
        return DatabaseManager._pool
        
    def connect(self) -> bool:
        """Test that connection pool is working"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            logger.info("Database connection pool is working")
            return True
        except Exception as e:
            logger.error(f"Database connection pool test failed: {str(e)}")
            raise DatabaseConnectionError(f"Failed to connect to database: {str(e)}")
    
    def disconnect(self) -> bool:
        """Close all connections in the pool"""
        try:
            if self.pool:
                self.pool.close_all()
                logger.info("All database connections closed")
            return True
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test database connection from pool"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(self.queries.CONNECTION_TEST_QUERY)
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections from pool"""
        conn = None
        try:
            conn = self.pool.get_connection(timeout=db_config.CONNECTION_TIMEOUT)
            yield conn
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise
        finally:
            if conn:
                self.pool.return_connection(conn)
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursors using pooled connections"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame using connection pool"""
        max_retries = db_config.MAX_RETRIES
        retry_delay = db_config.RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                with self.get_cursor() as cursor:
                    # Track query execution in pool stats
                    with self.pool._lock:
                        self.pool._stats.total_queries += 1
                    
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
        """Get individual contract records with intelligent caching"""
        try:
            if not contract_managers:
                logger.warning("No contract managers provided")
                return pd.DataFrame()
            
            # Create cache-friendly filters
            filters = {
                "selected_managers": contract_managers,
                "selected_statuses": status_filter or []
            }
            
            # Try cache first
            cache = get_cache_manager()
            cached_result = cache.get("contract_status_data", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached contract records")
                return cached_result
            
            # Cache miss - execute query
            logger.info(f"Cache MISS: Executing query for {len(contract_managers)} managers")
            
            # FIXED: Use IN clause for specific managers and return individual records
            manager_placeholders = ','.join(['%s'] * len(contract_managers))
            
            # ENHANCED: Include manager names via LEFT JOIN with employee table
            # Using LEFT JOIN ensures we get data even if manager name is missing
            query = f"""
                SELECT 
                    c.co_contractmanager,
                    COALESCE(e.e_name, c.co_contractmanager) as manager_name,
                    c.co_status,
                    c.co_amount
                FROM contract c
                LEFT JOIN employee e ON c.co_contractmanager = e.e_empkey
                WHERE c.co_contractmanager IN ({manager_placeholders})
                    AND c.co_amount IS NOT NULL
                    AND c.co_amount > 0
                ORDER BY c.co_contractmanager, c.co_status, c.co_amount DESC
            """
            
            params = tuple(contract_managers)
            
            logger.info(f"Query: {query}")
            logger.info(f"Sample managers: {contract_managers[:3]}...")
            
            df = self.execute_query(query, params)
            
            if not df.empty:
                logger.info(f"Retrieved {len(df)} individual contract records")
                logger.info(f"Amount range in data: ${df['co_amount'].min():,.0f} - ${df['co_amount'].max():,.0f}")
                logger.info(f"Unique managers: {df['co_contractmanager'].nunique()}")
                logger.info(f"Unique statuses: {df['co_status'].nunique()}")
                
                # Cache the result with appropriate TTL
                ttl = db_config.CACHE_TTL_DYNAMIC_QUERIES if len(contract_managers) <= 10 else db_config.CACHE_TTL_CONTRACT_DATA
                cache.put("contract_status_data", filters, df, ttl=ttl)
                logger.info(f"Cached contract status data for {len(contract_managers)} managers")
                
            else:
                logger.warning("No contract records found for the selected managers")
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting contract status data: {str(e)}")
            raise QueryExecutionError(f"Failed to get contract status data: {str(e)}")
    
    def get_customer_contract_data(self,
                                 selected_customers: List[str],
                                 year_range: Optional[Tuple[int, int]] = None) -> pd.DataFrame:
        """Get contract data grouped by customer with caching"""
        try:
            if not selected_customers:
                logger.warning("No customers provided")
                return pd.DataFrame()

            # Create cache filters
            filters = {
                "selected_customers": selected_customers,
                "year_range": year_range
            }

            # Try cache first
            cache = get_cache_manager()
            cached_result = cache.get("customer_contract_data", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached customer records")
                return cached_result

            # Cache miss - execute query
            logger.info(f"Cache MISS: Executing customer contract query for {len(selected_customers)} customers")

            # Default to last 10 years if no year range specified
            years_back = 10
            if year_range:
                years_back = year_range[1] - year_range[0] + 1

            # Create placeholders for customer names
            customer_placeholders = ','.join(['%s'] * len(selected_customers))
            query = self.queries.CUSTOMER_CONTRACT_QUERY.format(customer_placeholders=customer_placeholders)

            # Parameters: years_back, then all customer names
            params = (years_back,) + tuple(selected_customers)

            df = self.execute_query(query, params)

            # Filter by year range if specified
            if year_range:
                df = df[
                    (df['contract_year'] >= year_range[0]) &
                    (df['contract_year'] <= year_range[1])
                ]

            logger.info(f"Retrieved customer contract data: {len(df)} records for {len(selected_customers)} customers")

            # Cache the result
            ttl = db_config.CACHE_TTL_DYNAMIC_QUERIES if len(selected_customers) <= 10 else db_config.CACHE_TTL_CONTRACT_DATA
            cache.put("customer_contract_data", filters, df, ttl=ttl)

            return df

        except Exception as e:
            logger.error(f"Error getting customer contract data: {str(e)}")
            raise QueryExecutionError(f"Failed to get customer contract data: {str(e)}")
    
    def get_country_contract_data(self,
                                selected_customers: List[str],
                                year_range: Optional[Tuple[int, int]] = None) -> pd.DataFrame:
        """Get contract data grouped by country with caching"""
        try:
            if not selected_customers:
                logger.warning("No customers provided")
                return pd.DataFrame()

            # Create cache filters
            filters = {
                "selected_customers": selected_customers,
                "year_range": year_range
            }

            # Try cache first
            cache = get_cache_manager()
            cached_result = cache.get("country_contract_data", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached country records")
                return cached_result

            # Cache miss - execute query
            logger.info(f"Cache MISS: Executing country contract query for {len(selected_customers)} customers")

            # Default to last 10 years if no year range specified
            years_back = 10
            if year_range:
                years_back = year_range[1] - year_range[0] + 1

            # Create placeholders for customer names
            customer_placeholders = ','.join(['%s'] * len(selected_customers))
            query = self.queries.COUNTRY_CONTRACT_QUERY.format(customer_placeholders=customer_placeholders)

            # Parameters: years_back, then all customer names
            params = (years_back,) + tuple(selected_customers)

            df = self.execute_query(query, params)

            # Filter by year range if specified
            if year_range:
                df = df[
                    (df['contract_year'] >= year_range[0]) &
                    (df['contract_year'] <= year_range[1])
                ]

            logger.info(f"Retrieved country contract data: {len(df)} records for {len(selected_customers)} customers")

            # Cache the result
            ttl = db_config.CACHE_TTL_DYNAMIC_QUERIES if len(selected_customers) <= 10 else db_config.CACHE_TTL_CONTRACT_DATA
            cache.put("country_contract_data", filters, df, ttl=ttl)

            return df

        except Exception as e:
            logger.error(f"Error getting country contract data: {str(e)}")
            raise QueryExecutionError(f"Failed to get country contract data: {str(e)}")
    
    def get_contract_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for contracts with caching"""
        try:
            # Create cache filters for summary stats
            filters = {"query": "summary_stats"}
            
            # Try cache first
            cache = get_cache_manager()
            cached_result = cache.get("contract_summary_stats", filters)
            if cached_result is not None:
                logger.info("Cache HIT: Retrieved cached contract summary stats")
                return cached_result
            
            # Cache miss - execute query
            logger.info("Cache MISS: Executing contract summary stats query")
            
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
                
                # Cache summary stats
                cache.put("contract_summary_stats", filters, stats, ttl=db_config.CACHE_TTL_SUMMARY_STATS)
                
                logger.info(f"Contract summary stats retrieved and cached: {stats}")
                return stats
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting contract summary stats: {str(e)}")
            raise QueryExecutionError(f"Failed to get contract summary stats: {str(e)}")
    
    def get_available_contract_managers(self) -> List[str]:
        """Get list of available contract managers with long-term caching"""
        try:
            # Static data - cache for longer period
            filters = {"query": "all_managers"}
            
            cache = get_cache_manager()
            cached_result = cache.get("available_managers", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached managers")
                return cached_result
            
            logger.info("Cache MISS: Fetching available contract managers")
            
            # ENHANCED: Get both manager IDs and names for better UI experience
            query = """
                SELECT 
                    e_empkey,
                    COALESCE(e_name, e_empkey) as manager_name
                FROM employee 
                ORDER BY COALESCE(e_name, e_empkey)
                LIMIT 1000
            """
            
            df = self.execute_query(query)
            # For backward compatibility, still return list of IDs
            # But store the full mapping for future use
            managers = df['e_empkey'].tolist()
            
            # Store manager name mapping for potential future use
            # Note: The main mapping is cached separately via get_manager_name_mapping()
            self._last_manager_mapping = dict(zip(df['e_empkey'], df['manager_name']))
            
            # Cache static data
            cache.put("available_managers", filters, managers, ttl=db_config.CACHE_TTL_STATIC_DATA)
            
            logger.info(f"Retrieved and cached {len(managers)} contract managers")
            return managers

        except Exception as e:
            logger.error(f"Error getting contract managers: {str(e)}")
            raise QueryExecutionError(f"Failed to get contract managers: {str(e)}")

    def get_available_customers(self) -> List[str]:
        """Get list of available customers with long-term caching"""
        try:
            # Static data - cache for longer period
            filters = {"query": "all_customers"}

            cache = get_cache_manager()
            cached_result = cache.get("available_customers", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached customers")
                return cached_result

            logger.info("Cache MISS: Fetching available customers")

            # Get customers with contracts only
            query = """
                SELECT DISTINCT c.c_name
                FROM customer c
                INNER JOIN contract co ON c.c_custkey = co.co_custkey
                WHERE c.c_name IS NOT NULL
                    AND c.c_name != ''
                    AND co.co_amount IS NOT NULL
                    AND co.co_amount > 0
                ORDER BY c.c_name
                LIMIT 1000
            """

            df = self.execute_query(query)
            customers = df['c_name'].tolist()

            # Cache static data
            cache.put("available_customers", filters, customers, ttl=db_config.CACHE_TTL_STATIC_DATA)

            logger.info(f"Retrieved and cached {len(customers)} customers with contracts")
            return customers

        except Exception as e:
            logger.error(f"Error getting available customers: {str(e)}")
            raise QueryExecutionError(f"Failed to get available customers: {str(e)}")

    def get_customer_mapping(self) -> Dict[str, str]:
        """Get mapping of customer keys to customer names"""
        try:
            filters = {"query": "customer_mapping"}

            cache = get_cache_manager()
            cached_result = cache.get("customer_mapping", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved customer mapping for {len(cached_result)} customers")
                return cached_result

            logger.info("Cache MISS: Fetching customer mapping")

            query = """
                SELECT DISTINCT c.c_custkey, c.c_name
                FROM customer c
                INNER JOIN contract co ON c.c_custkey = co.co_custkey
                WHERE c.c_name IS NOT NULL
                    AND c.c_name != ''
                    AND co.co_amount IS NOT NULL
                    AND co.co_amount > 0
                ORDER BY c.c_name
                LIMIT 1000
            """

            df = self.execute_query(query)
            mapping = dict(zip(df['c_custkey'], df['c_name']))

            # Cache static data
            cache.put("customer_mapping", filters, mapping, ttl=db_config.CACHE_TTL_STATIC_DATA)

            logger.info(f"Retrieved and cached customer mapping for {len(mapping)} customers")
            return mapping

        except Exception as e:
            logger.error(f"Error getting customer mapping: {str(e)}")
            raise QueryExecutionError(f"Failed to get customer mapping: {str(e)}")

    def get_manager_name_mapping(self) -> Dict[str, str]:
        """Get mapping of manager IDs to manager names with caching"""
        try:
            # Check for cached mapping
            filters = {"query": "manager_name_mapping"}
            
            cache = get_cache_manager()
            cached_result = cache.get("manager_name_mapping", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached manager name mappings")
                return cached_result
            
            logger.info("Cache MISS: Fetching manager name mappings")
            
            # Get manager ID to name mapping
            query = """
                SELECT 
                    e_empkey,
                    COALESCE(e_name, e_empkey) as manager_name
                FROM employee 
                ORDER BY e_empkey
            """
            
            df = self.execute_query(query)
            mapping = dict(zip(df['e_empkey'], df['manager_name']))
            
            # Cache the mapping with static data TTL
            cache.put("manager_name_mapping", filters, mapping, ttl=db_config.CACHE_TTL_STATIC_DATA)
            
            logger.info(f"Retrieved and cached {len(mapping)} manager name mappings")
            return mapping
            
        except Exception as e:
            logger.error(f"Error getting manager name mapping: {str(e)}")
            # Return empty mapping on error
            return {}
    
    def get_available_statuses(self) -> List[str]:
        """Get list of available contract statuses with caching"""
        try:
            # Static data - cache for longer period
            filters = {"query": "all_statuses"}
            
            cache = get_cache_manager()
            cached_result = cache.get("available_statuses", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached statuses")
                return cached_result
            
            logger.info("Cache MISS: Fetching available contract statuses")
            
            query = """
                SELECT DISTINCT co_status 
                FROM contract 
                ORDER BY co_status
            """
            
            df = self.execute_query(query)
            statuses = df['co_status'].tolist()
            
            # Cache static data
            cache.put("available_statuses", filters, statuses, ttl=db_config.CACHE_TTL_STATIC_DATA)
            
            logger.info(f"Retrieved and cached {len(statuses)} contract statuses")
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
        """
        Get list of top managers by contract activity with caching.
        
        OPTIMIZED QUERY: Uses INNER JOIN with employee table for 33% performance improvement.
        - Original query: ~59 seconds (filtering 150M rows with string operations)  
        - Optimized query: ~40 seconds (leveraging employee table hash index)
        
        Performance improvements:
        1. Employee table acts as efficient filter (100K valid managers vs 150M contract rows)
        2. Eliminates expensive string filtering (IS NOT NULL, != '')  
        3. Leverages hash index on employee.e_empkey for fast lookups
        4. Uses hash join instead of shuffle operations
        """
        try:
            # Cache top managers queries since they're expensive but relatively stable
            filters = {"limit": limit}
            
            cache = get_cache_manager()
            cached_result = cache.get("top_managers_by_activity", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached top managers")
                return cached_result
            
            logger.info(f"Cache MISS: Fetching top {limit} managers by activity (optimized with employee join)")
            
            # OPTIMIZED QUERY: Uses INNER JOIN with employee table for 33% performance improvement
            # This leverages the hash index on employee.e_empkey (primary key) to efficiently 
            # filter valid contract managers, reducing query time from ~59s to ~40s
            query = f"""
            SELECT 
                c.co_contractmanager,
                COUNT(*) as contract_count,
                SUM(c.co_amount) as total_value,
                (COUNT(*) * 0.3 + (SUM(c.co_amount) / 1000000) * 0.7) as activity_score
            FROM contract c
            INNER JOIN employee e ON c.co_contractmanager = e.e_empkey
            WHERE c.co_amount > 0
            GROUP BY c.co_contractmanager
            ORDER BY activity_score DESC
            LIMIT {limit}
            """
            
            df = self.execute_query(query)
            managers = df['co_contractmanager'].tolist()
            
            # Cache summary stats (rankings change slowly)
            cache.put("top_managers_by_activity", filters, managers, ttl=db_config.CACHE_TTL_SUMMARY_STATS)
            
            logger.info(f"Retrieved and cached top {len(managers)} managers by activity (optimized query)")
            return managers
                
        except Exception as e:
            logger.error(f"Error getting top managers: {str(e)}")
            # Fallback to basic manager list
            managers = self.get_available_contract_managers()
            return managers[:limit] if managers else []

    def get_top_managers_by_activity_with_names(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Enhanced version: Get top managers by activity with employee names included.
        
        Returns list of dictionaries with manager details including names for better UI display.
        Uses same optimized INNER JOIN query as get_top_managers_by_activity() for performance.
        
        Returns:
            List[Dict]: Each dict contains:
                - co_contractmanager: Manager ID (string)
                - manager_name: Employee name (string) 
                - contract_count: Number of contracts (int)
                - total_value: Total contract value (float)
                - activity_score: Calculated activity score (float)
        """
        try:
            # Cache with different key since this returns different data structure
            filters = {"limit": limit, "include_names": True}
            
            cache = get_cache_manager()
            cached_result = cache.get("top_managers_by_activity_with_names", filters)
            if cached_result is not None:
                logger.info(f"Cache HIT: Retrieved {len(cached_result)} cached top managers with names")
                return cached_result
            
            logger.info(f"Cache MISS: Fetching top {limit} managers by activity with names (optimized)")
            
            # Enhanced query with employee names - same performance optimization as base method
            query = f"""
            SELECT 
                c.co_contractmanager,
                COALESCE(e.e_name, c.co_contractmanager) as manager_name,
                COUNT(*) as contract_count,
                SUM(c.co_amount) as total_value,
                (COUNT(*) * 0.3 + (SUM(c.co_amount) / 1000000) * 0.7) as activity_score
            FROM contract c
            INNER JOIN employee e ON c.co_contractmanager = e.e_empkey
            WHERE c.co_amount > 0
            GROUP BY c.co_contractmanager, e.e_name
            ORDER BY activity_score DESC
            LIMIT {limit}
            """
            
            df = self.execute_query(query)
            
            # Convert to list of dictionaries for easier consumption
            managers_with_names = df.to_dict('records')
            
            # Cache the enhanced results
            cache.put("top_managers_by_activity_with_names", filters, managers_with_names, ttl=db_config.CACHE_TTL_SUMMARY_STATS)
            
            logger.info(f"Retrieved and cached top {len(managers_with_names)} managers with names (optimized query)")
            return managers_with_names
                
        except Exception as e:
            logger.error(f"Error getting top managers with names: {str(e)}")
            # Fallback to basic method and convert format
            try:
                basic_managers = self.get_top_managers_by_activity(limit)
                return [{"co_contractmanager": mgr, "manager_name": mgr} for mgr in basic_managers]
            except:
                return []
    
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
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics for monitoring"""
        if self.pool:
            return self.pool.get_stats()
        return {}
    
    def get_pool_health(self) -> Dict[str, Any]:
        """Get connection pool health information"""
        stats = self.get_pool_stats()
        
        if not stats:
            return {"status": "no_pool", "health": "unhealthy"}
        
        # Calculate health metrics
        total_possible = stats.get("max_connections", 0)
        active = stats.get("active_connections", 0)
        failed = stats.get("failed_connections", 0)
        created = stats.get("created_connections", 0)
        
        # Health indicators
        utilization = (active / total_possible) * 100 if total_possible > 0 else 0
        failure_rate = (failed / max(created, 1)) * 100
        
        # Determine overall health
        if failure_rate > 10:
            health = "unhealthy"
        elif utilization > 90:
            health = "overloaded" 
        elif utilization > 70:
            health = "busy"
        else:
            health = "healthy"
        
        return {
            "status": "active",
            "health": health,
            "utilization_percent": round(utilization, 1),
            "failure_rate_percent": round(failure_rate, 1),
            "stats": stats,
            "recommendations": self._get_pool_recommendations(stats, utilization, failure_rate)
        }
    
    def _get_pool_recommendations(self, stats: Dict, utilization: float, failure_rate: float) -> List[str]:
        """Get recommendations for pool optimization"""
        recommendations = []
        
        if failure_rate > 10:
            recommendations.append("High failure rate detected - check database connectivity")
        
        if utilization > 90:
            recommendations.append(f"Pool utilization is {utilization:.1f}% - consider increasing pool size")
        
        if stats.get("active_connections", 0) == stats.get("max_connections", 0):
            recommendations.append("Pool is at maximum capacity - consider increasing max_overflow")
        
        if stats.get("total_queries", 0) > 1000 and utilization < 30:
            recommendations.append("Low utilization with high query count - pool may be oversized")
        
        return recommendations
    
    # Cache Management Methods
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        cache = get_cache_manager()
        return cache.get_stats()
    
    def invalidate_cache(self, tags: Optional[List[str]] = None):
        """Invalidate cache entries by tags or clear all"""
        cache = get_cache_manager()
        
        if tags:
            cache.invalidate_by_tags(tags)
            logger.info(f"Invalidated cache for tags: {tags}")
        else:
            cache.invalidate_all()
            logger.info("Cleared all cache entries")
    
    def invalidate_manager_cache(self, managers: List[str]):
        """Invalidate cache for specific managers"""
        cache = get_cache_manager()
        cache.invalidate_managers(managers)
        logger.info(f"Invalidated cache for {len(managers)} managers")
    
    def warm_cache(self, manager_limit: int = 20):
        """Pre-populate cache with common queries"""
        logger.info("Starting cache warm-up...")
        
        try:
            # Warm up managers list
            self.get_available_contract_managers()
            
            # Warm up manager name mapping
            self.get_manager_name_mapping()
            
            # Warm up top managers
            self.get_top_managers_by_activity(limit=manager_limit)
            
            # Warm up statuses
            self.get_available_statuses()
            
            # Warm up summary stats
            self.get_contract_summary_stats()
            
            logger.info("Cache warm-up completed successfully")
            
        except Exception as e:
            logger.error(f"Cache warm-up failed: {e}")
    
    def get_combined_health(self) -> Dict[str, Any]:
        """Get combined health status for both pool and cache"""
        pool_health = self.get_pool_health()
        cache_stats = self.get_cache_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "pool": pool_health,
            "cache": cache_stats,
            "overall_status": "healthy" if (
                pool_health.get("health") == "healthy" and 
                cache_stats.get("basic_stats", {}).get("hit_rate", 0) > 20
            ) else "needs_attention"
        }