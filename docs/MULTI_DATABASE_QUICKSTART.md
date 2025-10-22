# Multi-Database Quick Start Guide

Get up and running with multi-database support in 5 minutes.

## Quick Start

### 1. Basic Setup (PostgreSQL Only)

The simplest setup uses PostgreSQL (default):

```bash
# Start PostgreSQL with Docker
docker-compose up -d postgres

# Test connection
python scripts/test_db_connection.py --db-type postgresql

# Run pipeline
python cbw_main.py --download --extract --postprocess
```

### 2. Add MySQL Support

Enable MySQL in addition to PostgreSQL:

```bash
# Start PostgreSQL and MySQL
docker-compose --profile mysql up -d

# Enable MySQL in config/database.yaml
# Change enabled: false to enabled: true under mysql section

# Test connections
python scripts/test_db_connection.py --all

# Use MySQL for pipeline
python cbw_main.py --db-type mysql --postprocess
```

### 3. Add Analytics Database (ClickHouse)

For high-performance analytics:

```bash
# Start with ClickHouse
docker-compose --profile clickhouse up -d

# Enable in config/database.yaml
# Change enabled: false to enabled: true under clickhouse section

# Test connection
python scripts/test_db_connection.py --db-type clickhouse

# Use for analytics queries
```

### 4. Add Time Series Monitoring (InfluxDB)

For tracking legislative metrics over time:

```bash
# Start with InfluxDB
docker-compose --profile influxdb up -d

# Enable in config/database.yaml
# Change enabled: false to enabled: true under influxdb section

# Test connection
python scripts/test_db_connection.py --db-type influxdb
```

### 5. Remote Database Connection

Connect to a remote PostgreSQL server:

```bash
# Set environment variable
export DATABASE_URL_POSTGRES="postgresql://user:pass@remote-host:5432/dbname"

# Or edit config/database.yaml
# connection_string: "postgresql://user:pass@remote-host:5432/dbname"

# Test connection
python scripts/test_db_connection.py --db-type postgresql

# Use in pipeline
python cbw_main.py --postprocess
```

## Common Commands

### Testing Database Connections

```bash
# Test all enabled databases
python scripts/test_db_connection.py --all

# Test specific database
python scripts/test_db_connection.py --db-type postgresql

# Show API configurations
python scripts/test_db_connection.py --api-config

# Use custom config file
python scripts/test_db_connection.py --all --config /path/to/database.yaml
```

### Running the Pipeline

```bash
# Basic run with PostgreSQL
python cbw_main.py --download --extract --postprocess

# Use specific database type
python cbw_main.py --db-type mysql --postprocess

# Use custom config
python cbw_main.py --db-config /path/to/database.yaml --postprocess

# Dry run (show what would be downloaded)
python cbw_main.py --start-congress 118 --end-congress 118 --dry-run
```

### Docker Compose

```bash
# Start PostgreSQL only (default)
docker-compose up -d

# Start with MySQL
docker-compose --profile mysql up -d

# Start with ClickHouse
docker-compose --profile clickhouse up -d

# Start with InfluxDB
docker-compose --profile influxdb up -d

# Start with VictoriaMetrics
docker-compose --profile victoriametrics up -d

# Combine multiple profiles
docker-compose --profile mysql --profile clickhouse up -d

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ DELETES DATA)
docker-compose down -v
```

## Configuration Examples

### PostgreSQL (Local)

```yaml
# config/database.yaml
databases:
  postgresql:
    enabled: true
    connection_string: "postgresql://congress:congress@localhost:5432/congress"
```

### PostgreSQL (Remote)

```yaml
# config/database.yaml
databases:
  postgresql:
    enabled: true
    connection_string: "${DATABASE_URL_POSTGRES:-postgresql://user:pass@remote-host:5432/congress}"
```

Or use environment variable:

```bash
export DATABASE_URL_POSTGRES="postgresql://user:pass@remote-host:5432/congress"
```

### Multiple Databases

```yaml
# config/database.yaml
databases:
  postgresql:
    enabled: true
    connection_string: "postgresql://congress:congress@localhost:5432/congress"
  
  mysql:
    enabled: true
    connection_string: "mysql+pymysql://congress:congress@localhost:3306/congress"
  
  clickhouse:
    enabled: true
    host: "localhost"
    port: 9000
    database: "congress"
    user: "default"
    password: ""
```

## API Keys Setup

Configure API keys for government data sources:

```bash
# Congress.gov API
export CONGRESS_API_KEY="your_key_here"

# GovInfo.gov API
export GOVINFO_API_KEY="your_key_here"

# OpenStates API v3
export OPENSTATES_API_KEY="your_key_here"

# New York OpenLegislation
export NY_LEGISLATION_API_KEY="your_key_here"
```

Get API keys:
- Congress.gov: https://api.congress.gov/sign-up/
- GovInfo.gov: https://www.govinfo.gov/api-signup
- OpenStates: https://openstates.org/accounts/profile/
- NY OpenLegislation: https://legislation.nysenate.gov/

## Troubleshooting

### Cannot Connect to Database

```bash
# Check if database is running
docker-compose ps

# Check database logs
docker-compose logs postgres
docker-compose logs mysql

# Test connection manually
psql -h localhost -U congress -d congress  # PostgreSQL
mysql -h localhost -u congress -p congress  # MySQL
```

### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :5432  # PostgreSQL
sudo lsof -i :3306  # MySQL

# Stop conflicting service or change port in docker-compose.yml
```

### Authentication Failed

```bash
# Verify credentials in config/database.yaml
# Check environment variables
env | grep DATABASE

# For Docker containers, credentials are in docker-compose.yml
```

### Migration Errors

```bash
# Check database user has permissions
psql -U congress -d congress
GRANT ALL PRIVILEGES ON DATABASE congress TO congress;

# Run migrations manually to see detailed error
psql -U congress -d congress -f app/db/migrations/001_init.sql
```

## Examples

See working examples in the `examples/` directory:

```bash
# Database usage example
python examples/database_usage.py

# Embeddings example (requires analysis dependencies)
python examples/embeddings_example.py

# Complete analysis pipeline
python examples/complete_analysis_pipeline.py
```

## Next Steps

1. **Full Documentation**: See `docs/DATABASE_CONFIGURATION.md`
2. **Migration Guide**: See `app/db/migrations/README.md`
3. **API Integration**: See `docs/GOVERNMENT_DATA_RESOURCES.md`
4. **Analysis Modules**: See `docs/ANALYSIS_MODULES.md`

## Support

For issues or questions:
1. Check `docs/DATABASE_CONFIGURATION.md` troubleshooting section
2. Review logs in `./logs/` directory
3. Open an issue on GitHub with logs and configuration (sanitize credentials!)

## Security Notes

⚠️ **Never commit credentials to version control!**

- Use environment variables for production
- Keep `config/database.yaml` in `.gitignore` if it contains real credentials
- Use `docker-compose.override.yml` (not in git) for local customization
- Rotate API keys regularly
- Use SSL/TLS for remote database connections
