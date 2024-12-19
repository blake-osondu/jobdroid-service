# tests/conftest.py
import pytest
import asyncio
from typing import Dict
from src.bot.parsers.base import BaseParser
from src.utils.proxy import ProxyRotator
from src.bot.automation.session import AutomationSession
import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = str(Path(__file__).parent.parent / "src")
sys.path.append(src_path)

from bot.parsers.base import BaseParser

@pytest.fixture
def config() -> Dict:
    return {
        "max_retries": 3,
        "timeout": 10,
        "user_agent": "Mozilla/5.0...",
        "proxy_settings": {
            "enabled": True,
            "max_fails": 3
        }
    }

@pytest.fixture
def proxy_rotator():
    return ProxyRotator()

@pytest.fixture
def automation_session(config):
    return AutomationSession(config)