# Agiloft Analytics Dashboard

A comprehensive Streamlit-based analytics dashboard for Agiloft CLM (Contract Lifecycle Management) data with secure Google authentication, SingleStore database connectivity, and interactive multi-page visualizations.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-v1.28+-red.svg)
![SingleStore](https://img.shields.io/badge/database-SingleStore-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🚀 Features

### 📊 **Analytics Pages**
- **Contract Status Analysis**: Track contract values by manager and status with enhanced manager selection
- **Customer Performance**: Analyze contract trends by customer over time with lifecycle insights
- **Geographic Distribution**: Visualize contract data by country with interactive maps and regional analysis

### 🔐 **Security & Authentication**
- Google OAuth integration via Streamlit
- User session management
- Secure logout functionality
- Database connection security

### ⚡ **Performance Optimization**
- Custom in-memory caching with intelligent filter-aware invalidation
- Connection pooling (5 base + 10 overflow connections)
- Query result caching with configurable TTL
- Memory and performance monitoring
- Query timeout and retry logic

### 🎨 **Enhanced User Experience**
- **Smart Search**: Instant filtering for managers and customers
- **Quick Actions**: Fast selection buttons (Top 10, Top 20, All, Clear)
- **UUID Support**: Compatible with modern database schema
- **Responsive Design**: Mobile-friendly interface
- **Visual Feedback**: Clear selection summaries and progress indicators

## 🗄️ Database Setup

### Prerequisites
- SingleStore database instance
- Database user with appropriate permissions

### Create Database Schema

1. **Execute the DDL script** to create the database and tables:
   ```bash
   # Connect to your SingleStore instance and run:
   mysql -h your-singlestore-host -u username -p < database/order_mgt_ddl.sql
   ```

2. **Database Structure**:
   The `order_mgt_ddl.sql` file creates a comprehensive database with:

   | Table | Purpose | Key Features |
   |-------|---------|--------------|
   | `contract` | Contract lifecycle management | UUID keys, full-text search, optimized indexes |
   | `customer` | Customer master data | UUID keys, nation relationships |
   | `employee` | Employee/manager data | Used for manager name mapping |
   | `nation` | Country reference data | For geographic analysis |
   | `region` | Regional reference data | For regional grouping |
   | `orders` | Order header information | Transactional data |
   | `lineitem` | Order line items | Detailed order data |
   | `part` | Parts/products catalog | Product information |
   | `partsupp` | Part supplier relationships | Supply chain data |
   | `record_metadata` | Audit trail and metadata | JSON metadata storage |

3. **Key Schema Features**:
   - **UUID-based primary keys** for modern data architecture
   - **Full-text search indexes** on key text fields
   - **Comprehensive audit trail** via record_metadata table
   - **Sharding and sorting optimized** for SingleStore performance
   - **Created/updated timestamp tracking** on all tables

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/hjtapia74/agiloft-analytics.git
cd agiloft-analytics
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Configuration
1. Copy the configuration template:
   ```bash
   cp config/settings.py.template config/settings.py
   ```

2. Update `config/settings.py` with your database credentials:
   ```python
   # Database Configuration
   class DatabaseConfig:
       HOST = "your-singlestore-host"
       PORT = 3306
       DATABASE = "order_mgt"
       USERNAME = "your-username"
       PASSWORD = "your-password"
   ```

### 5. SSL Certificate (if required)
Place your SSL certificate file (e.g., `Presencia-Social.pem`) in the project root directory.

## 🚀 Running the Application

### Development Mode
```bash
streamlit run app.py
```

### Production Mode
```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

The application will be available at `http://localhost:8501`

## 📁 Project Structure

```
agiloft-analytics/
├── app.py                      # Main application entry point
├── requirements.txt            # Python dependencies
├── Presencia-Social.pem       # SSL certificate file
├── CLAUDE.md                  # Project documentation and instructions
├──
├── config/
│   ├── settings.py            # App, database, and UI configuration
│   └── settings.py.template   # Configuration template
├──
├── database/
│   ├── order_mgt_ddl.sql      # Database schema creation script
│   ├── db_manager.py          # SingleStore database manager with connection pooling
│   └── db_interface.py        # Database interface and query abstractions
├──
├── ui/
│   ├── base_page.py           # Base page class for common functionality
│   ├── cache_monitor.py       # Cache monitoring utilities
│   ├── components.py          # Reusable UI components
│   ├── enhanced_manager_filter.py # Advanced filtering components
│   └── pages/
│       ├── status_page.py     # Contract status analysis page
│       ├── customer_page.py   # Customer performance page
│       └── country_page.py    # Geographic distribution page
├──
├── utils/
│   ├── cache_manager.py       # Custom in-memory caching system with TTL support
│   ├── exceptions.py          # Custom exception classes
│   ├── helpers.py             # Utility functions
│   └── logging_config.py      # Logging configuration
├──
├── data/
│   └── country_coordinates.csv # Geographic reference data
├──
├── logs/                      # Application logs
└── tests/                     # Test suite (pytest)
```

## ⚙️ Configuration

### Cache Configuration
The application features intelligent caching with different TTL values:
- **Static data**: 4 hours TTL (managers, customers, statuses)
- **Summary stats**: 2 hours TTL
- **Contract data**: 1 hour TTL
- **Dynamic queries**: 30 minutes TTL

Detailed cache configuration is available in `cache_configuration.md`.

### Database Connection Pool
- **Base connections**: 5
- **Max overflow**: 10
- **Query timeout**: 30 seconds
- **Connection validation**: Automatic health checks

### UI Configuration
- **Chart theme**: Streamlit
- **Max table rows**: 500
- **Color palettes**: 8 predefined schemes
- **Export formats**: CSV, JSON, analysis reports

## 📊 Analytics Features

### Contract Status Analysis
- **Manager Performance**: Track contract values by manager with name-based selection
- **Status Distribution**: Analyze contract flow through different statuses
- **Value Range Filtering**: Dynamic sliders based on actual data ranges
- **Quick Actions**: Top performers, value ranges, status filters

### Customer Performance Analysis
- **Customer Selection**: Search and select from actual customer database
- **Trend Analysis**: Year-over-year performance tracking
- **Lifecycle Insights**: Customer retention and growth metrics
- **Geographic Integration**: Customer location analysis

### Geographic Distribution
- **Interactive Maps**: World map visualization of contract distribution
- **Regional Analysis**: Automatic grouping by geographic regions
- **Country Performance**: Top performing countries and growth trends
- **Export Capabilities**: Map data, country analysis, and reports

## 🔧 Development Commands

### Code Quality
```bash
# Format code
black .

# Lint code
flake8

# Type checking
mypy .
```

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov

# Run specific test
pytest tests/test_database.py
```

### Database Operations
```bash
# Test database connection
python -c "from database.db_manager import DatabaseManager; dm = DatabaseManager(); print('Connected:', dm.test_connection())"

# Check available managers
python -c "from database.db_manager import DatabaseManager; dm = DatabaseManager(); print('Managers:', len(dm.get_available_contract_managers()))"
```

## 🚨 Troubleshooting

### Database Connection Issues
1. **Check SingleStore service status**
2. **Verify network connectivity**: `telnet your-host 3306`
3. **Review connection pool settings** in `config/settings.py`
4. **Check logs** in `logs/` directory for detailed error messages

### Performance Issues
1. **Monitor connection pool usage** via Cache Monitor in sidebar
2. **Check query execution times** in application logs
3. **Review memory usage** with psutil monitoring
4. **Clear cache** using sidebar Cache Monitor if needed

### Cache Issues
1. **Monitor cache hit rates** via Cache Monitor in sidebar
2. **Check TTL settings** in cache configuration
3. **Review cache statistics** and memory usage
4. **Verify filter-aware caching** is working correctly

### Common Solutions
- **"No data found"**: Check customer/manager selections and database connectivity
- **Slow performance**: Review cache settings and connection pool configuration
- **Memory issues**: Monitor cache usage and clear if necessary
- **Authentication problems**: Verify Google OAuth configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation for API changes
- Use type hints where appropriate
- Ensure all tests pass before submitting PR

## 📚 Key Improvements & Recent Updates

### UUID Compatibility (Latest)
- **Database Schema**: Updated to support UUID primary keys (`varchar(36)`)
- **Enhanced Customer Selection**: Smart search and quick actions for customer selection
- **Query Optimization**: Direct UUID string joins instead of integer casting
- **Consistent UI**: Same selection patterns across all analysis pages
- **Improved Caching**: Filter-aware caching with intelligent TTL

### Performance Optimizations
- **Manager Activity Query**: 33% improvement (59s → 40s) using employee table hash index
- **Connection Pooling**: Prevents connection exhaustion under load
- **Intelligent Caching**: Reduces database load with smart invalidation
- **Query Limits**: Configurable limits (10K max rows) for performance

### User Experience Enhancements
- **Manager Names**: Display actual names instead of cryptic IDs
- **Enhanced Search**: Find managers and customers instantly by typing
- **Visual Feedback**: Clear selection summaries and progress indicators
- **Mobile Support**: Responsive design for mobile devices

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **SingleStore** for high-performance database platform
- **Streamlit** for the amazing web app framework
- **Altair** for beautiful data visualizations
- **Pandas** for powerful data manipulation capabilities

## 📞 Support

For support, please:
1. Check the [troubleshooting section](#🚨-troubleshooting)
2. Review logs in the `logs/` directory
3. Create an issue on GitHub with detailed error information
4. Include your configuration (without sensitive data) when reporting issues

---

**Built with ❤️ using Python, Streamlit, and SingleStore**