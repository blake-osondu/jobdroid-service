# src/bot/__init__.py
"""
Bot core functionality
"""
from .core import JobApplicationBot
from .parsers import IndeedParser, LinkedInParser
from .automation import AutomationSession
from .ml import FormDetector

__all__ = [
    'JobApplicationBot',
    'IndeedParser',
    'LinkedInParser',
    'AutomationSession',
    'FormDetector'
]