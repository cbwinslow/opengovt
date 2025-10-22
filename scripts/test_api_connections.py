#!/usr/bin/env python3
###############################################################################
# Name:        test_api_connections.py
# Date:        2025-10-22
# Script Name: test_api_connections.py
# Version:     1.0
# Log Summary: Test API connections to government data sources
# Description: Validates API connectivity and displays status for Congress.gov,
#              GovInfo.gov, OpenStates, and other government APIs.
# Usage:
#   python scripts/test_api_connections.py
#   python scripts/test_api_connections.py --api congress_api
# Change Summary:
#   - 1.0 initial API connection testing script
###############################################################################

import sys
import os
import argparse
from pathlib import Path
import requests
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cbw_db_adapter import DatabaseManager
from cbw_utils import configure_logger, adapter_for

logger = configure_logger()
ad = adapter_for(logger, "test_api")

def test_congress_api(config: Dict[str, Any]) -> bool:
    """Test Congress.gov API connection."""
    base_url = config.get('base_url', '')
    api_key = config.get('api_key', '')
    
    if not api_key:
        print("⚠️  No API key configured. Get one at: https://api.congress.gov/sign-up/")
        return False
    
    try:
        # Test with a simple request for current congress
        url = f"{base_url}/congress/current"
        params = {'api_key': api_key, 'format': 'json'}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if 'congress' in data:
            congress_num = data['congress'].get('number', 'unknown')
            print(f"✅ Current Congress: {congress_num}")
            return True
        else:
            print(f"⚠️  Unexpected response format")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_govinfo_api(config: Dict[str, Any]) -> bool:
    """Test GovInfo.gov API connection."""
    base_url = config.get('base_url', '')
    api_key = config.get('api_key', '')
    
    if not api_key:
        print("⚠️  No API key configured. Get one at: https://www.govinfo.gov/api-signup")
        return False
    
    try:
        # Test with collections endpoint
        url = f"{base_url}/collections"
        headers = {'X-Api-Key': api_key}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if 'collections' in data:
            count = len(data['collections'])
            print(f"✅ Found {count} collections")
            return True
        else:
            print(f"⚠️  Unexpected response format")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_openstates_api(config: Dict[str, Any]) -> bool:
    """Test OpenStates API v3 connection."""
    base_url = config.get('base_url', '')
    api_key = config.get('api_key', '')
    
    if not api_key:
        print("⚠️  No API key configured. Get one at: https://openstates.org/accounts/profile/")
        print("ℹ️  Note: API works without key but with lower rate limits")
    
    try:
        # Test with jurisdictions endpoint
        url = f"{base_url}/jurisdictions"
        headers = {}
        if api_key:
            headers['X-API-KEY'] = api_key
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if 'results' in data:
            count = len(data['results'])
            print(f"✅ Found {count} jurisdictions")
            return True
        else:
            print(f"⚠️  Unexpected response format")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_govinfo_bulkdata(config: Dict[str, Any]) -> bool:
    """Test GovInfo.gov bulk data access."""
    base_url = config.get('base_url', '')
    
    try:
        # Test with a simple HEAD request
        url = f"{base_url}/BILLSTATUS"
        
        response = requests.head(url, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        print(f"✅ Bulk data endpoint accessible")
        return True
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_openstates_bulk(config: Dict[str, Any]) -> bool:
    """Test OpenStates bulk data access."""
    base_url = config.get('base_url', '')
    
    try:
        # Test with a simple HEAD request
        response = requests.head(base_url, timeout=10, allow_redirects=True)
        
        # Even 403 or 404 means the server is reachable
        if response.status_code in [200, 403, 404]:
            print(f"✅ Bulk data server reachable")
            return True
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_ny_openlegislation(config: Dict[str, Any]) -> bool:
    """Test NY OpenLegislation API connection."""
    base_url = config.get('base_url', '')
    api_key = config.get('api_key', '')
    
    if not api_key:
        print("⚠️  No API key configured. Get one at: https://legislation.nysenate.gov/")
        return False
    
    try:
        # Test with bills endpoint
        url = f"{base_url}/bills/2023"
        params = {'key': api_key, 'limit': 1}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            print(f"✅ API accessible")
            return True
        else:
            print(f"⚠️  Unexpected response format")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_api(api_name: str, config: Dict[str, Any]) -> bool:
    """Test a specific API connection."""
    print(f"\n{'='*70}")
    print(f"Testing {api_name.upper()}")
    print(f"{'='*70}")
    
    print(f"📋 Base URL: {config.get('base_url', 'N/A')}")
    
    if 'description' in config:
        print(f"📝 Description: {config['description']}")
    
    if 'rate_limit' in config:
        print(f"⏱️  Rate Limit: {config['rate_limit']} requests/hour")
    
    print(f"\n⏳ Testing connection...")
    
    # Route to appropriate test function
    test_functions = {
        'congress_api': test_congress_api,
        'govinfo_api': test_govinfo_api,
        'govinfo_bulkdata': test_govinfo_bulkdata,
        'openstates_api': test_openstates_api,
        'openstates_bulk': test_openstates_bulk,
        'ny_openlegislation': test_ny_openlegislation,
    }
    
    test_func = test_functions.get(api_name)
    if test_func:
        return test_func(config)
    else:
        print(f"⚠️  No test function for {api_name}")
        return False

def test_all_apis(db_manager: DatabaseManager):
    """Test all configured APIs."""
    api_sources = db_manager.config.get('api_sources', {})
    
    if not api_sources:
        print("⚠️  No API sources configured")
        return
    
    print(f"\n{'='*70}")
    print(f"Found {len(api_sources)} API source(s) configured")
    print(f"{'='*70}")
    
    results = {}
    for api_name in api_sources:
        config = db_manager.get_api_config(api_name)
        if config:
            results[api_name] = test_api(api_name, config)
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    success_count = sum(1 for v in results.values() if v)
    fail_count = len(results) - success_count
    
    for api_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {api_name}")
    
    print(f"\nTotal: {len(results)} tested, {success_count} passed, {fail_count} failed")
    
    if fail_count > 0:
        print("\n⚠️  Some API connections failed. Check API keys and network connectivity.")
        print("ℹ️  See docs/DATABASE_CONFIGURATION.md for API key setup instructions.")

def main():
    parser = argparse.ArgumentParser(
        description="Test API connections to government data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all APIs
  python scripts/test_api_connections.py
  
  # Test specific API
  python scripts/test_api_connections.py --api congress_api
  
  # Custom config file
  python scripts/test_api_connections.py --config /path/to/database.yaml
        """
    )
    
    parser.add_argument(
        '--api',
        type=str,
        choices=['congress_api', 'govinfo_api', 'govinfo_bulkdata', 
                 'openstates_api', 'openstates_bulk', 'ny_openlegislation'],
        help='Test specific API'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/database.yaml',
        help='Path to database configuration file (default: config/database.yaml)'
    )
    
    args = parser.parse_args()
    
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 19 + "API Connection Test Utility" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    
    try:
        db_manager = DatabaseManager(config_path=args.config)
        
        if args.api:
            config = db_manager.get_api_config(args.api)
            if config:
                success = test_api(args.api, config)
                sys.exit(0 if success else 1)
            else:
                print(f"❌ API {args.api} not found in configuration")
                sys.exit(1)
        else:
            test_all_apis(db_manager)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        ad.exception("Fatal error in test script")
        sys.exit(1)

if __name__ == "__main__":
    main()
