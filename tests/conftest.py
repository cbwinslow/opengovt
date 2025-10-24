"""
Test configuration and fixtures.

This module provides common test fixtures and configuration for the test suite.
"""

import pytest
import psycopg2
from typing import Generator
import os


@pytest.fixture(scope='session')
def test_database_url() -> str:
    """Get test database URL from environment."""
    return os.getenv('TEST_DATABASE_URL', 'postgresql://postgres:postgres@localhost/opengovt_test')


@pytest.fixture(scope='session')
def test_db_connection(test_database_url: str) -> Generator:
    """Create test database connection."""
    conn = psycopg2.connect(test_database_url)
    yield conn
    conn.close()


@pytest.fixture(scope='function')
def db_cursor(test_db_connection):
    """Provide a database cursor with automatic rollback."""
    cursor = test_db_connection.cursor()
    yield cursor
    test_db_connection.rollback()
    cursor.close()


@pytest.fixture
def sample_tweet_text():
    """Sample tweet text for testing."""
    return "Just voted to support healthcare reform! #Congress #Healthcare"


@pytest.fixture
def sample_negative_tweet():
    """Sample negative tweet for testing."""
    return "Disappointed with today's vote. This will hurt working families."


@pytest.fixture
def sample_toxic_text():
    """Sample toxic text for testing (educational purposes only)."""
    return "You are a terrible person and should be ashamed!"


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "requires_api: Tests requiring API access")
    config.addinivalue_line("markers", "requires_db: Tests requiring database")
