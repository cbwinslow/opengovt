# Database Configuration Guide

This guide explains how to configure and use multiple database systems with the OpenGovt project.

## Table of Contents
- [Overview](#overview)
- [Supported Databases](#supported-databases)
- [Configuration](#configuration)
- [Connection Testing](#connection-testing)
- [Database-Specific Setup](#database-specific-setup)
- [Migration Management](#migration-management)
- [API Integrations](#api-integrations)
- [Troubleshooting](#troubleshooting)

## Overview

The OpenGovt project supports multiple database systems to accommodate different use cases:
- **PostgreSQL**: Primary relational database for structured legislative data
- **MySQL/MariaDB**: Alternative relational database
- **SQLite**: Lightweight option for development and testing
- **ClickHouse**: Columnar database for high-performance analytics
- **InfluxDB**: Time series database for tracking metrics over time
- **VictoriaMetrics**: Alternative time series database (Prometheus-compatible)

## Supported Databases

### PostgreSQL (Recommended)
- **Use Case**: Primary database for bills, votes, legislators, and relationships
- **Driver**: psycopg2-binary
- **Features**: Full ACID compliance, complex queries, JSON support

### MySQL/MariaDB
- **Use Case**: Alternative to PostgreSQL for organizations standardized on MySQL
- **Driver**: pymysql + SQLAlchemy
- **Features**: ACID compliance, wide ecosystem support

### SQLite
- **Use Case**: Local development, testing, single-user deployments
- **Driver**: SQLAlchemy (built-in Python support)
- **Features**: Zero configuration, file-based, portable

### ClickHouse
- **Use Case**: Analytical queries, aggregations, reporting on large datasets
- **Driver**: clickhouse-driver
- **Features**: Column-oriented storage, parallel processing, compression

### InfluxDB
- **Use Case**: Time series data, legislative activity metrics, tracking changes
- **Driver**: influxdb-client
- **Features**: Purpose-built for time series, efficient storage, powerful queries

### VictoriaMetrics
- **Use Case**: Metrics collection, Prometheus-compatible monitoring
- **Driver**: requests (HTTP API)
- **Features**: High performance, low resource usage, PromQL support

## Configuration

### Configuration File

The main configuration file is `config/database.yaml`. It supports environment variable expansion using `${VAR:-default}` syntax.

```yaml
databases:
  postgresql:
    enabled: true
    connection_string: "${DATABASE_URL_POSTGRES:-postgresql://user:pass@localhost:5432/congress}"
    pool_size: 10
    max_overflow: 20
```

### Environment Variables

Override configuration using environment variables:

```bash
# PostgreSQL
export DATABASE_URL_POSTGRES="postgresql://user:pass@host:5432/dbname"

# MySQL
export DATABASE_URL_MYSQL="mysql+pymysql://user:pass@host:3306/dbname"

# SQLite
export DATABASE_URL_SQLITE="sqlite:///./congress.db"

# ClickHouse
export CLICKHOUSE_HOST="localhost"
export CLICKHOUSE_PORT="9000"
export CLICKHOUSE_DB="congress"
export CLICKHOUSE_USER="default"
export CLICKHOUSE_PASSWORD="password"

# InfluxDB
export INFLUXDB_URL="http://localhost:8086"
export INFLUXDB_TOKEN="your_token"
export INFLUXDB_ORG="congress"
export INFLUXDB_BUCKET="legislative_metrics"

# VictoriaMetrics
export VICTORIAMETRICS_URL="http://localhost:8428"

# API Keys
export CONGRESS_API_KEY="your_api_key"
export GOVINFO_API_KEY="your_api_key"
export OPENSTATES_API_KEY="your_api_key"
export NY_LEGISLATION_API_KEY="your_api_key"
```

### Enabling Databases

Edit `config/database.yaml` to enable/disable databases:

```yaml
databases:
  postgresql:
    enabled: true    # Primary database
  mysql:
    enabled: false   # Disable if not needed
  clickhouse:
    enabled: false   # Enable for analytics
```

## Connection Testing

Use the connection test utility to verify your database configuration:

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

Expected output for successful connection:
```
======================================================================
Testing POSTGRESQL connection...
======================================================================
📋 Connection Info: PostgreSQL: postgresql://congress:****@localhost:5432/congress
⏳ Attempting connection...
✅ Connection established
⏳ Testing query execution...
✅ Query test passed
✨ POSTGRESQL connection is working properly!
🔒 Connection closed
```

## Database-Specific Setup

### PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE congress;
CREATE USER congress WITH PASSWORD 'congress';
GRANT ALL PRIVILEGES ON DATABASE congress TO congress;
\q

# Run migrations
python cbw_main.py --db "postgresql://congress:congress@localhost:5432/congress" --postprocess
```

### MySQL Setup

```bash
# Install MySQL
sudo apt-get install mysql-server

# Create database and user
mysql -u root -p
CREATE DATABASE congress CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'congress'@'localhost' IDENTIFIED BY 'congress';
GRANT ALL PRIVILEGES ON congress.* TO 'congress'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Update config/database.yaml to enable MySQL
# Set enabled: true for mysql section
```

### SQLite Setup

```bash
# No installation needed - SQLite is built into Python

# Update config/database.yaml to enable SQLite
# Connection string example: sqlite:///./congress.db

# Database file will be created automatically
```

### ClickHouse Setup

```bash
# Install ClickHouse
curl https://clickhouse.com/ | sh
sudo ./clickhouse install

# Start service
sudo clickhouse start

# Create database
clickhouse-client
CREATE DATABASE congress;
EXIT;

# Update config/database.yaml to enable ClickHouse
```

### InfluxDB Setup

```bash
# Install InfluxDB 2.x
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.0-amd64.deb
sudo dpkg -i influxdb2-2.7.0-amd64.deb

# Start service
sudo systemctl start influxdb

# Setup via UI at http://localhost:8086
# Or use CLI:
influx setup \
  --username congress \
  --password congress123 \
  --org congress \
  --bucket legislative_metrics \
  --force

# Get token
influx auth list

# Update config/database.yaml with token
```

### VictoriaMetrics Setup

```bash
# Install VictoriaMetrics
wget https://github.com/VictoriaMetrics/VictoriaMetrics/releases/download/v1.93.0/victoria-metrics-linux-amd64-v1.93.0.tar.gz
tar xvf victoria-metrics-linux-amd64-v1.93.0.tar.gz

# Run
./victoria-metrics-prod -storageDataPath=/var/lib/victoria-metrics-data

# Test
curl http://localhost:8428/health
```

## Migration Management

### Running Migrations

Migrations are automatically applied when using `--postprocess` flag:

```bash
# Apply migrations to PostgreSQL
python cbw_main.py \
  --db "postgresql://congress:congress@localhost:5432/congress" \
  --postprocess

# Migrations are in app/db/migrations/
# - 001_init.sql: Base schema
# - 002_analysis_tables.sql: Analysis tables
```

### Creating New Migrations

1. Create a new SQL file in `app/db/migrations/`
2. Name it with incremental number: `003_your_migration.sql`
3. Wrap in transaction:

```sql
BEGIN;

-- Your schema changes here
CREATE TABLE IF NOT EXISTS new_table (
  id SERIAL PRIMARY KEY,
  name TEXT
);

COMMIT;
```

### Database-Specific Migrations

Some databases may require different SQL syntax. Use conditional migrations:

```python
# In your migration runner
if db_type == 'mysql':
    # MySQL-specific migration
elif db_type == 'postgresql':
    # PostgreSQL-specific migration
```

## API Integrations

The configuration file includes settings for government data APIs:

### Congress.gov API

```bash
# Get API key: https://api.congress.gov/sign-up/
export CONGRESS_API_KEY="your_key_here"

# Base URL: https://api.congress.gov/v3
# Rate limit: 5000 requests/hour
```

### GovInfo.gov API

```bash
# Get API key: https://www.govinfo.gov/api-signup
export GOVINFO_API_KEY="your_key_here"

# Base URL: https://api.govinfo.gov
# Rate limit: 1000 requests/hour
```

### OpenStates API v3

```bash
# Get API key: https://openstates.org/accounts/profile/
export OPENSTATES_API_KEY="your_key_here"

# Base URL: https://v3.openstates.org
# GraphQL: https://v3.openstates.org/graphql
# Rate limit: 4000 requests/hour with key
```

### New York OpenLegislation

```bash
# Get API key: https://legislation.nysenate.gov/
export NY_LEGISLATION_API_KEY="your_key_here"

# Base URL: https://legislation.nysenate.gov/api/3
```

### Bulk Data Sources

#### GovInfo.gov Bulk Data
```bash
# Base URL: https://www.govinfo.gov/bulkdata
# Collections: BILLS, BILLSTATUS, CREC, FR
# Example: https://www.govinfo.gov/bulkdata/BILLSTATUS/118
```

#### OpenStates Bulk Data
```bash
# Primary: https://data.openstates.org
# Mirror: https://open.pluralpolicy.com/data
# Format: JSON files per state, updated regularly
```

## Troubleshooting

### Connection Failures

**Problem**: Cannot connect to database

**Solutions**:
1. Verify database is running: `sudo systemctl status postgresql`
2. Check connection string in config file
3. Verify credentials
4. Check firewall rules: `sudo ufw status`
5. Test with connection utility: `python scripts/test_db_connection.py --db-type postgresql`

### Authentication Errors

**Problem**: Access denied errors

**Solutions**:
1. Verify username and password in config
2. Check database user permissions: `GRANT ALL PRIVILEGES ON DATABASE congress TO congress;`
3. For PostgreSQL, check `pg_hba.conf` authentication method
4. For MySQL, check user host permissions

### Port Conflicts

**Problem**: Port already in use

**Solutions**:
1. Check what's using the port: `sudo lsof -i :5432`
2. Stop conflicting service
3. Or change port in configuration

### Migration Failures

**Problem**: Migration fails to apply

**Solutions**:
1. Check database logs
2. Verify SQL syntax for your database type
3. Check user permissions for DDL operations
4. Run migrations manually to see detailed error:
   ```bash
   psql -U congress -d congress -f app/db/migrations/001_init.sql
   ```

### Performance Issues

**Problem**: Slow queries or connections

**Solutions**:
1. Increase pool size in config
2. Add indexes for frequently queried columns
3. Use ClickHouse for analytical queries
4. Monitor connection pool usage
5. Check database resource usage: `top`, `htop`

### API Rate Limiting

**Problem**: API requests being throttled

**Solutions**:
1. Verify API key is configured
2. Implement request caching
3. Add delays between requests
4. Use bulk data downloads instead of API
5. Check rate limit in config file

## Best Practices

### Security
- Never commit credentials to version control
- Use environment variables for sensitive data
- Restrict database network access
- Use SSL/TLS for remote connections
- Rotate API keys regularly

### Performance
- Use connection pooling (already configured)
- Create indexes on frequently queried columns
- Use ClickHouse for analytics, PostgreSQL for transactions
- Implement caching for API responses
- Batch database operations

### Monitoring
- Enable InfluxDB or VictoriaMetrics for metrics
- Monitor connection pool usage
- Track API rate limit usage
- Log slow queries
- Set up alerts for failures

### Development
- Use SQLite for local development
- Use Docker Compose for consistent environments
- Test migrations before production
- Keep configuration in version control (without secrets)
- Document any custom modifications

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MySQL Documentation](https://dev.mysql.com/doc/)
- [ClickHouse Documentation](https://clickhouse.com/docs)
- [InfluxDB Documentation](https://docs.influxdata.com/)
- [Congress.gov API Docs](https://github.com/LibraryOfCongress/api.congress.gov)
- [OpenStates API Docs](https://docs.openstates.org/)
- [GovInfo.gov API Docs](https://api.govinfo.gov/docs/)
