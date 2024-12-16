# tests/__init__.py
"""
Test suite for Job Application Bot
"""
import pytest
from pathlib import Path

# Set up test constants
TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / 'fixtures'
CONFIG_PATH = TEST_DIR / 'test_config.yaml'

# Ensure test directories exist
FIXTURES_DIR.mkdir(exist_ok=True)

def pytest_configure(config):
    """
    Custom pytest configuration
    """
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """
    Add markers to test items
    """
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "slow" in item.nodeid:
            item.add_marker(pytest.mark.slow)