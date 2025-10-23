"""
Basic tests to verify test infrastructure is working.
"""

import pytest


@pytest.mark.unit
def test_basic_assertion():
    """Test that basic assertions work."""
    assert True
    assert 1 + 1 == 2
    assert "hello" == "hello"


@pytest.mark.unit
def test_fixtures_work(sample_tweet_text):
    """Test that fixtures are available."""
    assert sample_tweet_text is not None
    assert len(sample_tweet_text) > 0
    assert isinstance(sample_tweet_text, str)


@pytest.mark.unit
def test_imports():
    """Test that key modules can be imported."""
    # These should not raise ImportError
    import os
    import sys
    import psycopg2
    
    assert os is not None
    assert sys is not None
    assert psycopg2 is not None


@pytest.mark.unit
def test_models_can_be_imported():
    """Test that our models can be imported."""
    try:
        from models import person, bill, vote, social_media
        assert person is not None
        assert bill is not None
        assert vote is not None
        assert social_media is not None
    except ImportError as e:
        # Models should be importable
        pytest.fail(f"Failed to import models: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
