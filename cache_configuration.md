# Cache Configuration Guide

## 📍 **Where to Find Cache Durations**

All cache duration settings are now centralized in one place:

**File:** `config/settings.py`  
**Section:** `DatabaseConfig` class, lines 90-94

```python
# Cache TTL settings for different data types (in seconds)
CACHE_TTL_STATIC_DATA: int = 14400      # 4 hours - rarely changing data (managers, statuses)
CACHE_TTL_SUMMARY_STATS: int = 7200     # 2 hours - aggregate statistics
CACHE_TTL_CONTRACT_DATA: int = 3600     # 1 hour - individual contract records
CACHE_TTL_DYNAMIC_QUERIES: int = 1800   # 30 minutes - frequently changing data
```

## 🕐 **Current Cache Duration Settings**

| Data Type | Duration | Used For |
|-----------|----------|----------|
| **CACHE_TTL_STATIC_DATA** | 4 hours (14400s) | • Available managers list<br>• Available statuses list |
| **CACHE_TTL_SUMMARY_STATS** | 2 hours (7200s) | • Contract summary statistics<br>• Top managers by activity |
| **CACHE_TTL_CONTRACT_DATA** | 1 hour (3600s) | • Individual contract records<br>• Customer contract data |
| **CACHE_TTL_DYNAMIC_QUERIES** | 30 minutes (1800s) | • Small/frequent queries<br>• Real-time data |

## 🔧 **How to Update Cache Durations**

### **1. Edit the Configuration File**
Open `config/settings.py` and modify the values:

```python
# Example: Increase summary stats cache to 4 hours
CACHE_TTL_SUMMARY_STATS: int = 14400  # Changed from 7200 to 14400

# Example: Decrease contract data cache to 30 minutes
CACHE_TTL_CONTRACT_DATA: int = 1800   # Changed from 3600 to 1800
```

### **2. Restart the Application**
Changes to cache durations require an application restart to take effect.

### **3. Clear Existing Cache (Optional)**
To apply new durations immediately, clear the cache using the sidebar:
- Navigate to the "📊 Cache Monitor" in the sidebar
- Click "🗑️ Clear Cache"

## ⏱️ **Time Conversion Reference**

| Duration | Seconds | Common Use Cases |
|----------|---------|------------------|
| 15 minutes | 900 | Very dynamic data |
| 30 minutes | 1800 | Frequently changing data |
| 1 hour | 3600 | Standard caching |
| 2 hours | 7200 | Aggregate statistics |
| 4 hours | 14400 | Static/reference data |
| 8 hours | 28800 | Very stable data |
| 24 hours | 86400 | Daily refresh data |

## 🎯 **Recommended Settings by Environment**

### **Development Environment**
```python
CACHE_TTL_STATIC_DATA: int = 3600       # 1 hour (shorter for testing)
CACHE_TTL_SUMMARY_STATS: int = 1800     # 30 minutes (frequent changes)
CACHE_TTL_CONTRACT_DATA: int = 900      # 15 minutes (rapid iteration)
CACHE_TTL_DYNAMIC_QUERIES: int = 300    # 5 minutes (immediate feedback)
```

### **Production Environment**
```python
CACHE_TTL_STATIC_DATA: int = 14400      # 4 hours (stable data)
CACHE_TTL_SUMMARY_STATS: int = 7200     # 2 hours (balanced performance)
CACHE_TTL_CONTRACT_DATA: int = 3600     # 1 hour (good performance)
CACHE_TTL_DYNAMIC_QUERIES: int = 1800   # 30 minutes (responsive)
```

### **High-Traffic Environment**
```python
CACHE_TTL_STATIC_DATA: int = 28800      # 8 hours (maximum caching)
CACHE_TTL_SUMMARY_STATS: int = 14400    # 4 hours (longer caching)
CACHE_TTL_CONTRACT_DATA: int = 7200     # 2 hours (extended caching)
CACHE_TTL_DYNAMIC_QUERIES: int = 3600   # 1 hour (reduce database load)
```

## 📊 **Monitoring Cache Performance**

Use the **Cache Monitor** in the sidebar to track:
- **Hit Rate**: Higher is better (aim for >70%)
- **Cache Size**: Monitor memory usage
- **Query Patterns**: See which queries benefit most from caching

## 💡 **Best Practices**

1. **Start Conservative**: Begin with shorter durations and increase as needed
2. **Monitor Hit Rates**: Longer durations = higher hit rates but less fresh data
3. **Consider Data Patterns**: How often does your data actually change?
4. **Environment Specific**: Use different settings for dev vs. production
5. **Clear on Data Changes**: If you update data directly in the database, clear the cache

## 🚨 **When to Clear Cache**

Clear the cache when:
- You've updated cache duration settings
- Data has been modified directly in the database
- You're seeing stale/outdated information
- You're troubleshooting data issues

## 📝 **Usage in Code**

The cache settings are automatically used throughout the application:

```python
# Summary statistics (uses CACHE_TTL_SUMMARY_STATS)
cache.put("contract_summary_stats", filters, stats, ttl=db_config.CACHE_TTL_SUMMARY_STATS)

# Available managers (uses CACHE_TTL_STATIC_DATA)
cache.put("available_managers", filters, managers, ttl=db_config.CACHE_TTL_STATIC_DATA)

# Contract data (uses CACHE_TTL_CONTRACT_DATA)
cache.put("contract_status_data", filters, df, ttl=db_config.CACHE_TTL_CONTRACT_DATA)
```

No code changes needed when updating durations - just modify the settings file!