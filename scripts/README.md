# Scripts Directory

This directory contains utility scripts for database and API management.

## Available Scripts

### 1. test_db_connection.py

Test database connections for all configured database systems.

**Usage:**
```bash
# Test all enabled databases
python scripts/test_db_connection.py --all

# Test specific database
python scripts/test_db_connection.py --db-type postgresql
python scripts/test_db_connection.py --db-type mysql

# Show API configurations
python scripts/test_db_connection.py --api-config

# Use custom config file
python scripts/test_db_connection.py --all --config /path/to/database.yaml
```

**Features:**
- Tests connection to each enabled database
- Validates query execution
- Shows connection information (with sanitized credentials)
- Provides detailed error messages

### 2. test_api_connections.py

Test API connections to government data sources.

**Usage:**
```bash
# Test all APIs
python scripts/test_api_connections.py

# Test specific API
python scripts/test_api_connections.py --api congress_api
python scripts/test_api_connections.py --api openstates_api

# Use custom config file
python scripts/test_api_connections.py --config /path/to/database.yaml
```

**Supported APIs:**
- `congress_api` - Congress.gov API
- `govinfo_api` - GovInfo.gov API
- `govinfo_bulkdata` - GovInfo.gov Bulk Data
- `openstates_api` - OpenStates API v3
- `openstates_bulk` - OpenStates Bulk Data
- `ny_openlegislation` - NY OpenLegislation API

**Features:**
- Tests API connectivity
- Validates API keys
- Shows rate limits and endpoint information
- Works with or without API keys (where applicable)

### 3. generate_db_config.py

Interactive wizard to generate a customized database configuration file.

**Usage:**
```bash
# Generate config/database.yaml
python scripts/generate_db_config.py

# Generate custom location
python scripts/generate_db_config.py --output my_config.yaml

# Overwrite existing config
python scripts/generate_db_config.py --overwrite
```

**Features:**
- Interactive prompts for all database types
- Configures PostgreSQL, MySQL, SQLite, ClickHouse
- Sets up API keys for government data sources
- Generates properly formatted YAML with environment variable support
- Provides sensible defaults for quick setup

## Common Workflows

### Initial Setup

1. Generate configuration:
   ```bash
   python scripts/generate_db_config.py
   ```

2. Test database connections:
   ```bash
   python scripts/test_db_connection.py --all
   ```

3. Test API connections:
   ```bash
   python scripts/test_api_connections.py
   ```

### Adding a New Database

1. Start database service:
   ```bash
   docker-compose --profile mysql up -d mysql
   ```

2. Edit `config/database.yaml` and enable the database:
   ```yaml
   databases:
     mysql:
       enabled: true  # Change from false to true
   ```

3. Test connection:
   ```bash
   python scripts/test_db_connection.py --db-type mysql
   ```

### Troubleshooting Connection Issues

1. Test specific database:
   ```bash
   python scripts/test_db_connection.py --db-type postgresql
   ```

2. Check logs for detailed error messages

3. Verify credentials in config file

4. Ensure database service is running:
   ```bash
   docker-compose ps
   ```

### Setting Up API Keys

1. Get API keys from providers:
   - Congress.gov: https://api.congress.gov/sign-up/
   - GovInfo.gov: https://www.govinfo.gov/api-signup
   - OpenStates: https://openstates.org/accounts/profile/

2. Set environment variables:
   ```bash
   export CONGRESS_API_KEY="your_key_here"
   export GOVINFO_API_KEY="your_key_here"
   export OPENSTATES_API_KEY="your_key_here"
   ```

3. Or edit `config/database.yaml`:
   ```yaml
   api_sources:
     congress_api:
       api_key: "your_key_here"
   ```

4. Test API connections:
   ```bash
   python scripts/test_api_connections.py
   ```

## Script Requirements

All scripts require:
- Python 3.7+
- Dependencies from `requirements.txt`
- Configuration file at `config/database.yaml` (or custom path)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Exit Codes

All scripts use standard exit codes:
- `0` - Success
- `1` - Failure or error

Use in scripts:
```bash
if python scripts/test_db_connection.py --all; then
    echo "All databases connected successfully"
else
    echo "Some databases failed to connect"
    exit 1
fi
```

## Security Notes

⚠️ **Important:**
- Scripts sanitize credentials in output (replace passwords with `****`)
- Never commit actual API keys to version control
- Use environment variables for sensitive data in production
- Review logs before sharing to ensure no credentials are exposed

## Examples

### Complete Setup Script

```bash
#!/bin/bash
# setup_databases.sh

set -e

echo "Setting up OpenGovt databases..."

# Generate configuration
python scripts/generate_db_config.py

# Start PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 5

# Test connection
if python scripts/test_db_connection.py --db-type postgresql; then
    echo "✅ PostgreSQL setup complete"
else
    echo "❌ PostgreSQL setup failed"
    exit 1
fi

# Run migrations
python cbw_main.py --postprocess --db-type postgresql

echo "✅ Setup complete!"
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Test Database Connections
  run: |
    python scripts/test_db_connection.py --all
  env:
    DATABASE_URL_POSTGRES: ${{ secrets.DATABASE_URL }}
```

## Additional Documentation

- Full database guide: `docs/DATABASE_CONFIGURATION.md`
- Quick start guide: `docs/MULTI_DATABASE_QUICKSTART.md`
- Migration guide: `app/db/migrations/README.md`

## Support

For issues or questions:
1. Check script help: `python scripts/script_name.py --help`
2. Review documentation in `docs/`
3. Check logs in `./logs/` directory
4. Open issue on GitHub (sanitize any credentials!)
