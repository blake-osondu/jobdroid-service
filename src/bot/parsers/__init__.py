# src/bot/parsers/__init__.py
"""
Job board parsers
"""
from .indeed import IndeedParser
from .linkedin import LinkedInParser
from .base import BaseParser

__all__ = [
    'BaseParser',
    'IndeedParser',
    'LinkedInParser'
]