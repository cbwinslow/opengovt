#!/usr/bin/env python3
###############################################################################
# Name:        generate_db_config.py
# Date:        2025-10-22
# Script Name: generate_db_config.py
# Version:     1.0
# Log Summary: Interactive script to generate database configuration
# Description: Helps users create a customized database.yaml configuration
#              file with their specific database connections and API keys.
# Usage:
#   python scripts/generate_db_config.py
#   python scripts/generate_db_config.py --output my_config.yaml
# Change Summary:
#   - 1.0 initial configuration generator
###############################################################################

import sys
import os
import argparse
from pathlib import Path

def prompt(question: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    if default:
        response = input(f"{question} [{default}]: ").strip()
        return response if response else default
    else:
        return input(f"{question}: ").strip()

def prompt_bool(question: str, default: bool = False) -> bool:
    """Prompt user for yes/no input."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{question} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes', 'true', '1']

def generate_config():
    """Interactive configuration generator."""
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 17 + "Database Configuration Generator" + " " * 19 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print("This wizard will help you create a database configuration file.")
    print("Press Enter to accept default values shown in brackets.")
    print()
    
    config = {
        'databases': {},
        'api_sources': {},
        'features': {}
    }
    
    # PostgreSQL Configuration
    print("\n" + "="*70)
    print("PostgreSQL Configuration (Primary Database)")
    print("="*70)
    
    pg_enabled = prompt_bool("Enable PostgreSQL?", default=True)
    if pg_enabled:
        pg_host = prompt("PostgreSQL host", "localhost")
        pg_port = prompt("PostgreSQL port", "5432")
        pg_user = prompt("PostgreSQL user", "congress")
        pg_pass = prompt("PostgreSQL password", "congress")
        pg_db = prompt("PostgreSQL database", "congress")
        
        conn_str = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        config['databases']['postgresql'] = {
            'enabled': True,
            'connection_string': f"${{DATABASE_URL_POSTGRES:-{conn_str}}}",
            'description': "Primary relational database for bills, votes, legislators",
            'pool_size': 10,
            'max_overflow': 20
        }
    
    # MySQL Configuration
    print("\n" + "="*70)
    print("MySQL/MariaDB Configuration (Optional)")
    print("="*70)
    
    mysql_enabled = prompt_bool("Enable MySQL?", default=False)
    if mysql_enabled:
        mysql_host = prompt("MySQL host", "localhost")
        mysql_port = prompt("MySQL port", "3306")
        mysql_user = prompt("MySQL user", "congress")
        mysql_pass = prompt("MySQL password", "congress")
        mysql_db = prompt("MySQL database", "congress")
        
        conn_str = f"mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}:{mysql_port}/{mysql_db}"
        config['databases']['mysql'] = {
            'enabled': True,
            'connection_string': f"${{DATABASE_URL_MYSQL:-{conn_str}}}",
            'description': "Alternative relational database",
            'pool_size': 10,
            'max_overflow': 20
        }
    else:
        config['databases']['mysql'] = {
            'enabled': False,
            'connection_string': "${DATABASE_URL_MYSQL:-mysql+pymysql://congress:congress@localhost:3306/congress}",
            'description': "Alternative relational database",
            'pool_size': 10,
            'max_overflow': 20
        }
    
    # SQLite Configuration
    print("\n" + "="*70)
    print("SQLite Configuration (Optional - for development)")
    print("="*70)
    
    sqlite_enabled = prompt_bool("Enable SQLite?", default=False)
    if sqlite_enabled:
        sqlite_path = prompt("SQLite database file path", "./congress.db")
        config['databases']['sqlite'] = {
            'enabled': True,
            'connection_string': f"${{DATABASE_URL_SQLITE:-sqlite:///{sqlite_path}}}",
            'description': "Local file-based database for development",
            'pool_size': 1,
            'max_overflow': 0
        }
    else:
        config['databases']['sqlite'] = {
            'enabled': False,
            'connection_string': "${DATABASE_URL_SQLITE:-sqlite:///./congress.db}",
            'description': "Local file-based database for development",
            'pool_size': 1,
            'max_overflow': 0
        }
    
    # ClickHouse Configuration
    print("\n" + "="*70)
    print("ClickHouse Configuration (Optional - for analytics)")
    print("="*70)
    
    ch_enabled = prompt_bool("Enable ClickHouse?", default=False)
    if ch_enabled:
        ch_host = prompt("ClickHouse host", "localhost")
        ch_port = prompt("ClickHouse port", "9000")
        ch_db = prompt("ClickHouse database", "congress")
        ch_user = prompt("ClickHouse user", "default")
        ch_pass = prompt("ClickHouse password", "")
        
        config['databases']['clickhouse'] = {
            'enabled': True,
            'host': f"${{CLICKHOUSE_HOST:-{ch_host}}}",
            'port': f"${{CLICKHOUSE_PORT:-{ch_port}}}",
            'database': f"${{CLICKHOUSE_DB:-{ch_db}}}",
            'user': f"${{CLICKHOUSE_USER:-{ch_user}}}",
            'password': f"${{CLICKHOUSE_PASSWORD:-{ch_pass}}}",
            'description': "OLAP database for analytical queries and aggregations"
        }
    else:
        config['databases']['clickhouse'] = {
            'enabled': False,
            'host': "${CLICKHOUSE_HOST:-localhost}",
            'port': "${CLICKHOUSE_PORT:-9000}",
            'database': "${CLICKHOUSE_DB:-congress}",
            'user': "${CLICKHOUSE_USER:-default}",
            'password': "${CLICKHOUSE_PASSWORD:-}",
            'description': "OLAP database for analytical queries and aggregations"
        }
    
    # InfluxDB Configuration
    config['databases']['influxdb'] = {
        'enabled': False,
        'url': "${INFLUXDB_URL:-http://localhost:8086}",
        'token': "${INFLUXDB_TOKEN:-}",
        'org': "${INFLUXDB_ORG:-congress}",
        'bucket': "${INFLUXDB_BUCKET:-legislative_metrics}",
        'description': "Time series database for tracking legislative metrics over time"
    }
    
    # VictoriaMetrics Configuration
    config['databases']['victoriametrics'] = {
        'enabled': False,
        'url': "${VICTORIAMETRICS_URL:-http://localhost:8428}",
        'description': "Time series database for metrics and monitoring"
    }
    
    # API Keys
    print("\n" + "="*70)
    print("API Keys Configuration (Optional)")
    print("="*70)
    print("Get API keys from:")
    print("  - Congress.gov: https://api.congress.gov/sign-up/")
    print("  - GovInfo.gov: https://www.govinfo.gov/api-signup")
    print("  - OpenStates: https://openstates.org/accounts/profile/")
    print("  - NY OpenLegislation: https://legislation.nysenate.gov/")
    print()
    
    configure_apis = prompt_bool("Configure API keys now?", default=False)
    
    if configure_apis:
        congress_key = prompt("Congress.gov API key (leave empty to skip)", "")
        govinfo_key = prompt("GovInfo.gov API key (leave empty to skip)", "")
        openstates_key = prompt("OpenStates API key (leave empty to skip)", "")
        ny_key = prompt("NY OpenLegislation API key (leave empty to skip)", "")
    else:
        congress_key = govinfo_key = openstates_key = ny_key = ""
    
    # Congress API
    config['api_sources']['congress_api'] = {
        'base_url': "https://api.congress.gov/v3",
        'api_key': f"${{CONGRESS_API_KEY:-{congress_key}}}",
        'description': "Official Congress.gov API for federal legislative data",
        'rate_limit': 5000,
        'endpoints': ["/bill", "/amendment", "/member", "/committee", "/nomination", "/congress"]
    }
    
    # GovInfo API
    config['api_sources']['govinfo_api'] = {
        'base_url': "https://api.govinfo.gov",
        'api_key': f"${{GOVINFO_API_KEY:-{govinfo_key}}}",
        'description': "GovInfo.gov API for published government documents",
        'rate_limit': 1000,
        'endpoints': ["/collections", "/published"]
    }
    
    # GovInfo Bulk Data
    config['api_sources']['govinfo_bulkdata'] = {
        'base_url': "https://www.govinfo.gov/bulkdata",
        'description': "Bulk download access for government documents",
        'collections': ["BILLS", "BILLSTATUS", "CREC", "FR"]
    }
    
    # OpenStates API
    config['api_sources']['openstates_api'] = {
        'base_url': "https://v3.openstates.org",
        'api_key': f"${{OPENSTATES_API_KEY:-{openstates_key}}}",
        'description': "OpenStates API for state legislative data (all 50 states + DC, PR, VI)",
        'rate_limit': 4000,
        'graphql_endpoint': "https://v3.openstates.org/graphql"
    }
    
    # OpenStates Bulk
    config['api_sources']['openstates_bulk'] = {
        'base_url': "https://data.openstates.org",
        'mirror_url': "https://open.pluralpolicy.com/data",
        'description': "Bulk downloads for state legislative data"
    }
    
    # NY OpenLegislation
    config['api_sources']['ny_openlegislation'] = {
        'base_url': "https://legislation.nysenate.gov/api/3",
        'api_key': f"${{NY_LEGISLATION_API_KEY:-{ny_key}}}",
        'description': "New York State legislative data API"
    }
    
    # Feature Flags
    config['features'] = {
        'enable_remote_postgresql': True,
        'enable_mysql': mysql_enabled,
        'enable_clickhouse': ch_enabled,
        'enable_influxdb': False,
        'enable_victoriametrics': False,
        'enable_sqlite': sqlite_enabled
    }
    
    return config

def save_config(config: dict, output_path: str):
    """Save configuration to YAML file."""
    import yaml
    
    # Create directory if needed
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ Configuration saved to: {output_path}")
    print(f"\nNext steps:")
    print(f"1. Review and edit {output_path} if needed")
    print(f"2. Test connections: python scripts/test_db_connection.py --all")
    print(f"3. Run pipeline: python cbw_main.py --postprocess")

def main():
    parser = argparse.ArgumentParser(
        description="Generate database configuration file interactively",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='config/database.yaml',
        help='Output file path (default: config/database.yaml)'
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing configuration file'
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if os.path.exists(args.output) and not args.overwrite:
        print(f"❌ Configuration file already exists: {args.output}")
        print(f"Use --overwrite to replace it, or specify a different --output path")
        sys.exit(1)
    
    try:
        config = generate_config()
        save_config(config, args.output)
    except KeyboardInterrupt:
        print("\n\n⚠️  Configuration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
