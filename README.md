```markdown
# OpenGovt - Legislative Data Ingestion & Analysis Platform

End-to-end pipeline for discovering, downloading, processing, and analyzing U.S. legislative data from multiple government sources.

## 🎯 Key Features

- **Multi-Database Support**: PostgreSQL, MySQL, SQLite, ClickHouse, InfluxDB, VictoriaMetrics
- **API Integrations**: Congress.gov, GovInfo.gov, OpenStates API v3, NY OpenLegislation
- **Bulk Data Processing**: Automated download and extraction of legislative archives
- **Flexible Configuration**: YAML-based config with environment variable overrides
- **Docker Support**: Complete stack with optional database services
- **Testing Utilities**: Scripts to validate database and API connections
- **Comprehensive Documentation**: Setup guides, examples, and troubleshooting

## 📚 Quick Links

- [Quick Start Guide](docs/MULTI_DATABASE_QUICKSTART.md) - Get started in 5 minutes
- [Database Configuration](docs/DATABASE_CONFIGURATION.md) - Complete database setup guide
- [Government Data Resources](docs/GOVERNMENT_DATA_RESOURCES.md) - Available APIs and sources
- [Analysis Modules](docs/ANALYSIS_MODULES.md) - NLP and analysis capabilities
- [Scripts Documentation](scripts/README.md) - Utility scripts reference

## 🏗️ Architecture

### Core Modules

All Python modules are prefixed `cbw_` for clarity:
- **cbw_utils.py** - Logging, decorators, JSON helpers
- **cbw_config.py** - Configuration object & defaults
- **cbw_discovery.py** - Discovery of candidate URLs
- **cbw_validator.py** - HEAD/GET validation
- **cbw_downloader.py** - Async downloader with resume/retry
- **cbw_extractor.py** - Archive extraction
- **cbw_parser.py** - Conservative parsers for XML/JSON
- **cbw_db.py** - Database migration & upsert helper
- **cbw_db_adapter.py** - Multi-database adapter for different DB engines
- **cbw_retry.py** - Retry report manager
- **cbw_http.py** - HTTP control server for TUI/automation
- **cbw_main.py** - CLI entrypoint to run the end-to-end pipeline

### Supported Databases

- **PostgreSQL** (primary) - Relational database for structured data
- **MySQL/MariaDB** - Alternative relational database
- **SQLite** - Lightweight local development database
- **ClickHouse** - Columnar database for analytics
- **InfluxDB** - Time series database for metrics
- **VictoriaMetrics** - Prometheus-compatible time series database

### API Integrations

- **Congress.gov API** - Federal legislative data
- **GovInfo.gov API** - Published government documents
- **GovInfo.gov Bulk Data** - Large-scale downloads
- **OpenStates API v3** - State legislative data (50 states + territories)
- **OpenStates Bulk Data** - State data archives
- **NY OpenLegislation** - New York State legislative data

## 🚀 Quick Start

### Local Setup

```bash
# 1. Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Generate database configuration (interactive)
python scripts/generate_db_config.py

# 3. Test database connection
python scripts/test_db_connection.py --all

# 4. Run discovery dry-run (no downloads)
python cbw_main.py --start-congress 118 --end-congress 118 --dry-run

# 5. Full run (downloads and processes data)
python cbw_main.py --download --extract --postprocess
```

### Docker Setup

```bash
# Start with PostgreSQL only
docker-compose up -d

# Or include additional databases
docker-compose --profile mysql --profile clickhouse up -d

# Test connections
python scripts/test_db_connection.py --all

# View logs
docker-compose logs -f pipeline
```

### Remote Database Connection

```bash
# Set environment variable
export DATABASE_URL_POSTGRES="postgresql://user:pass@remote-host:5432/congress"

# Or edit config/database.yaml
# Then test connection
python scripts/test_db_connection.py --db-type postgresql
```

## 🔧 Configuration

The project uses a centralized configuration file at `config/database.yaml`.

### Generate Configuration

```bash
# Interactive wizard
python scripts/generate_db_config.py

# Custom output location
python scripts/generate_db_config.py --output my_config.yaml
```

### Environment Variables

Override configuration using environment variables:

```bash
# Databases
export DATABASE_URL_POSTGRES="postgresql://user:pass@host:5432/dbname"
export DATABASE_URL_MYSQL="mysql+pymysql://user:pass@host:3306/dbname"

# API Keys
export CONGRESS_API_KEY="your_key_here"
export GOVINFO_API_KEY="your_key_here"
export OPENSTATES_API_KEY="your_key_here"
```

## 🧪 Testing

```bash
# Test database connections
python scripts/test_db_connection.py --all
python scripts/test_db_connection.py --db-type postgresql

# Test API connections
python scripts/test_api_connections.py
python scripts/test_api_connections.py --api congress_api

# Show API configuration status
python scripts/test_db_connection.py --api-config

# Run example
python examples/database_usage.py
```

## 📖 Usage Examples

### Basic Pipeline Run

```bash
# Discover, download, and process data
python cbw_main.py --download --extract --postprocess

# Limit to specific congress
python cbw_main.py --start-congress 118 --end-congress 118 --download --postprocess

# Use specific database type
python cbw_main.py --db-type mysql --postprocess
```

### Using Different Databases

```bash
# PostgreSQL (default)
python cbw_main.py --postprocess

# MySQL
python cbw_main.py --db-type mysql --postprocess

# SQLite (for development)
python cbw_main.py --db-type sqlite --postprocess
```

### HTTP Control Server

```bash
# Start control server
python cbw_main.py --serve --serve-port 8080

# Access endpoints
curl http://localhost:8080/status
curl http://localhost:8080/metrics
```

## 📁 Project Structure

```
opengovt/
├── app/                          # Application modules
│   ├── db/migrations/           # SQL migration files
│   ├── db.py                    # Database helpers
│   ├── pipeline.py              # Pipeline orchestration
│   └── utils.py                 # Utility functions
├── config/                       # Configuration files
│   └── database.yaml            # Database & API configuration
├── docs/                         # Documentation
│   ├── DATABASE_CONFIGURATION.md
│   ├── MULTI_DATABASE_QUICKSTART.md
│   ├── GOVERNMENT_DATA_RESOURCES.md
│   └── ANALYSIS_MODULES.md
├── examples/                     # Working examples
│   ├── database_usage.py        # Multi-database example
│   └── complete_analysis_pipeline.py
├── models/                       # Data models
│   ├── bill.py
│   ├── vote.py
│   ├── person.py
│   └── committee.py
├── scripts/                      # Utility scripts
│   ├── test_db_connection.py   # Database testing
│   ├── test_api_connections.py # API testing
│   └── generate_db_config.py   # Config generator
├── cbw_*.py                     # Core pipeline modules
├── docker-compose.yml           # Docker stack definition
└── requirements.txt             # Python dependencies
```

## 🔐 Security

- **Never commit credentials** to version control
- Use environment variables for sensitive data
- API keys are sanitized in logs
- Connection strings are masked in output
- `.gitignore` excludes credential files
- Use `docker-compose.override.yml` (not in git) for local secrets

## 📊 Monitoring & Metrics

The pipeline exposes:
- **Prometheus metrics** on port 8000
- **HTTP control API** on port 8080
- **Logs** in `./logs/` directory (rotating files)
- **Retry reports** in `retry_report.json`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python scripts/test_db_connection.py --all`
5. Submit a pull request

## 📝 Notes

- Parsers are conservative starters - sample XML can be used to enhance lxml XPaths
- Each function is decorated with labeled entry/exit/exception logs for debugging
- Retry report automatically records failed URLs
- Compatible with Python 3.7+

## 🆘 Troubleshooting

### Connection Issues

```bash
# Check database is running
docker-compose ps

# View logs
docker-compose logs postgres

# Test connection
python scripts/test_db_connection.py --db-type postgresql
```

### API Issues

```bash
# Test API connectivity
python scripts/test_api_connections.py --api congress_api

# Show API configuration
python scripts/test_db_connection.py --api-config
```

See [DATABASE_CONFIGURATION.md](docs/DATABASE_CONFIGURATION.md) for detailed troubleshooting.

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Data sources:
- Library of Congress (Congress.gov API)
- Government Publishing Office (GovInfo.gov)
- OpenStates Project
- New York Senate (OpenLegislation)

## 📞 Support

- Documentation: See `docs/` directory
- Issues: GitHub Issues
- Examples: See `examples/` directory
