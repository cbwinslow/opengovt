#!/usr/bin/env python3
###############################################################################
# Name:        test_db_connection.py
# Date:        2025-10-22
# Script Name: test_db_connection.py
# Version:     1.0
# Log Summary: Test database connections for all configured databases
# Description: Validates database connectivity and displays connection status
#              for each configured database type. Useful for troubleshooting
#              and validating configuration before running the main pipeline.
# Usage:
#   python scripts/test_db_connection.py [--db-type postgresql]
#   python scripts/test_db_connection.py --all
# Change Summary:
#   - 1.0 initial database connection testing script
###############################################################################

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path so we can import cbw modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from cbw_db_adapter import DatabaseManager
from cbw_utils import configure_logger, adapter_for

logger = configure_logger()
ad = adapter_for(logger, "test_db")

def test_database_connection(db_manager: DatabaseManager, db_type: str) -> bool:
    """Test connection to a specific database type.
    
    Args:
        db_manager: DatabaseManager instance
        db_type: Type of database to test (postgresql, mysql, etc.)
        
    Returns:
        True if connection successful, False otherwise
    """
    print(f"\n{'='*70}")
    print(f"Testing {db_type.upper()} connection...")
    print(f"{'='*70}")
    
    try:
        adapter = db_manager.get_adapter(db_type)
        
        if not adapter:
            print(f"❌ {db_type} is not enabled or not configured")
            return False
        
        print(f"📋 Connection Info: {adapter.get_connection_info()}")
        print(f"⏳ Attempting connection...")
        
        adapter.connect()
        print(f"✅ Connection established")
        
        print(f"⏳ Testing query execution...")
        success = adapter.test_connection()
        
        if success:
            print(f"✅ Query test passed")
            print(f"✨ {db_type.upper()} connection is working properly!")
            return True
        else:
            print(f"❌ Query test failed")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        ad.exception("Connection test failed for %s", db_type)
        return False
    finally:
        try:
            if adapter:
                adapter.close()
                print(f"🔒 Connection closed")
        except:
            pass

def test_all_databases(db_manager: DatabaseManager):
    """Test all enabled databases.
    
    Args:
        db_manager: DatabaseManager instance
    """
    enabled_dbs = db_manager.get_enabled_databases()
    
    if not enabled_dbs:
        print("⚠️  No databases are enabled in the configuration")
        return
    
    print(f"\n{'='*70}")
    print(f"Found {len(enabled_dbs)} enabled database(s): {', '.join(enabled_dbs)}")
    print(f"{'='*70}")
    
    results = {}
    for db_type in enabled_dbs:
        results[db_type] = test_database_connection(db_manager, db_type)
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    success_count = sum(1 for v in results.values() if v)
    fail_count = len(results) - success_count
    
    for db_type, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {db_type}")
    
    print(f"\nTotal: {len(results)} tested, {success_count} passed, {fail_count} failed")
    
    if fail_count > 0:
        print("\n⚠️  Some database connections failed. Check the configuration and logs.")
        sys.exit(1)
    else:
        print("\n✨ All database connections are working!")
        sys.exit(0)

def test_api_configs(db_manager: DatabaseManager):
    """Display API configuration status."""
    print(f"\n{'='*70}")
    print("API CONFIGURATIONS")
    print(f"{'='*70}")
    
    api_sources = db_manager.config.get('api_sources', {})
    
    if not api_sources:
        print("⚠️  No API sources configured")
        return
    
    for api_name, api_config in api_sources.items():
        print(f"\n📡 {api_name}:")
        print(f"   Base URL: {api_config.get('base_url', 'N/A')}")
        
        api_key_field = 'api_key'
        if api_key_field in api_config:
            api_key = api_config[api_key_field]
            if api_key:
                print(f"   API Key: {'*' * 20} (configured)")
            else:
                print(f"   API Key: ⚠️  Not configured (may be optional)")
        
        if 'description' in api_config:
            print(f"   Description: {api_config['description']}")
        
        if 'rate_limit' in api_config:
            print(f"   Rate Limit: {api_config['rate_limit']} requests/hour")

def main():
    parser = argparse.ArgumentParser(
        description="Test database connections for OpenGovt project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all enabled databases
  python scripts/test_db_connection.py --all
  
  # Test specific database
  python scripts/test_db_connection.py --db-type postgresql
  
  # Show API configurations
  python scripts/test_db_connection.py --api-config
  
  # Custom config file location
  python scripts/test_db_connection.py --all --config /path/to/database.yaml
        """
    )
    
    parser.add_argument(
        '--db-type',
        type=str,
        choices=['postgresql', 'mysql', 'sqlite', 'clickhouse', 'influxdb', 'victoriametrics'],
        help='Test specific database type'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Test all enabled databases'
    )
    
    parser.add_argument(
        '--api-config',
        action='store_true',
        help='Display API configuration status'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/database.yaml',
        help='Path to database configuration file (default: config/database.yaml)'
    )
    
    args = parser.parse_args()
    
    # Show help if no arguments provided
    if not (args.db_type or args.all or args.api_config):
        parser.print_help()
        sys.exit(0)
    
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Database Connection Test Utility" + " " * 21 + "║")
    print("╚" + "═" * 68 + "╝")
    
    try:
        db_manager = DatabaseManager(config_path=args.config)
        
        if args.api_config:
            test_api_configs(db_manager)
        
        if args.db_type:
            success = test_database_connection(db_manager, args.db_type)
            sys.exit(0 if success else 1)
        
        if args.all:
            test_all_databases(db_manager)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        ad.exception("Fatal error in test script")
        sys.exit(1)

if __name__ == "__main__":
    main()
