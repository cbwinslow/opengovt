#!/usr/bin/env python3
"""
Example: Using Multi-Database Support

This example demonstrates how to use the multi-database support in OpenGovt.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cbw_db_adapter import DatabaseManager

def example_database_usage():
    """Example of using the DatabaseManager with multiple databases."""
    
    print("="*70)
    print("Multi-Database Usage Example")
    print("="*70)
    
    # Initialize database manager
    db_manager = DatabaseManager(config_path="config/database.yaml")
    
    # Get list of enabled databases
    enabled = db_manager.get_enabled_databases()
    print(f"\n✅ Enabled databases: {', '.join(enabled)}")
    
    # Example 1: Get PostgreSQL adapter
    print("\n" + "="*70)
    print("Example 1: PostgreSQL Connection")
    print("="*70)
    
    pg_adapter = db_manager.get_adapter("postgresql")
    if pg_adapter:
        print(f"📋 {pg_adapter.get_connection_info()}")
        print("💡 Connection ready (call .connect() to establish)")
    else:
        print("⚠️  PostgreSQL is not enabled or configured")
    
    # Example 2: Check API configurations
    print("\n" + "="*70)
    print("Example 2: API Configuration")
    print("="*70)
    
    congress_api = db_manager.get_api_config("congress_api")
    if congress_api:
        print(f"📡 Congress API: {congress_api.get('base_url')}")
        print(f"🔑 API Key configured: {'Yes' if congress_api.get('api_key') else 'No'}")
        print(f"⏱️  Rate Limit: {congress_api.get('rate_limit')} requests/hour")
    
    # Example 3: Demonstrate different database types
    print("\n" + "="*70)
    print("Example 3: Available Database Types")
    print("="*70)
    
    db_descriptions = {
        'postgresql': 'Relational database for structured legislative data',
        'mysql': 'Alternative relational database',
        'sqlite': 'Lightweight local database for development',
        'clickhouse': 'Columnar database for high-performance analytics',
        'influxdb': 'Time series database for tracking metrics',
        'victoriametrics': 'Prometheus-compatible time series database'
    }
    
    for db_type, description in db_descriptions.items():
        adapter = db_manager.get_adapter(db_type)
        status = "✅ Enabled" if adapter else "⚪ Disabled"
        print(f"\n{status} {db_type}:")
        print(f"    {description}")
    
    # Clean up
    db_manager.close_all()
    
    print("\n" + "="*70)
    print("Example Complete!")
    print("="*70)
    print("\nNext steps:")
    print("1. Enable databases in config/database.yaml")
    print("2. Test connections: python scripts/test_db_connection.py --all")
    print("3. Run pipeline with database: python cbw_main.py --postprocess")

if __name__ == "__main__":
    example_database_usage()
