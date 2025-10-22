###############################################################################
# Name:        cbw_db_adapter.py
# Date:        2025-10-22
# Script Name: cbw_db_adapter.py
# Version:     1.0
# Log Summary: Multi-database adapter supporting PostgreSQL, MySQL, SQLite,
#              ClickHouse, InfluxDB, and VictoriaMetrics
# Description: Provides a unified interface for connecting to and managing
#              multiple database systems. Implements adapter pattern to handle
#              database-specific operations.
# Change Summary:
#   - 1.0 initial multi-database adapter
# Inputs:
#   - Database configuration from YAML or environment variables
# Outputs:
#   - Database connections and operations across multiple database types
###############################################################################

import os
import yaml
from typing import Dict, Any, Optional, List, Union
from abc import ABC, abstractmethod
from cbw_utils import labeled, configure_logger, adapter_for
import re

logger = configure_logger()
ad = adapter_for(logger, "db_adapter")

def expand_env_vars(value: str) -> str:
    """Expand environment variables in configuration strings.
    
    Supports ${VAR:-default} syntax for environment variables with defaults.
    """
    if not isinstance(value, str):
        return value
    
    # Match ${VAR:-default} or ${VAR}
    pattern = r'\$\{([^}:]+)(?::-(.*?))?\}'
    
    def replacer(match):
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ''
        return os.environ.get(var_name, default_value)
    
    return re.sub(pattern, replacer, value)

class DatabaseAdapter(ABC):
    """Abstract base class for database adapters."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        
    @abstractmethod
    def connect(self):
        """Establish database connection."""
        pass
    
    @abstractmethod
    def close(self):
        """Close database connection."""
        pass
    
    @abstractmethod
    def execute(self, query: str, params: Optional[tuple] = None):
        """Execute a query."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if connection is working."""
        pass
    
    def get_connection_info(self) -> str:
        """Get safe connection info for logging (without credentials)."""
        return f"{self.__class__.__name__}"

class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL database adapter using psycopg2."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.conn_str = expand_env_vars(config.get('connection_string', ''))
        
    @labeled("postgres_connect")
    def connect(self):
        try:
            import psycopg2
            self.connection = psycopg2.connect(self.conn_str)
            self.connection.autocommit = False
            ad.info("Connected to PostgreSQL")
        except ImportError:
            raise RuntimeError("psycopg2 not installed. pip install psycopg2-binary")
        except Exception as e:
            ad.exception("Failed to connect to PostgreSQL: %s", e)
            raise
    
    @labeled("postgres_close")
    def close(self):
        if self.connection:
            self.connection.close()
            ad.info("PostgreSQL connection closed")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        if not self.connection:
            self.connect()
        with self.connection.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    
    @labeled("postgres_test")
    def test_connection(self) -> bool:
        try:
            if not self.connection:
                self.connect()
            with self.connection.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                return result[0] == 1
        except Exception as e:
            ad.error("PostgreSQL connection test failed: %s", e)
            return False
    
    def get_connection_info(self) -> str:
        # Sanitize connection string to hide password
        sanitized = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', self.conn_str)
        return f"PostgreSQL: {sanitized}"

class MySQLAdapter(DatabaseAdapter):
    """MySQL/MariaDB database adapter using pymysql."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.conn_str = expand_env_vars(config.get('connection_string', ''))
        
    @labeled("mysql_connect")
    def connect(self):
        try:
            import pymysql
            from sqlalchemy import create_engine
            self.engine = create_engine(
                self.conn_str,
                pool_size=self.config.get('pool_size', 10),
                max_overflow=self.config.get('max_overflow', 20)
            )
            self.connection = self.engine.connect()
            ad.info("Connected to MySQL")
        except ImportError:
            raise RuntimeError("pymysql not installed. pip install pymysql")
        except Exception as e:
            ad.exception("Failed to connect to MySQL: %s", e)
            raise
    
    @labeled("mysql_close")
    def close(self):
        if self.connection:
            self.connection.close()
            ad.info("MySQL connection closed")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        if not self.connection:
            self.connect()
        from sqlalchemy import text
        result = self.connection.execute(text(query), params or {})
        return result.fetchall()
    
    @labeled("mysql_test")
    def test_connection(self) -> bool:
        try:
            if not self.connection:
                self.connect()
            from sqlalchemy import text
            result = self.connection.execute(text("SELECT 1"))
            return result.fetchone()[0] == 1
        except Exception as e:
            ad.error("MySQL connection test failed: %s", e)
            return False
    
    def get_connection_info(self) -> str:
        sanitized = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', self.conn_str)
        return f"MySQL: {sanitized}"

class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.conn_str = expand_env_vars(config.get('connection_string', ''))
        
    @labeled("sqlite_connect")
    def connect(self):
        try:
            from sqlalchemy import create_engine
            self.engine = create_engine(self.conn_str)
            self.connection = self.engine.connect()
            ad.info("Connected to SQLite")
        except Exception as e:
            ad.exception("Failed to connect to SQLite: %s", e)
            raise
    
    @labeled("sqlite_close")
    def close(self):
        if self.connection:
            self.connection.close()
            ad.info("SQLite connection closed")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        if not self.connection:
            self.connect()
        from sqlalchemy import text
        result = self.connection.execute(text(query), params or {})
        return result.fetchall()
    
    @labeled("sqlite_test")
    def test_connection(self) -> bool:
        try:
            if not self.connection:
                self.connect()
            from sqlalchemy import text
            result = self.connection.execute(text("SELECT 1"))
            return result.fetchone()[0] == 1
        except Exception as e:
            ad.error("SQLite connection test failed: %s", e)
            return False
    
    def get_connection_info(self) -> str:
        return f"SQLite: {self.conn_str}"

class ClickHouseAdapter(DatabaseAdapter):
    """ClickHouse database adapter for analytical queries."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = expand_env_vars(str(config.get('host', 'localhost')))
        self.port = int(expand_env_vars(str(config.get('port', '9000'))))
        self.database = expand_env_vars(config.get('database', 'default'))
        self.user = expand_env_vars(config.get('user', 'default'))
        self.password = expand_env_vars(config.get('password', ''))
        
    @labeled("clickhouse_connect")
    def connect(self):
        try:
            from clickhouse_driver import Client
            self.connection = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            ad.info("Connected to ClickHouse")
        except ImportError:
            raise RuntimeError("clickhouse-driver not installed. pip install clickhouse-driver")
        except Exception as e:
            ad.exception("Failed to connect to ClickHouse: %s", e)
            raise
    
    @labeled("clickhouse_close")
    def close(self):
        if self.connection:
            self.connection.disconnect()
            ad.info("ClickHouse connection closed")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        if not self.connection:
            self.connect()
        return self.connection.execute(query, params or [])
    
    @labeled("clickhouse_test")
    def test_connection(self) -> bool:
        try:
            if not self.connection:
                self.connect()
            result = self.connection.execute("SELECT 1")
            return result[0][0] == 1
        except Exception as e:
            ad.error("ClickHouse connection test failed: %s", e)
            return False
    
    def get_connection_info(self) -> str:
        return f"ClickHouse: {self.user}@{self.host}:{self.port}/{self.database}"

class InfluxDBAdapter(DatabaseAdapter):
    """InfluxDB adapter for time series data."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = expand_env_vars(config.get('url', ''))
        self.token = expand_env_vars(config.get('token', ''))
        self.org = expand_env_vars(config.get('org', ''))
        self.bucket = expand_env_vars(config.get('bucket', ''))
        
    @labeled("influxdb_connect")
    def connect(self):
        try:
            from influxdb_client import InfluxDBClient
            self.connection = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            self.write_api = self.connection.write_api()
            self.query_api = self.connection.query_api()
            ad.info("Connected to InfluxDB")
        except ImportError:
            raise RuntimeError("influxdb-client not installed. pip install influxdb-client")
        except Exception as e:
            ad.exception("Failed to connect to InfluxDB: %s", e)
            raise
    
    @labeled("influxdb_close")
    def close(self):
        if self.connection:
            self.connection.close()
            ad.info("InfluxDB connection closed")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        if not self.connection:
            self.connect()
        return self.query_api.query(query)
    
    @labeled("influxdb_test")
    def test_connection(self) -> bool:
        try:
            if not self.connection:
                self.connect()
            # Test by checking bucket availability
            buckets_api = self.connection.buckets_api()
            buckets = buckets_api.find_buckets().buckets
            return len(buckets) >= 0
        except Exception as e:
            ad.error("InfluxDB connection test failed: %s", e)
            return False
    
    def get_connection_info(self) -> str:
        return f"InfluxDB: {self.url} (org: {self.org}, bucket: {self.bucket})"

class VictoriaMetricsAdapter(DatabaseAdapter):
    """VictoriaMetrics adapter for time series metrics."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = expand_env_vars(config.get('url', ''))
        
    @labeled("victoriametrics_connect")
    def connect(self):
        try:
            import requests
            self.session = requests.Session()
            ad.info("Connected to VictoriaMetrics")
        except ImportError:
            raise RuntimeError("requests not installed")
        except Exception as e:
            ad.exception("Failed to connect to VictoriaMetrics: %s", e)
            raise
    
    @labeled("victoriametrics_close")
    def close(self):
        if hasattr(self, 'session'):
            self.session.close()
            ad.info("VictoriaMetrics session closed")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        if not hasattr(self, 'session'):
            self.connect()
        # VictoriaMetrics uses PromQL for queries
        response = self.session.get(f"{self.url}/api/v1/query", params={'query': query})
        response.raise_for_status()
        return response.json()
    
    @labeled("victoriametrics_test")
    def test_connection(self) -> bool:
        try:
            if not hasattr(self, 'session'):
                self.connect()
            response = self.session.get(f"{self.url}/health")
            return response.status_code == 200
        except Exception as e:
            ad.error("VictoriaMetrics connection test failed: %s", e)
            return False
    
    def get_connection_info(self) -> str:
        return f"VictoriaMetrics: {self.url}"

class DatabaseManager:
    """Manages multiple database connections from configuration."""
    
    def __init__(self, config_path: str = "config/database.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.adapters: Dict[str, DatabaseAdapter] = {}
        
    @labeled("db_manager_load_config")
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            ad.info("Loaded database configuration from %s", self.config_path)
            return config
        except FileNotFoundError:
            ad.warning("Config file not found: %s, using defaults", self.config_path)
            return {'databases': {}, 'features': {}}
        except Exception as e:
            ad.exception("Failed to load config: %s", e)
            raise
    
    @labeled("db_manager_init_adapter")
    def get_adapter(self, db_type: str) -> Optional[DatabaseAdapter]:
        """Get or create a database adapter for the specified type."""
        if db_type in self.adapters:
            return self.adapters[db_type]
        
        db_config = self.config.get('databases', {}).get(db_type)
        if not db_config:
            ad.warning("No configuration found for database type: %s", db_type)
            return None
        
        if not db_config.get('enabled', False):
            ad.info("Database type %s is not enabled", db_type)
            return None
        
        # Create appropriate adapter
        adapter_map = {
            'postgresql': PostgreSQLAdapter,
            'mysql': MySQLAdapter,
            'sqlite': SQLiteAdapter,
            'clickhouse': ClickHouseAdapter,
            'influxdb': InfluxDBAdapter,
            'victoriametrics': VictoriaMetricsAdapter,
        }
        
        adapter_class = adapter_map.get(db_type)
        if not adapter_class:
            ad.error("Unknown database type: %s", db_type)
            return None
        
        try:
            adapter = adapter_class(db_config)
            self.adapters[db_type] = adapter
            ad.info("Created adapter for %s", db_type)
            return adapter
        except Exception as e:
            ad.exception("Failed to create adapter for %s: %s", db_type, e)
            return None
    
    @labeled("db_manager_get_enabled")
    def get_enabled_databases(self) -> List[str]:
        """Get list of enabled database types."""
        enabled = []
        for db_type, db_config in self.config.get('databases', {}).items():
            if db_config.get('enabled', False):
                enabled.append(db_type)
        return enabled
    
    @labeled("db_manager_close_all")
    def close_all(self):
        """Close all database connections."""
        for db_type, adapter in self.adapters.items():
            try:
                adapter.close()
            except Exception as e:
                ad.error("Failed to close %s: %s", db_type, e)
    
    def get_api_config(self, api_name: str) -> Optional[Dict[str, Any]]:
        """Get API configuration for government data sources."""
        api_sources = self.config.get('api_sources', {})
        api_config = api_sources.get(api_name)
        
        if api_config:
            # Expand environment variables in API config
            expanded = {}
            for key, value in api_config.items():
                if isinstance(value, str):
                    expanded[key] = expand_env_vars(value)
                else:
                    expanded[key] = value
            return expanded
        return None
