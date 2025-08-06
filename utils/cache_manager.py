"""
Advanced Cache Manager for Agiloft Analytics
Provides intelligent caching with filter-aware invalidation
"""

import hashlib
import json
import time
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import logging
from functools import wraps

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached entry with metadata"""
    data: Any
    created_at: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    ttl: Optional[float] = None
    tags: Set[str] = field(default_factory=set)
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def access(self):
        """Mark entry as accessed"""
        self.access_count += 1
        self.last_accessed = time.time()

@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_entries: int = 0
    total_size_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0

class SmartCacheManager:
    """
    Advanced cache manager with intelligent features:
    - Filter-aware cache keys
    - Hierarchical invalidation
    - LRU eviction with size limits
    - Query pattern optimization
    """
    
    def __init__(self, 
                 max_size_mb: int = 100,
                 default_ttl: int = 3600,  # 1 hour
                 max_entries: int = 1000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats()
        
        # Tag-based grouping for smart invalidation
        self._tag_map: Dict[str, Set[str]] = {}
        
        # Query pattern tracking
        self._query_patterns: Dict[str, int] = {}
        
    def _calculate_size(self, data: Any) -> int:
        """Estimate memory size of cached data"""
        try:
            if isinstance(data, pd.DataFrame):
                return data.memory_usage(deep=True).sum()
            elif isinstance(data, (dict, list)):
                return len(str(data).encode('utf-8'))
            else:
                return len(str(data).encode('utf-8'))
        except:
            return 1024  # Default fallback
    
    def _generate_cache_key(self, 
                          query_type: str,
                          filters: Dict[str, Any],
                          extra_params: Optional[Dict] = None) -> str:
        """Generate deterministic cache key from filters"""
        
        # Normalize filters for consistent hashing
        normalized_filters = self._normalize_filters(filters)
        
        # Create key components
        key_data = {
            "query_type": query_type,
            "filters": normalized_filters,
            "extra": extra_params or {}
        }
        
        # Generate hash
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _normalize_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize filters for consistent cache keys"""
        normalized = {}
        
        for key, value in filters.items():
            if isinstance(value, list):
                # Sort lists for consistent ordering
                normalized[key] = sorted(value) if value else []
            elif isinstance(value, tuple):
                # Sort tuples (for ranges)
                normalized[key] = tuple(sorted(value)) if len(value) == 2 else value
            elif isinstance(value, dict):
                # Recursively normalize nested dicts
                normalized[key] = self._normalize_filters(value)
            else:
                normalized[key] = value
        
        return normalized
    
    def _generate_tags(self, query_type: str, filters: Dict[str, Any]) -> Set[str]:
        """Generate tags for hierarchical cache invalidation"""
        tags = {f"query:{query_type}"}
        
        # Add filter-based tags
        for key, value in filters.items():
            if key == "selected_managers" and isinstance(value, list):
                tags.add("managers")
                # Add individual manager tags for fine-grained invalidation
                for manager in value[:5]:  # Limit to prevent tag explosion
                    tags.add(f"manager:{manager}")
            elif key == "selected_statuses" and isinstance(value, list):
                tags.add("statuses")
                for status in value:
                    tags.add(f"status:{status}")
            elif key == "amount_range":
                tags.add("amounts")
            elif key == "customer_range":
                tags.add("customers")
            elif key == "year_range":
                tags.add("years")
        
        return tags
    
    def _evict_lru(self):
        """Evict least recently used entries to free space"""
        with self._lock:
            if not self._cache:
                return
            
            # Sort by last accessed time
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            # Remove oldest entries until under limits
            entries_to_remove = []
            current_size = sum(entry.size_bytes for entry in self._cache.values())
            current_count = len(self._cache)
            
            for cache_key, entry in sorted_entries:
                if (current_size <= self.max_size_bytes and 
                    current_count <= self.max_entries):
                    break
                
                entries_to_remove.append(cache_key)
                current_size -= entry.size_bytes
                current_count -= 1
            
            # Remove entries
            for cache_key in entries_to_remove:
                self._remove_entry(cache_key)
                self._stats.evictions += 1
    
    def _remove_entry(self, cache_key: str):
        """Remove a single cache entry and update indexes"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            
            # Remove from tag map
            for tag in entry.tags:
                if tag in self._tag_map:
                    self._tag_map[tag].discard(cache_key)
                    if not self._tag_map[tag]:
                        del self._tag_map[tag]
            
            # Remove from cache
            del self._cache[cache_key]
            self._stats.total_entries -= 1
            self._stats.total_size_bytes -= entry.size_bytes
    
    def get(self, 
            query_type: str,
            filters: Dict[str, Any],
            extra_params: Optional[Dict] = None) -> Optional[Any]:
        """Get data from cache"""
        
        cache_key = self._generate_cache_key(query_type, filters, extra_params)
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                
                # Check expiration
                if entry.is_expired():
                    self._remove_entry(cache_key)
                    self._stats.misses += 1
                    return None
                
                # Update access statistics
                entry.access()
                self._stats.hits += 1
                
                logger.debug(f"Cache HIT for {query_type}: {cache_key[:8]}...")
                return entry.data
            
            self._stats.misses += 1
            logger.debug(f"Cache MISS for {query_type}: {cache_key[:8]}...")
            return None
    
    def put(self,
            query_type: str,
            filters: Dict[str, Any],
            data: Any,
            ttl: Optional[int] = None,
            extra_params: Optional[Dict] = None):
        """Store data in cache"""
        
        cache_key = self._generate_cache_key(query_type, filters, extra_params)
        tags = self._generate_tags(query_type, filters)
        size_bytes = self._calculate_size(data)
        
        with self._lock:
            # Create cache entry
            entry = CacheEntry(
                data=data,
                created_at=time.time(),
                ttl=ttl or self.default_ttl,
                tags=tags,
                size_bytes=size_bytes
            )
            
            # Update tag map
            for tag in tags:
                if tag not in self._tag_map:
                    self._tag_map[tag] = set()
                self._tag_map[tag].add(cache_key)
            
            # Store entry
            self._cache[cache_key] = entry
            self._stats.total_entries += 1
            self._stats.total_size_bytes += size_bytes
            
            # Track query patterns
            self._query_patterns[query_type] = self._query_patterns.get(query_type, 0) + 1
            
            logger.debug(f"Cache PUT for {query_type}: {cache_key[:8]}... ({size_bytes} bytes)")
            
            # Evict if necessary
            if (self._stats.total_size_bytes > self.max_size_bytes or 
                self._stats.total_entries > self.max_entries):
                self._evict_lru()
    
    def invalidate_by_tags(self, tags: Union[str, List[str]]):
        """Invalidate cache entries by tags"""
        if isinstance(tags, str):
            tags = [tags]
        
        with self._lock:
            keys_to_remove = set()
            
            for tag in tags:
                if tag in self._tag_map:
                    keys_to_remove.update(self._tag_map[tag])
            
            for cache_key in keys_to_remove:
                self._remove_entry(cache_key)
            
            if keys_to_remove:
                logger.info(f"Invalidated {len(keys_to_remove)} cache entries for tags: {tags}")
    
    def invalidate_managers(self, managers: List[str]):
        """Invalidate cache for specific managers"""
        tags = ["managers"] + [f"manager:{manager}" for manager in managers]
        self.invalidate_by_tags(tags)
    
    def invalidate_all(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._tag_map.clear()
            self._stats = CacheStats()
            logger.info("Cache cleared completely")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self._lock:
            # Calculate additional metrics
            if self._cache:
                avg_access_count = sum(e.access_count for e in self._cache.values()) / len(self._cache)
                oldest_entry = min(e.created_at for e in self._cache.values())
                newest_entry = max(e.created_at for e in self._cache.values())
            else:
                avg_access_count = 0
                oldest_entry = newest_entry = time.time()
            
            return {
                "basic_stats": {
                    "hits": self._stats.hits,
                    "misses": self._stats.misses,
                    "hit_rate": round(self._stats.hit_rate, 2),
                    "evictions": self._stats.evictions,
                    "total_entries": self._stats.total_entries,
                    "total_size_mb": round(self._stats.total_size_bytes / (1024*1024), 2),
                    "max_size_mb": round(self.max_size_bytes / (1024*1024), 2)
                },
                "performance": {
                    "avg_access_count": round(avg_access_count, 1),
                    "cache_age_hours": round((time.time() - oldest_entry) / 3600, 1),
                    "newest_entry_age_minutes": round((time.time() - newest_entry) / 60, 1)
                },
                "query_patterns": dict(sorted(self._query_patterns.items(), key=lambda x: x[1], reverse=True)),
                "tag_distribution": {tag: len(keys) for tag, keys in self._tag_map.items()},
                "recommendations": self._get_recommendations()
            }
    
    def _get_recommendations(self) -> List[str]:
        """Get cache optimization recommendations"""
        recommendations = []
        
        if self._stats.hit_rate < 30:
            recommendations.append("Low hit rate - consider increasing TTL or cache size")
        
        if self._stats.evictions > self._stats.hits * 0.1:
            recommendations.append("High eviction rate - consider increasing max_size_mb")
        
        if self._stats.total_entries > self.max_entries * 0.9:
            recommendations.append("Near entry limit - consider increasing max_entries")
        
        # Analyze query patterns
        total_queries = sum(self._query_patterns.values())
        if total_queries > 100:
            most_common = max(self._query_patterns.items(), key=lambda x: x[1])
            if most_common[1] > total_queries * 0.7:
                recommendations.append(f"Query '{most_common[0]}' dominates cache - consider optimizing")
        
        return recommendations

# Global cache instance
_cache_manager = None
_cache_lock = threading.Lock()

def get_cache_manager() -> SmartCacheManager:
    """Get singleton cache manager instance"""
    global _cache_manager
    
    if _cache_manager is None:
        with _cache_lock:
            if _cache_manager is None:
                # Try to import db_config, but use defaults if not available
                try:
                    from config.settings import db_config
                    _cache_manager = SmartCacheManager(
                        max_size_mb=db_config.CACHE_MAX_SIZE_MB,
                        default_ttl=db_config.CACHE_DEFAULT_TTL,
                        max_entries=db_config.CACHE_MAX_ENTRIES
                    )
                except ImportError:
                    # Fallback to defaults if config not available
                    _cache_manager = SmartCacheManager()
                
                logger.info("Initialized global cache manager")
    
    return _cache_manager

def cached_query(query_type: str, ttl: Optional[int] = None):
    """Decorator for caching database queries"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Extract filters from kwargs or args
            filters = kwargs.get('filters') or (args[1] if len(args) > 1 else {})
            extra_params = {k: v for k, v in kwargs.items() if k != 'filters'}
            
            # Try cache first
            cached_result = cache.get(query_type, filters, extra_params)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.put(query_type, filters, result, ttl, extra_params)
            
            return result
        return wrapper
    return decorator